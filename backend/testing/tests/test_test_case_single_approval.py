import copy
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from pymongo.errors import DuplicateKeyError

from src.modules.design.services import test_case_lifecycle as lifecycle


class Result:
    def __init__(self, matched_count=1):
        self.matched_count = matched_count


class Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def with_transaction(self, callback):
        return await callback(self)


class Collection:
    def __init__(self, *, documents=None):
        self.documents = documents or []
        self.calls = []

    async def find_one(self, query, **kwargs):
        self.calls.append(("find_one", query, kwargs))
        return next(
            (copy.deepcopy(item) for item in self.documents if all(item.get(key) == value for key, value in query.items())),
            None,
        )

    async def insert_one(self, value, **kwargs):
        self.calls.append(("insert_one", copy.deepcopy(value), kwargs))
        self.documents.append(copy.deepcopy(value))

    async def update_one(self, query, update, **kwargs):
        self.calls.append(("update_one", query, update, kwargs))
        target = next(
            (item for item in self.documents if all(item.get(key) == value for key, value in query.items())),
            None,
        )
        if not target:
            return Result(0)
        target.update(copy.deepcopy(update.get("$set", {})))
        for key, value in update.get("$inc", {}).items():
            target[key] = target.get(key, 0) + value
        return Result(1)


def review_draft():
    return {
        "_id": "draft-1",
        "project_id": "project-1",
        "test_case_key": "TC-1",
        "title": "Đăng nhập bằng thông tin hợp lệ",
        "type": "MANUAL",
        "revision": 4,
        "status": "IN_REVIEW",
        "priority": "MEDIUM",
        "risk": "MEDIUM",
        "preconditions_doc": {"type": "doc", "content": []},
        "steps": [],
        "test_data": [],
        "expected_result_doc": {"type": "doc", "content": []},
        "postconditions_doc": {"type": "doc", "content": []},
        "tags": [],
        "automation_status": "MANUAL",
        "requirement_version_ids": [],
        "acceptance_criterion_ids": [],
        "created_by": "qa-1",
    }


class SingleTestCaseApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_approval_audit_retry_accepts_only_matching_deterministic_receipt(self):
        draft = {"_id": "draft-1", "project_id": "project-1"}
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "index_status": "INDEXED",
            "trace_status": "READY",
            "approval_audit_status": "PENDING",
            "adequacy_invalidation_status": "READY",
        }
        user = SimpleNamespace(id="qa-1")
        audit_events = SimpleNamespace(
            find_one=AsyncMock(return_value={
                "_id": "AUD-TC-APPROVAL-version-1",
                "actor_id": "qa-1",
                "project_id": "project-1",
                "action": "test_case_version_approved",
                "entity_type": "TestCaseVersion",
                "entity_id": "version-1",
                "details": {"draft_id": "draft-1"},
            })
        )
        with (
            patch.object(
                lifecycle,
                "database",
                SimpleNamespace(value=SimpleNamespace(audit_events=audit_events)),
            ),
            patch.object(
                lifecycle.test_design_repository,
                "set_case_version_approval_result",
                new=AsyncMock(return_value=Result(1)),
            ),
            patch.object(
                lifecycle,
                "audit",
                new=AsyncMock(side_effect=DuplicateKeyError("duplicate")),
            ) as record_audit,
        ):
            ready = await lifecycle.finalize_test_case_derivatives(draft, version, user)

        self.assertTrue(ready)
        self.assertEqual(version["approval_audit_status"], "READY")
        self.assertEqual(
            record_audit.await_args.kwargs["event_id"],
            "AUD-TC-APPROVAL-version-1",
        )

    async def test_adequacy_invalidation_is_scoped_to_approved_version_and_idempotent(self):
        from src.repositories.test_adequacy import TestAdequacyRepository

        assessments = SimpleNamespace(update_many=AsyncMock())
        with patch(
            "src.repositories.test_adequacy.database",
            SimpleNamespace(value=SimpleNamespace(test_adequacy_assessments=assessments)),
        ):
            await TestAdequacyRepository().invalidate_for_requirement_versions(
                "project-1", ["requirement-version-1"], "time-1", "version-1"
            )

        query, update = assessments.update_many.await_args.args
        self.assertEqual(query["requirement_version_id"], {"$in": ["requirement-version-1"]})
        self.assertEqual(query["test_case_invalidation_ids"], {"$ne": "version-1"})
        self.assertEqual(update["$addToSet"]["test_case_invalidation_ids"], "version-1")
        self.assertEqual(update["$inc"]["revision"], 1)

    async def test_approval_repository_persists_adequacy_invalidation_state(self):
        from src.repositories.test_design import TestDesignRepository

        versions = SimpleNamespace(update_one=AsyncMock())
        database_stub = SimpleNamespace(value=SimpleNamespace(test_case_versions=versions))
        with patch("src.repositories.test_design.database", database_stub):
            await TestDesignRepository().set_case_version_approval_result(
                "version-1",
                "project-1",
                "INDEXED",
                None,
                None,
                "READY",
                None,
                "READY",
                None,
                "FAILED",
                "ADEQUACY_INVALIDATION_FAILED",
            )

        update = versions.update_one.await_args.args
        self.assertEqual(update[0], {"_id": "version-1", "project_id": "project-1"})
        self.assertEqual(
            update[1]["$set"]["adequacy_invalidation_status"], "FAILED"
        )
        self.assertEqual(
            update[1]["$set"]["adequacy_invalidation_error_code"],
            "ADEQUACY_INVALIDATION_FAILED",
        )

    async def test_adequacy_invalidation_failure_degrades_approval_and_is_retryable(self):
        draft = {"_id": "draft-1", "project_id": "project-1"}
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "requirement_version_ids": ["requirement-version-1"],
            "index_status": "INDEXED",
            "trace_status": "READY",
            "approval_audit_status": "READY",
            "adequacy_invalidation_status": "PENDING",
        }
        user = SimpleNamespace(id="qa-1")
        persist = AsyncMock(return_value=Result(1))
        invalidate = AsyncMock(side_effect=RuntimeError("temporary Mongo failure"))

        with (
            patch.object(lifecycle.test_design_repository, "set_case_version_approval_result", new=persist),
            patch(
                "src.modules.design.services.test_adequacy.invalidate_adequacy_for_test_case_version",
                new=invalidate,
            ),
        ):
            ready = await lifecycle.finalize_test_case_derivatives(draft, version, user)

        self.assertFalse(ready)
        self.assertEqual(version["adequacy_invalidation_status"], "FAILED")
        self.assertEqual(
            version["adequacy_invalidation_error_code"], "ADEQUACY_INVALIDATION_FAILED"
        )
        self.assertEqual(persist.await_args.args[-2:], ("FAILED", "ADEQUACY_INVALIDATION_FAILED"))

        invalidate.side_effect = None
        version["index_status"] = "INDEXED"
        with (
            patch.object(lifecycle.test_design_repository, "set_case_version_approval_result", new=persist),
            patch(
                "src.modules.design.services.test_adequacy.invalidate_adequacy_for_test_case_version",
                new=invalidate,
            ),
        ):
            ready = await lifecycle.finalize_test_case_derivatives(draft, version, user)

        self.assertTrue(ready)
        self.assertEqual(version["adequacy_invalidation_status"], "READY")

    async def test_approval_derivatives_stay_degraded_when_status_write_matches_nothing(self):
        draft = {"_id": "draft-1", "project_id": "project-1"}
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "index_status": "INDEXED",
            "trace_status": "READY",
            "approval_audit_status": "READY",
            "adequacy_invalidation_status": "READY",
        }
        with patch.object(
            lifecycle.test_design_repository,
            "set_case_version_approval_result",
            new=AsyncMock(return_value=Result(0)),
        ):
            ready = await lifecycle.finalize_test_case_derivatives(
                draft, version, SimpleNamespace(id="qa-1")
            )

        self.assertFalse(ready)
        self.assertEqual(version["index_error_code"], "APPROVAL_STATUS_PERSIST_FAILED")
        self.assertEqual(
            version["adequacy_invalidation_error_code"],
            "APPROVAL_STATUS_PERSIST_FAILED",
        )

    async def test_approval_and_ai_outbox_are_written_in_same_transaction(self):
        draft = review_draft()
        drafts = Collection(documents=[draft])
        cases = Collection()
        versions = Collection()
        outbox = Collection()
        session = Session()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=AsyncMock(return_value=session)),
            value=SimpleNamespace(
                test_case_drafts=drafts,
                test_cases=cases,
                test_case_versions=versions,
                ai_automation_outbox=outbox,
            ),
        )
        user = SimpleNamespace(id="qa-1", _ai_automation_run_id=None)
        payload = SimpleNamespace(expected_revision=4, change_reason="Đã rà soát", review_note="OK")

        async def queue(version, actor, transaction):
            self.assertIs(transaction, session)
            await outbox.insert_one({"_id": "event-1", "version_id": version["_id"]}, session=transaction)

        with (
            patch.object(lifecycle, "database", db),
            patch.object(lifecycle, "get_project_entity", new=AsyncMock(return_value=draft)),
            patch.object(lifecycle, "has_verifiable_steps", return_value=True),
            patch.object(lifecycle, "validate_test_case_custom_values", new=AsyncMock()),
            patch.object(lifecycle, "lint_test_case", return_value=[]),
            patch.object(lifecycle.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
            patch("src.modules.design.services.test_case_review.validate_review_sources_before_approval", new=AsyncMock()),
            patch("src.modules.design.services.test_case_review.review_context", new=AsyncMock(return_value={"duplicates": []})),
            patch("src.modules.design.services.test_case_review.assert_sources_current_in_session", new=AsyncMock()),
            patch("src.modules.design.services.test_case_review.validate_test_case_publication_uniqueness", new=AsyncMock()),
            patch.object(lifecycle, "audit", new=AsyncMock()) as audit,
            patch("src.clients.ai_automation.queue_test_case_approved", new=AsyncMock(side_effect=queue)),
            patch.object(lifecycle, "finalize_test_case_derivatives", new=AsyncMock(return_value=True)),
            patch("src.clients.ai_automation.emit_test_case_approved", new=AsyncMock()) as dispatch_now,
        ):
            result = await lifecycle.approve_test_case_draft_record("draft-1", payload, user)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(drafts.documents[0]["status"], "APPROVED")
        self.assertEqual(drafts.documents[0]["revision"], 5)
        self.assertEqual(len(cases.documents), 1)
        self.assertEqual(len(versions.documents), 1)
        self.assertEqual(len(outbox.documents), 1)
        dispatch_now.assert_not_awaited()
        self.assertEqual(versions.documents[0]["approval_audit_status"], "READY")
        self.assertIs(audit.await_args.kwargs["session"], session)
        for collection in (drafts, cases, versions, outbox):
            self.assertTrue(collection.calls)
            for call in collection.calls:
                kwargs = call[-1]
                self.assertIs(kwargs.get("session"), session)

    async def test_revision_conflict_stops_before_creating_case_or_event(self):
        draft = review_draft()
        db = SimpleNamespace(
            client=SimpleNamespace(start_session=AsyncMock(return_value=Session())),
            value=SimpleNamespace(
                test_case_drafts=Collection(documents=[{**draft, "revision": 5}]),
                test_cases=Collection(),
                test_case_versions=Collection(),
                ai_automation_outbox=Collection(),
            ),
        )
        user = SimpleNamespace(id="qa-1", _ai_automation_run_id=None)
        payload = SimpleNamespace(expected_revision=4, change_reason="Đã rà soát", review_note="OK")

        with (
            patch.object(lifecycle, "database", db),
            patch.object(lifecycle, "get_project_entity", new=AsyncMock(return_value=draft)),
            patch.object(lifecycle, "has_verifiable_steps", return_value=True),
            patch.object(lifecycle, "validate_test_case_custom_values", new=AsyncMock()),
            patch.object(lifecycle, "lint_test_case", return_value=[]),
            patch.object(lifecycle.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
            patch("src.modules.design.services.test_case_review.validate_review_sources_before_approval", new=AsyncMock()),
            patch("src.modules.design.services.test_case_review.review_context", new=AsyncMock(return_value={"duplicates": []})),
            patch("src.modules.design.services.test_case_review.assert_sources_current_in_session", new=AsyncMock()),
            patch("src.modules.design.services.test_case_review.validate_test_case_publication_uniqueness", new=AsyncMock()),
            patch("src.clients.ai_automation.queue_test_case_approved", new=AsyncMock()) as queue,
        ):
            with self.assertRaises(Exception) as raised:
                await lifecycle.approve_test_case_draft_record("draft-1", payload, user)

        self.assertEqual(getattr(raised.exception, "status_code", None), 409)
        self.assertEqual(db.value.test_cases.documents, [])
        self.assertEqual(db.value.test_case_versions.documents, [])
        self.assertEqual(db.value.ai_automation_outbox.documents, [])
        queue.assert_not_awaited()

    async def test_single_approval_rejects_near_duplicate_without_qa_reason(self):
        draft = review_draft()
        draft["duplicate_reason"] = ""
        start_session = AsyncMock()
        user = SimpleNamespace(id="qa-1", _ai_automation_run_id=None)
        payload = SimpleNamespace(expected_revision=4, change_reason="Đã rà soát", review_note="OK")
        matches = [{"test_case_key": "TC-EXISTING", "version_id": "version-1", "score": 0.91}]

        with (
            patch.object(lifecycle, "get_project_entity", new=AsyncMock(return_value=draft)),
            patch.object(lifecycle, "has_verifiable_steps", return_value=True),
            patch.object(lifecycle, "validate_test_case_custom_values", new=AsyncMock()),
            patch.object(lifecycle, "lint_test_case", return_value=[]),
            patch.object(lifecycle.test_design_repository, "find_project_settings", new=AsyncMock(return_value={})),
            patch("src.modules.design.services.test_case_review.validate_review_sources_before_approval", new=AsyncMock()),
            patch("src.modules.design.services.test_case_review.review_context", new=AsyncMock(return_value={"duplicates": matches})),
            patch.object(
                lifecycle,
                "database",
                SimpleNamespace(client=SimpleNamespace(start_session=start_session)),
            ),
        ):
            with self.assertRaises(Exception) as raised:
                await lifecycle.approve_test_case_draft_record("draft-1", payload, user)

        error = raised.exception
        self.assertEqual(getattr(error, "status_code", None), 409)
        self.assertEqual(error.detail["code"], "TEST_CASE_DUPLICATE_REVIEW_REQUIRED")
        self.assertEqual(error.detail["matches"], matches)
        start_session.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
