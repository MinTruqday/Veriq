import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.services import retrieval
from src.store.vector import VectorStore


def async_batches(batches):
    async def stream(_batch_size=256):
        for batch in batches:
            yield batch

    return stream


class LegacyVectorPayloadCleanupTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def consuming_bm25_mock(indexed_documents):
        async def consume(documents):
            async for document in documents:
                indexed_documents.append(document)

        return AsyncMock(side_effect=consume)

    async def test_vector_scroll_stream_yields_each_page_without_collecting_all_points(self):
        store = VectorStore()
        store.client = AsyncMock()
        store.client.scroll.side_effect = [
            ([SimpleNamespace(id="point-1", payload={"text": "first"})], "next"),
            ([SimpleNamespace(id="point-2", payload={"text": "second"})], None),
        ]

        batches = [batch async for batch in store.iter_scroll_batches(batch_size=1)]

        self.assertEqual(
            [[item["id"] for item in batch] for batch in batches],
            [["point-1"], ["point-2"]],
        )
        self.assertEqual(store.client.scroll.await_count, 2)

    async def test_vector_store_deletes_only_requested_payload_keys_and_points(self):
        store = VectorStore()
        store.client = AsyncMock()

        await store.delete_payload_keys(["point-1", "point-2"], ["file_url"])

        store.client.delete_payload.assert_awaited_once()
        kwargs = store.client.delete_payload.await_args.kwargs
        self.assertEqual(kwargs["collection_name"], "veriq")
        self.assertEqual(kwargs["keys"], ["file_url"])
        self.assertEqual(kwargs["points"].points, ["point-1", "point-2"])
        self.assertTrue(kwargs["wait"])

    async def test_startup_removes_legacy_object_urls_before_bm25_load(self):
        documents = [
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "text": "Private document chunk",
                "metadata": {
                    "document_id": "doc-private",
                    "file_url": "https://object-store.invalid/signed/private-token",
                    "embedding_model": retrieval.settings.EMBEDDING_MODEL,
                },
            },
            {
                "id": "00000000-0000-4000-8000-000000000002",
                "text": "Public document chunk",
                "metadata": {
                    "document_id": "doc-public",
                    "embedding_model": retrieval.settings.EMBEDDING_MODEL,
                },
            },
        ]
        indexed_documents = []
        initialize_bm25 = self.consuming_bm25_mock(indexed_documents)
        with (
            patch.object(retrieval.embedder, "initialize", new=AsyncMock(return_value=[0.0])),
            patch.object(retrieval.embedder, "_dimensions", 1),
            patch.object(retrieval.vector_store, "ensure_collection", new=AsyncMock()),
            patch.object(retrieval.vector_store, "iter_scroll_batches", new=async_batches([documents])),
            patch.object(retrieval.vector_store, "delete_payload_keys", new=AsyncMock()) as delete_payload,
            patch.object(retrieval.bm25_store, "initialize_stream", new=initialize_bm25),
            patch.object(retrieval.retriever, "initialize", new=AsyncMock()),
        ):
            await retrieval.initialize_retrieval()

        delete_payload.assert_awaited_once_with(
            ["00000000-0000-4000-8000-000000000001"], ["file_url"]
        )
        self.assertNotIn("file_url", indexed_documents[0]["metadata"])
        self.assertEqual(indexed_documents[0]["metadata"]["document_id"], "doc-private")
        self.assertNotIn("file_url", indexed_documents[1]["metadata"])

    async def test_startup_does_not_delete_payload_when_no_legacy_url_exists(self):
        documents = [
            {
                "id": "00000000-0000-4000-8000-000000000003",
                "text": "Public document chunk",
                "metadata": {
                    "document_id": "doc-public",
                    "embedding_model": retrieval.settings.EMBEDDING_MODEL,
                },
            }
        ]
        indexed_documents = []
        initialize_bm25 = self.consuming_bm25_mock(indexed_documents)
        with (
            patch.object(retrieval.embedder, "initialize", new=AsyncMock(return_value=[0.0])),
            patch.object(retrieval.embedder, "_dimensions", 1),
            patch.object(retrieval.vector_store, "ensure_collection", new=AsyncMock()),
            patch.object(retrieval.vector_store, "iter_scroll_batches", new=async_batches([documents])),
            patch.object(retrieval.vector_store, "delete_payload_keys", new=AsyncMock()) as delete_payload,
            patch.object(retrieval.bm25_store, "initialize_stream", new=initialize_bm25),
            patch.object(retrieval.retriever, "initialize", new=AsyncMock()),
        ):
            await retrieval.initialize_retrieval()

        self.assertEqual(len(indexed_documents), 1)
        delete_payload.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
