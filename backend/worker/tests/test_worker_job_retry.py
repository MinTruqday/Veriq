import hashlib
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.schemas import (
    TestingJobEvent as WorkerJobEvent,
    TestingJobRequest as WorkerJobRequest,
    WorkerJobStatus,
)
from src.services import WorkerJobService


class WorkerJobRetryTests(unittest.IsolatedAsyncioTestCase):
    def test_failed_status_matches_retry_state_machine(self):
        self.assertEqual(WorkerJobStatus.FAILED, "failed")

    async def test_retry_persists_outbox_before_returning_queued(self):
        claimed = {
            "_id": "qa-job-1",
            "status": "queued",
            "manual_retry_count": 3,
            "request": {"job_id": "qa-job-1"},
        }
        with (
            patch("src.services.worker_job_repository.find_one", new=AsyncMock(
                return_value={"status": "failed", "request": claimed["request"]}
            )),
            patch("src.services.worker_job_repository.claim_retry_with_outbox", new=AsyncMock(
                return_value=claimed
            )) as claim,
        ):
            result = await WorkerJobService.retry("qa-job-1")

        claim.assert_awaited_once_with("qa-job-1", 9)
        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["manual_retry_count"], 3)

    async def test_concurrent_retry_loser_does_not_publish(self):
        with (
            patch("src.services.worker_job_repository.find_one", new=AsyncMock(
                side_effect=[
                    {"status": "failed", "request": {"job_id": "qa-job-2"}},
                    {"status": "queued", "manual_retry_count": 1},
                ]
            )),
            patch("src.services.worker_job_repository.claim_retry_with_outbox", new=AsyncMock(
                return_value=None
            )),
        ):
            with self.assertRaises(HTTPException) as raised:
                await WorkerJobService.retry("qa-job-2")

        self.assertEqual(raised.exception.status_code, 409)

    async def test_enqueue_records_job_and_dispatch_outbox_as_one_repository_operation(self):
        payload = WorkerJobRequest(
            event=WorkerJobEvent.TEST_GENERATE,
            project_id="project-1",
            artifact_version_id="version-1",
            model_version="model-1",
            requester_id="user-1",
            requester_email="user@example.test",
            payload={"requirement_id": "requirement-1"},
        )
        with (
            patch("src.services.worker_job_repository.find_one", new=AsyncMock(return_value=None)),
            patch("src.services.worker_job_repository.create_job_with_outbox", new=AsyncMock()) as create,
        ):
            result = await WorkerJobService.enqueue(payload)

        self.assertEqual(result["status"], "queued")
        create.assert_awaited_once()
        job_id, values, insert, outbox = create.await_args.args
        self.assertEqual(values["status"], "queued")
        self.assertEqual(values["dispatch_generation"], 0)
        self.assertEqual(insert["request"]["job_id"], job_id)
        self.assertEqual(outbox["_id"], f"{job_id}:0")
        self.assertEqual(outbox["status"], "pending")

    async def test_existing_queued_job_repairs_missing_legacy_outbox(self):
        payload = WorkerJobRequest(
            event=WorkerJobEvent.TEST_GENERATE,
            project_id="project-1",
            artifact_version_id="version-1",
            model_version="model-1",
            requester_id="user-1",
            requester_email="user@example.test",
            payload={"requirement_id": "requirement-1"},
        )
        legacy_identity = ":".join(
            [
                payload.project_id,
                payload.artifact_version_id,
                payload.event.value,
                payload.model_version,
            ]
        )
        legacy_job_id = f"qa-{hashlib.sha256(legacy_identity.encode()).hexdigest()[:40]}"
        existing = {
            "_id": legacy_job_id,
            "status": "queued",
            "request": {"job_id": legacy_job_id, **payload.model_dump(mode="json")},
        }
        with (
            patch(
                "src.services.worker_job_repository.find_one",
                new=AsyncMock(side_effect=[None, existing]),
            ),
            patch("src.services.worker_job_repository.ensure_queued_job_outbox", new=AsyncMock()) as ensure,
        ):
            result = await WorkerJobService.enqueue(payload)

        self.assertEqual(result, {"job_id": legacy_job_id, "status": "queued"})
        ensure.assert_awaited_once_with(existing)

    async def test_different_payloads_for_same_artifact_get_distinct_job_keys(self):
        base = {
            "event": WorkerJobEvent.TEST_GENERATE,
            "project_id": "project-1",
            "artifact_version_id": "version-1",
            "model_version": "model-1",
            "requester_id": "user-1",
            "requester_email": "user@example.test",
        }
        with (
            patch("src.services.worker_job_repository.find_one", new=AsyncMock(return_value=None)),
            patch("src.services.worker_job_repository.create_job_with_outbox", new=AsyncMock()),
        ):
            first = await WorkerJobService.enqueue(
                WorkerJobRequest(**base, payload={"count": 2})
            )
            second = await WorkerJobService.enqueue(
                WorkerJobRequest(**base, payload={"count": 5})
            )

        self.assertNotEqual(first["job_id"], second["job_id"])

if __name__ == "__main__":
    unittest.main()
