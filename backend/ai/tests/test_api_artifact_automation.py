import json
import unittest
from unittest.mock import AsyncMock, patch

from src.tools import api_artifact


class ConfirmedApiOperationAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_reads_published_frozen_version_instead_of_publishing_again(self):
        operation = {
            "_id": "APIOP-1",
            "project_id": "PRJ-1",
            "revision": 3,
        }
        import_job = {
            "_id": "TIMP-1",
            "project_id": "PRJ-1",
            "source_api_operation_id": "APIOP-1",
            "status": "CONFIRMED",
            "created_draft_ids": ["TCD-1"],
        }
        source_evidence = [
            {
                "artifact_type": "api_operation",
                "artifact_version_id": "APIOP-1",
                "text": "GET /accounts returns the account list.",
            }
        ]
        evidence_quotes = [
            {
                "evidence_ref": "APIOP-1",
                "quote": "GET /accounts returns the account list.",
            }
        ]
        draft = {
            "_id": "TCD-1",
            "project_id": "PRJ-1",
            "origin": "ai_generated",
            "status": "APPROVED",
            "frozen_version_id": "TCV-1",
            "source_evidence": source_evidence,
            "requirement_version_ids": ["REQV-1"],
            "evidence_refs": ["APIOP-1"],
            "evidence_quotes": evidence_quotes,
            "coverage_obligations": [],
        }
        version = {
            "_id": "TCV-1",
            "project_id": "PRJ-1",
            "test_case_id": "TC-1",
            "status": "ACTIVE",
            "source_evidence": source_evidence,
            "requirement_version_ids": ["REQV-1"],
            "evidence_refs": ["APIOP-1"],
            "evidence_quotes": evidence_quotes,
            "coverage_obligations": [],
        }
        case = {
            "_id": "TC-1",
            "project_id": "PRJ-1",
            "status": "ACTIVE",
            "current_version_id": "TCV-1",
        }
        required_permissions = [
            "ai.generate_api_testcase",
            "testcase.import",
            "testcase.create",
            "testcase.read",
            "testcase.lint",
            "testcase.submit_review",
            "testcase.review",
            "testcase.version.read",
        ]

        async def fake_require(method, path, config, body=None):
            if method == "GET" and path == "/dac-ta-giao-dien/thao-tac/APIOP-1":
                return operation
            if method == "POST" and path == "/dac-ta-giao-dien/thao-tac/APIOP-1/sinh-ca-kiem-thu":
                return {
                    "_id": "TIMP-1",
                    "project_id": "PRJ-1",
                    "source_api_operation_id": "APIOP-1",
                    "status": "CONFIRMED",
                }
            if method == "GET" and path == "/nhap-ca-kiem-thu/TIMP-1":
                return import_job
            if method == "GET" and path == "/ban-nhap-ca-kiem-thu/TCD-1":
                return draft
            if method == "GET" and path == "/phien-ban-ca-kiem-thu/TCV-1":
                return version
            if method == "GET" and path == "/ca-kiem-thu/TC-1":
                return case
            raise AssertionError(f"Unexpected request: {method} {path}")

        config = {
            "configurable": {
                "project_id": "PRJ-1",
                "permissions": required_permissions,
            }
        }
        with (
            patch.object(api_artifact, "require_operation", new=AsyncMock(side_effect=fake_require)),
            patch.object(api_artifact, "publish_grounded_test_case", new=AsyncMock()) as publish,
            patch.object(api_artifact, "verified_test_case_publication_readback", return_value=True),
        ):
            result = json.loads(
                await api_artifact.process_confirmed_api_operation.ainvoke(
                {"operation_id": "APIOP-1", "expected_revision": 3},
                config=config,
                )
            )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(
            result["published_test_cases"],
            [
                {
                    "test_case_id": "TC-1",
                    "test_case_version_id": "TCV-1",
                    "publication_status": "ALREADY_PUBLISHED",
                }
            ],
        )
        publish.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
