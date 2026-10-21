import time

import jwt
from fastapi import HTTPException
from loguru import logger
from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.mq import mq
from src.core.security.guardrails import guardrails_engine
from src.repositories.automation import automation_repository
from src.services.project_access import project_access
from src.tools.registry import registered_tools, tool_access
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationRun,
    AutomationRunRequest,
    AutomationStatus,
    AutomationDefinition,
    AutomationDefinitionPatch,
    AutomationDefinitionRequest,
    AutomationEventRequest,
    AutomationKind,
)
from src.prompts.automation_events import generic_event_objective
from src.runtime.limits import limits


class AutomationService:
    async def create_definition(
        self,
        payload: AutomationDefinitionRequest,
        user_id: str,
        role: str,
        permissions: list[str],
    ) -> AutomationDefinition:
        if role not in {"BA", "QA"}:
            raise HTTPException(status_code=403, detail={"code": "AUTOMATION_DEFINITION_DENIED"})
        if payload.enabled and await automation_repository.list_enabled_definitions(
            payload.project_id, payload.trigger
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_TRIGGER_ALREADY_CONFIGURED"},
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
            enabled=payload.enabled,
        )
        try:
            await automation_repository.create_definition(definition)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_TRIGGER_ALREADY_CONFIGURED"},
            ) from exc
        return definition

    async def update_definition(
        self,
        definition: AutomationDefinition,
        payload: AutomationDefinitionPatch,
    ) -> AutomationDefinition:
        if definition.revision != payload.expected_revision:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "latest": definition.model_dump(mode="json")})
        values = payload.model_dump(exclude={"expected_revision"}, exclude_none=True)
        if values.get("enabled") is True:
            enabled = await automation_repository.list_enabled_definitions(
                definition.project_id, definition.trigger
            )
            if any(item.definition_id != definition.definition_id for item in enabled):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "AUTOMATION_TRIGGER_ALREADY_CONFIGURED"},
                )
        try:
            updated = await automation_repository.patch_definition(
                definition.definition_id, payload.expected_revision, values
            )
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_TRIGGER_ALREADY_CONFIGURED"},
            ) from exc
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        return updated

    async def create(
        self,
        payload: AutomationRunRequest,
        user_id: str,
        role: str,
        permissions: list[str],
    ) -> AutomationRun:
        if any(item.project_id != payload.project_id for item in payload.evidence):
            raise HTTPException(status_code=422, detail={"code": "AUTOMATION_EVIDENCE_PROJECT_MISMATCH"})
        if payload.change_simulation:
            inspection = await guardrails_engine.async_inspect_input(
                payload.change_simulation.proposed_source_text
            )
            if not inspection.get("is_safe", False):
                raise HTTPException(
                    status_code=422,
                    detail={"code": "CHANGE_SIMULATION_SOURCE_REJECTED"},
                )
        if payload.intent:
            capability = registered_tools().get(payload.intent)
            access = tool_access(capability)
            if not access:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "AUTOMATION_CAPABILITY_UNKNOWN"},
                )
            if access.permission not in permissions:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "AUTOMATION_CAPABILITY_DENIED"},
                )
        run = AutomationRun(
            project_id=payload.project_id,
            requester_user_id=user_id,
            requester_role=role,
            requester_permissions=permissions,
            execution_user_id=user_id,
            execution_role=role,
            execution_permissions=permissions,
            kind=payload.kind,
            objective=payload.objective,
            intent=payload.intent,
            target_artifact_ids=payload.target_artifact_ids,
            evidence=payload.evidence,
            constraints=payload.constraints,
            change_simulation=payload.change_simulation,
        )
        await automation_repository.create_run(run)
        await self._checkpoint(run, AutomationCheckpointPhase.QUEUED)
        if not await mq.publish("ai.automation", {"automation_run_id": run.automation_run_id}):
            updated = await automation_repository.transition(
                run.automation_run_id,
                run.revision,
                {"status": AutomationStatus.DEGRADED, "error_code": "AUTOMATION_QUEUE_UNAVAILABLE"},
            )
            if updated:
                await self._checkpoint(
                    updated,
                    AutomationCheckpointPhase.FINALIZED,
                    {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
                )
                return updated
        return run

    async def enqueue_event(self, event: AutomationEventRequest) -> list[AutomationRun]:
        if any(item.project_id != event.project_id for item in event.evidence):
            raise HTTPException(status_code=422, detail={"code": "AUTOMATION_EVIDENCE_PROJECT_MISMATCH"})
        existing = await automation_repository.find_event_run(event.project_id, event.event_id)
        if existing:
            if existing.status == AutomationStatus.QUEUED or (
                existing.status == AutomationStatus.DEGRADED
                and existing.error_code == "AUTOMATION_QUEUE_UNAVAILABLE"
            ):
                if existing.status == AutomationStatus.DEGRADED:
                    queued = await automation_repository.transition(
                        existing.automation_run_id,
                        existing.revision,
                        {"status": AutomationStatus.QUEUED, "error_code": None},
                    )
                    if not queued:
                        latest = await automation_repository.find_event_run(
                            event.project_id, event.event_id
                        )
                        return [latest or existing]
                    existing = queued
                    await self._checkpoint(existing, AutomationCheckpointPhase.QUEUED)
                if not await mq.publish(
                    "ai.automation", {"automation_run_id": existing.automation_run_id}
                ):
                    degraded = await automation_repository.transition(
                        existing.automation_run_id,
                        existing.revision,
                        {
                            "status": AutomationStatus.DEGRADED,
                            "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                        },
                    )
                    if degraded:
                        await self._checkpoint(
                            degraded,
                            AutomationCheckpointPhase.FINALIZED,
                            {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
                        )
                    return [degraded or existing]
            return [existing]
        token = self._token_for_user(event.requester_user_id)
        role, permissions = await project_access(event.project_id, token)
        execution_user_id, execution_role, execution_permissions = (
            await self._default_execution_principal(event, role, permissions)
        )
        definitions = await automation_repository.list_definitions(event.project_id)
        matching_definitions = [
            item for item in definitions if item.trigger == event.trigger
        ]
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
            {
                "uid": user_id,
                "sub": user_id,
                "system_role": "USER",
                "exp": int(time.time()) + 30,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    async def _default_execution_principal(self, event, role, permissions):
        """Run project automation as the event actor, without borrowing a project role.

        Tool and service authorization still validate the actor's current project
        permissions at execution time. This lets one person own the whole workflow
        when their role grants the requested operation, while preventing implicit
        QA elevation or cross-user execution.
        """
        return event.requester_user_id, role, permissions

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
            existing = await automation_repository.find_event_run(
                event.project_id,
                event.event_id,
            )
            if existing:
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
                constraints={"trigger": event.trigger.value},
                status=(
                    AutomationStatus.QUEUED
                    if default_execution_user_id
                    else AutomationStatus.AWAITING_AUTHORIZATION
                ),
                error_code=(
                    None
                    if default_execution_user_id
                    else "PROJECT_QA_EXECUTOR_UNAVAILABLE"
                ),
            )
            try:
                await automation_repository.create_run(run)
            except DuplicateKeyError:
                existing = await automation_repository.find_event_run(
                    event.project_id,
                    event.event_id,
                )
                if existing:
                    runs.append(existing)
                    continue
                raise

            await self._checkpoint(run, AutomationCheckpointPhase.QUEUED)
            if not default_execution_user_id:
                await self._checkpoint(
                    run,
                    AutomationCheckpointPhase.FINALIZED,
                    {"reason_code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"},
                )
                runs.append(run)
                continue
            if not await mq.publish(
                "ai.automation", {"automation_run_id": run.automation_run_id}
            ):
                updated = await automation_repository.transition(
                    run.automation_run_id,
                    run.revision,
                    {
                        "status": AutomationStatus.DEGRADED,
                        "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                    },
                )
                if updated:
                    await self._checkpoint(
                        updated,
                        AutomationCheckpointPhase.FINALIZED,
                        {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
                    )
                runs.append(updated or run)
                continue
            runs.append(run)
        return runs

    async def authorize_retry(
        self, run: AutomationRun, expected_revision: int
    ) -> AutomationRun:
        if run.revision != expected_revision:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")})
        if run.error_code == "AUTOMATION_ACTION_OUTCOME_UNCERTAIN":
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOMATION_RETRY_REQUIRES_RECONCILIATION"},
            )
        if run.status not in {AutomationStatus.AWAITING_AUTHORIZATION, AutomationStatus.FAILED, AutomationStatus.DEGRADED}:
            raise HTTPException(status_code=409, detail={"code": "AUTOMATION_RETRY_NOT_ALLOWED"})
        retry_values = {"status": AutomationStatus.QUEUED, "error_code": None}
        if run.error_code == "PROJECT_QA_EXECUTOR_UNAVAILABLE":
            token = self._token_for_user(run.requester_user_id)
            role, permissions = await project_access(run.project_id, token)
            execution_user_id, execution_role, execution_permissions = (
                await self._default_execution_principal(
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
            )
            if not execution_user_id:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"},
                )
            retry_values.update(
                {
                    "execution_user_id": execution_user_id,
                    "execution_role": execution_role,
                    "execution_permissions": execution_permissions,
                }
            )
        updated = await automation_repository.transition(
            run.automation_run_id,
            expected_revision,
            retry_values,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        await self._checkpoint(updated, AutomationCheckpointPhase.QUEUED)
        if not await mq.publish("ai.automation", {"automation_run_id": run.automation_run_id}):
            degraded = await automation_repository.transition(
                updated.automation_run_id,
                updated.revision,
                {
                    "status": AutomationStatus.DEGRADED,
                    "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                },
            )
            if not degraded:
                raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
            await self._checkpoint(
                degraded,
                AutomationCheckpointPhase.FINALIZED,
                {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
            )
            return degraded
        return updated

    async def cancel(self, run: AutomationRun, expected_revision: int) -> AutomationRun:
        if run.revision != expected_revision:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")})
        if run.status in {AutomationStatus.COMPLETED, AutomationStatus.CANCELLED}:
            raise HTTPException(status_code=409, detail={"code": "AUTOMATION_CANCEL_NOT_ALLOWED"})
        updated = await automation_repository.transition(
            run.automation_run_id,
            expected_revision,
            {"status": AutomationStatus.CANCELLED},
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        await self._checkpoint(updated, AutomationCheckpointPhase.FINALIZED)
        return updated

    async def token_for(self, automation_run_id: str) -> str | None:
        run = await automation_repository.get_run(automation_run_id)
        if not run or not run.execution_user_id or not run.execution_role:
            return None
        execution_user_id = run.execution_user_id
        return jwt.encode(
            {
                "uid": execution_user_id,
                "sub": execution_user_id,
                "system_role": "USER",
                "ai_automation_run_id": run.automation_run_id,
                "ai_automation_initiator_id": run.requester_user_id,
                "ai_automation_definition_id": run.definition_id,
                "exp": int(time.time()) + limits.run_timeout_seconds,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    async def _checkpoint(self, run: AutomationRun, phase: AutomationCheckpointPhase, detail: dict | None = None) -> None:
        await automation_repository.save_checkpoint(
            AutomationCheckpoint(
                automation_run_id=run.automation_run_id,
                phase=phase,
                status=run.status,
                detail=detail or {},
            )
        )

automation_service = AutomationService()
