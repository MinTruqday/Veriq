import json
import unittest
from unittest.mock import AsyncMock, patch

from src.tools.automation_execution import process_recorded_test_execution


class AutomationExecutionTests(unittest.IsolatedAsyncioTestCase):
    def config(self):
        return {
            "configurable": {
                "automation_run_id": "run-1",
                "evidence": [
                    {
                        "project_id": "project-1",
                        "artifact_type": "test_result",
                        "artifact_id": "result-1",
                        "artifact_revision": 1,
                        "text": "FAIL result from verified outbox event",
                    }
                ],
            }
        }

    async def test_multiple_linked_defects_are_not_silently_reduced_to_first(self):
        with patch(
            "src.tools.automation_execution.require_operation",
            new=AsyncMock(
                return_value={
                    "_id": "result-1",
                    "project_id": "project-1",
                    "status": "FAIL",
                    "revision": 1,
                    "test_case_version_id": "case-version-1",
                    "defects": [{"_id": "defect-1"}, {"_id": "defect-2"}],
                }
            ),
        ) as operation:
            result = json.loads(
                await process_recorded_test_execution.ainvoke(
                    {"project_id": "project-1", "result_id": "result-1", "expected_revision": 1},
                    self.config(),
                )
            )

        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["reason_code"], "MULTIPLE_LINKED_DEFECTS_REQUIRE_REVIEW")
        self.assertEqual(result["linked_defect_ids"], ["defect-1", "defect-2"])
        self.assertEqual(result["feedback_recorded"], 0)
        operation.assert_awaited_once()

    async def test_single_linked_defect_updates_only_mapped_assurance_and_reads_back(self):
        assessment = {
            "_id": "assessment-1",
            "project_id": "project-1",
            "revision": 3,
            "coverage_items": [
                {
                    "coverage_item_id": "coverage-1",
                    "test_case_versions": [{"id": "case-version-1"}],
                    "execution_feedback": [],
                },
                {
                    "coverage_item_id": "coverage-unrelated",
                    "test_case_versions": [{"id": "other-case-version"}],
                    "execution_feedback": [],
                },
            ],
        }
        updated = {**assessment, "revision": 4}
        readback = {
            **updated,
            "coverage_items": [
                {
                    "coverage_item_id": "coverage-1",
                    "test_case_versions": [{"id": "case-version-1"}],
                    "execution_feedback": [
                        {
                            "test_result_id": "result-1",
                            "test_result_revision": 1,
                            "outcome": "CAUGHT_DEFECT",
                        }
                    ],
                },
                assessment["coverage_items"][1],
            ],
        }
        with patch(
            "src.tools.automation_execution.require_operation",
            new=AsyncMock(
                side_effect=[
                    {
                        "_id": "result-1",
                        "project_id": "project-1",
                        "status": "FAIL",
                        "revision": 1,
                        "test_case_version_id": "case-version-1",
                        "test_case_version": {
                            "requirement_version_ids": ["requirement-version-1"]
                        },
                        "defects": [{"_id": "defect-1"}],
                    },
                    assessment,
                    updated,
                    readback,
                ]
            ),
        ) as operation:
            result = json.loads(
                await process_recorded_test_execution.ainvoke(
                    {"project_id": "project-1", "result_id": "result-1", "expected_revision": 1},
                    self.config(),
                )
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["feedback_recorded"], 1)
        self.assertEqual(result["coverage_item_ids"], ["coverage-1"])
        self.assertEqual(operation.await_args_list[2].args[3]["defect_id"], "defect-1")
        self.assertEqual(operation.await_count, 4)

    async def test_superseded_execution_event_is_a_verified_noop(self):
        with patch(
            "src.tools.automation_execution.require_operation",
            new=AsyncMock(
                return_value={
                    "_id": "result-1",
                    "project_id": "project-1",
                    "revision": 2,
                    "status": "PASS",
                }
            ),
        ) as operation:
            result = json.loads(
                await process_recorded_test_execution.ainvoke(
                    {
                        "project_id": "project-1",
                        "result_id": "result-1",
                        "expected_revision": 1,
                    },
                    self.config(),
                )
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["reason_code"], "TEST_RESULT_EVENT_SUPERSEDED")
        self.assertEqual(result["verification"]["status"], "COMPLETED")
        operation.assert_awaited_once()

