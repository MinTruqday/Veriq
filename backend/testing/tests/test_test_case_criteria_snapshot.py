from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.design.services.test_case_records import (
    attach_manual_criterion_evidence,
    create_test_case_draft_record,
    update_test_case_draft_record,
)
from src.schemas.contracts.design import (
    TestCaseDraftCreate as DraftInput,
    TestCaseDraftPatch,
)


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


class ManualTestCaseEvidenceTests(unittest.IsolatedAsyncioTestCase):
    def make_payload(self, **changes):
        return DraftInput(
            title="Đăng nhập với email sai",
            origin="manual",
            requirement_version_ids=["REQV-1"],
            acceptance_criterion_ids=["AC-1"],
            **changes,
        )

    async def test_manual_selected_criterion_gets_exact_server_verified_citation(self):
        version = {"_id": "REQV-1", "plain_text_projection": "Đăng nhập."}
        criterion = {"_id": "AC-1", "plain_text": "Email sai định dạng phải bị từ chối."}
        with (
            patch(
                "src.modules.design.services.test_case_records.analysis_repository.list_requirement_versions",
                new=AsyncMock(return_value=[version]),
            ),
            patch(
                "src.modules.design.services.test_case_records.test_design_repository.list_acceptance_criteria_by_ids",
                new=AsyncMock(return_value=[criterion]),
            ),
        ):
            result = await attach_manual_criterion_evidence("PRJ-1", self.make_payload())

        self.assertEqual(result.evidence_refs, ["AC-1"])
        self.assertEqual(
            [item["artifact_version_id"] for item in result.source_evidence],
            ["REQV-1", "AC-1"],
        )
        self.assertEqual(
            [item.model_dump() if hasattr(item, "model_dump") else item for item in result.evidence_quotes],
            [{"evidence_ref": "AC-1", "quote": criterion["plain_text"]}],
        )

    async def test_manual_citation_is_not_added_when_the_user_supplied_one(self):
        quote = "Email sai định dạng phải bị từ chối."
        payload = self.make_payload(
            evidence_refs=["AC-1"],
            evidence_quotes=[{"evidence_ref": "AC-1", "quote": quote}],
            source_evidence=[{
                "artifact_type": "acceptance_criterion",
                "artifact_version_id": "AC-1",
                "text": quote,
            }],
        )
        with patch(
            "src.modules.design.services.test_case_records.analysis_repository.list_requirement_versions",
            new=AsyncMock(),
        ) as list_versions:
            result = await attach_manual_criterion_evidence("PRJ-1", payload)

        self.assertIs(result, payload)
        list_versions.assert_not_awaited()

    async def test_manual_citation_rejects_a_missing_selected_criterion(self):
        payload = self.make_payload()
        with (
            patch(
                "src.modules.design.services.test_case_records.analysis_repository.list_requirement_versions",
                new=AsyncMock(return_value=[{"_id": "REQV-1"}]),
            ),
            patch(
                "src.modules.design.services.test_case_records.test_design_repository.list_acceptance_criteria_by_ids",
                new=AsyncMock(return_value=[]),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await attach_manual_criterion_evidence("PRJ-1", payload)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "TEST_CASE_EVIDENCE_CHANGED")

    async def test_manual_draft_edit_refreshes_exact_selected_criterion_citation(self):
        draft = {
            "_id": "TCD-1",
            "project_id": "PRJ-1",
            "revision": 4,
            "status": "DRAFT",
            "origin": "manual",
            "title": "Đăng nhập với email sai",
            "requirement_version_ids": ["REQV-1"],
            "acceptance_criterion_ids": ["AC-1"],
            "evidence_refs": ["AC-1"],
            "evidence_quotes": [{"evidence_ref": "AC-1", "quote": "Trích dẫn cũ."}],
            "source_evidence": [{
                "artifact_type": "acceptance_criterion",
                "artifact_version_id": "AC-1",
                "text": "Trích dẫn cũ.",
            }],
            "coverage_obligations": [],
            "obligation_evidence": [],
            "challenge_hypotheses": [],
            "steps": [],
        }
        payload = TestCaseDraftPatch(expected_revision=4, title="Kiểm tra email sai định dạng")
        write = AsyncMock(return_value={**draft, "revision": 5, "title": payload.title})
        with (
            patch(
                "src.modules.design.services.test_case_records.get_project_entity",
                new=AsyncMock(return_value=draft),
            ),
            patch(
                "src.modules.design.services.test_case_records.validate_design_sources",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.design.services.test_case_records.validate_data_set_versions",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.design.services.test_case_records.validate_test_design_structure",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.design.services.test_case_records.validate_coverage_items",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.design.services.test_case_records.validate_test_case_custom_values",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.design.services.test_case_records.analysis_repository.list_requirement_versions",
                new=AsyncMock(return_value=[{"_id": "REQV-1", "plain_text_projection": "Đăng nhập."}]),
            ),
            patch(
                "src.modules.design.services.test_case_records.test_design_repository.list_acceptance_criteria_by_ids",
                new=AsyncMock(return_value=[{
                    "_id": "AC-1",
                    "plain_text": "Email sai định dạng phải bị từ chối.",
                }]),
            ),
            patch("src.modules.design.services.test_case_records.optimistic_patch", new=write),
            patch("src.modules.design.services.test_case_records.audit", new=AsyncMock()),
            patch(
                "src.modules.design.services.test_case_records.database.client",
                SimpleNamespace(start_session=AsyncMock(return_value=_AsyncSession())),
            ),
            patch("src.clients.ai_automation.emit_test_case_changed", new=AsyncMock()),
        ):
            result = await update_test_case_draft_record(
                "TCD-1", payload, SimpleNamespace(id="user-1")
            )

        written_changes = write.await_args.args[4]
        self.assertEqual(written_changes["evidence_refs"], ["AC-1"])
        self.assertEqual(written_changes["evidence_quotes"], [{
            "evidence_ref": "AC-1",
            "quote": "Email sai định dạng phải bị từ chối.",
        }])
        self.assertEqual(written_changes["source_evidence"][-1]["text"], "Email sai định dạng phải bị từ chối.")
        self.assertEqual(result["revision"], 5)


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
