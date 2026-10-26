import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.jobs.outbox import dispatch_outbox_once
from src.jobs.task import handle_testing_job


class WorkerJobOutboxTests(unittest.IsolatedAsyncioTestCase):
    async def test_unconfirmed_publish_is_rescheduled_without_counting_as_queued(self):
        entry = {
            "_id": "job-1:0",
            "job_id": "job-1",
            "dispatch_generation": 0,
            "payload": {"job_id": "job-1"},
            "attempt_count": 1,
        }
        with (
            patch("src.jobs.outbox.worker_job_repository.claim_next_outbox", new=AsyncMock(return_value=entry)) as claim,
            patch("src.jobs.outbox.mq.publish", new=AsyncMock(return_value=False)),
            patch("src.jobs.outbox.worker_job_repository.reschedule_outbox", new=AsyncMock()) as reschedule,
            patch("src.jobs.outbox.worker_job_repository.mark_outbox_published", new=AsyncMock()) as mark_published,
            patch("src.jobs.outbox.metrics_collector.change_queue_depth") as metric,
        ):
            self.assertTrue(await dispatch_outbox_once())

        claim.assert_awaited_once()
        reschedule.assert_awaited_once()
        self.assertEqual(reschedule.await_args.args[0:2], ("job-1:0", claim.await_args.args[0]))
        self.assertGreaterEqual(reschedule.await_args.args[3], datetime.now(timezone.utc))
        mark_published.assert_not_awaited()
        metric.assert_not_called()

    async def test_confirmed_publish_marks_outbox_and_updates_queue_depth(self):
        entry = {
            "_id": "job-2:0",
            "job_id": "job-2",
            "dispatch_generation": 0,
            "payload": {"job_id": "job-2"},
            "attempt_count": 1,
        }
        with (
            patch("src.jobs.outbox.worker_job_repository.claim_next_outbox", new=AsyncMock(return_value=entry)) as claim,
            patch("src.jobs.outbox.mq.publish", new=AsyncMock(return_value=True)),
            patch(
                "src.jobs.outbox.worker_job_repository.mark_outbox_published",
                new=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
            ) as mark_published,
            patch("src.jobs.outbox.worker_job_repository.reschedule_outbox", new=AsyncMock()) as reschedule,
            patch("src.jobs.outbox.metrics_collector.change_queue_depth") as metric,
        ):
            self.assertTrue(await dispatch_outbox_once())

        mark_published.assert_awaited_once()
        self.assertEqual(mark_published.await_args.args[0], "job-2:0")
        self.assertEqual(mark_published.await_args.args[1], claim.await_args.args[0])
        reschedule.assert_not_awaited()
        metric.assert_called_once()
        self.assertEqual(metric.call_args.args[1], 1)

    async def test_lost_outbox_lease_does_not_increment_queue_depth(self):
        entry = {
            "_id": "job-4:0",
            "job_id": "job-4",
            "dispatch_generation": 0,
            "payload": {"job_id": "job-4"},
            "attempt_count": 1,
        }
        lost_lease = type("UpdateResult", (), {"matched_count": 0})()
        with (
            patch("src.jobs.outbox.worker_job_repository.claim_next_outbox", new=AsyncMock(return_value=entry)),
            patch("src.jobs.outbox.mq.publish", new=AsyncMock(return_value=True)),
            patch(
                "src.jobs.outbox.worker_job_repository.mark_outbox_published",
                new=AsyncMock(return_value=lost_lease),
            ),
            patch("src.jobs.outbox.metrics_collector.change_queue_depth") as metric,
        ):
            self.assertTrue(await dispatch_outbox_once())

        metric.assert_not_called()

    async def test_empty_outbox_does_not_publish(self):
        with (
            patch("src.jobs.outbox.worker_job_repository.claim_next_outbox", new=AsyncMock(return_value=None)),
            patch("src.jobs.outbox.mq.publish", new=AsyncMock()) as publish,
        ):
            self.assertFalse(await dispatch_outbox_once())
        publish.assert_not_awaited()

    async def test_duplicate_delivery_does_not_execute_a_running_job_again(self):
        payload = {
            "job_id": "job-3",
            "requester_id": "user-1",
            "requester_email": "user@example.test",
            "event": "requirement.extract.requested",
            "project_id": "project-1",
            "payload": {"requirement_id": "requirement-1"},
        }
        with (
            patch("src.jobs.task.worker_job_repository.claim_execution", new=AsyncMock(return_value=None)),
            patch("src.jobs.task.worker_job_repository.find_one", new=AsyncMock(return_value={"status": "running"})),
            patch("src.jobs.task.httpx.AsyncClient") as client,
        ):
            await handle_testing_job(payload)

        client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
