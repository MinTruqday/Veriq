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

    def test_final_retrieval_filter_rejects_untyped_and_outdated_document_points(self):
        current_document = {
            "metadata": {
                "artifact_type": "project_document",
                "document_id": "doc-current",
                "document_index_contract_version": retrieval.settings.DOCUMENT_INDEX_CONTRACT_VERSION,
            }
        }
        legacy_untyped_document = {
            "metadata": {"document_id": "doc-untyped"}
        }
        legacy_source_document = {
            "metadata": {"source_document_id": "doc-source-untyped"}
        }
        legacy_typed_document = {
            "metadata": {
                "artifact_type": "project_document",
                "document_id": "doc-old-contract",
                "document_index_contract_version": retrieval.settings.DOCUMENT_INDEX_CONTRACT_VERSION - 1,
            }
        }
        non_document_artifact = {
            "metadata": {"artifact_type": "test_case_version", "artifact_id": "tc-1"}
        }

        self.assertEqual(
            retrieval.RetrievalService._filter_document_index_contract(
                [
                    current_document,
                    legacy_untyped_document,
                    legacy_source_document,
                    legacy_typed_document,
                    non_document_artifact,
                ]
            ),
            [current_document, non_document_artifact],
        )

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

    async def test_generation_cleanup_rejects_incomplete_scope_before_qdrant_call(self):
        store = VectorStore()
        store.client = AsyncMock()

        with self.assertRaisesRegex(ValueError, "document_index_cleanup_scope_invalid"):
            await store.delete_document_generation("doc-1", " ")
        with self.assertRaisesRegex(ValueError, "document_index_cleanup_scope_invalid"):
            await store.delete_stale_document_generations("", "generation-1")

        store.client.delete.assert_not_awaited()

    async def test_startup_removes_legacy_object_urls_before_bm25_load(self):
        documents = [
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "text": "Private document chunk",
                "metadata": {
                    "artifact_type": "project_document",
                    "document_id": "doc-private",
                    "document_index_contract_version": retrieval.settings.DOCUMENT_INDEX_CONTRACT_VERSION,
                    "file_url": "https://object-store.invalid/signed/private-token",
                    "embedding_model": retrieval.settings.EMBEDDING_MODEL,
                },
            },
            {
                "id": "00000000-0000-4000-8000-000000000002",
                "text": "Public document chunk",
                "metadata": {
                    "artifact_type": "project_document",
                    "document_id": "doc-public",
                    "document_index_contract_version": retrieval.settings.DOCUMENT_INDEX_CONTRACT_VERSION,
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
                    "artifact_type": "project_document",
                    "document_id": "doc-public",
                    "document_index_contract_version": retrieval.settings.DOCUMENT_INDEX_CONTRACT_VERSION,
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

    async def test_startup_excludes_incomplete_legacy_document_until_reindex(self):
        legacy = {
            "id": "00000000-0000-4000-8000-000000000004",
            "text": "Legacy document text",
            "metadata": {
                "artifact_type": "project_document",
                "document_id": "doc-legacy",
                "embedding_model": "retired-model",
            },
        }
        indexed_documents = []
        initialize_bm25 = self.consuming_bm25_mock(indexed_documents)
        with (
            patch.object(retrieval.embedder, "initialize", new=AsyncMock(return_value=[0.0])),
            patch.object(retrieval.embedder, "_dimensions", 1),
            patch.object(retrieval.vector_store, "ensure_collection", new=AsyncMock()),
            patch.object(retrieval.vector_store, "iter_scroll_batches", new=async_batches([[legacy]])),
            patch.object(retrieval.embedder, "embed_batch", new=AsyncMock()) as embed_batch,
            patch.object(retrieval.vector_store, "upsert", new=AsyncMock()) as upsert,
            patch.object(retrieval.bm25_store, "initialize_stream", new=initialize_bm25),
            patch.object(retrieval.retriever, "initialize", new=AsyncMock()),
        ):
            await retrieval.initialize_retrieval()

        embed_batch.assert_not_awaited()
        upsert.assert_not_awaited()
        self.assertEqual(indexed_documents, [])

    async def test_startup_excludes_legacy_document_without_artifact_type(self):
        legacy = {
            "id": "00000000-0000-4000-8000-000000000005",
            "text": "Legacy untyped document text",
            "metadata": {
                "document_id": "doc-untyped-legacy",
                "embedding_model": retrieval.settings.EMBEDDING_MODEL,
            },
        }
        indexed_documents = []
        initialize_bm25 = self.consuming_bm25_mock(indexed_documents)
        with (
            patch.object(retrieval.embedder, "initialize", new=AsyncMock(return_value=[0.0])),
            patch.object(retrieval.embedder, "_dimensions", 1),
            patch.object(retrieval.vector_store, "ensure_collection", new=AsyncMock()),
            patch.object(retrieval.vector_store, "iter_scroll_batches", new=async_batches([[legacy]])),
            patch.object(retrieval.bm25_store, "initialize_stream", new=initialize_bm25),
            patch.object(retrieval.retriever, "initialize", new=AsyncMock()),
        ):
            await retrieval.initialize_retrieval()

        self.assertEqual(indexed_documents, [])

    async def test_dense_search_is_scoped_to_the_active_embedding_model(self):
        store = VectorStore()
        store.client = AsyncMock()
        store.client.search.return_value = []

        await store.query([0.1])

        query_filter = store.client.search.await_args.kwargs["query_filter"]
        self.assertEqual(query_filter.must[0].key, "embedding_model")
        self.assertEqual(
            query_filter.must[0].match.value,
            retrieval.settings.EMBEDDING_MODEL,
        )
        document_contract_filter = query_filter.must[1]
        self.assertTrue(
            any(
                getattr(condition, "is_empty", None) is not None
                and condition.is_empty.key == "artifact_type"
                for condition in document_contract_filter.should[0].must_not
            )
        )
        self.assertEqual(
            [condition.is_empty.key for condition in document_contract_filter.should[1].must],
            ["artifact_type", "document_id", "source_document_id"],
        )
        self.assertEqual(
            document_contract_filter.should[2].must[1].key,
            "document_index_contract_version",
        )
        self.assertEqual(
            document_contract_filter.should[2].must[1].match.value,
            retrieval.settings.DOCUMENT_INDEX_CONTRACT_VERSION,
        )


if __name__ == "__main__":
    unittest.main()
