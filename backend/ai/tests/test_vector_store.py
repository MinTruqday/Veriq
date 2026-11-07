import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    PayloadSchemaType,
    PointIdsList,
    VectorParams,
)

from src.core.infrastructure.configuration import settings
from src.services.embedding import embedder
from src.store.vector import VectorStore


def collection_info(vector_config, payload_schema=None):
    return SimpleNamespace(
        config=SimpleNamespace(params=SimpleNamespace(vectors=vector_config)),
        payload_schema=payload_schema or {},
    )


class VectorCollectionInitializationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = VectorStore.__new__(VectorStore)
        self.store.collection_name = "test_collection"
        self.store.upsert_batch_size = VectorStore.UPSERT_BATCH_SIZE
        self.store.client = AsyncMock()
        self.store.client.get_collections.return_value = SimpleNamespace(
            collections=[SimpleNamespace(name="test_collection")]
        )
        self.store.client.get_collection.return_value = collection_info(
            VectorParams(size=embedder._dimensions, distance=Distance.COSINE)
        )

    async def test_existing_collection_with_matching_schema_is_not_reindexed(self):
        self.store.client.get_collection.return_value = collection_info(
            VectorParams(size=embedder._dimensions, distance=Distance.COSINE),
            {
                field: SimpleNamespace(data_type=field_type)
                for field, field_type in VectorStore.PAYLOAD_INDEX_FIELDS.items()
            },
        )

        await self.store.ensure_collection()

        self.store.client.create_payload_index.assert_not_awaited()
        self.store.client.delete_payload_index.assert_not_awaited()

    async def test_missing_payload_indexes_are_created_without_replacing_existing_ones(self):
        existing_field, existing_type = next(iter(VectorStore.PAYLOAD_INDEX_FIELDS.items()))
        self.store.client.get_collection.return_value = collection_info(
            VectorParams(size=embedder._dimensions, distance=Distance.COSINE),
            {existing_field: SimpleNamespace(data_type=existing_type)},
        )

        await self.store.ensure_collection()

        self.assertEqual(
            self.store.client.create_payload_index.await_count,
            len(VectorStore.PAYLOAD_INDEX_FIELDS) - 1,
        )
        self.store.client.delete_payload_index.assert_not_awaited()

    async def test_vector_dimension_mismatch_fails_without_mutating_collection(self):
        self.store.client.get_collection.return_value = collection_info(
            VectorParams(size=embedder._dimensions + 1, distance=Distance.COSINE)
        )

        with self.assertRaisesRegex(RuntimeError, "qdrant_collection_vector_schema_mismatch"):
            await self.store.ensure_collection()

        self.store.client.create_payload_index.assert_not_awaited()
        self.store.client.delete_payload_index.assert_not_awaited()

    async def test_vector_distance_mismatch_fails_without_mutating_collection(self):
        self.store.client.get_collection.return_value = collection_info(
            VectorParams(size=embedder._dimensions, distance=Distance.DOT)
        )

        with self.assertRaisesRegex(RuntimeError, "qdrant_collection_vector_schema_mismatch"):
            await self.store.ensure_collection()

        self.store.client.create_payload_index.assert_not_awaited()

    async def test_wrong_payload_index_type_is_reported_without_deletion(self):
        field, _ = next(iter(VectorStore.PAYLOAD_INDEX_FIELDS.items()))
        self.store.client.get_collection.return_value = collection_info(
            VectorParams(size=embedder._dimensions, distance=Distance.COSINE),
            {field: SimpleNamespace(data_type=PayloadSchemaType.INTEGER)},
        )

        with self.assertRaisesRegex(RuntimeError, f"qdrant_payload_index_schema_mismatch:{field}"):
            await self.store.ensure_collection()

        self.store.client.delete_payload_index.assert_not_awaited()
        self.store.client.create_payload_index.assert_not_awaited()

    async def test_polymorphic_field_index_is_reported_without_deletion(self):
        self.store.client.get_collection.return_value = collection_info(
            VectorParams(size=embedder._dimensions, distance=Distance.COSINE),
            {"source_version": SimpleNamespace(data_type=PayloadSchemaType.KEYWORD)},
        )

        with self.assertRaisesRegex(RuntimeError, "qdrant_unindexed_payload_field_has_index:source_version"):
            await self.store.ensure_collection()

        self.store.client.delete_payload_index.assert_not_awaited()

    async def test_document_deletion_waits_until_qdrant_applies_it(self):
        await self.store.delete_by_document("document-1")

        self.store.client.delete.assert_awaited_once()
        self.assertIs(self.store.client.delete.await_args.kwargs["wait"], True)


class VectorStoreQdrantIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_temporary_collection_supports_upsert_search_update_and_delete(self):
        store = VectorStore()
        store.collection_name = f"veriq_test_{uuid4().hex}"
        client = AsyncQdrantClient(url=settings.QDRANT_URL, timeout=30)
        store.client = client
        first_id = str(uuid4())
        second_id = str(uuid4())
        vector = [1.0, *([0.0] * (embedder._dimensions - 1))]
        try:
            await store.ensure_collection()
            await store.upsert(
                ids=[first_id, second_id],
                embeddings=[vector, vector],
                documents=["first version", "other source"],
                metadatas=[
                    {"embedding_model": settings.EMBEDDING_MODEL, "visibility": "public"},
                    {"embedding_model": settings.EMBEDDING_MODEL, "visibility": "public"},
                ],
            )
            first_search = await store.query(vector, limit=2, is_admin=True)
            self.assertEqual({item["id"] for item in first_search}, {first_id, second_id})

            await store.upsert(
                ids=[first_id],
                embeddings=[vector],
                documents=["updated source"],
                metadatas=[
                    {"embedding_model": settings.EMBEDDING_MODEL, "visibility": "public"}
                ],
            )
            updated_search = await store.query(vector, limit=2, is_admin=True)
            self.assertEqual(
                next(item["text"] for item in updated_search if item["id"] == first_id),
                "updated source",
            )

            await client.delete(
                collection_name=store.collection_name,
                points_selector=PointIdsList(points=[first_id, second_id]),
                wait=True,
            )
            self.assertEqual(await store.query(vector, limit=2, is_admin=True), [])
        finally:
            await client.delete_collection(collection_name=store.collection_name)
            await client.close()


if __name__ == "__main__":
    unittest.main()
