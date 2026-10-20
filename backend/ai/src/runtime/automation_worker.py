import asyncio
import hashlib
from uuid import UUID, uuid4

from loguru import logger

from src.agents.runner.automation_graph import automation_workflow
from src.core.infrastructure.mq import mq
from src.memory.long_term import long_term_memory
from src.memory.short_term import run_store
from src.repositories.automation import automation_repository
from src.runtime.limits import limits
from src.schemas.agent import AgentRunStatus, VeriqRunState
from src.schemas.automation import AutomationCheckpointPhase, AutomationKind, AutomationStatus
from src.schemas.automation import DerivationReceipt, SourceFact
from src.tools.registry import registered_tools, tool_access
from src.services.agent_metrics import agentops
from src.services.automation import automation_service
from src.services.project_access import project_access
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
        for run in await automation_repository.recover_interrupted_runs():
            if run.status == AutomationStatus.QUEUED:
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
                        await automation_service._checkpoint(
                            updated,
                            AutomationCheckpointPhase.FINALIZED,
                            {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
                        )
            else:
                logger.warning(
                    "Interrupted AI automation cannot be replayed safely run_id={} error_code={}",
                    run.automation_run_id,
                    run.error_code,
                )
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
            try:
                message = await mq.consume("ai.automation", timeout=5)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("AI automation worker could not receive a message")
                await asyncio.sleep(1)
                continue
            if not message:
                continue
            acknowledge = False
            requeue = False
            try:
                await self._process(message["payload"])
                acknowledge = True
            except asyncio.CancelledError:
                await mq.reject(message["delivery_tag"], requeue=True)
                raise
            except Exception:
                logger.exception("AI automation worker failed to process a run")
                try:
                    acknowledge = await self._record_worker_failure(message["payload"])
                except Exception:
                    logger.exception("AI automation worker could not persist the failed run state")
                    requeue = True
            finally:
                if message["delivery_tag"] in mq.pending_acks:
                    if acknowledge:
                        await mq.ack(message["delivery_tag"])
                    else:
                        await mq.reject(message["delivery_tag"], requeue=requeue)

    async def _record_worker_failure(self, payload: dict) -> bool:
        automation_run_id = str(payload.get("automation_run_id") or "")
        if not automation_run_id:
            return True
        run = await automation_repository.get_run(automation_run_id)
        if not run or run.status not in {AutomationStatus.QUEUED, AutomationStatus.RUNNING}:
            return run is None or run.status not in {AutomationStatus.QUEUED, AutomationStatus.RUNNING}
        updated = await automation_repository.transition(
            automation_run_id,
            run.revision,
            {
                "status": AutomationStatus.FAILED,
                "error_code": "AUTOMATION_WORKER_FAILED",
            },
        )
        if updated:
            await automation_service._checkpoint(
                updated,
                AutomationCheckpointPhase.FINALIZED,
                {"reason_code": "AUTOMATION_WORKER_FAILED"},
            )
            return True
        return False

    async def _process(self, payload: dict) -> None:
        automation_run_id = str(payload.get("automation_run_id") or "")
        if not automation_run_id:
            return
        run = await automation_repository.get_run(automation_run_id)
        if not run or run.status != AutomationStatus.QUEUED:
            return
        token = await automation_service.token_for(automation_run_id)
        if not token:
            reason_code = (
                "AUTOMATION_EXECUTOR_UNAVAILABLE"
                if not run.execution_user_id or not run.execution_role
                else "AUTHORIZATION_EXPIRED"
            )
            updated = await automation_repository.transition(
                automation_run_id,
                run.revision,
                {"status": AutomationStatus.AWAITING_AUTHORIZATION, "error_code": reason_code},
            )
            if updated:
                await automation_service._checkpoint(
                    updated,
                    AutomationCheckpointPhase.FINALIZED,
                    {"reason_code": reason_code},
                )
            return
        try:
            live_role, live_permissions = await project_access(
                run.project_id, token, run.automation_run_id
            )
        except Exception:
            logger.exception("AI automation principal is no longer authorized")
            updated = await automation_repository.transition(
                automation_run_id,
                run.revision,
                {
                    "status": AutomationStatus.AWAITING_AUTHORIZATION,
                    "error_code": "AUTOMATION_PRINCIPAL_UNAVAILABLE",
                },
            )
            if updated:
                await automation_service._checkpoint(
                    updated,
                    AutomationCheckpointPhase.FINALIZED,
                    {"reason_code": "AUTOMATION_PRINCIPAL_UNAVAILABLE"},
                )
            return
        expected_role = run.execution_role
        if live_role != expected_role:
            updated = await automation_repository.transition(
                automation_run_id,
                run.revision,
                {
                    "status": AutomationStatus.AWAITING_AUTHORIZATION,
                    "error_code": "AUTOMATION_PRINCIPAL_ROLE_CHANGED",
                },
            )
            if updated:
                await automation_service._checkpoint(
                    updated,
                    AutomationCheckpointPhase.FINALIZED,
                    {"reason_code": "AUTOMATION_PRINCIPAL_ROLE_CHANGED"},
                )
            return
        running = await automation_repository.transition(
            automation_run_id,
            run.revision,
            {
                "status": AutomationStatus.RUNNING,
                "error_code": None,
                "execution_permissions": live_permissions,
            },
        )
        if not running:
            return
        trace_id = str(uuid4())
        traced = await automation_repository.transition(
            automation_run_id,
            running.revision,
            {"trace_id": trace_id},
        )
        if not traced:
            return
        running = traced
        latest_checkpoint = await automation_repository.latest_checkpoint(automation_run_id)
        snapshot = latest_checkpoint.state_snapshot if latest_checkpoint else None
        resume_phase = snapshot.completed_phase.value if snapshot else None
        if snapshot and (
            snapshot.run.run_id != automation_run_id
            or snapshot.run.project_id != running.project_id
            or snapshot.run.user_id != (running.execution_user_id or running.requester_user_id)
            or snapshot.run.role != live_role
        ):
            await self._fail(
                automation_run_id,
                running.revision,
                "AUTOMATION_CHECKPOINT_IDENTITY_MISMATCH",
            )
            return
        agent_run = snapshot.run if snapshot else VeriqRunState(
            run_id=running.automation_run_id,
            project_id=running.project_id,
            user_id=running.execution_user_id or running.requester_user_id,
            role=live_role,
            permissions=live_permissions,
            objective=running.objective,
            intent=running.intent,
            model_metadata=model_metadata(),
        )
        agentops.record_session_start(agent_run.run_id, running.requester_user_id)
        try:
            graph_state = (
                snapshot.model_dump(mode="python")
                if snapshot
                else {
                    "automatic": True,
                    "run": agent_run.model_dump(mode="python"),
                    "evidence": [item.model_dump(mode="python") for item in running.evidence],
                    "target_artifact_ids": running.target_artifact_ids,
                    "constraints": running.constraints,
                    "source_event_verified": running.source_event_verified,
                    "tasks": [],
                    "results": [],
                }
            )
            graph_state["token"] = f"Bearer {token}"
            graph_state["automatic"] = True
            graph_state["constraints"] = {
                **graph_state.get("constraints", {}),
                "change_simulation": running.kind == AutomationKind.CHANGE_SIMULATION,
            }
            graph_state["resume_after_phase"] = resume_phase
            result = await asyncio.wait_for(
                automation_workflow.ainvoke(
                    graph_state,
                    config={
                        "run_id": UUID(trace_id),
                        "run_name": "veriq-ai-automation",
                        "tags": ["veriq", "automation", running.kind.value],
                        "metadata": {
                            "automation_run_id": automation_run_id,
                            "project_id": running.project_id,
                            "trigger": running.trigger.value if running.trigger else "ON_DEMAND",
                        },
                    },
                ),
                timeout=limits.run_timeout_seconds,
            )
            completed = VeriqRunState(**result["run"])
            if completed.status == AgentRunStatus.COMPLETED:
                terminal_status = AutomationStatus.COMPLETED
            elif completed.status == AgentRunStatus.FAILED:
                terminal_status = AutomationStatus.FAILED
            else:
                terminal_status = AutomationStatus.DEGRADED
            source_facts = [
                SourceFact(
                    source_fact_id=(
                        "FACT-"
                        + hashlib.sha256(
                            "|".join(
                                (
                                    automation_run_id,
                                    str(item.get("artifact_type") or "artifact"),
                                    str(item.get("artifact_id") or ""),
                                    str(item.get("artifact_version_id") or ""),
                                    str(item.get("source_start") or ""),
                                    str(item.get("source_end") or ""),
                                    str(item.get("quote") or ""),
                                )
                            ).encode("utf-8")
                        ).hexdigest()[:32]
                    ),
                    automation_run_id=automation_run_id,
                    project_id=running.project_id,
                    artifact_type=str(item.get("artifact_type") or "artifact"),
                    artifact_id=str(item.get("artifact_id") or ""),
                    artifact_version_id=item.get("artifact_version_id"),
                    source_start=item.get("source_start"),
                    source_end=item.get("source_end"),
                    source=str(item.get("source") or "database"),
                    authority=str(item.get("authority") or "project"),
                    quote=str(item["quote"]),
                    fact_kind=str(item.get("fact_kind") or "source_evidence"),
                    quote_sha256=hashlib.sha256(
                        str(item["quote"]).encode("utf-8")
                    ).hexdigest(),
                )
                for item in result.get("source_facts", [])
                if item.get("artifact_id") and str(item.get("quote") or "").strip()
            ]
            # Mutation tools may return source citations read from the
            # authoritative service during compilation. Accept those only
            # after the tool's postcondition readback succeeded; an LLM
            # narrative or an unverified tool response is not provenance.
            seen_facts = {
                (
                    fact.artifact_type,
                    fact.artifact_id,
                    fact.artifact_version_id,
                    fact.source_start,
                    fact.source_end,
                    fact.quote,
                )
                for fact in source_facts
            }
            for observation in completed.observations:
                if (
                    observation.get("tool_name") != "process_ingested_requirement_document"
                    or observation.get("status") != "COMPLETED"
                    or (observation.get("verification") or {}).get("status") != "COMPLETED"
                ):
                    continue
                operation_result = observation.get("result") or {}
                for item in operation_result.get("source_facts", []):
                    quote = str(item.get("quote") or "").strip()
                    artifact_id = str(item.get("artifact_id") or "").strip()
                    if not quote or not artifact_id:
                        continue
                    key = (
                        str(item.get("artifact_type") or "artifact"),
                        artifact_id,
                        str(item.get("artifact_version_id") or "") or None,
                        item.get("source_start"),
                        item.get("source_end"),
                        quote,
                    )
                    if key in seen_facts:
                        continue
                    seen_facts.add(key)
                    source_facts.append(
                        SourceFact(
                            automation_run_id=automation_run_id,
                            project_id=running.project_id,
                            artifact_type=key[0],
                            artifact_id=artifact_id,
                            artifact_version_id=key[2],
                            source=str(item.get("source") or "document"),
                            authority=str(item.get("authority") or "project"),
                            quote=key[5],
                            fact_kind=str(item.get("fact_kind") or "source_evidence"),
                            quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                            source_start=key[3],
                            source_end=key[4],
                        )
                    )
            verified_outputs = self._verified_output_refs(completed)
            transformation_steps = list(
                dict.fromkeys(
                    str(item.get("tool_name"))
                    for item in completed.tool_calls
                    if item.get("tool_name")
                )
            )
            try:
                await automation_repository.replace_provenance(
                    automation_run_id,
                    source_facts,
                    DerivationReceipt(
                        automation_run_id=automation_run_id,
                        project_id=running.project_id,
                        agent_run_id=completed.run_id,
                        source_fact_ids=[item.source_fact_id for item in source_facts],
                        transformation_steps=transformation_steps,
                        output_evidence_refs=verified_outputs,
                        model_metadata=completed.model_metadata,
                        outcome=terminal_status.value,
                    ),
                )
            except Exception:
                logger.exception("AI automation provenance could not be persisted")
                await self._fail(
                    automation_run_id,
                    running.revision,
                    "AUTOMATION_PROVENANCE_PERSISTENCE_FAILED",
                )
                agentops.record_session_end(completed.run_id, "failed")
                return

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
            if not updated:
                agentops.record_session_end(completed.run_id, "failed")
                return
            try:
                await run_store.save(completed)
                if completed.status == AgentRunStatus.COMPLETED:
                    await long_term_memory.record_verified(completed)
            except Exception:
                logger.exception(
                    "AI automation completed but optional agent memory could not be persisted"
                )
            await automation_service._checkpoint(
                updated,
                AutomationCheckpointPhase.FINALIZED,
                {"agent_run_id": completed.run_id, "error_code": completed.error_code},
            )
            agentops.record_session_end(
                completed.run_id,
                "done" if terminal_status == AutomationStatus.COMPLETED else "failed",
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

    @staticmethod
    def _verified_output_refs(run) -> list[str]:
        references = []
        for observation in run.observations:
            if observation.get("status") != "COMPLETED":
                continue
            access = tool_access(registered_tools().get(observation.get("tool_name")))
            if not access or access.action != "MUTATE":
                continue
            verification = observation.get("verification") or {}
            if verification.get("status") != "COMPLETED":
                continue
            references.extend(
                str(value)
                for value in verification.get("artifact_ids", [])
                if value
            )
            if verification.get("artifact_id"):
                references.append(str(verification["artifact_id"]))
        return list(dict.fromkeys(references))


automation_worker = AutomationWorker()
