import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

from fastapi import HTTPException
from pydantic import ValidationError

from src.modules.design.services import test_case_review as review
from src.modules.design.services import test_case_records as records
from src.modules.design.services.linters import lint_test_case
from src.repositories import common as common_repository_module
from src.repositories import test_case_review as review_repository_module
from src.schemas.contracts.design import (
    TestCaseBatchAccept as BatchAccept,
    TestCaseDraftCreate as DraftCreate,
    TestCaseMergeSave as MergeSave,
)


def document(text):
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


class TestCaseMergeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="qa", _ai_automation_run_id=None)
        self.draft = {
            **DraftCreate(title="Ca do AI đề xuất", steps=[{"id": "step-1", "order": 1, "action_doc": document("Nhập mã"), "expected_doc": document("Hiển thị kết quả")}]).model_dump(),
            "_id": "draft", "project_id": "project", "revision": 3, "status": "IN_REVIEW",
        }
        self.draft["ai_proposal_snapshot"] = review.proposal_snapshot(self.draft)
        self.context = {"draft": self.draft, "proposal": self.draft["ai_proposal_snapshot"], "proposal_available": True, "original": None, "stale_reasons": [], "comparison_token": "a" * 64}
        self.payload = MergeSave(expected_revision=3, comparison_token="a" * 64, operation_id="operation-1", result={**self.draft, "title": "Bản QA đã ghép"}, choices=[{"field": "title", "source": "MANUAL"}])

    async def test_duplicate_preflight_reads_all_active_versions_across_pages(self):
        pages = [
            [{"_id": "version-first", "test_case_id": "case-first"}],
            [{"_id": "version-after-2000", "test_case_id": "case-after-2000"}],
        ]

        async def iter_pages(*_args):
            for page in pages:
                yield page

        async def empty_draft_pages(*_args):
            if False:
                yield []

        drafts = []
        with (
            patch.object(records.analysis_repository, "iter_active_test_case_version_pages", new=iter_pages),
            patch.object(records.test_design_repository, "iter_case_draft_pages", new=empty_draft_pages),
            patch.object(records.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
        ):
            candidates, threshold = await records.comparison_cases("project")

        self.assertEqual([item["_id"] for item in candidates], ["version-first", "version-after-2000"])
        self.assertEqual(threshold, 0.72)

    async def test_duplicate_preflight_reads_all_unreviewed_drafts_across_pages(self):
        drafts = [
            [{"_id": "draft-first", "title": "Ca đầu"}],
            [{"_id": "draft-after-2000", "title": "Ca sau"}],
        ]

        async def empty_active_pages(*_args):
            if False:
                yield []

        async def draft_pages(*_args):
            for page in drafts:
                yield page

        with (
            patch.object(records.analysis_repository, "iter_active_test_case_version_pages", new=empty_active_pages),
            patch.object(records.test_design_repository, "iter_case_draft_pages", new=draft_pages),
            patch.object(records.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
        ):
            candidates, _threshold = await records.comparison_cases("project")

        self.assertEqual([item["_id"] for item in candidates], ["draft-first", "draft-after-2000"])

    async def test_duplicate_preflight_fails_closed_for_dangling_current_version(self):
        async def iter_pages(*_args):
            raise records.ActiveTestCaseVersionIntegrityError
            yield []

        with patch.object(records.analysis_repository, "iter_active_test_case_version_pages", new=iter_pages):
            with self.assertRaises(HTTPException) as raised:
                await records.comparison_cases("project")

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "TEST_CASE_CURRENT_VERSION_MISSING")

    def test_snapshot_is_deeply_detached_from_edited_result(self):
        snapshot = review.proposal_snapshot(self.draft)
        self.draft["steps"][0]["expected_doc"] = document("Nội dung mới")
        self.assertNotEqual(snapshot["steps"], self.draft["steps"])
        self.assertNotIn("status", snapshot)

    async def test_acceptance_criteria_read_is_paginated_without_dropping_tail(self):
        criteria = [{"_id": f"AC-{index:04d}"} for index in range(1001)]
        calls = []

        class Cursor:
            def __init__(self, page):
                self.page = page

            def sort(self, key, direction):
                self.assert_sort = (key, direction)
                return self

            async def to_list(self, length):
                return self.page[:length]

        class Collection:
            def find(self, query, session=None):
                calls.append((query, session))
                remaining = [
                    item for item in criteria
                    if "_id" not in query or item["_id"] > query["_id"]["$gt"]
                ]
                return Cursor(remaining)

        class Collections:
            def __getitem__(self, name):
                if name != "acceptance_criteria":
                    raise AssertionError(name)
                return Collection()

        session = object()
        with patch.object(
            common_repository_module,
            "database",
            SimpleNamespace(value=Collections()),
        ):
            result = await review.list_acceptance_criteria_in_session(
                "requirement-version", session
            )

        self.assertEqual(len(result), 1001)
        self.assertEqual(result[-1]["_id"], "AC-1000")
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(call[1] is session for call in calls))

    def test_duplicate_step_identity_is_rejected(self):
        value = deepcopy(self.draft)
        value["steps"].append({**value["steps"][0], "order": 2})
        with self.assertRaises(ValidationError):
            DraftCreate.model_validate(value)

    def test_bdd_expectation_does_not_require_duplicate_manual_expected_field(self):
        value = {**self.draft, "bdd": {"feature": "Đăng nhập", "scenario": "Thông tin hợp lệ", "steps": [
            {"id": "bdd-1", "keyword": "Given", "text": "Tài khoản tồn tại"},
            {"id": "bdd-2", "keyword": "When", "text": "Người dùng đăng nhập"},
            {"id": "bdd-3", "keyword": "Then", "text": "Mở trang tổng quan"},
        ]}, "requirement_version_ids": ["req-v1"]}
        self.assertNotIn("TCQ-001", {finding["rule_id"] for finding in lint_test_case(value)})

    def test_batch_rejects_duplicate_draft_selection(self):
        item = {"draft_id": "draft-1", "expected_revision": 1, "comparison_token": "a" * 64}
        with self.assertRaises(ValidationError):
            BatchAccept(items=[item, item], operation_id="batch-op-1", review_note="Duyệt nhóm")

    def test_duplicate_review_reason_is_editable_in_a_merge(self):
        patch_model = review.TestCaseDraftPatch(
            expected_revision=3,
            duplicate_reason="QA giữ riêng vì mục tiêu kiểm thử khác.",
        )
        self.assertEqual(
            patch_model.model_dump(exclude_unset=True)["duplicate_reason"],
            "QA giữ riêng vì mục tiêu kiểm thử khác.",
        )

    def test_source_choice_must_match_the_selected_immutable_value(self):
        proposal = {"title": "AI gợi ý", "steps": [{"id": "step-1", "action_doc": document("Mở trang")}]}
        review.validate_merge_choices(
            [{"field": "title", "source": "AI"}],
            {"title": "AI gợi ý"},
            None,
            proposal,
        )
        with self.assertRaises(HTTPException) as error:
            review.validate_merge_choices(
                [{"field": "title", "source": "AI"}],
                {"title": "Nội dung bị sửa nhưng khai AI"},
                None,
                proposal,
            )
        self.assertEqual(error.exception.detail["code"], "MERGE_CHOICE_VALUE_MISMATCH")

    def test_source_choice_can_accept_an_omitted_optional_field(self):
        proposal = {"title": "AI gợi ý"}
        review.validate_merge_choices(
            [{"field": "test_kind", "source": "AI"}],
            {"title": "AI gợi ý", "test_kind": None},
            None,
            proposal,
        )
        with self.assertRaises(HTTPException) as error:
            review.validate_merge_choices(
                [{"field": "test_kind", "source": "AI"}],
                {"title": "AI gợi ý", "test_kind": "security"},
                None,
                proposal,
            )
        self.assertEqual(error.exception.detail["code"], "MERGE_CHOICE_VALUE_MISMATCH")

    def test_step_source_choice_is_checked_by_stable_step_id(self):
        proposal = {"steps": [{"id": "step-ai", "action_doc": document("Bước AI")}]}
        review.validate_merge_choices(
            [{"field": "steps.action_doc", "step_id": "step-ai", "source": "AI"}],
            {"steps": [{"id": "step-ai", "action_doc": document("Bước AI")}]},
            None,
            proposal,
        )
        with self.assertRaises(HTTPException):
            review.validate_merge_choices(
                [{"field": "steps.action_doc", "step_id": "step-ai", "source": "AI"}],
                {"steps": [{"id": "step-ai", "action_doc": document("Bước khác")}]},
                None,
                proposal,
            )

    def test_step_absence_can_be_an_explicit_merge_choice(self):
        original = {"steps": [{"id": "step-original", "action_doc": document("Bước gốc")}]}
        proposal = {"steps": []}
        review.validate_merge_choices(
            [{"field": "steps", "step_id": "step-original", "source": "AI"}],
            {"steps": []},
            original,
            proposal,
        )
        review.validate_merge_choices(
            [{"field": "steps", "step_id": "step-ai", "source": "ORIGINAL"}],
            {"steps": []},
            original,
            {"steps": [{"id": "step-ai", "action_doc": document("Bước AI")}]},
        )
        with self.assertRaises(HTTPException) as error:
            review.validate_merge_choices(
                [{"field": "steps", "step_id": "step-ai", "source": "AI"}],
                {"steps": []},
                original,
                {"steps": [{"id": "step-ai", "action_doc": document("Bước AI")}]},
            )
        self.assertEqual(error.exception.detail["code"], "MERGE_CHOICE_VALUE_MISMATCH")

    def test_step_source_choice_can_accept_an_omitted_data_field(self):
        proposal = {"steps": [{"id": "step-ai", "action_doc": document("Bước AI")}]}
        review.validate_merge_choices(
            [{"field": "steps.test_data", "step_id": "step-ai", "source": "AI"}],
            {"steps": [{"id": "step-ai", "action_doc": document("Bước AI"), "test_data": {}}]},
            None,
            proposal,
        )
        with self.assertRaises(HTTPException) as error:
            review.validate_merge_choices(
                [{"field": "steps.test_data", "step_id": "step-ai", "source": "AI"}],
                {
                    "steps": [
                        {
                            "id": "step-ai",
                            "action_doc": document("Bước AI"),
                            "test_data": {"unexpected": "value"},
                        }
                    ]
                },
                None,
                proposal,
            )
        self.assertEqual(error.exception.detail["code"], "MERGE_CHOICE_VALUE_MISMATCH")

    def test_only_behavior_or_trace_edits_invalidate_coverage_proofs(self):
        self.assertFalse(review.merge_invalidates_coverage({"priority", "expected_impact"}))
        self.assertTrue(review.merge_invalidates_coverage({"steps"}))
        self.assertTrue(review.merge_invalidates_coverage({"requirement_version_ids"}))

    async def test_comparison_context_includes_project_custom_field_definitions(self):
        configured_fields = [
            {
                "_id": "field-browser",
                "key": "browser",
                "label": "Trình duyệt",
                "value_type": "choice",
                "choices": ["Chrome", "Firefox"],
                "status": "ACTIVE",
            }
        ]
        changed_fields = [
            {
                **configured_fields[0],
                "revision": 2,
                "choices": ["Chrome", "Firefox", "Safari"],
            }
        ]

        async def no_active_versions(*_args):
            if False:
                yield []

        with (
            patch.object(
                review,
                "get_project_entity",
                new=AsyncMock(return_value=self.draft),
            ),
            patch.object(
                review,
                "comparison_sources",
                new=AsyncMock(return_value={"sources": [], "parent": None, "stale_reasons": []}),
            ),
            patch.object(
                review.test_design_repository,
                "find_project_settings",
                new=AsyncMock(return_value={}),
            ),
            patch.object(
                review.test_design_repository,
                "list_all_test_case_custom_fields",
                new=AsyncMock(side_effect=[configured_fields, changed_fields]),
            ),
            patch.object(
                review.analysis_repository,
                "iter_active_test_case_version_pages",
                new=no_active_versions,
            ),
            patch.object(review, "lint_test_case", return_value=[]),
        ):
            result = await review.review_context("draft", self.user)
            refreshed = await review.review_context("draft", self.user)

        self.assertEqual(result["custom_fields"], configured_fields)
        self.assertNotEqual(result["comparison_token"], refreshed["comparison_token"])

    async def test_comparison_context_checks_every_active_case_page_for_duplicates(self):
        candidates = [
            {"_id": "version-a", "test_case_id": "case-a", "test_case_key": "TC-A"},
            {"_id": "version-z", "test_case_id": "case-z", "test_case_key": "TC-Z"},
        ]
        compared = []

        async def active_pages(*_args):
            yield candidates[:1]
            yield candidates[1:]

        def duplicate(_draft, candidate, _threshold):
            compared.append(candidate["_id"])
            return 0.9, ["title"]

        with (
            patch.object(review, "get_project_entity", new=AsyncMock(return_value=self.draft)),
            patch.object(
                review,
                "comparison_sources",
                new=AsyncMock(return_value={"sources": [], "parent": None, "stale_reasons": []}),
            ),
            patch.object(review.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
            patch.object(review.test_design_repository, "list_all_test_case_custom_fields", new=AsyncMock(return_value=[])),
            patch.object(review.analysis_repository, "iter_active_test_case_version_pages", new=active_pages),
            patch.object(review, "duplicate_score", side_effect=duplicate),
            patch.object(review, "lint_test_case", return_value=[]),
        ):
            result = await review.review_context("draft", self.user)

        self.assertEqual(compared, ["version-a", "version-z"])
        self.assertEqual(
            [item["version_id"] for item in result["duplicates"]],
            ["version-a", "version-z"],
        )

    async def test_publication_rechecks_duplicates_inside_transaction_fence(self):
        class Cursor:
            def __init__(self, items):
                self.items = items

            def sort(self, *_args):
                return self

            async def to_list(self, length):
                return self.items[:length]

        project_update = AsyncMock(return_value=SimpleNamespace(matched_count=1))
        active_case = {
            "_id": "case-existing",
            "test_case_key": "TC-EXISTING",
            "current_version_id": "version-existing",
        }
        current_version = {
            "_id": "version-existing",
            "test_case_id": "case-existing",
            "title": "Đăng nhập bằng thông tin hợp lệ",
        }
        cases = SimpleNamespace(
            find=Mock(return_value=Cursor([active_case]))
        )
        versions = SimpleNamespace(
            find_one=AsyncMock(),
            find=Mock(return_value=Cursor([current_version])),
        )
        db = SimpleNamespace(
            projects=SimpleNamespace(
                update_one=project_update,
                find_one=AsyncMock(return_value={"settings": {"testcase_duplicate_threshold": 0.72}}),
            ),
            test_cases=cases,
            test_case_versions=versions,
        )
        session = object()

        with (
            patch.object(review, "database", SimpleNamespace(value=db)),
            patch.object(review, "duplicate_score", return_value=(0.95, ["same_behavior"])),
        ):
            with self.assertRaises(HTTPException) as error:
                await review.validate_test_case_publication_uniqueness(
                    {**self.draft, "project_id": "project", "parent_version_id": None},
                    0.72,
                    session,
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_DUPLICATE_REVIEW_REQUIRED")
        self.assertEqual(error.exception.detail["matches"][0]["version_id"], "version-existing")
        project_update.assert_awaited_once_with(
            {"_id": "project"},
            {"$inc": {"test_case_publication_revision": 1}},
            session=session,
        )

    async def test_save_reopens_review_and_preserves_proposal(self):
        self.payload = self.payload.model_copy(
            update={
                "result": self.payload.result.model_copy(
                    update={"duplicate_reason": "QA xác nhận giữ riêng vì mục tiêu khác."}
                )
            }
        )
        with (
            patch.object(review, "review_context", new=AsyncMock(return_value=self.context)),
            patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=None)),
            patch.object(review, "comparison_sources", new=AsyncMock(return_value={"stale_reasons": []})),
            patch("src.modules.design.services.test_case_records.validate_design_sources", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_data_set_versions", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_test_design_structure", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_coverage_items", new=AsyncMock()),
            patch("src.modules.design.services.test_case_custom_fields.validate_test_case_custom_values", new=AsyncMock()),
            patch.object(review, "lint_test_case", return_value=[]),
            patch.object(review.test_case_review_repository, "merge", new=AsyncMock(return_value={"draft": {**self.draft, "revision": 4}})) as commit,
        ):
            await review.save_merged_test_case("draft", self.payload, self.user)
        changes = commit.await_args.args[1]
        decision = commit.await_args.args[2]
        self.assertEqual(changes["status"], "DRAFT")
        self.assertEqual(changes["title"], "Bản QA đã ghép")
        self.assertEqual(
            changes["duplicate_reason"], "QA xác nhận giữ riêng vì mục tiêu khác."
        )
        self.assertNotIn("ai_proposal_snapshot", changes)
        self.assertEqual(decision["details"]["result_revision"], 4)
        self.assertEqual(decision["actor_id"], "qa")
        self.assertEqual(self.draft["ai_proposal_snapshot"]["title"], "Ca do AI đề xuất")

    async def test_merge_attachment_change_requires_attachment_manage_permission(self):
        self.payload = self.payload.model_copy(
            update={
                "result": self.payload.result.model_copy(
                    update={
                        "attachments": [
                            {"filename": "evidence.txt", "url": "/tai-len/evidence.txt"}
                        ]
                    }
                )
            }
        )
        with (
            patch.object(review, "review_context", new=AsyncMock(return_value=self.context)),
            patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=None)),
            patch.object(
                review,
                "get_project",
                new=AsyncMock(side_effect=HTTPException(403, detail={"code": "PROJECT_PERMISSION_DENIED"})),
            ) as check_permission,
            patch.object(review.test_case_review_repository, "merge", new=AsyncMock()) as commit,
        ):
            with self.assertRaises(HTTPException) as error:
                await review.save_merged_test_case("draft", self.payload, self.user)

        self.assertEqual(error.exception.status_code, 403)
        check_permission.assert_awaited_once_with("project", self.user, "attachment.manage")
        commit.assert_not_awaited()

    async def test_merge_rejects_an_owner_who_is_not_an_active_project_member(self):
        self.payload = self.payload.model_copy(
            update={"result": self.payload.result.model_copy(update={"owner_id": "former-user"})}
        )
        with (
            patch.object(review, "review_context", new=AsyncMock(return_value=self.context)),
            patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=None)),
            patch.object(review, "get_project", new=AsyncMock(return_value={})) as check_permission,
            patch(
                "src.modules.design.services.test_case_records.validate_test_case_owner",
                new=AsyncMock(
                    side_effect=HTTPException(
                        422,
                        detail={"code": "TEST_CASE_OWNER_NOT_ACTIVE_PROJECT_MEMBER"},
                    )
                ),
            ) as validate_owner,
            patch.object(review.test_case_review_repository, "merge", new=AsyncMock()) as commit,
        ):
            with self.assertRaises(HTTPException) as error:
                await review.save_merged_test_case("draft", self.payload, self.user)

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_OWNER_NOT_ACTIVE_PROJECT_MEMBER")
        check_permission.assert_awaited_once_with("project", self.user, "project.members.read")
        validate_owner.assert_awaited_once_with("project", "former-user")
        commit.assert_not_awaited()

    async def test_merge_requires_member_read_permission_before_changing_owner(self):
        self.payload = self.payload.model_copy(
            update={"result": self.payload.result.model_copy(update={"owner_id": "tester"})}
        )
        with (
            patch.object(review, "review_context", new=AsyncMock(return_value=self.context)),
            patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=None)),
            patch.object(
                review,
                "get_project",
                new=AsyncMock(side_effect=HTTPException(403, detail={"code": "PROJECT_PERMISSION_DENIED"})),
            ) as check_permission,
            patch(
                "src.modules.design.services.test_case_records.validate_test_case_owner",
                new=AsyncMock(),
            ) as validate_owner,
            patch.object(review.test_case_review_repository, "merge", new=AsyncMock()) as commit,
        ):
            with self.assertRaises(HTTPException) as error:
                await review.save_merged_test_case("draft", self.payload, self.user)

        self.assertEqual(error.exception.status_code, 403)
        check_permission.assert_awaited_once_with("project", self.user, "project.members.read")
        validate_owner.assert_not_awaited()
        commit.assert_not_awaited()

    async def test_create_requires_member_read_permission_before_assigning_owner(self):
        payload = DraftCreate(
            title="Ca có người phụ trách",
            owner_id="tester",
            steps=[{"id": "step-1", "order": 1, "action_doc": document("Thực hiện"), "expected_doc": document("Thành công")}],
        )
        with (
            patch.object(
                records,
                "get_project",
                new=AsyncMock(
                    side_effect=[None, HTTPException(403, detail={"code": "PROJECT_PERMISSION_DENIED"})]
                ),
            ) as check_permission,
            patch.object(records, "validate_test_case_owner", new=AsyncMock()) as validate_owner,
        ):
            with self.assertRaises(HTTPException) as error:
                await records.create_test_case_draft_record("project", payload, self.user)

        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(
            check_permission.await_args_list,
            [
                call("project", self.user, "testcase.create"),
                call("project", self.user, "project.members.read"),
            ],
        )
        validate_owner.assert_not_awaited()

    async def test_test_case_owner_must_be_an_active_member_of_the_same_project(self):
        with patch.object(
            records.common_repository,
            "find_membership",
            new=AsyncMock(return_value={"_id": "membership", "user_id": "tester"}),
        ) as find_member:
            normalized_owner = await records.validate_test_case_owner("project", " tester ")
        self.assertEqual(normalized_owner, "tester")
        find_member.assert_awaited_once_with(
            "project", "tester", status="ACTIVE", projection={"_id": 1, "user_id": 1}
        )

        for membership in (None, {"_id": "inactive", "user_id": "tester", "status": "INACTIVE"}):
            with (
                self.subTest(membership=membership),
                patch.object(
                    records.common_repository,
                    "find_membership",
                    new=AsyncMock(return_value=membership),
                ),
            ):
                with self.assertRaises(HTTPException) as error:
                    await records.validate_test_case_owner("project", "tester")
                self.assertEqual(
                    error.exception.detail["code"],
                    "TEST_CASE_OWNER_NOT_ACTIVE_PROJECT_MEMBER",
                )

        with patch.object(records.common_repository, "find_membership", new=AsyncMock()) as find_member:
            await records.validate_test_case_owner("project", None)
        find_member.assert_not_awaited()

    async def test_merge_rejects_invalid_typed_custom_field_before_persisting(self):
        self.payload = self.payload.model_copy(
            update={
                "result": self.payload.result.model_copy(
                    update={"custom_values": {"browser": "Safari"}}
                )
            }
        )
        with (
            patch.object(review, "review_context", new=AsyncMock(return_value=self.context)),
            patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=None)),
            patch.object(review, "comparison_sources", new=AsyncMock(return_value={"stale_reasons": []})),
            patch("src.modules.design.services.test_case_records.validate_design_sources", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_data_set_versions", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_test_design_structure", new=AsyncMock()),
            patch("src.modules.design.services.test_case_records.validate_coverage_items", new=AsyncMock()),
            patch(
                "src.modules.design.services.test_case_custom_fields.validate_test_case_custom_values",
                new=AsyncMock(side_effect=HTTPException(422, detail={"code": "TEST_CASE_CUSTOM_FIELD_VALUE_INVALID"})),
            ),
            patch.object(review.test_case_review_repository, "merge", new=AsyncMock()) as commit,
        ):
            with self.assertRaises(HTTPException) as error:
                await review.save_merged_test_case("draft", self.payload, self.user)

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_CUSTOM_FIELD_VALUE_INVALID")
        commit.assert_not_awaited()

    async def test_stale_comparison_and_revision_do_not_write(self):
        for changes, code in (({"stale_reasons": ["SOURCE_EVIDENCE_CHANGED"]}, "TEST_CASE_COMPARISON_STALE"), ({"draft": {**self.draft, "revision": 4}}, "REVISION_CONFLICT")):
            with (
                self.subTest(code=code),
                patch.object(review, "review_context", new=AsyncMock(return_value={**self.context, **changes})),
                patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=None)),
                patch.object(review.test_case_review_repository, "merge", new=AsyncMock()) as commit,
            ):
                with self.assertRaises(HTTPException) as error:
                    await review.save_merged_test_case("draft", self.payload, self.user)
                self.assertEqual(error.exception.detail["code"], code)
                commit.assert_not_awaited()

    async def test_repeated_request_is_idempotent(self):
        decision_id = "TCMERGE-" + review.fingerprint(["draft", self.payload.operation_id])
        previous = {
            "_id": decision_id,
            "project_id": "project",
            "actor_id": "qa",
            "action": "test_case_merge_saved",
            "entity_type": "TestCaseDraft",
            "entity_id": "draft",
            "details": {
                "request_hash": review.fingerprint(self.payload.model_dump()),
                "base_revision": 3,
                "result_revision": 4,
            },
        }
        current = {
            **self.draft,
            "revision": 4,
            "merge_decision_ids": [decision_id],
        }
        with (
            patch.object(review, "review_context", new=AsyncMock(return_value={**self.context, "draft": current})),
            patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=previous)),
            patch.object(review.test_case_review_repository, "merge", new=AsyncMock()) as commit,
        ):
            result = await review.save_merged_test_case("draft", self.payload, self.user)
        self.assertTrue(result["idempotent"])
        self.assertEqual(result["applied_revision"], 4)
        commit.assert_not_awaited()

    async def test_repeated_request_rejects_corrupt_or_unlinked_receipt(self):
        decision_id = "TCMERGE-" + review.fingerprint(["draft", self.payload.operation_id])
        valid = {
            "_id": decision_id,
            "project_id": "project",
            "actor_id": "qa",
            "action": "test_case_merge_saved",
            "entity_type": "TestCaseDraft",
            "entity_id": "draft",
            "details": {
                "request_hash": review.fingerprint(self.payload.model_dump()),
                "base_revision": 3,
                "result_revision": 4,
            },
        }
        current = {
            **self.draft,
            "revision": 4,
            "merge_decision_ids": [decision_id],
        }
        invalid_receipts = [
            {**valid, "project_id": "another-project"},
            {**valid, "entity_id": "another-draft"},
            {**valid, "action": "another-action"},
            {**valid, "details": {**valid["details"], "result_revision": True}},
        ]
        for previous in invalid_receipts:
            with (
                self.subTest(previous=previous),
                patch.object(review, "review_context", new=AsyncMock(return_value={**self.context, "draft": current})),
                patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=previous)),
                patch.object(review.test_case_review_repository, "merge", new=AsyncMock()) as commit,
            ):
                with self.assertRaises(HTTPException) as error:
                    await review.save_merged_test_case("draft", self.payload, self.user)
                self.assertEqual(error.exception.detail["code"], "TEST_CASE_MERGE_INCOMPLETE")
                commit.assert_not_awaited()

        current_without_receipt = {**current, "merge_decision_ids": []}
        with (
            patch.object(review, "review_context", new=AsyncMock(return_value={**self.context, "draft": current_without_receipt})),
            patch.object(review.test_case_review_repository, "find_decision", new=AsyncMock(return_value=valid)),
            patch.object(review.test_case_review_repository, "merge", new=AsyncMock()) as commit,
        ):
            with self.assertRaises(HTTPException) as error:
                await review.save_merged_test_case("draft", self.payload, self.user)
            self.assertEqual(error.exception.detail["code"], "TEST_CASE_MERGE_INCOMPLETE")
            commit.assert_not_awaited()

    async def test_transaction_race_replay_requires_matching_persisted_draft(self):
        decision_id = "TCMERGE-" + review.fingerprint(["draft", self.payload.operation_id])
        request_hash = review.fingerprint(self.payload.model_dump())
        decision = {
            "_id": decision_id,
            "project_id": "project",
            "actor_id": "qa",
            "action": "test_case_merge_saved",
            "entity_type": "TestCaseDraft",
            "entity_id": "draft",
            "details": {
                "request_hash": request_hash,
                "base_revision": 3,
                "result_revision": 4,
            },
        }
        current = {
            **self.draft,
            "revision": 4,
            "merge_decision_ids": [decision_id],
        }

        class Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return False

            async def with_transaction(self, callback):
                return await callback(self)

        session = Session()
        audit_events = SimpleNamespace(find_one=AsyncMock(return_value=decision))
        test_case_drafts = SimpleNamespace(find_one=AsyncMock(return_value=current))
        value = SimpleNamespace(
            audit_events=audit_events,
            test_case_drafts=test_case_drafts,
        )
        database = SimpleNamespace(
            value=value,
            client=SimpleNamespace(start_session=AsyncMock(return_value=session)),
        )
        with patch.object(review_repository_module, "database", database):
            result = await review_repository_module.test_case_review_repository.merge(
                self.draft,
                {},
                decision,
            )

        self.assertTrue(result["idempotent"])
        self.assertEqual(result["draft"], current)
        self.assertEqual(result["applied_revision"], 4)
        audit_events.find_one.assert_awaited_once_with(
            {"_id": decision_id}, session=session
        )
        test_case_drafts.find_one.assert_awaited_once_with(
            {"_id": "draft", "project_id": "project"}, session=session
        )

        test_case_drafts.find_one.return_value = {
            **current,
            "merge_decision_ids": [],
        }
        with patch.object(review_repository_module, "database", database):
            with self.assertRaises(HTTPException) as error:
                await review_repository_module.test_case_review_repository.merge(
                    self.draft,
                    {},
                    decision,
                )
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_MERGE_INCOMPLETE")

    async def test_requirement_change_invalidates_proposal(self):
        draft = {**self.draft, "requirement_version_ids": ["v1"]}
        draft["ai_proposal_snapshot"] = {"source_evidence": [{"artifact_version_id": "v1", "text": "Nguồn trước"}]}
        with (
            patch.object(review.analysis_repository, "list_requirement_versions", new=AsyncMock(return_value=[{"_id": "v1", "requirement_id": "requirement", "plain_text_projection": "Nguồn sau", "status": "BASELINED"}])),
            patch.object(review.analysis_repository, "list_acceptance_criteria", new=AsyncMock(return_value=[])),
            patch.object(review.test_design_repository, "find_current_requirement", new=AsyncMock(return_value={"current_version_id": "v2"})),
        ):
            sources = await review.comparison_sources(draft)
        self.assertIn("REQUIREMENT_VERSION_CHANGED", sources["stale_reasons"])
        self.assertIn("SOURCE_EVIDENCE_CHANGED", sources["stale_reasons"])

    async def test_ai_identity_cannot_decide_the_merge(self):
        with self.assertRaises(HTTPException) as error:
            await review.save_merged_test_case("draft", self.payload, SimpleNamespace(id="qa", _ai_automation_run_id="run"))
        self.assertEqual(
            error.exception.detail["code"],
            "AUTOMATION_PUBLICATION_NOT_AUTHORIZED",
        )


if __name__ == "__main__":
    unittest.main()
