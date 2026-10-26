import unittest
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.repositories.automation import automation_repository
from src.schemas.agent import AgentTask, ToolCall, VeriqRunState
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationGraphSnapshot,
    AutomationKind,
    AutomationRun,
    AutomationStatus,
)


class AsyncContextManager:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class MongoSession(AsyncContextManager):
    def start_transaction(self):
        return AsyncContextManager()


class AutomationCheckpointRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_run_and_initial_checkpoint_are_created_in_one_transaction(self):
        run = AutomationRun(
            automation_run_id="AUT-ATOMIC-CREATE",
            project_id="PRJ-1",
            requester_user_id="USER-1",
            requester_role="BA",
            kind=AutomationKind.EVENT,
            objective="Create a durable initial state",
            status=AutomationStatus.AWAITING_AUTHORIZATION,
        )
        runs = MagicMock()
        runs.insert_one = AsyncMock()
        checkpoints = MagicMock()
        checkpoints.insert_one = AsyncMock()
        db = MagicMock(automation_runs=runs, automation_checkpoints=checkpoints)
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db
        infrastructure.mongodb.start_session = AsyncMock(return_value=MongoSession())

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            created = await automation_repository.create_run_with_checkpoint(
                run,
                phase=AutomationCheckpointPhase.FINALIZED,
                detail={"reason_code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"},
            )

        self.assertEqual(created.checkpoint_sequence, 1)
        runs.insert_one.assert_awaited_once()
        checkpoints.insert_one.assert_awaited_once()
        run_write = runs.insert_one.await_args
        checkpoint_write = checkpoints.insert_one.await_args
        self.assertEqual(run_write.args[0]["checkpoint_sequence"], 1)
        self.assertEqual(checkpoint_write.args[0]["checkpoint_sequence"], 1)
        self.assertEqual(run_write.kwargs["session"], checkpoint_write.kwargs["session"])
        self.assertEqual(checkpoint_write.args[0]["status"], AutomationStatus.AWAITING_AUTHORIZATION.value)
        self.assertEqual(
            checkpoint_write.args[0]["detail"]["reason_code"],
            "PROJECT_QA_EXECUTOR_UNAVAILABLE",
        )

    def make_run_document(self):
        run = AutomationRun(
            automation_run_id="AUT-RECOVERY-1",
            project_id="PRJ-1",
            requester_user_id="USER-1",
            requester_role="BA",
            execution_user_id="USER-1",
            execution_role="BA",
            kind=AutomationKind.EVENT,
            objective="Continue the interrupted run",
            status=AutomationStatus.RUNNING,
            revision=4,
        )
        document = run.model_dump(mode="json")
        document["_id"] = document.pop("automation_run_id")
        return document

    def make_checkpoint_document(self, phase, detail=None, with_snapshot=True):
        run = VeriqRunState(
            run_id="AUT-RECOVERY-1",
            project_id="PRJ-1",
            user_id="USER-1",
            role="BA",
            objective="Continue the interrupted run",
        )
        snapshot = AutomationGraphSnapshot(
            completed_phase=phase,
            run=run,
        ) if with_snapshot else None
        checkpoint = AutomationCheckpoint(
            automation_run_id="AUT-RECOVERY-1",
            phase=phase,
            status=AutomationStatus.RUNNING,
            detail=detail or {},
            state_snapshot=snapshot,
        )
        document = checkpoint.model_dump(mode="json")
        document["_id"] = document.pop("checkpoint_id")
        return document

    def test_checkpoint_task_identity_survives_a_restart(self):
        run = VeriqRunState(
            run_id="AUT-RECOVERY-1",
            project_id="PRJ-1",
            user_id="USER-1",
            role="BA",
            objective="Continue the interrupted run",
        )
        task = AgentTask(
            run_id=run.run_id,
            project_id=run.project_id,
            user_id=run.user_id,
            domain="requirement",
            objective="Read the current Requirement",
            tool_calls=[ToolCall(tool_name="get_requirement", arguments={"requirement_id": "REQ-1"})],
        )

        snapshot = AutomationGraphSnapshot(
            completed_phase=AutomationCheckpointPhase.ACTION_STARTED,
            run=run,
            tasks=[task],
        )
        restored = AutomationGraphSnapshot.model_validate(snapshot.model_dump(mode="python"))

        self.assertEqual(restored.tasks[0].run_id, run.run_id)
        self.assertEqual(restored.tasks[0].project_id, run.project_id)
        self.assertEqual(restored.tasks[0].tool_calls[0].tool_name, "get_requirement")

    def test_legacy_planned_task_checkpoint_is_bound_to_its_run(self):
        snapshot = AutomationGraphSnapshot.model_validate(
            {
                "completed_phase": "ACTION_STARTED",
                "run": {
                    "run_id": "AUT-RECOVERY-1",
                    "project_id": "PRJ-1",
                    "user_id": "USER-1",
                    "role": "BA",
                    "objective": "Continue the interrupted run",
                },
                "tasks": [
                    {
                        "domain": "requirement",
                        "objective": "Read the current Requirement",
                        "tool_calls": [
                            {"tool_name": "get_requirement", "arguments": {"requirement_id": "REQ-1"}}
                        ],
                    }
                ],
            }
        )

        self.assertEqual(snapshot.tasks[0].run_id, "AUT-RECOVERY-1")
        self.assertEqual(snapshot.tasks[0].project_id, "PRJ-1")
        self.assertEqual(snapshot.tasks[0].user_id, "USER-1")

    async def recover(self, checkpoint, **recovery_options):
        run_document = self.make_run_document()
        run_document["worker_lease_expires_at"] = datetime.now(timezone.utc)
        updated_document = deepcopy(run_document)
        updated_document.update(
            {
                "status": AutomationStatus.QUEUED.value,
                "error_code": None,
                "revision": run_document["revision"] + 1,
            }
        )

        runs = MagicMock()
        runs.find.return_value.to_list = AsyncMock(return_value=[run_document])
        runs.find_one_and_update = AsyncMock(return_value=updated_document)

        checkpoints = MagicMock()
        checkpoints.find_one = AsyncMock(return_value=checkpoint)
        checkpoints.insert_one = AsyncMock()

        db = MagicMock()
        db.automation_runs = runs
        db.automation_checkpoints = checkpoints

        database_infrastructure = MagicMock()
        database_infrastructure.mongodb.__getitem__.return_value = db
        database_infrastructure.mongodb.start_session = AsyncMock(
            return_value=MongoSession()
        )
        with (
            patch("src.repositories.automation.database", database_infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            recovered = await automation_repository.recover_interrupted_runs(
                **recovery_options
            )

        return recovered, runs, checkpoints

    async def test_read_checkpoint_is_queued_for_resume_and_preserved(self):
        checkpoint = self.make_checkpoint_document(
            AutomationCheckpointPhase.ACTION_STARTED,
            {"action": "READ", "task_has_mutation": False},
        )

        recovered, runs, checkpoints = await self.recover(checkpoint)

        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].status, AutomationStatus.QUEUED)
        self.assertIsNone(recovered[0].error_code)
        runs.find_one_and_update.assert_awaited_once()
        recovery_filter = runs.find_one_and_update.await_args.args[0]
        self.assertEqual(recovery_filter["status"], AutomationStatus.RUNNING.value)
        lease_recovery = recovery_filter["$and"][0]["$or"]
        self.assertEqual(
            lease_recovery[0]["worker_lease_expires_at"]["$type"], "date"
        )
        self.assertEqual(
            lease_recovery[1]["worker_lease_expires_at"], None
        )
        saved = checkpoints.insert_one.await_args.args[0]
        self.assertEqual(saved["checkpoint_sequence"], 1)
        self.assertEqual(saved["phase"], AutomationCheckpointPhase.QUEUED)
        self.assertEqual(
            saved["detail"]["reason_code"],
            "AUTOMATION_RESUMED_FROM_CHECKPOINT",
        )
        self.assertEqual(
            saved["state_snapshot"]["completed_phase"],
            AutomationCheckpointPhase.ACTION_STARTED,
        )
        self.assertEqual(
            runs.find_one_and_update.await_args.args[1]["$inc"]["checkpoint_sequence"],
            1,
        )

    async def test_periodic_expired_lease_recovery_cas_excludes_legacy_runs(self):
        checkpoint = self.make_checkpoint_document(
            AutomationCheckpointPhase.OBSERVED,
            {"action": "READ", "task_has_mutation": False},
        )

        recovered, runs, _ = await self.recover(
            checkpoint,
            include_queued=False,
            include_legacy_running=False,
        )

        self.assertEqual(len(recovered), 1)
        recovery_filter = runs.find_one_and_update.await_args.args[0]
        recovery_branches = recovery_filter["$and"][0]["$or"]
        self.assertEqual(len(recovery_branches), 1)
        self.assertEqual(
            recovery_branches[0]["worker_lease_expires_at"]["$type"], "date"
        )
        self.assertNotIn("updated_at", recovery_branches[0])

    async def test_recovery_cutoff_only_selects_runs_present_at_startup(self):
        runs = MagicMock()
        runs.find.return_value.to_list = AsyncMock(return_value=[])
        db = MagicMock()
        db.automation_runs = runs
        database_infrastructure = MagicMock()
        database_infrastructure.mongodb.__getitem__.return_value = db
        cutoff = datetime(2026, 10, 24, tzinfo=timezone.utc)

        with (
            patch("src.repositories.automation.database", database_infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            await automation_repository.recover_interrupted_runs(cutoff)

        query = runs.find.call_args.args[0]
        branches = query["$or"]
        self.assertEqual(len(branches), 3)
        self.assertEqual(branches[0]["status"], AutomationStatus.RUNNING.value)
        self.assertEqual(branches[0]["worker_lease_expires_at"]["$type"], "date")
        self.assertIn("$lte", branches[0]["worker_lease_expires_at"])
        self.assertEqual(
            branches[1],
            {
                "status": AutomationStatus.RUNNING.value,
                "worker_lease_expires_at": None,
                "updated_at": {"$lte": cutoff},
            },
        )
        self.assertEqual(
            branches[2],
            {
                "status": AutomationStatus.QUEUED.value,
                "created_at": {"$lte": cutoff},
            },
        )

    async def test_periodic_recovery_excludes_queued_and_legacy_runs(self):
        runs = MagicMock()
        runs.find.return_value.to_list = AsyncMock(return_value=[])
        db = MagicMock()
        db.automation_runs = runs
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            await automation_repository.recover_interrupted_runs(
                include_queued=False,
                include_legacy_running=False,
            )

        query = runs.find.call_args.args[0]
        self.assertEqual(query["status"]["$in"], [AutomationStatus.RUNNING.value])
        self.assertEqual(len(query["$or"]), 1)
        expired_lease = query["$or"][0]
        self.assertEqual(expired_lease["status"], AutomationStatus.RUNNING.value)
        self.assertEqual(expired_lease["worker_lease_expires_at"]["$type"], "date")
        self.assertIsInstance(expired_lease["worker_lease_expires_at"]["$lte"], datetime)
        self.assertNotIn("updated_at", expired_lease)
    async def test_stale_worker_checkpoint_is_rejected_after_run_revision_changes(self):
        run_updates = MagicMock()
        run_updates.find_one_and_update = AsyncMock(return_value=None)
        checkpoints = MagicMock()
        checkpoints.insert_one = AsyncMock()
        db = MagicMock(automation_runs=run_updates, automation_checkpoints=checkpoints)
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db
        infrastructure.mongodb.start_session = AsyncMock(return_value=MongoSession())
        checkpoint = AutomationCheckpoint(
            automation_run_id="AUT-RECOVERY-1",
            phase=AutomationCheckpointPhase.OBSERVED,
            status=AutomationStatus.RUNNING,
        )

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            saved = await automation_repository.save_checkpoint(
                checkpoint, expected_worker_revision=4
            )

        self.assertFalse(saved)
        checkpoints.insert_one.assert_not_awaited()
        recovery_filter = run_updates.find_one_and_update.call_args.args[0]
        self.assertEqual(recovery_filter["_id"], "AUT-RECOVERY-1")
        self.assertEqual(recovery_filter["revision"], 4)
        self.assertEqual(recovery_filter["status"], AutomationStatus.RUNNING.value)
        self.assertIsInstance(
            recovery_filter["worker_lease_expires_at"]["$gt"], datetime
        )

    async def test_worker_checkpoint_refreshes_lease_and_inserts_atomically(self):
        run_updates = MagicMock()
        run_updates.find_one_and_update = AsyncMock(return_value={"_id": "AUT-RECOVERY-1"})
        checkpoints = MagicMock()
        checkpoints.insert_one = AsyncMock()
        db = MagicMock(automation_runs=run_updates, automation_checkpoints=checkpoints)
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db
        infrastructure.mongodb.start_session = AsyncMock(return_value=MongoSession())
        checkpoint = AutomationCheckpoint(
            automation_run_id="AUT-RECOVERY-1",
            phase=AutomationCheckpointPhase.OBSERVED,
            status=AutomationStatus.RUNNING,
        )

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            saved = await automation_repository.save_checkpoint(
                checkpoint, expected_worker_revision=4
            )

        self.assertTrue(saved)
        update = run_updates.find_one_and_update.call_args
        self.assertEqual(update.args[0]["revision"], 4)
        self.assertEqual(update.args[1]["$set"]["worker_lease_expires_at"].tzinfo, timezone.utc)
        self.assertEqual(update.args[1]["$inc"]["checkpoint_sequence"], 1)
        checkpoints.insert_one.assert_awaited_once()
        self.assertEqual(
            checkpoints.insert_one.await_args.args[0]["checkpoint_sequence"], 1
        )

    async def test_unfenced_checkpoint_still_allocates_sequence_transactionally(self):
        run_updates = MagicMock()
        run_updates.find_one_and_update = AsyncMock(
            return_value={"_id": "AUT-RECOVERY-1", "checkpoint_sequence": 7}
        )
        checkpoints = MagicMock()
        checkpoints.insert_one = AsyncMock()
        db = MagicMock(automation_runs=run_updates, automation_checkpoints=checkpoints)
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db
        infrastructure.mongodb.start_session = AsyncMock(return_value=MongoSession())
        checkpoint = AutomationCheckpoint(
            automation_run_id="AUT-RECOVERY-1",
            phase=AutomationCheckpointPhase.QUEUED,
            status=AutomationStatus.QUEUED,
        )

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            saved = await automation_repository.save_checkpoint(checkpoint)

        self.assertTrue(saved)
        self.assertEqual(
            run_updates.find_one_and_update.await_args.args[1]["$inc"][
                "checkpoint_sequence"
            ],
            1,
        )
        self.assertEqual(
            checkpoints.insert_one.await_args.args[0]["checkpoint_sequence"], 7
        )
        self.assertIsNotNone(
            checkpoints.insert_one.await_args.kwargs.get("session")
        )

    async def test_latest_checkpoint_orders_by_monotonic_run_sequence(self):
        checkpoint = self.make_checkpoint_document(
            AutomationCheckpointPhase.OBSERVED
        )
        checkpoint["checkpoint_sequence"] = 12
        checkpoints = MagicMock()
        checkpoints.find_one = AsyncMock(return_value=checkpoint)
        db = MagicMock(automation_checkpoints=checkpoints)
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            latest = await automation_repository.latest_checkpoint("AUT-RECOVERY-1")

        self.assertEqual(latest.checkpoint_sequence, 12)
        self.assertEqual(
            checkpoints.find_one.call_args.kwargs["sort"],
            [
                ("checkpoint_sequence", -1),
                ("created_at", -1),
                ("_id", -1),
            ],
        )

    async def test_already_queued_run_is_returned_for_startup_redelivery(self):
        run_document = self.make_run_document()
        run_document.update(
            {
                "status": AutomationStatus.QUEUED.value,
                "revision": 5,
            }
        )
        runs = MagicMock()
        runs.find.return_value.to_list = AsyncMock(return_value=[run_document])
        runs.find_one_and_update = AsyncMock()
        checkpoints = MagicMock()
        checkpoints.find_one = AsyncMock()
        checkpoints.insert_one = AsyncMock()
        db = MagicMock(automation_runs=runs, automation_checkpoints=checkpoints)
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db
        infrastructure.mongodb.start_session = AsyncMock(return_value=MongoSession())

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            recovered = await automation_repository.recover_interrupted_runs()

        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].automation_run_id, "AUT-RECOVERY-1")
        self.assertEqual(recovered[0].status, AutomationStatus.QUEUED)
        self.assertEqual(recovered[0].revision, 5)
        runs.find_one_and_update.assert_not_awaited()
        checkpoints.find_one.assert_not_awaited()
        checkpoints.insert_one.assert_not_awaited()

    async def test_mutation_with_unknown_outcome_is_marked_degraded(self):
        checkpoint = self.make_checkpoint_document(
            AutomationCheckpointPhase.ACTION_STARTED,
            {"action": "MUTATE", "task_has_mutation": True},
        )

        run_document = self.make_run_document()
        degraded_document = deepcopy(run_document)
        degraded_document.update(
            {
                "status": AutomationStatus.DEGRADED.value,
                "error_code": "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
                "revision": run_document["revision"] + 1,
            }
        )
        runs = MagicMock()
        runs.find.return_value.to_list = AsyncMock(return_value=[run_document])
        runs.find_one_and_update = AsyncMock(return_value=degraded_document)
        checkpoints = MagicMock()
        checkpoints.find_one = AsyncMock(return_value=checkpoint)
        checkpoints.insert_one = AsyncMock()
        db = MagicMock(automation_runs=runs, automation_checkpoints=checkpoints)
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db
        infrastructure.mongodb.start_session = AsyncMock(return_value=MongoSession())

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            recovered = await automation_repository.recover_interrupted_runs()

        self.assertEqual(recovered[0].status, AutomationStatus.DEGRADED)
        self.assertEqual(
            recovered[0].error_code,
            "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
        )
        saved = checkpoints.insert_one.await_args.args[0]
        self.assertEqual(
            saved["detail"]["reason_code"], "AUTOMATION_ACTION_OUTCOME_UNCERTAIN"
        )
        self.assertIsNone(saved["state_snapshot"])
        self.assertFalse(saved["detail"]["retryable"])

    async def test_missing_checkpoint_is_marked_degraded(self):
        run_document = self.make_run_document()
        degraded_document = deepcopy(run_document)
        degraded_document.update(
            {
                "status": AutomationStatus.DEGRADED.value,
                "error_code": "AUTOMATION_INTERRUPTED_WITHOUT_CHECKPOINT",
                "revision": run_document["revision"] + 1,
            }
        )
        runs = MagicMock()
        runs.find.return_value.to_list = AsyncMock(return_value=[run_document])
        runs.find_one_and_update = AsyncMock(return_value=degraded_document)
        checkpoints = MagicMock()
        checkpoints.find_one = AsyncMock(return_value=None)
        checkpoints.insert_one = AsyncMock()
        db = MagicMock(automation_runs=runs, automation_checkpoints=checkpoints)
        infrastructure = MagicMock()
        infrastructure.mongodb.__getitem__.return_value = db
        infrastructure.mongodb.start_session = AsyncMock(return_value=MongoSession())

        with (
            patch("src.repositories.automation.database", infrastructure),
            patch("src.repositories.automation.settings.AI_DB_NAME", "test"),
        ):
            recovered = await automation_repository.recover_interrupted_runs()

        self.assertEqual(recovered[0].status, AutomationStatus.DEGRADED)
        self.assertEqual(
            recovered[0].error_code,
            "AUTOMATION_INTERRUPTED_WITHOUT_CHECKPOINT",
        )
        saved = checkpoints.insert_one.await_args.args[0]
        self.assertFalse(saved["detail"]["retryable"])
        self.assertIsNone(saved["state_snapshot"])

if __name__ == "__main__":
    unittest.main()
