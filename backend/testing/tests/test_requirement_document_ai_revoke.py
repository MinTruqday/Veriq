import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.requirements.services import requirement_documents
from src.schemas.contracts.requirements import RequirementDocumentAIReadPatch


class RequirementDocumentAIRevokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.document = {
            "_id": "RDOC-private-source",
            "project_id": "PRJ-source",
            "created_by": "owner-1",
            "revision": 8,
            "status": "READY",
            "ai_enabled": True,
            "index_status": "INDEXED",
        }
        self.updated = {
            **self.document,
            "revision": 9,
            "ai_enabled": False,
            "index_status": "REVOKE_PENDING",
        }
        self.payload = RequirementDocumentAIReadPatch(
            expected_revision=8, ai_enabled=False
        )
        self.user = SimpleNamespace(id="owner-1", is_system_admin=False)

    async def test_revoke_cancels_queued_ingestion_and_removes_search_index(self):
        stored = {**self.updated, "index_status": "NOT_REQUESTED"}
        with (
            patch.object(requirement_documents, "get_project_entity", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents.ai_automation_access_repository, "revoke_and_wait", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents.requirement_document_repository, "update_with_revision", new=AsyncMock(return_value=self.updated)) as update,
            patch.object(requirement_documents, "cancel_pending_document_ingestion", new=AsyncMock(return_value=2)) as cancel,
            patch.object(requirement_documents, "cancel_document_ingestion_runs", new=AsyncMock(return_value=1)) as cancel_runs,
            patch.object(requirement_documents, "remove_artifact", new=AsyncMock(return_value=True)) as remove,
            patch.object(requirement_documents.requirement_document_repository, "set_index_result", new=AsyncMock(return_value=SimpleNamespace(matched_count=1))) as save_index_status,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=stored)),
            patch.object(requirement_documents, "audit", new=AsyncMock()) as audit,
        ):
            result = await requirement_documents.update_requirement_document_ai_read(
                self.document["_id"], self.payload, self.user
            )

        self.assertFalse(result.data["ai_enabled"])
        self.assertEqual(result.data["index_status"], "NOT_REQUESTED")
        self.assertEqual(update.await_args.args[3]["index_status"], "REVOKE_PENDING")
        cancel.assert_awaited_once_with(self.document["_id"], "AI_READ_PERMISSION_REVOKED")
        cancel_runs.assert_awaited_once_with(self.document["_id"])
        remove.assert_awaited_once_with(self.document["project_id"], self.document["_id"])
        self.assertEqual(save_index_status.await_args.kwargs["expected_revision"], 9)
        self.assertEqual(audit.await_args.args[5]["cancelled_pending_events"], 2)

    async def test_failed_index_removal_keeps_permission_revoked_and_reports_pending(self):
        with (
            patch.object(requirement_documents, "get_project_entity", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents.ai_automation_access_repository, "revoke_and_wait", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents.requirement_document_repository, "update_with_revision", new=AsyncMock(return_value=self.updated)) as update,
            patch.object(requirement_documents, "cancel_pending_document_ingestion", new=AsyncMock(return_value=1)),
            patch.object(requirement_documents, "cancel_document_ingestion_runs", new=AsyncMock(return_value=1)),
            patch.object(requirement_documents, "remove_artifact", new=AsyncMock(return_value=False)),
            patch.object(requirement_documents.requirement_document_repository, "set_index_result", new=AsyncMock()) as save_index_status,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.update_requirement_document_ai_read(
                    self.document["_id"], self.payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["code"], "KNOWLEDGE_REVOCATION_PENDING")
        self.assertFalse(update.await_args.args[3]["ai_enabled"])
        save_index_status.assert_not_awaited()

    async def test_source_fence_timeout_keeps_document_revocation_pending(self):
        with (
            patch.object(requirement_documents, "get_project_entity", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "update_with_revision", new=AsyncMock(return_value=self.updated)) as update,
            patch.object(requirement_documents.ai_automation_access_repository, "revoke_and_wait", new=AsyncMock(return_value=False)),
            patch.object(requirement_documents, "cancel_pending_document_ingestion", new=AsyncMock()) as cancel,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.update_requirement_document_ai_read(
                    self.document["_id"], self.payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["code"], "AI_AUTOMATION_REQUESTS_STILL_ACTIVE")
        self.assertEqual(update.await_args.args[3]["index_status"], "REVOKE_PENDING")
        cancel.assert_not_awaited()

    async def test_reenable_is_blocked_until_pending_revocation_is_recovered(self):
        pending = {**self.updated, "ai_enabled": False, "index_status": "REVOKE_PENDING"}
        enable = RequirementDocumentAIReadPatch(expected_revision=9, ai_enabled=True)
        with (
            patch.object(requirement_documents, "get_project_entity", new=AsyncMock(return_value=pending)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "update_with_revision", new=AsyncMock()) as update,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.update_requirement_document_ai_read(
                    self.document["_id"], enable, self.user
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "AI_READ_REVOCATION_IN_PROGRESS")
        update.assert_not_awaited()

    async def test_outbox_cancellation_failure_keeps_revocation_retryable(self):
        with (
            patch.object(requirement_documents, "get_project_entity", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents.ai_automation_access_repository, "revoke_and_wait", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents.requirement_document_repository, "update_with_revision", new=AsyncMock(return_value=self.updated)),
            patch.object(requirement_documents, "cancel_pending_document_ingestion", new=AsyncMock(side_effect=RuntimeError("outbox unavailable"))),
            patch.object(requirement_documents, "cancel_document_ingestion_runs", new=AsyncMock(return_value=1)),
            patch.object(requirement_documents, "remove_artifact", new=AsyncMock(return_value=True)) as remove,
            patch.object(requirement_documents.requirement_document_repository, "set_index_result", new=AsyncMock(return_value=SimpleNamespace(matched_count=1))),
            patch.object(requirement_documents.requirement_document_repository, "set_index_result", new=AsyncMock()) as set_index_status,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.update_requirement_document_ai_read(
                    self.document["_id"], self.payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["code"], "AI_INGESTION_CANCELLATION_PENDING")
        remove.assert_awaited_once_with(self.document["project_id"], self.document["_id"])
        set_index_status.assert_not_awaited()

    async def test_dispatched_run_cancellation_failure_keeps_revoke_retryable(self):
        with (
            patch.object(requirement_documents, "get_project_entity", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents.ai_automation_access_repository, "revoke_and_wait", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents.requirement_document_repository, "update_with_revision", new=AsyncMock(return_value=self.updated)),
            patch.object(requirement_documents, "cancel_pending_document_ingestion", new=AsyncMock(return_value=0)),
            patch.object(requirement_documents, "cancel_document_ingestion_runs", new=AsyncMock(side_effect=RuntimeError("AI unavailable"))) as cancel_runs,
            patch.object(requirement_documents, "remove_artifact", new=AsyncMock(return_value=True)) as remove,
            patch.object(requirement_documents.requirement_document_repository, "set_index_result", new=AsyncMock()) as save_index_status,
            patch.object(requirement_documents, "audit", new=AsyncMock()) as audit,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.update_requirement_document_ai_read(
                    self.document["_id"], self.payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["code"], "AI_INGESTION_CANCELLATION_PENDING")
        cancel_runs.assert_awaited_once_with(self.document["_id"])
        remove.assert_not_awaited()
        save_index_status.assert_not_awaited()
        self.assertFalse(self.updated["ai_enabled"])
        self.assertEqual(audit.await_args.args[1], "requirement_document.ai_read_event_cancellation_pending")

    async def test_concurrent_reenable_restores_index_before_reporting_revision_conflict(self):
        latest = {
            **self.document,
            "revision": 10,
            "ai_enabled": True,
            "index_status": "PENDING",
        }
        with (
            patch.object(requirement_documents, "get_project_entity", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents.ai_automation_access_repository, "revoke_and_wait", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents.requirement_document_repository, "update_with_revision", new=AsyncMock(return_value=self.updated)),
            patch.object(requirement_documents, "cancel_pending_document_ingestion", new=AsyncMock(return_value=1)),
            patch.object(requirement_documents, "cancel_document_ingestion_runs", new=AsyncMock(return_value=1)),
            patch.object(requirement_documents, "remove_artifact", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents.requirement_document_repository, "set_index_result", new=AsyncMock(return_value=SimpleNamespace(matched_count=0))),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=latest)),
            patch.object(requirement_documents, "index_requirement_document", new=AsyncMock(return_value=True)) as index,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.update_requirement_document_ai_read(
                    self.document["_id"], self.payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 409)
        index.assert_awaited_once_with(latest)


if __name__ == "__main__":
    unittest.main()
