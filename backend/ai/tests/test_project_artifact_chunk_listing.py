import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.knowledge.metadata import public_retrieval_metadata
from src.services import project_knowledge
from src.store.bm25 import BM25Store
from src.store.vector import VectorStore


class ProjectArtifactChunkListingTests(unittest.IsolatedAsyncioTestCase):
    async def test_bm25_document_and_artifact_deletion_require_complete_scope(self):
        store = BM25Store()
        await store.initialize(
            [
                {
                    "id": "document-point",
                    "text": "Document content",
                    "metadata": {"document_id": "doc-1"},
                },
                {
                    "id": "artifact-point",
                    "text": "Requirement content",
                    "metadata": {
                        "project_id": "project-1",
                        "artifact_type": "requirement",
                        "artifact_id": "req-1",
                        "artifact_version_id": "version-1",
                    },
                },
            ]
        )

        with self.assertRaisesRegex(ValueError, "document_index_cleanup_scope_invalid"):
            await store.delete_by_document(" ")
        with self.assertRaisesRegex(ValueError, "project_artifact_cleanup_scope_invalid"):
            await store.delete_artifact_version("project-1", "requirement", "req-1", "")
        with self.assertRaisesRegex(ValueError, "project_artifact_cleanup_scope_invalid"):
            await store.delete_project_artifact_version("", "version-1")

        self.assertEqual(set(store._documents), {"document-point", "artifact-point"})

    async def test_bm25_artifact_generation_deletion_requires_complete_scope(self):
        store = BM25Store()
        await store.initialize(
            [
                {
                    "id": "active-point",
                    "text": "Current artifact generation",
                    "metadata": {
                        "project_id": "project-1",
                        "artifact_type": "requirement_version",
                        "artifact_id": "req-1",
                        "artifact_version_id": "version-1",
                        "index_generation": "active-generation",
                    },
                }
            ]
        )

        with self.assertRaisesRegex(ValueError, "project_artifact_cleanup_scope_invalid"):
            await store.delete_artifact_generation(
                "project-1", "requirement_version", "req-1", "version-1", ""
            )
        with self.assertRaisesRegex(ValueError, "project_artifact_cleanup_scope_invalid"):
            await store.delete_stale_artifact_generations(
                "project-1", "requirement_version", "req-1", "version-1", " "
            )

        self.assertEqual(
            await store.ids_by_artifact_version("project-1", "version-1"),
            ["active-point"],
        )

    async def test_bm25_generation_cleanup_rejects_incomplete_scope_without_mutating_index(self):
        store = BM25Store()
        await store.initialize(
            [
                {
                    "id": "kept-point",
                    "text": "Keep this document indexed",
                    "metadata": {"document_id": "doc-1", "index_generation": "generation-1"},
                }
            ]
        )

        with self.assertRaisesRegex(ValueError, "document_index_cleanup_scope_invalid"):
            await store.delete_document_generation("doc-1", "")
        with self.assertRaisesRegex(ValueError, "document_index_cleanup_scope_invalid"):
            await store.delete_stale_document_generations("doc-1", " ")

        self.assertEqual(await store.ids_by_document("doc-1"), ["kept-point"])

    async def test_bm25_publishes_only_the_requested_staged_generation(self):
        store = BM25Store()
        await store.initialize(
            [
                {
                    "id": "published-point",
                    "text": "Published requirement source",
                    "metadata": {"project_id": "project-1"},
                }
            ]
        )
        await store.stage_upsert(
            [
                {
                    "id": "generation-a-point",
                    "text": "Generation alpha source",
                    "metadata": {"project_id": "project-1"},
                }
            ],
            "generation-a",
        )
        await store.stage_upsert(
            [
                {
                    "id": "generation-b-point",
                    "text": "Generation beta source",
                    "metadata": {"project_id": "project-1"},
                }
            ],
            "generation-b",
        )

        self.assertEqual(set(store._documents), {"published-point"})
        await store.publish_staged("generation-a")
        self.assertEqual(set(store._documents), {"published-point", "generation-a-point"})
        await store.publish_staged("generation-b")
        self.assertEqual(
            set(store._documents),
            {"published-point", "generation-a-point", "generation-b-point"},
        )

    async def test_bm25_publish_failure_preserves_active_index_and_staged_retry_data(self):
        store = BM25Store()
        await store.initialize(
            [
                {
                    "id": "published-point",
                    "text": "Published requirement source",
                    "metadata": {"project_id": "project-1"},
                }
            ]
        )
        published_documents = store._documents
        published_order = store._ordered_ids
        published_index = store._index
        await store.stage_upsert(
            [
                {
                    "id": "next-point",
                    "text": "New requirement source",
                    "metadata": {"project_id": "project-1"},
                }
            ],
            "next-generation",
        )

        with patch.object(
            store,
            "_build_index",
            side_effect=RuntimeError("bm25_build_failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "bm25_build_failed"):
                await store.publish_staged("next-generation")

        self.assertIs(store._documents, published_documents)
        self.assertIs(store._ordered_ids, published_order)
        self.assertIs(store._index, published_index)
        self.assertIn("next-generation", store._staged_documents)
        self.assertIn("next-point", store._staged_documents["next-generation"])

    async def test_bm25_stream_initialization_keeps_published_index_on_source_failure(self):
        store = BM25Store()
        await store.initialize(
            [
                {
                    "id": "published-point",
                    "text": "Published requirement source",
                    "metadata": {"project_id": "project-1"},
                }
            ]
        )
        published_documents = store._documents
        published_order = store._ordered_ids
        published_index = store._index

        async def broken_stream():
            yield {
                "id": "partial-point",
                "text": "Partially loaded source",
                "metadata": {"project_id": "project-1"},
            }
            raise RuntimeError("qdrant_scroll_failed")

        with self.assertRaisesRegex(RuntimeError, "qdrant_scroll_failed"):
            await store.initialize_stream(broken_stream())

        self.assertIs(store._documents, published_documents)
        self.assertIs(store._ordered_ids, published_order)
        self.assertIs(store._index, published_index)
        self.assertIn("published-point", store._documents)
        self.assertNotIn("partial-point", store._documents)

    async def test_qdrant_artifact_scroll_skips_content_points_without_empty_cursor_page(self):
        content_point = SimpleNamespace(
            id="content-point",
            payload={
                "document_id": "document-1",
                "index_generation": "content-generation",
                "text": "Content document text",
            },
        )
        artifact_point = SimpleNamespace(
            id="artifact-point",
            payload={
                "artifact_id": "requirement-1",
                "artifact_version_id": "version-1",
                "index_generation": "artifact-generation",
                "text": "Artifact text",
            },
        )
        store = VectorStore.__new__(VectorStore)
        store.collection_name = "veriq"
        store.client = SimpleNamespace(
            scroll=AsyncMock(
                side_effect=[([content_point], "content-offset"), ([artifact_point], None)]
            )
        )

        items, next_offset = await store.scroll_artifact_version(
            "project-1", "version-1", 1, index_generation="artifact-generation"
        )

        self.assertEqual([item["id"] for item in items], ["artifact-point"])
        self.assertIsNone(next_offset)
        self.assertEqual(store.client.scroll.await_count, 2)

    async def test_qdrant_artifact_id_lookup_excludes_content_document_points(self):
        content_point = SimpleNamespace(
            id="content-point", payload={"document_id": "document-1"}
        )
        artifact_point = SimpleNamespace(id="artifact-point", payload={})
        store = VectorStore.__new__(VectorStore)
        store.collection_name = "veriq"
        store.client = SimpleNamespace(
            scroll=AsyncMock(return_value=([content_point, artifact_point], None))
        )

        point_ids = await store.ids_by_artifact_version("project-1", "version-1")

        self.assertEqual(point_ids, ["artifact-point"])

        store.client.scroll = AsyncMock(
            return_value=(
                [
                    SimpleNamespace(
                        id="content-point",
                        payload={"document_id": "document-1"},
                    ),
                    SimpleNamespace(
                        id="artifact-point",
                        payload={
                            "index_generation": "artifact-generation",
                            "indexed_at": "2026-10-26T00:00:00Z",
                        },
                    ),
                ],
                None,
            )
        )
        legacy_points = await store.list_artifact_version_points(
            "project-1", "version-1"
        )
        self.assertEqual([point["id"] for point in legacy_points], ["artifact-point"])

    async def test_qdrant_artifact_scroll_does_not_return_cursor_for_content_only_tail(self):
        artifact_point = SimpleNamespace(
            id="artifact-point",
            payload={
                "index_generation": "artifact-generation",
                "text": "Artifact text",
            },
        )
        content_point = SimpleNamespace(
            id="content-point",
            payload={"document_id": "document-1", "text": "Content text"},
        )
        store = VectorStore.__new__(VectorStore)
        store.collection_name = "veriq"
        store.client = SimpleNamespace(
            scroll=AsyncMock(
                side_effect=[([artifact_point], "content-tail"), ([content_point], None)]
            )
        )

        items, next_offset = await store.scroll_artifact_version(
            "project-1", "version-1", 1, index_generation="artifact-generation"
        )

        self.assertEqual([item["id"] for item in items], ["artifact-point"])
        self.assertIsNone(next_offset)
        self.assertEqual(store.client.scroll.await_count, 2)

    async def test_bm25_artifact_lookup_and_legacy_scan_exclude_content_document_points(self):
        store = BM25Store()
        store._documents = {
            "content-point": {
                "id": "content-point",
                "text": "Content document text",
                "metadata": {
                    "project_id": "project-1",
                    "artifact_version_id": "version-1",
                    "document_id": "document-1",
                    "index_generation": "content-generation",
                },
            },
            "artifact-point": {
                "id": "artifact-point",
                "text": "Artifact text",
                "metadata": {
                    "project_id": "project-1",
                    "artifact_version_id": "version-1",
                    "index_generation": "artifact-generation",
                },
            },
        }

        point_ids = await store.ids_by_artifact_version("project-1", "version-1")
        points = await store.list_artifact_version_points("project-1", "version-1")

        self.assertEqual(point_ids, ["artifact-point"])
        self.assertEqual([point["id"] for point in points], ["artifact-point"])

    async def test_public_retrieval_metadata_removes_private_keys_recursively(self):
        metadata = {
            "title": "Source title",
            "owner_id": "private-owner",
            "source_spans": [
                {
                    "block_id": "block-1",
                    "image_metadata": {"asset_key": "private/object/key"},
                }
            ],
        }

        result = public_retrieval_metadata(metadata)

        self.assertEqual(result["title"], "Source title")
        self.assertEqual(result["source_spans"][0]["block_id"], "block-1")
        self.assertNotIn("owner_id", result)
        self.assertNotIn("asset_key", result["source_spans"][0]["image_metadata"])

    async def test_lists_only_scoped_chunk_metadata_and_encodes_next_cursor(self):
        point = {
            "id": "point-1",
            "text": "Requirement text",
            "metadata": {
                "project_id": "project-1",
                "artifact_version_id": "version-1",
                "chunk_id": "chunk-1",
                "chunk_index": 0,
                "index_generation": "artifact-generation",
                "page_numbers": [4],
                "extraction_warning_count": 2,
                "extraction_warning_codes": ["OCR_TEXT_REQUIRES_ACCURACY_VALIDATION"],
                "summary_scope": "DISTRIBUTED_CHUNK_SAMPLE",
                "summary_sample_chunk_ids": ["chunk-1", "chunk-9"],
                "summary_sample_page_numbers": [1, 18],
                "summary_sample_char_count": 1500,
                "document_chunk_count": 9,
                "source_spans": [
                    {
                        "block_id": "block-1",
                        "page_no": 4,
                        "table_metadata": {
                            "table_id": "table-1",
                            "data_row_start": 3,
                            "data_row_end": 5,
                            "header_repeated": True,
                            "row_boundary_preserved": True,
                        },
                    },
                    {
                        "block_id": "image-block",
                        "image_metadata": {"asset_key": "private/object/key"},
                    },
                ],
                "owner_id": "private-owner",
                "creator_id": "private-creator",
                "shared_with": ["private-user"],
            },
        }
        with patch.object(
            project_knowledge.project_artifact_generation_repository,
            "get_or_migrate",
            new=AsyncMock(return_value={
                "status": "ACTIVE", "revision": 1, "active_generation": "artifact-generation"
            }),
        ), patch.object(
            project_knowledge.vector_store,
            "scroll_artifact_version",
            new=AsyncMock(return_value=([point], "point-2")),
        ) as scroll:
            result = await project_knowledge.list_project_artifact_chunks(
                "project-1", "version-1", 10
            )

        scroll.assert_awaited_once_with(
            "project-1", "version-1", 10, None, "artifact-generation"
        )
        self.assertEqual(result["items"][0]["point_id"], "point-1")
        self.assertEqual(result["items"][0]["metadata"]["page_numbers"], [4])
        self.assertEqual(result["items"][0]["metadata"]["extraction_warning_count"], 2)
        self.assertEqual(
            result["items"][0]["metadata"]["summary_scope"],
            "DISTRIBUTED_CHUNK_SAMPLE",
        )
        self.assertEqual(
            result["items"][0]["metadata"]["summary_sample_chunk_ids"],
            ["chunk-1", "chunk-9"],
        )
        self.assertEqual(
            result["items"][0]["metadata"]["document_chunk_count"], 9
        )
        self.assertEqual(
            result["items"][0]["metadata"]["extraction_warning_codes"],
            ["OCR_TEXT_REQUIRES_ACCURACY_VALIDATION"],
        )
        self.assertEqual(
            result["items"][0]["metadata"]["source_spans"][0]["table_metadata"]["data_row_start"],
            3,
        )
        self.assertNotIn("owner_id", result["items"][0]["metadata"])
        self.assertNotIn("creator_id", result["items"][0]["metadata"])
        self.assertNotIn("shared_with", result["items"][0]["metadata"])
        self.assertNotIn(
            "asset_key",
            result["items"][0]["metadata"]["source_spans"][1]["image_metadata"],
        )
        cursor = json.loads(
            base64.urlsafe_b64decode(result["next_cursor"]).decode("utf-8")
        )
        self.assertEqual(cursor, {"offset": "point-2", "generation": "artifact-generation"})

    async def test_rejects_invalid_page_size_or_cursor_before_scrolling(self):
        with patch.object(
            project_knowledge.vector_store,
            "scroll_artifact_version",
            new=AsyncMock(),
        ) as scroll:
            with self.assertRaises(HTTPException) as size_error:
                await project_knowledge.list_project_artifact_chunks(
                    "project-1", "version-1", 101
                )
            with self.assertRaises(HTTPException) as cursor_error:
                await project_knowledge.list_project_artifact_chunks(
                    "project-1", "version-1", 10, "not-a-valid-cursor"
                )

        self.assertEqual(size_error.exception.status_code, 422)
        self.assertEqual(cursor_error.exception.status_code, 422)
        scroll.assert_not_awaited()

    async def test_readback_rejects_qdrant_text_that_disagrees_with_chunk_hash(self):
        manifest = {"status": "ACTIVE", "active_generation": "generation-1"}
        point = {
            "id": "point-1",
            "text": "payload text changed",
            "metadata": {
                "project_id": "project-1",
                "artifact_version_id": "version-1",
                "index_generation": "generation-1",
                "chunk_hash": "0" * 64,
            },
        }
        with (
            patch.object(
                project_knowledge.project_artifact_generation_repository,
                "get_or_migrate",
                new=AsyncMock(return_value=manifest),
            ),
            patch.object(
                project_knowledge.vector_store,
                "scroll_artifact_version",
                new=AsyncMock(return_value=([point], None)),
            ),
        ):
            with self.assertRaises(HTTPException) as error:
                await project_knowledge.list_project_artifact_chunks(
                    "project-1", "version-1"
                )

        self.assertEqual(error.exception.status_code, 502)
        self.assertEqual(
            error.exception.detail, {"code": "CHUNK_POINT_PAYLOAD_INVALID"}
        )
