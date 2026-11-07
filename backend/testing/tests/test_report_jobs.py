import unittest
from unittest.mock import AsyncMock, patch

from src.modules.execution.services.report_jobs import enqueue_export


class ReportExportDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_requester_email_uses_worker_identity(self):
        job = {
            "_id": "REXP-test",
            "project_id": "PRJ-test",
            "requested_by": "user-test",
            "requester_email": "",
            "dispatch_generation": 0,
        }
        enqueue = AsyncMock(return_value={"job_id": "worker-job-test"})
        change = AsyncMock()

        with (
            patch("src.modules.execution.services.report_jobs.worker_client.enqueue", enqueue),
            patch("src.modules.execution.services.report_jobs.repository.change", change),
        ):
            await enqueue_export(job)

        self.assertEqual(enqueue.await_args.args[0]["requester_email"], "worker@internal")


if __name__ == "__main__":
    unittest.main()
