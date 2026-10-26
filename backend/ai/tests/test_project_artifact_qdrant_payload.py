import unittest
from hashlib import sha256

from pydantic import ValidationError

from src.schemas.project import (
    ProjectArtifactIndexRequest,
    QdrantPointPayload,
    validate_project_source_structure,
)
from src.services.project_knowledge import (
    project_artifact_metadata,
    project_artifact_point_payload,
)


class ProjectArtifactQdrantPayloadTests(unittest.TestCase):
    def test_payload_keeps_chunk_text_separate_from_typed_and_extended_metadata(self):
        payload = project_artifact_point_payload(
            "The account is locked after five failed attempts.",
            {
                "project_id": "project-1",
                "artifact_type": "requirement_version",
                "artifact_id": "requirement-1",
                "artifact_version_id": "version-3",
                "document_id": "document-1",
                "source_spans": [
                    {
                        "block_id": "block-7",
                        "parent_block_id": "section-2",
                        "section_path": ["Authentication", "Lockout"],
                    }
                ],
                "tenant_extension": "preserved",
            },
        )

        self.assertEqual(
            payload["text"], "The account is locked after five failed attempts."
        )
        self.assertEqual(payload["char_count"], len(payload["text"]))
        self.assertEqual(payload["word_count"], len(payload["text"].split()))
        self.assertEqual(payload["artifact_version_id"], "version-3")
        self.assertEqual(payload["source_spans"][0]["parent_block_id"], "section-2")
        self.assertEqual(payload["tenant_extension"], "preserved")

    def test_payload_rejects_content_overridden_by_metadata(self):
        with self.assertRaisesRegex(ValueError, "content_metadata_conflict"):
            project_artifact_point_payload(
                "approved chunk text", {"text": "different unembedded text"}
            )

    def test_payload_rejects_empty_content(self):
        with self.assertRaisesRegex(ValueError, "content_required"):
            project_artifact_point_payload("  ", {"project_id": "project-1"})

    def test_normalized_content_hash_is_not_mislabeled_as_source_file_hash(self):
        request = ProjectArtifactIndexRequest(
            artifact_type="requirement_version",
            artifact_id="requirement-1",
            artifact_version_id="version-3",
            text="Normalized requirement text",
        )

        metadata = project_artifact_metadata("project-1", request)

        self.assertIsNone(metadata["source_hash"])
        self.assertEqual(
            metadata["normalized_content_hash"],
            sha256(b"Normalized requirement text").hexdigest(),
        )

    def test_source_structure_validates_page_and_preserves_table_and_image_data(self):
        request = ProjectArtifactIndexRequest(
            artifact_type="source_document",
            artifact_id="document-1",
            artifact_version_id="version-1",
            text="Section text",
            source_structure=[
                {
                    "block_id": "block-1",
                    "parent_block_id": "section-1",
                    "text": "Section text",
                    "type": "paragraph",
                    "page_no": 2,
                    "extraction_status": "EXTRACTED",
                    "locations": [{"page_no": 2, "bbox": {"left": 0.1}}],
                    "table_metadata": {
                        "table_id": "table-1",
                        "column_headers": ["Field", "Value"],
                    },
                    "image_metadata": {
                        "image_id": "image-1",
                        "asset_status": "AVAILABLE",
                        "asset_key": "private/source/image-1",
                    },
                }
            ],
        )

        block = request.source_structure[0]
        self.assertEqual(block.page_no, 2)
        self.assertEqual(block.parent_block_id, "section-1")
        self.assertEqual(block.table_metadata.column_headers, ["Field", "Value"])
        self.assertEqual(block.image_metadata.asset_key, "private/source/image-1")

    def test_source_table_cell_offsets_must_resolve_inside_the_source_block(self):
        with self.assertRaisesRegex(
            ValueError, "source_structure_table_cell_out_of_range"
        ):
            ProjectArtifactIndexRequest(
                artifact_type="source_document",
                artifact_id="document-1",
                artifact_version_id="version-1",
                text="| A | B |",
                source_structure=[
                    {
                        "block_id": "table-1",
                        "type": "table",
                        "text": "| A | B |",
                        "table_metadata": {
                            "row_count": 1,
                            "column_count": 2,
                            "cell_spans": [
                                {
                                    "row_index": 0,
                                    "column_index": 0,
                                    "source_start": 2,
                                    "source_end": 10,
                                }
                            ],
                        },
                    }
                ],
            )

    def test_source_structure_rejects_invalid_page_and_ambiguous_block_ids(self):
        with self.assertRaises(ValidationError):
            ProjectArtifactIndexRequest(
                artifact_type="source_document",
                artifact_id="document-1",
                artifact_version_id="version-1",
                text="Source text",
                source_structure=[
                    {"block_id": "block-1", "type": "paragraph", "page_no": 0}
                ],
            )

        with self.assertRaisesRegex(ValidationError, "source_structure_block_id_ambiguous"):
            ProjectArtifactIndexRequest(
                artifact_type="source_document",
                artifact_id="document-1",
                artifact_version_id="version-1",
                text="Source text",
                source_structure=[
                    {"block_id": "block-1", "type": "paragraph"},
                    {"block_id": "block-1", "type": "paragraph"},
                ],
            )

        with self.assertRaisesRegex(ValueError, "source_structure_block_id_ambiguous"):
            validate_project_source_structure(
                [
                    {"block_id": "block-1", "type": "paragraph"},
                    {"block_id": "block-1", "type": "paragraph"},
                ]
            )

    def test_source_structure_rejects_self_parent_and_cycles(self):
        with self.assertRaisesRegex(
            ValueError, "source_structure_block_cannot_parent_itself"
        ):
            validate_project_source_structure(
                [{"block_id": "block-1", "parent_block_id": "block-1", "type": "section"}]
            )

        with self.assertRaisesRegex(ValueError, "source_structure_parent_cycle"):
            validate_project_source_structure(
                [
                    {"block_id": "block-1", "parent_block_id": "block-2", "type": "section"},
                    {"block_id": "block-2", "parent_block_id": "block-1", "type": "section"},
                ]
            )

    def test_source_structure_allows_parent_reference_to_parser_page_anchor(self):
        blocks = validate_project_source_structure(
            [
                {
                    "block_id": "block-1",
                    "parent_block_id": "#/pages/4",
                    "type": "paragraph",
                    "page_no": 4,
                }
            ]
        )

        self.assertEqual(blocks[0].parent_block_id, "#/pages/4")

    def test_generic_qdrant_payload_checks_text_embedding_and_source_span(self):
        text = "Account access is locked after repeated failures."
        payload = QdrantPointPayload.model_validate(
            {
                "text": text,
                "title": "Authentication",
                "embedding_input_mode": "TEXT",
                "embedding_input_hash": sha256(text.encode("utf-8")).hexdigest(),
                "chunk_hash": sha256(text.encode("utf-8")).hexdigest(),
                "char_count": len(text),
                "word_count": len(text.split()),
                "page_numbers": [3],
                "page_start": 3,
                "page_end": 3,
                "source_spans": [
                    {
                        "block_id": "block-3",
                        "locations": [{"page_no": 3}],
                        "chunk_start": 0,
                        "chunk_end": len(text),
                    }
                ],
            }
        )

        self.assertEqual(payload.page_numbers, [3])
        self.assertEqual(payload.source_spans[0].block_id, "block-3")

    def test_generic_qdrant_payload_rejects_wrong_embedding_mode_hash(self):
        text = "Source text"
        with self.assertRaisesRegex(ValidationError, "qdrant_point_embedding_input_hash_mismatch"):
            QdrantPointPayload.model_validate(
                {
                    "text": text,
                    "title": "Document title",
                    "embedding_input_mode": "TITLE_AND_TEXT",
                    "embedding_input_hash": sha256(text.encode("utf-8")).hexdigest(),
                }
            )

    def test_generic_qdrant_payload_requires_complete_nonnegative_source_offsets(self):
        for offsets in (
            {"source_start": 0},
            {"source_end": 4},
            {"source_start": -1, "source_end": 2},
            {"source_start": 5, "source_end": 4},
        ):
            with self.subTest(offsets=offsets):
                with self.assertRaisesRegex(
                    ValidationError, "qdrant_point_source_range_invalid"
                ):
                    QdrantPointPayload.model_validate(
                        {
                            "text": "Source text",
                            "source_spans": [{"block_id": "block-1", **offsets}],
                        }
                    )

    def test_generic_qdrant_payload_allows_zero_width_source_anchor(self):
        payload = QdrantPointPayload.model_validate(
            {
                "text": "Image caption",
                "source_spans": [
                    {"block_id": "image-1", "source_start": 8, "source_end": 8}
                ],
            }
        )

        self.assertEqual(payload.source_spans[0].source_start, 8)
        self.assertEqual(payload.source_spans[0].source_end, 8)

    def test_generic_qdrant_payload_rejects_inaccurate_content_counts(self):
        for count_field, count_value, error_code in (
            ("char_count", 1, "qdrant_point_char_count_mismatch"),
            ("word_count", 1, "qdrant_point_word_count_mismatch"),
        ):
            with self.subTest(count_field=count_field):
                with self.assertRaisesRegex(ValidationError, error_code):
                    QdrantPointPayload.model_validate(
                        {"text": "Source text has five words.", count_field: count_value}
                    )
