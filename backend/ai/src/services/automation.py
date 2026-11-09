import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone

import httpx
import jwt
from fastapi import HTTPException
from loguru import logger
from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.mq import mq
from src.repositories.automation import automation_repository
from src.runtime.limits import limits
from src.runtime.queue_names import AUTOMATION_QUEUE
from src.schemas.automation import (
    AutomationCheckpointPhase,
    AutomationClarificationResponseRequest,
    AutomationEventRequest,
    AutomationKind,
    AutomationRun,
    AutomationStatus,
    AutomationTrigger,
    EvidenceItem,
)
from src.services.project_access import project_access
from src.tools.registry import registered_tools, requires_human_decision, tool_access


async def publish_automation_run(automation_run_id: str) -> bool:
    try:
        return bool(
            await mq.publish(
                AUTOMATION_QUEUE, {"automation_run_id": automation_run_id}
            )
        )
    except Exception:
        logger.exception("AI automation run could not be queued")
        return False


class AutomationService:
    async def create_user_run(self, payload, user_id: str, role: str, permissions: list[str]):
        if payload.evidence:
            raise HTTPException(
                status_code=422, detail={"code": "AGENT_EVIDENCE_MUST_BE_RETRIEVED"}
            )
        available = []
        for tool in registered_tools().values():
            access = tool_access(tool)
            if (
                access
                and access.permission in permissions
                and not requires_human_decision(access.permission)
                and (access.action != "MUTATE" or access.draft_only)
                and tool.metadata.get("user_selectable")
            ):
                available.append(access.name)
        if not available:
            raise HTTPException(status_code=403, detail={"code": "AGENT_REQUEST_DENIED"})
        if payload.intent:
            tool = registered_tools().get(payload.intent)
            access = tool_access(tool)
            if (
                not access
                or payload.intent not in available
                or not tool.metadata.get("user_selectable")
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
        event_id = "agent-request:" + hashlib.sha256(
            f"{user_id}:{payload.idempotency_key}".encode("utf-8")
        ).hexdigest()
        existing = await automation_repository.find_event_run(payload.project_id, event_id)
        if existing:
            if (
                existing.requester_user_id != user_id
                or (existing.constraints or {}).get("request_fingerprint") != fingerprint
            ):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            return existing
        run = AutomationRun(
            project_id=payload.project_id,
            requester_user_id=user_id,
            requester_role=role,
            requester_permissions=permissions,
            execution_user_id=user_id,
            execution_role=role,
            execution_permissions=permissions,
            kind=AutomationKind.ON_DEMAND,
            trigger=AutomationTrigger.MANUAL,
            source_event_id=event_id,
            source_event_verified=False,
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
            run = await automation_repository.create_run_with_checkpoint(
                run,
                phase=AutomationCheckpointPhase.QUEUED,
                detail={"reason_code": "USER_REQUESTED"},
            )
        except DuplicateKeyError:
            existing = await automation_repository.find_event_run(payload.project_id, event_id)
            if (
                not existing
                or existing.requester_user_id != user_id
                or (existing.constraints or {}).get("request_fingerprint") != fingerprint
            ):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            return existing
        if await publish_automation_run(run.automation_run_id):
            return run
        degraded = await automation_repository.transition_with_checkpoint(
            run.automation_run_id,
            run.revision,
            {"status": AutomationStatus.DEGRADED, "error_code": "AGENT_QUEUE_UNAVAILABLE"},
            phase=AutomationCheckpointPhase.FINALIZED,
            detail={"reason_code": "AGENT_QUEUE_UNAVAILABLE", "retryable": True},
        )
        return degraded or run

    async def enqueue_event(self, event: AutomationEventRequest) -> list[AutomationRun]:
        return []

    async def authorize_retry(self, run: AutomationRun, expected_revision: int) -> AutomationRun:
        if not (run.constraints or {}).get("user_requested"):
            raise HTTPException(status_code=409, detail={"code": "AGENT_REQUEST_REQUIRED"})
        if run.revision != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")},
            )
        if run.error_code == "AUTOMATION_ACTION_OUTCOME_UNCERTAIN":
            raise HTTPException(
                status_code=409, detail={"code": "AUTOMATION_RETRY_REQUIRES_RECONCILIATION"}
            )
        if run.status not in {
            AutomationStatus.AWAITING_AUTHORIZATION,
            AutomationStatus.FAILED,
            AutomationStatus.DEGRADED,
        }:
            raise HTTPException(status_code=409, detail={"code": "AUTOMATION_RETRY_NOT_ALLOWED"})
        latest_checkpoint = await automation_repository.latest_checkpoint(run.automation_run_id)
        resume_snapshot = None
        if latest_checkpoint:
            action_outcome_uncertain = (
                latest_checkpoint.phase == AutomationCheckpointPhase.ACTION_STARTED
                and (
                    latest_checkpoint.detail.get("action") != "READ"
                    or latest_checkpoint.detail.get("task_has_mutation") is True
                )
            )
            if action_outcome_uncertain:
                raise HTTPException(
                    status_code=409, detail={"code": "AUTOMATION_RETRY_REQUIRES_RECONCILIATION"}
                )
            resume_snapshot = latest_checkpoint.state_snapshot
        if resume_snapshot is None and (
            run.status != AutomationStatus.AWAITING_AUTHORIZATION
            and run.error_code != "AUTOMATION_QUEUE_UNAVAILABLE"
        ):
            raise HTTPException(
                status_code=409, detail={"code": "AUTOMATION_RETRY_REQUIRES_RECONCILIATION"}
            )
        retry_values = {"status": AutomationStatus.QUEUED, "error_code": None}
        if run.error_code == "AUTOMATION_EXECUTOR_UNAVAILABLE" or (
            str(run.error_code or "").startswith("PROJECT_")
            and str(run.error_code).endswith("_EXECUTOR_UNAVAILABLE")
        ):
            token = self._token_for_user(run.requester_user_id)
            role, permissions = await project_access(run.project_id, token)
            required_permission = (
                "requirement_document.extract"
                if run.trigger == AutomationTrigger.DOCUMENT_INGESTED
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
        updated = await automation_repository.transition_with_checkpoint(
            run.automation_run_id,
            expected_revision,
            retry_values,
            phase=AutomationCheckpointPhase.QUEUED,
            detail={
                "reason_code": "AUTOMATION_RESUMED_FROM_CHECKPOINT"
                if resume_snapshot
                else "AUTOMATION_RETRY_STARTED",
                "resuming_after": resume_snapshot.completed_phase.value
                if resume_snapshot
                else None,
            },
            state_snapshot=resume_snapshot,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        if not await publish_automation_run(run.automation_run_id):
            degraded = await automation_repository.transition_with_checkpoint(
                updated.automation_run_id,
                updated.revision,
                {"status": AutomationStatus.DEGRADED, "error_code": "AUTOMATION_QUEUE_UNAVAILABLE"},
                phase=AutomationCheckpointPhase.FINALIZED,
                detail={"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
                state_snapshot=resume_snapshot,
            )
            if not degraded:
                raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
            return degraded
        return updated

    async def provide_clarification(
        self,
        run: AutomationRun,
        payload: AutomationClarificationResponseRequest,
        responder_user_id: str,
    ) -> AutomationRun:
        if not (run.constraints or {}).get("user_requested"):
            raise HTTPException(status_code=409, detail={"code": "AGENT_REQUEST_REQUIRED"})
        if run.revision != payload.expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")},
            )
        if run.status != AutomationStatus.AWAITING_INPUT:
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_NOT_AWAITING_INPUT"},
            )
        checkpoint = await automation_repository.latest_checkpoint(run.automation_run_id)
        snapshot = checkpoint.state_snapshot if checkpoint else None
        if snapshot is None:
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_CLARIFICATION_CHECKPOINT_MISSING"},
            )
        matching_uncertainties = [
            item
            for item in snapshot.uncertainties
            if item.code == payload.uncertainty_code
            and item.resolution_status == "OPEN"
        ]
        if not matching_uncertainties:
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_CLARIFICATION_NOT_OPEN"},
            )
        if len(matching_uncertainties) != 1:
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_CLARIFICATION_CODE_AMBIGUOUS"},
            )
        uncertainty = matching_uncertainties[0]
        if not uncertainty.response_allowed:
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_CLARIFICATION_REQUIRES_SOURCE_OR_SYSTEM_RECOVERY"},
            )

        answered_at = datetime.now(timezone.utc)
        evidence_ref = "clarification:" + hashlib.sha256(
            f"{run.automation_run_id}:{payload.uncertainty_code}:{payload.expected_revision + 1}".encode()
        ).hexdigest()[:48]
        clarification_evidence = EvidenceItem(
            artifact_type="automation_clarification",
            artifact_id=evidence_ref,
            artifact_version_id=evidence_ref,
            source="user",
            authority="user_clarification",
            text=payload.answer,
            project_id=run.project_id,
        )
        resolved_uncertainties = [
            item.model_copy(
                update={
                    "blocking": False,
                    "resolution_status": "USER_ANSWERED",
                    "answer": payload.answer,
                    "answered_by": responder_user_id,
                    "answered_at": answered_at,
                }
            )
            if item.code == payload.uncertainty_code
            and item.resolution_status == "OPEN"
            else item
            for item in snapshot.uncertainties
        ]
        response_record = {
            "uncertainty_code": payload.uncertainty_code,
            "question": uncertainty.question,
            "reason": uncertainty.reason,
            "evidence_refs": list(uncertainty.evidence_refs),
            "answer": payload.answer,
            "answered_by": responder_user_id,
            "answered_at": answered_at.isoformat(),
            "evidence_ref": evidence_ref,
        }
        prior_responses = list(
            (run.constraints or {}).get("clarification_responses") or []
        )
        updated_constraints = {
            **(run.constraints or {}),
            "clarification_responses": [*prior_responses, response_record],
        }
        resume_after_phase = (
            AutomationCheckpointPhase.FACTS_EXTRACTED
            if snapshot.source_facts
            else AutomationCheckpointPhase.OBSERVED
        )
        resumed_snapshot = snapshot.model_copy(
            update={
                "completed_phase": resume_after_phase,
                "run": snapshot.run.model_copy(
                    update={
                        "evidence_refs": list(
                            dict.fromkeys([*snapshot.run.evidence_refs, evidence_ref])
                        )
                    }
                ),
                "evidence": [*snapshot.evidence, clarification_evidence],
                "uncertainties": resolved_uncertainties,
                "constraints": {
                    **snapshot.constraints,
                    "clarification_responses": [*prior_responses, response_record],
                },
            }
        )
        updated = await automation_repository.transition_with_checkpoint(
            run.automation_run_id,
            payload.expected_revision,
            {
                "status": AutomationStatus.QUEUED,
                "error_code": None,
                "constraints": updated_constraints,
                "evidence": [
                    item.model_dump(mode="python")
                    if hasattr(item, "model_dump")
                    else item
                    for item in [*run.evidence, clarification_evidence]
                ],
            },
            phase=AutomationCheckpointPhase.QUEUED,
            detail={
                "reason_code": "AUTOMATION_RESUMED_WITH_USER_CLARIFICATION",
                "uncertainty_code": payload.uncertainty_code,
                "responder_user_id": responder_user_id,
                "resuming_after": resume_after_phase.value,
            },
            state_snapshot=resumed_snapshot,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        if not await publish_automation_run(run.automation_run_id):
            degraded = await automation_repository.transition_with_checkpoint(
                updated.automation_run_id,
                updated.revision,
                {
                    "status": AutomationStatus.DEGRADED,
                    "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                },
                phase=AutomationCheckpointPhase.FINALIZED,
                detail={
                    "reason_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                    "retryable": True,
                    "resuming_after": resume_after_phase.value,
                },
                state_snapshot=resumed_snapshot,
            )
            if not degraded:
                raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
            return degraded
        return updated

    async def cancel(self, run: AutomationRun, expected_revision: int) -> AutomationRun:
        if run.revision != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")},
            )
        if run.status in {AutomationStatus.COMPLETED, AutomationStatus.CANCELLED}:
            raise HTTPException(status_code=409, detail={"code": "AUTOMATION_CANCEL_NOT_ALLOWED"})
        if run.status == AutomationStatus.RUNNING:
            try:
                await self._revoke_testing_run_access(run.automation_run_id)
            except (httpx.HTTPError, RuntimeError, ValueError) as error:
                raise HTTPException(
                    status_code=503,
                    detail={"code": "AUTOMATION_CANCEL_DRAIN_UNAVAILABLE", "retryable": True},
                ) from error
        current = run
        for _ in range(3):
            updated = await automation_repository.transition_with_checkpoint(
                current.automation_run_id,
                current.revision,
                {"status": AutomationStatus.CANCELLED, "worker_lease_expires_at": None},
                phase=AutomationCheckpointPhase.FINALIZED,
                detail={"reason_code": "AUTOMATION_CANCELLED"},
            )
            if updated:
                return updated
            latest = await automation_repository.get_run(current.automation_run_id)
            if not latest:
                break
            if latest.status == AutomationStatus.CANCELLED:
                return latest
            if latest.status == AutomationStatus.COMPLETED:
                raise HTTPException(
                    status_code=409, detail={"code": "AUTOMATION_CANCEL_NOT_ALLOWED"}
                )
            current = latest
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})

    async def cancel_document_ingestion_runs(self, document_id: str) -> int:
        candidates = await automation_repository.list_incomplete_document_ingestion_runs(
            document_id
        )
        await asyncio.gather(
            *(self._revoke_testing_run_access(run.automation_run_id) for run in candidates)
        )
        cancelled_count = 0
        for candidate in candidates:
            run = candidate
            for _ in range(3):
                if run.status in {AutomationStatus.COMPLETED, AutomationStatus.CANCELLED}:
                    break
                updated = await automation_repository.transition_with_checkpoint(
                    run.automation_run_id,
                    run.revision,
                    {
                        "status": AutomationStatus.CANCELLED,
                        "error_code": "AI_READ_PERMISSION_REVOKED",
                        "worker_lease_expires_at": None,
                    },
                    phase=AutomationCheckpointPhase.FINALIZED,
                    detail={"reason_code": "AI_READ_PERMISSION_REVOKED"},
                )
                if updated:
                    cancelled_count += 1
                    run = updated
                    break
                latest = await automation_repository.get_run(run.automation_run_id)
                if not latest:
                    break
                run = latest
            if run.status not in {AutomationStatus.COMPLETED, AutomationStatus.CANCELLED}:
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
            raise RuntimeError("AI_AUTOMATION_ACCESS_REVOCATION_RESPONSE_INVALID")
        payload = result.get("data", result)
        if not isinstance(payload, dict) or payload.get("drained") is not True:
            raise RuntimeError("AI_AUTOMATION_ACCESS_REVOCATION_NOT_DRAINED")

    async def token_for(
        self, automation_run_id: str, worker_revision: int | None = None
    ) -> str | None:
        run = await automation_repository.get_run(automation_run_id)
        if not run or not run.execution_user_id or not run.execution_role:
            return None
        if worker_revision is not None and (
            run.status != AutomationStatus.RUNNING or run.revision != worker_revision
        ):
            return None
        execution_user_id = run.execution_user_id
        trigger = getattr(run.trigger, "value", run.trigger)
        source_document_ids = []
        if trigger == "DOCUMENT_INGESTED":
            event_id = str(run.source_event_id or "")
            prefix = "requirement-document:"
            if event_id.startswith(prefix):
                parts = event_id[len(prefix):].split(":", 2)
                if len(parts) >= 2 and parts[0] and parts[1].isdigit():
                    document_id = parts[0]
                    source_document_ids = [document_id]
                else:
                    return None
            else:
                return None
        publication_permissions = []
        return jwt.encode(
            {
                "uid": execution_user_id,
                "sub": execution_user_id,
                "system_role": "USER",
                "ai_automation_run_id": run.automation_run_id,
                "ai_automation_worker_revision": worker_revision,
                "ai_automation_trigger": trigger,
                "ai_automation_source_event_id": run.source_event_id,
                "ai_automation_initiator_id": run.requester_user_id,
                "ai_automation_definition_id": run.definition_id,
                "ai_automation_source_document_ids": source_document_ids,
                "ai_automation_publication_project_id": run.project_id
                if publication_permissions
                else None,
                "ai_automation_publication_permissions": publication_permissions,
                "exp": int(time.time()) + limits.run_timeout_seconds,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )


automation_service = AutomationService()
