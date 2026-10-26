import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.repositories.requirement_document import RequirementDocumentRepository


class RequirementDocumentDuplicateVisibilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.collection = SimpleNamespace(find_one=AsyncMock(return_value=None))
        self.database = SimpleNamespace(
            value=SimpleNamespace(requirement_documents=self.collection)
        )
        self.repository = RequirementDocumentRepository()

    async def test_private_source_is_never_reused_between_uploads(self):
        with patch("src.repositories.requirement_document.database", self.database):
            result = await self.repository.find_reusable_duplicate(
                "project-1", "hash", "pdf", "private", [], True, "REFERENCE", "user-1"
            )

        self.assertIsNone(result)
        self.collection.find_one.assert_not_awaited()

    async def test_shared_source_is_not_reused_for_a_user_outside_its_recipients(self):
        with patch("src.repositories.requirement_document.database", self.database):
            result = await self.repository.find_reusable_duplicate(
                "project-1",
                "hash",
                "pdf",
                "shared",
                ["user-2"],
                True,
                "REFERENCE",
                "user-1",
            )

        self.assertIsNone(result)
        self.collection.find_one.assert_not_awaited()

    async def test_project_source_reuse_matches_processing_settings_and_excludes_failed_sources(self):
        with patch("src.repositories.requirement_document.database", self.database):
            await self.repository.find_reusable_duplicate(
                "project-1", "hash", "pdf", "project", [], True, "REFERENCE", "user-1"
            )

        self.collection.find_one.assert_awaited_once_with(
            {
                "project_id": "project-1",
                "content_hash": "hash",
                "format": "pdf",
                "visibility": "project",
                "ai_enabled": True,
                "source_type": "REFERENCE",
                "ocr_language": None,
                "status": {"$nin": ["ARCHIVED", "PARSE_FAILED"]},
            }
        )

    async def test_shared_source_reuse_requires_exact_recipient_scope(self):
        recipients = ["user-1", "user-2"]
        with patch("src.repositories.requirement_document.database", self.database):
            await self.repository.find_reusable_duplicate(
                "project-1",
                "hash",
                "pdf",
                "shared",
                recipients,
                True,
                "REFERENCE",
                "user-1",
            )

        query = self.collection.find_one.await_args.args[0]
        self.assertEqual(query["shared_with"], recipients)
        self.assertEqual(query["visibility"], "shared")


if __name__ == "__main__":
    unittest.main()
