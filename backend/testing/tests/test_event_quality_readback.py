import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.modules.design.services import test_case_lifecycle
from src.modules.requirements.services import requirement_ai


class EventQualityReadbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_requirement_analysis_read_requires_project_read_permission(self):
        version = {"_id": "REQV-1", "project_id": "PRJ-1", "revision": 5}
        finding = {"_id": "AIF-1", "artifact_revision": 5}
        user = SimpleNamespace(id="USER-1")
        with (
            patch.object(
                requirement_ai,
                "get_project_entity",
                new=AsyncMock(return_value=version),
            ) as get_version,
            patch.object(
                requirement_ai.requirement_ai_repository,
                "find_latest_quality_analysis",
                new=AsyncMock(return_value=finding),
            ) as find_latest,
        ):
            result = await requirement_ai.get_latest_requirement_quality_analysis(
                version["_id"], user
            )

        get_version.assert_awaited_once_with(
            "requirement_versions", "REQV-1", user, "requirement.read"
        )
        find_latest.assert_awaited_once_with("PRJ-1", "REQV-1")
        self.assertFalse(result["is_stale"])

    async def test_test_case_analysis_read_marks_previous_revision_stale(self):
        draft = {"_id": "TCD-1", "project_id": "PRJ-1", "revision": 7}
        finding = {"_id": "AIF-2", "artifact_revision": 6}
        user = SimpleNamespace(id="USER-1")
        with (
            patch.object(
                test_case_lifecycle,
                "get_project_entity",
                new=AsyncMock(return_value=draft),
            ) as get_draft,
            patch.object(
                test_case_lifecycle.test_design_repository,
                "find_latest_test_draft_lint",
                new=AsyncMock(return_value=finding),
            ) as find_latest,
        ):
            result = await test_case_lifecycle.get_latest_test_case_draft_lint(
                draft["_id"], user
            )

        get_draft.assert_awaited_once_with(
            "test_case_drafts", "TCD-1", user, "testcase.read"
        )
        find_latest.assert_awaited_once_with("PRJ-1", "TCD-1")
        self.assertTrue(result["is_stale"])
