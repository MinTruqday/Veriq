import unittest

from src.store.bm25 import BM25Store


class BM25LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = BM25Store()
        await self.store.initialize(
            [
                {
                    "id": "document-v1",
                    "text": "authentication token expires at sunset",
                    "metadata": {"document_id": "document-1", "visibility": "public"},
                },
                {
                    "id": "other-document",
                    "text": "payment settlement reconciliation",
                    "metadata": {"document_id": "document-2", "visibility": "public"},
                },
            ]
        )

    async def test_update_replaces_old_text_and_delete_removes_document(self):
        await self.store.upsert(
            [
                {
                    "id": "document-v1",
                    "text": "authentication token expires at midnight",
                    "metadata": {"document_id": "document-1", "visibility": "public"},
                }
            ]
        )

        updated = await self.store.search("midnight", limit=10, is_admin=True)
        stale = await self.store.search("sunset", limit=10, is_admin=True)
        self.assertEqual([item["id"] for item in updated], ["document-v1"])
        self.assertEqual(stale, [])

        await self.store.delete_by_document("document-1")
        remaining = await self.store.search("authentication token", limit=10, is_admin=True)
        self.assertEqual(remaining, [])

    async def test_staged_replacement_publishes_atomically(self):
        await self.store.stage_upsert(
            [
                {
                    "id": "document-v1",
                    "text": "authentication token expires at midnight",
                    "metadata": {"document_id": "document-1", "visibility": "public"},
                }
            ],
            stage_id="replacement",
        )

        before_publish = await self.store.search("sunset", limit=10, is_admin=True)
        self.assertEqual([item["id"] for item in before_publish], ["document-v1"])

        await self.store.publish_staged("replacement")

        after_publish = await self.store.search("midnight", limit=10, is_admin=True)
        stale = await self.store.search("sunset", limit=10, is_admin=True)
        self.assertEqual([item["id"] for item in after_publish], ["document-v1"])
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
