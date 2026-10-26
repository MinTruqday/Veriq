import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from src.clients import document_conversion
from src.core.configuration import settings
from src.modules.requirements.services import requirement_documents
from src.schemas.document_source import DocumentConversionResult


class RequirementSourceStructureTests(unittest.IsolatedAsyncioTestCase):
    async def test_pdf_conversion_http_timeout_matches_parse_lease_budget(self):
        response = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"data": {"markdown": "Parsed source", "source_hash": "abc"}},
        )

        class FakeAsyncClient:
            timeout_values = []

            def __init__(self, *, timeout):
                self.timeout = timeout
                type(self).timeout_values.append(timeout)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, *_args, **_kwargs):
                return response

        with patch.object(document_conversion.httpx, "AsyncClient", FakeAsyncClient):
            await document_conversion.convert_requirement_source(b"source", "source.pdf")

        self.assertEqual(
            FakeAsyncClient.timeout_values[0].read,
            settings.DOCUMENT_PARSE_TIMEOUT_SECONDS,
        )

    async def test_pdf_parse_uses_stable_ai_checkpoint_identity_and_attempt_guard(self):
        source = b"stable pdf source"
        source_hash = __import__("hashlib").sha256(source).hexdigest()
        document = {
            "_id": "doc-1",
            "project_id": "project-1",
            "created_by": "user-1",
            "filename": "requirements.pdf",
            "format": "pdf",
            "content_hash": source_hash,
            "ocr_language": "iso:en",
            "status": "PARSING",
            "parse_attempt_id": "attempt-1",
        }
        parsed = DocumentConversionResult(
            markdown="Rule A", source_hash=source_hash, page_count=1, parser="pymupdf_text"
        )
        with (
            patch.object(requirement_documents, "read_raw_requirement_source", new=AsyncMock(return_value=source)),
            patch.object(requirement_documents, "convert_requirement_source", new=AsyncMock(return_value=parsed)) as convert,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=document)),
        ):
            content, _ = await requirement_documents.read_and_parse_requirement_source(
                document, "attempt-1"
            )

        self.assertEqual(content, "Rule A")
        self.assertEqual(convert.await_args.kwargs["document_id"], "doc-1")
        self.assertEqual(convert.await_args.kwargs["project_id"], "project-1")
        self.assertEqual(convert.await_args.kwargs["owner_id"], "user-1")
        self.assertEqual(convert.await_args.kwargs["ocr_language"], "iso:en")

    async def test_pdf_parse_rejects_superseded_attempt_after_conversion(self):
        source = b"stable pdf source"
        source_hash = __import__("hashlib").sha256(source).hexdigest()
        document = {
            "_id": "doc-1", "project_id": "project-1", "created_by": "user-1",
            "filename": "requirements.pdf", "format": "pdf", "content_hash": source_hash,
        }
        parsed = DocumentConversionResult(markdown="Rule A", source_hash=source_hash)
        superseded = {**document, "status": "PARSING", "parse_attempt_id": "new-attempt"}
        with (
            patch.object(requirement_documents, "read_raw_requirement_source", new=AsyncMock(return_value=source)),
            patch.object(requirement_documents, "convert_requirement_source", new=AsyncMock(return_value=parsed)),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=superseded)),
            patch.object(requirement_documents, "clear_requirement_conversion_checkpoints", new=AsyncMock()) as cleanup,
        ):
            with self.assertRaisesRegex(RuntimeError, "requirement_parse_attempt_superseded"):
                await requirement_documents.read_and_parse_requirement_source(document, "old-attempt")
        cleanup.assert_not_awaited()

    async def test_obsolete_pdf_checkpoints_are_cleared_when_source_is_no_longer_parsing(self):
        source = b"stable pdf source"
        source_hash = __import__("hashlib").sha256(source).hexdigest()
        document = {
            "_id": "doc-1", "project_id": "project-1", "created_by": "user-1",
            "filename": "requirements.pdf", "format": "pdf", "content_hash": source_hash,
        }
        parsed = DocumentConversionResult(markdown="Rule A", source_hash=source_hash)
        archived = {**document, "status": "ARCHIVED", "parse_attempt_id": None}
        with (
            patch.object(requirement_documents, "read_raw_requirement_source", new=AsyncMock(return_value=source)),
            patch.object(requirement_documents, "convert_requirement_source", new=AsyncMock(return_value=parsed)),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=archived)),
            patch.object(requirement_documents, "clear_requirement_conversion_checkpoints", new=AsyncMock()) as cleanup,
        ):
            with self.assertRaisesRegex(RuntimeError, "requirement_parse_attempt_superseded"):
                await requirement_documents.read_and_parse_requirement_source(document, "old-attempt")

        cleanup.assert_awaited_once_with("doc-1", "project-1", "user-1", source_hash)

    async def test_pdf_hash_mismatch_discards_only_expected_source_checkpoints(self):
        source = b"stable pdf source"
        source_hash = __import__("hashlib").sha256(source).hexdigest()
        document = {
            "_id": "doc-1", "project_id": "project-1", "created_by": "user-1",
            "filename": "requirements.pdf", "format": "pdf", "content_hash": source_hash,
        }
        parsed = DocumentConversionResult(markdown="Wrong snapshot", source_hash="f" * 64)
        with (
            patch.object(requirement_documents, "read_raw_requirement_source", new=AsyncMock(return_value=source)),
            patch.object(requirement_documents, "convert_requirement_source", new=AsyncMock(return_value=parsed)),
            patch.object(requirement_documents, "clear_requirement_conversion_checkpoints", new=AsyncMock()) as cleanup,
        ):
            with self.assertRaisesRegex(RuntimeError, "requirement_source_hash_mismatch"):
                await requirement_documents.read_and_parse_requirement_source(document, "attempt-1")

        cleanup.assert_awaited_once_with("doc-1", "project-1", "user-1", source_hash)

    async def test_docling_blocks_and_unreadable_regions_are_retained(self):
        parsed = DocumentConversionResult(
            markdown="Rule A", page_count=200, parser="docling",
            structure=[{"block_id": "#/texts/2", "parent_block_id": "#/body", "text": "Rule A", "type": "text", "page_no": 19, "locations": [{"page_no": 19, "bbox": {"l": 20, "t": 40}}], "extraction_status": "EXTRACTED"}],
            unprocessed_blocks=[{"block_id": "#/pictures/1", "type": "picture"}],
        )
        with patch.object(requirement_documents, "convert_requirement_source", new=AsyncMock(return_value=parsed)):
            content, details = await requirement_documents.parse_requirement_source(b"pdf", "pdf", "source.pdf")
        self.assertEqual(content, "Rule A")
        self.assertEqual(details["source_structure"][0]["locations"][0]["page_no"], 19)
        self.assertEqual(details["parse_report"]["page_count"], 200)
        self.assertEqual(len(details["parse_report"]["unprocessed_blocks"]), 1)

    async def test_unavailable_converter_does_not_silently_fallback_to_text_only(self):
        with (
            patch.object(requirement_documents, "convert_requirement_source", new=AsyncMock(side_effect=httpx.ConnectError("unavailable"))),
            patch.object(requirement_documents, "extract_file_content") as fallback,
        ):
            with self.assertRaises(httpx.ConnectError):
                await requirement_documents.parse_requirement_source(b"pdf", "pdf", "source.pdf")
        fallback.assert_not_called()

    async def test_text_source_has_no_fabricated_page_or_blocks(self):
        content, details = await requirement_documents.parse_requirement_source(b"Rule A", "txt", "source.txt")
        self.assertEqual(content, "Rule A")
        self.assertIsNone(details["parse_report"]["page_count"])
        self.assertEqual(details["source_structure"], [])

    async def test_source_structure_is_forwarded_to_project_index(self):
        document = {"_id": "doc", "project_id": "project", "normalized_content": "Rule A", "source_version": "2", "content_hash": "sourcehash", "source_structure": [{"block_id": "#/texts/2", "text": "Rule A"}], "parse_report": {"page_count": 200}}
        with (
            patch.object(requirement_documents, "index_artifact", new=AsyncMock(return_value=True)) as index,
            patch.object(requirement_documents.requirement_document_repository, "set_index_result", new=AsyncMock(return_value=SimpleNamespace(matched_count=1))),
        ):
            await requirement_documents.index_requirement_document(document)
        self.assertEqual(index.await_args.kwargs["source_structure"], document["source_structure"])
        self.assertEqual(index.await_args.kwargs["document_id"], "doc")
        self.assertEqual(index.await_args.kwargs["source_version"], "2")

    async def test_stale_revision_reindexes_latest_source_once(self):
        old_document = {
            "_id": "doc",
            "project_id": "project",
            "revision": 4,
            "ai_enabled": True,
            "normalized_content": "Old access metadata",
        }
        current_document = {
            **old_document,
            "revision": 5,
            "visibility": "private",
            "shared_with": [],
            "normalized_content": "Current access metadata",
        }
        with (
            patch.object(requirement_documents, "index_artifact", new=AsyncMock(return_value=True)) as index,
            patch.object(
                requirement_documents.requirement_document_repository,
                "set_index_result",
                new=AsyncMock(
                    side_effect=[
                        SimpleNamespace(matched_count=0),
                        SimpleNamespace(matched_count=1),
                    ]
                ),
            ) as save_status,
            patch.object(
                requirement_documents.requirement_document_repository,
                "find",
                new=AsyncMock(return_value=current_document),
            ) as find,
        ):
            indexed = await requirement_documents.index_requirement_document(old_document)

        self.assertTrue(indexed)
        self.assertEqual(index.await_count, 2)
        self.assertEqual(index.await_args_list[1].kwargs["visibility"], "private")
        self.assertEqual(save_status.await_args_list[0].kwargs["expected_revision"], 4)
        self.assertEqual(save_status.await_args_list[1].kwargs["expected_revision"], 5)
        find.assert_awaited_once_with("doc", "project")

    async def test_stale_revision_is_not_retried_when_document_was_archived(self):
        old_document = {
            "_id": "doc",
            "project_id": "project",
            "revision": 4,
            "ai_enabled": True,
            "normalized_content": "Old source",
        }
        current_document = {**old_document, "revision": 5, "status": "ARCHIVED"}
        with (
            patch.object(requirement_documents, "index_artifact", new=AsyncMock(return_value=True)) as index,
            patch.object(
                requirement_documents.requirement_document_repository,
                "set_index_result",
                new=AsyncMock(return_value=SimpleNamespace(matched_count=0)),
            ) as save_status,
            patch.object(
                requirement_documents.requirement_document_repository,
                "find",
                new=AsyncMock(return_value=current_document),
            ),
            patch.object(requirement_documents, "remove_artifact", new=AsyncMock(return_value=True)) as remove,
        ):
            indexed = await requirement_documents.index_requirement_document(old_document)

        self.assertFalse(indexed)
        index.assert_awaited_once()
        remove.assert_awaited_once_with("project", "doc")
        self.assertEqual(save_status.await_args_list[1].args[2], "NOT_REQUESTED")
        self.assertEqual(save_status.await_args_list[1].kwargs["expected_revision"], 5)


if __name__ == "__main__":
    unittest.main()
