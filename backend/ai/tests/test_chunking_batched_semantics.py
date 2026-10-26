import unittest
from unittest.mock import AsyncMock, patch

from src.services.chunking import ChunkingService, embedder


class ChunkingBatchedSemanticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_batched_refinement_preserves_grouping_without_retaining_all_vectors(self):
        service = ChunkingService(
            min_chars=1,
            target_chars=8,
            max_chars=100,
            semantic_threshold=0.5,
            soft_threshold=0.8,
        )
        units = [
            {"text": f"unit-{index}", "hard_boundary": False}
            for index in range(4)
        ]
        vectors_by_text = {
            "unit-0": [1.0, 0.0],
            "unit-1": [1.0, 0.0],
            "unit-2": [0.0, 1.0],
            "unit-3": [0.0, 1.0],
        }
        expected = service._semantic_refinement(
            units, [vectors_by_text[unit["text"]] for unit in units]
        )
        embed_call_sizes = []

        async def embed_batch(texts):
            embed_call_sizes.append(len(texts))
            return [vectors_by_text[text] for text in texts]

        with (
            patch.object(embedder, "_batch_size", 2),
            patch.object(embedder, "embed_batch", new=AsyncMock(side_effect=embed_batch)),
        ):
            actual = await service._semantic_refinement_batched(units)

        self.assertEqual(actual, expected)
        self.assertEqual(embed_call_sizes, [2, 2])

    async def test_batched_refinement_rejects_provider_shape_mismatch(self):
        service = ChunkingService(min_chars=1, target_chars=2, max_chars=10)
        units = [
            {"text": "one", "hard_boundary": False},
            {"text": "two", "hard_boundary": False},
        ]

        with (
            patch("src.services.chunking.embedder._batch_size", 2),
            patch(
                "src.services.chunking.embedder.embed_batch",
                new=AsyncMock(return_value=[[1.0, 0.0]]),
            ),
            self.assertRaisesRegex(ValueError, "semantic_embedding_count_mismatch"),
        ):
            await service._semantic_refinement_batched(units)
