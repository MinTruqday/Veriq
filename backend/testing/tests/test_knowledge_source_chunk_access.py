import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.requirements.api import requirement_documents


class KnowledgeSourceChunkAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_chunk_inspection_checks_project_and_document_access_before_ai_call(self):
        user = SimpleNamespace(id="qa-1", is_system_admin=False)
        document = {
            "_id": "source-1",
            "project_id": "project-1",
            "artifact_version_id": "source-version-3",
        }
        expected = {
            "project_id": "project-1",
            "artifact_version_id": "source-version-3",
            "items": [],
            "next_cursor": None,
        }
        with (
            patch.object(
                requirement_documents,
                "get_project_entity",
                new=AsyncMock(return_value=document),
            ) as get_entity,
            patch.object(
                requirement_documents,
                "require_document_access",
                new=AsyncMock(return_value=document),
            ) as check_document_access,
            patch.object(
                requirement_documents,
                "list_project_artifact_chunks",
                new=AsyncMock(return_value=expected),
            ) as list_chunks,
        ):
            response = await requirement_documents.list_knowledge_source_chunks(
                "project-1", "source-1", limit=50, cursor=None, user=user
            )

        get_entity.assert_awaited_once_with(
            "requirement_documents", "source-1", user, "knowledge.read"
        )
        check_document_access.assert_awaited_once_with(
            document, user, "knowledge.read"
        )
        list_chunks.assert_awaited_once_with(
            "project-1", "source-version-3", 50, None
        )
        self.assertEqual(response["data"], expected)

    async def test_denied_document_access_never_reads_vector_metadata(self):
        user = SimpleNamespace(id="tester-1", is_system_admin=False)
        document = {"_id": "source-1", "project_id": "project-1"}
        with (
            patch.object(
                requirement_documents,
                "get_project_entity",
                new=AsyncMock(return_value=document),
            ),
            patch.object(
                requirement_documents,
                "require_document_access",
                new=AsyncMock(side_effect=HTTPException(status_code=403)),
            ),
            patch.object(
                requirement_documents,
                "list_project_artifact_chunks",
                new=AsyncMock(),
            ) as list_chunks,
        ):
            with self.assertRaises(HTTPException):
                await requirement_documents.list_knowledge_source_chunks(
                    "project-1", "source-1", limit=50, cursor=None, user=user
                )

        list_chunks.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
