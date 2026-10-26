import unittest
from unittest.mock import AsyncMock, patch

from src.clients.content import ContentClient
from src.services.retrieval import RetrievalService, RetrievalUnavailableError


class RetrievalLiveAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_retrieval_drops_documents_whose_live_access_was_revoked(self):
        service = RetrievalService()
        documents = [
            {
                "id": "chunk-allowed",
                "text": "Allowed source content",
                "metadata": {"document_id": "doc-allowed"},
                "score": 0.9,
            },
            {
                "id": "chunk-revoked",
                "text": "Revoked source content",
                "metadata": {"document_id": "doc-revoked"},
                "score": 0.8,
            },
        ]
        with (
            patch(
                "src.services.retrieval.project_artifact_generation_repository.filter_active",
                new=AsyncMock(side_effect=lambda documents: documents),
            ),
            patch("src.services.retrieval.embedder.embed_query", new=AsyncMock(return_value=[0.1])),
            patch("src.services.retrieval.vector_store.query", new=AsyncMock(return_value=documents)),
            patch("src.services.retrieval.bm25_store.search", new=AsyncMock(return_value=[])),
            patch(
                "src.services.retrieval.ContentClient.active_index_generations_many",
                new=AsyncMock(return_value={"doc-allowed": None}),
            ) as authorize,
        ):
            result = await service.retrieve("source content", requester_id="user-1")

        self.assertEqual([item["id"] for item in result], ["chunk-allowed"])
        authorize.assert_awaited_once_with(
            ["doc-allowed", "doc-revoked"], "user-1", False
        )

    async def test_retrieval_fails_closed_if_live_access_cannot_be_verified(self):
        service = RetrievalService()
        with (
            patch(
                "src.services.retrieval.project_artifact_generation_repository.filter_active",
                new=AsyncMock(side_effect=lambda documents: documents),
            ),
            patch("src.services.retrieval.embedder.embed_query", new=AsyncMock(return_value=[0.1])),
            patch(
                "src.services.retrieval.vector_store.query",
                new=AsyncMock(
                    return_value=[
                        {
                            "id": "chunk-1",
                            "text": "Private indexed content",
                            "metadata": {"document_id": "doc-1"},
                            "score": 0.9,
                        }
                    ]
                ),
            ),
            patch("src.services.retrieval.bm25_store.search", new=AsyncMock(return_value=[])),
            patch(
                "src.services.retrieval.ContentClient.active_index_generations_many",
                new=AsyncMock(side_effect=RuntimeError("content service unavailable")),
            ),
        ):
            with self.assertRaises(RetrievalUnavailableError) as raised:
                await service.retrieve("private indexed content", requester_id="user-1")

        self.assertEqual(str(raised.exception), "document_access_verification_unavailable")

    async def test_retrieval_keeps_only_the_active_document_index_generation(self):
        documents = [
            {
                "id": "old-point",
                "text": "old indexed text",
                "metadata": {
                    "document_id": "doc-1",
                    "index_generation": "generation-old",
                },
            },
            {
                "id": "new-point",
                "text": "new indexed text",
                "metadata": {
                    "document_id": "doc-1",
                    "index_generation": "generation-new",
                },
            },
        ]

        with patch.object(
            ContentClient,
            "active_index_generations_many",
            new=AsyncMock(return_value={"doc-1": "generation-new"}),
        ):
            result = await RetrievalService._filter_currently_accessible_sources(
                documents, "user-1", False
            )

        self.assertEqual([item["id"] for item in result], ["new-point"])

    async def test_inactive_generation_does_not_affect_dense_sparse_ranking(self):
        service = RetrievalService()
        def result(point_id, document_id, generation):
            return {
                "id": point_id,
                "text": point_id,
                "metadata": {
                    "document_id": document_id,
                    "index_generation": generation,
                },
            }

        active_generation = "generation-current"
        first = result("first", "doc-first", active_generation)
        stale = result("stale", "doc-reindexed", "generation-old")
        second = result("second", "doc-second", active_generation)
        third = result("third", "doc-third", active_generation)

        async def keep_artifact_generations(documents):
            return documents

        with (
            patch("src.services.retrieval.embedder.embed_query", new=AsyncMock(return_value=[0.1])),
            patch(
                "src.services.retrieval.vector_store.query",
                new=AsyncMock(return_value=[first, stale, second]),
            ),
            patch(
                "src.services.retrieval.bm25_store.search",
                new=AsyncMock(return_value=[second, third, first]),
            ),
            patch.object(
                service,
                "_filter_active_artifact_generations",
                new=AsyncMock(side_effect=keep_artifact_generations),
            ),
            patch(
                "src.services.retrieval.ContentClient.active_index_generations_many",
                new=AsyncMock(
                    return_value={
                        "doc-first": active_generation,
                        "doc-reindexed": active_generation,
                        "doc-second": active_generation,
                        "doc-third": active_generation,
                    }
                ),
            ),
        ):
            result = await service.retrieve(
                "query", k=1, requester_id="user-1"
            )

        self.assertEqual([item["id"] for item in result], ["second"])

    async def test_legacy_document_results_do_not_mix_observed_generations(self):
        documents = [
            {
                "id": "legacy-old-point",
                "text": "old indexed text",
                "metadata": {
                    "document_id": "doc-legacy",
                    "index_generation": "generation-old",
                    "indexed_at": "2026-10-25T10:00:00+00:00",
                },
            },
            {
                "id": "legacy-new-point",
                "text": "new indexed text",
                "metadata": {
                    "document_id": "doc-legacy",
                    "index_generation": "generation-new",
                    "indexed_at": "2026-10-26T10:00:00+00:00",
                },
            },
        ]

        with patch.object(
            ContentClient,
            "active_index_generations_many",
            new=AsyncMock(return_value={"doc-legacy": None}),
        ):
            result = await RetrievalService._filter_currently_accessible_sources(
                documents, "user-1", False
            )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
