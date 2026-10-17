import asyncio

from loguru import logger

from src.agents.runner.graph import canonical_workflow
from src.core.infrastructure.mq import mq
from src.memory.long_term import long_term_memory
from src.memory.short_term import run_store
from src.repositories.automation import automation_repository
from src.runtime.limits import limits
from src.schemas.agent import AgentRunStatus, VeriqRunState
from src.schemas.automation import AutomationCheckpointPhase, AutomationStatus
from src.schemas.automation import DerivationReceipt, SourceFact
from src.services.agent_metrics import agentops
from src.services.automation import automation_service
from src.services.inference import model_metadata
from src.utils.background import create_background_task


class AutomationWorker:
    def __init__(self):
        self._task = None
        self._stopping = False

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopping = False
        self._task = create_background_task(self._consume(), "ai-automation-worker")

    async def stop(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _consume(self) -> None:
        while not self._stopping:
            message = await mq.consume("ai.automation", timeout=5)
            if not message:
                continue
            try:
                await self._process(message["payload"])
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("AI automation worker failed to process a run")
            finally:
                await mq.ack(message["delivery_tag"])

    async def _process(self, payload: dict) -> None:
        automation_run_id = str(payload.get("automation_run_id") or "")
        if not automation_run_id:
            return
        run = await automation_repository.get_run(automation_run_id)
        if not run or run.status != AutomationStatus.QUEUED:
            return
        token = await automation_service.token_for(automation_run_id)
        if not token:
            updated = await automation_repository.transition(
                automation_run_id,
                run.revision,
                {"status": AutomationStatus.AWAITING_AUTHORIZATION, "error_code": "AUTHORIZATION_EXPIRED"},
            )
            if updated:
                await automation_service._checkpoint(updated, AutomationCheckpointPhase.FINALIZED)
            return
        running = await automation_repository.transition(
            automation_run_id,
            run.revision,
            {"status": AutomationStatus.RUNNING, "error_code": None},
        )
        if not running:
            return
        await automation_service._checkpoint(running, AutomationCheckpointPhase.CONTEXT_LOADED)
        agent_run = VeriqRunState(
            project_id=running.project_id,
            user_id=running.requester_user_id,
            role=running.requester_role,
            permissions=running.requester_permissions,
            objective=running.objective,
            intent=running.intent,
            model_metadata=model_metadata(),
        )
        agentops.record_session_start(agent_run.run_id, running.requester_user_id)
        try:
            result = await asyncio.wait_for(
                canonical_workflow.ainvoke(
                    {
                        "run": agent_run.model_dump(mode="python"),
                        "token": f"Bearer {token}",
                        "evidence": [item.model_dump(mode="python") for item in running.evidence],
                        "target_artifact_ids": running.target_artifact_ids,
                        "constraints": running.constraints,
                        "tasks": [],
                        "results": [],
                    }
                ),
                timeout=limits.run_timeout_seconds,
            )
            completed = VeriqRunState(**result["run"])
            await run_store.save(completed)
            if completed.status == AgentRunStatus.COMPLETED:
                await long_term_memory.record_verified(completed)
            terminal_status = (
                AutomationStatus.AWAITING_HUMAN_DECISION
                if completed.status == AgentRunStatus.APPROVAL_REQUIRED
                else AutomationStatus.COMPLETED
                if completed.status == AgentRunStatus.COMPLETED
                else AutomationStatus.DEGRADED
            )
            updated = await automation_repository.transition(
                automation_run_id,
                running.revision,
                {
                    "status": terminal_status,
                    "agent_run_id": completed.run_id,
                    "result": {
                        "proposal": completed.proposal,
                        "evidence_refs": completed.evidence_refs,
                        "observations": completed.observations,
                        "error_code": completed.error_code,
                    },
                    "error_code": completed.error_code,
                },
            )
            if updated:
                await automation_repository.clear_provenance(automation_run_id)
                source_facts = []
                for item in result.get("evidence", []):
                    quote = str(item.get("text") or "").strip()
                    if not quote:
                        continue
                    source_facts.append(
                        SourceFact(
                            automation_run_id=automation_run_id,
                            project_id=running.project_id,
                            artifact_type=str(item.get("artifact_type") or "artifact"),
                            artifact_id=str(item.get("artifact_id") or ""),
                            artifact_version_id=item.get("artifact_version_id"),
                            source=str(item.get("source") or "database"),
                            authority=str(item.get("authority") or "project"),
                            quote=quote,
                        )
                    )
                await automation_repository.save_source_facts(source_facts)
                await automation_repository.save_receipt(
                    DerivationReceipt(
                        automation_run_id=automation_run_id,
                        project_id=running.project_id,
                        agent_run_id=completed.run_id,
                        source_fact_ids=[item.source_fact_id for item in source_facts],
                        output_evidence_refs=completed.evidence_refs,
                        outcome=terminal_status.value,
                    )
                )
                await automation_service._checkpoint(
                    updated,
                    AutomationCheckpointPhase.GRAPH_COMPLETED,
                    {"agent_run_id": completed.run_id},
                )
                await automation_service._checkpoint(updated, AutomationCheckpointPhase.FINALIZED)
            agentops.record_session_end(
                completed.run_id,
                "done" if terminal_status in {AutomationStatus.COMPLETED, AutomationStatus.AWAITING_HUMAN_DECISION} else "failed",
            )
        except TimeoutError:
            await self._fail(automation_run_id, running.revision, "AUTOMATION_LIMIT_REACHED")
            agentops.record_session_end(agent_run.run_id, "failed")
        except Exception:
            logger.exception("AI automation graph execution failed")
            await self._fail(automation_run_id, running.revision, "AUTOMATION_EXECUTION_FAILED")
            agentops.record_session_end(agent_run.run_id, "failed")

    async def _fail(self, automation_run_id: str, revision: int, code: str) -> None:
        updated = await automation_repository.transition(
            automation_run_id,
            revision,
            {"status": AutomationStatus.FAILED, "error_code": code},
        )
        if updated:
            await automation_service._checkpoint(updated, AutomationCheckpointPhase.FINALIZED)


automation_worker = AutomationWorker()
