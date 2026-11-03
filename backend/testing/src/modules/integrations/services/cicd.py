import hashlib
import hmac
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.core.configuration import settings
from src.core.database import database
from src.repositories.cicd import cicd_repository
from src.core.sensitive_data import redact_sensitive_data


def _request_fingerprint(payload, excluded):
    request = payload.model_dump(mode="json", exclude=set(excluded))
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_trigger_replay(existing, payload):
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _request_fingerprint(payload, {"idempotency_key", "context_signature"}):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})


def _verify_retry_replay(existing, run_id, payload, user):
    requested_by = existing.get("requested_by")
    if not requested_by:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if requested_by != user.id:
        raise HTTPException(status_code=403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _request_fingerprint(payload, {"idempotency_key"}) or existing.get("pipeline_run_id") != run_id:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})


def verify_signature(value, signature):
    
    expected = hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=403, detail={"code": 'INVALID_JOB_CONTEXT_SIGNATURE'}
        )


def require_internal_token(value):
    
    if not hmac.compare_digest(value, settings.SECRET_KEY):
        raise HTTPException(
            status_code=403, detail={"code": 'INVALID_INTERNAL_TOKEN'}
        )


def public_binding(value):
    
    result = dict(value)
    result["pipeline_reference"] = 'Đã cấu hình'
    return result


class CiCdService:
    @staticmethod
    async def list_state(project_id, user):
        
        await get_project(project_id, user, 'cicd.read')
        bindings = await cicd_repository.list_bindings(project_id, 500)
        runs = await cicd_repository.list_runs(project_id, 1000)
        reconciliations = await cicd_repository.list_reconciliations(
            project_id, 1000
        )
        return {
            "bindings": [public_binding(item) for item in bindings],
            "runs": redact_sensitive_data(runs),
            "reconciliations": reconciliations,
        }

    @staticmethod
    async def create_binding(project_id, payload, user):
        
        await get_project(project_id, user, 'cicd.manage')
        connector = await cicd_repository.find_active_connector(
            payload.connector_id, project_id, 'BOUND'
        )
        if not connector:
            raise HTTPException(
                status_code=422, detail={"code": 'ACTIVE_CONNECTOR_REQUIRED'}
            )
        if payload.postman_artifact_id:
            artifact = await cicd_repository.find_api_artifact(
                payload.postman_artifact_id,
                project_id,
                'postman',
                'CONFIRMED',
            )
            if not artifact:
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'CONFIRMED_POSTMAN_COLLECTION_REQUIRED'},
                )
        timestamp = now()
        value = {
            "_id": new_id('CIBIND'),
            "project_id": project_id,
            **payload.model_dump(),
            "enabled": True,
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await cicd_repository.insert_binding(value)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409, detail={"code": 'PIPELINE_ALREADY_BOUND'}
            )
        await audit(
            user.id,
            'cicd_binding_created',
            'CiCdBinding',
            value["_id"],
            project_id,
            {"connector_id": payload.connector_id},
        )
        return public_binding(value)

    @staticmethod
    async def update_binding(project_id, binding_id, payload, user):
        
        binding = await get_project_entity(
            "cicd_bindings", binding_id, user, 'cicd.manage'
        )
        if binding["project_id"] != project_id:
            raise HTTPException(
                status_code=422, detail={"code": 'PROJECT_MISMATCH'}
            )
        changes = payload.model_dump(exclude_unset=True)
        changes.pop("expected_revision", None)
        updated = await cicd_repository.update_binding(
            binding_id,
            project_id,
            payload.expected_revision,
            {**changes, "updated_at": now()},
        )
        if not updated:
            raise HTTPException(
                status_code=409, detail={"code": 'REVISION_CONFLICT'}
            )
        await audit(
            user.id,
            'cicd_binding_updated',
            'CiCdBinding',
            binding_id,
            project_id,
        )
        return public_binding(updated)

    @staticmethod
    async def trigger(payload, internal_token):
        
        require_internal_token(internal_token)
        verify_signature(
            f"{payload.project_id}:{payload.binding_id}:{payload.external_run_id}:{payload.idempotency_key}",
            payload.context_signature,
        )
        existing = await cicd_repository.find_run_by_idempotency(
            payload.project_id, payload.idempotency_key
        )
        if existing:
            _verify_trigger_replay(existing, payload)
            return existing
        binding = await cicd_repository.find_active_binding(
            payload.binding_id, payload.project_id
        )
        if not binding:
            raise HTTPException(
                status_code=422,
                detail={"code": 'ACTIVE_PIPELINE_BINDING_REQUIRED'},
            )
        timestamp = now()
        automation = {
            "_id": new_id('AUTOEX'),
            "project_id": payload.project_id,
            "name": 'CI {binding_name} {external_run_id}'.format(
                binding_name=binding["name"], external_run_id=payload.external_run_id
            ),
            "runner": 'external_ci',
            "postman_artifact_id": binding.get("postman_artifact_id"),
            "release_id": binding.get("release_id"),
            "test_case_version_ids": binding.get("test_case_version_ids", []),
            "status": 'RUNNING',
            "summary": {},
            "results": [],
            "logs": [],
            "artifact_refs": [],
            "idempotency_key": f"{'ci'}:{payload.idempotency_key}",
            "revision": 1,
            "created_by": 'service:cicd',
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        run = {
            "_id": new_id('PIPERUN'),
            "project_id": payload.project_id,
            "binding_id": payload.binding_id,
            "automation_execution_id": automation["_id"],
            "external_run_id": payload.external_run_id,
            "commit_reference": payload.commit_reference,
            "status": 'RUNNING',
            "attempt": 1,
            "idempotency_key": payload.idempotency_key,
            "idempotency_request_hash": _request_fingerprint(
                payload, {"idempotency_key", "context_signature"}
            ),
            "requested_by": "service:cicd",
            "revision": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    await cicd_repository.insert_execution(automation, session=session)
                    await cicd_repository.insert_run(run, session=session)
                    await audit(
                        'service:cicd',
                        'cicd_run_triggered',
                        'PipelineRun',
                        run["_id"],
                        payload.project_id,
                        {"external_run_id": payload.external_run_id},
                        session=session,
                    )
        except DuplicateKeyError:
            existing = await cicd_repository.find_run_by_idempotency(
                payload.project_id, payload.idempotency_key
            )
            if existing:
                _verify_trigger_replay(existing, payload)
                return existing
            raise
        return run

    @staticmethod
    async def ingest_result(payload, internal_token):
        
        require_internal_token(internal_token)
        verify_signature(
            f"{payload.project_id}:{payload.pipeline_run_id}:{payload.status}",
            payload.context_signature,
        )
        run = await cicd_repository.find_run(
            payload.pipeline_run_id, payload.project_id
        )
        if not run:
            raise HTTPException(
                status_code=404, detail={"code": 'PIPELINE_RUN_NOT_FOUND'}
            )
        if run.get("status") in ['COMPLETED', 'FAILED', 'CANCELLED']:
            return run
        timestamp = now()
        run_changes = {
            "status": payload.status,
            "summary": redact_sensitive_data(payload.summary),
            "logs": redact_sensitive_data(payload.logs),
            "completed_at": timestamp,
            "updated_at": timestamp,
        }
        updated = await cicd_repository.complete_run(
            payload.pipeline_run_id,
            payload.project_id,
            'RUNNING',
            run_changes,
        )
        if not updated:
            updated = await cicd_repository.find_run(
                payload.pipeline_run_id, payload.project_id
            )
        execution_changes = {
            "status": payload.status,
            "summary": redact_sensitive_data(payload.summary),
            "results": redact_sensitive_data(payload.results),
            "logs": redact_sensitive_data(payload.logs),
            "completed_at": timestamp,
            "updated_at": timestamp,
        }
        await cicd_repository.complete_execution(
            run["automation_execution_id"],
            payload.project_id,
            'RUNNING',
            execution_changes,
        )
        await audit(
            'service:cicd',
            'cicd_result_ingested',
            'PipelineRun',
            run["_id"],
            payload.project_id,
            {"status": payload.status},
        )
        return updated

    @staticmethod
    async def retry(project_id, run_id, payload, user):
        
        run = await get_project_entity(
            "pipeline_runs", run_id, user, 'cicd.retry'
        )
        if run["project_id"] != project_id:
            raise HTTPException(
                status_code=422, detail={"code": 'PROJECT_MISMATCH'}
            )
        existing = await cicd_repository.find_reconciliation(
            project_id, payload.idempotency_key
        )
        if existing:
            _verify_retry_replay(existing, run_id, payload, user)
            return existing
        if (
            run.get("status") != 'FAILED'
            or run.get("revision") != payload.expected_revision
        ):
            raise HTTPException(
                status_code=409, detail={"code": 'PIPELINE_RUN_NOT_RETRYABLE'}
            )
        timestamp = now()
        value = {
            "_id": new_id('CIREC'),
            "project_id": project_id,
            "pipeline_run_id": run_id,
            "binding_id": run["binding_id"],
            "status": 'QUEUED',
            "reason": payload.reason,
            "idempotency_key": payload.idempotency_key,
            "idempotency_request_hash": _request_fingerprint(payload, {"idempotency_key"}),
            "requested_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    await cicd_repository.insert_reconciliation(value, session=session)
                    await audit(
                        user.id,
                        'cicd_reconciliation_queued',
                        'PipelineRun',
                        run_id,
                        project_id,
                        {"operation_id": value["_id"], "reason": payload.reason},
                        session=session,
                    )
        except DuplicateKeyError:
            existing = await cicd_repository.find_reconciliation(
                project_id, payload.idempotency_key
            )
            if existing:
                _verify_retry_replay(existing, run_id, payload, user)
                return existing
            raise
        return value
