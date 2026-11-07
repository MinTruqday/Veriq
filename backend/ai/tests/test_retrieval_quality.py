import unittest
from unittest.mock import AsyncMock, patch

from src.services.retrieval import RetrievalService


def result(point_id):
    return {
        "id": point_id,
        "text": point_id,
        "score": 1.0,
        "metadata": {"visibility": "public"},
    }


class RetrievalQualityTests(unittest.IsolatedAsyncioTestCase):
    async def test_expands_candidate_window_when_stale_candidates_are_filtered(self):
        service = RetrievalService()
        service._reranker_ready = False
        candidates = {
            2: [result("stale"), result("valid-1")],
            4: [result("stale"), result("valid-1"), result("valid-2")],
        }

        async def dense_query(*, limit, **kwargs):
            return candidates[limit]

        async def filter_active(documents):
            return [document for document in documents if document["id"] != "stale"]

        with (
            patch("src.services.retrieval.vector_store.query", new=AsyncMock(side_effect=dense_query)) as dense,
            patch("src.services.retrieval.bm25_store.search", new=AsyncMock(return_value=[])),
            patch.object(service, "_filter_active_artifact_generations", side_effect=filter_active),
            patch.object(
                service,
                "_filter_currently_accessible_sources",
                new=AsyncMock(side_effect=lambda documents, *_: documents),
            ),
        ):
            found = await service.retrieve(
                "query",
                k=2,
                query_vector_override=[0.0],
                is_admin=True,
            )

        self.assertEqual([document["id"] for document in found], ["valid-1", "valid-2"])
        self.assertEqual(
            [call.kwargs["limit"] for call in dense.await_args_list],
            [2, 4],
        )

    async def test_reranked_candidates_are_revalidated_before_truncation(self):
        service = RetrievalService()
        service._reranker_ready = True
        initial = [result("revoked"), result("valid")]
        generation_check_count = 0

        async def generation_filter(documents):
            nonlocal generation_check_count
            generation_check_count += 1
            if generation_check_count == 1:
                return documents
            return [document for document in documents if document["id"] != "revoked"]

        async def accessibility_filter(documents, *_):
            return documents

        with (
            patch("src.services.retrieval.vector_store.query", new=AsyncMock(return_value=initial)),
            patch("src.services.retrieval.bm25_store.search", new=AsyncMock(return_value=[])),
            patch.object(service, "_filter_active_artifact_generations", side_effect=generation_filter),
            patch.object(
                service,
                "_filter_currently_accessible_sources",
                new=AsyncMock(side_effect=accessibility_filter),
            ),
            patch("src.services.retrieval.auxiliary_client.rerank", new=AsyncMock(return_value=[0.9, 0.8])),
        ):
            found = await service.retrieve(
                "query",
                k=1,
                query_vector_override=[0.0],
                is_admin=True,
            )

        self.assertEqual([document["id"] for document in found], ["valid"])

    async def test_rejects_invalid_result_count(self):
        service = RetrievalService()
        for invalid in (0, -1, 101, True, 1.5):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                await service.retrieve("query", k=invalid, query_vector_override=[0.0])


if __name__ == "__main__":
    unittest.main()
