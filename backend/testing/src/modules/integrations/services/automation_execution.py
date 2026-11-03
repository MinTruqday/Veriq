import hashlib
import hmac
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.worker import WorkerClientError, worker_client
from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.core.configuration import settings
from src.core.database import database
from src.repositories.execution_asset import execution_asset_repository
from src.core.sensitive_data import redact_sensitive_data


def _create_request_hash(payload):
    request = payload.model_dump(mode="json", exclude={"idempotency_key"})
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_create_replay(existing, payload, user):
    if not existing.get("created_by"):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if existing["created_by"] != user.id:
        raise HTTPException(status_code=403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _create_request_hash(payload):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})





def public_execution(value, evidence=False):
    excluded = {"runner_payload", "context_signature"}
    if not evidence:
        excluded |= {"results", "logs", "artifact_refs"}
    return redact_sensitive_data({key: item for key, item in value.items() if key not in excluded})


class AutomationExecutionService:
    @staticmethod
    async def list(project_id, user):
        await get_project(project_id, user, 'automation.read')
        items = await execution_asset_repository.list_executions(project_id)
        return [public_execution(item) for item in items]

    @staticmethod
    async def get(execution_id, user, evidence=False):
        value = await get_project_entity(
            'automation_executions',
            execution_id,
            user,
            'automation.read',
        )
        return public_execution(value, evidence=evidence)

    @staticmethod
    async def create(project_id, payload, user):
        await get_project(project_id, user, 'automation.create')
        existing = await execution_asset_repository.find_execution_by_idempotency_key(
            project_id, payload.idempotency_key
        )
        if existing:
            _verify_create_replay(existing, payload, user)
            return public_execution(existing)
        artifact = None
        script = None
        if payload.runner == 'newman':
            artifact = await execution_asset_repository.find_confirmed_postman_import(
                project_id,
                payload.postman_artifact_id,
                'postman',
                'CONFIRMED',
            )
            if not artifact or not artifact.get("raw_content"):
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'CONFIRMED_POSTMAN_COLLECTION_REQUIRED'},
                )
        else:
            script = await execution_asset_repository.find_approved_playwright_script(
                project_id,
                payload.automation_script_id,
                'playwright',
                'APPROVED',
            )
            if not script or not str(script.get("source") or "").strip():
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'APPROVED_PLAYWRIGHT_SCRIPT_REQUIRED'},
                )
        environment = None
        if payload.environment_id:
            environment = await execution_asset_repository.find_active_environment(
                project_id,
                payload.environment_id,
                'ARCHIVED',
            )
            if not environment:
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'INVALID_ENVIRONMENT'},
                )
        timestamp = now()
        value = {
            "_id": new_id('AUTOEX'),
            "project_id": project_id,
            "name": payload.name,
            "runner": payload.runner,
            "postman_artifact_id": artifact["_id"] if artifact else None,
            "automation_script_id": script["_id"] if script else None,
            "environment_id": payload.environment_id,
            "environment_snapshot": {
                "name": environment.get("name"),
                "base_url_configured": bool(environment.get("base_url")),
                "secret_reference_names": sorted((environment.get("secret_refs") or {}).keys()),
            }
            if environment
            else None,
            "runner_payload": {
                **({"collection": artifact["raw_content"]} if artifact else {}),
                **(
                    {"source": script["source"], "filename": script["filename"], "language": script["language"]}
                    if script
                    else {}
                ),
                "environment": {
                    key: environment.get("base_url")
                    for key in ['BASE_URL', 'baseUrl']
                }
                if environment and environment.get("base_url")
                else {},
            },
            "status": 'CREATED',
            "summary": {},
            "results": [],
            "logs": [],
            "artifact_refs": [],
            "idempotency_key": payload.idempotency_key,
            "idempotency_request_hash": _create_request_hash(payload),
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    await execution_asset_repository.insert_execution(value, session=session)
                    await audit(
                        user.id,
                        'automation_execution_created',
                        'AutomationExecution',
                        value["_id"],
                        project_id,
                        {
                            "postman_artifact_id": artifact["_id"] if artifact else None,
                            "automation_script_id": script["_id"] if script else None,
                            "runner": payload.runner,
                        },
                        session=session,
                    )
        except DuplicateKeyError:
            existing = await execution_asset_repository.find_execution_by_idempotency_key(
                project_id, payload.idempotency_key
            )
            if existing:
                _verify_create_replay(existing, payload, user)
                return public_execution(existing)
            raise
        return public_execution(value)

    @staticmethod
    async def start(execution_id, payload, user):
        execution = await get_project_entity(
            'automation_executions',
            execution_id,
            user,
            'automation.execute',
        )
        if execution.get("status") == 'QUEUED' and execution.get(
            "start_idempotency_key"
        ) == payload.idempotency_key:
            return public_execution(execution), execution.get("operation_id")
        if execution.get("status") != 'CREATED' or execution.get(
            "revision"
        ) != payload.expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": 'AUTOMATION_STATE_CONFLICT'},
            )
        runner = execution.get("runner")
        if runner not in set(['newman', 'playwright']):
            raise HTTPException(
                status_code=422,
                detail={"code": 'UNSUPPORTED_AUTOMATION_RUNNER'},
            )
        request = {
            "event": f"automation.{runner}.requested",
            "project_id": execution["project_id"],
            "artifact_version_id": execution_id,
            "model_version": runner,
            "requester_id": user.id,
            "requester_email": user.email,
            "payload": {"execution_id": execution_id, **execution["runner_payload"]},
        }
        idempotency_value = ":".join(
            [request["project_id"], request["artifact_version_id"], request["event"], request["model_version"]]
        )
        operation_id = f"qa-{hashlib.sha256(idempotency_value.encode()).hexdigest()[:40]}"
        timestamp = now()
        updated = await execution_asset_repository.transition_execution(
            execution_id,
            payload.expected_revision,
            'CREATED',
            {
                "status": 'QUEUED',
                "operation_id": operation_id,
                "start_idempotency_key": payload.idempotency_key,
                "queued_at": timestamp,
                "updated_at": timestamp,
            },
        )
        if not updated:
            raise HTTPException(
                status_code=409,
                detail={"code": 'AUTOMATION_STATE_CONFLICT'},
            )
        try:
            job = await worker_client.enqueue(request)
            if job.get("job_id") != operation_id:
                raise WorkerClientError()
        except WorkerClientError as error:
            await execution_asset_repository.rollback_queued_execution(
                execution_id,
                payload.expected_revision,
                operation_id,
                'QUEUED',
                'CREATED',
                now(),
            )
            raise HTTPException(
                status_code=503,
                detail={"code": 'WORKER_UNAVAILABLE'},
            ) from error
        await audit(
            user.id,
            'automation_execution_queued',
            'AutomationExecution',
            execution_id,
            execution["project_id"],
            {"operation_id": operation_id},
        )
        return public_execution(updated), operation_id

    @staticmethod
    async def cancel(execution_id, payload, user):
        execution = await get_project_entity(
            'automation_executions',
            execution_id,
            user,
            'automation.execute',
        )
        if execution.get("status") == 'CANCELLED':
            return public_execution(execution)
        if execution.get("status") != 'QUEUED' or execution.get(
            "revision"
        ) != payload.expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": 'AUTOMATION_NOT_CANCELLABLE'},
            )
        try:
            await worker_client.cancel(execution["operation_id"])
        except WorkerClientError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": 'WORKER_UNAVAILABLE'},
            ) from error
        timestamp = now()
        updated = await execution_asset_repository.transition_execution(
            execution_id,
            payload.expected_revision,
            'QUEUED',
            {
                "status": 'CANCELLED',
                "cancelled_by": user.id,
                "cancelled_at": timestamp,
                "updated_at": timestamp,
            },
        )
        await audit(
            user.id,
            'automation_execution_cancelled',
            'AutomationExecution',
            execution_id,
            execution["project_id"],
        )
        return public_execution(updated)

    @staticmethod
    async def ingest_result(payload, internal_token):
        if not hmac.compare_digest(internal_token, settings.SECRET_KEY):
            raise HTTPException(
                status_code=403,
                detail={"code": 'INVALID_INTERNAL_TOKEN'},
            )
        signature_value = f"{payload.execution_id}:{payload.operation_id}:{payload.status}"
        expected = hmac.new(settings.SECRET_KEY.encode(), signature_value.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, payload.context_signature):
            raise HTTPException(
                status_code=403,
                detail={"code": 'INVALID_JOB_CONTEXT_SIGNATURE'},
            )
        execution = await execution_asset_repository.find_execution_operation(
            payload.execution_id, payload.operation_id
        )
        if not execution:
            raise HTTPException(
                status_code=404,
                detail={"code": 'AUTOMATION_EXECUTION_NOT_FOUND'},
            )
        if execution.get("status") in set(
            ['COMPLETED', 'FAILED', 'CANCELLED']
        ):
            return public_execution(execution, evidence=True)
        timestamp = now()
        updated = await execution_asset_repository.ingest_execution_result(
            payload.execution_id,
            payload.operation_id,
            ['QUEUED', 'RUNNING'],
            {
                "status": payload.status,
                "summary": redact_sensitive_data(payload.summary),
                "results": redact_sensitive_data(payload.results),
                "logs": redact_sensitive_data(payload.logs),
                "artifact_refs": payload.artifact_refs,
                "completed_at": timestamp,
                "updated_at": timestamp,
            },
        )
        if not updated:
            raise HTTPException(
                status_code=409,
                detail={"code": 'AUTOMATION_STATE_CONFLICT'},
            )
        await audit(
            'service:worker',
            'automation_result_ingested',
            'AutomationExecution',
            payload.execution_id,
            updated["project_id"],
            {"operation_id": payload.operation_id, "status": payload.status},
        )
        return public_execution(updated, evidence=True)
