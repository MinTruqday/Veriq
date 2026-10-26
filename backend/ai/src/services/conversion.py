import asyncio
import hashlib
import io
import math
import os
import re
import tempfile
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from src.core.infrastructure.configuration import settings
from src.services.table_spans import markdown_table_metadata


class ConversionService:
    CHECKPOINT_CONTRACT_VERSION = 5
    OCR_LANGUAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_-]{0,31}$")
    MINIMUM_EXTRACTABLE_PAGE_TEXT = 32

    def __init__(self):
        self._storage_endpoint = settings.OBJECT_STORAGE_ENDPOINT.rstrip("/")
        self._storage_private_bucket = settings.OBJECT_STORAGE_PRIVATE_BUCKET
        self._storage_public_bucket = settings.OBJECT_STORAGE_PUBLIC_BUCKET
        self._storage_access_key = settings.OBJECT_STORAGE_ACCESS_KEY
        self._storage_secret_key = settings.OBJECT_STORAGE_SECRET_KEY
        self._storage_region = settings.OBJECT_STORAGE_REGION
        self._ocr_language = settings.DOCUMENT_OCR_LANGUAGE
        self._docling = {}
        logger.info("Docling document conversion service initialized")

    def _resolve_bucket(self, object_key: str, visibility: str) -> str:
        if visibility in ("private", "restricted"):
            return self._storage_private_bucket
        return self._storage_public_bucket

    def _resolve_ocr_language(self, language: str | None) -> str:
        resolved = str(language or self._ocr_language).strip()
        if not self.OCR_LANGUAGE_PATTERN.fullmatch(resolved):
            raise ValueError("document_ocr_language_invalid")
        return resolved

    @staticmethod
    def _ocr_page_confidences(conversion) -> dict[int, float]:
        confidence_report = getattr(conversion, "confidence", None)
        page_scores = getattr(confidence_report, "pages", None)
        if not isinstance(page_scores, Mapping):
            return {}
        scores = {}
        for raw_page_no, page_score in page_scores.items():
            if isinstance(raw_page_no, bool):
                continue
            if isinstance(raw_page_no, int):
                page_no = raw_page_no
            elif isinstance(raw_page_no, str) and raw_page_no.isdigit():
                page_no = int(raw_page_no)
            else:
                continue
            raw_score = getattr(page_score, "ocr_score", None)
            if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
                continue
            score = float(raw_score)
            if page_no > 0 and math.isfinite(score) and 0 <= score <= 1:
                scores[page_no] = score
        return scores

    @classmethod
    def _ocr_page_confidence(cls, conversion, page_no: int | None) -> float | None:
        if page_no is None:
            return None
        return cls._ocr_page_confidences(conversion).get(page_no)

    def _storage_client(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=self._storage_endpoint,
            aws_access_key_id=self._storage_access_key,
            aws_secret_access_key=self._storage_secret_key,
            region_name=self._storage_region,
        )

    async def storage_ready(self) -> bool:
        client = self._storage_client()
        await asyncio.to_thread(client.head_bucket, Bucket=self._storage_private_bucket)
        return True

    def _delete_picture_assets(
        self,
        project_id: str,
        document_id: str,
        source_hash: str | None = None,
    ) -> int:
        if not project_id or not document_id or "/" in project_id or "/" in document_id:
            raise ValueError("document_image_cleanup_scope_invalid")
        if source_hash is not None and not re.fullmatch(r"[0-9a-f]{64}", source_hash):
            raise ValueError("document_image_cleanup_source_invalid")
        client = self._storage_client()
        source_prefix = f"sources/{source_hash}/" if source_hash else "sources/"
        prefix = f"project/{project_id}/documents/{document_id}/{source_prefix}"
        paginator = client.get_paginator("list_objects_v2")
        deleted_count = 0
        pending_keys = []
        for page in paginator.paginate(
            Bucket=self._storage_private_bucket,
            Prefix=prefix,
        ):
            for item in page.get("Contents", []):
                key = item.get("Key", "")
                if "/images/" not in key:
                    continue
                pending_keys.append({"Key": key})
                if len(pending_keys) == 1000:
                    client.delete_objects(
                        Bucket=self._storage_private_bucket,
                        Delete={"Objects": pending_keys, "Quiet": True},
                    )
                    deleted_count += len(pending_keys)
                    pending_keys = []
        if pending_keys:
            client.delete_objects(
                Bucket=self._storage_private_bucket,
                Delete={"Objects": pending_keys, "Quiet": True},
            )
            deleted_count += len(pending_keys)
        return deleted_count

    async def delete_picture_assets(
        self,
        project_id: str,
        document_id: str,
        source_hash: str | None = None,
    ) -> int:
        return await asyncio.to_thread(
            self._delete_picture_assets,
            project_id,
            document_id,
            source_hash,
        )

    def _read_picture_asset(
        self,
        project_id: str,
        document_id: str,
        asset_key: str,
    ) -> tuple[bytes, str]:
        if not project_id or not document_id or "/" in project_id or "/" in document_id:
            raise ValueError("document_image_read_scope_invalid")
        prefix = f"project/{project_id}/documents/{document_id}/sources/"
        match = re.fullmatch(
            re.escape(prefix)
            + r"[0-9a-f]{64}/images/[0-9a-f]{64}-(?P<image_hash>[0-9a-f]{64})\.png",
            asset_key,
        )
        if not match:
            raise ValueError("document_image_asset_reference_invalid")
        result = self._storage_client().get_object(
            Bucket=self._storage_private_bucket,
            Key=asset_key,
        )
        content_type = str(result.get("ContentType") or "")
        if content_type != "image/png":
            raise ValueError("document_image_asset_type_invalid")
        body = result["Body"]
        try:
            content = body.read()
        finally:
            body.close()
        if not content:
            raise ValueError("document_image_asset_empty")
        if hashlib.sha256(content).hexdigest() != match.group("image_hash"):
            raise ValueError("document_image_asset_hash_mismatch")
        return content, content_type

    async def read_picture_asset(
        self,
        project_id: str,
        document_id: str,
        asset_key: str,
    ) -> tuple[bytes, str]:
        return await asyncio.to_thread(
            self._read_picture_asset,
            project_id,
            document_id,
            asset_key,
        )

    def _get_docling(self, do_ocr: bool = True, ocr_language: str | None = None):
        language = self._resolve_ocr_language(ocr_language)
        cache_key = (do_ocr, language if do_ocr else "")
        if cache_key not in self._docling:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption

            pdf_options = PdfPipelineOptions()
            pdf_options.do_ocr = do_ocr
            pdf_options.do_table_structure = True
            if do_ocr:
                hf_home = Path(os.environ["HF_HOME"])
                rapidocr_cache = hf_home / "rapidocr"
                rapidocr_cache.mkdir(parents=True, exist_ok=True)
                pdf_options.ocr_options = RapidOcrOptions(
                    lang=[language],
                    backend="onnxruntime",
                    rapidocr_params={"Global.model_root_dir": rapidocr_cache},
                )
            self._docling[cache_key] = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}
            )
            logger.info(
                "Docling document converter loaded ocr_enabled={} ocr_language={}",
                do_ocr,
                language if do_ocr else None,
            )
        return self._docling[cache_key]

    @classmethod
    def _pdf_requires_ocr(cls, file_path: Path) -> bool:
        try:
            import fitz

            document = fitz.open(file_path)
            if not document.page_count:
                return True
            return any(
                len(" ".join(page.get_text("text").split())) < cls.MINIMUM_EXTRACTABLE_PAGE_TEXT
                or page.get_images(full=True)
                for page in document
            )
        except Exception as error:
            logger.warning("PDF text preflight failed; keeping OCR enabled ({})", type(error).__name__)
            return True
        finally:
            if "document" in locals():
                document.close()

    @staticmethod
    def _pdf_page_count(file_path: Path) -> int:
        import fitz

        document = fitz.open(file_path)
        try:
            return document.page_count
        finally:
            document.close()

    @classmethod
    def _can_use_text_pdf_fast_path(cls, file_path: Path) -> bool:
        try:
            import fitz

            document = fitz.open(file_path)
            if not document.page_count:
                return False
            for page in document:
                text = " ".join(page.get_text("text").split())
                if len(text) < cls.MINIMUM_EXTRACTABLE_PAGE_TEXT or page.get_images(full=True):
                    return False
                drawings = page.get_drawings()
                if drawings:
                    table_bounds = [table.bbox for table in page.find_tables().tables]
                    if not table_bounds or any(
                        not any(
                            bounds[0] - 1 <= drawing["rect"].x0 <= bounds[2] + 1
                            and bounds[0] - 1 <= drawing["rect"].x1 <= bounds[2] + 1
                            and bounds[1] - 1 <= drawing["rect"].y0 <= bounds[3] + 1
                            and bounds[1] - 1 <= drawing["rect"].y1 <= bounds[3] + 1
                            for bounds in table_bounds
                        )
                        for drawing in drawings
                    ):
                        return False
            return True
        except Exception as error:
            logger.warning("PDF fast-path inspection failed; using Docling ({})", type(error).__name__)
            return False
        finally:
            if "document" in locals():
                document.close()

    @staticmethod
    def _parse_text_pdf(
        file_path: Path,
        page_range: tuple[int, int] | None = None,
    ) -> Dict:
        from importlib.metadata import version

        import fitz

        document = fitz.open(file_path)
        try:
            structure = []
            page_markdown = []
            unprocessed_blocks = []
            extraction_warnings = []
            source_token_counts = Counter()
            structured_token_counts = Counter()
            first_page, last_page = page_range or (1, document.page_count)
            if first_page < 1 or last_page < first_page or last_page > document.page_count:
                raise ValueError("invalid_pdf_page_range")
            for page_no in range(first_page, last_page + 1):
                page = document[page_no - 1]
                source_token_counts.update(
                    ConversionService._text_tokens(page.get_text("text") or "")
                )
                page_entries = []
                tables = page.find_tables().tables
                table_bounds = []
                for table_index, table in enumerate(tables):
                    x0, y0, x1, y1 = (float(value) for value in table.bbox)
                    table_bounds.append(table.bbox)
                    rows = table.extract()
                    table_text = "\n".join(
                        [
                            "| " + " | ".join(str(cell or "").replace("|", "\\|").replace("\n", " ") for cell in row) + " |"
                            for row in rows[:1]
                        ]
                        + (["| " + " | ".join("---" for _ in rows[0]) + " |"] if rows and rows[0] else [])
                        + [
                            "| " + " | ".join(str(cell or "").replace("|", "\\|").replace("\n", " ") for cell in row) + " |"
                            for row in rows[1:]
                        ]
                    )
                    table_block_id = f"#/pages/{page_no}/tables/{table_index}"
                    locations = [{
                        "page_no": page_no,
                        "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                    }]
                    structure.append({
                        "block_id": table_block_id,
                        "parent_block_id": f"#/pages/{page_no}",
                        "text": table_text,
                        "type": "table",
                        "level": 0,
                        "page_no": page_no,
                        "locations": locations,
                        "extraction_status": "EXTRACTED" if table_text else "NO_TEXT_EXTRACTED",
                        "table_metadata": markdown_table_metadata(
                            table_text, table_block_id, "pymupdf_table"
                        ),
                    })
                    structured_token_counts.update(
                        ConversionService._text_tokens(table_text)
                    )
                    if not table_text:
                        unprocessed_blocks.append({
                            "block_id": table_block_id,
                            "type": "table",
                            "reason_code": "TABLE_TEXT_NOT_EXTRACTED",
                            "locations": locations,
                        })
                    page_entries.append((y0, table_text))
                for block_index, block in enumerate(page.get_text("blocks", sort=True)):
                    if len(block) < 7 or block[6] != 0:
                        continue
                    text = str(block[4] or "").strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = (float(value) for value in block[:4])
                    center_x, center_y = (x0 + x1) / 2, (y0 + y1) / 2
                    if any(
                        bounds[0] <= center_x <= bounds[2]
                        and bounds[1] <= center_y <= bounds[3]
                        for bounds in table_bounds
                    ):
                        continue
                    locations = [{
                        "page_no": page_no,
                        "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                    }]
                    structure.append({
                        "block_id": f"#/pages/{page_no}/blocks/{block_index}",
                        "parent_block_id": f"#/pages/{page_no}",
                        "text": text,
                        "type": "text",
                        "level": 0,
                        "page_no": page_no,
                        "locations": locations,
                        "extraction_status": "EXTRACTED",
                    })
                    structured_token_counts.update(ConversionService._text_tokens(text))
                    page_entries.append((y0, text))
                page_markdown.append("\n\n".join(text for _, text in sorted(page_entries, key=lambda item: item[0])))
            missing_tokens = sorted(
                (source_token_counts - structured_token_counts).elements()
            )
            if missing_tokens:
                source_document = fitz.open(file_path)
                try:
                    page_markdown = [
                        source_document[page_no - 1].get_text("text") or ""
                        for page_no in range(first_page, last_page + 1)
                    ]
                finally:
                    source_document.close()
                unprocessed_blocks.append({
                    "block_id": None,
                    "type": "document_structure",
                    "reason_code": "PDF_TEXT_NOT_MAPPED_TO_STRUCTURE",
                    "locations": [],
                    "unmapped_token_count": len(missing_tokens),
                })
            return {
                "markdown": "\n\n".join(text for text in page_markdown if text),
                "structure": structure,
                "page_count": document.page_count,
                "parser": "pymupdf_text",
                "parser_version": version("PyMuPDF"),
                "ocr_enabled": False,
                "unprocessed_blocks": unprocessed_blocks,
                "extraction_warnings": extraction_warnings,
            }
        finally:
            document.close()

    @staticmethod
    def _markdown_table_metadata(table_id: str | None, markdown: str) -> Dict:
        return markdown_table_metadata(markdown, table_id, "docling_markdown")

    def _store_picture_asset(
        self,
        item,
        document,
        project_id: str,
        document_id: str,
        source_hash: str,
    ) -> Dict | None:
        get_image = getattr(item, "get_image", None)
        image = get_image(document) if callable(get_image) else None
        if image is None:
            return None
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        image_bytes = buffer.getvalue()
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        block_ref = str(getattr(item, "self_ref", "") or "")
        block_hash = hashlib.sha256(block_ref.encode("utf-8")).hexdigest()
        object_key = (
            f"project/{project_id}/documents/{document_id}/sources/{source_hash}/"
            f"images/{block_hash}-{image_hash}.png"
        )
        self._storage_client().put_object(
            Bucket=self._storage_private_bucket,
            Key=object_key,
            Body=image_bytes,
            ContentType="image/png",
            Metadata={
                "project-id": project_id,
                "document-id": document_id,
                "source-hash": source_hash,
                "image-sha256": image_hash,
            },
        )
        return {
            "asset_key": object_key,
            "content_type": "image/png",
            "content_sha256": image_hash,
            "width": int(image.width),
            "height": int(image.height),
        }

    def _extract_structure(
        self,
        document,
        image_asset_context: Dict | None = None,
    ) -> List[Dict]:
        structure = []
        for item, level in document.iterate_items():
            label = getattr(item, "label", type(item).__name__)
            label = getattr(label, "value", str(label))
            text = str(getattr(item, "text", "") or "").strip()
            if label == "table" and hasattr(item, "export_to_markdown"):
                text = str(item.export_to_markdown(doc=document) or "").strip()
            elif label in {"picture", "image"} and not text:
                caption_text = getattr(item, "caption_text", None)
                if callable(caption_text):
                    text = str(caption_text(document) or "").strip()
            provenance = getattr(item, "prov", None) or []
            page_no = getattr(provenance[0], "page_no", None) if provenance else None
            locations = []
            for location in provenance:
                bbox = getattr(location, "bbox", None)
                if hasattr(bbox, "model_dump"):
                    bbox_value = bbox.model_dump(mode="json")
                elif isinstance(bbox, Mapping):
                    bbox_value = dict(bbox)
                else:
                    bbox_value = None
                locations.append({
                    "page_no": getattr(location, "page_no", None),
                    "bbox": bbox_value,
                })
            parent = getattr(item, "parent", None)
            image_asset = None
            image_asset_status = "NOT_REQUESTED"
            if label in {"picture", "image"} and image_asset_context:
                try:
                    image_asset = self._store_picture_asset(
                        item,
                        document,
                        str(image_asset_context["project_id"]),
                        str(image_asset_context["document_id"]),
                        str(image_asset_context["source_hash"]),
                    )
                    image_asset_status = "STORED" if image_asset else "UNAVAILABLE"
                except Exception as error:
                    image_asset_status = "FAILED"
                    logger.warning(
                        "Document image asset extraction failed block={} error={}",
                        getattr(item, "self_ref", None),
                        type(error).__name__,
                    )
            structure.append({
                "block_id": getattr(item, "self_ref", None),
                "parent_block_id": getattr(parent, "cref", None),
                "text": text, "type": label, "level": int(level),
                "page_no": page_no, "locations": locations,
                "extraction_status": "EXTRACTED" if text else "NO_TEXT_EXTRACTED",
                "table_metadata": (
                    ConversionService._markdown_table_metadata(
                        getattr(item, "self_ref", None), text
                    )
                    if label == "table"
                    else None
                ),
                "image_metadata": (
                    {
                        "image_id": getattr(item, "self_ref", None),
                        "extracted_text_present": bool(text),
                        "asset_available": image_asset is not None,
                        "asset_status": image_asset_status,
                        **(image_asset or {}),
                    }
                    if label in {"picture", "image"}
                    else None
                ),
            })
        return structure

    @staticmethod
    def _text_tokens(value: str) -> Counter:
        return Counter(
            token.casefold()
            for token in re.findall(r"[^\W_]+", value, flags=re.UNICODE)
            if len(token) >= 3 or token.isdigit()
        )

    @staticmethod
    def _unmapped_markdown_tokens(markdown: str, structure: List[Dict]) -> list[str]:
        markdown_tokens = ConversionService._text_tokens(markdown)
        structured_tokens = ConversionService._text_tokens(
            "\n".join(str(item.get("text") or "") for item in structure)
        )
        missing = markdown_tokens - structured_tokens
        return sorted(missing.elements())

    def _parse_file(
        self,
        file_path: Path,
        page_range: tuple[int, int] | None = None,
        total_page_count: int | None = None,
        use_text_pdf_fast_path: bool | None = None,
        ocr_enabled: bool | None = None,
        ocr_language: str | None = None,
        image_asset_context: Dict | None = None,
    ) -> Dict:
        if file_path.suffix.lower() == ".pdf" and (
            self._can_use_text_pdf_fast_path(file_path)
            if use_text_pdf_fast_path is None
            else use_text_pdf_fast_path
        ):
            return self._parse_text_pdf(file_path, page_range)
        is_pdf = file_path.suffix.lower() == ".pdf"
        if ocr_enabled is None:
            ocr_enabled = self._pdf_requires_ocr(file_path) if is_pdf else False
        elif not is_pdf:
            ocr_enabled = False
        convert_options = {"page_range": page_range} if page_range is not None else {}
        language = self._resolve_ocr_language(ocr_language) if ocr_enabled else None
        conversion = self._get_docling(
            do_ocr=ocr_enabled, ocr_language=language
        ).convert(
            str(file_path), **convert_options
        )
        document = conversion.document
        markdown = str(document.export_to_markdown() or "")
        page_count = total_page_count or (
            len(document.pages) if getattr(document, "pages", None) else None
        )
        unprocessed_blocks = []
        extraction_warnings = []
        try:
            structure = self._extract_structure(document, image_asset_context)
            if ocr_enabled:
                page_confidences = self._ocr_page_confidences(conversion)
                for block in structure:
                    page_no = block.get("page_no")
                    if isinstance(page_no, int) and not isinstance(page_no, bool):
                        block["ocr_page_confidence"] = page_confidences.get(page_no)
                    image_metadata = block.get("image_metadata")
                    if isinstance(image_metadata, dict):
                        image_metadata["page_ocr_confidence"] = block.get(
                            "ocr_page_confidence"
                        )
        except Exception as error:
            logger.warning(
                "Docling structure extraction failed; chunking will use Markdown ({})",
                type(error).__name__,
            )
            structure = []
            unprocessed_blocks.append({
                "block_id": None,
                "type": "document_structure",
                "reason_code": "STRUCTURE_EXTRACTION_FAILED",
                "locations": [],
            })

        if markdown.strip() and not structure and not any(
            item.get("reason_code") == "STRUCTURE_EXTRACTION_FAILED"
            for item in unprocessed_blocks
        ):
            unprocessed_blocks.append({
                "block_id": None,
                "type": "document_structure",
                "reason_code": "STRUCTURE_EXTRACTION_EMPTY",
                "locations": [],
            })

        unmapped_tokens = self._unmapped_markdown_tokens(markdown, structure) if structure else []
        if unmapped_tokens:
            structure = [{
                "block_id": None,
                "parent_block_id": None,
                "text": markdown,
                "type": "document_text_fallback",
                "level": 0,
                "page_no": None,
                "locations": [],
                "extraction_status": "EXTRACTED",
            }]
            unprocessed_blocks.append({
                "block_id": None,
                "type": "document_structure",
                "reason_code": "MARKDOWN_TEXT_NOT_MAPPED_TO_STRUCTURE",
                "locations": [],
                "unmapped_token_count": len(unmapped_tokens),
            })

        if not markdown.strip() and structure:
            structured_text = [str(item.get("text") or "").strip() for item in structure]
            structured_text = [text for text in structured_text if text]
            if structured_text:
                markdown = "\n\n".join(structured_text)
                unprocessed_blocks.append({
                    "block_id": None,
                    "type": "document_structure",
                    "reason_code": "MARKDOWN_EXPORT_EMPTY",
                    "locations": [],
                })

        if ocr_enabled:
            page_no = (
                page_range[0]
                if page_range is not None and page_range[0] == page_range[1]
                else None
            )
            if markdown.strip():
                page_confidences = self._ocr_page_confidences(conversion)
                diagnostics = (
                    [
                        (confidence_page, page_confidences[confidence_page])
                        for confidence_page in sorted(page_confidences)
                    ]
                    if page_no is None and page_confidences
                    else [(page_no, page_confidences.get(page_no))]
                )
                extraction_warnings.extend(
                    {
                        "block_id": None,
                        "type": "ocr_text",
                        "page_no": confidence_page,
                        "ocr_page_confidence": confidence,
                        "locations": [],
                        "reason_code": "OCR_TEXT_REQUIRES_ACCURACY_VALIDATION",
                    }
                    for confidence_page, confidence in diagnostics
                )
            elif not any(
                item.get("extraction_status") != "EXTRACTED" for item in structure
            ):
                unprocessed_blocks.append({
                    "block_id": None,
                    "type": "ocr_text",
                    "page_no": page_no,
                    "ocr_page_confidence": self._ocr_page_confidence(
                        conversion, page_no
                    ),
                    "locations": [],
                    "reason_code": "OCR_NO_TEXT_EXTRACTED",
                })

        from importlib.metadata import version

        return {
            "markdown": markdown, "structure": structure, "page_count": page_count,
            "parser": "docling", "parser_version": version("docling"),
            "ocr_enabled": ocr_enabled,
            "ocr_language": language if ocr_enabled else None,
            "unprocessed_blocks": unprocessed_blocks + [
                {
                    "block_id": item["block_id"],
                    "type": item["type"],
                    "page_no": item.get("page_no"),
                    "locations": item["locations"],
                    "reason_code": (
                        "PICTURE_TEXT_NOT_EXTRACTED"
                        if str(item.get("type") or "").casefold() in {"picture", "image"}
                        else "TABLE_TEXT_NOT_EXTRACTED"
                        if str(item.get("type") or "").casefold() == "table"
                        else "DOCUMENT_BLOCK_TEXT_NOT_EXTRACTED"
                    ),
                }
                for item in structure if item["extraction_status"] != "EXTRACTED"
            ] + [
                {
                    "block_id": item["block_id"],
                    "type": item["type"],
                    "page_no": item.get("page_no"),
                    "locations": item["locations"],
                    "reason_code": (
                        "PICTURE_ASSET_STORE_FAILED"
                        if (item.get("image_metadata") or {}).get("asset_status") == "FAILED"
                        else "PICTURE_ASSET_UNAVAILABLE"
                    ),
                }
                for item in structure
                if (item.get("image_metadata") or {}).get("asset_status")
                in {"FAILED", "UNAVAILABLE"}
            ],
            "extraction_warnings": extraction_warnings,
        }

    async def parse_document(self, file_url: str, visibility: str = "public") -> Dict:
        file_bytes, file_ext = await self._download_from_object_storage(
            file_url, visibility=visibility
        )
        if not file_bytes:
            return {"error": "File load failed"}

        return await self.parse_bytes(file_bytes, file_ext)

    async def parse_document_checkpointed(
        self,
        file_url: str,
        visibility: str,
        document_id: str,
        project_id: str,
        owner_id: str,
        authorization_check=None,
        progress_callback=None,
        ocr_language: str | None = None,
    ) -> Dict:
        temporary_path, file_ext, source_hash = await asyncio.to_thread(
            self._download_to_temporary_file,
            file_url, visibility=visibility
        )
        if temporary_path is None:
            return {"error": "File load failed"}
        normalized_ext = file_ext.lower() if file_ext.startswith(".") else f".{file_ext.lower()}"
        try:
            if normalized_ext != ".pdf":
                try:
                    if authorization_check:
                        await authorization_check()
                    result = await asyncio.to_thread(
                        self._parse_file,
                        temporary_path,
                        ocr_language=ocr_language,
                        image_asset_context={
                            "document_id": document_id,
                            "project_id": project_id,
                            "source_hash": source_hash,
                        },
                    )
                    if authorization_check:
                        await authorization_check()
                except PermissionError:
                    try:
                        await self.delete_picture_assets(
                            project_id, document_id, source_hash
                        )
                    except Exception:
                        logger.exception(
                            "Revoked document image assets retained for cleanup document_id={}",
                            document_id,
                        )
                    raise
                except Exception:
                    logger.exception("Docling document conversion failed")
                    result = {"error": "document_parsing_failed"}
                if not result.get("error"):
                    result["source_sha256"] = source_hash
                return result
            try:
                return await self._parse_pdf_with_page_checkpoints(
                    temporary_path,
                    source_hash,
                    document_id,
                    project_id,
                    owner_id,
                    authorization_check,
                    progress_callback,
                    ocr_language,
                )
            except PermissionError:
                await self.clear_document_checkpoints(
                    document_id, project_id, owner_id, source_hash
                )
                try:
                    await self.delete_picture_assets(
                        project_id, document_id, source_hash
                    )
                except Exception:
                    logger.exception(
                        "Revoked document image assets retained for cleanup document_id={}",
                        document_id,
                    )
                raise
            except Exception:
                logger.exception(
                    "Checkpointed PDF parsing failed document_id={}", document_id
                )
                raise
        finally:
            await asyncio.to_thread(temporary_path.unlink, missing_ok=True)

    async def parse_bytes_checkpointed(
        self,
        file_bytes: bytes,
        file_ext: str,
        document_id: str,
        project_id: str,
        owner_id: str,
        ocr_language: str | None = None,
    ) -> Dict:
        normalized_ext = file_ext.lower() if file_ext.startswith(".") else f".{file_ext.lower()}"
        if normalized_ext != ".pdf":
            return await self.parse_bytes(
                file_bytes,
                normalized_ext,
                ocr_language=ocr_language,
                document_id=document_id,
                project_id=project_id,
            )
        if not file_bytes:
            return {"error": "File load failed"}
        source_hash = hashlib.sha256(file_bytes).hexdigest()
        with tempfile.NamedTemporaryFile(suffix=normalized_ext, delete=False) as temporary:
            temporary.write(file_bytes)
            temporary_path = Path(temporary.name)
        try:
            return await self._parse_pdf_with_page_checkpoints(
                temporary_path,
                source_hash,
                document_id,
                project_id,
                owner_id,
                authorization_check=None,
                progress_callback=None,
                ocr_language=ocr_language,
            )
        finally:
            await asyncio.to_thread(temporary_path.unlink, missing_ok=True)

    async def _parse_pdf_with_page_checkpoints(
        self,
        file_path: Path,
        source_hash: str,
        document_id: str,
        project_id: str,
        owner_id: str,
        authorization_check,
        progress_callback=None,
        ocr_language: str | None = None,
    ) -> Dict:
        from importlib.metadata import version

        from src.repositories.document_ingestion_checkpoint import (
            document_ingestion_checkpoint_repository,
        )
        from src.schemas.document_ingestion_checkpoint import DocumentIngestionPageCheckpoint

        page_count = await asyncio.to_thread(self._pdf_page_count, file_path)
        if page_count < 1:
            raise ValueError("document_pdf_has_no_pages")
        use_text_fast_path = await asyncio.to_thread(
            self._can_use_text_pdf_fast_path, file_path
        )
        ocr_enabled = False if use_text_fast_path else await asyncio.to_thread(
            self._pdf_requires_ocr, file_path
        )
        ocr_language = (
            self._resolve_ocr_language(ocr_language) if ocr_enabled else ""
        )
        parser_name = "pymupdf_text" if use_text_fast_path else "docling"
        parser_version = version("PyMuPDF" if use_text_fast_path else "docling")
        cached_pages = document_ingestion_checkpoint_repository.iter_pages(
            document_id,
            project_id,
            owner_id,
            source_hash,
            parser_name,
            parser_version,
            self.CHECKPOINT_CONTRACT_VERSION,
            ocr_language,
        )
        cached_page = await anext(cached_pages, None)
        processed_page_count = 0
        markdown_buffer = io.StringIO()
        has_markdown = False
        structure = []
        unprocessed_blocks = []
        extraction_warnings = []
        unprocessed_page_count = 0
        for page_no in range(1, page_count + 1):
            result = None
            page_markdown = None
            page_structure = None
            page_unprocessed_blocks = None
            if authorization_check:
                await authorization_check()
            if cached_page and cached_page.page_count != page_count:
                raise RuntimeError("document_page_checkpoint_page_count_mismatch")
            if cached_page and cached_page.page_no < page_no:
                raise RuntimeError("document_page_checkpoint_order_invalid")
            if cached_page and cached_page.page_no == page_no:
                checkpoint = cached_page
                cached_page = await anext(cached_pages, None)
            else:
                result = await asyncio.to_thread(
                    self._parse_file,
                    file_path,
                    (page_no, page_no),
                    page_count,
                    use_text_fast_path,
                    ocr_enabled,
                    ocr_language,
                    {
                        "document_id": document_id,
                        "project_id": project_id,
                        "source_hash": source_hash,
                    },
                )
                if authorization_check:
                    await authorization_check()
                if result.get("error"):
                    raise RuntimeError(f"document_page_parse_failed:{page_no}")
                page_markdown = str(result.get("markdown") or "")
                page_unprocessed_blocks = list(result.get("unprocessed_blocks") or [])
                page_structure = list(result.get("structure") or [])
                for block in page_structure:
                    if not isinstance(block, dict) or not str(
                        block.get("text") or ""
                    ).strip():
                        continue
                    locations = block.get("locations")
                    has_page_location = isinstance(locations, list) and any(
                        isinstance(location, dict)
                        and location.get("page_no") == page_no
                        for location in locations
                    )
                    if has_page_location:
                        continue
                    page_unprocessed_blocks.append(
                        {
                            "block_id": block.get("block_id"),
                            "type": str(block.get("type") or "document_block"),
                            "page_no": page_no,
                            "reported_page_no": block.get("page_no"),
                            "locations": locations if isinstance(locations, list) else [],
                            "reason_code": "SOURCE_PAGE_LOCATION_MISSING",
                        }
                    )
                if not page_markdown.strip() and not page_unprocessed_blocks:
                    page_unprocessed_blocks.append(
                        {
                            "block_id": None,
                            "type": "document_page",
                            "reason_code": "PAGE_TEXT_NOT_EXTRACTED",
                            "page_no": page_no,
                            "locations": [],
                        }
                    )
                now = datetime.now(timezone.utc)
                checkpoint = DocumentIngestionPageCheckpoint(
                    document_id=document_id,
                    project_id=project_id,
                    owner_id=owner_id,
                    source_hash=source_hash,
                    parser_name=parser_name,
                    parser_version=parser_version,
                    parser_contract_version=self.CHECKPOINT_CONTRACT_VERSION,
                    ocr_language=ocr_language,
                    page_no=page_no,
                    page_count=page_count,
                    markdown=page_markdown,
                    structure=page_structure,
                    unprocessed_blocks=page_unprocessed_blocks,
                    extraction_warnings=list(result.get("extraction_warnings") or []),
                    ocr_enabled=bool(result.get("ocr_enabled", ocr_enabled)),
                    created_at=now,
                    expires_at=now,
                )
                await document_ingestion_checkpoint_repository.save_page(checkpoint)
            if checkpoint.markdown.strip():
                if has_markdown:
                    markdown_buffer.write("\n\n")
                markdown_buffer.write(checkpoint.markdown)
                has_markdown = True
            structure.extend(checkpoint.structure)
            unprocessed_blocks.extend(checkpoint.unprocessed_blocks)
            extraction_warnings.extend(checkpoint.extraction_warnings)
            if checkpoint.unprocessed_blocks:
                unprocessed_page_count += 1
            processed_page_count += 1
            if progress_callback:
                await progress_callback(page_no, page_count, unprocessed_page_count)
            checkpoint = None
            result = None
            page_markdown = None
            page_structure = None
            page_unprocessed_blocks = None

        if processed_page_count != page_count or cached_page is not None:
            raise RuntimeError("document_page_checkpoint_set_incomplete")
        if authorization_check:
            await authorization_check()
        markdown = markdown_buffer.getvalue()
        markdown_buffer.close()
        unmapped_tokens = self._unmapped_markdown_tokens(markdown, structure) if structure else []
        if unmapped_tokens:
            structure = [{
                "block_id": None,
                "parent_block_id": None,
                "text": markdown,
                "type": "document_text_fallback",
                "level": 0,
                "page_no": None,
                "locations": [],
                "extraction_status": "EXTRACTED",
            }]
            unprocessed_blocks.append({
                "block_id": None,
                "type": "document_structure",
                "reason_code": "MARKDOWN_TEXT_NOT_MAPPED_TO_STRUCTURE",
                "locations": [],
                "unmapped_token_count": len(unmapped_tokens),
            })
        if not markdown.strip() and structure:
            markdown = "\n\n".join(
                str(block.get("text") or "").strip()
                for block in structure
                if str(block.get("text") or "").strip()
            )
            unprocessed_blocks.append({
                "block_id": None,
                "type": "document_structure",
                "reason_code": "MARKDOWN_EXPORT_EMPTY",
                "locations": [],
            })
        if not markdown.strip():
            raise RuntimeError("document_pdf_no_extractable_text")
        return {
            "markdown": markdown,
            "structure": structure,
            "page_count": page_count,
            "parser": parser_name,
            "parser_version": parser_version,
            "ocr_enabled": ocr_enabled,
            "ocr_language": ocr_language or None,
            "unprocessed_blocks": unprocessed_blocks,
            "extraction_warnings": extraction_warnings,
            "source_sha256": source_hash,
        }

    async def clear_document_checkpoints(
        self, document_id: str, project_id: str, owner_id: str, source_hash: str
    ) -> None:
        from src.repositories.document_ingestion_checkpoint import (
            document_ingestion_checkpoint_repository,
        )

        await document_ingestion_checkpoint_repository.delete_source_version(
            document_id, project_id, owner_id, source_hash
        )

    async def parse_bytes(
        self,
        file_bytes: bytes,
        file_ext: str = ".pdf",
        page_range: tuple[int, int] | None = None,
        ocr_language: str | None = None,
        document_id: str | None = None,
        project_id: str | None = None,
    ) -> Dict:
        normalized_ext = file_ext.lower() if file_ext.startswith(".") else f".{file_ext.lower()}"
        if not normalized_ext[1:].isalnum():
            normalized_ext = ".pdf"

        with tempfile.NamedTemporaryFile(suffix=normalized_ext, delete=False) as temporary:
            temporary.write(file_bytes)
            temporary_path = Path(temporary.name)

        try:
            if page_range is not None and normalized_ext != ".pdf":
                raise ValueError("page_range_requires_pdf")
            total_page_count = (
                await asyncio.to_thread(self._pdf_page_count, temporary_path)
                if page_range is not None
                else None
            )
            parsed = await asyncio.to_thread(
                self._parse_file,
                temporary_path,
                page_range,
                total_page_count,
                ocr_language=ocr_language,
                image_asset_context=(
                    {
                        "document_id": document_id,
                        "project_id": project_id,
                        "source_hash": hashlib.sha256(file_bytes).hexdigest(),
                    }
                    if document_id and project_id
                    else None
                ),
            )
            if not parsed.get("error"):
                parsed["source_sha256"] = hashlib.sha256(file_bytes).hexdigest()
            return parsed
        except Exception:
            logger.exception("Docling document conversion failed")
            return {"error": "document_parsing_failed"}
        finally:
            await asyncio.to_thread(temporary_path.unlink, missing_ok=True)

    async def get_markdown(self, file_url: str, visibility: str = "private") -> str:
        parse_result = await self.parse_document(file_url, visibility=visibility)
        return parse_result.get("markdown", "")

    async def _download_from_object_storage(
        self, file_url: str, visibility: str = "public"
    ) -> tuple[Optional[bytes], str]:
        try:
            from urllib.parse import urlparse

            if file_url.startswith("http"):
                parsed = urlparse(file_url)
                path_parts = parsed.path.lstrip("/").split("/", 1)
                object_key = path_parts[1] if len(path_parts) == 2 else parsed.path.lstrip("/")
            else:
                object_key = file_url

            if ".." in object_key:
                logger.error("Prevented path traversal attempt")
                return None, ""

            bucket = self._resolve_bucket(object_key, visibility)
            s3 = self._storage_client()
            obj = await asyncio.to_thread(s3.get_object, Bucket=bucket, Key=object_key)
            data = await asyncio.to_thread(obj["Body"].read)
            extension = f".{object_key.rsplit('.', 1)[-1].lower()}" if "." in object_key else ".pdf"
            logger.info("Retrieved file content from storage")
            return data, extension
        except Exception:
            logger.exception("File download connection error")
            return None, ""

    def _download_to_temporary_file(
        self, file_url: str, visibility: str = "public"
    ) -> tuple[Path | None, str, str]:
        temporary_path = None
        body = None
        try:
            from urllib.parse import urlparse

            if file_url.startswith("http"):
                parsed = urlparse(file_url)
                path_parts = parsed.path.lstrip("/").split("/", 1)
                object_key = path_parts[1] if len(path_parts) == 2 else parsed.path.lstrip("/")
            else:
                object_key = file_url

            if not object_key or ".." in object_key:
                raise ValueError("document_storage_key_invalid")
            extension = (
                f".{object_key.rsplit('.', 1)[-1].lower()}"
                if "." in object_key
                else ".pdf"
            )
            bucket = self._resolve_bucket(object_key, visibility)
            result = self._storage_client().get_object(Bucket=bucket, Key=object_key)
            body = result["Body"]
            digest = hashlib.sha256()
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                while True:
                    block = body.read(1024 * 1024)
                    if not block:
                        break
                    temporary.write(block)
                    digest.update(block)
            body.close()
            body = None
            if temporary_path.stat().st_size == 0:
                temporary_path.unlink(missing_ok=True)
                return None, "", ""
            return temporary_path, extension, digest.hexdigest()
        except Exception:
            logger.exception("File download connection error")
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            return None, "", ""
        finally:
            if body is not None:
                body.close()


document_parser = ConversionService()
