import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.services.document.internal import (
    INDEX_SOURCE_SNAPSHOT_FIELDS,
    exchange_internal_document,
)


class LiveDocumentAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_index_completion_publishes_active_generation_with_status(self):
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(matched_count=1),
        ) as update_one:
            result = await exchange_internal_document(
                {
                    "action": "update_index",
                    "document_id": "doc-1",
                    "indexing_attempt_id": "attempt-1",
                    "index_generation": "a" * 64,
                    "indexed_chunks": 4,
                    "index_report": {},
                    "extraction_method": "docling",
                    "source_snapshot": {
                        field: None for field in INDEX_SOURCE_SNAPSHOT_FIELDS
                    },
                }
            )

        self.assertTrue(result["data"]["updated"])
        update = update_one.await_args.args[1]
        self.assertEqual(update["$set"]["active_index_generation"], "a" * 64)
        self.assertEqual(update["$set"]["indexing_status"], "indexed")

    async def test_index_completion_rejects_invalid_generation_without_write(self):
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(),
        ) as update_one:
            with self.assertRaises(HTTPException) as raised:
                await exchange_internal_document(
                    {
                        "action": "update_index",
                        "document_id": "doc-1",
                        "indexing_attempt_id": "attempt-1",
                        "index_generation": "not-a-generation",
                        "index_report": {},
                        "source_snapshot": {
                            field: None for field in INDEX_SOURCE_SNAPSHOT_FIELDS
                        },
                    }
                )

        self.assertEqual(raised.exception.status_code, 422)
        update_one.assert_not_awaited()

    async def test_bulk_access_returns_only_live_documents_allowed_for_requester(self):
        cursor = SimpleNamespace(
            to_list=AsyncMock(return_value=[{"_id": "doc-owner"}, {"_id": "doc-public"}])
        )
        with patch(
            "src.services.document.internal.DocumentRepository.find", return_value=cursor
        ) as find:
            result = await exchange_internal_document(
                {
                    "action": "get_accessible_documents",
                    "document_ids": ["doc-owner", "doc-public", "doc-revoked", "doc-owner"],
                    "user_id": "user-1",
                    "is_admin": False,
                }
            )

        find.assert_called_once_with(
            {
                "_id": {"$in": ["doc-owner", "doc-public", "doc-revoked"]},
                "is_deleted": {"$ne": True},
                "is_indexed": {"$ne": False},
                "ai_enabled": {"$ne": False},
                "index_status": {"$ne": "REVOKE_PENDING"},
                "$or": [
                    {"creator_id": "user-1"},
                    {
                        "status": "published",
                        "$or": [
                            {"visibility": "public"},
                            {"visibility": {"$exists": False}},
                        ],
                    },
                ],
            },
            {"_id": 1, "active_index_generation": 1},
        )
        self.assertEqual(
            result["data"],
            {
                "documents": [
                    {"_id": "doc-owner", "active_index_generation": None},
                    {"_id": "doc-public", "active_index_generation": None},
                ]
            },
        )

    async def test_admin_bulk_access_still_excludes_deleted_documents(self):
        cursor = SimpleNamespace(to_list=AsyncMock(return_value=[]))
        with patch(
            "src.services.document.internal.DocumentRepository.find", return_value=cursor
        ) as find:
            result = await exchange_internal_document(
                {
                    "action": "get_accessible_documents",
                    "document_ids": ["doc-1"],
                    "user_id": "admin-1",
                    "is_admin": True,
                }
            )

        find.assert_called_once_with(
            {
                "_id": {"$in": ["doc-1"]},
                "is_deleted": {"$ne": True},
                "is_indexed": {"$ne": False},
                "ai_enabled": {"$ne": False},
                "index_status": {"$ne": "REVOKE_PENDING"},
            },
            {"_id": 1, "active_index_generation": 1},
        )
        self.assertEqual(result["data"], {"documents": []})

    async def test_bulk_access_rejects_unbounded_identifier_lists(self):
        with self.assertRaises(HTTPException) as raised:
            await exchange_internal_document(
                {
                    "action": "get_accessible_documents",
                    "document_ids": [f"doc-{index}" for index in range(101)],
                    "user_id": "user-1",
                    "is_admin": False,
                }
            )

        self.assertEqual(raised.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
