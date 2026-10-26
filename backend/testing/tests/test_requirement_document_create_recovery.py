import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.requirements.services import requirement_documents
from src.schemas.contracts.requirements import ImportCreate


class RequirementDocumentCreateRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_duplicate_still_parsing_is_not_reused_as_complete(self):
        user = SimpleNamespace(id="ba-user", is_system_admin=False)
        shared = {
            "_id": "RDOC-shared-pending",
            "project_id": "project-1",
            "status": "PARSING",
            "created_by": "another-member",
        }
        with patch.object(
            requirement_documents,
            "recover_document_ingestion",
            new=AsyncMock(),
        ) as recover:
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.reuse_ready_requirement_document(shared, user)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "DUPLICATE_SOURCE_NOT_READY")
        recover.assert_not_awaited()

    async def test_archived_duplicate_requires_restore_instead_of_silent_reuse(self):
        user = SimpleNamespace(id="ba-user", is_system_admin=False)
        archived = {"_id": "RDOC-archived", "status": "ARCHIVED"}
        with self.assertRaises(HTTPException) as raised:
            await requirement_documents.reuse_ready_requirement_document(archived, user)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "DUPLICATE_SOURCE_ARCHIVED")

    async def test_shared_ready_duplicate_repairs_ingestion_before_reuse(self):
        user = SimpleNamespace(id="ba-user", is_system_admin=False)
        shared = {
            "_id": "RDOC-shared-ready",
            "project_id": "project-1",
            "status": "READY",
            "created_by": "another-member",
        }
        with (
            patch.object(requirement_documents, "recover_document_ingestion", new=AsyncMock(return_value=True)) as recover,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=shared)) as find,
        ):
            result = await requirement_documents.reuse_ready_requirement_document(shared, user)

        self.assertEqual(result["_id"], shared["_id"])
        recover.assert_awaited_once_with(shared, user)
        find.assert_awaited_once_with(shared["_id"], shared["project_id"])

    async def test_temporary_index_failure_does_not_revoke_ai_consent(self):
        user = SimpleNamespace(id="ba-user", is_system_admin=False)
        payload = ImportCreate(
            filename="requirements.txt",
            format="txt",
            content="User Story: A user signs in.",
            ai_enabled=True,
        )
        with (
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(requirement_documents, "validate_document_recipients", new=AsyncMock(return_value=[])),
            patch.object(requirement_documents, "resolve_source_successor", new=AsyncMock(return_value=None)),
            patch.object(requirement_documents.requirement_document_repository, "find_by_hash", new=AsyncMock(return_value=None)),
            patch.object(requirement_documents, "find_reusable_document_duplicate", new=AsyncMock(return_value=None)),
            patch.object(requirement_documents.requirement_document_repository, "insert", new=AsyncMock()) as insert,
            patch.object(requirement_documents.requirement_document_repository, "update", new=AsyncMock()) as update,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
            patch.object(requirement_documents, "index_requirement_document", new=AsyncMock(return_value=False)),
            patch.object(requirement_documents, "new_id", return_value="RDOC-create-recovery"),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.create_requirement_document_record(
                    "project-1", payload, user
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["code"], "KNOWLEDGE_INDEX_FAILED")
        self.assertTrue(insert.await_args.args[0]["ai_enabled"])
        update.assert_not_awaited()

    async def test_duplicate_retry_reindexes_then_requeues_the_same_revision(self):
        user = SimpleNamespace(id="ba-user", is_system_admin=False)
        stale = {
            "_id": "RDOC-create-recovery",
            "project_id": "project-1",
            "status": "READY",
            "revision": 2,
            "ai_enabled": True,
            "index_status": "FAILED",
        }
        recovered = {**stale, "index_status": "INDEXED"}
        with (
            patch.object(requirement_documents.ai_automation_access_repository, "allow_source", new=AsyncMock(return_value=True)) as allow_source,
            patch.object(requirement_documents, "index_requirement_document", new=AsyncMock(return_value=True)) as index,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=recovered)),
            patch.object(requirement_documents, "queue_document_ingestion", new=AsyncMock()) as enqueue,
        ):
            result = await requirement_documents.recover_document_ingestion(stale, user)

        self.assertTrue(result)
        allow_source.assert_awaited_once_with("source:RDOC-create-recovery")
        index.assert_awaited_once_with(stale)
        enqueue.assert_awaited_once_with(recovered, user)

    async def test_duplicate_retry_does_not_queue_when_source_fence_cannot_reopen(self):
        user = SimpleNamespace(id="ba-user", is_system_admin=False)
        ready = {
            "_id": "RDOC-create-recovery",
            "project_id": "project-1",
            "status": "READY",
            "revision": 2,
            "ai_enabled": True,
            "index_status": "INDEXED",
        }
        with (
            patch.object(requirement_documents.ai_automation_access_repository, "allow_source", new=AsyncMock(return_value=False)),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=ready)),
            patch.object(requirement_documents, "queue_document_ingestion", new=AsyncMock()) as enqueue,
        ):
            recovered = await requirement_documents.recover_document_ingestion(ready, user)

        self.assertFalse(recovered)
        enqueue.assert_not_awaited()

    async def test_duplicate_retry_completes_a_pending_permission_revocation(self):
        user = SimpleNamespace(id="ba-user", is_system_admin=False)
        stale = {
            "_id": "RDOC-revoke-recovery",
            "project_id": "project-1",
            "revision": 9,
            "status": "READY",
            "ai_enabled": False,
            "index_status": "REVOKE_PENDING",
        }
        with (
            patch.object(requirement_documents.ai_automation_access_repository, "revoke_and_wait", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents, "cancel_pending_document_ingestion", new=AsyncMock(return_value=1)) as cancel,
            patch.object(requirement_documents, "cancel_document_ingestion_runs", new=AsyncMock(return_value=1)) as cancel_runs,
            patch.object(requirement_documents, "remove_artifact", new=AsyncMock(return_value=True)) as remove,
            patch.object(
                requirement_documents.requirement_document_repository,
                "set_index_result",
                new=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
            ) as set_status,
        ):
            recovered = await requirement_documents.recover_document_ingestion(stale, user)

        self.assertTrue(recovered)
        cancel.assert_awaited_once_with(stale["_id"], "AI_READ_PERMISSION_REVOKED")
        cancel_runs.assert_awaited_once_with(stale["_id"])
        remove.assert_awaited_once_with(stale["project_id"], stale["_id"])
        self.assertEqual(set_status.await_args.kwargs["expected_revision"], 9)

    async def test_pending_revoke_retry_restores_index_if_permission_was_reenabled(self):
        user = SimpleNamespace(id="ba-user", is_system_admin=False)
        stale = {
            "_id": "RDOC-revoke-recovery",
            "project_id": "project-1",
            "revision": 9,
            "status": "READY",
            "ai_enabled": False,
            "index_status": "REVOKE_PENDING",
        }
        latest = {**stale, "revision": 10, "ai_enabled": True, "index_status": "PENDING"}
        with (
            patch.object(requirement_documents.ai_automation_access_repository, "revoke_and_wait", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents, "cancel_pending_document_ingestion", new=AsyncMock(return_value=1)),
            patch.object(requirement_documents, "cancel_document_ingestion_runs", new=AsyncMock(return_value=1)),
            patch.object(requirement_documents, "remove_artifact", new=AsyncMock(return_value=True)),
            patch.object(
                requirement_documents.requirement_document_repository,
                "set_index_result",
                new=AsyncMock(return_value=SimpleNamespace(matched_count=0)),
            ),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=latest)),
            patch.object(requirement_documents, "index_requirement_document", new=AsyncMock(return_value=True)) as index,
        ):
            recovered = await requirement_documents.recover_document_ingestion(stale, user)

        self.assertTrue(recovered)
        index.assert_awaited_once_with(latest)


if __name__ == "__main__":
    unittest.main()
