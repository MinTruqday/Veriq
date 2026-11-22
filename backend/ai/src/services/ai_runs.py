import asyncio
import hashlib
import json
import re
import time

import httpx
import jwt
from fastapi import HTTPException
from loguru import logger
from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.mq import mq
from src.repositories.ai_runs import ai_run_repository
from src.runtime.limits import limits
from src.runtime.queue_names import AI_RUN_QUEUE
from src.schemas.agent import AIRunRequest, RequirementDocumentRunRequest
from src.schemas.ai_runs import (
    AIRunPhase,
    AIRunKind,
    AIRun,
    AIRunStatus,
    AIRunTrigger,
)
from src.services.project_access import project_access
from src.tools.registry import agent_available_tools, registered_tools, tool_access


async def publish_ai_run(ai_run_id: str) -> bool:
    try:
        return bool(
            await mq.publish(
                AI_RUN_QUEUE, {"ai_run_id": ai_run_id}
            )
        )
    except Exception:
        logger.exception("AI run could not be queued")
        return False


class AIRunService:
    async def create_user_run(
        self,
        payload,
        user_id: str,
        role: str,
        permissions: list[str],
        *,
        trigger: AIRunTrigger = AIRunTrigger.MANUAL,
        source_event_id: str | None = None,
        source_event_verified: bool = False,
    ):
        if payload.evidence:
            raise HTTPException(
                status_code=422, detail={"code": "AGENT_EVIDENCE_MUST_BE_RETRIEVED"}
            )
        available = agent_available_tools(permissions)
        if not available:
            raise HTTPException(status_code=403, detail={"code": "AGENT_REQUEST_DENIED"})
        if payload.intent:
            tool = available.get(payload.intent)
            access = tool_access(tool)
            if (
                not access
            ):
                raise HTTPException(status_code=403, detail={"code": "AGENT_CAPABILITY_DENIED"})
            try:
                intent_arguments = tool.args_schema.model_validate(
                    payload.intent_arguments
                ).model_dump(mode="python", exclude_unset=True)
            except Exception as error:
                raise HTTPException(
                    status_code=422, detail={"code": "AGENT_ARGUMENT_INVALID"}
                ) from error
        elif payload.intent_arguments:
            raise HTTPException(
                status_code=422, detail={"code": "AGENT_ARGUMENTS_REQUIRE_CAPABILITY"}
            )
        else:
            intent_arguments = {}
        request_data = {
            "project_id": payload.project_id,
            "requester_user_id": user_id,
            "objective": payload.objective.strip(),
            "intent": payload.intent,
            "intent_arguments": intent_arguments,
            "target_artifact_ids": payload.target_artifact_ids,
            "evidence": [],
            "output_language": payload.output_language,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                request_data,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        event_id = source_event_id or (
            "agent-request:"
            + hashlib.sha256(
                f"{user_id}:{payload.idempotency_key}".encode("utf-8")
            ).hexdigest()
        )
        existing = await ai_run_repository.find_event_run(payload.project_id, event_id)
        if existing:
            if (
                existing.requester_user_id != user_id
                or (existing.constraints or {}).get("request_fingerprint") != fingerprint
            ):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            return existing
        run = AIRun(
            project_id=payload.project_id,
            requester_user_id=user_id,
            requester_role=role,
            requester_permissions=permissions,
            execution_user_id=user_id,
            execution_role=role,
            execution_permissions=permissions,
            kind=AIRunKind.ON_DEMAND,
            trigger=trigger,
            source_event_id=event_id,
            source_event_verified=source_event_verified,
            objective=payload.objective.strip(),
            intent=payload.intent,
            intent_arguments=intent_arguments,
            target_artifact_ids=payload.target_artifact_ids,
            evidence=[],
            constraints={
                "user_requested": True,
                "output_language": payload.output_language,
                "request_fingerprint": fingerprint,
            },
        )
        try:
            run = await ai_run_repository.create_run_with_checkpoint(
                run,
                phase=AIRunPhase.QUEUED,
                detail={"reason_code": "USER_REQUESTED"},
            )
        except DuplicateKeyError:
            existing = await ai_run_repository.find_event_run(payload.project_id, event_id)
            if (
                not existing
                or existing.requester_user_id != user_id
                or (existing.constraints or {}).get("request_fingerprint") != fingerprint
            ):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            return existing
        if await publish_ai_run(run.ai_run_id):
            return run
        degraded = await ai_run_repository.transition_with_checkpoint(
            run.ai_run_id,
            run.revision,
            {"status": AIRunStatus.DEGRADED, "error_code": "AI_RUN_QUEUE_UNAVAILABLE"},
            phase=AIRunPhase.FINALIZED,
            detail={"reason_code": "AI_RUN_QUEUE_UNAVAILABLE", "retryable": True},
        )
        return degraded or run

    async def create_requirement_document_run(
        self, payload: RequirementDocumentRunRequest
    ) -> AIRun:
        event_parts = payload.idempotency_key.split(":")
        if (
            len(event_parts) not in {3, 4}
            or event_parts[0] != "requirement-document"
            or event_parts[1] != payload.document_id
            or not event_parts[2].isdigit()
            or (
                len(event_parts) == 4
                and (
                    len(event_parts[3]) != 64
                    or re.fullmatch(r"[0-9a-f]{64}", event_parts[3]) is None
                )
            )
        ):
            raise HTTPException(
                status_code=422,
                detail={"code": "DOCUMENT_INGESTION_EVENT_INVALID"},
            )
        token = self._token_for_user(payload.requester_user_id)
        role, permissions = await project_access(payload.project_id, token)
        if "requirement_document.extract" not in permissions:
            raise HTTPException(status_code=403, detail={"code": "AGENT_REQUEST_DENIED"})
        request = AIRunRequest(
            project_id=payload.project_id,
            objective=(
                "Process this user-requested Requirement document import. Extract grounded "
                "Requirements and create only traceable draft outputs in this project."
            ),
            intent="process_ingested_requirement_document",
            intent_arguments={
                "project_id": payload.project_id,
                "document_id": payload.document_id,
                "source_hash": payload.source_hash,
            },
            target_artifact_ids=[payload.document_id],
            output_language=payload.output_language,
            idempotency_key=payload.idempotency_key,
        )
        return await self.create_user_run(
            request,
            payload.requester_user_id,
            role,
            permissions,
            trigger=AIRunTrigger.DOCUMENT_INGESTED,
            source_event_id=payload.idempotency_key,
            source_event_verified=True,
        )

    @staticmethod
    def _token_for_user(user_id: str) -> str:
        return jwt.encode(
            {
                "uid": user_id,
                "sub": user_id,
                "system_role": "USER",
                "exp": int(time.time()) + 30,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    async def authorize_retry(self, run: AIRun, expected_revision: int) -> AIRun:
        if not (run.constraints or {}).get("user_requested"):
            raise HTTPException(status_code=409, detail={"code": "AGENT_REQUEST_REQUIRED"})
        if run.revision != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")},
            )
        if run.error_code == "AI_RUN_ACTION_OUTCOME_UNCERTAIN":
            raise HTTPException(
                status_code=409, detail={"code": "AI_RUN_RETRY_REQUIRES_RECONCILIATION"}
            )
        if run.status not in {
            AIRunStatus.AWAITING_AUTHORIZATION,
            AIRunStatus.FAILED,
            AIRunStatus.DEGRADED,
        }:
            raise HTTPException(status_code=409, detail={"code": "AI_RUN_RETRY_NOT_ALLOWED"})
        latest_checkpoint = await ai_run_repository.latest_checkpoint(run.ai_run_id)
        resume_snapshot = None
        if latest_checkpoint:
            action_outcome_uncertain = (
                latest_checkpoint.phase == AIRunPhase.ACTION_STARTED
                and (
                    latest_checkpoint.detail.get("action") != "READ"
                    or latest_checkpoint.detail.get("task_has_mutation") is True
                )
            )
            if action_outcome_uncertain:
                raise HTTPException(
                    status_code=409, detail={"code": "AI_RUN_RETRY_REQUIRES_RECONCILIATION"}
                )
            resume_snapshot = latest_checkpoint.state_snapshot
        if resume_snapshot is None and (
            run.status != AIRunStatus.AWAITING_AUTHORIZATION
            and run.error_code != "AI_RUN_QUEUE_UNAVAILABLE"
        ):
            raise HTTPException(
                status_code=409, detail={"code": "AI_RUN_RETRY_REQUIRES_RECONCILIATION"}
            )
        retry_values = {"status": AIRunStatus.QUEUED, "error_code": None}
        if run.error_code == "AI_RUN_EXECUTOR_UNAVAILABLE" or (
            str(run.error_code or "").startswith("PROJECT_")
            and str(run.error_code).endswith("_EXECUTOR_UNAVAILABLE")
        ):
            token = self._token_for_user(run.requester_user_id)
            role, permissions = await project_access(run.project_id, token)
            required_permission = (
                "requirement_document.extract"
                if run.intent == "process_ingested_requirement_document"
                else "ai.generate_testcase"
            )
            if required_permission not in permissions:
                raise HTTPException(
                    status_code=403, detail={"code": "AGENT_REQUEST_DENIED"}
                )
            retry_values.update(
                {
                    "execution_user_id": run.requester_user_id,
                    "execution_role": role,
                    "execution_permissions": permissions,
                }
            )
        updated = await ai_run_repository.transition_with_checkpoint(
            run.ai_run_id,
            expected_revision,
            retry_values,
            phase=AIRunPhase.QUEUED,
            detail={
                "reason_code": "AI_RUN_RESUMED_FROM_CHECKPOINT"
                if resume_snapshot
                else "AI_RUN_RETRY_STARTED",
                "resuming_after": resume_snapshot.completed_phase.value
                if resume_snapshot
                else None,
            },
            state_snapshot=resume_snapshot,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        if not await publish_ai_run(run.ai_run_id):
            degraded = await ai_run_repository.transition_with_checkpoint(
                updated.ai_run_id,
                updated.revision,
                {"status": AIRunStatus.DEGRADED, "error_code": "AI_RUN_QUEUE_UNAVAILABLE"},
                phase=AIRunPhase.FINALIZED,
                detail={"reason_code": "AI_RUN_QUEUE_UNAVAILABLE", "retryable": True},
                state_snapshot=resume_snapshot,
            )
            if not degraded:
                raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
            return degraded
        return updated

    async def cancel(self, run: AIRun, expected_revision: int) -> AIRun:
        if run.revision != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")},
            )
        if run.status in {AIRunStatus.COMPLETED, AIRunStatus.CANCELLED}:
            raise HTTPException(status_code=409, detail={"code": "AI_RUN_CANCEL_NOT_ALLOWED"})
        if run.status == AIRunStatus.RUNNING:
            try:
                await self._revoke_testing_run_access(run.ai_run_id)
            except (httpx.HTTPError, RuntimeError, ValueError) as error:
                raise HTTPException(
                    status_code=503,
                    detail={"code": "AI_RUN_CANCEL_DRAIN_UNAVAILABLE", "retryable": True},
                ) from error
        current = run
        for _ in range(3):
            updated = await ai_run_repository.transition_with_checkpoint(
                current.ai_run_id,
                current.revision,
                {"status": AIRunStatus.CANCELLED, "worker_lease_expires_at": None},
                phase=AIRunPhase.FINALIZED,
                detail={"reason_code": "AI_RUN_CANCELLED"},
            )
            if updated:
                return updated
            latest = await ai_run_repository.get_run(current.ai_run_id)
            if not latest:
                break
            if latest.status == AIRunStatus.CANCELLED:
                return latest
            if latest.status == AIRunStatus.COMPLETED:
                raise HTTPException(
                    status_code=409, detail={"code": "AI_RUN_CANCEL_NOT_ALLOWED"}
                )
            current = latest
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})

    async def cancel_document_ingestion_runs(self, document_id: str) -> int:
        candidates = await ai_run_repository.list_incomplete_document_ingestion_runs(
            document_id
        )
        await asyncio.gather(
            *(self._revoke_testing_run_access(run.ai_run_id) for run in candidates)
        )
        cancelled_count = 0
        for candidate in candidates:
            run = candidate
            for _ in range(3):
                if run.status in {AIRunStatus.COMPLETED, AIRunStatus.CANCELLED}:
                    break
                updated = await ai_run_repository.transition_with_checkpoint(
                    run.ai_run_id,
                    run.revision,
                    {
                        "status": AIRunStatus.CANCELLED,
                        "error_code": "AI_READ_PERMISSION_REVOKED",
                        "worker_lease_expires_at": None,
                    },
                    phase=AIRunPhase.FINALIZED,
                    detail={"reason_code": "AI_READ_PERMISSION_REVOKED"},
                )
                if updated:
                    cancelled_count += 1
                    run = updated
                    break
                latest = await ai_run_repository.get_run(run.ai_run_id)
                if not latest:
                    break
                run = latest
            if run.status not in {AIRunStatus.COMPLETED, AIRunStatus.CANCELLED}:
                raise RuntimeError("DOCUMENT_INGESTION_RUN_CANCELLATION_CONFLICT")
        return cancelled_count

    async def _revoke_testing_run_access(self, run_id: str) -> None:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(
                f"{settings.INTERNAL_API_URL.rstrip('/')}/kiem-thu/noi-bo/tac-vu/"
                f"ai-luot-chay/{run_id}/thu-hoi-quyen",
                headers={"X-Internal-Token": settings.SECRET_KEY},
            )
            response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise RuntimeError("AI_RUN_ACCESS_REVOCATION_RESPONSE_INVALID")
        payload = result.get("data", result)
        if not isinstance(payload, dict) or payload.get("drained") is not True:
            raise RuntimeError("AI_RUN_ACCESS_REVOCATION_NOT_DRAINED")

    async def token_for(
        self, ai_run_id: str, worker_revision: int | None = None
    ) -> str | None:
        run = await ai_run_repository.get_run(ai_run_id)
        if not run or not run.execution_user_id or not run.execution_role:
            return None
        if worker_revision is not None and (
            run.status != AIRunStatus.RUNNING or run.revision != worker_revision
        ):
            return None
        execution_user_id = run.execution_user_id
        trigger = getattr(run.trigger, "value", run.trigger)
        source_document_ids = (
            [str(run.intent_arguments.get("document_id"))]
            if run.intent == "process_ingested_requirement_document"
            and run.intent_arguments.get("document_id")
            else []
        )
        source_document_hash = (
            str(run.intent_arguments.get("source_hash") or "")
            if source_document_ids
            else ""
        )
        publication_permissions = []
        return jwt.encode(
            {
                "uid": execution_user_id,
                "sub": execution_user_id,
                "system_role": "USER",
                "ai_capability_run_id": run.ai_run_id,
                "ai_capability_intent": run.intent,
                "ai_capability_worker_revision": worker_revision,
                "ai_capability_trigger": trigger,
                "ai_capability_source_event_id": run.source_event_id,
                "ai_capability_initiator_id": run.requester_user_id,
                "ai_capability_definition_id": run.definition_id,
                "ai_capability_source_document_ids": source_document_ids,
                "ai_capability_source_document_hash": source_document_hash,
                "ai_capability_publication_project_id": run.project_id
                if publication_permissions
                else None,
                "ai_capability_publication_permissions": publication_permissions,
                "exp": int(time.time()) + limits.run_timeout_seconds,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )


ai_run_service = AIRunService()
