import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.schemas.project import ProjectArtifactIndexRequest
from src.services import project_knowledge
from src.store.bm25 import BM25Store
from src.store.vector import VectorStore


class ProjectIndexReplacementTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def chunk_stream(chunks, calls=None):
        async def iterate(*args, **kwargs):
            if calls is not None:
                calls.append((args, kwargs))
            for chunk in chunks:
                yield chunk

        return iterate

    def setUp(self):
        manifest = {"status": "ACTIVE", "revision": 1, "active_generation": "old-generation"}
        self.manifest_read = patch.object(
            project_knowledge.project_artifact_generation_repository,
            "get_or_migrate",
            new=AsyncMock(return_value=manifest),
        )
        self.manifest_publish = patch.object(
            project_knowledge.project_artifact_generation_repository,
            "publish",
            new=AsyncMock(return_value=True),
        )
        self.manifest_read.start()
        self.manifest_publish.start()
        self.addCleanup(self.manifest_read.stop)
        self.addCleanup(self.manifest_publish.stop)

    def request(self, text="Nội dung mới", source_structure=None):
        return ProjectArtifactIndexRequest(
            artifact_type="requirement_version",
            artifact_id="req",
            artifact_version_id="v1",
            text=text,
            source_structure=source_structure or [],
        )

    async def test_project_artifact_vectors_are_written_in_bounded_batches(self):
        chunks = [
            {
                "text": f"Requirement evidence {index}",
                "metadata": (
                    {"project_id": "other", "artifact_id": "other", "index_generation": "other"}
                    if index == 0
                    else {}
                ),
            }
            for index in range(5)
        ]
        vector_batches = []
        embed_batches = []
        lexical_batches = []
        with (
            patch.object(project_knowledge.chunker, "iter_chunk_document", new=self.chunk_stream(chunks)),
            patch.object(project_knowledge.embedder, "_batch_size", 2),
            patch.object(project_knowledge.vector_store, "upsert_batch_size", 3),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(side_effect=lambda inputs: embed_batches.append(inputs) or [[1.0] for _ in inputs])),
            patch.object(project_knowledge.vector_store, "ids_by_artifact_version", new=AsyncMock(side_effect=AssertionError("full Qdrant point enumeration is not allowed"))) as vector_id_scan,
            patch.object(project_knowledge.bm25_store, "ids_by_artifact_version", new=AsyncMock(side_effect=AssertionError("full BM25 point enumeration is not allowed"))) as bm25_id_scan,
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock(side_effect=lambda ids, vectors, texts, metadata: vector_batches.append((ids, vectors, texts, metadata)))),
            patch.object(
                project_knowledge.bm25_store,
                "stage_upsert",
                new=AsyncMock(side_effect=lambda documents, stage_id: lexical_batches.append((documents, stage_id))),
            ) as lexical_stage,
            patch.object(project_knowledge.bm25_store, "publish_staged", new=AsyncMock()) as lexical_publish,
            patch.object(project_knowledge.vector_store, "delete_stale_artifact_generations", new=AsyncMock()) as vector_stale,
            patch.object(project_knowledge.bm25_store, "delete_stale_artifact_generations", new=AsyncMock()) as bm25_stale,
            patch.object(project_knowledge.project_artifact_generation_repository, "get_or_migrate", new=AsyncMock(return_value={"status": "ACTIVE", "revision": 1})),
            patch.object(project_knowledge.project_artifact_generation_repository, "publish", new=AsyncMock(return_value=True)),
            patch("src.knowledge.graph.sync.sync_indexed_artifact", new=AsyncMock(return_value={"status": "SYNCED"})),
        ):
            await project_knowledge.index_project_artifact("project", self.request())

        self.assertEqual([len(batch) for batch in embed_batches], [2, 2, 1])
        self.assertEqual([len(batch[0]) for batch in vector_batches], [2, 2, 1])
        self.assertEqual(sum(len(batch[0]) for batch in vector_batches), len(chunks))
        point_metadata = [metadata for batch in vector_batches for metadata in batch[3]]
        self.assertTrue(all(metadata["project_id"] == "project" for metadata in point_metadata))
        self.assertTrue(all(metadata["artifact_id"] == "req" for metadata in point_metadata))
        self.assertEqual(len({metadata["index_generation"] for metadata in point_metadata}), 1)
        self.assertEqual([len(batch[0]) for batch in lexical_batches], [2, 2, 1])
        self.assertEqual(len({batch[1] for batch in lexical_batches}), 1)
        lexical_publish.assert_awaited_once_with(lexical_batches[0][1])
        self.assertEqual(lexical_stage.await_count, 3)
        self.assertEqual(vector_stale.await_args.args, bm25_stale.await_args.args)
        self.assertEqual(vector_stale.await_args.args[1:4], ("requirement_version", "req", "v1"))
        vector_id_scan.assert_not_awaited()
        bm25_id_scan.assert_not_awaited()

    async def test_failed_vector_write_preserves_previous_index(self):
        with (
            patch.object(project_knowledge.chunker, "iter_chunk_document", new=self.chunk_stream([{"text": "new", "metadata": {}}])),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock(side_effect=RuntimeError("unavailable"))),
            patch.object(project_knowledge.vector_store, "delete_artifact_generation", new=AsyncMock()) as delete_vector,
            patch.object(project_knowledge.bm25_store, "stage_upsert", new=AsyncMock()) as upsert_lexical,
            patch.object(project_knowledge.bm25_store, "discard_staged", new=AsyncMock()) as discard_staged,
            patch.object(project_knowledge.bm25_store, "delete_artifact_generation", new=AsyncMock()) as delete_lexical,
        ):
            with self.assertRaises(RuntimeError):
                await project_knowledge.index_project_artifact("project", self.request())
        self.assertEqual(delete_vector.await_args.args, delete_lexical.await_args.args)
        self.assertEqual(delete_vector.await_args.args[1:4], ("requirement_version", "req", "v1"))
        upsert_lexical.assert_not_awaited()
        discard_staged.assert_awaited_once()

    async def test_failed_lexical_write_preserves_previous_index(self):
        with (
            patch.object(project_knowledge.chunker, "iter_chunk_document", new=self.chunk_stream([{"text": "new", "metadata": {}}])),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "stage_upsert", new=AsyncMock(side_effect=RuntimeError("unavailable"))),
            patch.object(project_knowledge.bm25_store, "discard_staged", new=AsyncMock()) as discard_staged,
            patch.object(project_knowledge.vector_store, "delete_artifact_generation", new=AsyncMock()) as delete_vector,
            patch.object(project_knowledge.bm25_store, "delete_artifact_generation", new=AsyncMock()) as delete_lexical,
        ):
            with self.assertRaises(RuntimeError):
                await project_knowledge.index_project_artifact("project", self.request())
        self.assertEqual(delete_vector.await_args.args, delete_lexical.await_args.args)
        self.assertEqual(delete_vector.await_args.args[1:4], ("requirement_version", "req", "v1"))
        discard_staged.assert_awaited_once()

    async def test_failed_lexical_publish_rolls_back_new_generation(self):
        with (
            patch.object(project_knowledge.chunker, "iter_chunk_document", new=self.chunk_stream([{"text": "new", "metadata": {}}])),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "stage_upsert", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "publish_staged", new=AsyncMock(side_effect=RuntimeError("publish unavailable"))),
            patch.object(project_knowledge.bm25_store, "discard_staged", new=AsyncMock()) as discard_staged,
            patch.object(project_knowledge.vector_store, "delete_artifact_generation", new=AsyncMock()) as delete_vector,
            patch.object(project_knowledge.bm25_store, "delete_artifact_generation", new=AsyncMock()) as delete_lexical,
        ):
            with self.assertRaises(RuntimeError):
                await project_knowledge.index_project_artifact("project", self.request())

        self.assertEqual(delete_vector.await_args.args, delete_lexical.await_args.args)
        self.assertEqual(delete_vector.await_args.args[1:4], ("requirement_version", "req", "v1"))
        self.assertEqual(delete_lexical.await_args.args[1:4], ("requirement_version", "req", "v1"))
        discard_staged.assert_awaited_once()

    async def test_cancellation_during_embedding_removes_partial_generation_and_stage(self):
        chunks = [
            {"text": "first new chunk", "metadata": {}},
            {"text": "second new chunk", "metadata": {}},
        ]
        embed = AsyncMock(side_effect=[[[1.0]], asyncio.CancelledError()])
        with (
            patch.object(project_knowledge.chunker, "iter_chunk_document", new=self.chunk_stream(chunks)),
            patch.object(project_knowledge.embedder, "_batch_size", 1),
            patch.object(project_knowledge.vector_store, "upsert_batch_size", 1),
            patch.object(project_knowledge.embedder, "embed_batch", new=embed),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock()) as vector_upsert,
            patch.object(project_knowledge.bm25_store, "stage_upsert", new=AsyncMock()) as lexical_stage,
            patch.object(project_knowledge.bm25_store, "publish_staged", new=AsyncMock()) as lexical_publish,
            patch.object(project_knowledge.vector_store, "delete_artifact_generation", new=AsyncMock()) as delete_vector,
            patch.object(project_knowledge.bm25_store, "delete_artifact_generation", new=AsyncMock()) as delete_lexical,
            patch.object(project_knowledge.bm25_store, "discard_staged", new=AsyncMock()) as discard_staged,
        ):
            with self.assertRaises(asyncio.CancelledError):
                await project_knowledge.index_project_artifact("project", self.request())

        vector_upsert.assert_awaited_once()
        lexical_stage.assert_awaited_once()
        lexical_publish.assert_not_awaited()
        self.assertEqual(delete_vector.await_args.args, delete_lexical.await_args.args)
        self.assertEqual(delete_vector.await_args.args[1:4], ("requirement_version", "req", "v1"))
        discard_staged.assert_awaited_once()

    async def test_long_document_is_not_truncated_and_cleanup_follows_writes(self):
        text = "Nội dung có nguồn. " * 4000 + "PHẦN CUỐI TÀI LIỆU"
        req = self.request(
            text,
            source_structure=[{"block_id": "source-1", "type": "paragraph", "text": text}],
        )
        operations = []
        with (
            patch.object(project_knowledge.chunker, "iter_chunk_document", new=self.chunk_stream([{"text": text, "metadata": {}}], calls := [])),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock(side_effect=lambda *args: operations.append("vector"))),
            patch.object(project_knowledge.bm25_store, "stage_upsert", new=AsyncMock(side_effect=lambda *args, **kwargs: operations.append("lexical-stage"))),
            patch.object(project_knowledge.bm25_store, "publish_staged", new=AsyncMock(side_effect=lambda *args: operations.append("lexical-publish"))),
            patch.object(project_knowledge.vector_store, "delete_stale_artifact_generations", new=AsyncMock(side_effect=lambda *args: operations.append("delete_vector"))),
            patch.object(project_knowledge.bm25_store, "delete_stale_artifact_generations", new=AsyncMock(side_effect=lambda *args: operations.append("delete_lexical"))),
            patch("src.knowledge.graph.sync.sync_indexed_artifact", new=AsyncMock(return_value={"status": "SYNCED"})),
        ):
            result = await project_knowledge.index_project_artifact("project", req)
        self.assertEqual(calls[0][0][0], text)
        self.assertIs(calls[0][1]["structure"], req.source_structure)
        self.assertEqual(set(operations), {"vector", "lexical-stage", "lexical-publish", "delete_vector", "delete_lexical"})
        self.assertEqual(result["status"], "indexed")

    async def test_semantic_chunk_stream_failure_rolls_back_before_structural_fallback(self):
        events = []

        async def chunks(*args, semantic=True, **kwargs):
            if semantic:
                yield {"text": "semantic partial", "metadata": {}}
                raise RuntimeError("semantic provider unavailable")
            yield {"text": "structural result", "metadata": {}}

        with (
            patch.object(project_knowledge.chunker, "iter_chunk_document", new=chunks),
            patch.object(project_knowledge.embedder, "_batch_size", 1),
            patch.object(project_knowledge.vector_store, "upsert_batch_size", 1),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(
                project_knowledge.vector_store,
                "upsert",
                new=AsyncMock(side_effect=lambda ids, vectors, texts, metadata: events.append(("upsert", texts[0]))),
            ),
            patch.object(
                project_knowledge.vector_store,
                "delete_artifact_generation",
                new=AsyncMock(side_effect=lambda *args: events.append(("rollback", args[-1]))),
            ),
            patch.object(
                project_knowledge.vector_store,
                "delete_stale_artifact_generations",
                new=AsyncMock(),
            ),
            patch.object(
                project_knowledge.bm25_store,
                "delete_stale_artifact_generations",
                new=AsyncMock(),
            ),
            patch.object(project_knowledge.bm25_store, "stage_upsert", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "discard_staged", new=AsyncMock()) as discard_staged,
            patch.object(project_knowledge.bm25_store, "publish_staged", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "delete_artifact_generation", new=AsyncMock()),
            patch("src.knowledge.graph.sync.sync_indexed_artifact", new=AsyncMock(return_value={"status": "SYNCED"})),
        ):
            result = await project_knowledge.index_project_artifact("project", self.request())

        self.assertEqual(result["status"], "indexed")
        self.assertEqual([event[0] for event in events], ["upsert", "rollback", "upsert"])
        self.assertEqual(events[0][1], "semantic partial")
        self.assertTrue(events[1][1])
        self.assertEqual(events[2][1], "structural result")
        discard_staged.assert_awaited_once()
        self.assertEqual(result["chunks_count"], 1)

    async def test_failed_stale_generation_cleanup_is_reported_as_degraded(self):
        with (
            patch.object(project_knowledge.chunker, "iter_chunk_document", new=self.chunk_stream([{"text": "new", "metadata": {}}])),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "stage_upsert", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "publish_staged", new=AsyncMock()),
            patch.object(project_knowledge.vector_store, "delete_stale_artifact_generations", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "delete_stale_artifact_generations", new=AsyncMock(side_effect=RuntimeError("cleanup unavailable"))),
            patch("src.knowledge.graph.sync.sync_indexed_artifact", new=AsyncMock(return_value={"status": "SYNCED"})),
        ):
            result = await project_knowledge.index_project_artifact("project", self.request())

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["index_cleanup_pending"], ["bm25"])

    async def test_artifact_removal_uses_scoped_deletion_without_enumerating_ids(self):
        manifest = {"_id": "manifest", "revision": 2, "status": "DELETING"}
        with (
            patch.object(
                project_knowledge.project_artifact_generation_repository,
                "begin_removal",
                new=AsyncMock(return_value=manifest),
            ),
            patch.object(
                project_knowledge.project_artifact_generation_repository,
                "removal_is_current",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                project_knowledge.project_artifact_generation_repository,
                "finish_removal",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                project_knowledge.vector_store,
                "ids_by_artifact_version",
                new=AsyncMock(side_effect=AssertionError("artifact removal must not enumerate Qdrant IDs")),
            ),
            patch.object(
                project_knowledge.bm25_store,
                "ids_by_artifact_version",
                new=AsyncMock(side_effect=AssertionError("artifact removal must not enumerate BM25 IDs")),
            ),
            patch.object(
                project_knowledge.vector_store,
                "delete_project_artifact_version",
                new=AsyncMock(),
            ) as vector_delete,
            patch.object(
                project_knowledge.bm25_store,
                "delete_project_artifact_version",
                new=AsyncMock(),
            ) as bm25_delete,
            patch(
                "src.knowledge.graph.repository.graph_repository.delete_artifact_version",
                new=AsyncMock(return_value=[{"removed": 2}]),
            ),
        ):
            result = await project_knowledge.remove_project_artifact("project", "v1")

        self.assertEqual(result["status"], "removed")
        self.assertEqual(vector_delete.await_args.args, ("project", "v1"))
        self.assertEqual(bm25_delete.await_args.args, ("project", "v1"))

    async def test_bm25_project_artifact_removal_includes_testing_documents(self):
        store = BM25Store()
        store._documents = {
            "testing-doc": {
                "text": "requirement text",
                "metadata": {
                    "project_id": "project",
                    "artifact_type": "requirement_document",
                    "artifact_id": "doc",
                    "artifact_version_id": "doc",
                    "document_id": "doc",
                },
            },
            "content-doc": {
                "text": "content document text",
                "metadata": {
                    "project_id": "project",
                    "artifact_type": "source_document",
                    "artifact_id": "source",
                    "artifact_version_id": "doc",
                    "document_id": "content-doc",
                },
            },
            "other-project": {
                "text": "other project text",
                "metadata": {
                    "project_id": "other",
                    "artifact_type": "requirement_document",
                    "artifact_id": "other-doc",
                    "artifact_version_id": "doc",
                    "document_id": "other-doc",
                },
            },
        }

        await store.delete_project_artifact_version("project", "doc")

        self.assertEqual(set(store._documents), {"other-project"})

    async def test_bm25_requirement_document_is_in_active_snapshot_and_search(self):
        store = BM25Store()
        await store.upsert(
            [
                {
                    "id": "requirement-point",
                    "text": "AC-1 login accepts valid email and password",
                    "metadata": {
                        "project_id": "project",
                        "artifact_type": "requirement_document",
                        "artifact_id": "doc",
                        "artifact_version_id": "doc",
                        "document_id": "doc",
                        "index_generation": "generation-1",
                        "visibility": "private",
                        "owner_id": "owner",
                    },
                }
            ]
        )

        snapshot = await store.artifact_version_summary_snapshot(
            "project", "doc", "LEGACY"
        )
        owner_hits = await store.search(
            "login valid password",
            requester_id="owner",
            metadata_filters={
                "project_id": "project",
                "artifact_type": ["requirement_document"],
                "index_generation": "generation-1",
            },
        )
        denied_hits = await store.search(
            "login valid password",
            requester_id="tester",
            metadata_filters={
                "project_id": "project",
                "artifact_type": ["requirement_document"],
                "index_generation": "generation-1",
            },
        )

        self.assertIn("generation-1", snapshot.generation_counts)
        self.assertTrue(snapshot.contains("requirement-point", "generation-1"))
        self.assertEqual([item["id"] for item in owner_hits], ["requirement-point"])
        self.assertEqual(denied_hits, [])

    async def test_qdrant_requirement_document_is_in_active_summaries_and_chunks(self):
        store = object.__new__(VectorStore)
        store.collection_name = "veriq"
        point = SimpleNamespace(
            id="requirement-point",
            payload={
                "document_id": "doc",
                "artifact_type": "requirement_document",
                "index_generation": "generation-1",
                "indexed_at": "2026-10-27T00:00:00Z",
                "text": "AC-1 login",
                "project_id": "project",
                "artifact_version_id": "doc",
            },
        )
        store.client = AsyncMock()
        store.client.scroll.return_value = ([point], None)

        summaries = [
            item
            async for item in store.iter_artifact_version_summaries("project", "doc")
        ]
        chunks, cursor = await store.scroll_artifact_version(
            "project", "doc", limit=10, index_generation="generation-1"
        )

        self.assertEqual([item["id"] for item in summaries], ["requirement-point"])
        self.assertEqual([item["id"] for item in chunks], ["requirement-point"])
        self.assertIsNone(cursor)

    async def test_qdrant_requirement_document_removal_includes_document_id(self):
        store = object.__new__(VectorStore)
        store.collection_name = "veriq"
        store.client = AsyncMock()

        await store.delete_project_artifact_version("project", "doc")

        calls = store.client.delete.await_args_list
        self.assertEqual(len(calls), 2)
        requirement_filter = calls[0].kwargs["points_selector"]
        generic_filter = calls[1].kwargs["points_selector"]
        self.assertIn("value='requirement_document'", str(requirement_filter))
        self.assertNotIn("document_id", str(requirement_filter))
        self.assertIn("document_id", str(generic_filter))

    async def test_qdrant_scoped_generation_deletion_allows_requirement_document_id(self):
        store = object.__new__(VectorStore)
        store.collection_name = "veriq"
        store.client = AsyncMock()

        await store.delete_artifact_generation(
            "project", "requirement_document", "doc", "doc", "generation"
        )

        query_filter = store.client.delete.await_args.kwargs["points_selector"]
        self.assertNotIn("document_id", str(query_filter.must))


if __name__ == "__main__":
    unittest.main()
