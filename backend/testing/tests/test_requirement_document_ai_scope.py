import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.requirements.services import requirement_documents


class RequirementDocumentAIScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_cursor_is_signed_and_round_trips_document_id(self):
        with patch.object(requirement_documents.settings, "SECRET_KEY", "scope-secret"):
            cursor = requirement_documents.encode_ai_document_cursor("PRJ-1", "RDOC-200")
            self.assertEqual(
                requirement_documents.decode_ai_document_cursor(cursor, "PRJ-1"), "RDOC-200"
            )

    async def test_invalid_cursor_is_rejected(self):
        with patch.object(requirement_documents.settings, "SECRET_KEY", "scope-secret"):
            with self.assertRaises(HTTPException) as raised:
                requirement_documents.decode_ai_document_cursor("RDOC-private.invalid", "PRJ-1")
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail["code"], "DOCUMENT_CURSOR_INVALID")

    async def test_cursor_cannot_be_replayed_across_projects(self):
        with patch.object(requirement_documents.settings, "SECRET_KEY", "scope-secret"):
            cursor = requirement_documents.encode_ai_document_cursor("PRJ-1", "RDOC-200")
            with self.assertRaises(HTTPException):
                requirement_documents.decode_ai_document_cursor(cursor, "PRJ-2")

    async def test_page_filters_private_documents_and_returns_opaque_next_cursor(self):
        documents = [
            {
                "_id": "RDOC-owner",
                "project_id": "PRJ-1",
                "status": "READY",
                "ai_enabled": True,
                "index_status": "DEGRADED",
                "parse_report": {
                    "parser": "docling",
                    "parser_version": "1.2",
                    "page_count": 12,
                    "ocr_enabled": True,
                    "structure_available": True,
                    "unprocessed_blocks_reported": True,
                    "unprocessed_blocks": [
                        {
                            "block_id": "page-4-table-2",
                            "type": "table",
                            "page_no": 4,
                            "reason_code": "TABLE_TEXT_NOT_EXTRACTED",
                            "locations": [{"bbox": "not exposed"}],
                        }
                    ],
                },
                "created_by": "user-1",
                "normalized_content": "authorized source",
                "object_key": "private/object/key",
            },
            {
                "_id": "RDOC-other",
                "project_id": "PRJ-1",
                "status": "READY",
                "ai_enabled": True,
                "created_by": "user-2",
                "visibility": "private",
                "normalized_content": "private source",
            },
        ]
        user = SimpleNamespace(id="user-1", is_system_admin=False)
        with (
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(
                requirement_documents.requirement_document_repository,
                "list_ai_scope_page",
                new=AsyncMock(return_value=documents),
            ) as list_page,
            patch.object(requirement_documents.settings, "SECRET_KEY", "scope-secret"),
        ):
            result = await requirement_documents.list_ai_requirement_document_page(
                "PRJ-1", "", 2, user
            )

        self.assertEqual([item["_id"] for item in result["items"]], ["RDOC-owner"])
        self.assertNotIn("object_key", result["items"][0])
        self.assertEqual(result["items"][0]["index_status"], "DEGRADED")
        self.assertEqual(
            result["items"][0]["parse_report"]["unprocessed_block_count"], 1
        )
        self.assertTrue(result["items"][0]["parse_report"]["unprocessed_blocks_reported"])
        self.assertEqual(
            result["items"][0]["parse_report"]["unprocessed_blocks"][0]["page_no"], 4
        )
        self.assertNotIn("locations", result["items"][0]["parse_report"]["unprocessed_blocks"][0])
        self.assertNotIn("object_key", result["items"][0]["parse_report"])
        self.assertNotIn("RDOC-other", result["next_cursor"])
        with patch.object(requirement_documents.settings, "SECRET_KEY", "scope-secret"):
            self.assertEqual(
                requirement_documents.decode_ai_document_cursor(
                    result["next_cursor"], "PRJ-1"
                ),
                "RDOC-other",
            )
        list_page.assert_awaited_once_with("PRJ-1", None, 2)


if __name__ == "__main__":
    unittest.main()
