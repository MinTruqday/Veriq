import unittest
from unittest.mock import AsyncMock, patch

from src.clients.content import ContentClient


class ContentLiveAccessClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_access_checks_large_results_in_bounded_batches(self):
        document_ids = [f"document-{index}" for index in range(201)]
        document_ids.insert(7, "document-0")
        exchange = AsyncMock(
            side_effect=[
                {"documents": [{"_id": f"document-{index}"} for index in range(100)]},
                {
                    "documents": [
                        {"_id": f"document-{index}"} for index in range(100, 200)
                    ]
                },
                {"documents": [{"_id": "document-200"}]},
            ]
        )

        with patch.object(ContentClient, "exchange", new=exchange):
            accessible = await ContentClient.authorize_read_many(
                document_ids, requester_id="user-1", is_admin=False
            )

        calls = [call.kwargs["document_ids"] for call in exchange.await_args_list]
        self.assertEqual([len(batch) for batch in calls], [100, 100, 1])
        self.assertEqual(len(accessible), 201)
        self.assertEqual(accessible, [f"document-{index}" for index in range(201)])
        self.assertEqual(len(set(accessible)), len(accessible))

    async def test_bulk_access_rejects_malformed_response(self):
        with patch.object(ContentClient, "exchange", new=AsyncMock(return_value=[])):
            with self.assertRaisesRegex(RuntimeError, "content_document_access_response_invalid"):
                await ContentClient.authorize_read_many(["document-1"], "user-1", False)

    async def test_active_index_generation_is_returned_with_live_access(self):
        with patch.object(
            ContentClient,
            "exchange",
            new=AsyncMock(
                return_value={
                    "documents": [
                        {
                            "_id": "document-1",
                            "active_index_generation": "a" * 64,
                        },
                        {"_id": "document-2", "active_index_generation": None},
                    ]
                }
            ),
        ):
            generations = await ContentClient.active_index_generations_many(
                ["document-1", "document-2"], "user-1", False
            )

        self.assertEqual(
            generations,
            {"document-1": "a" * 64, "document-2": None},
        )


if __name__ == "__main__":
    unittest.main()
