import unittest
from unittest.mock import AsyncMock, patch

from src.repositories.project_artifact_generation import ProjectArtifactGenerationRepository
from src.store.bm25 import BM25ArtifactVersionSummarySnapshot, bm25_store
from src.store.vector import vector_store


class ProjectArtifactGenerationSummaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_manifest_compares_streamed_ids_without_full_point_lists(self):
        vector_rows = [
            {
                "id": "point-1",
                "index_generation": "generation-1",
                "indexed_at": "2026-10-26T10:00:00+00:00",
            },
            {
                "id": "point-2",
                "index_generation": "generation-1",
                "indexed_at": "2026-10-26T10:01:00+00:00",
            },
            {
                "id": "old-point",
                "index_generation": "generation-old",
                "indexed_at": "2026-10-25T10:00:00+00:00",
            },
        ]
        bm25_rows = [
            {"id": "point-2", "index_generation": "generation-1"},
            {"id": "point-1", "index_generation": "generation-1"},
            {"id": "orphan-point", "index_generation": "generation-old"},
        ]

        async def vector_stream(_project_id, _version_id):
            for row in vector_rows:
                yield row

        bm25_snapshot = BM25ArtifactVersionSummarySnapshot(
            {
                row["id"]: {
                    "metadata": {
                        "project_id": "project-1",
                        "artifact_version_id": "version-1",
                        "index_generation": row["index_generation"],
                    }
                }
                for row in bm25_rows
            },
            "project-1",
            "version-1",
            "LEGACY",
        )

        with (
            patch.object(vector_store, "iter_artifact_version_summaries", new=vector_stream),
            patch.object(
                bm25_store,
                "artifact_version_summary_snapshot",
                new=AsyncMock(return_value=bm25_snapshot),
            ) as bm25_snapshot_read,
            patch.object(
                vector_store,
                "list_artifact_version_points",
                new=AsyncMock(side_effect=AssertionError("full vector listing used")),
            ) as vector_list,
            patch.object(
                bm25_store,
                "list_artifact_version_points",
                new=AsyncMock(side_effect=AssertionError("full BM25 listing used")),
            ) as bm25_list,
        ):
            manifest = await ProjectArtifactGenerationRepository()._legacy_manifest(
                "project-1", "version-1"
            )

        self.assertEqual(manifest["status"], "ACTIVE")
        self.assertEqual(manifest["active_generation"], "generation-1")
        self.assertEqual(manifest["point_count"], 2)
        bm25_snapshot_read.assert_awaited_once_with(
            "project-1", "version-1", "LEGACY"
        )
        vector_list.assert_not_awaited()
        bm25_list.assert_not_awaited()

    async def test_legacy_manifest_hides_generation_when_streamed_ids_disagree(self):
        async def vector_stream(_project_id, _version_id):
            yield {"id": "vector-point", "index_generation": "generation-1"}

        bm25_snapshot = BM25ArtifactVersionSummarySnapshot(
            {
                "bm25-point": {
                    "metadata": {
                        "project_id": "project-1",
                        "artifact_version_id": "version-1",
                        "index_generation": "generation-1",
                    }
                }
            },
            "project-1",
            "version-1",
            "LEGACY",
        )

        with (
            patch.object(vector_store, "iter_artifact_version_summaries", new=vector_stream),
            patch.object(
                bm25_store,
                "artifact_version_summary_snapshot",
                new=AsyncMock(return_value=bm25_snapshot),
            ),
        ):
            manifest = await ProjectArtifactGenerationRepository()._legacy_manifest(
                "project-1", "version-1"
            )

        self.assertEqual(manifest["status"], "REMOVED")
        self.assertIsNone(manifest["active_generation"])
        self.assertEqual(manifest["point_count"], 0)
