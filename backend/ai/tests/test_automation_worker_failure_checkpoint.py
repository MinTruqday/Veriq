import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.runtime.automation_worker import (
    AutomationWorker,
    _automation_retry_delay_seconds,
)
from src.runtime.limits import limits
from src.schemas.agent import VeriqRunState
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationGraphSnapshot,
    AutomationKind,
    AutomationRun,
    AutomationStatus,
)


class AutomationWorkerFailureCheckpointTests(unittest.IsolatedAsyncioTestCase):
    def test_retry_delay_caps_the_exponent_before_calculation(self):
        with patch(
            "src.runtime.automation_worker.limits",
            type(
                "RetryLimits",
                (),
                {"queue_retry_base_seconds": 15, "queue_retry_max_seconds": 300},
            )(),
        ):
            self.assertEqual(
                [_automation_retry_delay_seconds(value) for value in (0, 1, 2, 3, 4, 5, 10**9)],
                [15, 15, 30, 60, 120, 240, 300],
            )

    async def test_idle_queue_yields_before_next_consume(self):
        worker = AutomationWorker()
        sleeps = []

        async def sleep(delay):
            sleeps.append(delay)
            worker._stopping = True

        with (
            patch("src.runtime.automation_worker.mq.consume", new=AsyncMock(return_value=None)),
            patch.object(worker, "_retry_queue_unavailable_runs", new=AsyncMock()),
            patch("src.runtime.automation_worker.asyncio.sleep", new=sleep),
        ):
            await worker._consume()

        self.assertEqual(sleeps, [0.25])

    async def test_interrupted_mcp_audits_recover_only_on_queue_scan_interval(self):
        worker = AutomationWorker()
        worker._last_queue_retry_scan = asyncio.get_running_loop().time()
        with (
            patch.object(worker, "_recover_expired_running_runs", new=AsyncMock()),
            patch(
                "src.runtime.automation_worker.mcp_repository.recover_interrupted_call_audits",
                new=AsyncMock(return_value=0),
            ) as recover_audits,
            patch(
                "src.runtime.automation_worker.automation_repository.list_retryable_queue_runs",
                new=AsyncMock(return_value=[]),
            ),
        ):
            await worker._retry_queue_unavailable_runs()
            recover_audits.assert_not_awaited()

            worker._last_queue_retry_scan -= limits.queue_retry_scan_seconds + 1
            await worker._retry_queue_unavailable_runs()

        recover_audits.assert_awaited_once()

    async def test_stale_queued_run_is_republished_after_dispatch_crash_window(self):
        worker = AutomationWorker()
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        current_time = datetime.now(timezone.utc)
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.claim_stale_queued_runs",
                new=AsyncMock(return_value=[run]),
            ) as claim,
            patch(
                "src.runtime.automation_worker.mq.publish",
                new=AsyncMock(return_value=True),
            ) as publish,
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
        ):
            await worker._dispatch_stale_queued_runs(current_time)

        dispatch_window = max(1, limits.message_ack_timeout_seconds)
        stale_before, lease_expires_at = claim.await_args.args
        self.assertLessEqual(
            abs((stale_before - (current_time - timedelta(seconds=dispatch_window))).total_seconds()),
            0.001,
        )
        self.assertEqual(
            lease_expires_at, current_time + timedelta(seconds=dispatch_window)
        )
        publish.assert_awaited_once_with(
            "ai.automation", {"automation_run_id": run.automation_run_id}
        )
        transition.assert_not_awaited()

    async def test_stale_queued_publish_failure_returns_run_to_retryable_state(self):
        worker = AutomationWorker()
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.PLAN_CREATED,
            {"reason_code": "AUTOMATION_QUEUE_REDELIVERY"},
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.claim_stale_queued_runs",
                new=AsyncMock(return_value=[run]),
            ),
            patch(
                "src.runtime.automation_worker.mq.publish",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=run),
            ) as transition,
        ):
            await worker._dispatch_stale_queued_runs(datetime.now(timezone.utc))

        self.assertEqual(
            transition.await_args.args[2]["status"], AutomationStatus.DEGRADED
        )
        self.assertEqual(
            transition.await_args.args[2]["error_code"],
            "AUTOMATION_QUEUE_UNAVAILABLE",
        )
        self.assertIsNone(
            transition.await_args.args[2]["queue_dispatch_lease_expires_at"]
        )
        self.assertEqual(
            transition.await_args.kwargs["state_snapshot"], checkpoint.state_snapshot
        )

    def make_run(self):
        return AutomationRun(
            automation_run_id="AUT-WORKER-FAILURE-1",
            project_id="PRJ-1",
            requester_user_id="USER-1",
            requester_role="QA",
            execution_user_id="USER-1",
            execution_role="QA",
            kind=AutomationKind.EVENT,
            objective="Tiếp tục từ checkpoint an toàn",
            status=AutomationStatus.RUNNING,
            revision=2,
        )

    def make_checkpoint(self, phase, detail):
        run = self.make_run()
        state = VeriqRunState(
            run_id=run.automation_run_id,
            project_id=run.project_id,
            user_id=run.execution_user_id,
            role=run.execution_role,
            objective=run.objective,
        )
        return AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=phase,
            status=AutomationStatus.RUNNING,
            detail=detail,
            state_snapshot=AutomationGraphSnapshot(completed_phase=phase, run=state),
        )

    async def test_redelivered_message_does_not_restart_a_non_queued_run(self):
        worker = AutomationWorker()
        for status in (
            AutomationStatus.RUNNING,
            AutomationStatus.COMPLETED,
            AutomationStatus.AWAITING_AUTHORIZATION,
        ):
            with self.subTest(status=status):
                run = self.make_run().model_copy(update={"status": status})
                with (
                    patch(
                        "src.runtime.automation_worker.automation_repository.get_run",
                        new=AsyncMock(return_value=run),
                    ) as get_run,
                    patch(
                        "src.runtime.automation_worker.automation_service.token_for",
                        new=AsyncMock(),
                    ) as token_for,
                    patch(
                        "src.runtime.automation_worker.automation_workflow.ainvoke",
                        new=AsyncMock(),
                    ) as graph,
                    patch(
                        "src.runtime.automation_worker.project_access",
                        new=AsyncMock(),
                    ) as access,
                ):
                    await worker._process(
                        {"automation_run_id": run.automation_run_id}
                    )

                get_run.assert_awaited_once_with(run.automation_run_id)
                token_for.assert_not_awaited()
                graph.assert_not_awaited()
                access.assert_not_awaited()

    async def test_missing_executor_token_atomically_records_authorization_checkpoint(self):
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        awaiting = run.model_copy(
            update={
                "status": AutomationStatus.AWAITING_AUTHORIZATION,
                "error_code": "AUTHORIZATION_EXPIRED",
                "revision": run.revision + 1,
            }
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.get_run",
                new=AsyncMock(return_value=run),
            ),
            patch(
                "src.runtime.automation_worker.automation_service.token_for",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=awaiting),
            ) as transition_with_checkpoint,
        ):
            await AutomationWorker()._process(
                {"automation_run_id": run.automation_run_id}
            )

        transition_with_checkpoint.assert_awaited_once()
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["phase"],
            AutomationCheckpointPhase.FINALIZED,
        )
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["detail"]["reason_code"],
            "AUTHORIZATION_EXPIRED",
        )
        self.assertIsNone(
            transition_with_checkpoint.await_args.kwargs["state_snapshot"]
        )

    async def test_safe_failure_checkpoint_preserves_snapshot_for_retry(self):
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.ACTIONS_EXECUTED,
            {"task_id": "TASK-1", "action": "MUTATE", "task_has_mutation": True},
        )
        failed = run.model_copy(
            update={"status": AutomationStatus.FAILED, "revision": 3}
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.get_run",
                new=AsyncMock(return_value=run),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=failed),
            ) as transition,
        ):
            recorded = await AutomationWorker()._record_worker_failure(
                {"automation_run_id": run.automation_run_id}
            )

        self.assertTrue(recorded)
        self.assertEqual(
            transition.await_args.args[2]["error_code"], "AUTOMATION_WORKER_RETRYABLE"
        )
        self.assertEqual(transition.await_args.kwargs["phase"], AutomationCheckpointPhase.FINALIZED)
        self.assertEqual(
            transition.await_args.kwargs["state_snapshot"], checkpoint.state_snapshot
        )
        self.assertTrue(transition.await_args.kwargs["detail"]["resumable"])

    async def test_uncertain_mutation_failure_does_not_hide_action_started_checkpoint(self):
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.ACTION_STARTED,
            {"task_id": "TASK-1", "action": "MUTATE", "task_has_mutation": True},
        )
        failed = run.model_copy(
            update={
                "status": AutomationStatus.FAILED,
                "error_code": "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
                "revision": 3,
            }
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.get_run",
                new=AsyncMock(return_value=run),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=failed),
            ) as transition,
        ):
            recorded = await AutomationWorker()._record_worker_failure(
                {"automation_run_id": run.automation_run_id}
            )

        self.assertTrue(recorded)
        self.assertEqual(
            transition.await_args.args[2]["error_code"],
            "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
        )
        self.assertEqual(
            transition.await_args.kwargs["phase"], AutomationCheckpointPhase.ACTION_STARTED
        )
        self.assertEqual(
            transition.await_args.kwargs["detail"]["reason_code"],
            "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
        )
        self.assertEqual(
            transition.await_args.kwargs["state_snapshot"], checkpoint.state_snapshot
        )

    async def test_graph_failure_preserves_safe_snapshot_for_retry(self):
        run = self.make_run()
        checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.ACTIONS_EXECUTED,
            {"task_id": "TASK-1", "action": "MUTATE", "task_has_mutation": True},
        )
        failed = run.model_copy(
            update={"status": AutomationStatus.FAILED, "revision": 3}
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=failed),
            ) as transition,
        ):
            await AutomationWorker()._fail(
                run.automation_run_id, run.revision, "AUTOMATION_EXECUTION_FAILED"
            )

        self.assertEqual(transition.await_args.kwargs["detail"]["reason_code"], "AUTOMATION_EXECUTION_FAILED")
        self.assertEqual(
            transition.await_args.kwargs["state_snapshot"], checkpoint.state_snapshot
        )

    async def test_graph_failure_marks_mutating_action_outcome_uncertain(self):
        run = self.make_run()
        checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.ACTION_STARTED,
            {"task_id": "TASK-1", "action": "MUTATE", "task_has_mutation": True},
        )
        failed = run.model_copy(
            update={
                "status": AutomationStatus.FAILED,
                "error_code": "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
                "revision": 3,
            }
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=failed),
            ) as transition,
        ):
            await AutomationWorker()._fail(
                run.automation_run_id, run.revision, "AUTOMATION_EXECUTION_FAILED"
            )

        self.assertEqual(
            transition.await_args.args[2]["error_code"],
            "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
        )
        self.assertEqual(
            transition.await_args.kwargs["phase"], AutomationCheckpointPhase.ACTION_STARTED
        )
        self.assertEqual(
            transition.await_args.kwargs["detail"]["reason_code"],
            "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
        )
        self.assertEqual(
            transition.await_args.kwargs["state_snapshot"], checkpoint.state_snapshot
        )

    async def test_run_timeout_fails_the_claimed_run_and_clears_its_lease(self):
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        running = run.model_copy(
            update={
                "status": AutomationStatus.RUNNING,
                "revision": run.revision + 1,
            }
        )
        failed = running.model_copy(
            update={
                "status": AutomationStatus.FAILED,
                "error_code": "AUTOMATION_LIMIT_REACHED",
                "revision": running.revision + 1,
            }
        )

        async def never_complete(*_args, **_kwargs):
            await asyncio.Event().wait()

        real_wait_for = asyncio.wait_for

        async def force_timeout(coroutine, *, timeout):
            return await real_wait_for(coroutine, timeout=0.001)

        with (
            patch(
                "src.runtime.automation_worker.automation_repository.get_run",
                new=AsyncMock(return_value=run),
            ),
            patch(
                "src.runtime.automation_worker.automation_service.token_for",
                new=AsyncMock(return_value="executor-token"),
            ),
            patch(
                "src.runtime.automation_worker.project_access",
                new=AsyncMock(return_value=("QA", ["project.read"])),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(side_effect=[running, failed]),
            ) as transition,
            patch(
                "src.runtime.automation_worker.automation_workflow.ainvoke",
                new=AsyncMock(side_effect=never_complete),
            ) as graph,
            patch(
                "src.runtime.automation_worker.asyncio.wait_for",
                new=force_timeout,
            ),
            patch("src.runtime.automation_worker.agentops.record_session_start"),
            patch("src.runtime.automation_worker.agentops.record_session_end"),
        ):
            await AutomationWorker()._process(
                {"automation_run_id": run.automation_run_id}
            )

        self.assertEqual(transition.await_count, 2)
        self.assertEqual(
            transition.await_args_list[1].args[2]["error_code"],
            "AUTOMATION_LIMIT_REACHED",
        )
        self.assertIsNone(transition.await_args_list[1].args[2]["worker_lease_expires_at"])
        self.assertEqual(
            transition.await_args_list[1].kwargs["phase"],
            AutomationCheckpointPhase.FINALIZED,
        )
        graph.assert_awaited_once()

    async def test_startup_redelivery_failure_keeps_the_recovered_snapshot(self):
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.ACTIONS_EXECUTED,
            {"task_id": "TASK-1"},
        )
        degraded = run.model_copy(
            update={
                "status": AutomationStatus.DEGRADED,
                "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                "revision": run.revision + 1,
            }
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=degraded),
            ) as transition_with_checkpoint,
            patch("src.runtime.automation_worker.mq.publish", new=AsyncMock(return_value=False)),
        ):
            await AutomationWorker()._dispatch_recovered_runs([run])

        self.assertEqual(transition_with_checkpoint.await_count, 1)
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["phase"],
            AutomationCheckpointPhase.FINALIZED,
        )
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["detail"]["retryable"],
            True,
        )
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["state_snapshot"], checkpoint.state_snapshot
        )

    async def test_startup_publish_exception_is_recoverable(self):
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.ACTIONS_EXECUTED,
            {"task_id": "TASK-1"},
        )
        degraded = run.model_copy(
            update={
                "status": AutomationStatus.DEGRADED,
                "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                "revision": run.revision + 1,
            }
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=degraded),
            ) as transition_with_checkpoint,
            patch(
                "src.runtime.automation_worker.mq.publish",
                new=AsyncMock(side_effect=RuntimeError("broker unavailable")),
            ),
        ):
            await AutomationWorker()._dispatch_recovered_runs([run])

        transition_with_checkpoint.assert_awaited_once()
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["phase"],
            AutomationCheckpointPhase.FINALIZED,
        )
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["state_snapshot"],
            checkpoint.state_snapshot,
        )
    async def test_startup_redelivers_a_persisted_queued_run(self):
        run = self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})
        with (
            patch(
                "src.runtime.automation_worker.mq.publish",
                new=AsyncMock(return_value=True),
            ) as publish,
        ):
            await AutomationWorker()._dispatch_recovered_runs([run])

        publish.assert_awaited_once_with(
            "ai.automation", {"automation_run_id": run.automation_run_id}
        )

    async def test_start_schedules_consumer_and_recovery_without_waiting_for_database(self):
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.recover_interrupted_runs",
                new=AsyncMock(),
            ) as recover,
            patch(
                "src.runtime.automation_worker.create_background_task",
                side_effect=lambda coroutine, name: (coroutine.close(), name)[1],
            ) as create_task,
        ):
            await AutomationWorker().start()

        recover.assert_not_awaited()
        self.assertEqual(
            [call.args[1] for call in create_task.call_args_list],
            ["ai-automation-worker", "ai-automation-startup-recovery"],
        )

    async def test_startup_recovery_retries_database_failure_with_same_cutoff(self):
        worker = AutomationWorker()
        worker._stopping = False
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.recover_interrupted_runs",
                new=AsyncMock(
                    side_effect=[RuntimeError("database unavailable"), []]
                ),
            ) as recover,
            patch(
                "src.runtime.automation_worker.asyncio.sleep",
                new=AsyncMock(),
            ) as sleep,
        ):
            cutoff = datetime.now(timezone.utc)
            await worker._retry_startup_recovery(cutoff)

        self.assertEqual(recover.await_count, 2)
        self.assertEqual(recover.await_args_list[0].args, (cutoff,))
        self.assertEqual(recover.await_args_list[1].args, (cutoff,))
        sleep.assert_awaited_once_with(5)

    async def test_live_worker_periodically_recovers_only_expired_leases(self):
        worker = AutomationWorker()
        recovered = [self.make_run().model_copy(update={"status": AutomationStatus.QUEUED})]
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.recover_interrupted_runs",
                new=AsyncMock(return_value=recovered),
            ) as recover,
            patch.object(worker, "_dispatch_recovered_runs", new=AsyncMock()) as dispatch,
        ):
            await worker._recover_expired_running_runs()

        recover.assert_awaited_once_with(
            include_queued=False,
            include_legacy_running=False,
            after_automation_run_id=None,
            limit=limits.automation_recovery_batch_size,
        )
        dispatch.assert_awaited_once_with(recovered)

    async def test_stop_cancels_both_consumer_and_startup_recovery_tasks(self):
        worker = AutomationWorker()
        started = asyncio.Event()
        wait_forever = asyncio.Event()

        async def hold_worker_open():
            started.set()
            await wait_forever.wait()

        consumer_task = asyncio.create_task(hold_worker_open())
        recovery_task = asyncio.create_task(hold_worker_open())
        worker._task = consumer_task
        worker._startup_recovery_task = recovery_task
        await started.wait()

        await worker.stop()

        self.assertTrue(consumer_task.cancelled())
        self.assertTrue(recovery_task.cancelled())
        self.assertIsNone(worker._task)
        self.assertIsNone(worker._startup_recovery_task)

    async def test_queue_unavailable_run_is_republished_after_backoff(self):
        run = self.make_run().model_copy(
            update={
                "status": AutomationStatus.DEGRADED,
                "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=10),
            }
        )
        queued = run.model_copy(
            update={
                "status": AutomationStatus.QUEUED,
                "error_code": None,
                "revision": run.revision + 1,
            }
        )
        failed_checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.FINALIZED,
            {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
        )
        stale_checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.OBSERVED,
            {"reason_code": "OLDER_CHECKPOINT"},
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.recover_interrupted_runs",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.list_retryable_queue_runs",
                new=AsyncMock(return_value=[run]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.count_retry_checkpoints",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=failed_checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=queued),
            ) as transition_with_checkpoint,
            patch(
                "src.runtime.automation_worker.mq.publish", new=AsyncMock(return_value=True)
            ) as publish,
        ):
            await AutomationWorker()._retry_queue_unavailable_runs()

        transition_with_checkpoint.assert_awaited_once_with(
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
                "dispatch_attempt": 2,
            },
            state_snapshot=failed_checkpoint.state_snapshot,
        )
        publish.assert_awaited_once_with(
            "ai.automation", {"automation_run_id": run.automation_run_id}
        )

    async def test_failed_redelivery_preserves_checkpoint_for_next_attempt(self):
        run = self.make_run().model_copy(
            update={
                "status": AutomationStatus.DEGRADED,
                "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=10),
            }
        )
        queued = run.model_copy(
            update={
                "status": AutomationStatus.QUEUED,
                "error_code": None,
                "revision": run.revision + 1,
            }
        )
        degraded = queued.model_copy(
            update={
                "status": AutomationStatus.DEGRADED,
                "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                "revision": queued.revision + 1,
            }
        )
        failed_checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.FINALIZED,
            {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.recover_interrupted_runs",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.list_retryable_queue_runs",
                new=AsyncMock(return_value=[run]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.count_retry_checkpoints",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=failed_checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(side_effect=[queued, degraded]),
            ) as transition_with_checkpoint,
            patch(
                "src.runtime.automation_worker.mq.publish", new=AsyncMock(return_value=False)
            ),
        ):
            await AutomationWorker()._retry_queue_unavailable_runs()

        self.assertEqual(transition_with_checkpoint.await_count, 2)
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["state_snapshot"],
            failed_checkpoint.state_snapshot,
        )

    async def test_queue_unavailable_run_obeys_exponential_backoff(self):
        run = self.make_run().model_copy(
            update={
                "status": AutomationStatus.DEGRADED,
                "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                "updated_at": datetime.now(timezone.utc) - timedelta(seconds=20),
            }
        )
        prior_failures = [
            self.make_checkpoint(
                AutomationCheckpointPhase.FINALIZED,
                {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
            )
            for _ in range(2)
        ]
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.recover_interrupted_runs",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.list_retryable_queue_runs",
                new=AsyncMock(return_value=[run]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.count_retry_checkpoints",
                new=AsyncMock(return_value=2),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=prior_failures[-1]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition_with_checkpoint,
            patch("src.runtime.automation_worker.mq.publish", new=AsyncMock()) as publish,
        ):
            await AutomationWorker()._retry_queue_unavailable_runs()

        transition_with_checkpoint.assert_not_awaited()
        publish.assert_not_awaited()

    async def test_queue_redelivery_stops_at_automatic_retry_limit(self):
        run = self.make_run().model_copy(
            update={
                "status": AutomationStatus.DEGRADED,
                "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                "automatic_retry_count": limits.retries,
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=10),
            }
        )
        checkpoint = self.make_checkpoint(
            AutomationCheckpointPhase.FINALIZED,
            {"reason_code": "AUTOMATION_QUEUE_UNAVAILABLE", "retryable": True},
        )
        with (
            patch(
                "src.runtime.automation_worker.automation_repository.recover_interrupted_runs",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.list_retryable_queue_runs",
                new=AsyncMock(return_value=[run]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.count_retry_checkpoints",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition_with_checkpoint,
            patch("src.runtime.automation_worker.mq.publish", new=AsyncMock()) as publish,
        ):
            await AutomationWorker()._retry_queue_unavailable_runs()

        transition_with_checkpoint.assert_not_awaited()
        publish.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
