import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.tools import testing_api
from src.tools.test_design_tools import recommend_test_design_techniques_for_requirement_change


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

    async def test_requirement_change_tool_accepts_testing_api_items_envelope(self):
        version = {
            "_id": "REQV-1",
            "project_id": "PRJ-1",
            "revision": 3,
            "status": "BASELINED",
        }
        responses = [
            json.dumps(version),
            json.dumps({"items": [{"technique": "BOUNDARY_VALUE"}]}),
            json.dumps(version),
        ]
        config = {
            "configurable": {
                "automation_run_id": "AUT-1",
                "evidence": [
                    {
                        "project_id": "PRJ-1",
                        "artifact_type": "requirement_version",
                        "artifact_version_id": "REQV-1",
                        "artifact_revision": 3,
                    }
                ],
            }
        }

        with patch(
            "src.tools.test_design_tools.call",
            new=AsyncMock(side_effect=responses),
        ):
            result = json.loads(
                await recommend_test_design_techniques_for_requirement_change.coroutine(
                    project_id="PRJ-1",
                    requirement_version_id="REQV-1",
                    expected_revision=3,
                    config=config,
                )
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            result["recommendation"]["items"],
            [{"technique": "BOUNDARY_VALUE"}],
        )

    async def test_requirement_change_tool_preserves_known_design_conflicts(self):
        version = {
            "_id": "REQV-1",
            "project_id": "PRJ-1",
            "revision": 3,
            "status": "BASELINED",
        }
        config = {
            "configurable": {
                "automation_run_id": "AUT-1",
                "evidence": [
                    {
                        "project_id": "PRJ-1",
                        "artifact_type": "requirement_version",
                        "artifact_version_id": "REQV-1",
                        "artifact_revision": 3,
                    }
                ],
            }
        }

        for error_code in (
            "TEST_DESIGN_REQUIREMENT_CHANGED",
            "TEST_DESIGN_PREVIEW_STALE",
        ):
            with self.subTest(error_code=error_code):
                with patch(
                    "src.tools.test_design_tools.call",
                    new=AsyncMock(
                        side_effect=[
                            json.dumps(version),
                            json.dumps(
                                {
                                    "status": "qa_operation_failed",
                                    "upstream_status": 409,
                                    "error": {"code": error_code},
                                }
                            ),
                        ]
                    ),
                ):
                    result = json.loads(
                        await recommend_test_design_techniques_for_requirement_change.coroutine(
                            project_id="PRJ-1",
                            requirement_version_id="REQV-1",
                            expected_revision=3,
                            config=config,
                        )
                    )

                self.assertEqual(result["status"], "automation_partial_failure")
                self.assertEqual(result["reason_code"], error_code)

    async def test_requirement_change_tool_does_not_preserve_unknown_conflict_code(self):
        version = {
            "_id": "REQV-1",
            "project_id": "PRJ-1",
            "revision": 3,
            "status": "BASELINED",
        }
        config = {
            "configurable": {
                "automation_run_id": "AUT-1",
                "evidence": [
                    {
                        "project_id": "PRJ-1",
                        "artifact_type": "requirement_version",
                        "artifact_version_id": "REQV-1",
                        "artifact_revision": 3,
                    }
                ],
            }
        }
        with patch(
            "src.tools.test_design_tools.call",
            new=AsyncMock(
                side_effect=[
                    json.dumps(version),
                    json.dumps(
                        {
                            "status": "qa_operation_failed",
                            "upstream_status": 409,
                            "error": {"code": "UNEXPECTED_CONFLICT"},
                        }
                    ),
                ]
            ),
        ):
            result = json.loads(
                await recommend_test_design_techniques_for_requirement_change.coroutine(
                    project_id="PRJ-1",
                    requirement_version_id="REQV-1",
                    expected_revision=3,
                    config=config,
                )
            )

        self.assertEqual(result["status"], "automation_partial_failure")
        self.assertEqual(
            result["reason_code"], "TECHNIQUE_RECOMMENDATION_RESULT_INVALID"
        )


if __name__ == "__main__":
    unittest.main()
