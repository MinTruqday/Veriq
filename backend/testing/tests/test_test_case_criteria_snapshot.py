from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.design.services.test_case_records import create_test_case_draft_record
from src.schemas.contracts.design import TestCaseDraftCreate as DraftInput


class GeneratedTestCaseCriteriaSnapshotTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.version = {
            "_id": "REQV-1",
            "requirement_id": "REQ-1",
            "project_id": "PRJ-1",
            "status": "BASELINED",
            "plain_text_projection": "Người dùng có thể đăng nhập.",
        }
        self.criteria = [
            {"_id": "AC-1", "plain_text": "Dùng email đã đăng ký."},
            {"_id": "AC-2", "plain_text": "Mật khẩu đúng."},
            {"_id": "AC-3", "plain_text": "Đăng nhập thành công."},
        ]
        self.payload = DraftInput(
            title="Đăng nhập với mật khẩu đúng",
            origin="ai_generated",
            requirement_version_ids=["REQV-1"],
            acceptance_criterion_ids=["AC-2"],
            source_evidence=[
                {
                    "artifact_type": "requirement_version",
                    "artifact_version_id": "REQV-1",
                    "text": "Người dùng có thể đăng nhập.",
                },
                {
                    "artifact_type": "acceptance_criterion",
                    "artifact_version_id": "AC-2",
                    "text": "Mật khẩu đúng.",
                },
            ],
            evidence_refs=["REQV-1", "AC-2"],
            suite_signature="suite-v1",
            acceptance_criteria_snapshot_ids=["AC-1", "AC-2", "AC-3"],
        )

    async def run_create(self, current_criteria):
        patches = (
            patch("src.modules.design.services.test_case_records.get_project", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_design_sources", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_data_set_versions", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_test_design_structure", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_coverage_items", new=AsyncMock()),
            patch(
                "src.modules.design.services.test_case_records.analysis_repository.list_requirement_versions",
                new=AsyncMock(return_value=[self.version]),
            ),
            patch(
                "src.modules.design.services.test_case_records.require_current_baselined_version",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.design.services.test_case_records.comparison_cases",
                new=AsyncMock(return_value=([], 0.72)),
            ),
            patch(
                "src.modules.design.services.test_case_records.active_suite_signature",
                return_value="suite-v1",
            ),
            patch(
                "src.modules.design.services.test_case_records.analysis_repository.list_acceptance_criteria",
                new=AsyncMock(return_value=current_criteria),
            ),
            patch(
                "src.modules.design.services.test_case_records.test_design_repository.list_acceptance_criteria_by_ids",
                new=AsyncMock(return_value=[self.criteria[1]]),
            ),
            patch(
                "src.modules.design.services.test_case_records.test_design_repository.insert_case_draft",
                new=AsyncMock(),
            ),
            patch("src.modules.design.services.test_case_records.audit", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.next_key", new=AsyncMock(return_value="TC-1")),
            patch("src.clients.ai_automation.emit_test_case_changed", new=AsyncMock()),
            patch(
                "src.modules.design.services.test_case_records.database.client",
                SimpleNamespace(start_session=AsyncMock(return_value=_AsyncSession())),
            ),
        )
        with ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            return await create_test_case_draft_record(
                "PRJ-1", self.payload, SimpleNamespace(id="user-1", _ai_automation_run_id="AUT-1")
            )

    async def test_selected_criterion_citation_saves_against_full_unchanged_snapshot(self):
        draft = await self.run_create(self.criteria)

        self.assertEqual(draft["acceptance_criterion_ids"], ["AC-2"])
        self.assertEqual(
            [item["artifact_version_id"] for item in draft["source_evidence"]],
            ["REQV-1", "AC-2"],
        )
        self.assertNotIn("acceptance_criteria_snapshot_ids", draft)

    async def test_new_criterion_after_preview_rejects_without_saving(self):
        changed = [*self.criteria, {"_id": "AC-4", "plain_text": "Mã xác thực hợp lệ."}]

        with self.assertRaises(HTTPException) as raised:
            await self.run_create(changed)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "TEST_CASE_EVIDENCE_CHANGED")


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _AsyncSession(_AsyncContext):
    def start_transaction(self):
        return _AsyncContext()


if __name__ == "__main__":
    unittest.main()
