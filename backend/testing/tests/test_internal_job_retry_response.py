import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.operations.api import internal_jobs


class InternalJobRetryResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_retryable_job_failure_is_not_acknowledged_as_http_success(self):
        with patch.object(
            internal_jobs,
            "process_delegated_job",
            new=AsyncMock(
                return_value={
                    "status": "FAILED",
                    "error_code": "KNOWLEDGE_INDEX_FAILED",
                    "retryable": True,
                    "state_after_failure": "INDEX_FAILED",
                }
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await internal_jobs.process_job(
                    "knowledge.index.requested",
                    {"project_id": "project-1"},
                    "requester-1",
                    "qa@example.test",
                    None,
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(
            raised.exception.detail,
            {
                "code": "KNOWLEDGE_INDEX_FAILED",
                "retryable": True,
                "state_after_failure": "INDEX_FAILED",
            },
        )

    async def test_completed_job_keeps_success_response(self):
        with patch.object(
            internal_jobs,
            "process_delegated_job",
            new=AsyncMock(return_value={"status": "COMPLETED", "result": {"indexed": True}}),
        ):
            result = await internal_jobs.process_job(
                "knowledge.index.requested",
                {"project_id": "project-1"},
                "requester-1",
                "qa@example.test",
                None,
            )

        self.assertEqual(result["data"]["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
