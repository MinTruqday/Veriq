import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.clients import ai_automation


class DocumentIngestionEventCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_revoke_cancels_only_pending_or_dispatching_event_for_document(self):
        outbox = SimpleNamespace(
            update_many=AsyncMock(return_value=SimpleNamespace(modified_count=2))
        )
        class FakeClient:
            def __getitem__(self, _database_name):
                return SimpleNamespace(ai_automation_outbox=outbox)

        with patch.object(ai_automation.database, "client", FakeClient()):
            cancelled = await ai_automation.cancel_pending_document_ingestion(
                "RDOC-1", "AI_READ_PERMISSION_REVOKED"
            )

        self.assertEqual(cancelled, 2)
        query, update = outbox.update_many.await_args.args
        self.assertEqual(query["trigger"], "DOCUMENT_INGESTED")
        self.assertEqual(query["status"], {"$in": ["PENDING", "DISPATCHING"]})
        self.assertEqual(
            query["payload.evidence"]["$elemMatch"],
            {"artifact_type": "requirement_document", "artifact_id": "RDOC-1"},
        )
        self.assertEqual(update["$set"]["status"], "CANCELLED")
        self.assertEqual(update["$set"]["cancel_reason"], "AI_READ_PERMISSION_REVOKED")
        self.assertIn("payload", update["$unset"])


if __name__ == "__main__":
    unittest.main()
