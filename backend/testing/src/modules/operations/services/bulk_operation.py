import hashlib
import json
from functools import wraps

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.core.project_settings import resolve_project_settings
from src.core.database import database
from src.schemas.contracts.design import ProposalAction
from src.repositories.bulk_operation import bulk_operation_repository
from src.modules.quality.services.maintenance_proposal import create_maintenance_proposal_records
from src.modules.quality.services.proposal_application import apply_maintenance_proposal


def _request_hash(operation_type, project_id, payload):
    request = payload.model_dump(mode="json", exclude={"idempotency_key"})
    request.update({"operation_type": operation_type, "project_id": project_id})
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_replay(existing, operation_type, project_id, payload, user):
    if not existing.get("created_by"):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if existing["created_by"] != user.id:
        raise HTTPException(status_code=403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _request_hash(operation_type, project_id, payload):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})


def operation_key(payload):
    return payload.idempotency_key or new_id('OP')


def item_result(item_id, status, code=None, **details):
    result = {"id": item_id, "status": status}
    if code:
        result["code"] = code
    result.update(details)
    return result


def _transactional_bulk(operation_type):
    def decorate(method):
        @wraps(method)
        async def run(cls, project_id, payload, user, *args, **kwargs):
            try:
                async with await database.client.start_session() as session:
                    async with session.start_transaction():
                        return await method(
                            cls,
                            project_id,
                            payload,
                            user,
                            *args,
                            session=session,
                            **kwargs,
                        )
            except DuplicateKeyError:
                replay = await cls.replay(
                    project_id, operation_key(payload), operation_type, payload, user
                )
                if replay is not None:
                    return replay
                raise

        return run

    return decorate


class BulkOperationService:
    @staticmethod
    async def finish(
        project_id,
        operation_type,
        succeeded,
        failed,
        user,
        idempotency_key=None,
        request_payload=None,
        preview=False,
        results=None,
        details=None,
        session=None,
    ):
        if idempotency_key:
            existing = await bulk_operation_repository.find_operation(
                project_id, idempotency_key
            )
            if existing:
                if request_payload is None:
                    raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
                _verify_replay(existing, operation_type, project_id, request_payload, user)
                return existing["response"]
        operation = {
            "_id": new_id('OP'),
            "operation_id": new_id('OPR'),
            "project_id": project_id,
            "operation_type": operation_type,
            "succeeded": succeeded,
            "failed": failed,
            "created_by": user.id,
            "created_at": now(),
            "idempotency_key": idempotency_key,
            "idempotency_request_hash": (
                _request_hash(operation_type, project_id, request_payload)
                if request_payload is not None
                else None
            ),
            "preview": preview,
        }
        response = {
            "operation_id": operation["operation_id"],
            "operation_type": operation_type,
            "status": 'PREVIEW' if preview else 'COMPLETED',
            "preview": preview,
            "succeeded": succeeded,
            "failed": failed,
            "results": results or [],
            "details": details or {},
        }
        operation["response"] = response
        try:
            async def persist(active_session):
                await bulk_operation_repository.insert_operation(
                    operation, session=active_session
                )
                await audit(
                    user.id,
                    "bulk_operation_completed",
                    "BulkOperation",
                    operation["_id"],
                    project_id,
                    {
                        "operation_type": operation_type,
                        "succeeded": len(succeeded),
                        "failed": len(failed),
                        "preview": preview,
                    },
                    session=active_session,
                )

            if session is not None:
                await persist(session)
            else:
                async with await database.client.start_session() as active_session:
                    async with active_session.start_transaction():
                        await persist(active_session)
        except DuplicateKeyError:
            if session is not None:
                raise
            if idempotency_key:
                existing = await bulk_operation_repository.find_operation(
                    project_id, idempotency_key
                )
                if existing:
                    if request_payload is None:
                        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
                    _verify_replay(existing, operation_type, project_id, request_payload, user)
                    return existing["response"]
            raise
        return response

    @staticmethod
    async def replay(project_id, idempotency_key, operation_type, payload, user):
        if not idempotency_key:
            return None
        existing = await bulk_operation_repository.find_operation(project_id, idempotency_key)
        if existing:
            _verify_replay(existing, operation_type, project_id, payload, user)
        return existing["response"] if existing else None

    @staticmethod
    async def fresh_proposal(proposal):
        if proposal.get("proposal_type") not in ['UPDATE_TEST_CASE', 'MARK_OBSOLETE']:
            return True
        target = await bulk_operation_repository.find_case_version_identity(
            proposal.get("target_artifact_id"), proposal["project_id"]
        )
        return bool(target and target.get("current_version_id") == proposal.get("base_version_id"))

    @classmethod
    @_transactional_bulk('BULK_TAGS')
    async def tags(cls, project_id, payload, user, session=None):
        permission = {'requirement': 'requirement.update', 'test_case': 'testcase.bulk.update'}[payload.artifact_type]
        await get_project(project_id, user, permission)
        idempotency_key = operation_key(payload)
        replay = await cls.replay(project_id, idempotency_key, 'BULK_TAGS', payload, user)
        if replay:
            return replay
        add_tags = {value.strip() for value in payload.add_tags if value.strip()}
        remove_tags = {value.strip() for value in payload.remove_tags if value.strip()}
        if not add_tags and not remove_tags:
            raise HTTPException(
                status_code=422, detail={"code": 'EMPTY_BULK_OPERATION'}
            )
        if any(len(value) > 100 for value in add_tags | remove_tags):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_TAG'})
        succeeded = []
        failed = []
        results = []
        for artifact_id in dict.fromkeys(payload.ids):
            artifact = await bulk_operation_repository.find_artifact(
                payload.artifact_type, artifact_id, project_id
            )
            if not artifact:
                failed.append({"id": artifact_id, "code": 'ENTITY_NOT_FOUND'})
                results.append(
                    item_result(
                        artifact_id, 'FAILED', 'ENTITY_NOT_FOUND'
                    )
                )
                continue
            tags = (set(artifact.get("tags", [])) | add_tags) - remove_tags
            if payload.preview:
                succeeded.append(artifact_id)
                results.append(item_result(artifact_id, 'PREVIEW', before_tags=sorted(artifact.get("tags", [])), after_tags=sorted(tags)))
                continue
            result = await bulk_operation_repository.update_artifact_tags(
                payload.artifact_type, artifact_id, project_id, sorted(tags), now(), session
            )
            if result.matched_count:
                succeeded.append(artifact_id)
                results.append(item_result(artifact_id, 'SUCCEEDED', tags=sorted(tags)))
            else:
                failed.append({"id": artifact_id, "code": 'REVISION_CONFLICT'})
                results.append(item_result(artifact_id, 'FAILED', 'REVISION_CONFLICT'))
        return await cls.finish(
            project_id,
            'BULK_TAGS',
            succeeded,
            failed,
            user,
            idempotency_key=idempotency_key,
            request_payload=payload,
            preview=payload.preview,
            results=results,
            details={"artifact_type": payload.artifact_type, "add_tags": sorted(add_tags), "remove_tags": sorted(remove_tags)},
            session=session,
        )

    @classmethod
    @_transactional_bulk('BULK_ADD_TO_SUITE')
    async def add_to_suite(cls, project_id, payload, user, session=None):
        await get_project(project_id, user, 'testcase.bulk.update')
        idempotency_key = operation_key(payload)
        replay = await cls.replay(project_id, idempotency_key, 'BULK_ADD_TO_SUITE', payload, user)
        if replay:
            return replay
        suite = await bulk_operation_repository.find_suite(payload.suite_id, project_id)
        if not suite:
            raise HTTPException(
                status_code=404, detail={"code": 'ENTITY_NOT_FOUND'}
            )
        if suite.get("revision", 1) != payload.expected_revision:
            raise HTTPException(
                status_code=409, detail={"code": 'REVISION_CONFLICT'}
            )
        succeeded = []
        failed = []
        results = []
        version_ids = set(suite.get("test_case_version_ids", []))
        for test_case_id in dict.fromkeys(payload.test_case_ids):
            test_case = await bulk_operation_repository.find_current_case(
                test_case_id, project_id, 'OBSOLETE'
            )
            if not test_case or not test_case.get("current_version_id"):
                failed.append({"id": test_case_id, "code": 'ENTITY_NOT_FOUND'})
                results.append(item_result(test_case_id, 'FAILED', 'ENTITY_NOT_FOUND'))
                continue
            version_ids.add(test_case["current_version_id"])
            succeeded.append(test_case_id)
            results.append(item_result(test_case_id, 'PREVIEW' if payload.preview else 'SUCCEEDED', version_id=test_case["current_version_id"]))
        if not payload.preview:
            updated = await bulk_operation_repository.update_suite_versions(
                payload.suite_id,
                project_id,
                payload.expected_revision,
                sorted(version_ids),
                now(),
                session,
            )
            if not updated:
                raise HTTPException(
                    status_code=409, detail={"code": 'REVISION_CONFLICT'}
                )
        return await cls.finish(
            project_id,
            'BULK_ADD_TO_SUITE',
            succeeded,
            failed,
            user,
            idempotency_key=idempotency_key,
            request_payload=payload,
            preview=payload.preview,
            results=results,
            details={"suite_id": payload.suite_id, "resulting_version_ids": sorted(version_ids)},
            session=session,
        )

    @classmethod
    @_transactional_bulk('BULK_MARK_REVIEW_REQUIRED')
    async def mark_review_required(cls, project_id, payload, user, session=None):
        await get_project(project_id, user, 'testcase.bulk.update')
        idempotency_key = operation_key(payload)
        replay = await cls.replay(project_id, idempotency_key, 'BULK_MARK_REVIEW_REQUIRED', payload, user)
        if replay:
            return replay
        succeeded = []
        failed = []
        results = []
        for test_case_id in dict.fromkeys(payload.test_case_ids):
            test_case = await bulk_operation_repository.find_current_case(
                test_case_id, project_id, 'OBSOLETE'
            )
            result = (
                None
                if payload.preview
                else await bulk_operation_repository.mark_case_review_required(
                    test_case_id,
                    project_id,
                    'OBSOLETE',
                    'NEEDS_UPDATE',
                    payload.reason,
                    user.id,
                    now(),
                    session,
                )
            )
            if (payload.preview and test_case) or (result and result.matched_count):
                succeeded.append(test_case_id)
                results.append(item_result(test_case_id, 'PREVIEW' if payload.preview else 'SUCCEEDED'))
            else:
                failed.append({"id": test_case_id, "code": 'ENTITY_NOT_FOUND'})
                results.append(item_result(test_case_id, 'FAILED', 'ENTITY_NOT_FOUND'))
        return await cls.finish(
            project_id,
            'BULK_MARK_REVIEW_REQUIRED',
            succeeded,
            failed,
            user,
            idempotency_key=idempotency_key,
            request_payload=payload,
            preview=payload.preview,
            results=results,
            details={"reason": payload.reason},
            session=session,
        )

    @classmethod
    @_transactional_bulk('BULK_ARCHIVE')
    async def archive(cls, project_id, payload, user, session=None):
        permission = {'requirement': 'requirement.archive', 'test_case': 'testcase.bulk.archive'}[payload.artifact_type]
        await get_project(project_id, user, permission)
        idempotency_key = operation_key(payload)
        replay = await cls.replay(project_id, idempotency_key, 'BULK_ARCHIVE', payload, user)
        if replay:
            return replay
        succeeded = []
        failed = []
        results = []
        for artifact_id in dict.fromkeys(payload.ids):
            artifact = await bulk_operation_repository.find_artifact(
                payload.artifact_type, artifact_id, project_id
            )
            if not artifact:
                failed.append({"id": artifact_id, "code": 'ENTITY_NOT_FOUND'})
                results.append(item_result(artifact_id, 'FAILED', 'ENTITY_NOT_FOUND'))
                continue
            if artifact.get("status") == 'OBSOLETE':
                failed.append({"id": artifact_id, "code": 'ALREADY_ARCHIVED'})
                results.append(item_result(artifact_id, 'FAILED', 'ALREADY_ARCHIVED'))
                continue
            if payload.artifact_type == 'test_case':
                active_run = await bulk_operation_repository.find_active_run(
                    project_id,
                    ['DRAFT', 'READY', 'IN_PROGRESS'],
                    artifact.get("current_version_id"),
                )
                if active_run:
                    failed.append({"id": artifact_id, "code": 'ACTIVE_RUN_LINK'})
                    results.append(item_result(artifact_id, 'FAILED', 'ACTIVE_RUN_LINK'))
                    continue
            if payload.preview:
                succeeded.append(artifact_id)
                results.append(item_result(artifact_id, 'PREVIEW', current_status=artifact.get("status", 'ACTIVE'), target_status='OBSOLETE'))
                continue
            result = await bulk_operation_repository.archive_artifact(
                payload.artifact_type,
                artifact_id,
                project_id,
                artifact.get("current_version_id"),
                'OBSOLETE',
                payload.reason,
                user.id,
                now(),
                session,
            )
            if result.matched_count:
                succeeded.append(artifact_id)
                results.append(item_result(artifact_id, 'SUCCEEDED', target_status='OBSOLETE'))
            else:
                failed.append({"id": artifact_id, "code": 'REVISION_CONFLICT'})
                results.append(item_result(artifact_id, 'FAILED', 'REVISION_CONFLICT'))
        return await cls.finish(
            project_id,
            'BULK_ARCHIVE',
            succeeded,
            failed,
            user,
            idempotency_key=idempotency_key,
            request_payload=payload,
            preview=payload.preview,
            results=results,
            details={"artifact_type": payload.artifact_type, "reason": payload.reason},
            session=session,
        )

    @classmethod
    async def generate_proposals(cls, project_id, payload, user):
        await get_project(project_id, user, 'proposal.bulk.generate')
        idempotency_key = operation_key(payload)
        replay = await cls.replay(project_id, idempotency_key, 'BULK_GENERATE_PROPOSALS', payload, user)
        if replay:
            return replay
        succeeded = []
        failed = []
        results = []
        for analysis_id in dict.fromkeys(payload.impact_analysis_ids):
            analysis = await bulk_operation_repository.find_impact_analysis(
                analysis_id, project_id
            )
            if not analysis:
                failed.append({"id": analysis_id, "code": 'ENTITY_NOT_FOUND'})
                results.append(item_result(analysis_id, 'FAILED', 'ENTITY_NOT_FOUND'))
                continue
            if payload.preview:
                succeeded.append(analysis_id)
                results.append(item_result(
                    analysis_id,
                    'PREVIEW',
                    analysis_status=analysis.get("status"),
                    proposal_count=await bulk_operation_repository.count_proposals(analysis_id),
                ))
                continue
            try:
                await create_maintenance_proposal_records(analysis_id, user)
                succeeded.append(analysis_id)
                results.append(item_result(analysis_id, 'SUCCEEDED'))
            except HTTPException as error:
                detail = error.detail if isinstance(error.detail, dict) else {}
                code = detail.get("code", 'REQUEST_FAILED')
                failed.append({"id": analysis_id, "code": code})
                results.append(item_result(analysis_id, 'FAILED', code))
        return await cls.finish(
            project_id,
            'BULK_GENERATE_PROPOSALS',
            succeeded,
            failed,
            user,
            idempotency_key=idempotency_key,
            request_payload=payload,
            preview=payload.preview,
            results=results,
        )

    @classmethod
    async def approve_proposals(cls, project_id, payload, user):
        project = await get_project(project_id, user, 'proposal.bulk.approve')
        idempotency_key = operation_key(payload)
        replay = await cls.replay(project_id, idempotency_key, 'BULK_APPROVE_PROPOSALS', payload, user)
        if replay:
            return replay
        threshold = float(
            resolve_project_settings(project.get("settings"))[
                "impact_confidence_threshold"
            ]
        )
        succeeded = []
        failed = []
        results = []
        for proposal_id in dict.fromkeys(payload.proposal_ids):
            proposal = await bulk_operation_repository.find_proposal(proposal_id, project_id)
            code = None
            if not proposal:
                code = 'ENTITY_NOT_FOUND'
            elif proposal.get("status") in {"ACCEPTED", "EDITED_ACCEPTED"} and proposal.get(
                "applied_artifact_id"
            ):
                succeeded.append(proposal_id)
                results.append(
                    item_result(
                        proposal_id,
                        'SUCCEEDED',
                        target_artifact_id=proposal.get("target_artifact_id"),
                    )
                )
                continue
            elif proposal.get("status") != 'PENDING':
                code = 'INVALID_STATE_TRANSITION'
            elif not proposal.get("last_reviewed_by"):
                code = 'PROPOSAL_REVIEW_REQUIRED'
            elif float(proposal.get("confidence", 0)) < threshold:
                code = 'POLICY_THRESHOLD_NOT_MET'
            elif not await cls.fresh_proposal(proposal):
                code = 'STALE_PROPOSAL'
            if code:
                failed.append({"id": proposal_id, "code": code})
                details = {"target_artifact_id": (proposal or {}).get("target_artifact_id")}
                if code == 'POLICY_THRESHOLD_NOT_MET':
                    details.update({"confidence": proposal.get("confidence", 0), "threshold": threshold})
                if code == 'STALE_PROPOSAL':
                    details["base_version_id"] = proposal.get("base_version_id")
                results.append(item_result(proposal_id, 'FAILED', code, **details))
                continue
            if payload.preview:
                succeeded.append(proposal_id)
                results.append(item_result(proposal_id, 'PREVIEW', target_artifact_id=proposal.get("target_artifact_id"), base_version_id=proposal.get("base_version_id")))
                continue
            try:
                await apply_maintenance_proposal(
                    proposal_id,
                    ProposalAction(expected_revision=proposal["revision"], review_note=payload.review_note),
                    user,
                    'ACCEPTED',
                )
                succeeded.append(proposal_id)
                results.append(item_result(proposal_id, 'SUCCEEDED', target_artifact_id=proposal.get("target_artifact_id")))
            except HTTPException as error:
                detail = error.detail if isinstance(error.detail, dict) else {}
                code = detail.get("code", 'REQUEST_FAILED')
                failed.append({"id": proposal_id, "code": code})
                results.append(item_result(proposal_id, 'FAILED', code, target_artifact_id=proposal.get("target_artifact_id")))
        return await cls.finish(
            project_id,
            'BULK_APPROVE_PROPOSALS',
            succeeded,
            failed,
            user,
            idempotency_key=idempotency_key,
            request_payload=payload,
            preview=payload.preview,
            results=results,
            details={"review_note": payload.review_note, "confidence_threshold": threshold},
        )
