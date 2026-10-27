import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.modules.design.services import test_case_batch_review as batch_review
from src.schemas.contracts.design import TestCaseBatchAccept as BatchAccept


def document(value):
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": value}]}],
    }


def draft(draft_id, key, *, parent_version_id=None, duplicate_reason=None):
    return {
        "_id": draft_id,
        "project_id": "project-1",
        "test_case_key": key,
        "title": "Kiểm tra đăng nhập thành công",
        "type": "FUNCTIONAL",
        "revision": 2,
        "status": "IN_REVIEW",
        "origin": "manual",
        "priority": "MEDIUM",
        "risk": "MEDIUM",
        "preconditions_doc": document("Điều kiện trước"),
        "expected_result_doc": document("Mở trang chính"),
        "postconditions_doc": document("Không có thay đổi ngoài dự kiến"),
        "test_data": {},
        "tags": [],
        "techniques": [],
        "automation_status": "MANUAL",
        "attachments": [],
        "data_set_version_ids": [],
        "requirement_version_ids": [],
        "acceptance_criterion_ids": [],
        "parent_version_id": parent_version_id,
        "duplicate_reason": duplicate_reason,
        "steps": [{"id": f"step-{draft_id}", "action_doc": document("Đăng nhập"), "expected_doc": document("Mở trang chính")}],
    }


def payload(*items):
    return BatchAccept(
        items=[
            {"draft_id": item["_id"], "expected_revision": item["revision"], "comparison_token": "a" * 64}
            for item in items
        ],
        operation_id="batch-operation-1",
        review_note="QA đã rà soát nội dung và nguồn.",
    )


class TestCaseBatchReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="qa-1", _ai_automation_run_id=None)
        validator = patch.object(
            batch_review, "validate_test_case_custom_values", new=AsyncMock()
        )
        validator.start()
        self.addCleanup(validator.stop)

    async def test_invalid_typed_custom_field_blocks_batch_before_transaction(self):
        item = draft("draft-1", "TC-1")
        context = {
            "draft": {**item, "custom_values": {"browser": "Safari"}},
            "comparison_token": "a" * 64,
            "stale_reasons": [],
            "duplicates": [],
        }
        start_session = AsyncMock()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=start_session),
            value=SimpleNamespace(
                audit_events=SimpleNamespace(find_one=AsyncMock(return_value=None))
            ),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(
                batch_review.test_design_repository,
                "find_project_settings",
                new=AsyncMock(return_value={"testcase_duplicate_threshold": 0.72}),
            ),
            patch.object(batch_review, "review_context", new=AsyncMock(return_value=context)),
            patch.object(batch_review, "validate_review_sources_before_approval", new=AsyncMock()),
            patch.object(
                batch_review,
                "validate_test_case_custom_values",
                new=AsyncMock(
                    side_effect=HTTPException(
                        422, detail={"code": "TEST_CASE_CUSTOM_FIELD_VALUE_INVALID"}
                    )
                ),
            ),
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group(
                    "project-1", payload(item), self.user
                )

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(
            error.exception.detail["code"], "TEST_CASE_CUSTOM_FIELD_VALUE_INVALID"
        )
        start_session.assert_not_awaited()

    async def test_batch_idempotent_replay_retries_only_derived_finalization(self):
        draft_record = {
            "_id": "draft-1",
            "project_id": "project-1",
            "status": "APPROVED",
            "frozen_version_id": "version-1",
        }
        version_record = {"_id": "version-1", "project_id": "project-1"}
        db = SimpleNamespace(
            value=SimpleNamespace(
                test_case_drafts=SimpleNamespace(find_one=AsyncMock(return_value=draft_record)),
                test_case_versions=SimpleNamespace(find_one=AsyncMock(return_value=version_record)),
            )
        )
        result = {
            "batch_id": "batch-1",
            "count": 1,
            "draft_ids": ["draft-1"],
            "version_ids": ["version-1"],
            "idempotent": True,
        }
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "_verify_batch_publication_links", new=AsyncMock()),
            patch.object(batch_review, "finalize_test_case_derivatives", new=AsyncMock(return_value=True)) as finalize,
        ):
            recovered = await batch_review._retry_batch_derived_state(
                result, "project-1", self.user
            )

        self.assertEqual(recovered["derived_pending_version_ids"], [])
        finalize.assert_awaited_once_with(draft_record, version_record, self.user)

    async def test_idempotent_batch_reports_failed_or_missing_versions_as_pending(self):
        versions = SimpleNamespace(
            find=unittest.mock.Mock(
                return_value=SimpleNamespace(
                    to_list=AsyncMock(
                        return_value=[
                            {
                                "_id": "version-ready",
                                "index_status": "INDEXED",
                                "trace_status": "READY",
                                "approval_audit_status": "READY",
                                "adequacy_invalidation_status": "READY",
                            },
                            {
                                "_id": "version-pending",
                                "index_status": "INDEXED",
                                "trace_status": "READY",
                                "approval_audit_status": "READY",
                                "adequacy_invalidation_status": "FAILED",
                            },
                        ]
                    )
                )
            )
        )
        db = SimpleNamespace(value=SimpleNamespace(test_case_versions=versions))

        with patch.object(batch_review, "database", db):
            result = await batch_review._result_with_derived_state(
                {
                    "version_ids": [
                        "version-ready",
                        "version-pending",
                        "version-missing",
                    ]
                }
            )

        self.assertEqual(
            result["derived_pending_version_ids"],
            ["version-missing", "version-pending"],
        )

    async def test_duplicate_against_active_case_blocks_batch_without_recorded_reason(self):
        item = draft("draft-1", "TC-1")
        context = {"draft": item, "comparison_token": "a" * 64, "stale_reasons": [], "duplicates": [{"version_id": "version-1", "test_case_key": "TC-OLD"}]}
        start_session = AsyncMock()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=start_session),
            value=SimpleNamespace(audit_events=SimpleNamespace(find_one=AsyncMock(return_value=None))),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(batch_review.test_design_repository, "find_project_settings", new=AsyncMock(return_value={"testcase_duplicate_threshold": 0.72})),
            patch.object(batch_review, "review_context", new=AsyncMock(return_value=context)),
            patch.object(batch_review, "has_verifiable_steps", return_value=True),
            patch.object(batch_review, "validate_review_sources_before_approval", new=AsyncMock()),
            patch.object(batch_review, "lint_test_case", return_value=[]),
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group("project-1", payload(item), self.user)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_DUPLICATE_REVIEW_REQUIRED")
        start_session.assert_not_awaited()

    async def test_updated_case_cannot_bypass_duplicate_review_for_another_active_case(self):
        item = draft("draft-update", "TC-UPDATE", parent_version_id="version-own-case")
        context = {
            "draft": item,
            "comparison_token": "a" * 64,
            "stale_reasons": [],
            "duplicates": [{"version_id": "version-other-case", "test_case_key": "TC-OTHER"}],
        }
        start_session = AsyncMock()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=start_session),
            value=SimpleNamespace(audit_events=SimpleNamespace(find_one=AsyncMock(return_value=None))),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(batch_review.test_design_repository, "find_project_settings", new=AsyncMock(return_value={"testcase_duplicate_threshold": 0.72})),
            patch.object(batch_review, "review_context", new=AsyncMock(return_value=context)),
            patch.object(batch_review, "has_verifiable_steps", return_value=True),
            patch.object(batch_review, "validate_review_sources_before_approval", new=AsyncMock()),
            patch.object(batch_review, "lint_test_case", return_value=[]),
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group("project-1", payload(item), self.user)

        self.assertEqual(error.exception.detail["code"], "TEST_CASE_DUPLICATE_REVIEW_REQUIRED")
        self.assertEqual(error.exception.detail["matches"][0]["test_case_key"], "TC-OTHER")
        start_session.assert_not_awaited()

    async def test_similar_items_inside_group_require_explicit_reason(self):
        first, second = draft("draft-1", "TC-1"), draft("draft-2", "TC-2")
        contexts = [
            {"draft": item, "comparison_token": "a" * 64, "stale_reasons": [], "duplicates": []}
            for item in (first, second)
        ]
        start_session = AsyncMock()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=start_session),
            value=SimpleNamespace(audit_events=SimpleNamespace(find_one=AsyncMock(return_value=None))),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(batch_review.test_design_repository, "find_project_settings", new=AsyncMock(return_value={"testcase_duplicate_threshold": 0.72})),
            patch.object(batch_review, "review_context", new=AsyncMock(side_effect=contexts)),
            patch.object(batch_review, "has_verifiable_steps", return_value=True),
            patch.object(batch_review, "validate_review_sources_before_approval", new=AsyncMock()),
            patch.object(batch_review, "lint_test_case", return_value=[]),
            patch.object(batch_review, "duplicate_score", return_value=(0.95, ["same_behavior"])),
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group("project-1", payload(first, second), self.user)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_BATCH_DUPLICATE_REVIEW_REQUIRED")
        self.assertEqual(error.exception.detail["draft_id"], "draft-2")
        start_session.assert_not_awaited()

    async def test_tester_cannot_use_qa_batch_approval(self):
        with (
            patch.object(batch_review, "get_project", new=AsyncMock(side_effect=HTTPException(403, detail={"code": "PROJECT_PERMISSION_DENIED"}))) as get_project,
            patch.object(batch_review, "review_context", new=AsyncMock()) as review_context,
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group("project-1", payload(draft("draft-1", "TC-1")), self.user)
        self.assertEqual(error.exception.status_code, 403)
        get_project.assert_awaited_once_with("project-1", self.user, "testcase.approve")
        review_context.assert_not_awaited()

    async def test_repeated_group_request_returns_existing_result_without_republishing(self):
        item = draft("draft-1", "TC-1")
        request = payload(item)
        request_hash = batch_review.fingerprint(request.model_dump())
        previous = {
            "_id": "TCBATCH-existing",
            "project_id": "project-1",
            "actor_id": self.user.id,
            "action": "test_case_group_approved",
            "entity_type": "TestCaseApprovalGroup",
            "entity_id": "TCBATCH-existing",
            "details": {
                "request_hash": request_hash,
                "result": {
                    "batch_id": "TCBATCH-existing",
                    "count": 1,
                    "draft_ids": [item["_id"]],
                    "version_ids": ["version-1"],
                    "idempotent": False,
                },
            },
        }
        transaction = AsyncMock()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=transaction),
            value=SimpleNamespace(
                audit_events=SimpleNamespace(find_one=AsyncMock(return_value=previous))
            ),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(batch_review, "_verify_batch_publication_links", new=AsyncMock()),
            patch.object(
                batch_review,
                "_retry_batch_derived_state",
                new=AsyncMock(
                    return_value={
                        **previous["details"]["result"],
                        "idempotent": True,
                    }
                ),
            ) as retry,
            patch.object(batch_review, "_result_with_derived_state", new=AsyncMock(return_value={
                **previous["details"]["result"],
                "derived_pending_version_ids": [],
            })) as derived,
        ):
            result = await batch_review.accept_test_case_group("project-1", request, self.user)

        self.assertTrue(result["idempotent"])
        self.assertEqual(result["version_ids"], ["version-1"])
        transaction.assert_not_awaited()
        derived.assert_awaited_once_with(previous["details"]["result"])
        retry.assert_awaited_once_with(
            {
                **previous["details"]["result"],
                "derived_pending_version_ids": [],
                "idempotent": True,
            },
            "project-1",
            self.user,
        )

    async def test_reused_group_operation_id_with_different_payload_is_rejected(self):
        item = draft("draft-1", "TC-1")
        request = payload(item)
        previous = {
            "_id": "TCBATCH-existing",
            "project_id": "project-1",
            "actor_id": self.user.id,
            "action": "test_case_group_approved",
            "entity_type": "TestCaseApprovalGroup",
            "entity_id": "TCBATCH-existing",
            "details": {
                "request_hash": "different-request-hash",
                "result": {"batch_id": "TCBATCH-existing", "version_ids": []},
            },
        }
        transaction = AsyncMock()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=transaction),
            value=SimpleNamespace(
                audit_events=SimpleNamespace(find_one=AsyncMock(return_value=previous))
            ),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group("project-1", request, self.user)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "IDEMPOTENCY_KEY_REUSED")
        transaction.assert_not_awaited()

    async def test_incomplete_batch_receipt_is_not_replayed_as_success(self):
        item = draft("draft-1", "TC-1")
        request = payload(item)
        batch_id = "TCBATCH-" + batch_review.fingerprint(
            ["project-1", request.operation_id]
        )
        malformed = {
            "_id": batch_id,
            "project_id": "project-1",
            "actor_id": self.user.id,
            "action": "test_case_group_approved",
            "entity_type": "TestCaseApprovalGroup",
            "entity_id": batch_id,
            "details": {
                "request_hash": batch_review.fingerprint(request.model_dump()),
                "result": {
                    "batch_id": batch_id,
                    "count": 1,
                    "draft_ids": [item["_id"]],
                    "version_ids": [],
                },
            },
        }
        db = SimpleNamespace(
            value=SimpleNamespace(
                audit_events=SimpleNamespace(find_one=AsyncMock(return_value=malformed))
            )
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(
                batch_review,
                "_result_with_derived_state",
                new=AsyncMock(),
            ) as derived,
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group("project-1", request, self.user)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_APPROVAL_INCOMPLETE")
        derived.assert_not_awaited()

    async def test_batch_receipt_must_belong_to_same_project_and_audit_action(self):
        request = payload(draft("draft-1", "TC-1"))
        receipt = {
            "_id": "TCBATCH-existing",
            "project_id": "another-project",
            "actor_id": self.user.id,
            "action": "test_case_group_approved",
            "entity_type": "TestCaseApprovalGroup",
            "entity_id": "TCBATCH-existing",
            "details": {
                "request_hash": batch_review.fingerprint(request.model_dump()),
                "result": {
                    "batch_id": "TCBATCH-existing",
                    "count": 1,
                    "draft_ids": ["draft-1"],
                    "version_ids": ["version-1"],
                },
            },
        }

        with self.assertRaises(HTTPException) as error:
            await batch_review._existing_batch_result(
                receipt,
                self.user,
                receipt["details"]["request_hash"],
                "project-1",
                ["draft-1"],
            )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "IDEMPOTENCY_KEY_REUSED")

    async def test_batch_receipt_must_match_the_exact_selected_draft_scope(self):
        receipt = {
            "_id": "TCBATCH-existing",
            "project_id": "project-1",
            "actor_id": self.user.id,
            "action": "test_case_group_approved",
            "entity_type": "TestCaseApprovalGroup",
            "entity_id": "TCBATCH-existing",
            "details": {
                "request_hash": "same-request",
                "result": {
                    "batch_id": "TCBATCH-existing",
                    "count": 1,
                    "draft_ids": ["different-draft"],
                    "version_ids": ["version-1"],
                },
            },
        }
        with self.assertRaises(HTTPException) as error:
            await batch_review._existing_batch_result(
                receipt,
                self.user,
                "same-request",
                "project-1",
                ["draft-1"],
            )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_APPROVAL_INCOMPLETE")

    async def test_batch_receipt_requires_matching_approved_draft_and_frozen_version(self):
        def collection(values):
            return SimpleNamespace(
                find=lambda *_args, **_kwargs: SimpleNamespace(
                    to_list=AsyncMock(return_value=values)
                )
            )

        db = SimpleNamespace(
            value=SimpleNamespace(
                test_case_drafts=collection(
                    [{"_id": "draft-1", "status": "APPROVED", "frozen_version_id": "version-2", "test_case_key": "TC-1"}]
                ),
                test_case_versions=collection(
                    [{"_id": "version-1", "test_case_id": "case-1"}]
                ),
                test_cases=collection([{"_id": "case-1", "test_case_key": "TC-1"}]),
            )
        )

        with patch.object(batch_review, "database", db):
            with self.assertRaises(HTTPException) as error:
                await batch_review._verify_batch_publication_links(
                    "project-1", ["draft-1"], ["version-1"]
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_APPROVAL_INCOMPLETE")

    async def test_batch_receipt_rejects_version_linked_to_a_different_case_key(self):
        def collection(values):
            return SimpleNamespace(
                find=lambda *_args, **_kwargs: SimpleNamespace(
                    to_list=AsyncMock(return_value=values)
                )
            )

        db = SimpleNamespace(
            value=SimpleNamespace(
                test_case_drafts=collection(
                    [{"_id": "draft-1", "status": "APPROVED", "frozen_version_id": "version-1", "test_case_key": "TC-1"}]
                ),
                test_case_versions=collection(
                    [{"_id": "version-1", "test_case_id": "case-1"}]
                ),
                test_cases=collection([{"_id": "case-1", "test_case_key": "TC-OTHER"}]),
            )
        )

        with patch.object(batch_review, "database", db):
            with self.assertRaises(HTTPException) as error:
                await batch_review._verify_batch_publication_links(
                    "project-1", ["draft-1"], ["version-1"]
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "TEST_CASE_APPROVAL_INCOMPLETE")

    async def test_concurrent_retry_replays_the_committed_batch_after_duplicate_key(self):
        item = draft("draft-1", "TC-1")
        request = payload(item)
        request_hash = batch_review.fingerprint(request.model_dump())
        batch_id = "TCBATCH-" + batch_review.fingerprint(["project-1", request.operation_id])
        committed = {
            "_id": batch_id,
            "project_id": "project-1",
            "actor_id": self.user.id,
            "action": "test_case_group_approved",
            "entity_type": "TestCaseApprovalGroup",
            "entity_id": batch_id,
            "details": {
                "request_hash": request_hash,
                "result": {
                    "batch_id": batch_id,
                    "count": 1,
                    "draft_ids": [item["_id"]],
                    "version_ids": ["version-1"],
                    "idempotent": False,
                },
            },
        }
        context = {
            "draft": item,
            "comparison_token": "a" * 64,
            "stale_reasons": [],
            "duplicates": [],
        }

        class Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return False

            async def with_transaction(self, _callback):
                raise DuplicateKeyError("competing transaction committed first")

        audits = SimpleNamespace(
            find_one=AsyncMock(side_effect=[None, committed])
        )
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=AsyncMock(return_value=Session())),
            value=SimpleNamespace(audit_events=audits),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(batch_review, "_verify_batch_publication_links", new=AsyncMock()),
            patch.object(
                batch_review,
                "_retry_batch_derived_state",
                new=AsyncMock(
                    return_value={
                        **committed["details"]["result"],
                        "idempotent": True,
                    }
                ),
            ) as retry,
            patch.object(batch_review.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
            patch.object(batch_review, "review_context", new=AsyncMock(return_value=context)),
            patch.object(batch_review, "has_verifiable_steps", return_value=True),
            patch.object(batch_review, "validate_review_sources_before_approval", new=AsyncMock()),
            patch.object(batch_review, "lint_test_case", return_value=[]),
            patch.object(batch_review, "_result_with_derived_state", new=AsyncMock(return_value={
                **committed["details"]["result"],
                "derived_pending_version_ids": [],
            })) as derived,
        ):
            result = await batch_review.accept_test_case_group("project-1", request, self.user)

        self.assertTrue(result["idempotent"])
        self.assertEqual(result["version_ids"], ["version-1"])
        audits.find_one.assert_awaited()
        derived.assert_awaited_once_with(committed["details"]["result"])
        retry.assert_awaited_once_with(
            {
                **committed["details"]["result"],
                "derived_pending_version_ids": [],
                "idempotent": True,
            },
            "project-1",
            self.user,
        )

    async def test_stale_revision_or_comparison_blocks_group_before_transaction(self):
        item = draft("draft-1", "TC-1")
        request = payload(item)
        stale_context = {
            "draft": {**item, "revision": item["revision"] + 1},
            "comparison_token": "b" * 64,
            "stale_reasons": ["SOURCE_EVIDENCE_CHANGED"],
            "duplicates": [],
        }
        transaction = AsyncMock()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=transaction),
            value=SimpleNamespace(audit_events=SimpleNamespace(find_one=AsyncMock(return_value=None))),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(batch_review.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
            patch.object(batch_review, "review_context", new=AsyncMock(return_value=stale_context)),
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group("project-1", request, self.user)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "REVISION_CONFLICT")
        transaction.assert_not_awaited()

    async def test_stale_later_item_blocks_entire_group_before_transaction(self):
        first = draft("draft-1", "TC-1")
        second = draft("draft-2", "TC-2")
        contexts = [
            {
                "draft": first,
                "comparison_token": "a" * 64,
                "stale_reasons": [],
                "duplicates": [],
            },
            {
                "draft": {**second, "revision": second["revision"] + 1},
                "comparison_token": "b" * 64,
                "stale_reasons": ["SOURCE_EVIDENCE_CHANGED"],
                "duplicates": [],
            },
        ]
        request = payload(first, second)
        transaction = AsyncMock()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=transaction),
            value=SimpleNamespace(
                audit_events=SimpleNamespace(find_one=AsyncMock(return_value=None))
            ),
        )
        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(
                batch_review.test_design_repository,
                "find_project_settings",
                new=AsyncMock(return_value={}),
            ),
            patch.object(
                batch_review, "review_context", new=AsyncMock(side_effect=contexts)
            ) as review_context,
            patch.object(
                batch_review, "validate_review_sources_before_approval", new=AsyncMock()
            ),
            patch.object(batch_review, "has_verifiable_steps", return_value=True),
            patch.object(batch_review, "lint_test_case", return_value=[]),
        ):
            with self.assertRaises(HTTPException) as error:
                await batch_review.accept_test_case_group("project-1", request, self.user)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "REVISION_CONFLICT")
        self.assertEqual(error.exception.detail["draft_id"], "draft-2")
        self.assertEqual(review_context.await_count, 2)
        transaction.assert_not_awaited()

    async def test_approval_commits_outbox_event_without_synchronously_dispatching_ai(self):
        item = draft("draft-1", "TC-1")
        context = {
            "draft": item,
            "comparison_token": "a" * 64,
            "stale_reasons": [],
            "duplicates": [],
        }

        class Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return False

            async def with_transaction(self, callback):
                return await callback(self)

        async def start_session():
            return Session()

        class Collection:
            def __init__(self, *, find_one=None):
                self.find_one_result = find_one
                self.insert_one = AsyncMock()
                self.update_one = AsyncMock(return_value=SimpleNamespace(matched_count=1))

            async def find_one(self, *_args, **_kwargs):
                return self.find_one_result

        audits = Collection()
        audits.find_one = AsyncMock(return_value=None)
        drafts = Collection(find_one=item)
        cases = Collection()
        versions = Collection()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=start_session),
            value=SimpleNamespace(
                audit_events=audits,
                test_case_drafts=drafts,
                test_cases=cases,
                test_case_versions=versions,
            ),
        )

        with (
            patch.object(batch_review, "database", db),
            patch.object(batch_review, "get_project", new=AsyncMock()),
            patch.object(batch_review.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
            patch.object(batch_review, "review_context", new=AsyncMock(return_value=context)),
            patch.object(batch_review, "has_verifiable_steps", return_value=True),
            patch.object(batch_review, "validate_review_sources_before_approval", new=AsyncMock()),
            patch.object(batch_review, "lint_test_case", return_value=[]),
            patch.object(batch_review, "assert_sources_current_in_session", new=AsyncMock()),
            patch.object(batch_review, "validate_test_case_publication_uniqueness", new=AsyncMock()),
            patch.object(batch_review, "queue_test_case_approved", new=AsyncMock()) as queue_event,
            patch.object(batch_review, "finalize_test_case_derivatives", new=AsyncMock(return_value=True)),
            patch("src.clients.ai_automation.emit_test_case_approved", new=AsyncMock()) as dispatch_now,
        ):
            result = await batch_review.accept_test_case_group("project-1", payload(item), self.user)

        queue_event.assert_awaited_once()
        self.assertIsNotNone(queue_event.await_args.args[2])
        dispatch_now.assert_not_awaited()
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["derived_pending_version_ids"], [])


if __name__ == "__main__":
    unittest.main()
