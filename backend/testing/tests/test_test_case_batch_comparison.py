import unittest
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

from fastapi import HTTPException

from src.modules.design.services.test_case_automation import (
    compare_test_case_draft_batch,
    find_duplicate_test_case_records,
)


class TestCaseBatchComparisonTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_project_duplicate_rule_and_returns_only_confirmed_pairs(self):
        candidates = [
            SimpleNamespace(model_dump=lambda: {"title": "first"}),
            SimpleNamespace(model_dump=lambda: {"title": "second"}),
            SimpleNamespace(model_dump=lambda: {"title": "third"}),
        ]

        with (
            patch(
                "src.modules.design.services.test_case_automation.get_project",
                new=AsyncMock(),
            ) as get_project,
            patch(
                "src.modules.design.services.test_case_automation.comparison_cases",
                new=AsyncMock(return_value=([], 0.72)),
            ) as comparison_cases,
            patch(
                "src.modules.design.services.test_case_automation.duplicate_score",
                side_effect=[(0.9, ["same behavior"]), (0.2, []), (0.8, ["same outcome"])],
            ) as duplicate_score,
        ):
            result = await compare_test_case_draft_batch("project-1", candidates, object())

        self.assertEqual(result["candidate_count"], 3)
        self.assertEqual(
            result["duplicates"],
            [
                {"left_index": 0, "right_index": 1, "similarity": 0.9, "reasons": ["same behavior"]},
                {"left_index": 1, "right_index": 2, "similarity": 0.8, "reasons": ["same outcome"]},
            ],
        )
        self.assertEqual(get_project.await_count, 2)
        comparison_cases.assert_awaited_once_with("project-1")
        self.assertEqual(duplicate_score.call_count, 3)

    async def test_targeted_duplicate_scan_compares_only_the_current_draft_revision(self):
        draft = {
            "_id": "draft-2",
            "project_id": "project-1",
            "revision": 4,
            "test_case_id": "case-1",
            "parent_version_id": "version-1",
            "title": "Updated sign-in lockout case",
        }
        versions = [
            {"_id": "version-1", "test_case_id": "case-1", "title": "Original case"},
            {"_id": "version-2", "test_case_id": "case-2", "title": "Similar case"},
            {"_id": "version-3", "test_case_id": "case-3", "title": "Different case"},
        ]

        with (
            patch(
                "src.modules.design.services.test_case_automation.get_project",
                new=AsyncMock(),
            ) as get_project,
            patch(
                "src.modules.design.services.test_case_automation.get_project_entity",
                new=AsyncMock(return_value=draft),
            ) as get_project_entity,
            patch(
                "src.modules.design.services.test_case_automation.analysis_repository.list_active_test_case_versions",
                new=AsyncMock(return_value=versions),
            ) as list_versions,
            patch(
                "src.modules.design.services.test_case_automation.test_design_repository.find_project_settings",
                new=AsyncMock(return_value={"testcase_duplicate_threshold": 0.8}),
            ),
            patch(
                "src.modules.design.services.test_case_automation.duplicate_score",
                side_effect=[(0.91, ["same behavior"]), (0.2, [])],
            ) as duplicate_score,
        ):
            result = await find_duplicate_test_case_records(
                "project-1", object(), test_case_draft_id="draft-2", expected_revision=4
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["left"]["_id"], "draft-2")
        self.assertEqual(result[0]["right"]["_id"], "version-2")
        self.assertEqual(result[0]["similarity"], 0.91)
        self.assertEqual(duplicate_score.call_count, 2)
        self.assertEqual(get_project.await_count, 2)
        get_project_entity.assert_awaited_once_with(
            "test_case_drafts", "draft-2", ANY, "testcase.read"
        )
        list_versions.assert_awaited_once_with("project-1", "ACTIVE")

    async def test_targeted_duplicate_scan_rejects_a_stale_event_revision(self):
        with (
            patch(
                "src.modules.design.services.test_case_automation.get_project",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.design.services.test_case_automation.get_project_entity",
                new=AsyncMock(
                    return_value={"project_id": "project-1", "revision": 5}
                ),
            ),
            patch(
                "src.modules.design.services.test_case_automation.analysis_repository.list_active_test_case_versions",
                new=AsyncMock(),
            ) as list_versions,
        ):
            with self.assertRaises(HTTPException) as error:
                await find_duplicate_test_case_records(
                    "project-1", object(), test_case_draft_id="draft-2", expected_revision=4
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_DRAFT_REVISION_STALE")
        list_versions.assert_not_awaited()

    async def test_targeted_duplicate_scan_requires_the_event_revision(self):
        with patch(
            "src.modules.design.services.test_case_automation.get_project",
            new=AsyncMock(),
        ):
            with self.assertRaises(HTTPException) as error:
                await find_duplicate_test_case_records(
                    "project-1", object(), test_case_draft_id="draft-2"
                )

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_DRAFT_REVISION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
