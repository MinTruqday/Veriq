import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from loguru import logger

from src.agents.runner.automation_graph import automation_workflow
from src.agents.runner.automation_validation import tool_call_records_for_observations
from src.core.infrastructure.mq import mq
from src.memory.long_term import long_term_memory
from src.memory.short_term import run_store
from src.repositories.automation import automation_repository
from src.repositories.mcp import mcp_repository
from src.runtime.limits import limits
from src.runtime.queue_names import AUTOMATION_QUEUE
from src.schemas.agent import AgentRunStatus, VeriqRunState
from src.schemas.automation import (
    AutomationCheckpointPhase,
    AutomationEventRequest,
    AutomationGraphSnapshot,
    AutomationKind,
    AutomationRun,
    AutomationStatus,
    AutomationTrigger,
    ChangeSimulationInput,
    DerivationReceipt,
    DerivationStep,
    EvidenceItem,
    SourceFact,
)
from src.services.agent_metrics import agentops
from src.services.automation import automation_service
from src.services.automation_provenance import (
    canonicalize_source_facts,
    carry_source_fact_lineage,
    has_provenance_gap,
    missing_blueprint_artifact_coverage_count,
    source_fact_identity,
    verified_release_gate_mutation_refs,
    verified_blueprint_artifact_lineage,
    verified_blueprint_claim_lineage,
    verified_blueprint_from_observations,
    verified_source_span,
)
from src.services.inference import model_metadata
from src.services.project_access import project_access
from src.tools.registry import registered_tools, tool_access
from src.tools.testing_api import AutomationOperationError, require_operation
from src.utils.background import create_background_task


def _automation_retry_delay_seconds(dispatch_failures: int) -> int:
    base_delay = limits.queue_retry_base_seconds
    maximum_delay = limits.queue_retry_max_seconds
    if (
        isinstance(dispatch_failures, bool)
        or not isinstance(dispatch_failures, int)
        or dispatch_failures < 0
        or base_delay < 1
        or maximum_delay < base_delay
    ):
        raise ValueError("automation_retry_delay_configuration_invalid")
    doublings = max(0, dispatch_failures - 1)
    maximum_doublings = (maximum_delay // base_delay).bit_length()
    return min(base_delay * (1 << min(doublings, maximum_doublings)), maximum_delay)


def terminal_status_for_agent_run(completed: VeriqRunState) -> AutomationStatus:
    if completed.status == AgentRunStatus.COMPLETED:
        return AutomationStatus.COMPLETED
    if completed.error_code == "AUTOMATION_WAITING_FOR_INPUT":
        return AutomationStatus.AWAITING_INPUT
    if (
        completed.status == AgentRunStatus.FAILED
        and completed.error_code == "INSUFFICIENT_EVIDENCE"
    ):
        return AutomationStatus.DEGRADED
    if completed.status == AgentRunStatus.FAILED:
        return AutomationStatus.FAILED
    return AutomationStatus.DEGRADED


def resume_run_with_live_permissions(snapshot, live_permissions):
    if snapshot is None:
        return None
    return snapshot.run.model_copy(update={"permissions": list(live_permissions)})


class AutomationWorker:
    def __init__(self):
        self._task = None
        self._startup_recovery_task = None
        self._stopping = False
        self._last_queue_retry_scan = 0.0
        self._last_expired_run_recovery_scan = 0.0

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopping = False
        startup_cutoff = datetime.now(timezone.utc)
        self._task = create_background_task(
            self._supervise_consumer(), "ai-automation-worker"
        )
        self._startup_recovery_task = create_background_task(
            self._retry_startup_recovery(startup_cutoff),
            "ai-automation-startup-recovery",
        )

    async def _retry_startup_recovery(self, startup_cutoff: datetime) -> None:
        while not self._stopping:
            try:
                cursor = None
                while not self._stopping:
                    runs = await automation_repository.recover_interrupted_runs(
                        startup_cutoff,
                        after_automation_run_id=cursor,
                        limit=limits.automation_recovery_batch_size,
                    )
                    if not runs:
                        break
                    await self._dispatch_recovered_runs(runs)
                    cursor = runs[-1].automation_run_id
                    if len(runs) < limits.automation_recovery_batch_size:
                        break
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "AI automation startup recovery failed; retrying without stopping consumer"
                )
                await asyncio.sleep(5)

    async def _dispatch_recovered_runs(self, runs) -> None:
        for run in runs:
            if run.status == AutomationStatus.QUEUED:
                try:
                    published = await mq.publish(
                        AUTOMATION_QUEUE,
                        {"automation_run_id": run.automation_run_id},
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "AI automation startup redelivery raised for run {}",
                        run.automation_run_id,
                    )
                    published = False
                if not published:
                    latest_checkpoint = await automation_repository.latest_checkpoint(
                        run.automation_run_id
                    )
                    await automation_repository.transition_with_checkpoint(
                        run.automation_run_id,
                        run.revision,
                        {
                            "status": AutomationStatus.DEGRADED,
                            "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                        },
                        phase=AutomationCheckpointPhase.FINALIZED,
                        detail={
                            "reason_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                            "retryable": True,
                        },
                        state_snapshot=(
                            latest_checkpoint.state_snapshot if latest_checkpoint else None
                        ),
                    )
            else:
                logger.warning(
                    "Interrupted AI automation cannot be replayed safely run_id={} error_code={}",
                    run.automation_run_id,
                    run.error_code,
                )

    async def _supervise_consumer(self) -> None:
        """Keep the durable queue consumer alive after an unexpected exit."""
        while not self._stopping:
            try:
                await self._consume()
            except asyncio.CancelledError:
                if self._stopping:
                    raise
                logger.warning("AI automation consumer was cancelled unexpectedly; restarting")
            except Exception:
                logger.exception("AI automation consumer exited unexpectedly; restarting")
            if not self._stopping:
                await asyncio.sleep(1)

    async def stop(self) -> None:
        self._stopping = True
        for task_name in ("_task", "_startup_recovery_task"):
            task = getattr(self, task_name)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                setattr(self, task_name, None)

    async def _consume(self) -> None:
        while not self._stopping:
            try:
                message = await mq.consume(AUTOMATION_QUEUE, timeout=5)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("AI automation worker could not receive a message")
                await self._retry_queue_unavailable_runs()
                await asyncio.sleep(1)
                continue
            if not message:
                await self._retry_queue_unavailable_runs()
                await asyncio.sleep(0.25)
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
            await self._retry_queue_unavailable_runs()

    async def _retry_queue_unavailable_runs(self) -> None:
        await self._recover_expired_running_runs()
        loop_now = asyncio.get_running_loop().time()
        if loop_now - self._last_queue_retry_scan < limits.queue_retry_scan_seconds:
            return
        self._last_queue_retry_scan = loop_now
        try:
            await mcp_repository.recover_interrupted_call_audits()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI automation worker could not recover interrupted MCP audit records")
        now = datetime.now(timezone.utc)
        await self._dispatch_stale_queued_runs(now)
        base_delay = max(1, limits.queue_retry_base_seconds)
        try:
            candidates = await automation_repository.list_retryable_queue_runs(
                now - timedelta(seconds=base_delay)
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI automation worker could not scan queue failures for recovery")
            return
        for run in candidates:
            try:
                dispatch_failures = await automation_repository.count_retry_checkpoints(
                    run.automation_run_id
                )
                latest_checkpoint = await automation_repository.latest_checkpoint(
                    run.automation_run_id
                )
                resume_snapshot = (
                    latest_checkpoint.state_snapshot if latest_checkpoint else None
                )
                if run.automatic_retry_count >= limits.retries:
                    continue
                delay = _automation_retry_delay_seconds(dispatch_failures)
                last_updated = run.updated_at
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                if now - last_updated < timedelta(seconds=delay):
                    continue

                queued = await automation_repository.transition_with_checkpoint(
                    run.automation_run_id,
                    run.revision,
                    {
                        "status": AutomationStatus.QUEUED,
                        "error_code": None,
                        "automatic_retry_count": run.automatic_retry_count + 1,
                    },
                    phase=AutomationCheckpointPhase.QUEUED,
                    detail={
                        "reason_code": "AUTOMATION_QUEUE_REDELIVERY",
                        "dispatch_attempt": dispatch_failures + 1,
                    },
                    state_snapshot=resume_snapshot,
                )
                if not queued:
                    continue

                try:
                    published = await mq.publish(
                        AUTOMATION_QUEUE,
                        {"automation_run_id": queued.automation_run_id},
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "AI automation queue redelivery raised for run {}",
                        queued.automation_run_id,
                    )
                    published = False
                if published:
                    continue

                await automation_repository.transition_with_checkpoint(
                    queued.automation_run_id,
                    queued.revision,
                    {
                        "status": AutomationStatus.DEGRADED,
                        "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                    },
                    phase=AutomationCheckpointPhase.FINALIZED,
                    detail={
                        "reason_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                        "retryable": True,
                        "dispatch_attempt": dispatch_failures + 1,
                    },
                    state_snapshot=resume_snapshot,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "AI automation recovery failed for run {}",
                    run.automation_run_id,
                )

    async def _dispatch_stale_queued_runs(self, now: datetime) -> None:
        dispatch_window = max(1, limits.message_ack_timeout_seconds)
        try:
            runs = await automation_repository.claim_stale_queued_runs(
                now - timedelta(seconds=dispatch_window),
                now + timedelta(seconds=dispatch_window),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI automation worker could not claim stale queued runs")
            return

        for run in runs:
            try:
                published = await mq.publish(
                    AUTOMATION_QUEUE,
                    {"automation_run_id": run.automation_run_id},
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "AI automation stale queued dispatch raised for run {}",
                    run.automation_run_id,
                )
                published = False
            if published:
                continue
            checkpoint = await automation_repository.latest_checkpoint(
                run.automation_run_id
            )
            await automation_repository.transition_with_checkpoint(
                run.automation_run_id,
                run.revision,
                {
                    "status": AutomationStatus.DEGRADED,
                    "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                    "queue_dispatch_lease_expires_at": None,
                },
                phase=AutomationCheckpointPhase.FINALIZED,
                detail={
                    "reason_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                    "retryable": True,
                    "recovered_stale_queued_dispatch": True,
                },
                state_snapshot=checkpoint.state_snapshot if checkpoint else None,
            )

    async def _recover_expired_running_runs(self) -> None:
        loop_now = asyncio.get_running_loop().time()
        if loop_now - self._last_expired_run_recovery_scan < limits.queue_retry_scan_seconds:
            return
        self._last_expired_run_recovery_scan = loop_now
        try:
            cursor = None
            while True:
                recovered = await automation_repository.recover_interrupted_runs(
                    include_queued=False,
                    include_legacy_running=False,
                    after_automation_run_id=cursor,
                    limit=limits.automation_recovery_batch_size,
                )
                if not recovered:
                    break
                await self._dispatch_recovered_runs(recovered)
                cursor = recovered[-1].automation_run_id
                if len(recovered) < limits.automation_recovery_batch_size:
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI automation worker could not recover expired run leases")

    async def _record_worker_failure(self, payload: dict) -> bool:
        automation_run_id = str(payload.get("automation_run_id") or "")
        if not automation_run_id:
            return True
        run = await automation_repository.get_run(automation_run_id)
        if not run or run.status != AutomationStatus.QUEUED:
            return True
        latest_checkpoint = await automation_repository.latest_checkpoint(automation_run_id)
        action_outcome_uncertain = bool(
            latest_checkpoint
            and latest_checkpoint.phase == AutomationCheckpointPhase.ACTION_STARTED
            and (
                latest_checkpoint.detail.get("action") != "READ"
                or latest_checkpoint.detail.get("task_has_mutation") is True
            )
        )
        resumable = bool(
            latest_checkpoint
            and latest_checkpoint.state_snapshot is not None
            and not action_outcome_uncertain
        )
        automatic_retry_count = run.automatic_retry_count + 1
        values = {
            "status": (
                AutomationStatus.DEGRADED
                if resumable and automatic_retry_count <= limits.retries
                else AutomationStatus.FAILED
            ),
            "worker_lease_expires_at": None,
            "error_code": (
                "AUTOMATION_ACTION_OUTCOME_UNCERTAIN"
                if action_outcome_uncertain
                else "AUTOMATION_WORKER_RETRYABLE"
                if resumable and automatic_retry_count <= limits.retries
                else "AUTOMATION_WORKER_FAILED"
            ),
            "automatic_retry_count": automatic_retry_count,
        }
        if action_outcome_uncertain:
            updated = await automation_repository.transition_with_checkpoint(
                automation_run_id,
                run.revision,
                values,
                phase=latest_checkpoint.phase,
                detail={
                    **latest_checkpoint.detail,
                    "reason_code": "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
                    "retryable": False,
                },
                state_snapshot=latest_checkpoint.state_snapshot,
            )
        else:
            updated = await automation_repository.transition_with_checkpoint(
                automation_run_id,
                run.revision,
                values,
                phase=AutomationCheckpointPhase.FINALIZED,
                detail={
                    "reason_code": values["error_code"],
                    "resumable": resumable,
                    "automatic_retry_count": automatic_retry_count,
                    "retryable": values["error_code"] == "AUTOMATION_WORKER_RETRYABLE",
                },
                state_snapshot=(
                    latest_checkpoint.state_snapshot if latest_checkpoint else None
                ),
            )
        return updated is not None

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
            await self._await_authorization(run, reason_code)
            return
        try:
            live_role, live_permissions = await project_access(
                run.project_id,
                token,
                run.automation_run_id,
                preferred_role=run.execution_role,
            )
        except Exception:
            logger.exception("AI automation principal is no longer authorized")
            await self._await_authorization(run, "AUTOMATION_PRINCIPAL_UNAVAILABLE")
            return
        expected_role = run.execution_role
        if live_role != expected_role:
            await self._await_authorization(run, "AUTOMATION_PRINCIPAL_ROLE_CHANGED")
            return
        latest_checkpoint = await automation_repository.latest_checkpoint(automation_run_id)
        snapshot = latest_checkpoint.state_snapshot if latest_checkpoint else None
        resume_phase = snapshot.completed_phase.value if snapshot else None
        if snapshot and (
            snapshot.run.run_id != automation_run_id
            or snapshot.run.project_id != run.project_id
            or snapshot.run.user_id != (run.execution_user_id or run.requester_user_id)
            or snapshot.run.role != live_role
        ):
            await self._fail(
                automation_run_id,
                run.revision,
                "AUTOMATION_CHECKPOINT_IDENTITY_MISMATCH",
            )
            return
        agent_run = resume_run_with_live_permissions(snapshot, live_permissions) or VeriqRunState(
            run_id=run.automation_run_id,
            project_id=run.project_id,
            user_id=run.execution_user_id or run.requester_user_id,
            role=live_role,
            source_event_id=run.source_event_id,
            permissions=live_permissions,
            objective=run.objective,
            intent=run.intent,
            intent_arguments=run.intent_arguments,
            model_metadata=model_metadata(),
        )
        graph_state = (
            snapshot.model_dump(mode="python")
            if snapshot
            else {
                "automatic": True,
                "run": agent_run.model_dump(mode="python"),
                "evidence": [item.model_dump(mode="python") for item in run.evidence],
                "target_artifact_ids": run.target_artifact_ids,
                "constraints": run.constraints,
                "source_event_verified": run.source_event_verified,
                "tasks": [],
                "results": [],
            }
        )
        graph_state["run"] = agent_run.model_dump(mode="python")
        graph_state["token"] = ""
        graph_state["automatic"] = True
        graph_state["constraints"] = {
            **graph_state.get("constraints", {}),
            "change_simulation": run.kind == AutomationKind.CHANGE_SIMULATION,
            **(
                {"change_simulation_input": run.change_simulation.model_dump(mode="json")}
                if run.change_simulation
                else {}
            ),
        }
        graph_state["resume_after_phase"] = resume_phase
        graph_state["worker_revision"] = run.revision + 1
        recovery_snapshot = AutomationGraphSnapshot.model_validate(
            {
                key: value
                for key, value in graph_state.items()
                if key in AutomationGraphSnapshot.model_fields and key != "completed_phase"
            }
            | {
                "completed_phase": (
                    snapshot.completed_phase if snapshot else AutomationCheckpointPhase.QUEUED
                )
            }
        )
        trace_id = str(uuid4())
        running = await automation_repository.transition_with_checkpoint(
            automation_run_id,
            run.revision,
            {
                "status": AutomationStatus.RUNNING,
                "error_code": None,
                "queue_dispatch_lease_expires_at": None,
                "execution_permissions": live_permissions,
                "trace_id": trace_id,
                "worker_lease_expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=limits.message_ack_timeout_seconds),
            },
            phase=AutomationCheckpointPhase.WORKER_STARTED,
            detail={
                "reason_code": "AUTOMATION_WORKER_CLAIMED",
                "resume_after_phase": resume_phase,
            },
            state_snapshot=recovery_snapshot,
        )
        if not running:
            return
        execution_token = await automation_service.token_for(
            automation_run_id, worker_revision=running.revision
        )
        if not execution_token:
            await self._fail(
                automation_run_id,
                running.revision,
                "AUTHORIZATION_EXPIRED",
                require_live_worker_lease=True,
            )
            return
        graph_state["token"] = f"Bearer {execution_token}"
        graph_state["worker_revision"] = running.revision
        recovery_snapshot.worker_revision = running.revision
        agentops.record_session_start(agent_run.run_id, running.requester_user_id)
        try:
            from src.core.infrastructure.observability import trace_span

            with trace_span(
                "automation.run",
                {
                    "automation.run_id": running.automation_run_id,
                    "automation.kind": running.kind.value,
                    "automation.trigger": running.trigger.value if running.trigger else "ON_DEMAND",
                },
            ) as automation_span:
                try:
                    result = await asyncio.wait_for(
                        automation_workflow.ainvoke(
                            graph_state,
                            config={
                                "run_id": UUID(trace_id),
                                "run_name": "veriq-ai-automation",
                                "tags": ["veriq", "automation", running.kind.value],
                                "metadata": {
                                    "automation_kind": running.kind.value,
                                    "trigger": running.trigger.value if running.trigger else "ON_DEMAND",
                                },
                            },
                        ),
                        timeout=limits.run_timeout_seconds,
                    )
                except asyncio.CancelledError:
                    if automation_span is not None:
                        automation_span.set_attribute("event.status", "cancelled")
                    raise
                except Exception:
                    if automation_span is not None:
                        automation_span.set_attribute("event.status", "failed")
                    raise
                graph_status = str(
                    ((result.get("run") or {}).get("status") or "")
                ).strip().lower()
                if graph_status not in {
                    "queued",
                    "running",
                    "awaiting_authorization",
                    "awaiting_input",
                    "completed",
                    "degraded",
                    "failed",
                    "cancelled",
                }:
                    graph_status = "failed"
                if automation_span is not None:
                    automation_span.set_attribute("event.status", graph_status)
            completed = VeriqRunState(**result["run"])
            terminal_status = terminal_status_for_agent_run(completed)
            authorization_error = None
            try:
                final_role, final_permissions = await project_access(
                    running.project_id,
                    execution_token,
                    running.automation_run_id,
                    preferred_role=running.execution_role,
                )
                if final_role != running.execution_role:
                    authorization_error = "AUTOMATION_PRINCIPAL_ROLE_CHANGED"
                elif "project.read" not in final_permissions:
                    authorization_error = "PROJECT_ACCESS_REVOKED_DURING_RUN"
            except HTTPException as error:
                detail = error.detail
                authorization_error = (
                    detail.get("code")
                    if isinstance(detail, dict) and detail.get("code")
                    else "PROJECT_ACCESS_REVOKED_DURING_RUN"
                )
            except Exception:
                logger.exception("AI automation could not revalidate its principal after execution")
                authorization_error = "PROJECT_AUTHORIZATION_CHECK_FAILED"
            if authorization_error:
                completed.status = AgentRunStatus.FAILED
                completed.error_code = authorization_error
                terminal_status = AutomationStatus.AWAITING_AUTHORIZATION
            source_evidence = [
                item.model_dump(mode="json")
                for item in running.evidence
            ]
            source_evidence.extend(
                item for item in result.get("evidence", []) if isinstance(item, dict)
            )
            for observation in completed.observations:
                if (
                    observation.get("tool_name") not in {
                        "process_ingested_requirement_document",
                        "process_changed_requirement_version",
                    }
                    or observation.get("status") != "COMPLETED"
                    or (observation.get("verification") or {}).get("status") != "COMPLETED"
                ):
                    continue
                source_evidence.extend(
                    item
                    for item in (observation.get("result") or {}).get("source_evidence", [])
                    if isinstance(item, dict)
                )
            downstream_handoffs = (
                await self._enqueue_requirement_test_design_handoffs(running, completed)
                if not authorization_error
                else []
            )
            if not authorization_error:
                downstream_handoffs.extend(
                    await self._enqueue_requirement_change_simulation(
                        running, execution_token
                    )
                )
            handoff_blocked = any(
                item.get("workflow_type") != "CHANGE_SIMULATION"
                and item.get("status") not in {"QUEUED", "RUNNING", "COMPLETED"}
                for item in downstream_handoffs
            )
            if handoff_blocked and terminal_status == AutomationStatus.COMPLETED:
                terminal_status = AutomationStatus.DEGRADED
                completed.error_code = "QA_TEST_DESIGN_HANDOFF_PENDING"
            raw_source_facts = [
                item
                for item in result.get("source_facts", [])
                if isinstance(item, dict)
            ]
            source_facts = []
            for item in raw_source_facts:
                verified = verified_source_span(item, source_evidence)
                if not verified:
                    continue
                quote = str(verified["quote"])
                source_facts.append(SourceFact(
                    source_fact_id=(
                        "FACT-"
                        + hashlib.sha256(
                            "|".join(
                                (
                                    automation_run_id,
                                    str(item.get("artifact_type") or "artifact"),
                                    str(item.get("artifact_id") or ""),
                                    str(item.get("artifact_version_id") or ""),
                                    str(verified["source_start"]),
                                    str(verified["source_end"]),
                                    quote,
                                )
                            ).encode("utf-8")
                        ).hexdigest()[:32]
                    ),
                    automation_run_id=automation_run_id,
                    project_id=running.project_id,
                    artifact_type=str(verified.get("artifact_type") or "artifact"),
                    artifact_id=str(verified["artifact_id"]),
                    artifact_version_id=str(verified["artifact_version_id"]),
                    source_start=verified["source_start"],
                    source_end=verified["source_end"],
                    source=str(verified.get("source") or "database"),
                    authority=str(verified.get("authority") or "project"),
                    relationship_path=list(verified.get("relationship_path") or []),
                    quote=quote,
                    fact_kind=str(verified.get("fact_kind") or "source_evidence"),
                    quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                    source_chunk_id=verified.get("source_chunk_id"),
                    source_chunk_index=verified.get("source_chunk_index"),
                    source_chunk_type=verified.get("source_chunk_type"),
                    source_page_numbers=list(verified.get("source_page_numbers") or []),
                    source_spans=list(verified.get("source_spans") or []),
                    source_hash=verified.get("source_hash"),
                    source_offset_basis=verified.get("source_offset_basis", "UNKNOWN"),
                ))
            rejected_source_fact_count = len(raw_source_facts) - len(source_facts)
            seen_facts = {
                source_fact_identity(fact.model_dump(mode="python"))
                for fact in source_facts
            }
            for observation in completed.observations:
                if (
                    observation.get("tool_name") not in {
                        "process_ingested_requirement_document",
                        "process_changed_requirement_version",
                    }
                    or observation.get("status") != "COMPLETED"
                    or (observation.get("verification") or {}).get("status") != "COMPLETED"
                ):
                    continue
                operation_result = observation.get("result") or {}
                for item in operation_result.get("source_facts", []):
                    verified = verified_source_span(item, source_evidence)
                    if not verified:
                        rejected_source_fact_count += 1
                        continue
                    quote = str(verified["quote"])
                    artifact_id = str(verified["artifact_id"])
                    fact_data = {
                        **verified,
                        "artifact_type": str(verified.get("artifact_type") or "artifact"),
                        "artifact_id": artifact_id,
                    }
                    key = source_fact_identity(fact_data)
                    if key in seen_facts:
                        continue
                    seen_facts.add(key)
                    source_facts.append(
                        SourceFact(
                            automation_run_id=automation_run_id,
                            project_id=running.project_id,
                            artifact_type=fact_data["artifact_type"],
                            artifact_id=artifact_id,
                            artifact_version_id=str(verified["artifact_version_id"]),
                            source=str(verified.get("source") or "document"),
                            authority=str(verified.get("authority") or "project"),
                            relationship_path=list(verified.get("relationship_path") or []),
                            quote=quote,
                            fact_kind=str(verified.get("fact_kind") or "source_evidence"),
                            quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                            source_start=verified["source_start"],
                            source_end=verified["source_end"],
                            source_chunk_id=verified.get("source_chunk_id"),
                            source_chunk_index=verified.get("source_chunk_index"),
                            source_chunk_type=verified.get("source_chunk_type"),
                            source_page_numbers=list(verified.get("source_page_numbers") or []),
                            source_spans=list(verified.get("source_spans") or []),
                            source_hash=verified.get("source_hash"),
                            source_offset_basis=verified.get("source_offset_basis", "UNKNOWN"),
                        )
                    )
            source_facts = [
                SourceFact.model_validate(fact)
                for fact in canonicalize_source_facts(
                    [fact.model_dump(mode="python") for fact in source_facts],
                    source_evidence,
                )
            ]
            verified_outputs = self._verified_output_refs(completed)
            all_verified_refs = set(completed.evidence_refs)
            verified_outputs = list(
                dict.fromkeys(
                    [
                        *verified_outputs,
                        *[
                            str(item.get("evidence_ref"))
                            for item in completed.observations
                            if item.get("evidence_ref") in all_verified_refs
                        ],
                    ]
                )
            )
            facts_by_ref = {}
            for fact in source_facts:
                facts_by_ref.setdefault(fact.artifact_id, []).append(fact)
                if fact.artifact_version_id:
                    facts_by_ref.setdefault(fact.artifact_version_id, []).append(fact)
            lineage_by_ref = {
                reference: list(dict.fromkeys(fact.source_fact_id for fact in facts))
                for reference, facts in facts_by_ref.items()
            }
            derivation_steps = []
            unlinked_mutation_count = 0
            testability_blueprint, rejected_blueprint_count = (
                verified_blueprint_from_observations(
                    completed.observations,
                    source_facts,
                    project_id=running.project_id,
                    automation_run_id=automation_run_id,
                )
            )
            blueprint_claim_lineage = verified_blueprint_claim_lineage(
                testability_blueprint,
                source_facts,
                project_id=running.project_id,
                automation_run_id=automation_run_id,
            )
            if testability_blueprint is not None and blueprint_claim_lineage is None:
                rejected_blueprint_count += 1
                testability_blueprint = None
                blueprint_claim_lineage = []
            blueprint_artifact_lineage, rejected_artifact_lineage_count = (
                verified_blueprint_artifact_lineage(
                    testability_blueprint,
                    blueprint_claim_lineage,
                    completed.observations,
                    running.project_id,
                )
            )
            rejected_blueprint_count += rejected_artifact_lineage_count
            unmapped_blueprint_obligation_count = missing_blueprint_artifact_coverage_count(
                testability_blueprint, blueprint_artifact_lineage
            )
            if source_facts:
                derivation_steps.append(
                    DerivationStep(
                        name="SOURCE_FACT_EXTRACTION",
                        source_fact_ids=[fact.source_fact_id for fact in source_facts],
                        input_artifact_refs=list(
                            dict.fromkeys(
                                fact.artifact_version_id or fact.artifact_id
                                for fact in source_facts
                            )
                        ),
                        input_artifact_version_ids=list(
                            dict.fromkeys(
                                fact.artifact_version_id
                                for fact in source_facts
                                if fact.artifact_version_id
                            )
                        ),
                        output_evidence_refs=list(
                            dict.fromkeys(
                                fact.artifact_version_id or fact.artifact_id
                                for fact in source_facts
                            )
                        ),
                        output_artifact_version_ids=list(
                            dict.fromkeys(
                                fact.artifact_version_id
                                for fact in source_facts
                                if fact.artifact_version_id
                            )
                        ),
                        verification_status="VERIFIED_EXACT_SOURCE_QUOTE",
                    )
                )
            matched_tool_calls = tool_call_records_for_observations(
                completed.tool_calls, completed.observations
            )
            for observation_index, observation in enumerate(completed.observations):
                tool_name = observation.get("tool_name")
                if not tool_name:
                    continue
                record = matched_tool_calls[observation_index]
                task = next(
                    (
                        item for item in completed.completed_tasks
                        if item.get("task_id") == record.get("task_id")
                    ),
                    {},
                )
                input_refs = list(
                    dict.fromkeys(
                        [
                            *(task.get("evidence_refs") or []),
                            *[
                                str(value)
                                for key, value in (record.get("arguments") or {}).items()
                                if key.endswith("_id") and value
                            ],
                        ]
                    )
                )
                verification = observation.get("verification") or {}
                verified_mutation = (
                    record.get("mutation_fingerprint") is not None
                    and verification.get("status") == "COMPLETED"
                    and verification.get("reason_code") != "SAFE_NO_MUTATION_OUTCOME"
                )
                evidence_ref = observation.get("evidence_ref")
                output_refs = []
                if evidence_ref and evidence_ref in all_verified_refs:
                    output_refs.append(str(evidence_ref))
                if verified_mutation:
                    output_refs.extend(
                        str(value)
                        for value in verification.get("artifact_ids", [])
                        if value
                    )
                    if verification.get("artifact_id"):
                        output_refs.append(str(verification["artifact_id"]))
                output_refs = list(dict.fromkeys(output_refs))
                input_fact_ids = carry_source_fact_lineage(
                    input_refs,
                    output_refs,
                    lineage_by_ref,
                )
                control_event_refs = (
                    verified_release_gate_mutation_refs(
                        automatic=True,
                        source_event_verified=running.source_event_verified,
                        trigger=str((running.constraints or {}).get("trigger") or ""),
                        project_id=running.project_id,
                        source_event_id=running.source_event_id,
                        control_evidence=source_evidence,
                        tool_name=str(tool_name),
                        arguments=record.get("arguments") or {},
                        input_refs=input_refs,
                        output_refs=output_refs,
                    )
                    if verified_mutation
                    else []
                )
                if verified_mutation and output_refs and not input_fact_ids and not control_event_refs:
                    unlinked_mutation_count += 1
                output_versions = list(
                    dict.fromkeys(
                        fact.artifact_version_id
                        for output_ref in output_refs
                        for fact in facts_by_ref.get(output_ref, [])
                        if fact.artifact_version_id
                    )
                )
                derivation_steps.append(
                    DerivationStep(
                        name="TOOL_TRANSFORMATION",
                        source_fact_ids=input_fact_ids,
                        control_event_refs=control_event_refs,
                        input_artifact_refs=input_refs,
                        input_artifact_version_ids=list(
                            dict.fromkeys(
                                fact.artifact_version_id
                                for reference in input_refs
                                for fact in facts_by_ref.get(reference, [])
                                if fact.artifact_version_id
                            )
                        ),
                        output_evidence_refs=output_refs,
                        output_artifact_version_ids=output_versions,
                        tool_name=str(tool_name),
                        verification_status=(
                            "VERIFIED_POSTCONDITION"
                            if verified_mutation
                            else "OBSERVED_AND_EVIDENCE_CHECKED"
                            if evidence_ref in all_verified_refs
                            else str(observation.get("status") or "UNVERIFIED")
                        ),
                        reason_code=observation.get("reason_code"),
                    )
                )
            if terminal_status == AutomationStatus.COMPLETED and has_provenance_gap(
                rejected_source_fact_count,
                unlinked_mutation_count,
                rejected_blueprint_count,
                unmapped_blueprint_obligation_count,
            ):
                terminal_status = AutomationStatus.DEGRADED
                completed.error_code = "DERIVATION_RECEIPT_INCOMPLETE"
            transformation_steps = list(
                dict.fromkeys(
                    [
                        *(step.name for step in derivation_steps[:1]),
                        *(str(item.get("tool_name")) for item in completed.tool_calls if item.get("tool_name")),
                    ]
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
                        steps=derivation_steps,
                        output_evidence_refs=verified_outputs,
                        testability_blueprint=testability_blueprint,
                        blueprint_claim_lineage=blueprint_claim_lineage,
                        blueprint_artifact_lineage=blueprint_artifact_lineage,
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
                    require_live_worker_lease=True,
                )
                agentops.record_session_end(completed.run_id, "failed")
                return

            final_snapshot = None
            if terminal_status in {
                AutomationStatus.AWAITING_INPUT,
                AutomationStatus.AWAITING_AUTHORIZATION,
            }:
                latest_checkpoint = await automation_repository.latest_checkpoint(
                    automation_run_id
                )
                final_snapshot = latest_checkpoint.state_snapshot if latest_checkpoint else None
            finalized_detail = {
                "agent_run_id": completed.run_id,
                "error_code": completed.error_code,
                "provenance_rejections": {
                    "source_facts": rejected_source_fact_count,
                    "unlinked_mutations": unlinked_mutation_count,
                    "testability_blueprints": rejected_blueprint_count,
                },
            }
            updated = await automation_repository.transition_with_checkpoint(
                automation_run_id,
                running.revision,
                {
                    "status": terminal_status,
                    "worker_lease_expires_at": None,
                    "agent_run_id": completed.run_id,
                    "result": {
                        "proposal": completed.proposal,
                        "evidence_refs": completed.evidence_refs,
                        "observations": completed.observations,
                        "downstream_workflows": downstream_handoffs,
                        "error_code": completed.error_code,
                        "provenance_rejections": {
                            "source_facts": rejected_source_fact_count,
                            "unlinked_mutations": unlinked_mutation_count,
                            "testability_blueprints": rejected_blueprint_count,
                        },
                    },
                    "error_code": completed.error_code,
                },
                phase=AutomationCheckpointPhase.FINALIZED,
                detail=finalized_detail,
                state_snapshot=final_snapshot,
                require_live_worker_lease=True,
            )
            if not updated:
                agentops.record_session_end(completed.run_id, "failed")
                return
            try:
                await run_store.save(completed)
                if terminal_status == AutomationStatus.COMPLETED:
                    await long_term_memory.record_verified(completed)
            except Exception:
                logger.exception(
                    "AI automation completed but optional agent memory could not be persisted"
                )
            agentops.record_session_end(
                completed.run_id,
                "done"
                if terminal_status == AutomationStatus.COMPLETED
                else "waiting_input"
                if terminal_status == AutomationStatus.AWAITING_INPUT
                else "failed",
            )
        except TimeoutError:
            await self._fail(
                automation_run_id,
                running.revision,
                "AUTOMATION_LIMIT_REACHED",
                require_live_worker_lease=True,
            )
            agentops.record_session_end(agent_run.run_id, "failed")
        except Exception:
            logger.exception("AI automation graph execution failed")
            await self._fail(
                automation_run_id,
                running.revision,
                "AUTOMATION_EXECUTION_FAILED",
                require_live_worker_lease=True,
            )
            agentops.record_session_end(agent_run.run_id, "failed")

    async def _await_authorization(self, run: AutomationRun, reason_code: str) -> None:
        await automation_repository.transition_with_checkpoint(
            run.automation_run_id,
            run.revision,
            {
                "status": AutomationStatus.AWAITING_AUTHORIZATION,
                "error_code": reason_code,
                "worker_lease_expires_at": None,
            },
            phase=AutomationCheckpointPhase.FINALIZED,
            detail={"reason_code": reason_code},
            state_snapshot=None,
        )

    async def _fail(
        self,
        automation_run_id: str,
        revision: int,
        code: str,
        *,
        require_live_worker_lease: bool = False,
    ) -> None:
        latest_checkpoint = await automation_repository.latest_checkpoint(automation_run_id)
        action_outcome_uncertain = bool(
            latest_checkpoint
            and latest_checkpoint.phase == AutomationCheckpointPhase.ACTION_STARTED
            and (
                latest_checkpoint.detail.get("action") != "READ"
                or latest_checkpoint.detail.get("task_has_mutation") is True
            )
        )
        effective_code = (
            "AUTOMATION_ACTION_OUTCOME_UNCERTAIN"
            if action_outcome_uncertain
            else code
        )
        resume_snapshot = (
            None
            if code == "AUTOMATION_CHECKPOINT_IDENTITY_MISMATCH"
            else latest_checkpoint.state_snapshot
            if latest_checkpoint
            else None
        )
        values = {
            "status": AutomationStatus.FAILED,
            "error_code": effective_code,
            "worker_lease_expires_at": None,
        }
        if action_outcome_uncertain:
            await automation_repository.transition_with_checkpoint(
                automation_run_id,
                revision,
                values,
                phase=latest_checkpoint.phase,
                detail={
                    **latest_checkpoint.detail,
                    "reason_code": "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
                    "retryable": False,
                },
                state_snapshot=latest_checkpoint.state_snapshot,
                require_live_worker_lease=require_live_worker_lease,
            )
            return
        await automation_repository.transition_with_checkpoint(
            automation_run_id,
            revision,
            values,
            phase=AutomationCheckpointPhase.FINALIZED,
            detail={"reason_code": code, "resumable": resume_snapshot is not None},
            state_snapshot=resume_snapshot,
            require_live_worker_lease=require_live_worker_lease,
        )

    async def _enqueue_requirement_test_design_handoffs(self, running, completed):
        if running.trigger != AutomationTrigger.DOCUMENT_INGESTED:
            return []
        ingestion = next(
            (
                item
                for item in completed.observations
                if item.get("tool_name") == "process_ingested_requirement_document"
                and item.get("status") == "COMPLETED"
                and (item.get("verification") or {}).get("status") == "COMPLETED"
            ),
            None,
        )
        if not ingestion:
            return []
        result = ingestion.get("result") or {}
        if result.get("status") != "COMPLETED":
            return []
        evidence_by_version = {
            str(item.get("artifact_version_id")): item
            for item in result.get("qa_test_design_handoff_evidence", [])
            if isinstance(item, dict) and item.get("artifact_version_id")
        }
        workflows = []
        for version_id in dict.fromkeys(
            str(value)
            for value in result.get("qa_test_design_handoff_version_ids", [])
            if value
        ):
            source = evidence_by_version.get(version_id)
            if not source or not str(source.get("text") or "").strip():
                workflows.append(
                    {
                        "requirement_version_id": version_id,
                        "status": "EVIDENCE_MISSING",
                        "reason_code": "QA_TEST_DESIGN_SOURCE_EVIDENCE_MISSING",
                    }
                )
                continue
            evidence = [
                EvidenceItem(
                    artifact_type=str(source.get("artifact_type") or "requirement_version"),
                    artifact_id=str(source.get("artifact_id") or version_id),
                    artifact_version_id=str(source.get("artifact_version_id") or version_id),
                    source="database",
                    authority=str(source.get("authority") or "PROJECT_REQUIREMENT"),
                    text=str(source["text"]),
                    project_id=running.project_id,
                )
            ]
            event = AutomationEventRequest(
                event_id=f"requirement-version:{version_id}:INGESTED_TEST_DESIGN",
                project_id=running.project_id,
                requester_user_id=running.requester_user_id,
                trigger=AutomationTrigger.REQUIREMENT_CHANGED,
                parent_automation_run_id=running.automation_run_id,
                target_artifact_ids=[version_id],
                evidence=evidence,
            )
            try:
                child_runs = await automation_service.enqueue_event(event)
            except Exception:
                logger.exception(
                    "Could not enqueue QA test-design handoff parent_run={} requirement_version={}",
                    running.automation_run_id,
                    version_id,
                )
                workflows.append(
                    {
                        "requirement_version_id": version_id,
                        "status": "DISPATCH_FAILED",
                        "reason_code": "QA_TEST_DESIGN_HANDOFF_DISPATCH_FAILED",
                    }
                )
                continue
            workflows.extend(
                {
                    "requirement_version_id": version_id,
                    "automation_run_id": child.automation_run_id,
                    "status": child.status.value,
                    "reason_code": child.error_code,
                }
                for child in child_runs
            )
        return workflows

    async def _enqueue_requirement_change_simulation(self, running, execution_token):
        if (
            running.trigger != AutomationTrigger.REQUIREMENT_CHANGED
            or getattr(running, "kind", None) == AutomationKind.CHANGE_SIMULATION
            or getattr(running, "change_simulation", None) is not None
        ):
            return []
        constraints = running.constraints if isinstance(running.constraints, dict) else {}
        current_version_id = next(
            (
                str(item.artifact_version_id or item.artifact_id)
                for item in running.evidence
                if item.artifact_type == "requirement_version"
                and (item.artifact_version_id or item.artifact_id)
                in running.target_artifact_ids
            ),
            "",
        )
        prior_version_id = str(constraints.get("prior_baseline_version_id") or "")
        blocked_reason = str(constraints.get("change_simulation_blocked_reason") or "")
        workflow = {
            "workflow_type": "CHANGE_SIMULATION",
            "requirement_version_id": current_version_id or None,
        }
        if blocked_reason or not prior_version_id:
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": blocked_reason or "PRIOR_BASELINE_REFERENCE_MISSING",
                }
            ]
        if not current_version_id or current_version_id == prior_version_id:
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": "REQUIREMENT_VERSION_PAIR_INVALID",
                }
            ]

        config = {
            "configurable": {
                "token": f"Bearer {execution_token}",
                "project_id": running.project_id,
                "automation_run_id": running.automation_run_id,
            }
        }
        try:
            prior = await require_operation(
                "GET", f"/phien-ban-yeu-cau/{prior_version_id}", config
            )
            current = await require_operation(
                "GET", f"/phien-ban-yeu-cau/{current_version_id}", config
            )
            requirement_id = str(current.get("requirement_id") or "")
            if not requirement_id:
                raise AutomationOperationError("REQUIREMENT_ID_MISSING")
            requirement = await require_operation(
                "GET", f"/yeu-cau/{requirement_id}", config
            )
            versions = await require_operation(
                "GET", f"/yeu-cau/{requirement_id}/phien-ban", config
            )
        except Exception:
            logger.exception(
                "Requirement change simulation pair could not be reread under project authorization"
            )
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": "REQUIREMENT_VERSION_PAIR_READBACK_FAILED",
                }
            ]

        if (
            not isinstance(prior, dict)
            or not isinstance(current, dict)
            or not isinstance(requirement, dict)
            or not isinstance(versions, list)
            or len(versions) >= 500
            or prior.get("_id") != prior_version_id
            or current.get("_id") != current_version_id
            or prior.get("project_id") != running.project_id
            or current.get("project_id") != running.project_id
            or prior.get("requirement_id") != requirement_id
            or current.get("requirement_id") != requirement_id
            or requirement.get("_id") != requirement_id
            or requirement.get("project_id") != running.project_id
            or not isinstance(requirement.get("current_version"), dict)
            or requirement["current_version"].get("_id") != current_version_id
            or prior.get("status") != "BASELINED"
            or current.get("status") != "BASELINED"
            or type(prior.get("version")) is not int
            or type(current.get("version")) is not int
            or prior.get("version") >= current.get("version")
        ):
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": "REQUIREMENT_VERSION_PAIR_NOT_CURRENT_OR_INVALID",
                }
            ]

        prior_baselines = [
            item
            for item in versions
            if isinstance(item, dict)
            and item.get("status") == "BASELINED"
            and type(item.get("version")) is int
            and item["version"] < current["version"]
        ]
        if not prior_baselines:
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": "PRIOR_BASELINE_NOT_FOUND_IN_HISTORY",
                }
            ]
        latest_prior_number = max(item["version"] for item in prior_baselines)
        latest_prior = [
            item for item in prior_baselines if item["version"] == latest_prior_number
        ]
        if len(latest_prior) != 1 or latest_prior[0].get("_id") != prior_version_id:
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": "PRIOR_BASELINE_IS_NOT_UNIQUE_LATEST",
                }
            ]

        prior_text = self._requirement_version_source_text(prior)
        current_text = self._requirement_version_source_text(current)
        if not prior_text or not current_text:
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": "REQUIREMENT_VERSION_SOURCE_TEXT_MISSING",
                }
            ]
        event_id = (
            f"change-simulation:{running.automation_run_id}:"
            f"{prior_version_id}:{current_version_id}"
        )
        event = AutomationEventRequest(
            event_id=event_id,
            project_id=running.project_id,
            requester_user_id=running.requester_user_id,
            trigger=AutomationTrigger.REQUIREMENT_CHANGED,
            parent_automation_run_id=running.automation_run_id,
            target_artifact_ids=[prior_version_id, current_version_id],
            evidence=[
                EvidenceItem(
                    artifact_type="requirement_version",
                    artifact_id=requirement_id,
                    artifact_version_id=prior_version_id,
                    source="database",
                    authority="requirement",
                    text=prior_text,
                    project_id=running.project_id,
                    artifact_status=prior.get("status"),
                ),
                EvidenceItem(
                    artifact_type="requirement_version",
                    artifact_id=requirement_id,
                    artifact_version_id=current_version_id,
                    source="database",
                    authority="requirement",
                    text=current_text,
                    project_id=running.project_id,
                    artifact_status=current.get("status"),
                ),
            ],
            change_simulation=ChangeSimulationInput(
                base_requirement_version_id=prior_version_id,
                proposed_source_text=current_text,
            ),
        )
        try:
            runs = await automation_service.enqueue_event(event)
        except Exception:
            logger.exception(
                "Requirement change simulation child event could not be enqueued parent_run={}",
                running.automation_run_id,
            )
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": "CHANGE_SIMULATION_CHILD_ENQUEUE_FAILED",
                }
            ]
        if not runs:
            return [
                {
                    **workflow,
                    "status": "WAITING",
                    "reason_code": "CHANGE_SIMULATION_CHILD_SUPPRESSED",
                }
            ]
        child = runs[0]
        return [
            {
                **workflow,
                "automation_run_id": child.automation_run_id,
                "status": child.status.value,
                "reason_code": child.error_code,
                "prior_baseline_version_id": prior_version_id,
                "current_requirement_version_id": current_version_id,
            }
        ]

    @staticmethod
    def _requirement_version_source_text(version):
        parts = []
        projection = str(version.get("plain_text_projection") or "").strip()
        if projection:
            parts.append(projection)
        for item in version.get("acceptance_criteria") or []:
            if isinstance(item, dict):
                text = str(item.get("plain_text") or "").strip()
                if text:
                    parts.append(text)

        def collect(value):
            if isinstance(value, str):
                return [value.strip()] if value.strip() else []
            if isinstance(value, dict):
                return [text for child in value.values() for text in collect(child)]
            if isinstance(value, (list, tuple)):
                return [text for child in value for text in collect(child)]
            return []

        for field in ("business_rules", "actors", "dependencies", "details", "custom_values"):
            parts.extend(collect(version.get(field)))
        return "\n".join(parts)

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
