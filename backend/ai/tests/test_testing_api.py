import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.tools import testing_api


class TestingApiErrorHandlingTests(unittest.IsolatedAsyncioTestCase):
    def test_safe_validation_issue_metadata_excludes_document_content(self):
        metadata = testing_api.safe_validation_issue_metadata(
            {
                "detail": [
                    {
                        "loc": ["body", "instruction"],
                        "type": "string_too_long",
                        "msg": "String should have at most 3000 characters",
                        "input": "PRIVATE_DOCUMENT_TEXT",
                        "ctx": {"max_length": 3000},
                    }
                ]
            }
        )

        self.assertEqual(
            metadata,
            [{"loc": ["body", "instruction"], "type": "string_too_long"}],
        )
        self.assertNotIn("PRIVATE_DOCUMENT_TEXT", json.dumps(metadata))

    def test_safe_validation_issue_metadata_ignores_unstructured_errors(self):
        self.assertEqual(
            testing_api.safe_validation_issue_metadata(
                {"detail": "PRIVATE_DOCUMENT_TEXT"}
            ),
            [],
        )

    def test_safe_validation_issue_metadata_reads_testing_error_envelope(self):
        metadata = testing_api.safe_validation_issue_metadata(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "details": {
                        "issues": [
                            {
                                "loc": ["body", "instruction"],
                                "type": "string_too_long",
                                "msg": "String should have at most 5000 characters",
                                "input": "PRIVATE_DOCUMENT_TEXT",
                            }
                        ]
                    },
                }
            }
        )

        self.assertEqual(
            metadata,
            [{"loc": ["body", "instruction"], "type": "string_too_long"}],
        )
        self.assertNotIn("PRIVATE_DOCUMENT_TEXT", json.dumps(metadata))

    async def test_string_error_detail_is_preserved_as_a_safe_upstream_failure(self):
        response = SimpleNamespace(
            status_code=403,
            json=lambda: {"detail": "Project access denied"},
        )
        with patch(
            "src.tools.testing_api.make_api_request", new=AsyncMock(return_value=response)
        ):
            result = await testing_api.call("GET", "/du-an/p1", {"configurable": {"token": "Bearer x"}})

        decoded = json.loads(result)
        self.assertEqual(decoded["status"], "qa_operation_failed")
        self.assertEqual(decoded["upstream_status"], 403)
        self.assertEqual(decoded["error"]["code"], "UPSTREAM_REQUEST_FAILED")
        self.assertEqual(decoded["error"]["message"], "Project access denied")

    async def test_typed_upstream_error_code_survives_normalization(self):
        response = SimpleNamespace(
            status_code=409,
            json=lambda: {"detail": {"code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"}},
        )
        with patch(
            "src.tools.testing_api.make_api_request", new=AsyncMock(return_value=response)
        ):
            result = await testing_api.call("POST", "/principal", {"configurable": {"token": "Bearer x"}})

        self.assertEqual(json.loads(result)["error"], {"code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"})


if __name__ == "__main__":
    unittest.main()
