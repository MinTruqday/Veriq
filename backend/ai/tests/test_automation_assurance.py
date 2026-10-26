import json
import unittest
from unittest.mock import AsyncMock, patch

from src.tools.automation_assurance import refresh_assurance_after_test_case_approval
from src.tools.testing import AutomationOperationError


class AutomationAssuranceTests(unittest.IsolatedAsyncioTestCase):
    def config(self):
        return {
            "configurable": {
                "automation_run_id": "run-1",
                "evidence": [
                    {
                        "project_id": "project-1",
                        "artifact_type": "test_case_version",
                        "artifact_id": "case-version-1",
                    }
                ],
            }
        }

    async def test_approval_refreshes_each_linked_requirement_and_reads_back(self):
        current = {
            "_id": "assessment-1",
            "project_id": "project-1",
            "requirement_version_id": "requirement-version-1",
            "revision": 4,
            "coverage_items": [],
        }
        refreshed = {**current, "revision": 5}
        readback = {
            **refreshed,
            "coverage_items": [
                {"test_case_versions": [{"id": "case-version-1"}]}
            ],
        }
        with patch(
            "src.tools.automation_assurance.require_operation",
            new=AsyncMock(
                side_effect=[
                    {
                        "_id": "case-version-1",
                        "project_id": "project-1",
                        "status": "ACTIVE",
                        "requirement_version_ids": ["requirement-version-1"],
                    },
                    current,
                    refreshed,
                    readback,
                ]
            ),
        ) as operation:
            result = json.loads(
                await refresh_assurance_after_test_case_approval.ainvoke(
                    {"project_id": "project-1", "version_id": "case-version-1"},
                    self.config(),
                )
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["refreshed_assessments"][0]["revision"], 5)
        self.assertTrue(result["refreshed_assessments"][0]["mapped"])
        self.assertEqual(result["verification"]["status"], "COMPLETED")
        self.assertEqual(operation.await_args_list[2].args[1], "/phien-ban-yeu-cau/requirement-version-1/do-day-du-kiem-thu/lam-moi")
        self.assertEqual(operation.await_args_list[2].args[3], {"expected_revision": 4})

    async def test_missing_verified_event_blocks_without_api_mutation(self):
        config = self.config()
        config["configurable"]["evidence"] = []
        with patch(
            "src.tools.automation_assurance.require_operation", new=AsyncMock()
        ) as operation:
            result = json.loads(
                await refresh_assurance_after_test_case_approval.ainvoke(
                    {"project_id": "project-1", "version_id": "case-version-1"},
                    config,
                )
            )
        self.assertEqual(result["reason_code"], "VERIFIED_TEST_CASE_APPROVAL_EVENT_REQUIRED")
        operation.assert_not_awaited()

    async def test_revision_conflict_is_accepted_only_when_latest_snapshot_contains_case(self):
        current = {
            "_id": "assessment-1",
            "project_id": "project-1",
            "requirement_version_id": "requirement-version-1",
            "revision": 4,
            "coverage_items": [],
        }
        latest = {
            **current,
            "revision": 5,
            "coverage_items": [
                {"test_case_versions": [{"id": "case-version-1"}]}
            ],
        }
        with patch(
            "src.tools.automation_assurance.require_operation",
            new=AsyncMock(
                side_effect=[
                    {
                        "_id": "case-version-1",
                        "project_id": "project-1",
                        "status": "ACTIVE",
                        "requirement_version_ids": ["requirement-version-1"],
                    },
                    current,
                    AutomationOperationError("REVISION_CONFLICT"),
                    latest,
                    latest,
                ]
            ),
        ) as operation:
            result = json.loads(
                await refresh_assurance_after_test_case_approval.ainvoke(
                    {"project_id": "project-1", "version_id": "case-version-1"},
                    self.config(),
                )
            )

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["refreshed_assessments"][0]["mapped"])
        self.assertEqual(operation.await_count, 5)

    async def test_inactive_test_case_version_is_not_applied(self):
        with patch(
            "src.tools.automation_assurance.require_operation",
            new=AsyncMock(
                return_value={
                    "_id": "case-version-1",
                    "project_id": "project-1",
                    "status": "SUPERSEDED",
                    "requirement_version_ids": ["requirement-version-1"],
                }
            ),
        ) as operation:
            result = json.loads(
                await refresh_assurance_after_test_case_approval.ainvoke(
                    {"project_id": "project-1", "version_id": "case-version-1"},
                    self.config(),
                )
            )
        self.assertEqual(result["reason_code"], "TEST_CASE_VERSION_NOT_ACTIVE")
        self.assertEqual(operation.await_count, 1)

    async def test_unlinked_approved_case_completes_without_touching_another_requirement(self):
        with patch(
            "src.tools.automation_assurance.require_operation",
            new=AsyncMock(
                return_value={
                    "_id": "case-version-1",
                    "project_id": "project-1",
                    "status": "ACTIVE",
                    "requirement_version_ids": [],
                }
            ),
        ) as operation:
            result = json.loads(
                await refresh_assurance_after_test_case_approval.ainvoke(
                    {"project_id": "project-1", "version_id": "case-version-1"},
                    self.config(),
                )
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["refreshed_assessments"], [])
        self.assertEqual(operation.await_count, 1)


if __name__ == "__main__":
    unittest.main()
