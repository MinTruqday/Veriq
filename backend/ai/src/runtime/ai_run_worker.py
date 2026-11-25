import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from loguru import logger

from src.agents.runner.ai_run_graph import run_ai_run_graph
from src.agents.runner.agent_validation import tool_call_records_for_observations
from src.core.infrastructure.mq import mq
from src.memory.long_term import long_term_memory
from src.memory.short_term import run_store
from src.repositories.ai_runs import ai_run_repository
from src.runtime.limits import limits
from src.runtime.queue_names import AI_RUN_QUEUE
from src.schemas.agent import AIRunExecutionStatus, VeriqRunState
from src.schemas.ai_runs import (
    AIRunPhase,
    AIRunStateSnapshot,
    AIRunKind,
    AIRun,
    AIRunStatus,
    AIRunTrigger,
    DerivationReceipt,
    DerivationStep,
    AgentUncertainty,
    SourceFact,
)
from src.services.agent_metrics import agentops
from src.services.agent_evidence import verified_tool_evidence_records
from src.services.ai_runs import ai_run_service
from src.services.source_provenance import (
    canonicalize_source_facts,
    carry_source_fact_lineage,
    has_provenance_gap,
    source_fact_identity,
    verified_source_span,
)
from src.services.inference import model_metadata
from src.services.project_access import project_access
from src.tools.registry import registered_tools, tool_access
from src.tools.testing_api import ToolOperationError, require_operation
from src.utils.background import create_background_task


def _dispatch_retry_delay_seconds(dispatch_failures: int) -> int:
    base_delay = limits.queue_retry_base_seconds
    maximum_delay = limits.queue_retry_max_seconds
    if (
        isinstance(dispatch_failures, bool)
        or not isinstance(dispatch_failures, int)
        or dispatch_failures < 0
        or base_delay < 1
        or maximum_delay < base_delay
    ):
        raise ValueError("ai_run_retry_delay_configuration_invalid")
    doublings = max(0, dispatch_failures - 1)
    maximum_doublings = (maximum_delay // base_delay).bit_length()
    return min(base_delay * (1 << min(doublings, maximum_doublings)), maximum_delay)


def terminal_status_for_ai_run(completed: VeriqRunState) -> AIRunStatus:
    if completed.status == AIRunExecutionStatus.COMPLETED:
        return AIRunStatus.COMPLETED
    if completed.error_code == "AI_RUN_WAITING_FOR_INPUT":
        return AIRunStatus.AWAITING_INPUT
    if (
        completed.status == AIRunExecutionStatus.FAILED
        and completed.error_code == "INSUFFICIENT_EVIDENCE"
    ):
        return AIRunStatus.DEGRADED
    if completed.status == AIRunExecutionStatus.FAILED:
        return AIRunStatus.FAILED
    return AIRunStatus.DEGRADED


def action_input_uncertainties(completed: VeriqRunState) -> list[AgentUncertainty]:
    grouped = {}
    for observation in completed.observations:
        if observation.get("status") != "COMPLETED":
            continue
        result = observation.get("result") or {}
        if not isinstance(result, dict) or result.get("status") != "awaiting_input":
            continue
        code = str(result.get("reason_code") or "AI_RUN_USER_INPUT_REQUIRED")
        entry = grouped.setdefault(
            code,
            {"result": result, "evidence_refs": set(), "unresolved": []},
        )
        entry["evidence_refs"].update(
            str(value)
            for value in (result.get("evidence_refs") or [])
            if isinstance(value, str) and value
        )
        entry["unresolved"].extend(
            value
            for value in (result.get("unresolved") or [])
            if isinstance(value, dict)
        )

    uncertainties = []
    for code, entry in grouped.items():
        unresolved = entry["unresolved"]
        references = []
        for item in unresolved:
            for match in item.get("candidate_matches", []):
                if not isinstance(match, dict):
                    continue
                key = str(match.get("requirement_key") or match.get("requirement_id") or "")
                title = str(match.get("title") or "").strip()
                label = " — ".join(value for value in (key, title) if value)
                if label:
                    references.append(label)
        details = list(dict.fromkeys(references))
        reason = str(entry["result"].get("summary") or "").strip()
        if not reason:
            reason = "; ".join(
                str(item.get("reason") or code)
                for item in unresolved
            ) or code
        if details:
            reason = f"{reason} ({'; '.join(details)})"
        uncertainties.append(
            AgentUncertainty(
                code=code,
                reason=reason[:4000],
                evidence_refs=sorted(entry["evidence_refs"]),
                blocking=True,
            )
        )
    return uncertainties


def resume_run_with_live_permissions(snapshot, live_permissions):
    if snapshot is None:
        return None
    return snapshot.run.model_copy(update={"permissions": list(live_permissions)})


class AIRunWorker:
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
            self._supervise_consumer(), "ai-run-worker"
        )
        self._startup_recovery_task = create_background_task(
            self._retry_startup_recovery(startup_cutoff),
            "ai-run-startup-recovery",
        )

    async def _retry_startup_recovery(self, startup_cutoff: datetime) -> None:
        while not self._stopping:
            try:
                cursor = None
                while not self._stopping:
                    runs = await ai_run_repository.recover_interrupted_runs(
                        startup_cutoff,
                        after_ai_run_id=cursor,
                        limit=limits.run_recovery_batch_size,
                    )
                    if not runs:
                        break
                    await self._dispatch_recovered_runs(runs)
                    cursor = runs[-1].ai_run_id
                    if len(runs) < limits.run_recovery_batch_size:
                        break
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "AI run startup recovery failed; retrying without stopping consumer"
                )
                await asyncio.sleep(5)

    async def _dispatch_recovered_runs(self, runs) -> None:
        for run in runs:
            if run.status == AIRunStatus.QUEUED:
                try:
                    published = await mq.publish(
                        AI_RUN_QUEUE,
                        {"ai_run_id": run.ai_run_id},
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "AI run startup redelivery raised for run {}",
                        run.ai_run_id,
                    )
                    published = False
                if not published:
                    latest_checkpoint = await ai_run_repository.latest_checkpoint(
                        run.ai_run_id
                    )
                    await ai_run_repository.transition_with_checkpoint(
                        run.ai_run_id,
                        run.revision,
                        {
                            "status": AIRunStatus.DEGRADED,
                            "error_code": "AI_RUN_QUEUE_UNAVAILABLE",
                        },
                        phase=AIRunPhase.FINALIZED,
                        detail={
                            "reason_code": "AI_RUN_QUEUE_UNAVAILABLE",
                            "retryable": True,
                        },
                        state_snapshot=(
                            latest_checkpoint.state_snapshot if latest_checkpoint else None
                        ),
                    )
            else:
                logger.warning(
                    "Interrupted AI run cannot be replayed safely run_id={} error_code={}",
                    run.ai_run_id,
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
                logger.warning("AI run consumer was cancelled unexpectedly; restarting")
            except Exception:
                logger.exception("AI run consumer exited unexpectedly; restarting")
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
                message = await mq.consume(AI_RUN_QUEUE, timeout=5)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("AI run worker could not receive a message")
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
                logger.exception("AI run worker failed to process a run")
                try:
                    acknowledge = await self._record_worker_failure(message["payload"])
                except Exception:
                    logger.exception("AI run worker could not persist the failed run state")
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
        now = datetime.now(timezone.utc)
        await self._dispatch_stale_queued_runs(now)
        base_delay = max(1, limits.queue_retry_base_seconds)
        try:
            candidates = await ai_run_repository.list_retryable_queue_runs(
                now - timedelta(seconds=base_delay)
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI run worker could not scan queue failures for recovery")
            return
        for run in candidates:
            try:
                dispatch_failures = await ai_run_repository.count_retry_checkpoints(
                    run.ai_run_id
                )
                latest_checkpoint = await ai_run_repository.latest_checkpoint(
                    run.ai_run_id
                )
                resume_snapshot = (
                    latest_checkpoint.state_snapshot if latest_checkpoint else None
                )
                if run.automatic_retry_count >= limits.retries:
                    continue
                delay = _dispatch_retry_delay_seconds(dispatch_failures)
                last_updated = run.updated_at
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                if now - last_updated < timedelta(seconds=delay):
                    continue

                queued = await ai_run_repository.transition_with_checkpoint(
                    run.ai_run_id,
                    run.revision,
                    {
                        "status": AIRunStatus.QUEUED,
                        "error_code": None,
                        "automatic_retry_count": run.automatic_retry_count + 1,
                    },
                    phase=AIRunPhase.QUEUED,
                    detail={
                        "reason_code": "AI_RUN_QUEUE_REDELIVERY",
                        "dispatch_attempt": dispatch_failures + 1,
                    },
                    state_snapshot=resume_snapshot,
                )
                if not queued:
                    continue

                try:
                    published = await mq.publish(
                        AI_RUN_QUEUE,
                        {"ai_run_id": queued.ai_run_id},
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "AI run queue redelivery raised for run {}",
                        queued.ai_run_id,
                    )
                    published = False
                if published:
                    continue

                await ai_run_repository.transition_with_checkpoint(
                    queued.ai_run_id,
                    queued.revision,
                    {
                        "status": AIRunStatus.DEGRADED,
                        "error_code": "AI_RUN_QUEUE_UNAVAILABLE",
                    },
                    phase=AIRunPhase.FINALIZED,
                    detail={
                        "reason_code": "AI_RUN_QUEUE_UNAVAILABLE",
                        "retryable": True,
                        "dispatch_attempt": dispatch_failures + 1,
                    },
                    state_snapshot=resume_snapshot,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "AI run recovery failed for run {}",
                    run.ai_run_id,
                )

    async def _dispatch_stale_queued_runs(self, now: datetime) -> None:
        dispatch_window = max(1, limits.message_ack_timeout_seconds)
        try:
            runs = await ai_run_repository.claim_stale_queued_runs(
                now - timedelta(seconds=dispatch_window),
                now + timedelta(seconds=dispatch_window),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI run worker could not claim stale queued runs")
            return

        for run in runs:
            try:
                published = await mq.publish(
                    AI_RUN_QUEUE,
                    {"ai_run_id": run.ai_run_id},
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "AI run stale queued dispatch raised for run {}",
                    run.ai_run_id,
                )
                published = False
            if published:
                continue
            checkpoint = await ai_run_repository.latest_checkpoint(
                run.ai_run_id
            )
            await ai_run_repository.transition_with_checkpoint(
                run.ai_run_id,
                run.revision,
                {
                    "status": AIRunStatus.DEGRADED,
                    "error_code": "AI_RUN_QUEUE_UNAVAILABLE",
                    "queue_dispatch_lease_expires_at": None,
                },
                phase=AIRunPhase.FINALIZED,
                detail={
                    "reason_code": "AI_RUN_QUEUE_UNAVAILABLE",
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
                recovered = await ai_run_repository.recover_interrupted_runs(
                    include_queued=False,
                    after_ai_run_id=cursor,
                    limit=limits.run_recovery_batch_size,
                )
                if not recovered:
                    break
                await self._dispatch_recovered_runs(recovered)
                cursor = recovered[-1].ai_run_id
                if len(recovered) < limits.run_recovery_batch_size:
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI run worker could not recover expired run leases")

    async def _record_worker_failure(self, payload: dict) -> bool:
        ai_run_id = str(payload.get("ai_run_id") or "")
        if not ai_run_id:
            return True
        run = await ai_run_repository.get_run(ai_run_id)
        if not run or run.status != AIRunStatus.QUEUED:
            return True
        latest_checkpoint = await ai_run_repository.latest_checkpoint(ai_run_id)
        action_outcome_uncertain = bool(
            latest_checkpoint
            and latest_checkpoint.phase == AIRunPhase.ACTION_STARTED
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
                AIRunStatus.DEGRADED
                if resumable and automatic_retry_count <= limits.retries
                else AIRunStatus.FAILED
            ),
            "worker_lease_expires_at": None,
            "error_code": (
                "AI_RUN_ACTION_OUTCOME_UNCERTAIN"
                if action_outcome_uncertain
                else "AI_RUN_WORKER_RETRYABLE"
                if resumable and automatic_retry_count <= limits.retries
                else "AI_RUN_WORKER_FAILED"
            ),
            "automatic_retry_count": automatic_retry_count,
        }
        if action_outcome_uncertain:
            updated = await ai_run_repository.transition_with_checkpoint(
                ai_run_id,
                run.revision,
                values,
                phase=latest_checkpoint.phase,
                detail={
                    **latest_checkpoint.detail,
                    "reason_code": "AI_RUN_ACTION_OUTCOME_UNCERTAIN",
                    "retryable": False,
                },
                state_snapshot=latest_checkpoint.state_snapshot,
            )
        else:
            updated = await ai_run_repository.transition_with_checkpoint(
                ai_run_id,
                run.revision,
                values,
                phase=AIRunPhase.FINALIZED,
                detail={
                    "reason_code": values["error_code"],
                    "resumable": resumable,
                    "automatic_retry_count": automatic_retry_count,
                    "retryable": values["error_code"] == "AI_RUN_WORKER_RETRYABLE",
                },
                state_snapshot=(
                    latest_checkpoint.state_snapshot if latest_checkpoint else None
                ),
            )
        return updated is not None

    async def _process(self, payload: dict) -> None:
        ai_run_id = str(payload.get("ai_run_id") or "")
        if not ai_run_id:
            return
        run = await ai_run_repository.get_run(ai_run_id)
        if not run or run.status != AIRunStatus.QUEUED:
            return
        if not (run.constraints or {}).get("user_requested"):
            await ai_run_service.cancel(run, run.revision)
            return
        token = await ai_run_service.token_for(ai_run_id)
        if not token:
            reason_code = (
                "AI_RUN_EXECUTOR_UNAVAILABLE"
                if not run.execution_user_id or not run.execution_role
                else "AUTHORIZATION_EXPIRED"
            )
            await self._await_authorization(run, reason_code)
            return
        try:
            live_role, live_permissions = await project_access(
                run.project_id,
                token,
                run.ai_run_id,
                preferred_role=run.execution_role,
            )
        except Exception:
            logger.exception("AI run principal is no longer authorized")
            await self._await_authorization(run, "AI_RUN_PRINCIPAL_UNAVAILABLE")
            return
        expected_role = run.execution_role
        if live_role != expected_role:
            await self._await_authorization(run, "AI_RUN_PRINCIPAL_ROLE_CHANGED")
            return
        latest_checkpoint = await ai_run_repository.latest_checkpoint(ai_run_id)
        snapshot = latest_checkpoint.state_snapshot if latest_checkpoint else None
        resume_phase = snapshot.completed_phase.value if snapshot else None
        if snapshot and (
            snapshot.run.run_id != ai_run_id
            or snapshot.run.project_id != run.project_id
            or snapshot.run.user_id != (run.execution_user_id or run.requester_user_id)
            or snapshot.run.role != live_role
        ):
            await self._fail(
                ai_run_id,
                run.revision,
                "AI_RUN_CHECKPOINT_IDENTITY_MISMATCH",
            )
            return
        ai_run = resume_run_with_live_permissions(snapshot, live_permissions) or VeriqRunState(
            run_id=run.ai_run_id,
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
        execution_state = (
            snapshot.model_dump(mode="python")
            if snapshot
            else {
                "automatic": True,
                "run": ai_run.model_dump(mode="python"),
                "evidence": [item.model_dump(mode="python") for item in run.evidence],
                "target_artifact_ids": run.target_artifact_ids,
                "constraints": run.constraints,
                "source_event_verified": run.source_event_verified,
                "tasks": [],
                "results": [],
            }
        )
        execution_state["run"] = ai_run.model_dump(mode="python")
        execution_state["token"] = ""
        execution_state["automatic"] = True
        execution_state["constraints"] = {
            **execution_state.get("constraints", {}),
            "change_simulation": run.kind == AIRunKind.CHANGE_SIMULATION,
            **(
                {"change_simulation_input": run.change_simulation.model_dump(mode="json")}
                if run.change_simulation
                else {}
            ),
        }
        execution_state["resume_after_phase"] = resume_phase
        execution_state["worker_revision"] = run.revision + 1
        recovery_snapshot = AIRunStateSnapshot.model_validate(
            {
                key: value
                for key, value in execution_state.items()
                if key in AIRunStateSnapshot.model_fields and key != "completed_phase"
            }
            | {
                "completed_phase": (
                    snapshot.completed_phase if snapshot else AIRunPhase.QUEUED
                )
            }
        )
        trace_id = str(uuid4())
        running = await ai_run_repository.transition_with_checkpoint(
            ai_run_id,
            run.revision,
            {
                "status": AIRunStatus.RUNNING,
                "error_code": None,
                "queue_dispatch_lease_expires_at": None,
                "execution_permissions": live_permissions,
                "trace_id": trace_id,
                "worker_lease_expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=limits.message_ack_timeout_seconds),
            },
            phase=AIRunPhase.WORKER_STARTED,
            detail={
                "reason_code": "AI_RUN_WORKER_CLAIMED",
                "resume_after_phase": resume_phase,
            },
            state_snapshot=recovery_snapshot,
        )
        if not running:
            return
        execution_token = await ai_run_service.token_for(
            ai_run_id, worker_revision=running.revision
        )
        if not execution_token:
            await self._fail(
                ai_run_id,
                running.revision,
                "AUTHORIZATION_EXPIRED",
                require_live_worker_lease=True,
            )
            return
        execution_state["token"] = f"Bearer {execution_token}"
        execution_state["worker_revision"] = running.revision
        recovery_snapshot.worker_revision = running.revision
        agentops.record_session_start(ai_run.run_id, running.requester_user_id)
        try:
            result = await asyncio.wait_for(
                run_ai_run_graph(execution_state),
                timeout=limits.run_timeout_seconds,
            )
            completed = VeriqRunState(**result["run"])
            terminal_status = terminal_status_for_ai_run(completed)
            authorization_error = None
            try:
                final_role, final_permissions = await project_access(
                    running.project_id,
                    execution_token,
                    running.ai_run_id,
                    preferred_role=running.execution_role,
                )
                if final_role != running.execution_role:
                    authorization_error = "AI_RUN_PRINCIPAL_ROLE_CHANGED"
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
                logger.exception("AI run could not revalidate its principal after execution")
                authorization_error = "PROJECT_AUTHORIZATION_CHECK_FAILED"
            if authorization_error:
                completed.status = AIRunStatus.FAILED
                completed.error_code = authorization_error
                terminal_status = AIRunStatus.AWAITING_AUTHORIZATION
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
            downstream_handoffs = []
            handoff_blocked = any(
                item.get("workflow_type") != "CHANGE_SIMULATION"
                and item.get("status") not in {"QUEUED", "RUNNING", "COMPLETED"}
                for item in downstream_handoffs
            )
            if handoff_blocked and terminal_status == AIRunStatus.COMPLETED:
                terminal_status = AIRunStatus.DEGRADED
                completed.error_code = "TEST_DESIGN_HANDOFF_PENDING"
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
                                    ai_run_id,
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
                    ai_run_id=ai_run_id,
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
                            ai_run_id=ai_run_id,
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
                if verified_mutation and output_refs and not input_fact_ids:
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
            if terminal_status == AIRunStatus.COMPLETED and has_provenance_gap(
                rejected_source_fact_count,
                unlinked_mutation_count,
            ):
                terminal_status = AIRunStatus.DEGRADED
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
                await ai_run_repository.replace_provenance(
                    ai_run_id,
                    source_facts,
                    DerivationReceipt(
                        ai_run_id=ai_run_id,
                        project_id=running.project_id,
                        source_fact_ids=[item.source_fact_id for item in source_facts],
                        transformation_steps=transformation_steps,
                        steps=derivation_steps,
                        output_evidence_refs=verified_outputs,
                        model_metadata=completed.model_metadata,
                        outcome=terminal_status.value,
                    ),
                )
            except Exception:
                logger.exception("AI run provenance could not be persisted")
                await self._fail(
                    ai_run_id,
                    running.revision,
                    "AI_RUN_PROVENANCE_PERSISTENCE_FAILED",
                    require_live_worker_lease=True,
                )
                agentops.record_session_end(completed.run_id, "failed")
                return

            final_snapshot = None
            if terminal_status in {
                AIRunStatus.AWAITING_INPUT,
                AIRunStatus.AWAITING_AUTHORIZATION,
            }:
                latest_checkpoint = await ai_run_repository.latest_checkpoint(
                    ai_run_id
                )
                final_snapshot = latest_checkpoint.state_snapshot if latest_checkpoint else None
                if terminal_status == AIRunStatus.AWAITING_INPUT and final_snapshot:
                    action_uncertainties = action_input_uncertainties(completed)
                    if action_uncertainties:
                        final_snapshot = final_snapshot.model_copy(
                            update={
                                "uncertainties": [
                                    *final_snapshot.uncertainties,
                                    *action_uncertainties,
                                ]
                            }
                        )
            finalized_detail = {
                "ai_run_id": completed.run_id,
                "error_code": completed.error_code,
                "provenance_rejections": {
                    "source_facts": rejected_source_fact_count,
                    "unlinked_mutations": unlinked_mutation_count,
                },
            }
            proposal_refs = set((completed.proposal or {}).get("evidence_refs") or [])
            allowed_tool_refs = proposal_refs & set(completed.evidence_refs)
            tool_evidence = verified_tool_evidence_records(
                result.get("evidence") or [],
                running.project_id,
                allowed_tool_refs,
            )
            updated = await ai_run_repository.transition_with_checkpoint(
                ai_run_id,
                running.revision,
                {
                    "status": terminal_status,
                    "worker_lease_expires_at": None,
                    "ai_run_id": completed.run_id,
                    "result": {
                        "proposal": completed.proposal,
                        "evidence_refs": completed.evidence_refs,
                        "tool_evidence": tool_evidence,
                        "observations": completed.observations,
                        "downstream_workflows": downstream_handoffs,
                        "error_code": completed.error_code,
                        "provenance_rejections": {
                            "source_facts": rejected_source_fact_count,
                            "unlinked_mutations": unlinked_mutation_count,
                                },
                    },
                    "error_code": completed.error_code,
                },
                phase=AIRunPhase.FINALIZED,
                detail=finalized_detail,
                state_snapshot=final_snapshot,
                require_live_worker_lease=True,
            )
            if not updated:
                agentops.record_session_end(completed.run_id, "failed")
                return
            try:
                await run_store.save(completed)
                if terminal_status == AIRunStatus.COMPLETED:
                    await long_term_memory.record_verified(completed)
            except Exception:
                logger.exception(
                    "AI run completed but optional memory could not be persisted"
                )
            agentops.record_session_end(
                completed.run_id,
                "done"
                if terminal_status == AIRunStatus.COMPLETED
                else "waiting_input"
                if terminal_status == AIRunStatus.AWAITING_INPUT
                else "failed",
            )
        except TimeoutError:
            await self._fail(
                ai_run_id,
                running.revision,
                "AI_RUN_LIMIT_REACHED",
                require_live_worker_lease=True,
            )
            agentops.record_session_end(ai_run.run_id, "failed")
        except Exception:
            logger.exception("AI request workflow execution failed")
            await self._fail(
                ai_run_id,
                running.revision,
                "AI_RUN_EXECUTION_FAILED",
                require_live_worker_lease=True,
            )
            agentops.record_session_end(ai_run.run_id, "failed")

    async def _await_authorization(self, run: AIRun, reason_code: str) -> None:
        await ai_run_repository.transition_with_checkpoint(
            run.ai_run_id,
            run.revision,
            {
                "status": AIRunStatus.AWAITING_AUTHORIZATION,
                "error_code": reason_code,
                "worker_lease_expires_at": None,
            },
            phase=AIRunPhase.FINALIZED,
            detail={"reason_code": reason_code},
            state_snapshot=None,
        )

    async def _fail(
        self,
        ai_run_id: str,
        revision: int,
        code: str,
        *,
        require_live_worker_lease: bool = False,
    ) -> None:
        latest_checkpoint = await ai_run_repository.latest_checkpoint(ai_run_id)
        action_outcome_uncertain = bool(
            latest_checkpoint
            and latest_checkpoint.phase == AIRunPhase.ACTION_STARTED
            and (
                latest_checkpoint.detail.get("action") != "READ"
                or latest_checkpoint.detail.get("task_has_mutation") is True
            )
        )
        effective_code = (
            "AI_RUN_ACTION_OUTCOME_UNCERTAIN"
            if action_outcome_uncertain
            else code
        )
        resume_snapshot = (
            None
            if code == "AI_RUN_CHECKPOINT_IDENTITY_MISMATCH"
            else latest_checkpoint.state_snapshot
            if latest_checkpoint
            else None
        )
        values = {
            "status": AIRunStatus.FAILED,
            "error_code": effective_code,
            "worker_lease_expires_at": None,
        }
        if action_outcome_uncertain:
            await ai_run_repository.transition_with_checkpoint(
                ai_run_id,
                revision,
                values,
                phase=latest_checkpoint.phase,
                detail={
                    **latest_checkpoint.detail,
                    "reason_code": "AI_RUN_ACTION_OUTCOME_UNCERTAIN",
                    "retryable": False,
                },
                state_snapshot=latest_checkpoint.state_snapshot,
                require_live_worker_lease=require_live_worker_lease,
            )
            return
        await ai_run_repository.transition_with_checkpoint(
            ai_run_id,
            revision,
            values,
            phase=AIRunPhase.FINALIZED,
            detail={"reason_code": code, "resumable": resume_snapshot is not None},
            state_snapshot=resume_snapshot,
            require_live_worker_lease=require_live_worker_lease,
        )

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


ai_run_worker = AIRunWorker()
