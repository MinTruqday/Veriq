import unittest
from unittest.mock import AsyncMock, patch

from src.schemas.project import ProjectArtifactIndexRequest
from src.services import project_knowledge


class ProjectIndexReplacementTests(unittest.IsolatedAsyncioTestCase):
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

    def request(self, text="Nội dung mới"):
        return ProjectArtifactIndexRequest(artifact_type="requirement_version", artifact_id="req", artifact_version_id="v1", text=text)

    async def test_project_artifact_vectors_are_written_in_bounded_batches(self):
        chunks = [
            {"text": f"Requirement evidence {index}", "metadata": {}}
            for index in range(5)
        ]
        vector_batches = []
        embed_batches = []
        with (
            patch.object(project_knowledge.chunker, "chunk_document", new=AsyncMock(return_value=chunks)),
            patch.object(project_knowledge.embedder, "_batch_size", 2),
            patch.object(project_knowledge.vector_store, "upsert_batch_size", 3),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(side_effect=lambda inputs: embed_batches.append(inputs) or [[1.0] for _ in inputs])),
            patch.object(project_knowledge.vector_store, "ids_by_artifact_version", new=AsyncMock(return_value=[])),
            patch.object(project_knowledge.bm25_store, "ids_by_artifact_version", new=AsyncMock(return_value=[])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock(side_effect=lambda ids, vectors, texts, metadata: vector_batches.append((ids, vectors, texts, metadata)))),
            patch.object(project_knowledge.bm25_store, "upsert", new=AsyncMock()) as lexical_upsert,
            patch.object(project_knowledge.project_artifact_generation_repository, "get_or_migrate", new=AsyncMock(return_value={"status": "ACTIVE", "revision": 1})),
            patch.object(project_knowledge.project_artifact_generation_repository, "publish", new=AsyncMock(return_value=True)),
            patch("src.knowledge.graph.sync.sync_indexed_artifact", new=AsyncMock(return_value={"status": "SYNCED"})),
        ):
            await project_knowledge.index_project_artifact("project", self.request())

        self.assertEqual([len(batch) for batch in embed_batches], [2, 2, 1])
        self.assertEqual([len(batch[0]) for batch in vector_batches], [2, 2, 1])
        self.assertEqual(sum(len(batch[0]) for batch in vector_batches), len(chunks))
        lexical_upsert.assert_awaited_once()
        self.assertEqual(len(lexical_upsert.await_args.args[0]), len(chunks))

    async def test_failed_vector_write_preserves_previous_index(self):
        with (
            patch.object(project_knowledge.chunker, "chunk_document", new=AsyncMock(return_value=[{"text": "new", "metadata": {}}])),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "ids_by_artifact_version", new=AsyncMock(return_value=["old"])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock(side_effect=RuntimeError("unavailable"))),
            patch.object(project_knowledge.vector_store, "delete_ids", new=AsyncMock()) as delete_vector,
            patch.object(project_knowledge.bm25_store, "ids_by_artifact_version", new=AsyncMock(return_value=["old-bm25"])),
            patch.object(project_knowledge.bm25_store, "upsert", new=AsyncMock()) as upsert_lexical,
            patch.object(project_knowledge.bm25_store, "delete_ids", new=AsyncMock()) as delete_lexical,
        ):
            with self.assertRaises(RuntimeError):
                await project_knowledge.index_project_artifact("project", self.request())
        self.assertEqual(delete_vector.await_args.args[0], delete_lexical.await_args.args[0])
        self.assertNotIn("old", delete_vector.await_args.args[0])
        upsert_lexical.assert_not_awaited()

    async def test_failed_lexical_write_preserves_previous_index(self):
        with (
            patch.object(project_knowledge.chunker, "chunk_document", new=AsyncMock(return_value=[{"text": "new", "metadata": {}}])),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "ids_by_artifact_version", new=AsyncMock(return_value=["old"])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "upsert", new=AsyncMock(side_effect=RuntimeError("unavailable"))),
            patch.object(project_knowledge.bm25_store, "ids_by_artifact_version", new=AsyncMock(return_value=["old-bm25"])),
            patch.object(project_knowledge.vector_store, "delete_ids", new=AsyncMock()) as delete_vector,
            patch.object(project_knowledge.bm25_store, "delete_ids", new=AsyncMock()) as delete_lexical,
        ):
            with self.assertRaises(RuntimeError):
                await project_knowledge.index_project_artifact("project", self.request())
        new_ids = delete_vector.await_args.args[0]
        self.assertTrue(new_ids)
        self.assertEqual(new_ids, delete_lexical.await_args.args[0])
        self.assertNotIn("old", new_ids)
        self.assertNotIn("old-bm25", new_ids)

    async def test_long_document_is_not_truncated_and_cleanup_follows_writes(self):
        text = "Nội dung có nguồn. " * 4000 + "PHẦN CUỐI TÀI LIỆU"
        operations = []
        with (
            patch.object(project_knowledge.chunker, "chunk_document", new=AsyncMock(return_value=[{"text": text, "metadata": {}}])) as chunk,
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "ids_by_artifact_version", new=AsyncMock(return_value=["old"])),
            patch.object(project_knowledge.bm25_store, "ids_by_artifact_version", new=AsyncMock(return_value=["old-bm25"])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock(side_effect=lambda *args: operations.append("vector"))),
            patch.object(project_knowledge.bm25_store, "upsert", new=AsyncMock(side_effect=lambda *args: operations.append("lexical"))),
            patch.object(project_knowledge.vector_store, "delete_ids", new=AsyncMock(side_effect=lambda *args: operations.append("delete_vector"))),
            patch.object(project_knowledge.bm25_store, "delete_ids", new=AsyncMock(side_effect=lambda *args: operations.append("delete_lexical"))),
            patch("src.knowledge.graph.sync.sync_indexed_artifact", new=AsyncMock(return_value={"status": "SYNCED"})),
        ):
            result = await project_knowledge.index_project_artifact("project", self.request(text))
        self.assertEqual(chunk.await_args.args[0], text)
        self.assertEqual(set(operations), {"vector", "lexical", "delete_vector", "delete_lexical"})
        self.assertEqual(result["status"], "indexed")

    async def test_failed_stale_generation_cleanup_is_reported_as_degraded(self):
        with (
            patch.object(project_knowledge.chunker, "chunk_document", new=AsyncMock(return_value=[{"text": "new", "metadata": {}}])),
            patch.object(project_knowledge.embedder, "embed_batch", new=AsyncMock(return_value=[[1.0]])),
            patch.object(project_knowledge.vector_store, "ids_by_artifact_version", new=AsyncMock(return_value=["old-vector"])),
            patch.object(project_knowledge.bm25_store, "ids_by_artifact_version", new=AsyncMock(return_value=["old-bm25"])),
            patch.object(project_knowledge.vector_store, "upsert", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "upsert", new=AsyncMock()),
            patch.object(project_knowledge.vector_store, "delete_ids", new=AsyncMock()),
            patch.object(project_knowledge.bm25_store, "delete_ids", new=AsyncMock(side_effect=RuntimeError("cleanup unavailable"))),
            patch("src.knowledge.graph.sync.sync_indexed_artifact", new=AsyncMock(return_value={"status": "SYNCED"})),
        ):
            result = await project_knowledge.index_project_artifact("project", self.request())

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["index_cleanup_pending"], ["bm25"])


if __name__ == "__main__":
    unittest.main()
