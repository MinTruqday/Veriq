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
from src.prompts.automation_events import generic_event_objective
from src.repositories.automation import automation_repository
from src.runtime.queue_names import AUTOMATION_QUEUE
from src.runtime.limits import limits
from src.schemas.automation import (
    AutomationCheckpointPhase,
    AutomationClarificationResponseRequest,
    AutomationDefinition,
    AutomationDefinitionPatch,
    AutomationDefinitionRequest,
    AutomationEventRequest,
    EvidenceItem,
    AutomationKind,
    AutomationRun,
    AutomationRunRequest,
    AutomationStatus,
    AutomationTrigger,
)
from src.services.project_access import project_access
from src.tools.registry import registered_tools, tool_access
from src.tools.testing_api import AutomationOperationError, require_operation


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
    @staticmethod
    def _event_fingerprint(
        event_id,
        project_id,
        requester_user_id,
        trigger,
        parent_automation_run_id,
        target_artifact_ids,
        evidence,
    ):
        normalized = {
            "event_id": str(event_id or ""),
            "project_id": str(project_id or ""),
            "requester_user_id": str(requester_user_id or ""),
            "trigger": str(getattr(trigger, "value", trigger) or ""),
            "parent_automation_run_id": str(parent_automation_run_id or ""),
            "target_artifact_ids": [str(value) for value in target_artifact_ids or []],
            "evidence": [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in evidence or []
            ],
        }
        serialized = json.dumps(
            normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def _event_matches_run(cls, event: AutomationEventRequest, run: AutomationRun) -> bool:
        constraints = run.constraints if isinstance(run.constraints, dict) else {}
        return cls._event_fingerprint(
            event.event_id,
            event.project_id,
            event.requester_user_id,
            event.trigger,
            event.parent_automation_run_id,
            event.target_artifact_ids,
            event.evidence,
        ) == cls._event_fingerprint(
            run.source_event_id,
            run.project_id,
            run.requester_user_id,
            run.trigger,
            constraints.get("parent_automation_run_id"),
            run.target_artifact_ids,
            run.evidence,
        )

    async def create_definition(
        self, payload: AutomationDefinitionRequest, user_id: str, role: str, permissions: list[str]
    ) -> AutomationDefinition:
        if role not in {"BA", "QA"}:
            raise HTTPException(status_code=403, detail={"code": "AUTOMATION_DEFINITION_DENIED"})
        if payload.trigger == AutomationTrigger.MANUAL:
            raise HTTPException(
                status_code=422,
                detail={"code": "AUTOMATION_TRIGGER_MUST_BE_DOMAIN_EVENT"},
            )
        if payload.enabled and await automation_repository.list_enabled_definitions(
            payload.project_id, payload.trigger
        ):
            raise HTTPException(
                status_code=409, detail={"code": "AUTOMATION_TRIGGER_ALREADY_CONFIGURED"}
            )
        definition = AutomationDefinition(
            project_id=payload.project_id,
            owner_user_id=user_id,
            owner_role=role,
            owner_permissions=permissions,
            name=payload.name,
            trigger=payload.trigger,
            objective=payload.objective,
            intent=payload.intent,
            actions=payload.actions,
            conditions=payload.conditions,
            enabled=payload.enabled,
        )
        try:
            await automation_repository.create_definition(definition)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=409, detail={"code": "AUTOMATION_TRIGGER_ALREADY_CONFIGURED"}
            ) from exc
        return definition

    async def update_definition(
        self, definition: AutomationDefinition, payload: AutomationDefinitionPatch
    ) -> AutomationDefinition:
        if payload.trigger == AutomationTrigger.MANUAL:
            raise HTTPException(
                status_code=422,
                detail={"code": "AUTOMATION_TRIGGER_MUST_BE_DOMAIN_EVENT"},
            )
        if definition.revision != payload.expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": "REVISION_CONFLICT", "latest": definition.model_dump(mode="json")},
            )
        values = payload.model_dump(exclude={"expected_revision"}, exclude_none=True)
        if values.get("enabled") is True:
            enabled = await automation_repository.list_enabled_definitions(
                definition.project_id, definition.trigger
            )
            if any(item.definition_id != definition.definition_id for item in enabled):
                raise HTTPException(
                    status_code=409, detail={"code": "AUTOMATION_TRIGGER_ALREADY_CONFIGURED"}
                )
        try:
            updated = await automation_repository.patch_definition(
                definition.definition_id, payload.expected_revision, values
            )
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=409, detail={"code": "AUTOMATION_TRIGGER_ALREADY_CONFIGURED"}
            ) from exc
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        return updated

    async def create(
        self, payload: AutomationRunRequest, user_id: str, role: str, permissions: list[str]
    ) -> AutomationRun:
        raise HTTPException(
            status_code=410,
            detail={"code": "DIRECT_AUTOMATION_RUN_RETIRED", "replacement": "enqueue_event"},
        )

    async def enqueue_event(self, event: AutomationEventRequest) -> list[AutomationRun]:
        if event.trigger == AutomationTrigger.MANUAL:
            raise HTTPException(
                status_code=422,
                detail={"code": "AUTOMATION_TRIGGER_MUST_BE_DOMAIN_EVENT"},
            )
        if any(item.project_id != event.project_id for item in event.evidence):
            raise HTTPException(
                status_code=422, detail={"code": "AUTOMATION_EVIDENCE_PROJECT_MISMATCH"}
            )
        existing = await automation_repository.find_event_run(event.project_id, event.event_id)
        if existing:
            if not self._event_matches_run(event, existing):
                raise HTTPException(
                    status_code=409, detail={"code": "AUTOMATION_EVENT_ID_REUSE_CONFLICT"}
                )
            if existing.status == AutomationStatus.QUEUED or (
                existing.status == AutomationStatus.DEGRADED
                and existing.error_code == "AUTOMATION_QUEUE_UNAVAILABLE"
            ):
                if existing.status == AutomationStatus.DEGRADED:
                    latest_checkpoint = await automation_repository.latest_checkpoint(
                        existing.automation_run_id
                    )
                    queued = await automation_repository.transition_with_checkpoint(
                        existing.automation_run_id,
                        existing.revision,
                        {"status": AutomationStatus.QUEUED, "error_code": None},
                        phase=AutomationCheckpointPhase.QUEUED,
                        detail={"reason_code": "AUTOMATION_QUEUE_RETRY"},
                        state_snapshot=(
                            latest_checkpoint.state_snapshot if latest_checkpoint else None
                        ),
                    )
                    if not queued:
                        latest = await automation_repository.find_event_run(
                            event.project_id, event.event_id
                        )
                        return [latest or existing]
                    existing = queued
                if not await publish_automation_run(existing.automation_run_id):
                    latest_checkpoint = await automation_repository.latest_checkpoint(
                        existing.automation_run_id
                    )
                    degraded = await automation_repository.transition_with_checkpoint(
                        existing.automation_run_id,
                        existing.revision,
                        {
                            "status": AutomationStatus.DEGRADED,
                            "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                        },
                        phase=AutomationCheckpointPhase.FINALIZED,
                        detail={"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
                        state_snapshot=(
                            latest_checkpoint.state_snapshot if latest_checkpoint else None
                        ),
                    )
                    latest = (
                        degraded
                        or await automation_repository.get_run(existing.automation_run_id)
                        or existing
                    )
                    return [latest]
            return [existing]
        token = self._token_for_user(event.requester_user_id)
        role, permissions = await project_access(event.project_id, token)
        (
            execution_user_id,
            execution_role,
            execution_permissions,
        ) = await self._default_execution_principal(event, role, permissions)
        definitions = await automation_repository.list_definitions(event.project_id)
        matching_definitions = [item for item in definitions if item.trigger == event.trigger]
        if matching_definitions:
            enabled_definitions = [item for item in matching_definitions if item.enabled]
            if not enabled_definitions:
                return []
            if len(enabled_definitions) > 1:
                logger.warning(
                    "Multiple enabled automation definitions found for project={} trigger={}; "
                    "using the most recently updated definition only",
                    event.project_id,
                    event.trigger.value,
                )
            return await self._enqueue_event_runs(
                event,
                role,
                permissions,
                enabled_definitions[:1],
                execution_user_id,
                execution_role,
                execution_permissions,
            )

        return await self._enqueue_event_runs(
            event,
            role,
            permissions,
            [None],
            execution_user_id,
            execution_role,
            execution_permissions,
        )

    @staticmethod
    def _token_for_user(user_id: str) -> str:
        return jwt.encode(
            {"uid": user_id, "sub": user_id, "system_role": "USER", "exp": int(time.time()) + 30},
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    async def _default_execution_principal(self, event, role=None, permissions=None):
        trigger = getattr(event, "trigger", None)
        trigger_value = getattr(trigger, "value", trigger)
        if trigger_value == "WORK_ITEM_CHANGED":
            if role and "project.read" in (permissions or []):
                return event.requester_user_id, role, permissions
            return None, None, []
        required_role = "BA" if trigger_value == "DOCUMENT_INGESTED" else "QA"
        requester_token = self._token_for_user(event.requester_user_id)
        config = {
            "configurable": {"token": f"Bearer {requester_token}", "project_id": event.project_id}
        }
        try:
            principal = await require_operation(
                "POST",
                f"/noi-bo/quan-tri/tu-dong-hoa/du-an/{event.project_id}/nguoi-thuc-thi",
                config,
                {"requester_user_id": event.requester_user_id, "required_role": required_role},
            )
        except AutomationOperationError as error:
            if error.reason_code in {
                "PROJECT_QA_EXECUTOR_UNAVAILABLE",
                "PROJECT_BA_EXECUTOR_UNAVAILABLE",
            }:
                return None, None, []
            raise
        execution_user_id = str(principal.get("executor_user_id") or "")
        if not execution_user_id:
            return None, None, []
        execution_token = self._token_for_user(execution_user_id)
        execution_role, execution_permissions = await project_access(
            event.project_id, execution_token, preferred_role=required_role
        )
        if required_role == "BA":
            stage_permission = "requirement.create"
        elif trigger_value == "API_OPERATION_CONFIRMED":
            stage_permission = "ai.generate_api_testcase"
        elif trigger_value == "PERFORMANCE_CONFIGURATION_APPROVED":
            stage_permission = "ai.generate_performance_plan"
        elif trigger_value == "RELEASE_CHANGED":
            stage_permission = "release.close"
        else:
            stage_permission = "ai.generate_testcase"
        if execution_role != required_role and stage_permission not in execution_permissions:
            return None, None, []
        return execution_user_id, execution_role, execution_permissions

    async def _enqueue_event_runs(
        self,
        event: AutomationEventRequest,
        role: str,
        permissions: list[str],
        definitions: list[AutomationDefinition | None],
        default_execution_user_id: str | None = None,
        default_execution_role: str | None = None,
        default_execution_permissions: list[str] | None = None,
    ) -> list[AutomationRun]:
        runs = []
        for definition in definitions[:1]:
            definition_id = definition.definition_id if definition else None
            existing = await automation_repository.find_event_run(event.project_id, event.event_id)
            if existing:
                if not self._event_matches_run(event, existing):
                    raise HTTPException(
                        status_code=409, detail={"code": "AUTOMATION_EVENT_ID_REUSE_CONFLICT"}
                    )
                runs.append(existing)
                continue

            run = AutomationRun(
                project_id=event.project_id,
                requester_user_id=event.requester_user_id,
                requester_role=role,
                requester_permissions=permissions,
                execution_user_id=default_execution_user_id,
                execution_role=default_execution_role,
                execution_permissions=default_execution_permissions or [],
                kind=AutomationKind.EVENT,
                trigger=event.trigger,
                definition_id=definition_id,
                source_event_id=event.event_id,
                source_event_verified=True,
                objective=(
                    definition.objective
                    if definition
                    else generic_event_objective(event.trigger.value)
                ),
                intent=definition.intent if definition else "",
                target_artifact_ids=event.target_artifact_ids,
                evidence=event.evidence,
                constraints={
                    "trigger": event.trigger.value,
                    "requester_role": role,
                    **(
                        {"automation_conditions": definition.conditions.model_dump(mode="json")}
                        if definition
                        else {}
                    ),
                    **(
                        {"automation_actions": [action.value for action in definition.actions]}
                        if definition and definition.actions
                        else {}
                    ),
                    **(
                        {"parent_automation_run_id": event.parent_automation_run_id}
                        if event.parent_automation_run_id
                        else {}
                    ),
                },
                status=(
                    AutomationStatus.QUEUED
                    if default_execution_user_id
                    else AutomationStatus.AWAITING_AUTHORIZATION
                ),
                error_code=(
                    None if default_execution_user_id else "PROJECT_QA_EXECUTOR_UNAVAILABLE"
                ),
            )
            try:
                run = await automation_repository.create_run_with_checkpoint(
                    run,
                    phase=(
                        AutomationCheckpointPhase.QUEUED
                        if default_execution_user_id
                        else AutomationCheckpointPhase.FINALIZED
                    ),
                    detail=(
                        {}
                        if default_execution_user_id
                        else {"reason_code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"}
                    ),
                )
            except DuplicateKeyError:
                existing = await automation_repository.find_event_run(
                    event.project_id, event.event_id
                )
                if existing:
                    if not self._event_matches_run(event, existing):
                        raise HTTPException(
                            status_code=409, detail={"code": "AUTOMATION_EVENT_ID_REUSE_CONFLICT"}
                        )
                    runs.append(existing)
                    continue
                raise

            if not default_execution_user_id:
                runs.append(run)
                continue
            if not await publish_automation_run(run.automation_run_id):
                updated = await automation_repository.transition_with_checkpoint(
                    run.automation_run_id,
                    run.revision,
                    {
                        "status": AutomationStatus.DEGRADED,
                        "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                    },
                    phase=AutomationCheckpointPhase.FINALIZED,
                    detail={"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
                )
                latest = (
                    updated or await automation_repository.get_run(run.automation_run_id) or run
                )
                runs.append(latest)
                continue
            runs.append(run)
        return runs

    async def authorize_retry(self, run: AutomationRun, expected_revision: int) -> AutomationRun:
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
        if run.error_code == "PROJECT_QA_EXECUTOR_UNAVAILABLE":
            token = self._token_for_user(run.requester_user_id)
            role, permissions = await project_access(run.project_id, token)
            (
                execution_user_id,
                execution_role,
                execution_permissions,
            ) = await self._default_execution_principal(
                AutomationEventRequest(
                    event_id=run.source_event_id or run.automation_run_id,
                    project_id=run.project_id,
                    requester_user_id=run.requester_user_id,
                    trigger=run.trigger or AutomationTrigger.MANUAL,
                    target_artifact_ids=run.target_artifact_ids,
                    evidence=run.evidence,
                ),
                role,
                permissions,
            )
            if not execution_user_id:
                raise HTTPException(
                    status_code=409, detail={"code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"}
                )
            retry_values.update(
                {
                    "execution_user_id": execution_user_id,
                    "execution_role": execution_role,
                    "execution_permissions": execution_permissions,
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
                document_id, separator, revision = event_id[len(prefix) :].rpartition(":")
                if separator and document_id and revision.isdigit():
                    source_document_ids = [document_id]
                else:
                    return None
            else:
                return None
        publication_permissions = (
            [
                "requirement.submit_review",
                "requirement.approve",
                "testcase.submit_review",
                "testcase.approve",
                "proposal.approve",
            ]
            if trigger in {"DOCUMENT_INGESTED", "REQUIREMENT_CHANGED"}
            else []
        )
        if trigger == "TEST_PLAN_CHANGED":
            publication_permissions = ["testplan.approve"]
        elif trigger == "RELEASE_CHANGED":
            publication_permissions = [
                "release.close",
                "testmonitor.snapshot.create",
                "testcompletion.create",
            ]
        elif trigger == "TEST_EXECUTION_RECORDED":
            publication_permissions = ["testadequacy.execution_feedback.record"]
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
