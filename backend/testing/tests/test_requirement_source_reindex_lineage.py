import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.modules.requirements.services import requirement_sources


class RequirementSourceReindexLineageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.document = {
            "_id": "RDOC-lineage",
            "project_id": "PRJ-lineage",
            "status": "READY",
            "normalized_content": "Page-aware normalized text",
            "source_structure": [{"block_id": "block-1", "page": 2}],
            "parse_report": {"parser": "docling", "page_count": 2},
            "visibility": "private",
            "created_by": "qa-1",
        }
        self.user = SimpleNamespace(id="qa-1", is_system_admin=False)

    async def run_reindex(self, resulting_status):
        updated = {**self.document, "index_status": resulting_status}
        with (
            patch.object(
                requirement_sources,
                "get_project_entity",
                new=AsyncMock(return_value=self.document),
            ),
            patch(
                "src.modules.requirements.services.requirement_documents.require_document_access",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.requirements.services.requirement_documents.index_requirement_document",
                new=AsyncMock(return_value=True),
            ) as index_document,
            patch.object(
                requirement_sources.requirement_document_repository,
                "find",
                new=AsyncMock(return_value=updated),
            ),
            patch.object(
                requirement_sources.requirement_document_repository,
                "update",
                new=AsyncMock(),
            ),
            patch.object(requirement_sources, "audit", new=AsyncMock()),
        ):
            result = await requirement_sources.reindex_requirement_source(
                self.document["_id"], self.user
            )

        index_document.assert_awaited_once_with(self.document)
        return result

    async def test_reindex_uses_canonical_document_indexer_for_source_lineage(self):
        result = await self.run_reindex("INDEXED")

        self.assertEqual(result.status, "SUCCESS")
        self.assertTrue(result.indexed)

    async def test_partial_document_remains_degraded_after_successful_store_write(self):
        result = await self.run_reindex("DEGRADED")

        self.assertEqual(result.status, "DEGRADED")
        self.assertFalse(result.indexed)
        self.assertEqual(result.degraded_mode, "PARTIAL_SOURCE_EXTRACTION")

    async def test_vector_failure_is_distinguished_from_partial_extraction(self):
        result = await self.run_reindex("FAILED")

        self.assertEqual(result.status, "DEGRADED")
        self.assertFalse(result.indexed)
        self.assertEqual(result.degraded_mode, "DEGRADED_VECTOR")


if __name__ == "__main__":
    unittest.main()
