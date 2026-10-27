import asyncio
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

from src.services.chunking import ChunkingService
from src.services.conversion import (
    ConversionService,
    IndexingAttemptSupersededError,
)


def async_values(values):
    async def iterate():
        for value in values:
            yield value

    return iterate()


class DocumentProvenanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_pdf_parse_failure_cleans_partial_image_assets(self):
        service = ConversionService()
        temporary_path = Path("/tmp/veriq-document-parse-failure.docx")
        source_hash = "a" * 64

        async def to_thread(function, *args, **kwargs):
            if function == service._download_to_temporary_file:
                return temporary_path, ".docx", source_hash
            if function == temporary_path.unlink:
                return None
            raise RuntimeError("parser failed after writing image asset")

        with (
            patch("src.services.conversion.asyncio.to_thread", new=to_thread),
            patch.object(
                service,
                "delete_picture_assets",
                new=AsyncMock(return_value=1),
            ) as cleanup,
        ):
            result = await service.parse_document_checkpointed(
                "private/source.docx",
                "private",
                "document-1",
                "project-1",
                "owner-1",
            )

        self.assertEqual(result, {"error": "document_parsing_failed"})
        cleanup.assert_awaited_once_with("project-1", "document-1", source_hash)

    async def test_invalid_pdf_checkpoints_are_discarded_before_one_fresh_parse(self):
        service = ConversionService()
        source_hash = "b" * 64
        parsed_result = {
            "markdown": "freshly parsed source",
            "structure": [],
            "source_sha256": source_hash,
        }
        service._download_to_temporary_file = Mock(
            return_value=(Path("/tmp/veriq-invalid-checkpoint.pdf"), ".pdf", source_hash)
        )
        service._parse_pdf_with_page_checkpoints = AsyncMock(
            side_effect=[
                RuntimeError("document_page_checkpoint_order_invalid"),
                parsed_result,
            ]
        )
        service.clear_document_checkpoints = AsyncMock()
        service.delete_picture_assets = AsyncMock(return_value=1)

        result = await service.parse_document_checkpointed(
            "private/source.pdf",
            "private",
            "document-1",
            "project-1",
            "owner-1",
        )

        self.assertEqual(result, parsed_result)
        service.clear_document_checkpoints.assert_awaited_once_with(
            "document-1", "project-1", "owner-1", source_hash
        )
        service.delete_picture_assets.assert_awaited_once_with(
            "project-1", "document-1", source_hash
        )
        self.assertEqual(service._parse_pdf_with_page_checkpoints.await_count, 2)

    async def test_invalid_pdf_byte_checkpoints_are_discarded_before_one_fresh_parse(self):
        service = ConversionService()
        parsed_result = {"markdown": "freshly parsed upload", "structure": []}
        service._parse_pdf_with_page_checkpoints = AsyncMock(
            side_effect=[
                RuntimeError("document_page_checkpoint_set_incomplete"),
                parsed_result,
            ]
        )
        service.clear_document_checkpoints = AsyncMock()
        service.delete_picture_assets = AsyncMock(return_value=1)

        result = await service.parse_bytes_checkpointed(
            b"%PDF-upload-bytes",
            ".pdf",
            "document-2",
            "project-2",
            "owner-2",
        )

        self.assertEqual(result, parsed_result)
        source_hash = hashlib.sha256(b"%PDF-upload-bytes").hexdigest()
        service.clear_document_checkpoints.assert_awaited_once_with(
            "document-2", "project-2", "owner-2", source_hash
        )
        service.delete_picture_assets.assert_awaited_once_with(
            "project-2", "document-2", source_hash
        )
        self.assertEqual(service._parse_pdf_with_page_checkpoints.await_count, 2)

    def test_picture_cleanup_deletes_in_bounded_object_storage_batches(self):
        service = ConversionService()
        object_pages = [
            {
                "Contents": [
                    {"Key": f"project/p/documents/d/sources/{'a' * 64}/images/{index}.png"}
                    for index in range(750)
                ]
            },
            {
                "Contents": [
                    {"Key": f"project/p/documents/d/sources/{'a' * 64}/images/{index}.png"}
                    for index in range(750, 1501)
                ]
            },
        ]

        class Paginator:
            def paginate(self, **_kwargs):
                return iter(object_pages)

        client = Mock()
        client.get_paginator.return_value = Paginator()
        client.delete_objects = Mock(
            side_effect=lambda **kwargs: {
                "Deleted": kwargs["Delete"]["Objects"]
            }
        )
        with patch.object(service, "_storage_client", return_value=client):
            deleted = service._delete_picture_assets(
                "p", "d", "a" * 64
            )

        self.assertEqual(deleted, 1501)
        self.assertEqual(
            [
                len(call.kwargs["Delete"]["Objects"])
                for call in client.delete_objects.call_args_list
            ],
            [1000, 501],
        )
        self.assertTrue(
            all(
                call.kwargs["Delete"]["Quiet"] is False
                for call in client.delete_objects.call_args_list
            )
        )

    def test_picture_cleanup_reports_object_storage_partial_failure(self):
        service = ConversionService()
        object_page = {
            "Contents": [
                {
                    "Key": (
                        f"project/p/documents/d/sources/{'a' * 64}/images/1.png"
                    )
                }
            ]
        }

        class Paginator:
            def paginate(self, **_kwargs):
                return iter([object_page])

        client = Mock()
        client.get_paginator.return_value = Paginator()
        client.delete_objects.return_value = {
            "Deleted": [],
            "Errors": [{"Code": "AccessDenied"}],
        }
        with patch.object(service, "_storage_client", return_value=client):
            with self.assertRaisesRegex(
                RuntimeError, "document_image_cleanup_incomplete"
            ):
                service._delete_picture_assets("p", "d", "a" * 64)

    def test_ocr_language_is_validated_before_parser_use(self):
        service = ConversionService()

        self.assertEqual(service._resolve_ocr_language("iso:en"), "iso:en")
        with self.assertRaisesRegex(ValueError, "document_ocr_language_invalid"):
            service._resolve_ocr_language("invalid language value")

    def test_ingestion_checkpoint_identity_changes_with_ocr_language(self):
        from src.repositories.document_ingestion_checkpoint import (
            DocumentIngestionCheckpointRepository,
        )

        repository = DocumentIngestionCheckpointRepository()
        common = (
            "document-1",
            "project-1",
            "owner-1",
            "source-hash",
            "docling",
            "1.0",
            ConversionService.CHECKPOINT_CONTRACT_VERSION,
        )

        vietnamese_key = repository._key(*common, "iso:vi", 1)
        english_key = repository._key(*common, "iso:en", 1)

        self.assertNotEqual(vietnamese_key, english_key)

    async def test_checkpoint_index_migration_includes_ocr_language(self):
        from src.core.infrastructure.database import database, setup_indexes

        class Collection:
            def __init__(self):
                self.create_indexes = AsyncMock()
                self.index_information = AsyncMock(
                    return_value={
                        "one_checkpoint_per_document_source_parser_page": {}
                    }
                )
                self.drop_index = AsyncMock()

        class Database:
            def __init__(self):
                self.collections = {}

            def __getitem__(self, name):
                return self.collections.setdefault(name, Collection())

        class Client:
            def __init__(self):
                self.databases = {}

            def __getitem__(self, name):
                return self.databases.setdefault(name, Database())

        client = Client()
        with patch.object(database, "mongodb", client):
            await setup_indexes()

        checkpoint_collection = client.databases[next(iter(client.databases))][
            "document_ingestion_page_checkpoints"
        ]
        models = checkpoint_collection.create_indexes.await_args.args[0]
        checkpoint_index = next(
            model.document
            for model in models
            if model.document.get("name")
            == "one_checkpoint_per_document_source_parser_language_page"
        )
        indexed_fields = list(checkpoint_index["key"])
        self.assertIn("ocr_language", indexed_fields)
        self.assertEqual(
            indexed_fields[-2:], ["ocr_language", "page_no"]
        )
        checkpoint_collection.drop_index.assert_awaited_once_with(
            "one_checkpoint_per_document_source_parser_page"
        )

    def test_text_pdf_fast_path_marks_text_that_was_not_mapped_to_source_blocks(self):

        page = SimpleNamespace(
            get_text=lambda kind, **kwargs: (
                "This requirement has an omitted business obligation."
                if kind == "text"
                else [(0, 0, 100, 20, "This requirement has an omitted.", 0, 0)]
            ),
            find_tables=lambda: SimpleNamespace(tables=[]),
        )

        class Document:
            page_count = 1

            def __getitem__(self, _index):
                return page

            def close(self):
                pass

        with (
            patch("fitz.open", return_value=Document()),
            patch("importlib.metadata.version", return_value="test-version"),
        ):
            result = ConversionService._parse_text_pdf(Path("source.pdf"))

        self.assertIn(
            "PDF_TEXT_NOT_MAPPED_TO_STRUCTURE",
            [item["reason_code"] for item in result["unprocessed_blocks"]],
        )
        self.assertEqual(result["unprocessed_blocks"][0]["unmapped_token_count"], 2)
        self.assertIn(
            "This requirement has an omitted business obligation.", result["markdown"]
        )

    def test_text_backed_pdf_skips_ocr_but_blank_page_keeps_ocr(self):
        import io

        import fitz
        from PIL import Image

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = f"{temporary_directory}/source.pdf"
            document = fitz.open()
            document.new_page().insert_text(
                (72, 72), "A sufficiently long requirement page with extractable source text."
            )
            document.new_page().insert_text(
                (72, 72), "Another sufficiently long requirement page with extractable source text."
            )
            document.save(pdf_path)
            document.close()
            self.assertFalse(ConversionService._pdf_requires_ocr(Path(pdf_path)))

            scanned_path = f"{temporary_directory}/scanned.pdf"
            scanned = fitz.open()
            scanned.new_page()
            scanned.new_page().insert_text((72, 72), "Page number only")
            scanned.save(scanned_path)
            scanned.close()
            self.assertTrue(ConversionService._pdf_requires_ocr(Path(scanned_path)))

            image_buffer = io.BytesIO()
            Image.new("RGB", (20, 20), "white").save(image_buffer, format="PNG")
            mixed_path = f"{temporary_directory}/mixed.pdf"
            mixed = fitz.open()
            mixed_page = mixed.new_page()
            mixed_page.insert_text(
                (72, 72),
                "This page has enough extractable text but also an image that may contain source text.",
            )
            mixed_page.insert_image(mixed_page.rect, stream=image_buffer.getvalue())
            mixed.save(mixed_path)
            mixed.close()
            self.assertTrue(ConversionService._pdf_requires_ocr(Path(mixed_path)))

    def test_plain_text_pdf_fast_path_keeps_page_and_block_provenance(self):
        import fitz

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "plain.pdf"
            document = fitz.open()
            for page_number in range(1, 4):
                document.new_page().insert_text(
                    (72, 72),
                    f"Veriq page marker {page_number:03d} with source text long enough for extraction.",
                )
            document.save(pdf_path)
            document.close()

            result = ConversionService()._parse_file(pdf_path)

        self.assertEqual(result["parser"], "pymupdf_text")
        self.assertFalse(result["ocr_enabled"])
        self.assertEqual(result["page_count"], 3)
        self.assertIn("marker 001", result["markdown"])
        self.assertIn("marker 003", result["markdown"])
        self.assertEqual([block["page_no"] for block in result["structure"]], [1, 2, 3])
        self.assertTrue(all(block["locations"][0]["bbox"] for block in result["structure"]))

    def test_text_pdf_page_range_preserves_original_page_numbers(self):
        import fitz

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "plain.pdf"
            document = fitz.open()
            for page_number in range(1, 4):
                document.new_page().insert_text(
                    (72, 72),
                    f"Veriq page marker {page_number:03d} with source text long enough for extraction.",
                )
            document.save(pdf_path)
            document.close()

            result = ConversionService()._parse_file(
                pdf_path,
                page_range=(2, 2),
                total_page_count=3,
                use_text_pdf_fast_path=True,
            )

        self.assertEqual(result["page_count"], 3)
        self.assertIn("marker 002", result["markdown"])
        self.assertNotIn("marker 001", result["markdown"])
        self.assertNotIn("marker 003", result["markdown"])
        self.assertEqual({block["page_no"] for block in result["structure"]}, {2})

    def test_docling_page_range_is_forwarded_without_losing_total_page_count(self):
        from unittest.mock import Mock

        document = SimpleNamespace(
            export_to_markdown=lambda: "Page three source requirement with a valid source quote.",
            pages={"page-3": object()},
            iterate_items=lambda: iter(()),
        )
        converter = SimpleNamespace(
            convert=Mock(return_value=SimpleNamespace(document=document))
        )
        service = ConversionService()
        service._get_docling = Mock(return_value=converter)
        with (
            patch.object(service, "_can_use_text_pdf_fast_path", return_value=False),
            patch.object(service, "_pdf_requires_ocr", return_value=False),
            patch("importlib.metadata.version", return_value="test-docling"),
        ):
            result = service._parse_file(
                Path("source.pdf"),
                page_range=(3, 3),
                total_page_count=8,
                use_text_pdf_fast_path=False,
            )

        converter.convert.assert_called_once_with("source.pdf", page_range=(3, 3))
        self.assertEqual(result["page_count"], 8)

    def test_ocr_text_with_page_confidence_is_warning_not_unprocessed_content(self):
        from unittest.mock import Mock

        document = SimpleNamespace(
            export_to_markdown=lambda: "Recognized text from the scanned source page.",
            pages={"page-3": object()},
            iterate_items=lambda: iter(()),
        )
        converter = SimpleNamespace(
            convert=Mock(return_value=SimpleNamespace(
                document=document,
                confidence=SimpleNamespace(
                    pages={3: SimpleNamespace(ocr_score=0.72)}
                ),
            ))
        )
        service = ConversionService()
        service._get_docling = Mock(return_value=converter)
        service._extract_structure = Mock(return_value=[{
            "block_id": "#/texts/1",
            "text": "Recognized text from the scanned source page.",
            "type": "text",
            "level": 0,
            "page_no": 3,
            "locations": [{"page_no": 3, "bbox": None}],
            "extraction_status": "EXTRACTED",
        }])

        with patch("importlib.metadata.version", return_value="test-docling"):
            result = service._parse_file(
                Path("source.pdf"),
                page_range=(3, 3),
                total_page_count=8,
                use_text_pdf_fast_path=False,
                ocr_enabled=True,
                ocr_language="iso:vi",
            )

        self.assertIn("Recognized text", result["markdown"])
        self.assertEqual(result["ocr_language"], "iso:vi")
        self.assertIn(
            {
                "block_id": None,
                "type": "ocr_text",
                "page_no": 3,
                "ocr_page_confidence": 0.72,
                    "locations": [],
                "reason_code": "OCR_TEXT_REQUIRES_ACCURACY_VALIDATION",
            },
            result["extraction_warnings"],
        )
        self.assertEqual(result["unprocessed_blocks"], [])

    def test_low_confidence_scanned_page_uses_tesseract_output_and_keeps_accuracy_warning(self):
        from unittest.mock import Mock

        document = SimpleNamespace(
            export_to_markdown=lambda: "Docling OCR with missing Vietnamese accents.",
            pages={"page-3": object()},
            iterate_items=lambda: iter(()),
        )
        converter = SimpleNamespace(convert=Mock(return_value=SimpleNamespace(
            document=document,
            confidence=SimpleNamespace(
                pages={3: SimpleNamespace(ocr_score=0.47)}
            ),
        )))
        service = ConversionService()
        service._get_docling = Mock(return_value=converter)
        service._extract_structure = Mock(return_value=[
            {
                "block_id": "#/texts/3",
                "text": "Docling OCR with missing Vietnamese accents.",
                "type": "text",
                "level": 0,
                "page_no": 3,
                "locations": [{"page_no": 3, "bbox": None}],
                "extraction_status": "EXTRACTED",
            },
            {
                "block_id": "#/pictures/3",
                "text": "Figure caption",
                "type": "picture",
                "level": 0,
                "page_no": 3,
                "locations": [{"page_no": 3, "bbox": None}],
                "extraction_status": "EXTRACTED",
                "image_metadata": {"asset_status": "STORED"},
            },
        ])
        service._tesseract_pdf_fallback = Mock(return_value=(
            "Đăng nhập thành công với tiếng Việt.",
            [{
                "block_id": "tesseract-ocr-page-3",
                "parent_block_id": None,
                "text": "Đăng nhập thành công với tiếng Việt.",
                "type": "ocr_fallback_page_text",
                "level": 0,
                "page_no": 3,
                "locations": [{"page_no": 3}],
                "extraction_status": "EXTRACTED",
            }],
            [{
                "block_id": None,
                "type": "ocr_fallback",
                "page_no": 3,
                "reason_code": "OCR_FALLBACK_ENGINE_USED",
            }],
            [],
        ))

        with patch("importlib.metadata.version", return_value="test-docling"):
            result = service._parse_file(
                Path("source.pdf"),
                page_range=(3, 3),
                total_page_count=8,
                use_text_pdf_fast_path=False,
                ocr_enabled=True,
                ocr_language="iso:vi",
            )

        self.assertEqual(result["markdown"], "Đăng nhập thành công với tiếng Việt.")
        self.assertEqual(
            [block["block_id"] for block in result["structure"]],
            ["#/pictures/3", "tesseract-ocr-page-3"],
        )
        self.assertIn(
            "OCR_TEXT_REQUIRES_ACCURACY_VALIDATION",
            [item["reason_code"] for item in result["extraction_warnings"]],
        )
        self.assertIn(
            "OCR_FALLBACK_LOW_CONFIDENCE",
            [item["reason_code"] for item in result["extraction_warnings"]],
        )
        service._tesseract_pdf_fallback.assert_called_once()

    def test_ocr_page_without_recognized_text_has_page_diagnostic(self):
        from unittest.mock import Mock

        document = SimpleNamespace(
            export_to_markdown=lambda: "",
            pages={"page-3": object()},
            iterate_items=lambda: iter(()),
        )
        converter = SimpleNamespace(
            convert=Mock(return_value=SimpleNamespace(document=document))
        )
        service = ConversionService()
        service._get_docling = Mock(return_value=converter)
        service._extract_structure = Mock(return_value=[])

        with patch("importlib.metadata.version", return_value="test-docling"):
            result = service._parse_file(
                Path("source.pdf"),
                page_range=(3, 3),
                total_page_count=8,
                use_text_pdf_fast_path=False,
                ocr_enabled=True,
                ocr_language="iso:vi",
            )

        self.assertEqual(result["markdown"], "")
        self.assertIn(
            {
                "block_id": None,
                "type": "ocr_text",
                "page_no": 3,
                "ocr_page_confidence": None,
                "locations": [],
                "reason_code": "OCR_NO_TEXT_EXTRACTED",
            },
            result["unprocessed_blocks"],
        )

    def test_multi_page_ocr_diagnostics_keep_each_docling_page_score(self):
        from unittest.mock import Mock

        markdown = "Page one scanned text.\n\nPage two scanned text."
        document = SimpleNamespace(
            export_to_markdown=lambda: markdown,
            pages={"page-1": object(), "page-2": object()},
            iterate_items=lambda: iter(()),
        )
        converter = SimpleNamespace(
            convert=Mock(return_value=SimpleNamespace(
                document=document,
                confidence=SimpleNamespace(pages={
                    1: SimpleNamespace(ocr_score=0.91),
                    2: SimpleNamespace(ocr_score=0.47),
                }),
            ))
        )
        service = ConversionService()
        service._get_docling = Mock(return_value=converter)
        service._extract_structure = Mock(return_value=[
            {
                "block_id": "#/texts/1",
                "text": "Page one scanned text.",
                "type": "text",
                "level": 0,
                "page_no": 1,
                "locations": [],
                "extraction_status": "EXTRACTED",
            },
            {
                "block_id": "#/texts/2",
                "text": "Page two scanned text.",
                "type": "text",
                "level": 0,
                "page_no": 2,
                "locations": [],
                "extraction_status": "EXTRACTED",
            },
        ])

        with patch("importlib.metadata.version", return_value="test-docling"):
            result = service._parse_file(
                Path("source.pdf"),
                use_text_pdf_fast_path=False,
                ocr_enabled=True,
                ocr_language="iso:en",
            )

        self.assertEqual(result["page_count"], 2)
        self.assertEqual(
            [
                (block["page_no"], block["ocr_page_confidence"])
                for block in result["extraction_warnings"]
            ],
            [(1, 0.91), (2, 0.47)],
        )
        self.assertTrue(
            all(
                block["reason_code"] == "OCR_TEXT_REQUIRES_ACCURACY_VALIDATION"
                for block in result["extraction_warnings"]
            )
        )
        self.assertEqual(result["unprocessed_blocks"], [])

    def test_invalid_ocr_page_confidence_is_not_reported_as_a_score(self):
        for invalid_score in (float("nan"), float("inf"), -0.01, 1.01, True, "0.9"):
            with self.subTest(score=invalid_score):
                conversion = SimpleNamespace(
                    confidence=SimpleNamespace(
                        pages={3: SimpleNamespace(ocr_score=invalid_score)}
                    )
                )
                self.assertIsNone(
                    ConversionService._ocr_page_confidence(conversion, 3)
                )

        conversion = SimpleNamespace(
            confidence=SimpleNamespace(pages={3: SimpleNamespace(ocr_score=0.0)})
        )
        self.assertEqual(ConversionService._ocr_page_confidence(conversion, 3), 0.0)

    def test_non_pdf_conversion_does_not_claim_or_configure_pdf_ocr(self):
        from unittest.mock import Mock

        document = SimpleNamespace(
            export_to_markdown=lambda: "A text document with source content.",
            pages={},
            iterate_items=lambda: iter(()),
        )
        converter = SimpleNamespace(
            convert=Mock(return_value=SimpleNamespace(document=document))
        )
        service = ConversionService()
        service._get_docling = Mock(return_value=converter)
        service._extract_structure = Mock(return_value=[{
            "block_id": "#/texts/1",
            "text": "A text document with source content.",
            "type": "text",
            "level": 0,
            "page_no": None,
            "locations": [],
            "extraction_status": "EXTRACTED",
        }])

        with patch("importlib.metadata.version", return_value="test-docling"):
            result = service._parse_file(Path("source.docx"), ocr_language="iso:en")

        service._get_docling.assert_called_once_with(do_ocr=False, ocr_language=None)
        self.assertFalse(result["ocr_enabled"])
        self.assertIsNone(result["ocr_language"])

    async def test_checkpointed_pdf_reuses_completed_pages_and_parses_only_missing_pages(self):
        from datetime import datetime, timezone

        import fitz

        from src.schemas.document_ingestion_checkpoint import DocumentIngestionPageCheckpoint

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "checkpointed.pdf"
            document = fitz.open()
            for page_number in range(1, 3):
                document.new_page().insert_text(
                    (72, 72),
                    f"Veriq page marker {page_number:03d} with source text long enough for extraction.",
                )
            document.save(pdf_path)
            document.close()

            cached_page = DocumentIngestionPageCheckpoint(
                document_id="document-1",
                project_id="project-1",
                owner_id="owner-1",
                source_hash="source-hash",
                parser_name="pymupdf_text",
                parser_version="test-version",
                parser_contract_version=ConversionService.CHECKPOINT_CONTRACT_VERSION,
                page_no=1,
                page_count=2,
                markdown="Previously parsed page one source text.",
                structure=[
                    {
                        "block_id": "#/pages/1/blocks/0",
                        "parent_block_id": "#/pages/1",
                        "text": "Previously parsed page one source text.",
                        "type": "text",
                        "level": 0,
                        "page_no": 1,
                        "locations": [],
                        "extraction_status": "EXTRACTED",
                    }
                ],
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc),
            )
            checkpoint_repository = SimpleNamespace(
                iter_pages=Mock(return_value=async_values([cached_page])),
                save_page=AsyncMock(),
            )
            service = ConversionService()
            authorization_check = AsyncMock()
            progress_callback = AsyncMock()
            with (
                patch.object(service, "_can_use_text_pdf_fast_path", return_value=True),
                patch("importlib.metadata.version", return_value="test-version"),
                patch(
                    "src.repositories.document_ingestion_checkpoint.document_ingestion_checkpoint_repository",
                    checkpoint_repository,
                ),
            ):
                result = await service._parse_pdf_with_page_checkpoints(
                    pdf_path,
                    "source-hash",
                    "document-1",
                    "project-1",
                    "owner-1",
                    authorization_check,
                    progress_callback,
                )

        self.assertIn("Previously parsed page one", result["markdown"])
        self.assertIn("marker 002", result["markdown"])
        self.assertNotIn("marker 001", result["markdown"])
        self.assertEqual({block["page_no"] for block in result["structure"]}, {1, 2})
        self.assertEqual(authorization_check.await_count, 4)
        self.assertEqual(
            progress_callback.await_args_list,
            [call(1, 2, 0), call(2, 2, 0)],
        )
        checkpoint_repository.save_page.assert_awaited_once()
        saved_page = checkpoint_repository.save_page.await_args.args[0]
        self.assertEqual(saved_page.page_no, 2)

    async def test_checkpointed_pdf_reports_missing_page_location_without_dropping_text(self):
        import fitz

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "missing-source-location.pdf"
            document = fitz.open()
            document.new_page().insert_text(
                (72, 72),
                "A readable page contains enough source text to index without losing its content.",
            )
            document.save(pdf_path)
            document.close()

            checkpoint_repository = SimpleNamespace(
                iter_pages=Mock(return_value=async_values([])),
                save_page=AsyncMock(),
            )
            service = ConversionService()
            with (
                patch.object(service, "_can_use_text_pdf_fast_path", return_value=False),
                patch.object(service, "_pdf_requires_ocr", return_value=False),
                patch("importlib.metadata.version", return_value="test-docling"),
                patch.object(
                    service,
                    "_parse_file",
                    return_value={
                        "markdown": "Readable extracted source text remains available.",
                        "structure": [
                            {
                                "block_id": "#/texts/1",
                                "text": "Readable extracted source text remains available.",
                                "type": "text",
                                "page_no": None,
                                "locations": [],
                                "extraction_status": "EXTRACTED",
                            }
                        ],
                        "unprocessed_blocks": [],
                        "extraction_warnings": [],
                        "ocr_enabled": False,
                    },
                ),
                patch(
                    "src.repositories.document_ingestion_checkpoint.document_ingestion_checkpoint_repository",
                    checkpoint_repository,
                ),
            ):
                result = await service._parse_pdf_with_page_checkpoints(
                    pdf_path,
                    "source-hash",
                    "document-1",
                    "project-1",
                    "owner-1",
                    None,
                )

        self.assertIn(
            "Readable extracted source text remains available", result["markdown"]
        )
        self.assertIsNone(result["structure"][0]["page_no"])
        self.assertEqual(
            result["unprocessed_blocks"][0]["reason_code"],
            "SOURCE_PAGE_LOCATION_MISSING",
        )
        self.assertEqual(result["unprocessed_blocks"][0]["page_no"], 1)
        checkpoint_repository.save_page.assert_awaited_once()
        saved_page = checkpoint_repository.save_page.await_args.args[0]
        self.assertEqual(saved_page.markdown, result["markdown"])
        self.assertEqual(
            saved_page.unprocessed_blocks[0]["reason_code"],
            "SOURCE_PAGE_LOCATION_MISSING",
        )

    async def test_checkpointed_pdf_rejects_checkpoint_from_different_page_count(self):
        from datetime import datetime, timezone

        from src.schemas.document_ingestion_checkpoint import DocumentIngestionPageCheckpoint

        now = datetime.now(timezone.utc)
        cached_page = DocumentIngestionPageCheckpoint(
            document_id="document-1",
            project_id="project-1",
            owner_id="owner-1",
            source_hash="source-hash",
            parser_name="pymupdf_text",
            parser_version="test-version",
            parser_contract_version=ConversionService.CHECKPOINT_CONTRACT_VERSION,
            page_no=1,
            page_count=3,
            markdown="Stale checkpoint page.",
            created_at=now,
            expires_at=now,
        )
        checkpoint_repository = SimpleNamespace(
            iter_pages=Mock(return_value=async_values([cached_page])),
            save_page=AsyncMock(),
        )
        service = ConversionService()
        with (
            patch.object(service, "_pdf_page_count", return_value=2),
            patch.object(service, "_can_use_text_pdf_fast_path", return_value=True),
            patch("importlib.metadata.version", return_value="test-version"),
            patch(
                "src.repositories.document_ingestion_checkpoint.document_ingestion_checkpoint_repository",
                checkpoint_repository,
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "document_page_checkpoint_page_count_mismatch"
            ):
                await service._parse_pdf_with_page_checkpoints(
                    Path("source.pdf"),
                    "source-hash",
                    "document-1",
                    "project-1",
                    "owner-1",
                    AsyncMock(),
                )

        checkpoint_repository.save_page.assert_not_awaited()

    async def test_revoked_source_during_page_parse_is_not_checkpointed(self):
        import fitz

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "revoked-during-parse.pdf"
            document = fitz.open()
            document.new_page().insert_text(
                (72, 72),
                "Authorized source text remains available while the page is parsed.",
            )
            document.save(pdf_path)
            document.close()

            checkpoint_repository = SimpleNamespace(
                iter_pages=Mock(return_value=async_values([])),
                save_page=AsyncMock(),
            )
            authorization_check = AsyncMock(
                side_effect=[None, PermissionError("document_access_revoked")]
            )
            service = ConversionService()
            with (
                patch.object(service, "_can_use_text_pdf_fast_path", return_value=True),
                patch("importlib.metadata.version", return_value="test-version"),
                patch.object(
                    service,
                    "_parse_file",
                    return_value={
                        "markdown": "Extracted page content",
                        "structure": [],
                        "unprocessed_blocks": [],
                        "ocr_enabled": False,
                    },
                ),
                patch(
                    "src.repositories.document_ingestion_checkpoint.document_ingestion_checkpoint_repository",
                    checkpoint_repository,
                ),
            ):
                with self.assertRaisesRegex(PermissionError, "document_access_revoked"):
                    await service._parse_pdf_with_page_checkpoints(
                        pdf_path,
                        "source-hash",
                        "document-1",
                        "project-1",
                        "owner-1",
                        authorization_check,
                    )

        checkpoint_repository.save_page.assert_not_awaited()

    async def test_revoked_non_pdf_source_after_parse_is_not_returned(self):
        service = ConversionService()
        service._download_to_temporary_file = Mock(
            return_value=(Path("source.txt"), ".txt", "source-hash")
        )
        service._parse_file = Mock(return_value={"markdown": "parsed source"})
        authorization_check = AsyncMock(
            side_effect=[None, PermissionError("document_access_revoked")]
        )

        with self.assertRaisesRegex(PermissionError, "document_access_revoked"):
            await service.parse_document_checkpointed(
                "private/source.txt",
                "private",
                "document-1",
                "project-1",
                "owner-1",
                authorization_check=authorization_check,
            )

        service._parse_file.assert_called_once()
        self.assertEqual(authorization_check.await_count, 2)

    async def test_revoked_source_clears_only_its_checkpoint_snapshot(self):
        import hashlib

        source_bytes = b"authorized document snapshot"
        service = ConversionService()
        service._download_to_temporary_file = Mock(
            return_value=(Path("source.pdf"), ".pdf", hashlib.sha256(source_bytes).hexdigest())
        )
        service._parse_pdf_with_page_checkpoints = AsyncMock(
            side_effect=PermissionError("document_source_changed_during_ingestion")
        )
        service.clear_document_checkpoints = AsyncMock()

        with self.assertRaises(PermissionError):
            await service.parse_document_checkpointed(
                "private/object.pdf",
                "private",
                "document-1",
                "project-1",
                "owner-1",
            )

        service.clear_document_checkpoints.assert_awaited_once_with(
            "document-1",
            "project-1",
            "owner-1",
            hashlib.sha256(source_bytes).hexdigest(),
        )

    async def test_superseded_pdf_attempt_preserves_shared_checkpoints_and_assets(self):
        source_hash = "c" * 64
        service = ConversionService()
        service._download_to_temporary_file = Mock(
            return_value=(Path("/tmp/veriq-superseded.pdf"), ".pdf", source_hash)
        )
        service._parse_pdf_with_page_checkpoints = AsyncMock(
            side_effect=IndexingAttemptSupersededError(
                "document_indexing_attempt_superseded"
            )
        )
        service.clear_document_checkpoints = AsyncMock()
        service.delete_picture_assets = AsyncMock(return_value=1)

        with self.assertRaisesRegex(
            IndexingAttemptSupersededError, "document_indexing_attempt_superseded"
        ):
            await service.parse_document_checkpointed(
                "private/source.pdf",
                "private",
                "document-1",
                "project-1",
                "owner-1",
            )

        service.clear_document_checkpoints.assert_not_awaited()
        service.delete_picture_assets.assert_not_awaited()

    async def test_superseded_non_pdf_attempt_preserves_shared_image_assets(self):
        source_hash = "d" * 64
        service = ConversionService()
        service._download_to_temporary_file = Mock(
            return_value=(Path("/tmp/veriq-superseded.docx"), ".docx", source_hash)
        )
        service._parse_file = Mock(return_value={"markdown": "parsed source"})
        service.delete_picture_assets = AsyncMock(return_value=1)

        async def authorization_check():
            raise IndexingAttemptSupersededError(
                "document_indexing_attempt_superseded"
            )

        with self.assertRaisesRegex(
            IndexingAttemptSupersededError, "document_indexing_attempt_superseded"
        ):
            await service.parse_document_checkpointed(
                "private/source.docx",
                "private",
                "document-1",
                "project-1",
                "owner-1",
                authorization_check=authorization_check,
            )

        service._parse_file.assert_not_called()
        service.delete_picture_assets.assert_not_awaited()

    async def test_ocr_page_without_extracted_text_is_reported_and_checkpointed(self):
        import fitz

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "mixed.pdf"
            document = fitz.open()
            document.new_page().insert_text(
                (72, 72),
                "This readable page contains enough text for parser selection and indexing.",
            )
            document.new_page()
            document.save(pdf_path)
            document.close()

            def parse_page(_path, page_range, page_count, _fast_path, _ocr_enabled, _ocr_language, _image_context):
                page_no = page_range[0]
                if page_no == 1:
                    return {
                        "markdown": "Readable page text with an observable requirement.",
                        "structure": [{
                            "block_id": "#/pages/1/blocks/0",
                            "parent_block_id": "#/pages/1",
                            "text": "Readable page text with an observable requirement.",
                            "type": "text",
                            "level": 0,
                            "page_no": 1,
                            "locations": [{"page_no": 1, "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10}}],
                            "extraction_status": "EXTRACTED",
                        }],
                        "page_count": page_count,
                        "ocr_enabled": True,
                        "unprocessed_blocks": [],
                    }
                return {
                    "markdown": "",
                    "structure": [{
                        "block_id": "#/pages/2/pictures/0",
                        "parent_block_id": "#/pages/2",
                        "text": "",
                        "type": "picture",
                        "level": 0,
                        "page_no": 2,
                        "locations": [{"page_no": 2, "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10}}],
                        "extraction_status": "NO_TEXT_EXTRACTED",
                    }],
                    "page_count": page_count,
                    "ocr_enabled": True,
                    "unprocessed_blocks": [{
                        "block_id": "#/pages/2/pictures/0",
                        "type": "picture",
                        "reason_code": "OCR_TEXT_NOT_EXTRACTED",
                        "page_no": 2,
                        "locations": [{"page_no": 2, "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10}}],
                    }],
                }

            checkpoint_repository = SimpleNamespace(
                iter_pages=Mock(return_value=async_values([])),
                save_page=AsyncMock(),
            )
            service = ConversionService()
            with (
                patch.object(service, "_can_use_text_pdf_fast_path", return_value=False),
                patch.object(service, "_pdf_requires_ocr", return_value=True),
                patch.object(service, "_parse_file", side_effect=parse_page),
                patch("importlib.metadata.version", return_value="test-docling"),
                patch(
                    "src.repositories.document_ingestion_checkpoint.document_ingestion_checkpoint_repository",
                    checkpoint_repository,
                ),
            ):
                result = await service._parse_pdf_with_page_checkpoints(
                    pdf_path,
                    "source-hash",
                    "document-1",
                    "project-1",
                    "owner-1",
                    None,
                )

        self.assertIn("Readable page text", result["markdown"])
        self.assertEqual(result["page_count"], 2)
        self.assertEqual(result["unprocessed_blocks"][0]["page_no"], 2)
        self.assertEqual(checkpoint_repository.save_page.await_count, 2)
        saved_pages = [
            call.args[0]
            for call in checkpoint_repository.save_page.await_args_list
        ]
        unreadable_page = next(page for page in saved_pages if page.page_no == 2)
        self.assertEqual(unreadable_page.markdown, "")
        self.assertEqual(unreadable_page.unprocessed_blocks[0]["page_no"], 2)

    async def test_two_hundred_page_pdf_keeps_every_page_through_chunking(self):
        import fitz

        service = ChunkingService(min_chars=80, target_chars=180, max_chars=320)
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "long-source.pdf"
            document = fitz.open()
            for page_number in range(1, 201):
                page = document.new_page()
                page.insert_text(
                    (72, 72),
                    f"Veriq source page {page_number:03d}: a distinct documented rule "
                    "with sufficient extractable content for parser selection.",
                )
            document.save(pdf_path)
            document.close()

            parsed = await asyncio.to_thread(ConversionService()._parse_file, pdf_path)
            with patch(
                "src.services.chunking.embedder.embed_batch",
                new=AsyncMock(side_effect=RuntimeError("embedding unavailable in unit fixture")),
            ):
                chunks = await service.chunk_document(
                    parsed["markdown"],
                    {"document_id": "long-source", "source_version": "v1"},
                    parsed["structure"],
                )

        self.assertEqual(parsed["page_count"], 200)
        self.assertEqual(
            [block["page_no"] for block in parsed["structure"]],
            list(range(1, 201)),
        )
        self.assertIn("source page 001", parsed["markdown"])
        self.assertIn("source page 200", parsed["markdown"])

        spans = [span for chunk in chunks for span in chunk["metadata"]["source_spans"]]
        self.assertEqual(len(spans), 200)
        self.assertEqual(
            sorted({page for chunk in chunks for page in chunk["metadata"]["page_numbers"]}),
            list(range(1, 201)),
        )
        self.assertTrue(
            all(
                span["locations"]
                and span["locations"][0]["page_no"] == span["block_index"] + 1
                for span in spans
            )
        )

    async def test_chunking_streams_size_guard_groups_into_serialization(self):
        service = ChunkingService(min_chars=20, target_chars=40, max_chars=80)
        structure = [
            {
                "block_id": "block-1",
                "type": "paragraph",
                "text": "The source contains a testable business rule.",
                "page_no": 1,
                "locations": [{"page_no": 1, "bbox": None}],
            }
        ]
        with (
            patch(
                "src.services.chunking.embedder.embed_batch",
                new=AsyncMock(side_effect=RuntimeError("embedding unavailable")),
            ),
            patch.object(
                service, "_serialize_groups", wraps=service._serialize_groups
            ) as serialize_groups,
        ):
            chunks = await service.chunk_document(
                structure[0]["text"], {"document_id": "doc-1"}, structure
            )

        self.assertTrue(chunks)
        self.assertFalse(isinstance(serialize_groups.call_args.args[0], list))

    def test_text_pdf_table_fast_path_keeps_rows_and_table_location(self):
        import fitz

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "table.pdf"
            document = fitz.open()
            page = document.new_page()
            x_positions = [72, 240, 390, 540]
            y_start = 100
            row_height = 70
            rows = [
                ["Requirement", "Rule", "Expected"],
                ["REQ-LOGIN", "Five failed attempts lock account", "Locked"],
                ["REQ-RESET", "Token expires after fifteen minutes", "Rejected"],
            ]
            for x_position in x_positions:
                page.draw_line(
                    (x_position, y_start),
                    (x_position, y_start + row_height * len(rows)),
                )
            for row_index in range(len(rows) + 1):
                page.draw_line(
                    (72, y_start + row_index * row_height),
                    (540, y_start + row_index * row_height),
                )
            for row_index, row in enumerate(rows):
                for column_index, cell in enumerate(row):
                    page.insert_text(
                        (x_positions[column_index] + 5, y_start + row_index * row_height + 25),
                        cell,
                        fontsize=9,
                    )
            page.insert_text((72, 360), "Additional requirement text outside the table.")
            document.save(pdf_path)
            document.close()

            result = ConversionService()._parse_file(pdf_path)

        table_blocks = [block for block in result["structure"] if block["type"] == "table"]
        self.assertEqual(result["parser"], "pymupdf_text")
        self.assertEqual(len(table_blocks), 1)
        self.assertIn("REQ-LOGIN", table_blocks[0]["text"])
        self.assertIn("REQ-RESET", table_blocks[0]["text"])
        self.assertEqual(table_blocks[0]["locations"][0]["page_no"], 1)
        self.assertEqual(table_blocks[0]["table_metadata"]["row_count"], 3)
        self.assertEqual(table_blocks[0]["table_metadata"]["column_count"], 3)
        self.assertEqual(
            table_blocks[0]["table_metadata"]["column_headers"],
            ["Requirement", "Rule", "Expected"],
        )
        self.assertIn("Additional requirement text", result["markdown"])
        self.assertNotIn("Five failed attempts", " ".join(
            block["text"] for block in result["structure"] if block["type"] == "text"
        ))

    async def test_repeated_text_on_different_pages_retains_both_source_blocks(self):
        service = ChunkingService(min_chars=10, target_chars=30, max_chars=80)
        text = "Quy tắc thanh toán được áp dụng."
        structure = [
            {"block_id": f"#/texts/{index}", "text": text, "type": "text", "page_no": index + 1}
            for index in range(2)
        ]
        with patch("src.services.chunking.embedder.embed_batch", new=AsyncMock(side_effect=RuntimeError)):
            chunks = await service.chunk_document(text, {"document_id": "doc", "source_version": "v1"}, structure)
        spans = [span for chunk in chunks for span in chunk["metadata"]["source_spans"]]
        self.assertEqual([span["block_id"] for span in spans], ["#/texts/0", "#/texts/1"])
        self.assertEqual({page for chunk in chunks for page in chunk["metadata"]["page_numbers"]}, {1, 2})

    async def test_chunker_consumes_typed_source_blocks_without_materializing_dict_list(self):
        service = ChunkingService(min_chars=10, target_chars=30, max_chars=80)
        structure = [
            SimpleNamespace(
                model_dump=Mock(
                    return_value={
                        "block_id": "#/texts/0",
                        "text": "Quy tắc có nguồn dẫn.",
                        "type": "text",
                        "page_no": 3,
                    }
                )
            )
        ]
        with patch(
            "src.services.chunking.embedder.embed_batch",
            new=AsyncMock(side_effect=RuntimeError("semantic refinement unavailable")),
        ):
            chunks = await service.chunk_document(
                "Quy tắc có nguồn dẫn.",
                {"document_id": "doc", "source_version": "v1"},
                structure,
            )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["metadata"]["page_numbers"], [3])
        structure[0].model_dump.assert_called_once_with(exclude_none=True)

    async def test_chunk_metadata_preserves_table_and_image_source_details(self):
        service = ChunkingService(min_chars=1, target_chars=20, max_chars=100)
        table_metadata = {
            "table_id": "table-1",
            "row_count": 3,
            "column_count": 2,
            "column_headers": ["Rule", "Result"],
        }
        image_metadata = {"image_id": "image-1", "extracted_text_present": False}
        structure = [
            {
                "block_id": "table-1",
                "parent_block_id": "page-2",
                "text": "Rule A Result B",
                "type": "table",
                "page_no": 2,
                "table_metadata": table_metadata,
            },
            {
                "block_id": "image-1",
                "parent_block_id": "page-2",
                "text": "Figure",
                "type": "picture",
                "page_no": 2,
                "image_metadata": image_metadata,
            },
        ]
        with patch("src.services.chunking.embedder.embed_batch", new=AsyncMock(side_effect=RuntimeError)):
            chunks = await service.chunk_document(
                "Rule A Result B\n\nFigure",
                {"document_id": "doc-1"},
                structure,
            )

        spans = [span for chunk in chunks for span in chunk["metadata"]["source_spans"]]
        by_block = {span["block_id"]: span for span in spans}
        self.assertTrue(
            all(
                by_block["table-1"]["table_metadata"].get(key) == value
                for key, value in table_metadata.items()
            )
        )
        self.assertEqual(by_block["image-1"]["image_metadata"], image_metadata)

    async def test_split_chunks_point_to_exact_source_substrings(self):
        service = ChunkingService(min_chars=10, target_chars=25, max_chars=45)
        text = "Quy tắc A.\n\n  Quy tắc B với dữ liệu khác. " + "Dữ liệu rất dài " * 15
        structure = [{"block_id": "#/texts/0", "text": text, "type": "text", "page_no": 12}]
        source = text.strip()
        with patch("src.services.chunking.embedder.embed_batch", new=AsyncMock(side_effect=RuntimeError)):
            chunks = await service.chunk_document(text, {"document_id": "doc"}, structure)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk["text"]), 45)
            self.assertEqual(chunk["metadata"]["page_numbers"], [12])
            for span in chunk["metadata"]["source_spans"]:
                self.assertEqual(
                    chunk["text"][span["chunk_start"]:span["chunk_end"]],
                    source[span["source_start"]:span["source_end"]],
                )

    def test_converter_preserves_multi_page_table_and_unreadable_picture(self):
        table = SimpleNamespace(
            label="table", text="incomplete table text", self_ref="#/tables/0",
            parent=SimpleNamespace(cref="#/body"),
            prov=[SimpleNamespace(page_no=1, bbox=None), SimpleNamespace(page_no=2, bbox=None)],
            export_to_markdown=lambda doc: "| Code | Result |\n| A | Accepted |",
        )
        picture = SimpleNamespace(label="picture", text="", self_ref="#/pictures/0", prov=[])
        document = SimpleNamespace(iterate_items=lambda: iter([(table, 1), (picture, 1)]))
        blocks = ConversionService()._extract_structure(document)
        self.assertEqual(len(blocks), 2)
        self.assertIn("Accepted", blocks[0]["text"])
        self.assertEqual([value["page_no"] for value in blocks[0]["locations"]], [1, 2])
        self.assertEqual(blocks[0]["table_metadata"]["column_headers"], ["Code", "Result"])
        self.assertEqual(blocks[0]["table_metadata"]["row_count"], 2)
        self.assertEqual(blocks[0]["table_metadata"]["metadata_source"], "docling_markdown")
        self.assertEqual(blocks[1]["extraction_status"], "NO_TEXT_EXTRACTED")
        self.assertEqual(blocks[1]["locations"], [])

    def test_unreadable_picture_has_actionable_reason_and_exact_source_location(self):
        text = SimpleNamespace(
            label="text",
            text="The system authenticates the user before opening the workspace.",
            self_ref="#/texts/0",
            parent=SimpleNamespace(cref="#/body"),
            prov=[SimpleNamespace(page_no=1, bbox=None)],
        )
        picture = SimpleNamespace(
            label="picture",
            text="",
            self_ref="#/pictures/0",
            parent=SimpleNamespace(cref="#/body"),
            prov=[SimpleNamespace(
                page_no=2,
                bbox={"l": 12, "t": 24, "r": 128, "b": 96},
            )],
        )
        document = SimpleNamespace(
            export_to_markdown=lambda: text.text,
            pages={1: object(), 2: object()},
            iterate_items=lambda: iter([(text, 0), (picture, 1)]),
        )
        converter = SimpleNamespace(
            convert=lambda _path: SimpleNamespace(document=document)
        )
        service = ConversionService()

        with (
            patch.object(service, "_can_use_text_pdf_fast_path", return_value=False),
            patch.object(service, "_pdf_requires_ocr", return_value=False),
            patch.object(service, "_get_docling", return_value=converter),
            patch("importlib.metadata.version", return_value="test-version"),
        ):
            result = service._parse_file(Path("source.pdf"))

        picture_issue = next(
            item for item in result["unprocessed_blocks"]
            if item["block_id"] == "#/pictures/0"
        )
        self.assertEqual(picture_issue["reason_code"], "PICTURE_TEXT_NOT_EXTRACTED")
        self.assertEqual(picture_issue["page_no"], 2)
        self.assertEqual(
            picture_issue["locations"][0]["bbox"],
            {"l": 12, "t": 24, "r": 128, "b": 96},
        )

    def test_converter_indexes_picture_caption_with_its_source_location(self):
        picture = SimpleNamespace(
            label="picture",
            text="",
            self_ref="#/pictures/1",
            parent=SimpleNamespace(cref="#/body"),
            prov=[SimpleNamespace(page_no=4, bbox={"l": 10, "t": 20, "r": 30, "b": 40})],
            caption_text=lambda _document: "Figure 2. Login request and response sequence",
        )
        document = SimpleNamespace(iterate_items=lambda: iter([(picture, 1)]))

        blocks = ConversionService()._extract_structure(document)

        self.assertEqual(blocks[0]["type"], "picture")
        self.assertEqual(
            blocks[0]["text"],
            "Figure 2. Login request and response sequence",
        )
        self.assertEqual(blocks[0]["extraction_status"], "EXTRACTED")
        self.assertEqual(blocks[0]["locations"][0]["page_no"], 4)
        self.assertEqual(
            blocks[0]["locations"][0]["bbox"],
            {"l": 10, "t": 20, "r": 30, "b": 40},
        )
        self.assertEqual(blocks[0]["block_id"], "#/pictures/1")

    def test_docling_structure_failure_is_reported_as_unprocessed(self):
        document = SimpleNamespace(
            export_to_markdown=lambda: "Readable markdown fallback",
            pages={1: object()},
        )
        converter = SimpleNamespace(convert=lambda _path: SimpleNamespace(document=document))
        service = ConversionService()
        with (
            patch.object(service, "_can_use_text_pdf_fast_path", return_value=False),
            patch.object(service, "_pdf_requires_ocr", return_value=False),
            patch.object(service, "_get_docling", return_value=converter),
            patch.object(
                service,
                "_extract_structure",
                side_effect=RuntimeError("private parser detail"),
            ),
        ):
            result = service._parse_file(Path("source.pdf"))

        self.assertEqual(result["markdown"], "Readable markdown fallback")
        self.assertEqual(result["structure"], [])
        self.assertEqual(
            result["unprocessed_blocks"],
            [{
                "block_id": None,
                "type": "document_structure",
                "reason_code": "STRUCTURE_EXTRACTION_FAILED",
                "locations": [],
            }],
        )

    def test_empty_structure_export_with_markdown_is_reported_as_unprocessed(self):
        document = SimpleNamespace(
            export_to_markdown=lambda: "Readable markdown without block provenance",
            pages={1: object()},
            iterate_items=lambda: iter([]),
        )
        converter = SimpleNamespace(convert=lambda _path: SimpleNamespace(document=document))
        service = ConversionService()
        with (
            patch.object(service, "_can_use_text_pdf_fast_path", return_value=False),
            patch.object(service, "_pdf_requires_ocr", return_value=False),
            patch.object(service, "_get_docling", return_value=converter),
            patch("importlib.metadata.version", return_value="test-version"),
        ):
            result = service._parse_file(Path("source.pdf"))

        self.assertEqual(result["markdown"], "Readable markdown without block provenance")
        self.assertEqual(result["structure"], [])
        self.assertIn(
            "STRUCTURE_EXTRACTION_EMPTY",
            [item["reason_code"] for item in result["unprocessed_blocks"]],
        )

    def test_empty_markdown_export_uses_extracted_blocks_but_marks_degraded(self):
        block = SimpleNamespace(
            label="text",
            text="A requirement recovered from the structured document block.",
            self_ref="#/texts/3",
            parent=SimpleNamespace(cref="#/body"),
            prov=[SimpleNamespace(page_no=7, bbox=None)],
        )
        document = SimpleNamespace(
            export_to_markdown=lambda: "  ",
            pages={7: object()},
            iterate_items=lambda: iter([(block, 0)]),
        )
        converter = SimpleNamespace(convert=lambda _path: SimpleNamespace(document=document))
        service = ConversionService()
        with (
            patch.object(service, "_can_use_text_pdf_fast_path", return_value=False),
            patch.object(service, "_pdf_requires_ocr", return_value=False),
            patch.object(service, "_get_docling", return_value=converter),
            patch("importlib.metadata.version", return_value="test-version"),
        ):
            result = service._parse_file(Path("source.pdf"))

        self.assertEqual(
            result["markdown"],
            "A requirement recovered from the structured document block.",
        )
        self.assertEqual(result["structure"][0]["page_no"], 7)
        self.assertIn(
            "MARKDOWN_EXPORT_EMPTY",
            [item["reason_code"] for item in result["unprocessed_blocks"]],
        )

    def test_partial_structure_falls_back_to_complete_markdown_without_fake_locations(self):
        markdown = "The login requires a valid account and a verified email address."
        extracted_item = SimpleNamespace(
            label="text",
            text="The login requires a valid account.",
            self_ref="#/texts/0",
            parent=SimpleNamespace(cref="#/body"),
            prov=[SimpleNamespace(page_no=1, bbox=None)],
        )
        document = SimpleNamespace(
            export_to_markdown=lambda: markdown,
            pages={1: object()},
            iterate_items=lambda: iter([(extracted_item, 0)]),
        )
        converter = SimpleNamespace(convert=lambda _path: SimpleNamespace(document=document))
        service = ConversionService()
        with (
            patch.object(service, "_can_use_text_pdf_fast_path", return_value=False),
            patch.object(service, "_pdf_requires_ocr", return_value=False),
            patch.object(service, "_get_docling", return_value=converter),
        ):
            result = service._parse_file(Path("source.pdf"))

        self.assertEqual(result["markdown"], markdown)
        self.assertEqual(result["structure"][0]["text"], markdown)
        self.assertIsNone(result["structure"][0]["block_id"])
        self.assertEqual(result["structure"][0]["locations"], [])
        self.assertIn(
            "MARKDOWN_TEXT_NOT_MAPPED_TO_STRUCTURE",
            [item["reason_code"] for item in result["unprocessed_blocks"]],
        )


if __name__ == "__main__":
    unittest.main()
