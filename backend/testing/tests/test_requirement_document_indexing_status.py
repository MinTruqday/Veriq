import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.modules.requirements.services import requirement_documents
from src.modules.requirements.services.requirement_documents import (
    list_requirement_source_structure_page,
    requirement_document_index_status,
)


class RequirementDocumentIndexStatusTests(unittest.TestCase):
    def test_failed_index_is_not_marked_degraded_or_complete(self):
        self.assertEqual(
            requirement_document_index_status(
                False,
                {"unprocessed_blocks": [{"block_id": "#/pages/1/pictures/0"}]},
            ),
            "FAILED",
        )

    def test_index_with_unprocessed_source_blocks_is_degraded(self):
        self.assertEqual(
            requirement_document_index_status(
                True,
                {"unprocessed_blocks": [{"block_id": "#/pages/1/pictures/0"}]},
            ),
            "DEGRADED",
        )

    def test_complete_index_is_indexed_when_parser_reports_no_unprocessed_blocks(self):
        self.assertEqual(
            requirement_document_index_status(
                True,
                {"unprocessed_blocks": [], "page_count": 200},
            ),
            "INDEXED",
        )

    def test_extracted_ocr_text_with_accuracy_warning_can_be_indexed(self):
        self.assertEqual(
            requirement_document_index_status(
                True,
                {
                    "unprocessed_blocks": [],
                    "extraction_warnings": [
                        {
                            "type": "ocr_text",
                            "reason_code": "OCR_TEXT_REQUIRES_ACCURACY_VALIDATION",
                        }
                    ],
                },
            ),
            "INDEXED",
        )

    def test_missing_extraction_report_is_not_presented_as_complete(self):
        self.assertEqual(requirement_document_index_status(True, {}), "DEGRADED")


class RequirementSourceImageMetadataPrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def read_structure(self, document):
        user = SimpleNamespace(id="qa-1", is_system_admin=False)
        with patch.object(
            requirement_documents,
            "get_requirement_document_record",
            new=AsyncMock(return_value=document),
        ):
            return await list_requirement_source_structure_page(
                document["_id"], 0, 10, user, permission="knowledge.read"
            )

    async def test_private_asset_key_is_removed_from_block_collection_response(self):
        document = {
            "_id": "document-1",
            "project_id": "project-1",
            "source_structure_store": "blocks",
            "source_structure_source_hash": "source-hash",
            "source_structure_count": 1,
            "parse_report": {"unprocessed_blocks": []},
        }
        row = {
            "block_index": 0,
            "block": {
                "text": "Figure caption",
                "image_metadata": {
                    "asset_key": "private/document-1/image.png",
                    "asset_status": "STORED",
                    "asset_available": True,
                },
            },
        }
        with patch.object(
            requirement_documents.requirement_source_block_repository,
            "page_version",
            new=AsyncMock(return_value=[row]),
        ):
            result = await self.read_structure(document)

        image_metadata = result["items"][0]["image_metadata"]
        self.assertNotIn("asset_key", image_metadata)
        self.assertTrue(image_metadata["asset_available"])
        self.assertEqual(image_metadata["asset_status"], "STORED")

    async def test_private_asset_key_is_removed_from_legacy_document_response(self):
        document = {
            "_id": "document-1",
            "project_id": "project-1",
            "source_structure": [
                {
                    "text": "Figure caption",
                    "image_metadata": {
                        "asset_key": "private/document-1/image.png",
                        "asset_status": "STORED",
                        "asset_available": True,
                    },
                }
            ],
            "parse_report": {"unprocessed_blocks": []},
        }
        result = await self.read_structure(document)

        image_metadata = result["items"][0]["image_metadata"]
        self.assertNotIn("asset_key", image_metadata)
        self.assertTrue(image_metadata["asset_available"])


if __name__ == "__main__":
    unittest.main()
