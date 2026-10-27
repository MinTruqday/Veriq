import asyncio
import base64
import json
import math
import random
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Dict
from uuid import NAMESPACE_URL, uuid4, uuid5

from loguru import logger

from src.clients.content import ContentClient
from src.core.infrastructure.configuration import settings
from src.core.infrastructure.observability import trace_span
from src.schemas.project import validate_project_source_structure
from src.services.chunking import SemanticChunkingError, chunker
from src.services.conversion import IndexingAttemptSupersededError, document_parser
from src.services.embedding import embedder
from src.services.inference import inspect_chunks, summarize_document
from src.store.bm25 import bm25_store
from src.store.vector import vector_store


class BoundedIngestionDiagnostics(list):
    def __init__(self, limit):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("document_ingestion_diagnostic_limit_invalid")
        super().__init__()
        self.limit = limit
        self.total_count = 0

    def append(self, value):
        self.total_count += 1
        if len(self) < self.limit:
            super().append(value)

    def clear(self):
        super().clear()
        self.total_count = 0


def source_timestamp(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def parsed_utc_datetime(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


SOURCE_SNAPSHOT_FIELDS = (
    "file_url",
    "revision",
    "content_hash",
    "source_hash",
    "content_sha256",
    "title",
    "author",
    "author_name",
    "visibility",
    "owner_id",
    "creator_id",
    "shared_with",
    "ai_enabled",
    "source",
    "content_source",
    "source_name",
    "source_url",
    "source_type",
    "authority",
    "content_format",
    "version",
    "source_version",
    "publisher",
    "publisher_name",
    "book_title",
    "collector_version",
    "project_id",
    "artifact_type",
    "artifact_id",
    "artifact_version_id",
    "module",
    "status",
    "content_type",
    "conflict_key",
    "claim_value",
    "ocr_language",
    "artifact_metadata",
)


async def _iter_chunk_batches(chunks, batch_size):
    if hasattr(chunks, "__aiter__"):
        batch = []
        async for chunk in chunks:
            batch.append(chunk)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
        return
    for batch_start in range(0, len(chunks), batch_size):
        yield chunks[batch_start : batch_start + batch_size]


def source_snapshot_values(document):
    return {field: document.get(field) for field in SOURCE_SNAPSHOT_FIELDS}


def source_snapshot_fingerprint(document):
    snapshot = source_snapshot_values(document)
    snapshot["shared_with"] = sorted(
        set(map(str, snapshot.get("shared_with") or []))
    )
    canonical = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


async def embed_and_index_chunks(
    chunks, verify_source_snapshot, *, document_id: str, stage_id="default"
):
    document_id = str(document_id or "").strip()
    if not document_id:
        raise ValueError("document_index_document_id_invalid")
    embedding_batch_size = getattr(embedder, "_batch_size", None)
    index_batch_size = getattr(vector_store, "upsert_batch_size", None)
    if (
        not isinstance(embedding_batch_size, int)
        or isinstance(embedding_batch_size, bool)
        or embedding_batch_size < 1
        or not isinstance(index_batch_size, int)
        or isinstance(index_batch_size, bool)
        or index_batch_size < 1
    ):
        raise ValueError("embedding_batch_size_invalid")
    index_batch_size = min(embedding_batch_size, index_batch_size)
    stage_id = str(stage_id or "").strip()
    if not stage_id:
        raise ValueError("document_index_generation_invalid")

    indexed_chunk_count = 0
    failed_chunks = BoundedIngestionDiagnostics(
        settings.DOCUMENT_MAX_INGESTION_DIAGNOSTIC_DETAILS
    )
    try:
        async for batch in _iter_chunk_batches(chunks, index_batch_size):
            if any(
                not isinstance(chunk, dict)
                or not isinstance(chunk.get("metadata"), dict)
                or str(chunk["metadata"].get("document_id") or "") != document_id
                or str(chunk["metadata"].get("index_generation") or "") != stage_id
                for chunk in batch
            ):
                raise ValueError("document_index_chunk_scope_mismatch")
            vectors = None
            try:
                vectors = await embedder.embed_batch([chunk["text"] for chunk in batch])
                if len(vectors) != len(batch) or any(
                    not isinstance(vector, list) or not vector for vector in vectors
                ):
                    raise ValueError("embedding_batch_shape_invalid")
            except Exception:
                vectors = []
                successful_batch = []
                for chunk in batch:
                    try:
                        vector = (await embedder.embed_batch([chunk["text"]]))[0]
                        if not isinstance(vector, list) or not vector:
                            raise ValueError("embedding_shape_invalid")
                        successful_batch.append((chunk, vector))
                    except Exception as error:
                        failed_chunks.append(
                            {
                                "chunk_id": chunk.get("metadata", {}).get("chunk_id")
                                or chunk.get("id"),
                                "stage": "embedding",
                                "error_code": type(error).__name__,
                            }
                        )
                batch = [chunk for chunk, _ in successful_batch]
                vectors = [vector for _, vector in successful_batch]

            if not batch:
                continue

            batch_ids = [str(chunk["id"]) for chunk in batch]
            metadatas = [
                {
                    **chunk["metadata"],
                    "embedding_model": settings.EMBEDDING_MODEL,
                    "embedding_input_hash": sha256(
                        chunk["text"].encode("utf-8")
                    ).hexdigest(),
                    "embedding_input_mode": "TEXT",
                }
                for chunk in batch
            ]
            await verify_source_snapshot()
            await vector_store.upsert(
                ids=batch_ids,
                embeddings=vectors,
                documents=[chunk["text"] for chunk in batch],
                metadatas=metadatas,
            )
            indexed_batch = [
                {
                    **chunk,
                    "metadata": metadata,
                }
                for chunk, metadata in zip(batch, metadatas)
            ]
            await bm25_store.stage_upsert(indexed_batch, stage_id)
            indexed_chunk_count += len(indexed_batch)

        if not indexed_chunk_count:
            raise RuntimeError("No chunks could be embedded")

        await vector_store.wait_upsert()
        await bm25_store.publish_staged(stage_id)
        await verify_source_snapshot()
    except BaseException as index_error:
        rollback_results = await asyncio.gather(
            vector_store.delete_document_generation(document_id, stage_id),
            bm25_store.delete_document_generation(document_id, stage_id),
            bm25_store.discard_staged(stage_id),
            return_exceptions=True,
        )
        if any(isinstance(result, BaseException) for result in rollback_results):
            logger.exception(
                "Batched document index rollback is incomplete document_id={} generation={}",
                document_id,
                stage_id,
            )
            raise RuntimeError("index_generation_rollback_incomplete") from index_error
        raise

    return indexed_chunk_count, failed_chunks


def validated_indexing_status(index_result: dict | None) -> str:
    if not index_result or index_result.get("updated") is not True:
        raise RuntimeError("document_index_status_update_failed")
    status = str(index_result.get("indexing_status") or "")
    if status not in {"indexed", "degraded"}:
        raise RuntimeError("document_index_status_invalid")
    return status


async def publish_index_generation(
    document_id,
    indexed_chunk_count,
    index_report,
    extracted_text,
    extraction_method,
    indexing_attempt_id,
    indexing_lease_token,
    index_generation,
    source_snapshot,
    document_index_contract_version=None,
):
    if document_index_contract_version is None:
        document_index_contract_version = settings.DOCUMENT_INDEX_CONTRACT_VERSION
    expected_status = (
        "degraded"
        if any(
            index_report.get(section)
            for section in (
                "failed_chunks",
                "quarantined_chunks",
                "unprocessed_blocks",
                "index_cleanup_pending",
            )
        )
        else "indexed"
    )
    try:
        result = await ContentClient.mark_indexed(
            document_id,
            indexed_chunk_count,
            index_report,
            extracted_text,
            extraction_method,
            indexing_attempt_id,
            indexing_lease_token,
            index_generation,
            source_snapshot,
            document_index_contract_version,
        )
        return validated_indexing_status(result)
    except Exception:
        try:
            current = await ContentClient.get(document_id)
        except Exception as error:
            raise RuntimeError("index_generation_publication_outcome_unknown") from error
        if not isinstance(current, dict):
            return ""
        current_chunk_count = current.get(
            "indexed_chunks", current.get("chunks_count")
        )
        if (
            not isinstance(current_chunk_count, int)
            or isinstance(current_chunk_count, bool)
        ):
            current_chunk_count = -1
        if (
            str(current.get("active_index_generation") or "") == index_generation
            and str(current.get("indexing_attempt_id") or "") == indexing_attempt_id
            and str(current.get("indexing_lease_token") or "") == indexing_lease_token
            and str(current.get("indexing_status") or "") == expected_status
            and current.get("document_index_contract_version")
            == document_index_contract_version
            and current_chunk_count == indexed_chunk_count
            and current.get("index_report") == index_report
        ):
            return expected_status
        return ""


def select_summary_chunks(chunks: list[dict], max_chars: int) -> tuple[str, list[dict]]:
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("document_summary_input_limit_invalid")
    usable = [
        chunk
        for chunk in chunks
        if isinstance(chunk, dict) and str(chunk.get("text") or "").strip()
    ]
    if not usable:
        return "", []

    total_chars = sum(len(str(chunk["text"])) for chunk in usable)
    if total_chars <= max_chars:
        candidates = usable
    else:
        average_chars = total_chars / len(usable)
        sample_count = max(
            2,
            min(len(usable), math.floor((max_chars + 2) / (average_chars + 2))),
        )
        sample_indexes = {
            round(index * (len(usable) - 1) / (sample_count - 1))
            for index in range(sample_count)
        }
        candidates = [usable[index] for index in sorted(sample_indexes)]

    selected = []
    text_parts = []
    selected_chars = 0
    for chunk in candidates:
        separator = 2 if text_parts else 0
        available = max_chars - selected_chars - separator
        if available <= 0:
            break
        text = str(chunk["text"]).strip()
        selected.append(chunk)
        text_parts.append(text[:available].rstrip())
        selected_chars += separator + len(text_parts[-1])

    return "\n\n".join(text_parts), selected


class DocumentSummarySampler:
    def __init__(self, max_chars: int, seed_material: str):
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
            raise ValueError("document_summary_input_limit_invalid")
        target_chars = max(1, int(chunker.target_chars))
        self.max_chars = max_chars
        self.reservoir_limit = max(
            2,
            min(max_chars, math.ceil(max_chars / target_chars) * 2),
        )
        seed = int.from_bytes(sha256(seed_material.encode("utf-8")).digest()[:8], "big")
        self.random = random.Random(seed)
        self.total_chunks = 0
        self.total_chars = 0
        self.all_chunks = []
        self.reservoir = None
        self.reservoir_seen = 0

    @staticmethod
    def _compact(chunk, index):
        metadata = chunk.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        return index, {
            "id": chunk.get("id"),
            "text": chunk.get("text", ""),
            "metadata": {
                key: metadata[key]
                for key in ("logical_chunk_id", "chunk_id", "page_numbers")
                if key in metadata
            },
        }

    def _add_to_reservoir(self, item):
        self.reservoir_seen += 1
        if len(self.reservoir) < self.reservoir_limit:
            self.reservoir.append(item)
            return
        replacement_index = self.random.randrange(self.reservoir_seen)
        if replacement_index < self.reservoir_limit:
            self.reservoir[replacement_index] = item

    def add(self, chunk):
        text = str(chunk.get("text") or "")
        if not text.strip():
            return
        self.total_chunks += 1
        self.total_chars += len(text)
        item = self._compact(chunk, self.total_chunks - 1)
        if self.reservoir is None and self.total_chars <= self.max_chars:
            self.all_chunks.append(item)
            return
        if self.reservoir is None:
            self.reservoir = []
            for existing in self.all_chunks:
                self._add_to_reservoir(existing)
            self.all_chunks.clear()
        self._add_to_reservoir(item)

    def select(self):
        if self.reservoir is None:
            candidates = self.all_chunks
            scope = "ALL_EXTRACTED_CHUNKS"
        else:
            candidates = sorted(self.reservoir, key=lambda item: item[0])
            scope = "UNIFORM_RESERVOIR_SAMPLE"
        chunks = [chunk for _, chunk in candidates]
        summary_input, selected_chunks = select_summary_chunks(chunks, self.max_chars)
        return summary_input, selected_chunks, scope


async def inspect_chunk_stream(chunks, quarantined):
    batch_size = settings.DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
        raise ValueError("document_chunk_inspection_batch_size_invalid")
    async for batch in _iter_chunk_batches(chunks, batch_size):
        accepted_indexes = await inspect_chunks([chunk["text"] for chunk in batch])
        for local_index, chunk in enumerate(batch):
            if local_index in accepted_indexes:
                yield chunk
            else:
                quarantined.append(
                    {
                        "chunk_id": chunk.get("metadata", {}).get("chunk_id")
                        or chunk.get("id"),
                        "flags": ["ai_safety_rejection"],
                    }
                )


async def inspect_and_quarantine_chunks(chunks: list[dict]) -> tuple[list[dict], list[dict]]:
    batch_size = settings.DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
        raise ValueError("document_chunk_inspection_batch_size_invalid")

    quarantined = []
    accepted_count = 0
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start : batch_start + batch_size]
        accepted_indexes = await inspect_chunks(
            [chunk["text"] for chunk in batch]
        )
        for local_index, chunk in enumerate(batch):
            if local_index in accepted_indexes:
                chunks[accepted_count] = chunk
                accepted_count += 1
            else:
                quarantined.append(
                    {
                        "chunk_id": chunk.get("metadata", {}).get("chunk_id")
                        or chunk.get("id"),
                        "flags": ["ai_safety_rejection"],
                    }
                )
    del chunks[accepted_count:]
    return chunks, quarantined


class IngestionPipelineService:
    async def ingest_document(
        self,
        document_id: str,
        requester_id: str,
        is_admin: bool = False,
        indexing_attempt_id: str = "",
        indexing_lease_token: str = "",
    ) -> Dict:
        logger.info(f"Starting ingestion for document {document_id}")
        doc = await ContentClient.authorize_document(document_id, requester_id, is_admin)

        file_url = doc.get("file_url", "") if doc else ""
        title = doc.get("title") or ""
        author = doc.get("author") or doc.get("author_name") or ""
        visibility = doc.get("visibility") or "private"
        content_format = doc.get("content_format") or ""
        content_source = (
            doc.get("source")
            or doc.get("content_source")
            or doc.get("source_name")
            or "user_upload"
        )
        artifact_metadata = doc.get("artifact_metadata") or {}
        source_snapshot = source_snapshot_fingerprint(doc)
        source_snapshot_values_at_start = source_snapshot_values(doc)

        def artifact_value(key: str, default=None):
            value = artifact_metadata.get(key)
            return doc.get(key, default) if value is None else value

        source_type = (
            doc.get("source_type") or artifact_metadata.get("source_type") or "project_document"
        )
        authority = (
            doc.get("authority") or artifact_metadata.get("authority") or "PROJECT_REFERENCE"
        )
        owner_id = str(doc.get("owner_id") or doc.get("creator_id") or "")

        if not file_url:
            raise ValueError(f"Document {document_id} not found or missing file_url")

        metadata = {
            "document_id": document_id,
            "title": title,
            "author": author,
            "content_format": content_format,
            "source": content_source,
            "visibility": visibility,
            "creator_id": str(doc.get("creator_id") or ""),
            "owner_id": owner_id,
            "shared_with": list(
                doc.get("shared_with") or artifact_metadata.get("shared_with") or []
            ),
            "source_url": doc.get("source_url"),
            "source_name": doc.get("source_name"),
            "source_type": source_type,
            "authority": authority,
            "publisher": doc.get("publisher") or doc.get("publisher_name"),
            "book_title": doc.get("book_title") or title,
            "collector_version": doc.get("collector_version"),
            "project_id": artifact_value("project_id"),
            "artifact_type": artifact_value("artifact_type", "project_document"),
            "artifact_id": artifact_value("artifact_id", document_id),
            "artifact_version_id": artifact_value("artifact_version_id", document_id),
            "module": artifact_value("module"),
            "status": artifact_value("status", "active"),
            "content_type": artifact_value("content_type"),
            "source_version": artifact_value("source_version") or doc.get("version"),
            "conflict_key": artifact_value("conflict_key"),
            "claim_value": artifact_value("claim_value"),
            "ocr_language": artifact_value("ocr_language"),
            "source_created_at": source_timestamp(doc.get("created_at")),
            "source_updated_at": source_timestamp(doc.get("updated_at")),
        }

        async def verify_source_snapshot():
            current_doc = await ContentClient.authorize_document(
                document_id, requester_id, is_admin
            )
            if (
                source_snapshot_fingerprint(current_doc) != source_snapshot
                or current_doc.get("file_url") != file_url
                or current_doc.get("revision") != doc.get("revision")
                or str(current_doc.get("owner_id") or current_doc.get("creator_id") or "")
                != owner_id
                or (current_doc.get("visibility") or "private") != visibility
                or (
                    doc.get("ai_enabled") is True
                    and (
                        current_doc.get("ai_enabled") is not True
                        or current_doc.get("index_status") == "REVOKE_PENDING"
                    )
                )
            ):
                raise PermissionError("document_source_changed_during_ingestion")
            lease_until = parsed_utc_datetime(
                current_doc.get("indexing_lease_until")
            )
            if (
                str(current_doc.get("indexing_attempt_id") or "")
                != indexing_attempt_id
                or str(current_doc.get("indexing_lease_token") or "")
                != indexing_lease_token
                or not lease_until
                or lease_until <= datetime.now(timezone.utc)
            ):
                raise IndexingAttemptSupersededError(
                    "document_indexing_attempt_superseded"
                )

        async def report_page_progress(
            processed_pages: int, total_pages: int, unprocessed_pages: int
        ):
            progress_result = await ContentClient.update_indexing_progress(
                document_id,
                indexing_attempt_id,
                indexing_lease_token,
                processed_pages,
                total_pages,
                unprocessed_pages,
            )
            if not progress_result or progress_result.get("updated") is not True:
                raise RuntimeError("document_index_progress_attempt_superseded")

        with trace_span(
            "document.ingestion.parse",
            {
                "document.id": document_id,
                "document.revision": doc.get("revision"),
            },
        ):
            parse_result = await document_parser.parse_document_checkpointed(
                file_url,
                visibility,
                document_id,
                str(artifact_value("project_id") or ""),
                owner_id,
                authorization_check=verify_source_snapshot,
                progress_callback=report_page_progress,
                ocr_language=metadata.get("ocr_language"),
            )
        if parse_result.get("error"):
            raise ValueError("Failed to convert document with Docling")
        raw_markdown = str(parse_result.pop("markdown", None) or "")
        source_structure = parse_result.pop("structure", None)
        document_structure = validate_project_source_structure(
            source_structure if isinstance(source_structure, list) else [],
            reuse_input_list=True,
        )
        del source_structure
        unprocessed_blocks = parse_result.get("unprocessed_blocks", [])
        source_hash = str(parse_result.get("source_sha256") or "")
        parser_name = str(parse_result.get("parser") or "unknown")
        parser_version = str(parse_result.get("parser_version") or "unknown")
        generation_metadata = dict(metadata)
        generation_metadata["document_index_contract_version"] = (
            settings.DOCUMENT_INDEX_CONTRACT_VERSION
        )
        generation_metadata["shared_with"] = sorted(
            set(map(str, generation_metadata.get("shared_with") or []))
        )
        index_generation_material = json.dumps(
            {
                "document_id": document_id,
                "indexing_attempt_id": indexing_attempt_id or None,
                "document_index_contract_version": (
                    settings.DOCUMENT_INDEX_CONTRACT_VERSION
                ),
                "source_version": metadata.get("source_version"),
                "source_hash": source_hash,
                "normalized_content_hash": sha256(
                    raw_markdown.encode("utf-8")
                ).hexdigest(),
                "parser_name": parser_name,
                "parser_version": parser_version,
                "embedding_model": settings.EMBEDDING_MODEL,
                "document_metadata": generation_metadata,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        metadata.update(
            {
                "source_hash": source_hash,
                "normalized_content_hash": sha256(
                    raw_markdown.encode("utf-8")
                ).hexdigest(),
                "parser_name": parser_name,
                "parser_version": parser_version,
                "ocr_enabled": bool(parse_result.get("ocr_enabled", False)),
                "ocr_language": parse_result.get("ocr_language"),
                "page_count": parse_result.get("page_count"),
                "source_block_count": len(document_structure),
                "indexing_attempt_id": indexing_attempt_id or None,
                "document_index_contract_version": (
                    settings.DOCUMENT_INDEX_CONTRACT_VERSION
                ),
                "extraction_status": "DEGRADED" if unprocessed_blocks else "COMPLETE",
                "unprocessed_block_count": len(unprocessed_blocks),
                "extraction_warning_count": len(parse_result.get("extraction_warnings") or []),
                "extraction_warning_codes": sorted(
                    {
                        str(item.get("reason_code"))
                        for item in parse_result.get("extraction_warnings") or []
                        if isinstance(item, dict) and item.get("reason_code")
                    }
                ),
                "index_generation": sha256(
                    index_generation_material.encode("utf-8")
                ).hexdigest(),
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        if not raw_markdown.strip():
            raise ValueError("Failed to extract document text")
        extraction_method = "docling_structure_semantic"
        diagnostic_limit = settings.DOCUMENT_MAX_INGESTION_DIAGNOSTIC_DETAILS
        quarantined_chunks = BoundedIngestionDiagnostics(diagnostic_limit)

        async def indexed_chunks(semantic=True):
            sampler = DocumentSummarySampler(
                settings.DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT,
                f"{document_id}:{metadata['index_generation']}",
            )
            source_chunks = chunker.iter_chunk_document(
                raw_markdown,
                {**metadata, "extraction_method": extraction_method},
                structure=document_structure,
                semantic=semantic,
            )
            async for chunk in inspect_chunk_stream(source_chunks, quarantined_chunks):
                sampler.add(chunk)
                yield chunk

            summary_input, summary_chunks, summary_scope = sampler.select()
            if len(summary_input) < 500:
                summary = summary_input.strip()
            else:
                try:
                    summary = await summarize_document(summary_input)
                except Exception:
                    logger.exception("Document summary generation error")
                    summary = ""
            if not summary:
                return

            summary_text = (
                "[SUMMARY OF EXTRACTED DOCUMENT CONTENT; "
                "VERIFY SOURCE BLOCKS FOR AUTHORITATIVE DETAILS]\n"
                f"Document: {title}\n"
                f"Author: {author}\n"
                f"{summary}"
            )
            summary_source_chunk_ids = [
                str(
                    chunk.get("metadata", {}).get("logical_chunk_id")
                    or chunk.get("metadata", {}).get("chunk_id")
                    or chunk.get("id")
                )
                for chunk in summary_chunks
            ]
            summary_chunk_hash = sha256(summary_text.encode("utf-8")).hexdigest()
            summary_logical_identity = json.dumps(
                {
                    "document_id": document_id,
                    "source_version": metadata.get("source_version"),
                    "source_hash": source_hash,
                    "normalized_content_hash": metadata.get("normalized_content_hash"),
                    "chunk_type": "summary",
                    "chunk_hash": summary_chunk_hash,
                    "sample_chunk_ids": summary_source_chunk_ids,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            summary_point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    ":".join(
                        [
                            document_id,
                            str(metadata.get("source_version") or ""),
                            str(metadata.get("index_generation") or ""),
                            "summary",
                            sha256(summary.encode()).hexdigest(),
                        ]
                    ),
                )
            )
            yield {
                "id": summary_point_id,
                "text": summary_text,
                "metadata": {
                    **metadata,
                    "chunk_id": "summary_001",
                    "logical_chunk_id": str(
                        uuid5(NAMESPACE_URL, summary_logical_identity)
                    ),
                    "chunk_hash": summary_chunk_hash,
                    "chunk_type": "summary",
                    "chunk_index": -1,
                    "summary_scope": summary_scope,
                    "summary_sample_chunk_ids": [
                        str(
                            chunk.get("metadata", {}).get("chunk_id")
                            or chunk.get("id")
                        )
                        for chunk in summary_chunks
                    ],
                    "summary_sample_page_numbers": sorted(
                        {
                            page
                            for chunk in summary_chunks
                            for page in (
                                chunk.get("metadata", {}).get("page_numbers") or []
                            )
                            if isinstance(page, int)
                            and not isinstance(page, bool)
                            and page > 0
                        }
                    ),
                    "summary_sample_char_count": len(summary_input),
                    "document_chunk_count": sampler.total_chunks,
                    "extraction_method": f"{extraction_method}_llm",
                },
            }

        with trace_span(
            "document.ingestion.index",
            {
                "document.id": document_id,
                "index.generation": str(metadata["index_generation"]),
            },
        ) as index_span:
            try:
                indexed_chunk_count, failed_chunks = await embed_and_index_chunks(
                    indexed_chunks(),
                    verify_source_snapshot,
                    document_id=document_id,
                    stage_id=str(metadata["index_generation"]),
                )
            except SemanticChunkingError:
                if index_span is not None:
                    index_span.set_attribute("event.status", "chunking_fallback")
                quarantined_chunks.clear()
                extraction_method = "docling_structure_fallback"
                indexed_chunk_count, failed_chunks = await embed_and_index_chunks(
                    indexed_chunks(semantic=False),
                    verify_source_snapshot,
                    document_id=document_id,
                    stage_id=str(metadata["index_generation"]),
                )
        extracted_text_preview = raw_markdown[:200000]
        del indexed_chunks
        del raw_markdown
        index_report = {
            "failed_chunks": failed_chunks, "quarantined_chunks": quarantined_chunks,
            "failed_chunk_count": failed_chunks.total_count,
            "failed_chunk_details_truncated": failed_chunks.total_count > len(failed_chunks),
            "quarantined_chunk_count": quarantined_chunks.total_count,
            "quarantined_chunk_details_truncated": (
                quarantined_chunks.total_count > len(quarantined_chunks)
            ),
            "unprocessed_blocks": unprocessed_blocks,
            "extraction_warnings": parse_result.get("extraction_warnings", []),
        }
        with trace_span(
            "document.ingestion.publish",
            {
                "document.id": document_id,
                "index.generation": str(metadata["index_generation"]),
                "index.chunk_count": indexed_chunk_count,
                "index.extraction_status": metadata["extraction_status"],
            },
        ):
            indexing_status = await publish_index_generation(
                document_id,
                indexed_chunk_count,
                index_report,
                extracted_text_preview,
                extraction_method,
                indexing_attempt_id,
                indexing_lease_token,
                str(metadata["index_generation"]),
                source_snapshot_values_at_start,
                settings.DOCUMENT_INDEX_CONTRACT_VERSION,
            )
        if not indexing_status:
            error = RuntimeError("document_index_status_update_failed")
            try:
                current = await ContentClient.get(document_id)
            except Exception as read_error:
                raise RuntimeError(
                    "index_generation_publication_outcome_unknown"
                ) from read_error
            if (
                isinstance(current, dict)
                and str(current.get("active_index_generation") or "")
                == str(metadata["index_generation"])
            ):
                raise RuntimeError(
                    "index_generation_published_but_attempt_state_changed"
                ) from error
            await self._rollback_generation(
                document_id, str(metadata["index_generation"]), error
            )
            raise error

        await verify_source_snapshot()
        cleanup_results = await asyncio.gather(
            vector_store.delete_stale_document_generations(
                document_id, str(metadata["index_generation"])
            ),
            bm25_store.delete_stale_document_generations(
                document_id, str(metadata["index_generation"])
            ),
            return_exceptions=True,
        )
        cleanup_pending = [
            store_name
            for store_name, result in zip(("qdrant", "bm25"), cleanup_results)
            if isinstance(result, BaseException)
        ]
        if cleanup_pending:
            logger.warning(
                "Stale index generation cleanup pending document_id={} stores={}",
                document_id,
                cleanup_pending,
            )
            index_report["index_cleanup_pending"] = cleanup_pending
            indexing_status = await publish_index_generation(
                document_id,
                indexed_chunk_count,
                index_report,
                extracted_text_preview,
                extraction_method,
                indexing_attempt_id,
                indexing_lease_token,
                str(metadata["index_generation"]),
                source_snapshot_values_at_start,
                settings.DOCUMENT_INDEX_CONTRACT_VERSION,
            )
            if not indexing_status:
                raise RuntimeError("document_index_status_update_failed")

        if indexing_attempt_id:
            completion = await ContentClient.complete_indexing(
                document_id, indexing_attempt_id, indexing_lease_token
            )
            if not completion or completion.get("updated") is not True:
                raise RuntimeError("document_index_attempt_superseded")

        if indexing_status == "indexed":
            try:
                await document_parser.clear_document_checkpoints(
                    document_id,
                    str(artifact_value("project_id") or ""),
                    owner_id,
                    source_hash,
                )
            except Exception:
                logger.exception(
                    "Completed document indexing but checkpoint cleanup is pending document_id={}",
                    document_id,
                )

        return {
            "document_id": document_id,
            "title": title,
            "chunks_count": indexed_chunk_count,
            "extraction_method": extraction_method,
            "status": indexing_status,
            "quarantined_chunks": quarantined_chunks,
            "quarantined_chunk_count": quarantined_chunks.total_count,
            "quarantined_chunk_details_truncated": (
                quarantined_chunks.total_count > len(quarantined_chunks)
            ),
            "failed_chunks": failed_chunks,
            "failed_chunk_count": failed_chunks.total_count,
            "failed_chunk_details_truncated": failed_chunks.total_count > len(failed_chunks),
            "failed_chunks": failed_chunks,
            "unprocessed_blocks": unprocessed_blocks,
            "extraction_warnings": parse_result.get("extraction_warnings", []),
            "index_cleanup_pending": cleanup_pending,
        }

    @staticmethod
    async def _rollback_generation(
        document_id: str, index_generation: str, cause: Exception
    ):
        results = await asyncio.gather(
            vector_store.delete_document_generation(document_id, index_generation),
            bm25_store.delete_document_generation(document_id, index_generation),
            return_exceptions=True,
        )
        if any(isinstance(result, BaseException) for result in results):
            logger.exception(
                "Rejected index generation cleanup is incomplete document_id={}",
                document_id,
            )
            raise RuntimeError("stale_index_generation_cleanup_incomplete") from cause


ingestion_pipeline = IngestionPipelineService()


async def index_document(
    document_id: str,
    requester_id: str,
    is_admin: bool,
    dispatch_event_id: str = "",
) -> dict:
    authorized = False
    claimed = False
    indexing_attempt_id = str(uuid4())
    indexing_lease_token = str(uuid4())
    heartbeat_task = None
    try:
        await ContentClient.authorize_document(document_id, requester_id, is_admin)
        authorized = True
        claim = await ContentClient.mark_indexing(
            document_id,
            indexing_attempt_id,
            indexing_lease_token,
            dispatch_event_id,
        )
        claim_status = str((claim or {}).get("status") or "")
        if claim_status == "busy":
            lease_until = parsed_utc_datetime((claim or {}).get("lease_until"))
            retry_after_seconds = float(settings.DOCUMENT_INDEXING_LEASE_SECONDS)
            if lease_until:
                lease_remaining = max(
                    1.0,
                    (lease_until - datetime.now(timezone.utc)).total_seconds(),
                )
                retry_after_seconds = min(retry_after_seconds, lease_remaining)
            return {
                "document_id": document_id,
                "status": "busy",
                "retry_after_seconds": retry_after_seconds,
            }
        if claim_status == "superseded":
            return {"document_id": document_id, "status": "superseded"}
        if claim_status == "already_indexed":
            return {"document_id": document_id, "status": "indexed"}
        if claim_status != "claimed" or claim.get("updated") is not True:
            raise RuntimeError("document_index_claim_failed")
        claimed = True

        current_task = asyncio.current_task()

        async def renew_lease_until_cancelled():
            while True:
                await asyncio.sleep(
                    settings.DOCUMENT_INDEXING_LEASE_HEARTBEAT_SECONDS
                )
                try:
                    renewed = await ContentClient.renew_indexing_lease(
                        document_id, indexing_attempt_id, indexing_lease_token
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    logger.warning(
                        "Document indexing lease renewal could not be confirmed document_id={} error_type={}",
                        document_id,
                        type(error).__name__,
                    )
                    if current_task and not current_task.done():
                        current_task.cancel()
                    return
                if not renewed or renewed.get("updated") is not True:
                    logger.warning(
                        "Document indexing lease was lost document_id={}", document_id
                    )
                    if current_task and not current_task.done():
                        current_task.cancel()
                    return

        heartbeat_task = asyncio.create_task(
            renew_lease_until_cancelled(),
            name=f"document-indexing-lease-{document_id}",
        )
        return await ingestion_pipeline.ingest_document(
            document_id,
            requester_id,
            is_admin,
            indexing_attempt_id,
            indexing_lease_token,
        )
    except Exception as error:
        if authorized and claimed:
            try:
                await ContentClient.mark_index_failed(
                    document_id,
                    type(error).__name__,
                    indexing_attempt_id,
                    indexing_lease_token,
                )
            except Exception as status_error:
                logger.warning(
                    "Unable to mark document indexing failure document_id={} error_type={}",
                    document_id,
                    type(status_error).__name__,
                )
        raise
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass


async def extract_document(document_id: str, requester_id: str, is_admin: bool) -> str:
    document = await ContentClient.authorize_document(document_id, requester_id, is_admin)
    file_url = str(document.get("file_url") or "")
    if not file_url:
        raise ValueError("Document file not found")
    markdown = await document_parser.get_markdown(
        file_url, visibility=document.get("visibility") or "private"
    )
    if not markdown:
        raise ValueError("Document text unavailable")
    return markdown


async def convert_attachment(
    data: str,
    filename: str,
    page_range: tuple[int, int] | None = None,
    document_id: str | None = None,
    project_id: str | None = None,
    owner_id: str | None = None,
    ocr_language: str | None = None,
) -> dict:
    payload = data.split(",", 1)[-1]
    try:
        file_bytes = base64.b64decode(payload, validate=True)
    except (ValueError, base64.binascii.Error) as error:
        raise ValueError("Invalid base64 attachment") from error
    if not file_bytes:
        raise ValueError("Empty attachment")
    if len(file_bytes) > 25 * 1024 * 1024:
        raise ValueError("Attachment exceeds 25 MB")
    extension = Path(filename).suffix or ".pdf"
    if document_id and project_id and owner_id:
        result = await document_parser.parse_bytes_checkpointed(
            file_bytes,
            extension,
            document_id,
            project_id,
            owner_id,
            ocr_language=ocr_language,
        )
    else:
        result = await document_parser.parse_bytes(
            file_bytes, extension, page_range, ocr_language=ocr_language
        )
    markdown = str(result.get("markdown") or "")
    if not markdown and page_range is None:
        raise ValueError("Document text unavailable")
    return {
        "markdown": markdown,
        "structure": result.get("structure", []),
        "page_count": result.get("page_count"),
        "unprocessed_blocks": result.get("unprocessed_blocks", []),
        "parser": result.get("parser"),
        "parser_version": result.get("parser_version"),
            "ocr_enabled": result.get("ocr_enabled", False),
            "ocr_language": result.get("ocr_language"),
        "source_hash": result.get("source_sha256"),
    }


async def remove_document(document_id: str, requester_id: str, is_admin: bool) -> dict:
    document = await ContentClient.authorize_document(
        document_id, requester_id, is_admin, True
    )
    cleanup_results = await asyncio.gather(
        vector_store.delete_by_document(document_id),
        bm25_store.delete_by_document(document_id),
        return_exceptions=True,
    )
    cleanup_failures = [result for result in cleanup_results if isinstance(result, BaseException)]
    cancellation = next(
        (error for error in cleanup_failures if isinstance(error, asyncio.CancelledError)),
        None,
    )
    if cancellation is not None:
        raise cancellation
    if cleanup_failures:
        raise RuntimeError("document_index_removal_incomplete") from cleanup_failures[0]

    project_id = str(document.get("project_id") or "")
    if project_id:
        try:
            await document_parser.delete_picture_assets(project_id, document_id)
        except Exception as error:
            logger.exception(
                "Document image asset removal incomplete document_id={}",
                document_id,
            )
            raise RuntimeError("document_image_asset_removal_incomplete") from error
        try:
            from src.repositories.document_ingestion_checkpoint import (
                document_ingestion_checkpoint_repository,
            )

            await document_ingestion_checkpoint_repository.delete_document_versions(
                document_id,
                project_id,
            )
        except Exception as error:
            logger.exception(
                "Document ingestion checkpoint removal incomplete document_id={}",
                document_id,
            )
            raise RuntimeError("document_checkpoint_removal_incomplete") from error

    status = await ContentClient.mark_unindexed(document_id)
    if not isinstance(status, dict) or status.get("updated") is not True:
        raise RuntimeError("document_unindex_status_update_failed")
    return {"document_id": document_id, "status": "deleted"}
