import unittest

from src.services.chunking import ChunkingService, chunker
from src.schemas.project import ProjectArtifactQdrantPayload


class ChunkIndexGenerationTests(unittest.TestCase):
    def test_unknown_heading_levels_do_not_invent_nested_source_hierarchy(self):
        service = ChunkingService()
        units = service._structure_units(
            "",
            [
                {"type": "heading", "level": None, "text": "First heading"},
                {"type": "text", "text": "First body"},
                {"type": "heading", "level": None, "text": "Second heading"},
                {"type": "text", "text": "Second body"},
                {"type": "heading", "level": 1, "text": "Known heading"},
                {"type": "heading", "level": 2, "text": "Known child"},
                {"type": "text", "text": "Known child body"},
            ],
        )

        section_path_by_text = {unit["text"]: unit["section_path"] for unit in units}
        self.assertEqual(section_path_by_text["First body"], ["First heading"])
        self.assertEqual(section_path_by_text["Second body"], ["Second heading"])
        self.assertEqual(
            section_path_by_text["Known child body"],
            ["Known heading", "Known child"],
        )

    def test_generation_change_gets_distinct_point_ids_and_retry_is_idempotent(self):
        units = [[
            {
                "text": "A source-grounded block with stable content.",
                "type": "text",
                "block_id": "#/pages/1/blocks/0",
                "parent_block_id": "#/pages/1",
                "block_index": 0,
                "locations": [{"page_no": 1}],
                "source_start": 0,
                "source_end": 44,
            }
        ]]
        metadata = {
            "document_id": "document-1",
            "source_version": "v1",
            "index_generation": "generation-a",
        }

        first = chunker._serialize_groups(units, metadata, "test")
        retry = chunker._serialize_groups(units, metadata, "test")
        replacement = chunker._serialize_groups(
            units, {**metadata, "index_generation": "generation-b"}, "test"
        )

        self.assertEqual(first[0]["id"], retry[0]["id"])
        self.assertNotEqual(first[0]["id"], replacement[0]["id"])

    def test_oversized_table_chunks_repeat_headers_and_keep_data_row_ranges(self):
        service = ChunkingService(min_chars=10, target_chars=40, max_chars=65)
        table = (
            "| ID | Description |\n"
            "| --- | --- |\n"
            "| 1 | alpha value |\n"
            "| 2 | bravo value |\n"
            "| 3 | charlie value |\n"
            "| 4 | delta value |"
        )
        pieces = service._split_oversized_unit(
            {
                "text": table,
                "type": "table",
                "source_start": 0,
                "source_end": len(table),
                "table_metadata": {
                    "table_id": "table-1",
                    "row_count": 5,
                    "column_count": 2,
                    "column_headers": ["ID", "Description"],
                },
            }
        )

        self.assertGreater(len(pieces), 1)
        self.assertTrue(all(piece["text"].startswith("| ID | Description |\n| --- | --- |\n") for piece in pieces))
        self.assertEqual(
            [
                (
                    piece["table_metadata"]["data_row_start"],
                    piece["table_metadata"]["data_row_end"],
                )
                for piece in pieces
            ][0][0],
            1,
        )
        self.assertEqual(pieces[-1]["table_metadata"]["data_row_end"], 4)
        self.assertTrue(all(piece["table_metadata"]["row_boundary_preserved"] for piece in pieces))
        self.assertTrue(pieces[0]["text"].endswith("| 1 | alpha value |\n"))
        self.assertTrue(pieces[-1]["text"].endswith("| 4 | delta value |"))
        for piece in pieces:
            for cell in piece["table_metadata"]["cell_spans"]:
                self.assertEqual(
                    piece["text"][cell["chunk_start"] : cell["chunk_end"]],
                    table[cell["source_start"] : cell["source_end"]],
                )

        serialized = chunker._serialize_groups(
            [[piece] for piece in pieces],
            {"document_id": "document-1", "index_generation": "generation-1"},
            "table",
        )
        for index, chunk in enumerate(serialized):
            payload = ProjectArtifactQdrantPayload.model_validate(
                {
                    "text": chunk["text"],
                    **chunk["metadata"],
                }
            )
            span = payload.source_spans[0]
            self.assertEqual(
                payload.text[span.chunk_start : span.chunk_end], pieces[index]["text"]
            )
            for cell in span.table_metadata.cell_spans:
                self.assertEqual(
                    payload.text[cell.chunk_start : cell.chunk_end],
                    table[cell.source_start : cell.source_end],
                )

    def test_trimmed_table_block_keeps_cell_offsets_aligned_to_indexed_text(self):
        raw_table = "\n| ID | Value |\n| --- | --- |\n| 1 | alpha |\n"
        cell_start = raw_table.index("ID")
        unit = chunker._structure_units(
            "",
            [
                {
                    "block_id": "table-1",
                    "parent_block_id": "section-1",
                    "type": "table",
                    "text": raw_table,
                    "table_metadata": {
                        "table_id": "table-1",
                        "row_count": 2,
                        "column_count": 2,
                        "cell_spans": [
                            {
                                "row_index": 0,
                                "column_index": 0,
                                "source_start": cell_start,
                                "source_end": cell_start + 2,
                            }
                        ],
                    },
                }
            ],
        )[0]

        cell = unit["table_metadata"]["cell_spans"][0]
        self.assertEqual(unit["text"][cell["source_start"] : cell["source_end"]], "ID")
        serialized = chunker._serialize_groups([[unit]], {}, "table")
        payload = ProjectArtifactQdrantPayload.model_validate(
            {"text": serialized[0]["text"], **serialized[0]["metadata"]}
        )
        span = payload.source_spans[0]
        self.assertEqual(span.parent_block_id, "section-1")
        mapped_cell = span.table_metadata.cell_spans[0]
        self.assertEqual(
            payload.text[mapped_cell.chunk_start : mapped_cell.chunk_end], "ID"
        )

    def test_source_segments_use_absolute_offsets_when_multiple_tables_share_chunk(self):
        service = ChunkingService()
        units = []
        for block_id, table_id, page_no in (
            ("table-1", "table-id-1", 1),
            ("table-2", "table-id-2", 2),
        ):
            table = "| Name |\n| --- |\n| Alpha |"
            units.extend(
                service._structure_units(
                    "",
                    [
                        {
                            "block_id": block_id,
                            "type": "table",
                            "text": table,
                            "page_no": page_no,
                            "locations": [{"page_no": page_no}],
                            "table_metadata": {
                                "table_id": table_id,
                                "row_count": 2,
                                "column_count": 1,
                            },
                        }
                    ],
                )
            )

        units[0]["source_segments"] = [
            {
                "role": "HEADER",
                "source_start": 0,
                "source_end": 8,
                "chunk_start": 0,
                "chunk_end": 8,
            }
        ]
        units[1]["source_segments"] = [
            {
                "role": "DATA_ROWS",
                "source_start": 16,
                "source_end": 26,
                "chunk_start": 0,
                "chunk_end": 10,
            }
        ]

        chunk = service._serialize_groups([units], {}, "table")[0]
        payload = ProjectArtifactQdrantPayload.model_validate(
            {"text": chunk["text"], **chunk["metadata"]}
        )

        second_span = payload.source_spans[1]
        second_segment = second_span.source_segments[0]
        self.assertGreater(second_span.chunk_start, 0)
        self.assertEqual(
            payload.text[second_segment.chunk_start : second_segment.chunk_end],
            "| Name |\n|",
        )

    def test_image_only_blocks_link_only_to_text_from_the_same_page(self):
        service = ChunkingService()
        units = service._structure_units(
            "",
            [
                {
                    "block_id": "text-page-1",
                    "parent_block_id": "document-root",
                    "type": "text",
                    "level": 1,
                    "page_no": 1,
                    "locations": [{"page_no": 1}],
                    "text": "Page one text",
                },
                {
                    "block_id": "image-page-2",
                    "parent_block_id": "document-root",
                    "type": "picture",
                    "level": 1,
                    "page_no": 2,
                    "locations": [{"page_no": 2}],
                    "text": "",
                    "image_metadata": {"asset_available": True},
                },
                {
                    "block_id": "text-page-2",
                    "parent_block_id": "document-root",
                    "type": "text",
                    "level": 1,
                    "page_no": 2,
                    "locations": [{"page_no": 2}],
                    "text": "Page two text",
                },
                {
                    "block_id": "image-page-3",
                    "parent_block_id": "document-root",
                    "type": "picture",
                    "level": 1,
                    "page_no": 3,
                    "locations": [{"page_no": 3}],
                    "text": "",
                    "image_metadata": {"asset_available": True},
                },
            ],
        )

        self.assertEqual(
            [image["block_id"] for image in units[0].get("related_images", [])],
            [],
        )
        self.assertEqual(
            [image["block_id"] for image in units[1].get("related_images", [])],
            ["image-page-2"],
        )
        linked_image_ids = {
            image["block_id"]
            for unit in units
            for image in unit.get("related_images", [])
        }
        self.assertNotIn("image-page-3", linked_image_ids)

    def test_page_ocr_confidence_survives_source_block_to_qdrant_span(self):
        service = ChunkingService()
        units = service._structure_units(
            "",
            [
                {
                    "block_id": "text-page-4",
                    "type": "text",
                    "page_no": 4,
                    "locations": [{"page_no": 4}],
                    "ocr_page_confidence": 0.83,
                    "text": "Text extracted from an OCR-processed source page.",
                }
            ],
        )
        chunks = service._serialize_groups(
            [[units[0]]], {"document_id": "document-1"}, "test"
        )
        payload = ProjectArtifactQdrantPayload.model_validate(
            {"text": chunks[0]["text"], **chunks[0]["metadata"]}
        )

        self.assertEqual(payload.source_spans[0].ocr_page_confidence, 0.83)


if __name__ == "__main__":
    unittest.main()
