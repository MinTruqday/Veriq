import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.integrations.services import api_artifact


class ApiOperationTestGenerationRecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.operation = {
            "_id": "APIOP-1",
            "project_id": "PRJ-1",
            "revision": 4,
            "import_id": "APIIMPORT-1",
        }
        self.user = SimpleNamespace(
            id="automation-user",
            _ai_automation_run_id="RUN-1",
            _ai_automation_trigger="API_OPERATION_CONFIRMED",
        )
        self.job = {
            "_id": "TIMP-existing",
            "project_id": "PRJ-1",
            "source_api_operation_id": "APIOP-1",
            "source_api_operation_fingerprint": "fingerprint-1",
            "status": "CONFIRMED",
            "created_draft_ids": ["TCD-1"],
        }

    async def test_retry_reads_existing_job_without_calling_model_again(self):
        with (
            patch.object(
                api_artifact, "get_project_entity", new=AsyncMock(return_value=self.operation)
            ),
            patch.object(api_artifact, "get_project", new=AsyncMock()),
            patch.object(
                api_artifact.api_artifact_repository,
                "find_import",
                new=AsyncMock(return_value={"status": "CONFIRMED"}),
            ),
            patch.object(
                api_artifact,
                "operation_fingerprint",
                return_value="fingerprint-1",
            ),
            patch.object(
                api_artifact.test_design_repository,
                "find_import",
                new=AsyncMock(return_value=self.job),
            ),
            patch.object(api_artifact, "request_ai_automation", new=AsyncMock()) as model,
        ):
            result = await api_artifact.generate_api_tests("APIOP-1", self.user)

        self.assertEqual(result["data"], self.job)
        model.assert_not_awaited()

    async def test_retry_rejects_existing_job_with_different_source_fingerprint(self):
        mismatched = {**self.job, "source_api_operation_fingerprint": "old-fingerprint"}
        with (
            patch.object(
                api_artifact, "get_project_entity", new=AsyncMock(return_value=self.operation)
            ),
            patch.object(api_artifact, "get_project", new=AsyncMock()),
            patch.object(
                api_artifact.api_artifact_repository,
                "find_import",
                new=AsyncMock(return_value={"status": "CONFIRMED"}),
            ),
            patch.object(
                api_artifact,
                "operation_fingerprint",
                return_value="fingerprint-1",
            ),
            patch.object(
                api_artifact.test_design_repository,
                "find_import",
                new=AsyncMock(return_value=mismatched),
            ),
            patch.object(api_artifact, "request_ai_automation", new=AsyncMock()) as model,
        ):
            with self.assertRaises(HTTPException) as raised:
                await api_artifact.generate_api_tests("APIOP-1", self.user)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "TEST_IMPORT_IDEMPOTENCY_CONFLICT"
        )
        model.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
