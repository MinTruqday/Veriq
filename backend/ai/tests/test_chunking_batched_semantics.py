import unittest
from unittest.mock import AsyncMock, patch

from src.services.chunking import ChunkingService, embedder


class ChunkingBatchedSemanticsTests(unittest.IsolatedAsyncioTestCase):
    def test_structured_chunk_retains_parent_chain_in_source_metadata(self):
        service = ChunkingService(min_chars=1, target_chars=100, max_chars=200)
        structure = [
            {"block_id": "root", "type": "chapter", "text": "Chapter"},
            {
                "block_id": "section",
                "parent_block_id": "root",
                "type": "section_header",
                "text": "Section",
            },
            {
                "block_id": "paragraph",
                "parent_block_id": "section",
                "type": "paragraph",
                "text": "Requirement text",
            },
        ]
        expected_ancestors = ["root", "section"]

        for units in (
            service._structure_units("Chapter\nSection\nRequirement text", structure),
            list(service._iter_plain_structure_units(structure)),
        ):
            chunks = service._serialize_groups(
                [units], {"document_id": "parent-chain"}, "docling_structure_fallback"
            )
            paragraph_span = next(
                span
                for span in chunks[0]["metadata"]["source_spans"]
                if span["block_id"] == "paragraph"
            )
            self.assertEqual(paragraph_span["parent_block_id"], "section")
            self.assertEqual(paragraph_span["ancestor_block_ids"], expected_ancestors)
            self.assertEqual(paragraph_span["ancestor_chain_status"], "COMPLETE")

        root_unit = next(service._iter_plain_structure_units(structure))
        root_span = service._serialize_groups(
            [[root_unit]],
            {"document_id": "parent-chain"},
            "docling_structure_fallback",
        )[0]["metadata"]["source_spans"][0]
        self.assertEqual(root_span["ancestor_chain_status"], "ROOT")

    def test_structured_parent_chain_marks_unresolved_external_parent(self):
        structure = [
            {
                "block_id": "paragraph",
                "parent_block_id": "parser-page-anchor",
                "type": "paragraph",
                "text": "Requirement text",
            }
        ]
        service = ChunkingService()
        unit = next(service._iter_plain_structure_units(structure))

        self.assertEqual(unit["ancestor_block_ids"], [])
        self.assertEqual(unit["ancestor_chain_status"], "PARTIAL")

    def test_related_image_retains_parent_chain(self):
        structure = [
            {"block_id": "root", "type": "chapter", "text": "Chapter", "page_no": 1},
            {
                "block_id": "section",
                "parent_block_id": "root",
                "type": "section_header",
                "text": "Section",
                "page_no": 1,
            },
            {
                "block_id": "paragraph",
                "parent_block_id": "section",
                "type": "paragraph",
                "text": "Requirement text",
                "page_no": 1,
            },
            {
                "block_id": "figure",
                "parent_block_id": "section",
                "type": "picture",
                "page_no": 1,
                "text": "",
                "image_metadata": {"asset_available": True},
            },
        ]

        links, _, _ = ChunkingService._streaming_image_links(structure)

        image = next(image for images in links.values() for image in images)
        self.assertEqual(image["ancestor_block_ids"], ["root", "section"])
        self.assertEqual(image["ancestor_chain_status"], "COMPLETE")

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

    async def test_semantic_group_is_bounded_even_when_neighbors_are_identical(self):
        service = ChunkingService(
            min_chars=1,
            target_chars=8,
            max_chars=12,
            semantic_threshold=0.1,
            soft_threshold=0.1,
        )
        units = [
            {"text": f"unit-{index}", "hard_boundary": False}
            for index in range(20)
        ]

        with (
            patch.object(embedder, "_batch_size", 4),
            patch.object(
                embedder,
                "embed_batch",
                new=AsyncMock(return_value=[[1.0, 0.0]] * 4),
            ),
        ):
            groups = [group async for group in service._iter_semantic_refinement_batched(units)]

        self.assertEqual(sum(len(group) for group in groups), len(units))
        self.assertTrue(all(sum(len(unit["text"]) for unit in group) <= service.max_chars for group in groups))

    async def test_chunk_document_preserves_ids_when_semantic_groups_stream(self):
        service = ChunkingService(
            min_chars=1,
            target_chars=8,
            max_chars=100,
            semantic_threshold=0.5,
            soft_threshold=0.8,
        )
        structure = [
            {"block_id": f"block-{index}", "type": "paragraph", "text": f"unit-{index}"}
            for index in range(4)
        ]
        metadata = {
            "document_id": "doc-stream",
            "source_version": "v1",
            "index_generation": "generation-1",
        }
        vectors_by_text = {
            "unit-0": [1.0, 0.0],
            "unit-1": [1.0, 0.0],
            "unit-2": [0.0, 1.0],
            "unit-3": [0.0, 1.0],
        }

        async def embed_batch(texts):
            return [vectors_by_text[text] for text in texts]

        units = service._structure_units("\n".join(item["text"] for item in structure), structure)
        with (
            patch.object(embedder, "_batch_size", 2),
            patch.object(embedder, "embed_batch", new=AsyncMock(side_effect=embed_batch)),
        ):
            expected_groups = await service._semantic_refinement_batched(units)
            expected = service._serialize_groups(
                service._iter_size_guard(expected_groups),
                metadata,
                "docling_structure_semantic",
            )
            actual = await service.chunk_document(
                "\n".join(item["text"] for item in structure), metadata, structure
            )
            streamed = [
                chunk
                async for chunk in service.iter_chunk_document(
                    "\n".join(item["text"] for item in structure), metadata, structure
                )
            ]

        self.assertEqual(actual, expected)
        self.assertEqual(streamed, expected)

    async def test_midstream_embedding_failure_returns_only_structural_fallback(self):
        service = ChunkingService(min_chars=1, target_chars=8, max_chars=100)
        structure = [
            {"block_id": f"block-{index}", "type": "paragraph", "text": f"unit-{index}"}
            for index in range(6)
        ]
        calls = 0

        async def embed_batch(texts):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("provider unavailable")
            return [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

        with (
            patch.object(embedder, "_batch_size", 3),
            patch.object(embedder, "embed_batch", new=AsyncMock(side_effect=embed_batch)),
        ):
            chunks = await service.chunk_document(
                "\n".join(item["text"] for item in structure),
                {"document_id": "doc-fallback"},
                structure,
            )

        self.assertTrue(chunks)
        self.assertTrue(
            all(chunk["metadata"]["chunk_type"] == "docling_structure_fallback" for chunk in chunks)
        )
        self.assertEqual(
            [span["block_id"] for chunk in chunks for span in chunk["metadata"]["source_spans"]],
            [item["block_id"] for item in structure],
        )

    async def test_markdown_only_path_streams_units_and_matches_compatibility_output(self):
        service = ChunkingService(
            min_chars=1,
            target_chars=12,
            max_chars=100,
            semantic_threshold=0.5,
            soft_threshold=0.8,
        )
        markdown = "# Account\n\nCreate an account.\n\n# Login\n\nSubmit credentials."
        metadata = {"document_id": "markdown-stream"}
        with (
            patch.object(embedder, "_batch_size", 2),
            patch.object(embedder, "embed_batch", new=AsyncMock(return_value=[[1.0, 0.0], [1.0, 0.0]])),
        ):
            expected = await service.chunk_document(markdown, metadata)
            with patch.object(service, "_markdown_units", side_effect=AssertionError("materialized markdown units")):
                actual = [
                    chunk
                    async for chunk in service.iter_chunk_document(markdown, metadata)
                ]

        self.assertEqual(actual, expected)

    async def test_markdown_fallback_uses_source_offsets_from_original_document(self):
        service = ChunkingService(min_chars=1, target_chars=8, max_chars=100)
        markdown = "  # Account  \n\n  Create an account.  \n\n# Login\n\nSubmit credentials."
        with (
            patch.object(embedder, "_batch_size", 4),
            patch.object(embedder, "embed_batch", new=AsyncMock(return_value=[[1.0, 0.0]] * 4)),
        ):
            chunks = await service.chunk_document(markdown, {"document_id": "source-offsets"})

        spans = [span for chunk in chunks for span in chunk["metadata"]["source_spans"]]
        for span in spans:
            source_slice = markdown[span["source_start"]:span["source_end"]]
            self.assertEqual(source_slice, source_slice.strip())
            self.assertEqual(span["chunk_end"] - span["chunk_start"], len(source_slice))
        self.assertEqual([span["source_start"] for span in spans], sorted(span["source_start"] for span in spans))

    async def test_structured_text_without_image_only_blocks_streams_units(self):
        service = ChunkingService(
            min_chars=1,
            target_chars=12,
            max_chars=100,
            semantic_threshold=0.5,
            soft_threshold=0.8,
        )
        structure = [
            {"block_id": "heading", "type": "heading", "level": 1, "text": "Account"},
            {"block_id": "paragraph-1", "type": "paragraph", "text": "Create an account."},
            {"block_id": "paragraph-2", "type": "paragraph", "text": "Submit credentials."},
        ]
        markdown = "# Account\n\nCreate an account.\n\nSubmit credentials."
        metadata = {"document_id": "structured-stream"}
        with (
            patch.object(embedder, "_batch_size", 2),
            patch.object(
                embedder,
                "embed_batch",
                new=AsyncMock(side_effect=lambda texts: [[1.0, 0.0] for _ in texts]),
            ),
        ):
            expected = await service.chunk_document(markdown, metadata, structure)
            with patch.object(service, "_structure_units", side_effect=AssertionError("materialized source units")):
                actual = [
                    chunk
                    async for chunk in service.iter_chunk_document(markdown, metadata, structure)
                ]

        self.assertEqual(actual, expected)

    async def test_structured_image_links_survive_streaming_without_materializing_units(self):
        service = ChunkingService(
            min_chars=1,
            target_chars=12,
            max_chars=100,
            semantic_threshold=0.5,
            soft_threshold=0.8,
        )
        structure = [
            {
                "block_id": "text-1",
                "parent_block_id": "root",
                "type": "text",
                "page_no": 1,
                "locations": [{"page_no": 1}],
                "text": "Page one text",
            },
            {
                "block_id": "image-2",
                "parent_block_id": "root",
                "type": "picture",
                "page_no": 2,
                "locations": [{"page_no": 2}],
                "text": "",
                "image_metadata": {"asset_available": True},
            },
            {
                "block_id": "text-2",
                "parent_block_id": "root",
                "type": "text",
                "page_no": 2,
                "locations": [{"page_no": 2}],
                "text": "Page two text",
            },
        ]
        metadata = {"document_id": "image-stream"}

        async def embed_batch(texts):
            return [[1.0, 0.0] for _ in texts]

        with (
            patch.object(embedder, "_batch_size", 2),
            patch.object(embedder, "embed_batch", new=AsyncMock(side_effect=embed_batch)),
        ):
            expected = await service.chunk_document("", metadata, structure)
            with patch.object(service, "_structure_units", side_effect=AssertionError("materialized source units")):
                actual = [
                    chunk
                    async for chunk in service.iter_chunk_document("", metadata, structure)
                ]

        self.assertEqual(actual, expected)
        image_spans = [
            span
            for chunk in actual
            for span in chunk["metadata"]["source_spans"]
            if span["content_type"] == "picture"
        ]
        self.assertEqual([span["block_id"] for span in image_spans], ["image-2"])
