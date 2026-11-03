from datetime import timedelta
import hashlib
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, envelope, get_project, get_project_entity, new_id, now
from src.core.database import database
from src.schemas.contracts.automation import CollaborationOperationInput
from src.schemas.contracts.design import TestCaseDraftPatch
from src.schemas.contracts.requirements import RequirementDraftPatch
from src.repositories.collaboration import collaboration_repository
from src.modules.requirements.services.requirement_records import update_requirement_draft_record
from src.modules.design.services.test_case_records import update_test_case_draft_record


def _operation_request_hash(project_id, artifact_type, artifact_id, payload):
    request = payload.model_dump(mode="json")
    request.update(
        {"project_id": project_id, "artifact_type": artifact_type, "artifact_id": artifact_id}
    )
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_operation_replay(existing, project_id, artifact_type, artifact_id, payload, user):
    if not existing.get("created_by"):
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if existing["created_by"] != user.id:
        raise HTTPException(403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _operation_request_hash(project_id, artifact_type, artifact_id, payload):
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})


async def artifact_context(project_id, artifact_type, artifact_id, user, edit=False):
    
    if artifact_type == 'requirement':
        requirement = await get_project_entity(
            "requirements", artifact_id, user, "requirement.update" if edit else "requirement.read"
        )
        if requirement["project_id"] != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        version = await collaboration_repository.find_requirement_version(
            requirement["current_version_id"], project_id
        )
        if not version:
            raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
        if edit and version.get("status") != 'DRAFT':
            raise HTTPException(
                status_code=409, detail={"code": 'IMMUTABLE_REQUIREMENT_VERSION'}
            )
        return version
    draft = await get_project_entity(
        "test_case_drafts", artifact_id, user, "testcase.update" if edit else "testcase.read"
    )
    if draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if edit and draft.get("status") != 'DRAFT':
        raise HTTPException(
            status_code=409, detail={"code": 'IMMUTABLE_TEST_CASE_DRAFT'}
        )
    return draft


class CollaborationService:
    @staticmethod
    async def update_presence(project_id, payload, user):
        
        await get_project(project_id, user, "collaboration.presence.read")
        await artifact_context(project_id, payload.artifact_type, payload.artifact_id, user)
        timestamp = now()
        return await collaboration_repository.upsert_presence(
            {
                "project_id": project_id,
                "artifact_type": payload.artifact_type,
                "artifact_id": payload.artifact_id,
                "user_id": user.id,
                "client_id": payload.client_id,
            },
            {
                "user_email": user.email,
                "last_seen_at": timestamp,
                "expires_at": timestamp + timedelta(seconds=45),
            },
            {"_id": new_id('COLSESS'), "created_at": timestamp},
        )

    @staticmethod
    async def list_presence(project_id, artifact_type, artifact_id, user):
        
        await get_project(project_id, user, "collaboration.presence.read")
        await artifact_context(project_id, artifact_type, artifact_id, user)
        return await collaboration_repository.list_presence(
            {
                "project_id": project_id,
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
                "expires_at": {"$gt": now()},
            },
            100,
        )

    @staticmethod
    async def apply_operation(project_id, artifact_type, artifact_id, payload, user):
        
        current = await artifact_context(project_id, artifact_type, artifact_id, user, edit=True)
        existing = await collaboration_repository.find_operation(
            project_id, payload.operation_id
        )
        if existing:
            if (
                existing.get("artifact_type") != artifact_type
                or existing.get("artifact_id") != artifact_id
            ):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            _verify_operation_replay(
                existing, project_id, artifact_type, artifact_id, payload, user
            )
            return existing["result"]
        current_revision = current["revision"]
        changes = payload.changes
        rebased = False
        if payload.base_revision != current_revision:
            operations = await collaboration_repository.list_operations_since(
                project_id,
                artifact_type,
                artifact_id,
                payload.base_revision,
                10000,
            )
            changed_keys = {
                key for operation in operations for key in operation.get("changed_keys", [])
            }
            if changed_keys.isdisjoint(changes):
                rebased = True
            else:
                conflict = {
                    "_id": new_id('DRAFTCONFLICT'),
                    "project_id": project_id,
                    "artifact_type": artifact_type,
                    "artifact_id": artifact_id,
                    "base_revision": payload.base_revision,
                    "current_revision": current_revision,
                    "incoming_changes": changes,
                    "changed_keys_since_base": sorted(changed_keys),
                    "operation_id": payload.operation_id,
                    "status": 'OPEN',
                    "revision": 1,
                    "created_by": user.id,
                    "created_at": now(),
                    "updated_at": now(),
                }
                await collaboration_repository.insert_conflict(conflict)
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": 'DRAFT_CONFLICT_REQUIRES_REVIEW',
                        "conflict_id": conflict["_id"],
                    },
                )
        record = {
            "_id": new_id('COLOP'),
            "project_id": project_id,
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "operation_id": payload.operation_id,
            "idempotency_request_hash": _operation_request_hash(
                project_id, artifact_type, artifact_id, payload
            ),
            "base_revision": payload.base_revision,
            "changed_keys": sorted(changes),
            "rebased": rebased,
            "created_by": user.id,
            "created_at": now(),
        }
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    if artifact_type == 'requirement':
                        updated = await update_requirement_draft_record(
                            project_id,
                            artifact_id,
                            RequirementDraftPatch(expected_revision=current_revision, **changes),
                            user,
                            session=session,
                        )
                        result = envelope(
                            updated, revision=updated["current_version"]["revision"]
                        )
                    else:
                        updated = await update_test_case_draft_record(
                            artifact_id,
                            TestCaseDraftPatch(expected_revision=current_revision, **changes),
                            user,
                            project_id,
                            session=session,
                        )
                        result = envelope(updated, revision=updated["revision"])
                    record["result"] = result
                    record["result_revision"] = result["meta"]["revision"]
                    await collaboration_repository.insert_operation(record, session=session)
                    await audit(
                        user.id,
                        "collaboration_operation_applied",
                        "CollaborationSession",
                        record["_id"],
                        project_id,
                        {"artifact_type": artifact_type, "artifact_id": artifact_id, "rebased": rebased},
                        session=session,
                    )
        except DuplicateKeyError:
            existing = await collaboration_repository.find_operation(
                project_id, payload.operation_id
            )
            if existing:
                if (
                    existing.get("artifact_type") != artifact_type
                    or existing.get("artifact_id") != artifact_id
                ):
                    raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
                _verify_operation_replay(
                    existing, project_id, artifact_type, artifact_id, payload, user
                )
                return existing["result"]
            raise
        except HTTPException as error:
            if error.status_code != 409:
                raise
            raise HTTPException(
                status_code=409,
                detail={"code": 'COLLABORATION_RETRY_REQUIRED'},
            ) from error
        return result

    @staticmethod
    async def list_conflicts(project_id, user):
        
        await get_project(project_id, user, "collaboration.conflict.resolve")
        return await collaboration_repository.list_conflicts(
            project_id, 1000
        )

    @classmethod
    async def resolve_conflict(cls, project_id, conflict_id, payload, user):
        
        conflict = await get_project_entity(
            "draft_conflicts", conflict_id, user, "collaboration.conflict.resolve"
        )
        if conflict["project_id"] != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        current = await artifact_context(
            project_id, conflict["artifact_type"], conflict["artifact_id"], user, edit=True
        )
        if current["revision"] != payload.expected_revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": 'REVISION_CONFLICT',
                    "current_revision": current["revision"],
                },
            )
        changes = (
            {}
            if payload.resolution == 'KEEP_CURRENT'
            else conflict["incoming_changes"]
            if payload.resolution == 'APPLY_INCOMING'
            else payload.merged_changes
        )
        result = None
        if changes:
            result = await cls.apply_operation(
                project_id,
                conflict["artifact_type"],
                conflict["artifact_id"],
                CollaborationOperationInput(
                    base_revision=current["revision"],
                    operation_id=f"resolve-{conflict_id}-{current['revision']}",
                    changes=changes,
                ),
                user,
            )
        timestamp = now()
        updated = await collaboration_repository.resolve_conflict(
            conflict_id,
            project_id,
            'OPEN',
            conflict["revision"],
            {
                "status": 'RESOLVED',
                "resolution": payload.resolution,
                "reason": payload.reason,
                "resolved_by": user.id,
                "resolved_at": timestamp,
                "updated_at": timestamp,
            },
        )
        if not updated:
            raise HTTPException(
                status_code=409, detail={"code": 'CONFLICT_ALREADY_RESOLVED'}
            )
        await audit(
            user.id,
            "collaboration_conflict_resolved",
            "DraftConflict",
            conflict_id,
            project_id,
            {"resolution": payload.resolution, "reason": payload.reason},
        )
        return {"conflict": updated, "result": result}
