import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.design.services.test_case_custom_fields import (
    _valid_value,
    create_test_case_custom_field,
    inherit_custom_values,
    update_test_case_custom_field,
    validate_test_case_custom_values,
)
from src.modules.design.services.test_case_lifecycle import build_test_case_version
from src.schemas.contracts.design import (
    TestCaseCustomFieldCreate as CustomFieldCreate,
    TestCaseCustomFieldPatch as CustomFieldPatch,
    TestCaseDraftCreate as DraftCreate,
    TestCaseFreezeInput as FreezeInput,
)


class TestCaseCustomFieldTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fields = [
            {"key": "browser", "value_type": "choice", "choices": ["Chrome", "Firefox"], "required": True},
            {"key": "attempts", "value_type": "number", "required": False},
            {"key": "is_mobile", "value_type": "boolean", "required": False},
            {"key": "test_date", "value_type": "date", "required": False},
            {"key": "note", "value_type": "text", "required": False},
        ]

    def test_typed_values_are_checked_without_coercion(self):
        cases = [
            ("browser", "choice", "Chrome", True),
            ("browser", "choice", "Safari", False),
            ("attempts", "number", 2, True),
            ("attempts", "number", True, False),
            ("is_mobile", "boolean", False, True),
            ("is_mobile", "boolean", 0, False),
            ("test_date", "date", "2026-10-24", True),
            ("test_date", "date", "24/10/2026", False),
            ("note", "text", "verified", True),
            ("note", "text", 42, False),
        ]
        for key, value_type, value, expected in cases:
            with self.subTest(key=key, value=value):
                self.assertEqual(
                    _valid_value({"key": key, "value_type": value_type, "choices": ["Chrome", "Firefox"]}, value),
                    expected,
                )

    def test_field_schema_requires_choices_only_for_choice_type(self):
        field = CustomFieldCreate(
            key="browser", label="Trình duyệt", value_type="choice", choices=["Chrome"]
        )
        self.assertEqual(field.value_type, "choice")
        with self.assertRaises(ValueError):
            CustomFieldCreate(
                key="browser", label="Trình duyệt", value_type="choice"
            )
        with self.assertRaises(ValueError):
            CustomFieldCreate(
                key="attempts", label="Số lần", value_type="number", choices=["1"]
            )

    def test_field_patch_requires_revision_and_a_change(self):
        payload = CustomFieldPatch(expected_revision=4, status="INACTIVE")
        self.assertEqual(payload.expected_revision, 4)
        self.assertEqual(
            CustomFieldPatch(expected_revision=4, label="  Tên  trường ").label,
            "Tên trường",
        )
        with self.assertRaises(ValueError):
            CustomFieldPatch(expected_revision=4)
        with self.assertRaises(ValueError):
            CustomFieldPatch(expected_revision=0, label="Mã")
        with self.assertRaises(ValueError):
            CustomFieldPatch(expected_revision=4, label=None, required=True)

    def test_custom_values_are_part_of_test_case_contract(self):
        draft = DraftCreate(title="Đăng nhập", custom_values={"browser": "Chrome"})
        self.assertEqual(draft.custom_values, {"browser": "Chrome"})

    def test_required_skills_are_normalized_deduplicated_and_versioned(self):
        draft_input = DraftCreate(
            title="API permission",
            required_skills=[" API Testing ", "api testing", "Security"],
        )
        self.assertEqual(draft_input.required_skills, ["API Testing", "Security"])
        draft = {
            "project_id": "PRJ-1", "test_case_key": "TC-1", "title": "API permission",
            "type": "happy_path", "priority": "medium", "risk": "medium",
            "preconditions_doc": {"type": "doc", "content": []}, "steps": [],
            "test_data": {}, "expected_result_doc": {"type": "doc", "content": []},
            "postconditions_doc": {"type": "doc", "content": []}, "tags": [],
            "custom_values": {}, "required_skills": draft_input.required_skills,
            "automation_status": "manual", "requirement_version_ids": [],
            "acceptance_criterion_ids": [], "origin": "manual",
        }
        version = build_test_case_version(
            draft, "TC-1", 1, None, FreezeInput(expected_revision=1),
            SimpleNamespace(id="qa-1"), "2026-10-24T00:00:00Z",
        )
        self.assertEqual(version["required_skills"], ["API Testing", "Security"])

    def test_ai_version_proposal_inherits_existing_manual_values(self):
        current = {"custom_values": {"browser": "Chrome", "test_date": "2026-10-24"}}
        self.assertEqual(inherit_custom_values({}, current), current["custom_values"])
        self.assertEqual(
            inherit_custom_values({"browser": "Firefox"}, current),
            {"browser": "Firefox"},
        )

    def test_custom_values_are_frozen_into_immutable_version(self):
        values = {"browser": "Chrome", "attempts": 2}
        draft = {
            "project_id": "PRJ-1",
            "test_case_key": "TC-1",
            "title": "Đăng nhập",
            "type": "happy_path",
            "priority": "medium",
            "risk": "medium",
            "preconditions_doc": {"type": "doc", "content": []},
            "steps": [],
            "test_data": {},
            "expected_result_doc": {"type": "doc", "content": []},
            "postconditions_doc": {"type": "doc", "content": []},
            "tags": [],
            "custom_values": values,
            "automation_status": "manual",
            "requirement_version_ids": [],
            "acceptance_criterion_ids": [],
            "origin": "manual",
        }
        version = build_test_case_version(
            draft,
            "TC-1",
            1,
            None,
            FreezeInput(expected_revision=1),
            SimpleNamespace(id="qa-1"),
            "2026-10-24T00:00:00Z",
        )
        self.assertEqual(version["custom_values"], values)

    async def test_validation_rejects_missing_required_unknown_and_wrong_type(self):
        with patch(
            "src.modules.design.services.test_case_custom_fields.test_design_repository.list_all_test_case_custom_fields",
            new=AsyncMock(return_value=self.fields),
        ):
            for values, code in (
                ({}, "TEST_CASE_CUSTOM_FIELD_REQUIRED"),
                ({"browser": "Chrome", "unknown": "x"}, "TEST_CASE_CUSTOM_FIELD_UNKNOWN"),
                ({"browser": "Safari"}, "TEST_CASE_CUSTOM_FIELD_VALUE_INVALID"),
                ({"browser": "Chrome", "attempts": True}, "TEST_CASE_CUSTOM_FIELD_VALUE_INVALID"),
            ):
                with self.subTest(values=values):
                    with self.assertRaises(HTTPException) as raised:
                        await validate_test_case_custom_values(
                            "PRJ-1", values, enforce_required=True
                        )
                    self.assertEqual(raised.exception.status_code, 422)
                    self.assertEqual(raised.exception.detail["code"], code)

    async def test_valid_custom_values_pass(self):
        with patch(
            "src.modules.design.services.test_case_custom_fields.test_design_repository.list_all_test_case_custom_fields",
            new=AsyncMock(return_value=self.fields),
        ):
            await validate_test_case_custom_values(
                "PRJ-1",
                {
                    "browser": "Chrome",
                    "attempts": 2,
                    "is_mobile": False,
                    "test_date": "2026-10-24",
                    "note": "Nguồn được xác nhận",
                },
            )

    async def test_review_schema_uses_stable_order_for_comparison_fingerprints(self):
        from src.repositories.test_design import TestDesignRepository

        class Cursor:
            def __init__(self):
                self.sort_spec = None

            def sort(self, spec):
                self.sort_spec = spec
                return self

            async def to_list(self, length):
                self.limit = length
                return []

        cursor = Cursor()

        class Collection:
            def find(self, query):
                self.query = query
                return cursor

        database_stub = SimpleNamespace(
            value=SimpleNamespace(test_case_custom_fields=Collection())
        )
        with patch("src.repositories.test_design.database", database_stub):
            await TestDesignRepository().list_all_test_case_custom_fields("PRJ-1")

        self.assertEqual(cursor.sort_spec, [("created_at", 1), ("_id", 1)])
        self.assertEqual(cursor.limit, 200)

    async def test_only_project_qa_can_configure_fields(self):
        payload = CustomFieldCreate(
            key="browser", label="Trình duyệt", value_type="text"
        )
        user = SimpleNamespace(id="qa-1", is_system_admin=False)
        with (
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project",
                new=AsyncMock(return_value={"_id": "PRJ-1"}),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project_roles",
                new=AsyncMock(return_value=["QA"]),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.test_design_repository.insert_test_case_custom_field",
                new=AsyncMock(),
            ) as insert,
            patch(
                "src.modules.design.services.test_case_custom_fields.audit", new=AsyncMock()
            ),
        ):
            created = await create_test_case_custom_field("PRJ-1", payload, user)
            self.assertEqual(created["key"], "browser")
            self.assertEqual(created["revision"], 1)
            insert.assert_awaited_once()

        with (
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project",
                new=AsyncMock(return_value={"_id": "PRJ-1"}),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project_roles",
                new=AsyncMock(return_value=["TESTER"]),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await create_test_case_custom_field("PRJ-1", payload, user)
            self.assertEqual(raised.exception.status_code, 403)

        platform_admin = SimpleNamespace(id="admin-1", is_system_admin=True)
        with (
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project",
                new=AsyncMock(return_value={"_id": "PRJ-1"}),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project_roles",
                new=AsyncMock(return_value=["ADMIN"]),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await create_test_case_custom_field("PRJ-1", payload, platform_admin)
            self.assertEqual(raised.exception.status_code, 403)

    async def test_inactive_field_is_accepted_for_old_values_but_not_required(self):
        fields = [
            {
                "key": "browser",
                "value_type": "choice",
                "choices": ["Chrome"],
                "required": True,
                "status": "INACTIVE",
            }
        ]
        with patch(
            "src.modules.design.services.test_case_custom_fields.test_design_repository.list_all_test_case_custom_fields",
            new=AsyncMock(return_value=fields),
        ):
            await validate_test_case_custom_values("PRJ-1", {}, enforce_required=True)
            await validate_test_case_custom_values(
                "PRJ-1", {"browser": "Chrome"}, enforce_required=True
            )

    async def test_qa_can_update_field_with_revision_and_audit(self):
        payload = CustomFieldPatch(expected_revision=1, label="Trình duyệt web", required=True)
        current = {
            "_id": "TCF-1",
            "project_id": "PRJ-1",
            "key": "browser",
            "label": "Trình duyệt",
            "value_type": "choice",
            "choices": ["Chrome"],
            "required": False,
            "status": "ACTIVE",
            "revision": 1,
        }
        updated = {**current, "label": "Trình duyệt web", "required": True, "revision": 2}
        user = SimpleNamespace(id="qa-1", is_system_admin=False)
        with (
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project",
                new=AsyncMock(return_value={"_id": "PRJ-1"}),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project_roles",
                new=AsyncMock(return_value=["QA"]),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.test_design_repository.find_test_case_custom_field",
                new=AsyncMock(side_effect=[current]),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.test_design_repository.update_test_case_custom_field",
                new=AsyncMock(return_value=updated),
            ) as update,
            patch(
                "src.modules.design.services.test_case_custom_fields.audit", new=AsyncMock()
            ) as audit,
        ):
            result = await update_test_case_custom_field("PRJ-1", "TCF-1", payload, user)
        self.assertEqual(result["revision"], 2)
        self.assertEqual(result["value_type"], "choice")
        self.assertEqual(result["choices"], ["Chrome"])
        self.assertEqual(update.await_args.args[2], 1)
        audit.assert_awaited_once()

    async def test_update_rejects_stale_revision_and_non_qa(self):
        payload = CustomFieldPatch(expected_revision=1, status="INACTIVE")
        user = SimpleNamespace(id="tester-1", is_system_admin=False)
        current = {"_id": "TCF-1", "project_id": "PRJ-1", "revision": 2}
        with (
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project",
                new=AsyncMock(return_value={"_id": "PRJ-1"}),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project_roles",
                new=AsyncMock(return_value=["QA"]),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.test_design_repository.find_test_case_custom_field",
                new=AsyncMock(return_value=current),
            ),
        ):
            with self.assertRaises(HTTPException) as stale:
                await update_test_case_custom_field("PRJ-1", "TCF-1", payload, user)
            self.assertEqual(stale.exception.status_code, 409)
            self.assertEqual(stale.exception.detail["code"], "REVISION_CONFLICT")

        with (
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project",
                new=AsyncMock(return_value={"_id": "PRJ-1"}),
            ),
            patch(
                "src.modules.design.services.test_case_custom_fields.get_project_roles",
                new=AsyncMock(return_value=["TESTER"]),
            ),
        ):
            with self.assertRaises(HTTPException) as forbidden:
                await update_test_case_custom_field("PRJ-1", "TCF-1", payload, user)
            self.assertEqual(forbidden.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
