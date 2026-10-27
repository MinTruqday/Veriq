import unittest
from unittest.mock import AsyncMock, patch

from src.clients.content import ContentClient
from src.core.infrastructure.configuration import settings
from src.repositories.project_artifact_generation import project_artifact_generation_repository
from src.services.retrieval import RetrievalService, RetrievalUnavailableError


def content_document_metadata(document_id, index_generation=None):
    metadata = {
        "artifact_type": "source_document",
        "document_index_contract_version": settings.DOCUMENT_INDEX_CONTRACT_VERSION,
        "document_id": document_id,
    }
    if index_generation:
        metadata["index_generation"] = index_generation
    return metadata


class RetrievalLiveAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_testing_document_generation_filter_keeps_only_active_generation(self):
        documents = [
            {
                "id": "stale-point",
                "metadata": {
                    "artifact_type": "requirement_document",
                    "document_id": "req-doc-1",
                    "project_id": "project-1",
                    "artifact_version_id": "req-doc-1",
                    "index_generation": "old-generation",
                },
            },
            {
                "id": "active-point",
                "metadata": {
                    "artifact_type": "requirement_document",
                    "document_id": "req-doc-1",
                    "project_id": "project-1",
                    "artifact_version_id": "req-doc-1",
                    "index_generation": "active-generation",
                },
            },
        ]
        with patch.object(
            project_artifact_generation_repository,
            "active_generations",
            new=AsyncMock(return_value={("project-1", "req-doc-1"): "active-generation"}),
        ) as active_generations:
            result = await project_artifact_generation_repository.filter_active(documents)

        self.assertEqual([item["id"] for item in result], ["active-point"])
        active_generations.assert_awaited_once_with(documents)

    async def test_malformed_reranker_scores_fall_back_without_dropping_results(self):
        service = RetrievalService()
        service._reranker_ready = True
        documents = [
            {
                "id": f"chunk-{index}",
                "text": f"content-{index}",
                "metadata": content_document_metadata(f"doc-{index}"),
                "score": 1 - index * 0.1,
            }
            for index in range(2)
        ]

        with (
            patch("src.services.retrieval.embedder.embed_query", new=AsyncMock(return_value=[0.1])),
            patch("src.services.retrieval.vector_store.query", new=AsyncMock(return_value=documents)),
            patch("src.services.retrieval.bm25_store.search", new=AsyncMock(return_value=[])),
            patch.object(
                service,
                "_filter_active_artifact_generations",
                new=AsyncMock(side_effect=lambda values: values),
            ),
            patch(
                "src.services.retrieval.ContentClient.active_index_generations_many",
                new=AsyncMock(return_value={"doc-0": None, "doc-1": None}),
            ),
            patch(
                "src.services.retrieval.auxiliary_client.rerank",
                new=AsyncMock(return_value=[0.9]),
            ),
        ):
            results = await service.retrieve("query", k=2, requester_id="user-1")

        self.assertEqual([item["id"] for item in results], ["chunk-0", "chunk-1"])

    async def test_retrieval_drops_documents_whose_live_access_was_revoked(self):
        service = RetrievalService()
        documents = [
            {
                "id": "chunk-allowed",
                "text": "Allowed source content",
                "metadata": content_document_metadata("doc-allowed"),
                "score": 0.9,
            },
            {
                "id": "chunk-revoked",
                "text": "Revoked source content",
                "metadata": content_document_metadata("doc-revoked"),
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

    async def test_cross_document_retrieval_rechecks_access_after_merging_results(self):
        service = RetrievalService()
        retrieved = [
            [
                {
                    "id": "revoked-point",
                    "text": "Same source text",
                    "metadata": content_document_metadata("doc-revoked"),
                    "score": 0.9,
                }
            ],
            [
                {
                    "id": "allowed-point",
                    "text": "Same source text",
                    "metadata": content_document_metadata("doc-allowed"),
                    "score": 0.8,
                }
            ],
        ]

        with (
            patch("src.services.retrieval.decompose_retrieval", new=AsyncMock(return_value=["q1", "q2"])),
            patch.object(service, "retrieve", new=AsyncMock(side_effect=retrieved)),
            patch.object(
                service,
                "_filter_active_artifact_generations",
                new=AsyncMock(side_effect=lambda documents: documents),
            ),
            patch(
                "src.services.retrieval.ContentClient.active_index_generations_many",
                new=AsyncMock(return_value={"doc-allowed": None}),
            ) as authorize,
        ):
            results = await service.cross_document_retrieve(
                "query",
                ["doc-allowed", "doc-revoked"],
                k=1,
                requester_id="user-1",
            )

        self.assertEqual([item["id"] for item in results], ["allowed-point"])
        authorize.assert_awaited_once_with(
            ["doc-allowed", "doc-revoked"], "user-1", False
        )

    async def test_cross_document_retrieval_rejects_partial_source_failure(self):
        service = RetrievalService()
        with (
            patch(
                "src.services.retrieval.decompose_retrieval",
                new=AsyncMock(return_value=["q1", "q2"]),
            ),
            patch.object(
                service,
                "retrieve",
                new=AsyncMock(side_effect=[[], RuntimeError("source unavailable")]),
            ),
        ):
            with self.assertRaises(RetrievalUnavailableError) as raised:
                await service.cross_document_retrieve(
                    "compare sources",
                    ["doc-1", "doc-2"],
                    requester_id="user-1",
                )

        self.assertEqual(
            str(raised.exception), "cross_document_retrieval_partial_failure"
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
                            "metadata": content_document_metadata("doc-1"),
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
            "metadata": content_document_metadata("doc-1", "generation-old"),
            },
            {
                "id": "new-point",
                "text": "new indexed text",
                "metadata": content_document_metadata("doc-1", "generation-new"),
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
                "metadata": content_document_metadata(document_id, generation),
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
                    **content_document_metadata("doc-legacy", "generation-old"),
                    "indexed_at": "2026-10-25T10:00:00+00:00",
                },
            },
            {
                "id": "legacy-new-point",
                "text": "new indexed text",
                "metadata": {
                    **content_document_metadata("doc-legacy", "generation-new"),
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

    async def test_private_requirement_document_uses_testing_acl_not_content_acl(self):
        owner_point = {
            "id": "owner-point",
            "metadata": {
                "artifact_type": "requirement_document",
                "document_id": "req-doc-1",
                "artifact_id": "req-doc-1",
                "artifact_version_id": "req-doc-1",
                "owner_id": "ba-owner",
                "visibility": "private",
                "ai_enabled": True,
            },
        }
        with patch(
            "src.services.retrieval.ContentClient.active_index_generations_many",
            new=AsyncMock(side_effect=AssertionError("primary Testing document must not use Content ACL")),
        ) as content_access:
            owner_result = await RetrievalService._filter_currently_accessible_sources(
                [owner_point], "ba-owner", False
            )
            member_result = await RetrievalService._filter_currently_accessible_sources(
                [owner_point], "project-tester", False
            )

        self.assertEqual(owner_result, [owner_point])
        self.assertEqual(member_result, [])
        content_access.assert_not_awaited()

    async def test_requirement_document_visibility_and_ai_disable_are_enforced(self):
        def point(document_id, visibility, owner="owner", shared=None, ai_enabled=True):
            return {
                "id": document_id,
                "metadata": {
                    "artifact_type": "requirement_document",
                    "document_id": document_id,
                    "artifact_id": document_id,
                    "artifact_version_id": document_id,
                    "owner_id": owner,
                    "visibility": visibility,
                    "shared_with": shared or [],
                    "ai_enabled": ai_enabled,
                },
            }

        candidates = [
            point("project-doc", "project"),
            point("shared-doc", "shared", shared=["viewer"]),
            point("disabled-doc", "private", ai_enabled=False),
        ]
        with patch(
            "src.services.retrieval.ContentClient.active_index_generations_many",
            new=AsyncMock(side_effect=AssertionError("Testing documents do not use Content ACL")),
        ):
            tester = await RetrievalService._filter_currently_accessible_sources(
                candidates, "tester", False
            )
            viewer = await RetrievalService._filter_currently_accessible_sources(
                candidates, "viewer", False
            )

        self.assertEqual([item["id"] for item in tester], ["project-doc"])
        self.assertEqual([item["id"] for item in viewer], ["project-doc", "shared-doc"])


if __name__ == "__main__":
    unittest.main()
