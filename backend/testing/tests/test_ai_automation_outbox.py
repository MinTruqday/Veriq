import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.clients import ai_automation


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {
            "status": "accepted",
            "runs": [{"automation_run_id": "run-1"}],
        }

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://ai.test/tu-dong-hoa-ai/noi-bo/su-kien")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "AI event endpoint failed", request=request, response=response
            )

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload
        self.posts = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        payload = self.payload
        if payload is None:
            event = kwargs["json"]
            payload = {
                "status": "accepted",
                "runs": [{
                    "automation_run_id": "run-1",
                    "project_id": event["project_id"],
                    "source_event_id": event["event_id"],
                    "trigger": event["trigger"],
                    "kind": "EVENT",
                    "source_event_verified": True,
                }],
            }
        return FakeResponse(self.status_code, payload)


class AutomationOutboxTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_test_case_event_without_typed_revision_remains_idempotent(self):
        class OutboxCollection:
            def __init__(self):
                self.record = None

            async def update_one(self, query, update, **kwargs):
                if self.record is None:
                    self.record = {"_id": query["_id"], **update["$setOnInsert"]}
                    return SimpleNamespace(upserted_id=query["_id"])
                return SimpleNamespace(upserted_id=None)

            async def find_one(self, query, projection, **kwargs):
                if not self.record or self.record["_id"] != query["_id"]:
                    return None
                return {
                    key: self.record[key]
                    for key in projection
                    if key in self.record
                }

        outbox = OutboxCollection()
        db = SimpleNamespace(value=SimpleNamespace(ai_automation_outbox=outbox))
        event = (
            "TEST_CASE_CHANGED",
            "test-case:draft-1:3:TEST_CASE_CHANGED",
            "project-1",
            "test_case_draft",
            "draft-1",
            "case-1",
            "database",
            "Current revision: 3\nChanged fields: title",
            "qa-1",
        )

        with patch.object(ai_automation, "database", db):
            await ai_automation.queue_event(*event)
            await ai_automation.queue_event(*event, artifact_revision=3)

        self.assertNotIn(
            "artifact_revision", outbox.record["payload"]["evidence"][0]
        )

    async def test_queue_event_captures_artifact_status_in_fingerprinted_evidence(self):
        class OutboxCollection:
            def __init__(self):
                self.record = None

            async def update_one(self, query, update, **kwargs):
                self.record = {"_id": query["_id"], **update["$setOnInsert"]}
                return SimpleNamespace(upserted_id=query["_id"])

            async def find_one(self, query, projection, **kwargs):
                return {key: self.record[key] for key in projection if key in self.record}

        outbox = OutboxCollection()
        db = SimpleNamespace(value=SimpleNamespace(ai_automation_outbox=outbox))
        event = (
            "TEST_CASE_APPROVED",
            "test-case-version:v1:1:TEST_CASE_APPROVED",
            "project-1",
            "test_case_version",
            "case-1",
            "v1",
            "database",
            "Approved test case",
            "qa-1",
        )

        with patch.object(ai_automation, "database", db):
            await ai_automation.queue_event(*event, artifact_status="APPROVED")

        evidence = outbox.record["payload"]["evidence"][0]
        self.assertEqual(evidence["artifact_status"], "APPROVED")
        self.assertEqual(len(outbox.record["event_fingerprint"]), 64)

    async def test_event_id_reuse_with_different_project_or_content_is_rejected(self):
        class OutboxCollection:
            def __init__(self):
                self.record = None

            async def update_one(self, query, update, **kwargs):
                if self.record is None:
                    self.record = {"_id": query["_id"], **update["$setOnInsert"]}
                    return SimpleNamespace(upserted_id=query["_id"])
                self.record.update(update.get("$set") or {})
                return SimpleNamespace(upserted_id=None)

            async def find_one(self, query, projection, **kwargs):
                if not self.record or self.record["_id"] != query["_id"]:
                    return None
                return {
                    key: self.record[key]
                    for key in projection
                    if key in self.record
                }

        outbox = OutboxCollection()
        db = SimpleNamespace(value=SimpleNamespace(ai_automation_outbox=outbox))

        async def enqueue(project_id, text):
            return await ai_automation.queue_event(
                "WORK_ITEM_CHANGED",
                "work-item:item-1:2:WORK_ITEM_CHANGED",
                project_id,
                "work_item",
                "item-1",
                "item-1-v2",
                "database",
                text,
                "user-1",
            )

        with patch.object(ai_automation, "database", db):
            await enqueue("project-1", "Saved update")
            with self.assertRaisesRegex(
                ValueError, "AI_AUTOMATION_EVENT_ID_REUSE_CONFLICT"
            ):
                await enqueue("project-2", "Different project update")

    async def test_document_event_preserves_ordered_source_version_lineage(self):
        update_one = AsyncMock()
        db = SimpleNamespace(
            value=SimpleNamespace(
                ai_automation_outbox=SimpleNamespace(update_one=update_one)
            )
        )
        document = {
            "_id": "doc-v3",
            "project_id": "project-1",
            "revision": 1,
            "authority": "PROJECT_REFERENCE",
            "normalized_content": "Updated requirement text",
            "source_series_id": "doc-v1",
            "previous_source_version_id": "doc-v2",
        }
        user = SimpleNamespace(id="ba-1", _ai_automation_run_id=None)

        with patch.object(ai_automation, "database", db):
            delivered = await ai_automation.emit_document_ingested(
                document, user, session=object()
            )

        self.assertTrue(delivered)
        payload = update_one.await_args.args[1]["$setOnInsert"]["payload"]
        self.assertEqual(
            payload["evidence"][0]["relationship_path"],
            ["doc-v1", "doc-v2", "doc-v3"],
        )

    async def test_new_document_event_uses_its_own_source_as_lineage_root(self):
        user = SimpleNamespace(id="ba-1", _ai_automation_run_id=None)
        with patch.object(
            ai_automation, "emit_event", new=AsyncMock(return_value=True)
        ) as emit:
            delivered = await ai_automation.emit_document_ingested(
                {
                    "_id": "doc-root",
                    "project_id": "project-1",
                    "normalized_content": "Original source",
                },
                user,
            )

        self.assertTrue(delivered)
        self.assertEqual(emit.await_args.kwargs["relationship_path"], ["doc-root"])

    async def test_second_source_version_does_not_repeat_the_series_root(self):
        update_one = AsyncMock()
        db = SimpleNamespace(
            value=SimpleNamespace(
                ai_automation_outbox=SimpleNamespace(update_one=update_one)
            )
        )
        user = SimpleNamespace(id="ba-1", _ai_automation_run_id=None)
        document = {
            "_id": "doc-v2",
            "project_id": "project-1",
            "source_series_id": "doc-v1",
            "previous_source_version_id": "doc-v1",
            "normalized_content": "Updated source",
        }

        with patch.object(ai_automation, "database", db):
            delivered = await ai_automation.emit_document_ingested(
                document, user, session=object()
            )

        self.assertTrue(delivered)
        payload = update_one.await_args.args[1]["$setOnInsert"]["payload"]
        self.assertEqual(
            payload["evidence"][0]["relationship_path"],
            ["doc-v1", "doc-v2"],
        )

    async def test_approved_test_case_event_is_enqueued_in_approval_transaction(self):
        session = object()
        update_one = AsyncMock()
        db = SimpleNamespace(value=SimpleNamespace(ai_automation_outbox=SimpleNamespace(update_one=update_one)))
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "test_case_id": "case-1",
            "version": 3,
            "title": "Đăng nhập",
            "plain_text_projection": "Đăng nhập Dùng tài khoản hợp lệ Mở trang chính",
        }
        user = SimpleNamespace(id="qa-1", _ai_automation_run_id=None)

        with patch.object(ai_automation, "database", db):
            event_id = await ai_automation.queue_test_case_approved(version, user, session)

        self.assertEqual(event_id, "test-case-version:version-1:1:TEST_CASE_APPROVED")
        update_one.assert_awaited_once()
        args = update_one.await_args
        self.assertEqual(args.args[0], {"_id": event_id})
        self.assertEqual(args.kwargs["session"], session)
        self.assertTrue(args.kwargs["upsert"])
        queued = args.args[1]["$setOnInsert"]
        self.assertEqual(queued["status"], "PENDING")
        self.assertEqual(len(queued["event_fingerprint"]), 64)
        self.assertEqual(queued["payload"]["trigger"], "TEST_CASE_APPROVED")
        self.assertEqual(queued["payload"]["requester_user_id"], "qa-1")
        self.assertEqual(
            queued["payload"]["evidence"][0]["text"],
            "Đăng nhập Dùng tài khoản hợp lệ Mở trang chính",
        )
        self.assertEqual(queued["payload"]["evidence"][0]["artifact_revision"], 1)

    async def test_automation_created_approval_does_not_enqueue_another_event(self):
        update_one = AsyncMock()
        db = SimpleNamespace(value=SimpleNamespace(ai_automation_outbox=SimpleNamespace(update_one=update_one)))
        user = SimpleNamespace(id="agent", _ai_automation_run_id="run-1")

        with patch.object(ai_automation, "database", db):
            event_id = await ai_automation.queue_test_case_approved(
                {"_id": "version-1", "project_id": "project-1"}, user, object()
            )

        self.assertIsNone(event_id)
        update_one.assert_not_awaited()

    def setUp(self):
        self.outbox = MagicMock()
        self.outbox.update_one = AsyncMock()
        self.outbox.find_one = AsyncMock()
        self.outbox.find_one_and_update = AsyncMock()
        self.database = MagicMock()
        self.database.value.ai_automation_outbox = self.outbox
        self.payload = {
            "event_id": "work-item:item-1:2:WORK_ITEM_CHANGED",
            "project_id": "project-1",
            "requester_user_id": "user-1",
            "trigger": "WORK_ITEM_CHANGED",
            "target_artifact_ids": ["item-1"],
            "evidence": [
                {
                    "artifact_type": "work_item",
                    "artifact_id": "item-1",
                    "artifact_version_id": "item-1-v2",
                    "source": "database",
                    "authority": "database",
                    "score": 1,
                    "text": "Thay đổi đã lưu",
                    "project_id": "project-1",
                }
            ],
        }

    async def test_event_delivery_marks_outbox_delivered_and_sends_source_payload(self):
        self.outbox.find_one.side_effect = [
            {"_id": self.payload["event_id"], "status": "PENDING"},
            {"_id": self.payload["event_id"], "status": "DELIVERED"},
        ]
        self.outbox.find_one_and_update.return_value = {
            "_id": self.payload["event_id"],
            "payload": self.payload,
        }
        client = FakeAsyncClient()
        with (
            patch.object(ai_automation, "database", self.database),
            patch.object(ai_automation.httpx, "AsyncClient", return_value=client),
        ):
            delivered = await ai_automation.emit_event(
                trigger="WORK_ITEM_CHANGED",
                event_id=self.payload["event_id"],
                project_id="project-1",
                artifact_type="work_item",
                artifact_id="item-1",
                artifact_version_id="item-1-v2",
                authority="database",
                text="Thay đổi đã lưu",
                requester_user_id="user-1",
            )

        self.assertTrue(delivered)
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(client.posts[0][1]["json"]["trigger"], "WORK_ITEM_CHANGED")
        self.assertEqual(client.posts[0][1]["json"]["evidence"][0]["text"], "Thay đổi đã lưu")
        dispatch_token = self.outbox.find_one_and_update.await_args.args[1]["$set"][
            "dispatch_token"
        ]
        delivered_update = self.outbox.update_one.await_args_list[-1]
        self.assertEqual(
            delivered_update.args[0],
            {
                "_id": self.payload["event_id"],
                "status": "DISPATCHING",
                "dispatch_token": dispatch_token,
            },
        )
        self.assertEqual(delivered_update.args[1]["$set"]["status"], "DELIVERED")
        self.assertIn("payload", delivered_update.args[1]["$unset"])

    async def test_failed_delivery_returns_event_to_pending_with_retry_time(self):
        self.outbox.find_one_and_update.return_value = {
            "_id": self.payload["event_id"],
            "payload": self.payload,
            "attempts": 2,
        }
        client = FakeAsyncClient(status_code=503)
        with (
            patch.object(ai_automation, "database", self.database),
            patch.object(ai_automation.httpx, "AsyncClient", return_value=client),
            patch.object(ai_automation.asyncio, "sleep", new=AsyncMock()),
        ):
            delivered = await ai_automation._dispatch_event(self.payload["event_id"])

        self.assertFalse(delivered)
        self.assertEqual(len(client.posts), 3)
        retry_update = self.outbox.update_one.await_args.args[1]["$set"]
        self.assertEqual(retry_update["status"], "PENDING")
        self.assertEqual(retry_update["attempts"], 3)
        self.assertEqual(retry_update["last_error"], "HTTPStatusError")
        self.assertGreaterEqual(retry_update["next_attempt_at"], datetime.now(timezone.utc))

    async def test_stale_dispatching_event_can_be_reclaimed_after_worker_restart(self):
        self.outbox.find_one.return_value = {
            "_id": self.payload["event_id"],
            "status": "DELIVERED",
        }
        self.outbox.find_one_and_update.return_value = {
            "_id": self.payload["event_id"],
            "payload": self.payload,
            "attempts": 1,
        }
        client = FakeAsyncClient()
        with (
            patch.object(ai_automation, "database", self.database),
            patch.object(ai_automation.httpx, "AsyncClient", return_value=client),
        ):
            delivered = await ai_automation._dispatch_event(self.payload["event_id"])

        self.assertTrue(delivered)
        self.assertEqual(len(client.posts), 1)
        claim_filter = self.outbox.find_one_and_update.await_args.args[0]
        stale_dispatch = next(
            branch for branch in claim_filter["$or"]
            if branch.get("status") == "DISPATCHING"
        )
        reclaim_cutoff = stale_dispatch["updated_at"]["$lte"]
        self.assertIsInstance(reclaim_cutoff, datetime)
        self.assertLessEqual(
            reclaim_cutoff,
            datetime.now(timezone.utc) - timedelta(seconds=59),
        )

    async def test_already_delivered_event_is_idempotent(self):
        self.outbox.find_one.return_value = {"_id": self.payload["event_id"], "status": "DELIVERED"}
        client = FakeAsyncClient()
        with (
            patch.object(ai_automation, "database", self.database),
            patch.object(ai_automation.httpx, "AsyncClient", return_value=client),
        ):
            delivered = await ai_automation.emit_event(
                trigger="WORK_ITEM_CHANGED",
                event_id=self.payload["event_id"],
                project_id="project-1",
                artifact_type="work_item",
                artifact_id="item-1",
                artifact_version_id="item-1-v2",
                authority="database",
                text="Thay đổi đã lưu",
                requester_user_id="user-1",
            )

        self.assertTrue(delivered)
        self.assertEqual(client.posts, [])
        self.outbox.find_one_and_update.assert_not_awaited()

    async def test_already_suppressed_event_is_idempotent(self):
        self.outbox.find_one.return_value = {
            "_id": self.payload["event_id"],
            "status": "SUPPRESSED",
            "suppression_reason": "AUTOMATION_TRIGGER_DISABLED",
        }
        client = FakeAsyncClient()
        with (
            patch.object(ai_automation, "database", self.database),
            patch.object(ai_automation.httpx, "AsyncClient", return_value=client),
        ):
            resolved = await ai_automation.emit_event(
                trigger="WORK_ITEM_CHANGED",
                event_id=self.payload["event_id"],
                project_id="project-1",
                artifact_type="work_item",
                artifact_id="item-1",
                artifact_version_id="item-1-v2",
                authority="database",
                text="Thay đổi đã lưu",
                requester_user_id="user-1",
            )

        self.assertTrue(resolved)
        self.assertEqual(client.posts, [])
        self.outbox.find_one_and_update.assert_not_awaited()

    async def test_suppressed_event_is_recorded_and_not_dispatched_again(self):
        self.outbox.find_one.return_value = {
            "_id": self.payload["event_id"],
            "status": "SUPPRESSED",
        }
        self.outbox.find_one_and_update.return_value = {
            "_id": self.payload["event_id"],
            "payload": self.payload,
        }
        client = FakeAsyncClient(
            payload={
                "status": "suppressed",
                "reason_code": "AUTOMATION_TRIGGER_DISABLED",
                "runs": [],
            }
        )
        with (
            patch.object(ai_automation, "database", self.database),
            patch.object(ai_automation.httpx, "AsyncClient", return_value=client),
        ):
            delivered = await ai_automation._dispatch_event(self.payload["event_id"])

        self.assertTrue(delivered)
        self.assertEqual(len(client.posts), 1)
        update = self.outbox.update_one.await_args.args[1]
        self.assertEqual(update["$set"]["status"], "SUPPRESSED")
        self.assertEqual(
            update["$set"]["suppression_reason"], "AUTOMATION_TRIGGER_DISABLED"
        )
        self.assertNotIn("payload", update["$set"])
        self.assertIn("payload", update["$unset"])

    async def test_invalid_success_body_is_retried_instead_of_marked_delivered(self):
        self.outbox.find_one_and_update.return_value = {
            "_id": self.payload["event_id"],
            "payload": self.payload,
            "attempts": 0,
        }
        client = FakeAsyncClient(payload={"runs": []})
        with (
            patch.object(ai_automation, "database", self.database),
            patch.object(ai_automation.httpx, "AsyncClient", return_value=client),
            patch.object(ai_automation.asyncio, "sleep", new=AsyncMock()),
        ):
            delivered = await ai_automation._dispatch_event(self.payload["event_id"])

        self.assertFalse(delivered)
        self.assertEqual(len(client.posts), 3)
        retry_update = self.outbox.update_one.await_args.args[1]["$set"]
        self.assertEqual(retry_update["status"], "PENDING")
        self.assertEqual(retry_update["last_error"], "AI_EVENT_RESPONSE_INVALID")

    async def test_accepted_response_for_another_source_event_is_not_marked_delivered(self):
        self.outbox.find_one_and_update.return_value = {
            "_id": self.payload["event_id"],
            "payload": self.payload,
            "attempts": 0,
        }
        client = FakeAsyncClient(payload={
            "status": "accepted",
            "runs": [{
                "automation_run_id": "run-other",
                "project_id": "project-1",
                "source_event_id": "different-event",
                "trigger": "WORK_ITEM_CHANGED",
                "kind": "EVENT",
                "source_event_verified": True,
            }],
        })
        with (
            patch.object(ai_automation, "database", self.database),
            patch.object(ai_automation.httpx, "AsyncClient", return_value=client),
            patch.object(ai_automation.asyncio, "sleep", new=AsyncMock()),
        ):
            delivered = await ai_automation._dispatch_event(self.payload["event_id"])

        self.assertFalse(delivered)
        self.assertEqual(len(client.posts), 3)
        retry_update = self.outbox.update_one.await_args.args[1]["$set"]
        self.assertEqual(retry_update["status"], "PENDING")
        self.assertEqual(retry_update["last_error"], "AI_EVENT_RESPONSE_INVALID")

    async def test_requirement_change_event_contains_separate_requirement_sources(self):
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "requirement_id": "requirement-1",
            "plain_text_projection": "Người dùng đăng nhập.",
            "acceptance_criteria": [{"plain_text": "Mã xác thực hết hạn sau 5 phút."}],
            "business_rules": ["Tài khoản bị khóa sau 3 lần sai."],
            "details": {"api_operations": [{"operation_id": "POST /login"}]},
        }
        user = SimpleNamespace(_ai_automation_run_id=None, id="user-1")
        with patch.object(ai_automation, "emit_event", new=AsyncMock(return_value=True)) as emit:
            delivered = await ai_automation.emit_requirement_changed(version, user)

        self.assertTrue(delivered)
        event_text = emit.await_args.args[7]
        self.assertIn("Mã xác thực hết hạn sau 5 phút.", event_text)
        self.assertIn("Tài khoản bị khóa sau 3 lần sai.", event_text)
        self.assertIn("POST /login", event_text)

    async def test_test_case_change_event_carries_the_exact_before_and_current_revision(self):
        user = SimpleNamespace(_ai_automation_run_id=None, id="user-1")
        previous = {
            "_id": "draft-1",
            "project_id": "project-1",
            "test_case_key": "TC-1",
            "revision": 4,
            "title": "Login",
            "steps": [{"action_doc": {"type": "doc", "content": [{"type": "text", "text": "Open sign-in"}]}}],
            "requirement_version_ids": ["REQ-V1"],
        }
        current = {
            **previous,
            "revision": 5,
            "steps": [{"action_doc": {"type": "doc", "content": [{"type": "text", "text": "Submit valid credentials"}]}}],
        }
        with patch.object(ai_automation, "emit_event", new=AsyncMock(return_value=True)) as emit:
            delivered = await ai_automation.emit_test_case_changed(current, user, previous_case=previous)

        self.assertTrue(delivered)
        event_text = emit.await_args.args[7]
        self.assertIn("Event type: TEST_CASE_UPDATED", event_text)
        self.assertIn("Previous revision: 4", event_text)
        self.assertIn("Current revision: 5", event_text)
        self.assertIn("Changed fields: steps", event_text)
        self.assertIn("Open sign-in", event_text)
        self.assertIn("Submit valid credentials", event_text)

    async def test_ai_generated_work_item_update_does_not_emit_a_recursive_event(self):
        user = SimpleNamespace(_ai_automation_run_id="run-1", id="user-1")
        with patch.object(ai_automation, "emit_event", new=AsyncMock()) as emit:
            delivered = await ai_automation.emit_work_item_changed(
                {"_id": "item-1", "project_id": "project-1"}, user
            )

        self.assertTrue(delivered)
        emit.assert_not_awaited()

    async def test_all_remaining_lifecycle_changes_emit_their_typed_source_event(self):
        user = SimpleNamespace(_ai_automation_run_id=None, id="user-1")
        cases = [
            (
                ai_automation.emit_test_execution_recorded,
                {
                    "_id": "result-1",
                    "project_id": "project-1",
                    "status": "FAIL",
                    "note": "Observed",
                },
                "TEST_EXECUTION_RECORDED",
                "test_result",
                "result-1",
            ),
            (
                ai_automation.emit_defect_recorded,
                {
                    "_id": "defect-1",
                    "project_id": "project-1",
                    "title": "Failure",
                    "description": "Observed",
                },
                "DEFECT_RECORDED",
                "defect",
                "defect-1",
            ),
            (
                ai_automation.emit_document_ingested,
                {"_id": "document-1", "project_id": "project-1", "normalized_content": "Source"},
                "DOCUMENT_INGESTED",
                "requirement_document",
                "document-1",
            ),
            (
                ai_automation.emit_test_case_changed,
                {"_id": "draft-1", "project_id": "project-1", "revision": 2, "title": "Draft"},
                "TEST_CASE_CHANGED",
                "test_case_draft",
                "draft-1",
            ),
            (
                ai_automation.emit_test_case_approved,
                {"_id": "version-1", "project_id": "project-1", "revision": 1, "title": "Approved"},
                "TEST_CASE_APPROVED",
                "test_case_version",
                "version-1",
            ),
            (
                ai_automation.emit_test_plan_changed,
                {"_id": "plan-1", "project_id": "project-1", "revision": 3, "name": "Plan"},
                "TEST_PLAN_CHANGED",
                "test_plan",
                "plan-1",
            ),
            (
                ai_automation.emit_test_plan_approved,
                {
                    "_id": "plan-2",
                    "project_id": "project-1",
                    "revision": 1,
                    "name": "Approved plan",
                },
                "TEST_PLAN_APPROVED",
                "test_plan",
                "plan-2",
            ),
            (
                ai_automation.emit_release_changed,
                {"_id": "release-1", "project_id": "project-1", "revision": 4, "name": "Release"},
                "RELEASE_CHANGED",
                "release",
                "release-1",
            ),
        ]

        for emitter, artifact, trigger, artifact_type, artifact_id in cases:
            with self.subTest(trigger=trigger):
                with patch.object(
                    ai_automation, "emit_event", new=AsyncMock(return_value=True)
                ) as emit:
                    self.assertTrue(await emitter(artifact, user))

                args = emit.await_args.args
                self.assertEqual(args[0], trigger)
                self.assertEqual(args[2], "project-1")
                self.assertEqual(args[3], artifact_type)
                self.assertEqual(args[4], artifact_id)
                self.assertEqual(args[8], "user-1")

    async def test_test_result_rechecks_only_its_active_release_with_causal_event_id(self):
        user = SimpleNamespace(_ai_automation_run_id=None, id="tester-1")
        release = {"_id": "release-1", "project_id": "project-1", "status": "ACTIVE", "revision": 4}
        result = {"_id": "result-1", "project_id": "project-1", "status": "PASS", "revision": 2}
        with patch.object(ai_automation, "emit_event", new=AsyncMock(return_value=True)) as emit:
            delivered = await ai_automation.emit_release_gate_recheck(release, result, user)
        self.assertTrue(delivered)
        args = emit.await_args.args
        self.assertEqual(args[0], "RELEASE_CHANGED")
        self.assertIn("test-result:result-1:r2", args[1])
        self.assertEqual(args[2:6], ("project-1", "release", "release-1", "release-1"))

    async def test_blocking_defect_changes_can_recheck_its_active_release(self):
        user = SimpleNamespace(_ai_automation_run_id=None, id="qa-1")
        release = {"_id": "release-1", "project_id": "project-1", "status": "ACTIVE", "revision": 4}
        defect = {
            "_id": "defect-1",
            "project_id": "project-1",
            "status": "CLOSED",
            "revision": 5,
        }
        with patch.object(ai_automation, "emit_event", new=AsyncMock(return_value=True)) as emit:
            delivered = await ai_automation.emit_release_gate_recheck(
                release, defect, user, artifact_type="defect"
            )
        self.assertTrue(delivered)
        args = emit.await_args.args
        self.assertIn("release-gate:release-1:defect:defect-1:r5", args[1])
        self.assertEqual(args[6], "release_gate")

    async def test_release_gate_recheck_does_not_emit_for_automation_runs_or_inactive_releases(self):
        release = {"_id": "release-1", "project_id": "project-1", "status": "PLANNED"}
        result = {"_id": "result-1", "project_id": "project-1", "status": "PASS"}
        for user in (
            SimpleNamespace(_ai_automation_run_id="run-1", id="agent"),
            SimpleNamespace(_ai_automation_run_id=None, id="tester-1"),
        ):
            with self.subTest(user=user), patch.object(ai_automation, "emit_event", new=AsyncMock()) as emit:
                self.assertTrue(await ai_automation.emit_release_gate_recheck(release, result, user))
                emit.assert_not_awaited()

    async def test_work_item_event_emitter_uses_saved_revision_and_stored_fields(self):
        user = SimpleNamespace(_ai_automation_run_id=None, id="user-1")
        item = {
            "_id": "work-item-1",
            "project_id": "project-1",
            "revision": 7,
            "title": "Update login behavior",
            "description": "Stored description",
            "status": "IN_PROGRESS",
        }

        with patch.object(ai_automation, "emit_event", new=AsyncMock(return_value=True)) as emit:
            delivered = await ai_automation.emit_work_item_changed(item, user)

        self.assertTrue(delivered)
        args = emit.await_args.args
        self.assertEqual(args[0], "WORK_ITEM_CHANGED")
        self.assertEqual(args[1], "work-item:work-item-1:7:WORK_ITEM_CHANGED")
        self.assertEqual(args[3], "work_item")
        self.assertEqual(args[6], "database")
        self.assertIn("Update login behavior", args[7])
        self.assertIn("Stored description", args[7])
        self.assertEqual(emit.await_args.kwargs["artifact_revision"], 7)
        self.assertEqual(emit.await_args.kwargs["artifact_status"], "IN_PROGRESS")

    async def test_dependency_change_queues_scoped_events_for_both_endpoints(self):
        user = SimpleNamespace(id="ba-1", _ai_automation_run_id=None)
        source = {
            "_id": "WI-1",
            "project_id": "project-1",
            "revision": 4,
            "title": "Implement login",
        }
        target = {
            "_id": "WI-2",
            "project_id": "project-1",
            "revision": 2,
            "title": "Run security review",
        }
        dependency = {
            "_id": "DEP-1",
            "project_id": "project-1",
            "source_item_id": "WI-1",
            "target_item_id": "WI-2",
            "dependency_type": "BLOCKS",
        }
        session = object()

        with patch.object(
            ai_automation, "queue_event", new=AsyncMock(return_value="outbox-id")
        ) as queue_event:
            delivered = await ai_automation.emit_work_item_dependency_changed(
                dependency, source, target, user, session=session
            )

        self.assertTrue(delivered)
        self.assertEqual(queue_event.await_count, 2)
        queued = [call.args for call in queue_event.await_args_list]
        self.assertEqual({args[3] for args in queued}, {"work_item"})
        self.assertEqual({args[4] for args in queued}, {"WI-1", "WI-2"})
        self.assertTrue(all(call.kwargs["session"] is session for call in queue_event.await_args_list))
        self.assertTrue(all("Work Item WI-2 blocks Work Item WI-1" in args[7] for args in queued))
        self.assertEqual(
            {args[1] for args in queued},
            {
                "work-item-dependency:DEP-1:WI-1:WORK_ITEM_CHANGED",
                "work-item-dependency:DEP-1:WI-2:WORK_ITEM_CHANGED",
            },
        )

    async def test_dependency_change_rejects_cross_project_endpoints(self):
        user = SimpleNamespace(id="ba-1", _ai_automation_run_id=None)
        with patch.object(ai_automation, "queue_event", new=AsyncMock()) as queue_event:
            delivered = await ai_automation.emit_work_item_dependency_changed(
                {
                    "_id": "DEP-1",
                    "project_id": "project-1",
                    "dependency_type": "BLOCKS",
                },
                {"_id": "WI-1", "project_id": "project-1"},
                {"_id": "WI-2", "project_id": "project-2"},
                user,
                session=object(),
            )

        self.assertFalse(delivered)
        queue_event.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
