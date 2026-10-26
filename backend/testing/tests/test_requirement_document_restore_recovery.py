import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.requirements.services import requirement_documents
from src.schemas.contracts.project import ProjectArchiveInput


class RequirementDocumentRestoreRecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="owner-1", is_system_admin=False)
        self.payload = ProjectArchiveInput(expected_revision=4, reason="Restore source")
        self.restored = {
            "_id": "RDOC-restore-1",
            "project_id": "PRJ-1",
            "status": "READY",
            "revision": 5,
            "ai_enabled": True,
            "index_status": "FAILED",
        }

    async def test_retry_after_restore_index_failure_rebuilds_and_requeues(self):
        latest = {**self.restored, "index_status": "INDEXED"}
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=self.restored)),
            patch.object(requirement_documents, "recover_document_ingestion", new=AsyncMock(return_value=True)) as recover,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=latest)),
        ):
            result = await requirement_documents.restore_requirement_document_record(
                self.restored["_id"], self.payload, self.user
            )

        self.assertEqual(result, latest)
        recover.assert_awaited_once_with(self.restored, self.user)

    async def test_retry_restore_remains_retryable_when_index_recovery_fails(self):
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=self.restored)),
            patch.object(requirement_documents, "recover_document_ingestion", new=AsyncMock(return_value=False)),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=self.restored)),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.restore_requirement_document_record(
                    self.restored["_id"], self.payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["code"], "DOCUMENT_RESTORE_RECOVERY_PENDING")

    async def test_restoring_archive_reopens_source_before_queueing_ingestion(self):
        archived = {
            **self.restored,
            "status": "ARCHIVED",
            "revision": 4,
            "status_before_archive": "READY",
        }
        latest = {**self.restored, "index_status": "INDEXED"}
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=archived)),
            patch.object(requirement_documents.requirement_document_repository, "update_with_revision", new=AsyncMock(return_value=self.restored)) as update,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=latest)),
            patch.object(requirement_documents, "index_requirement_document", new=AsyncMock(return_value=True)) as index,
            patch.object(requirement_documents.ai_automation_access_repository, "allow_source", new=AsyncMock(return_value=True)) as allow_source,
            patch.object(requirement_documents, "queue_document_ingestion", new=AsyncMock()) as enqueue,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            result = await requirement_documents.restore_requirement_document_record(
                archived["_id"], self.payload, self.user
            )

        self.assertEqual(result, latest)
        self.assertEqual(update.await_args.kwargs["status"], "ARCHIVED")
        index.assert_awaited_once_with(self.restored)
        allow_source.assert_awaited_once_with("source:RDOC-restore-1")
        enqueue.assert_awaited_once_with(latest, self.user)


if __name__ == "__main__":
    unittest.main()
