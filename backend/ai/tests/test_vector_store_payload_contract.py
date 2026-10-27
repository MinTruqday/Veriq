import unittest
from unittest.mock import AsyncMock

from qdrant_client.http.models import PayloadSchemaType

from src.store.vector import VectorStore


class VectorStorePayloadContractTests(unittest.IsolatedAsyncioTestCase):
    def test_payload_indexes_follow_payload_types(self):
        self.assertEqual(
            VectorStore.PAYLOAD_INDEX_FIELDS["ocr_enabled"],
            PayloadSchemaType.BOOL,
        )
        self.assertEqual(
            VectorStore.PAYLOAD_INDEX_FIELDS["unprocessed_block_count"],
            PayloadSchemaType.INTEGER,
        )
        self.assertEqual(
            VectorStore.PAYLOAD_INDEX_FIELDS["indexed_at"],
            PayloadSchemaType.DATETIME,
        )
        self.assertEqual(
            VectorStore.PAYLOAD_INDEX_FIELDS["document_index_contract_version"],
            PayloadSchemaType.INTEGER,
        )
        self.assertEqual(
            VectorStore.PAYLOAD_INDEX_FIELDS["source_document_id"],
            PayloadSchemaType.KEYWORD,
        )
        self.assertNotIn("source_version", VectorStore.PAYLOAD_INDEX_FIELDS)

    async def test_upsert_persists_content_with_metadata_and_preserves_extensions(self):
        store = VectorStore()
        store.client.upsert = AsyncMock()

        await store.upsert(
            ["point-1"],
            [[0.1, 0.2]],
            ["normalized source chunk"],
            [{"project_id": "project-1", "source_spans": [], "custom_ref": "r-1"}],
        )

        point = store.client.upsert.await_args.kwargs["points"][0]
        self.assertEqual(point.id, "point-1")
        self.assertEqual(point.vector, [0.1, 0.2])
        self.assertEqual(point.payload["text"], "normalized source chunk")
        self.assertEqual(point.payload["char_count"], len("normalized source chunk"))
        self.assertEqual(point.payload["word_count"], 3)
        self.assertEqual(point.payload["project_id"], "project-1")
        self.assertEqual(point.payload["custom_ref"], "r-1")

    async def test_upsert_rejects_metadata_that_disagrees_with_embedded_content(self):
        store = VectorStore()
        store.client.upsert = AsyncMock()

        with self.assertRaisesRegex(ValueError, "content_metadata_conflict"):
            await store.upsert(
                ["point-1"],
                [[0.1, 0.2]],
                ["embedded content"],
                [{"text": "different payload content"}],
            )

        store.client.upsert.assert_not_awaited()

    async def test_upsert_rejects_document_point_without_artifact_type(self):
        store = VectorStore()
        store.client.upsert = AsyncMock()

        with self.assertRaisesRegex(ValueError, "document_artifact_type_missing"):
            await store.upsert(
                ["point-legacy-document"],
                [[0.1, 0.2]],
                ["legacy document content"],
                [{"document_id": "doc-1"}],
            )

        store.client.upsert.assert_not_awaited()

    async def test_upsert_requires_matching_batch_lengths(self):
        store = VectorStore()
        store.client.upsert = AsyncMock()

        with self.assertRaisesRegex(ValueError, "batch_lengths_must_match"):
            await store.upsert(["point-1"], [[0.1]], [], [{}])

        store.client.upsert.assert_not_awaited()

    async def test_artifact_generation_deletion_requires_complete_scope(self):
        store = VectorStore()
        store.client.delete = AsyncMock()

        with self.assertRaisesRegex(ValueError, "project_artifact_cleanup_scope_invalid"):
            await store.delete_artifact_generation(
                "project-1", "requirement_version", "req-1", "version-1", ""
            )
        with self.assertRaisesRegex(ValueError, "project_artifact_cleanup_scope_invalid"):
            await store.delete_stale_artifact_generations(
                "project-1", "requirement_version", "req-1", "version-1", " "
            )

        store.client.delete.assert_not_awaited()

    async def test_document_and_artifact_deletion_require_complete_scope(self):
        store = VectorStore()
        store.client.delete = AsyncMock()

        with self.assertRaisesRegex(ValueError, "document_index_cleanup_scope_invalid"):
            await store.delete_by_document(" ")
        with self.assertRaisesRegex(ValueError, "project_artifact_cleanup_scope_invalid"):
            await store.delete_artifact_version("project-1", "requirement", "req-1", "")
        with self.assertRaisesRegex(ValueError, "project_artifact_cleanup_scope_invalid"):
            await store.delete_project_artifact_version("", "version-1")

        store.client.delete.assert_not_awaited()
