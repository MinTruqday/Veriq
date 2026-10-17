from fastapi import HTTPException

from src.core.infrastructure.mq import mq
from src.core.infrastructure.redis import redis
from src.repositories.automation import automation_repository
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationRun,
    AutomationRunRequest,
    AutomationStatus,
)


class AutomationService:
    async def create(
        self,
        payload: AutomationRunRequest,
        user_id: str,
        role: str,
        permissions: list[str],
        token: str,
    ) -> AutomationRun:
        run = AutomationRun(
            project_id=payload.project_id,
            requester_user_id=user_id,
            requester_role=role,
            requester_permissions=permissions,
            kind=payload.kind,
            objective=payload.objective,
            intent=payload.intent,
            target_artifact_ids=payload.target_artifact_ids,
            evidence=payload.evidence,
            constraints=payload.constraints,
        )
        await automation_repository.create_run(run)
        await self._store_token(run.automation_run_id, token)
        await self._checkpoint(run, AutomationCheckpointPhase.QUEUED)
        if not await mq.publish("ai.automation", {"automation_run_id": run.automation_run_id}):
            updated = await automation_repository.transition(
                run.automation_run_id,
                run.revision,
                {"status": AutomationStatus.DEGRADED, "error_code": "AUTOMATION_QUEUE_UNAVAILABLE"},
            )
            if updated:
                return updated
        return run

    async def authorize_retry(
        self, run: AutomationRun, expected_revision: int, token: str
    ) -> AutomationRun:
        if run.revision != expected_revision:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")})
        if run.status not in {AutomationStatus.AWAITING_AUTHORIZATION, AutomationStatus.FAILED, AutomationStatus.DEGRADED}:
            raise HTTPException(status_code=409, detail={"code": "AUTOMATION_RETRY_NOT_ALLOWED"})
        await self._store_token(run.automation_run_id, token)
        updated = await automation_repository.transition(
            run.automation_run_id,
            expected_revision,
            {"status": AutomationStatus.QUEUED, "error_code": None},
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        await self._checkpoint(updated, AutomationCheckpointPhase.QUEUED)
        if not await mq.publish("ai.automation", {"automation_run_id": run.automation_run_id}):
            raise HTTPException(status_code=503, detail={"code": "AUTOMATION_QUEUE_UNAVAILABLE"})
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
        await redis.delete(self._token_key(run.automation_run_id))
        await self._checkpoint(updated, AutomationCheckpointPhase.FINALIZED)
        return updated

    async def record_human_decision(
        self, run: AutomationRun, expected_revision: int, agent_run: dict
    ) -> AutomationRun:
        if run.revision != expected_revision:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "latest": run.model_dump(mode="json")})
        status = (
            AutomationStatus.COMPLETED
            if agent_run.get("status") == "COMPLETED"
            else AutomationStatus.DEGRADED
            if agent_run.get("status") != "FAILED"
            else AutomationStatus.FAILED
        )
        updated = await automation_repository.transition(
            run.automation_run_id,
            expected_revision,
            {
                "status": status,
                "result": {
                    "proposal": agent_run.get("proposal"),
                    "evidence_refs": agent_run.get("evidence_refs", []),
                    "observations": agent_run.get("observations", []),
                    "error_code": agent_run.get("error_code"),
                },
                "error_code": agent_run.get("error_code"),
            },
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        await self._checkpoint(updated, AutomationCheckpointPhase.FINALIZED)
        return updated

    async def token_for(self, automation_run_id: str) -> str | None:
        return await redis.get(self._token_key(automation_run_id))

    async def _store_token(self, automation_run_id: str, token: str) -> None:
        await redis.setex(self._token_key(automation_run_id), 1800, token)

    async def _checkpoint(self, run: AutomationRun, phase: AutomationCheckpointPhase, detail: dict | None = None) -> None:
        await automation_repository.save_checkpoint(
            AutomationCheckpoint(
                automation_run_id=run.automation_run_id,
                phase=phase,
                status=run.status,
                detail=detail or {},
            )
        )

    @staticmethod
    def _token_key(automation_run_id: str) -> str:
        return f"ai:automation:authorization:{automation_run_id}"


automation_service = AutomationService()
