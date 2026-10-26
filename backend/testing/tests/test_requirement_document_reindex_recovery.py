import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.modules.requirements.services import requirement_documents


class RequirementDocumentReindexRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.document = {
            "_id": "RDOC-reindex-recovery",
            "project_id": "PRJ-reindex-recovery",
            "status": "READY",
            "ai_enabled": True,
            "revision": 4,
        }
        self.updated_document = {**self.document, "revision": 4}
        self.user = SimpleNamespace(id="user-qa", is_system_admin=False)

    async def test_successful_reindex_requeues_current_document_revision(self):
        with (
            patch.object(
                requirement_documents,
                "get_requirement_document_record",
                new=AsyncMock(return_value=self.document),
            ),
            patch.object(
                requirement_documents,
                "index_requirement_document",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                requirement_documents.requirement_document_repository,
                "update",
                new=AsyncMock(),
            ) as update,
            patch.object(
                requirement_documents.requirement_document_repository,
                "find",
                new=AsyncMock(return_value=self.updated_document),
            ),
            patch.object(
                requirement_documents,
                "queue_document_ingestion",
                new=AsyncMock(return_value=True),
            ) as enqueue,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            result = await requirement_documents.reindex_requirement_document_record(
                self.document["_id"], self.user
            )

        self.assertEqual(result.data["revision"], 4)
        update.assert_awaited_once()
        self.assertNotIn("increment_revision", update.await_args.kwargs)
        enqueue.assert_awaited_once_with(self.updated_document, self.user)

    async def test_failed_reindex_does_not_enqueue_ai_work(self):
        with (
            patch.object(
                requirement_documents,
                "get_requirement_document_record",
                new=AsyncMock(return_value=self.document),
            ),
            patch.object(
                requirement_documents,
                "index_requirement_document",
                new=AsyncMock(return_value=False),
            ),
            patch.object(
                requirement_documents.requirement_document_repository,
                "update",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_documents.requirement_document_repository,
                "find",
                new=AsyncMock(return_value=self.updated_document),
            ),
            patch.object(
                requirement_documents,
                "queue_document_ingestion",
                new=AsyncMock(return_value=True),
            ) as enqueue,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            result = await requirement_documents.reindex_requirement_document_record(
                self.document["_id"], self.user
            )

        self.assertEqual(result.status, "DEGRADED")
        enqueue.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
