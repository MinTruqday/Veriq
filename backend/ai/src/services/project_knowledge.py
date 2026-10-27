import asyncio
import base64
import hashlib
import json
import time
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import HTTPException
from loguru import logger
from pydantic import ValidationError

from src.core.infrastructure.configuration import settings
from src.knowledge.metadata import public_retrieval_metadata
from src.repositories.project_artifact_generation import (
    ProjectArtifactGenerationConflict,
    project_artifact_generation_repository,
)
from src.schemas.project import (
    DOCUMENT_INDEXED_ARTIFACT_TYPES,
    ProjectArtifactChunkMetadata,
    ProjectArtifactIndexRequest,
    ProjectArtifactQdrantPayload,
    ProjectKnowledgeSearchRequest,
)
from src.services.chunking import chunker
from src.services.embedding import embedder
from src.services.retrieval import RetrievalUnavailableError, retriever
from src.store.bm25 import bm25_store
from src.store.vector import vector_store

SEARCH_CACHE: dict[tuple, tuple[float, dict]] = {}
_ARTIFACT_INDEX_LOCKS = tuple(asyncio.Lock() for _ in range(64))
def _artifact_index_lock(project_id: str, artifact_version_id: str) -> asyncio.Lock:
    key = f"{project_id}:{artifact_version_id}".encode("utf-8")
    slot = int.from_bytes(hashlib.sha256(key).digest()[:4], "big") % len(
        _ARTIFACT_INDEX_LOCKS
    )
    return _ARTIFACT_INDEX_LOCKS[slot]


def _invalidate_project_search_cache(project_id: str) -> None:
    for key in tuple(SEARCH_CACHE):
        if key[0] == project_id:
            SEARCH_CACHE.pop(key, None)


async def _rollback_project_artifact_generation(
    project_id: str,
    artifact_type: str,
    artifact_id: str,
    artifact_version_id: str,
    generation: str,
    cause: Exception,
) -> None:
    rollback_results = await asyncio.gather(
        vector_store.delete_artifact_generation(
            project_id, artifact_type, artifact_id, artifact_version_id, generation
        ),
        bm25_store.delete_artifact_generation(
            project_id, artifact_type, artifact_id, artifact_version_id, generation
        ),
        bm25_store.discard_staged(generation),
        return_exceptions=True,
    )
    rollback_incomplete = [
        store_name
        for store_name, result in zip(("qdrant", "bm25", "bm25_staging"), rollback_results)
        if isinstance(result, BaseException)
    ]
    if rollback_incomplete:
        logger.error(
            "Project artifact index rollback incomplete project={} artifact_version={} generation={} stores={}",
            project_id,
            artifact_version_id,
            generation,
            rollback_incomplete,
        )
        raise RuntimeError("project_artifact_index_rollback_incomplete") from cause


def graph_metadata(metadata):
    primitive = (str, int, float, bool)
    return {
        key: value
        for key, value in metadata.items()
        if value is None
        or isinstance(value, primitive)
        or (isinstance(value, list) and all(isinstance(item, primitive) for item in value))
    }


def project_artifact_metadata(project_id: str, req: ProjectArtifactIndexRequest):
    source_metadata = dict(req.metadata)
    extraction = source_metadata.pop("extraction", {})
    if not isinstance(extraction, dict):
        extraction = {}
    metadata = {
        **source_metadata,
        "project_id": project_id,
        "artifact_type": req.artifact_type,
        "artifact_id": req.artifact_id,
        "artifact_version_id": req.artifact_version_id,
        "title": req.title,
        "status": req.status,
        "authority": req.authority,
        "version": req.version,
        "module": req.module,
        "visibility": req.metadata.get("visibility", "project"),
        "ai_enabled": req.metadata.get("ai_enabled"),
        "requirement_ids": req.metadata.get(
            "requirement_ids",
            [req.artifact_id] if req.artifact_type == "requirement_version" else [],
        ),
        "source_document_id": req.metadata.get("source_document_id"),
        "page": req.metadata.get("page"),
        "section": req.metadata.get("section") or req.title,
        "owner_id": req.metadata.get("owner_id") or req.metadata.get("created_by"),
        "creator_id": req.metadata.get("created_by"),
        "shared_with": req.metadata.get("shared_with", []),
        "source_hash": req.metadata.get("source_hash"),
        "normalized_content_hash": hashlib.sha256(
            req.text.encode("utf-8")
        ).hexdigest(),
        "parser_name": extraction.get("parser"),
        "parser_version": extraction.get("parser_version"),
        "ocr_enabled": extraction.get("ocr_enabled"),
        "ocr_language": extraction.get("ocr_language"),
        "page_count": extraction.get("page_count"),
        "source_block_count": len(req.source_structure),
        "extraction_status": (
            "DEGRADED"
            if extraction.get("unprocessed_blocks")
            else "COMPLETE"
            if extraction.get("parser") and req.text.strip()
            else None
        ),
        "extraction_method": extraction.get("extraction_method") or extraction.get("parser"),
        "unprocessed_block_count": len(extraction.get("unprocessed_blocks") or []),
        "extraction_warning_count": len(extraction.get("extraction_warnings") or []),
        "extraction_warning_codes": sorted(
            {
                str(item.get("reason_code"))
                for item in extraction.get("extraction_warnings") or []
                if isinstance(item, dict) and item.get("reason_code")
            }
        ),
        "embedding_model": settings.EMBEDDING_MODEL,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }
    if req.artifact_type in DOCUMENT_INDEXED_ARTIFACT_TYPES:
        metadata["document_index_contract_version"] = (
            settings.DOCUMENT_INDEX_CONTRACT_VERSION
        )
    return metadata


def project_artifact_point_payload(text: str, metadata: dict) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("project_artifact_point_content_required")
    if not isinstance(metadata, dict):
        raise ValueError("project_artifact_point_metadata_must_be_object")
    if "text" in metadata and metadata["text"] != text:
        raise ValueError("project_artifact_point_content_metadata_conflict")
    metadata = dict(metadata)
    metadata.setdefault("char_count", len(text))
    metadata.setdefault("word_count", len(text.split()))
    return ProjectArtifactQdrantPayload.model_validate(
        {**metadata, "text": text}
    ).model_dump(exclude_none=True)


def project_artifact_chunk_read_metadata(
    text: str,
    metadata: dict,
    project_id: str,
    artifact_version_id: str,
    index_generation: str,
) -> dict:
    payload = ProjectArtifactQdrantPayload.model_validate({**metadata, "text": text})
    if payload.project_id != project_id:
        raise ValueError("project_artifact_point_project_mismatch")
    if payload.artifact_version_id != artifact_version_id:
        raise ValueError("project_artifact_point_version_mismatch")
    if index_generation != "LEGACY" and payload.index_generation != index_generation:
        raise ValueError("project_artifact_point_generation_mismatch")
    if index_generation == "LEGACY" and payload.index_generation:
        raise ValueError("project_artifact_legacy_point_generation_mismatch")
    typed_metadata = ProjectArtifactChunkMetadata.model_validate(
        payload.model_dump(exclude={"text"}, exclude_none=True)
    ).model_dump(exclude_none=True)
    return public_retrieval_metadata(typed_metadata)


async def index_project_artifact(project_id: str, req: ProjectArtifactIndexRequest):
    async with _artifact_index_lock(project_id, req.artifact_version_id):
        return await _index_project_artifact_locked(project_id, req)


async def _index_project_artifact_locked(project_id: str, req: ProjectArtifactIndexRequest):
    try:
        manifest = await project_artifact_generation_repository.get_or_migrate(
            project_id, req.artifact_version_id
        )
    except Exception as error:
        raise HTTPException(
            status_code=503, detail={"code": "INDEX_MANIFEST_UNAVAILABLE"}
        ) from error
    if manifest.get("status") == "DELETING":
        raise HTTPException(status_code=409, detail={"code": "ARTIFACT_REMOVAL_IN_PROGRESS"})
    content_hash = hashlib.sha256(req.text.encode("utf-8")).hexdigest()
    generation_material = json.dumps(
        {
            "project_id": project_id,
            "artifact_version_id": req.artifact_version_id,
            "content_hash": content_hash,
            "index_attempt_id": uuid4().hex,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    index_generation = hashlib.sha256(generation_material.encode("utf-8")).hexdigest()
    metadata = {
        **project_artifact_metadata(project_id, req),
        "index_generation": index_generation,
    }
    source_structure = req.source_structure
    embedding_batch_size = getattr(embedder, "_batch_size", None)
    point_batch_size = getattr(vector_store, "upsert_batch_size", None)
    if (
        not isinstance(embedding_batch_size, int)
        or isinstance(embedding_batch_size, bool)
        or embedding_batch_size < 1
        or not isinstance(point_batch_size, int)
        or isinstance(point_batch_size, bool)
        or point_batch_size < 1
    ):
        raise ValueError("project_artifact_index_batch_size_invalid")
    batch_size = min(embedding_batch_size, point_batch_size)
    stage_id = index_generation
    chunk_count = 0

    async def write_batch(batch_chunks, first_chunk_index):
        if not batch_chunks:
            return first_chunk_index
        batch_end = first_chunk_index + len(batch_chunks)
        batch_ids = [
            str(
                uuid5(
                    NAMESPACE_URL,
                    f"{project_id}:{req.artifact_version_id}:{content_hash}:{index_generation}:{index}",
                )
            )
            for index in range(first_chunk_index, batch_end)
        ]
        batch_texts = [chunk["text"] for chunk in batch_chunks]
        embedding_inputs = [f"{req.title} {text}" for text in batch_texts]
        vectors = await embedder.embed_batch(embedding_inputs)
        if len(vectors) != len(batch_chunks) or any(
            not isinstance(vector, list) or not vector for vector in vectors
        ):
            raise RuntimeError("INDEX_EMBEDDING_COUNT_MISMATCH")
        batch_metadata = [
            {
                **metadata,
                **chunk.get("metadata", {}),
                "project_id": project_id,
                "artifact_type": req.artifact_type,
                "artifact_id": req.artifact_id,
                "artifact_version_id": req.artifact_version_id,
                "index_generation": index_generation,
                "chunk_index": first_chunk_index + offset,
                "embedding_input_hash": hashlib.sha256(
                    embedding_inputs[offset].encode("utf-8")
                ).hexdigest(),
                "embedding_input_mode": "TITLE_AND_TEXT",
            }
            for offset, chunk in enumerate(batch_chunks)
        ]
        point_payloads = [
            project_artifact_point_payload(text, item_metadata)
            for text, item_metadata in zip(batch_texts, batch_metadata)
        ]
        await vector_store.upsert(
            batch_ids,
            vectors,
            [payload["text"] for payload in point_payloads],
            [
                {key: value for key, value in payload.items() if key != "text"}
                for payload in point_payloads
            ],
        )
        await bm25_store.stage_upsert(
            [
                {
                    "id": point_id,
                    "text": text,
                    "metadata": item_metadata,
                }
                for point_id, text, item_metadata in zip(
                    batch_ids, batch_texts, batch_metadata
                )
            ],
            stage_id=stage_id,
        )
        return batch_end

    try:
        semantic = True
        chunk_stream = chunker.iter_chunk_document(
            req.text, metadata, structure=source_structure, semantic=semantic
        )
        batch_chunks = []
        while True:
            try:
                chunk = await anext(chunk_stream)
            except StopAsyncIteration:
                break
            except asyncio.CancelledError:
                raise
            except Exception as chunk_error:
                if not semantic:
                    raise
                await _rollback_project_artifact_generation(
                    project_id,
                    req.artifact_type,
                    req.artifact_id,
                    req.artifact_version_id,
                    index_generation,
                    chunk_error,
                )
                batch_chunks.clear()
                chunk_count = 0
                semantic = False
                chunk_stream = chunker.iter_chunk_document(
                    req.text, metadata, structure=source_structure, semantic=False
                )
                continue
            batch_chunks.append(chunk)
            if len(batch_chunks) >= batch_size:
                chunk_count = await write_batch(batch_chunks, chunk_count)
                batch_chunks.clear()
        if batch_chunks:
            chunk_count = await write_batch(batch_chunks, chunk_count)
        if chunk_count == 0:
            raise HTTPException(status_code=422, detail={"code": "INDEX_CONTENT_EMPTY"})
        await bm25_store.publish_staged(stage_id)
    except asyncio.CancelledError as index_error:
        await _rollback_project_artifact_generation(
            project_id,
            req.artifact_type,
            req.artifact_id,
            req.artifact_version_id,
            index_generation,
            index_error,
        )
        raise
    except Exception as index_error:
        await _rollback_project_artifact_generation(
            project_id,
            req.artifact_type,
            req.artifact_id,
            req.artifact_version_id,
            index_generation,
            index_error,
        )
        raise

    try:
        published = await project_artifact_generation_repository.publish(
            manifest, index_generation, chunk_count
        )
    except Exception as publish_error:
        try:
            current_manifest = await project_artifact_generation_repository.get_or_migrate(
                project_id, req.artifact_version_id
            )
        except Exception as verification_error:
            raise RuntimeError("project_artifact_publish_outcome_unknown") from verification_error
        if (
            current_manifest.get("status") == "ACTIVE"
            and current_manifest.get("active_generation") == index_generation
        ):
            published = True
        else:
            await _rollback_project_artifact_generation(
                project_id,
                req.artifact_type,
                req.artifact_id,
                req.artifact_version_id,
                index_generation,
                publish_error,
            )
            raise
    if not published:
        conflict = ProjectArtifactGenerationConflict("artifact_generation_revision_changed")
        await _rollback_project_artifact_generation(
            project_id,
            req.artifact_type,
            req.artifact_id,
            req.artifact_version_id,
            index_generation,
            conflict,
        )
        raise conflict

    cleanup_pending = []
    cleanup_results = await asyncio.gather(
        vector_store.delete_stale_artifact_generations(
            project_id,
            req.artifact_type,
            req.artifact_id,
            req.artifact_version_id,
            index_generation,
        ),
        bm25_store.delete_stale_artifact_generations(
            project_id,
            req.artifact_type,
            req.artifact_id,
            req.artifact_version_id,
            index_generation,
        ),
        return_exceptions=True,
    )
    for store_name, result in zip(("qdrant", "bm25"), cleanup_results):
        if isinstance(result, BaseException):
            cleanup_pending.append(store_name)
    if cleanup_pending:
        logger.warning(
            "Project artifact stale index cleanup pending project={} artifact_version={} stores={}",
            project_id,
            req.artifact_version_id,
            cleanup_pending,
        )
    graph_status = {"status": "UNAVAILABLE", "reason_code": "GRAPH_UNAVAILABLE"}
    try:
        from src.knowledge.graph.sync import sync_indexed_artifact

        graph_status = await sync_indexed_artifact(
            project_id,
            req.artifact_type,
            req.artifact_id,
            req.artifact_version_id,
            {
                **graph_metadata(req.metadata),
                "artifact_version_id": req.artifact_version_id,
                "title": req.title,
                "status": req.status,
                "authority": req.authority,
            },
        )
    except Exception:
        graph_status = {"status": "UNAVAILABLE", "reason_code": "GRAPH_UNAVAILABLE"}
    _invalidate_project_search_cache(project_id)
    return {
        "status": "degraded" if cleanup_pending else "indexed",
        "project_id": project_id,
        "artifact_version_id": req.artifact_version_id,
        "chunks_count": chunk_count,
        "index_generation": index_generation,
        "index_cleanup_pending": cleanup_pending,
        "graph": graph_status,
    }


async def remove_project_artifact(project_id: str, artifact_version_id: str):
    async with _artifact_index_lock(project_id, artifact_version_id):
        _invalidate_project_search_cache(project_id)
        try:
            manifest = await project_artifact_generation_repository.begin_removal(
                project_id, artifact_version_id
            )
        except ProjectArtifactGenerationConflict as error:
            raise HTTPException(
                status_code=409, detail={"code": "ARTIFACT_REMOVAL_CONFLICT"}
            ) from error
        except Exception as error:
            raise HTTPException(
                status_code=503, detail={"code": "INDEX_MANIFEST_UNAVAILABLE"}
            ) from error
        if not await project_artifact_generation_repository.removal_is_current(manifest):
            raise HTTPException(status_code=409, detail={"code": "ARTIFACT_REMOVAL_SUPERSEDED"})
        delete_results = await asyncio.gather(
            vector_store.delete_project_artifact_version(project_id, artifact_version_id),
            bm25_store.delete_project_artifact_version(project_id, artifact_version_id),
            return_exceptions=True,
        )
        failed_stores = [
            store_name
            for store_name, result in zip(("qdrant", "bm25"), delete_results)
            if isinstance(result, BaseException)
        ]
        if failed_stores:
            logger.error(
                "Project artifact removal incomplete project={} artifact_version={} stores={}",
                project_id,
                artifact_version_id,
                failed_stores,
            )
            raise RuntimeError("project_artifact_removal_incomplete")
        if not await project_artifact_generation_repository.finish_removal(manifest):
            raise RuntimeError("project_artifact_removal_manifest_conflict")
        from src.knowledge.graph.repository import graph_repository

        graph_result = await graph_repository.delete_artifact_version(
            project_id, artifact_version_id
        )
        return {
            "status": "removed",
            "artifact_version_id": artifact_version_id,
            "graph_removed": graph_result[0]["removed"] if graph_result else 0,
        }


async def list_project_artifact_chunks(
    project_id: str,
    artifact_version_id: str,
    limit: int = 50,
    cursor: str | None = None,
):
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail={"code": "CHUNK_PAGE_SIZE_INVALID"})
    offset = None
    cursor_generation = None
    if cursor:
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode("ascii"))
            offset = json.loads(decoded.decode("utf-8"))
            if isinstance(offset, dict):
                cursor_generation = offset.get("generation")
                offset = offset.get("offset")
            if not isinstance(offset, (str, int)) or isinstance(offset, bool):
                raise ValueError("invalid_cursor_type")
        except (ValueError, UnicodeError, json.JSONDecodeError) as error:
            raise HTTPException(status_code=422, detail={"code": "CHUNK_CURSOR_INVALID"}) from error

    try:
        manifest = await project_artifact_generation_repository.get_or_migrate(
            project_id, artifact_version_id
        )
    except Exception as error:
        raise HTTPException(
            status_code=503, detail={"code": "INDEX_MANIFEST_UNAVAILABLE"}
        ) from error
    if manifest.get("status") != "ACTIVE" or not manifest.get("active_generation"):
        return {
            "project_id": project_id,
            "artifact_version_id": artifact_version_id,
            "items": [],
            "next_cursor": None,
        }
    active_generation = str(manifest["active_generation"])
    if cursor_generation and cursor_generation != active_generation:
        raise HTTPException(status_code=409, detail={"code": "CHUNK_CURSOR_STALE"})
    points, next_offset = await vector_store.scroll_artifact_version(
        project_id,
        artifact_version_id,
        limit,
        offset,
        active_generation,
    )
    try:
        current_manifest = await project_artifact_generation_repository.get_or_migrate(
            project_id, artifact_version_id
        )
    except Exception as error:
        raise HTTPException(
            status_code=503, detail={"code": "INDEX_MANIFEST_UNAVAILABLE"}
        ) from error
    if (
        current_manifest.get("status") != "ACTIVE"
        or current_manifest.get("active_generation") != active_generation
    ):
        raise HTTPException(status_code=409, detail={"code": "CHUNK_GENERATION_CHANGED"})
    next_cursor = (
        base64.urlsafe_b64encode(
            json.dumps(
                {"offset": next_offset, "generation": active_generation},
                separators=(",", ":"),
            ).encode("utf-8")
        ).decode("ascii")
        if next_offset is not None
        else None
    )
    try:
        items = [
            {
                "point_id": point["id"],
                "text": point["text"],
                "metadata": project_artifact_chunk_read_metadata(
                    point["text"],
                    point["metadata"],
                    project_id,
                    artifact_version_id,
                    active_generation,
                ),
            }
            for point in points
        ]
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        raise HTTPException(
            status_code=502, detail={"code": "CHUNK_POINT_PAYLOAD_INVALID"}
        ) from error
    return {
        "project_id": project_id,
        "artifact_version_id": artifact_version_id,
        "items": items,
        "next_cursor": next_cursor,
    }


async def search_project_knowledge(project_id: str, req: ProjectKnowledgeSearchRequest):
    cache_key = (
        project_id,
        req.query,
        tuple(sorted(req.artifact_types or [])),
        req.limit,
        req.requester_id,
        req.is_admin,
    )
    cached = SEARCH_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[0] < 30:
        try:
            visible_items = await retriever._filter_currently_accessible_sources(
                cached[1].get("items", []), req.requester_id, req.is_admin
            )
            visible_items = await project_artifact_generation_repository.filter_active(
                visible_items
            )
        except RetrievalUnavailableError:
            raise
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "DOCUMENT_ACCESS_VERIFICATION_UNAVAILABLE"},
            ) from error
        return {**cached[1], "items": visible_items}
    if cached:
        SEARCH_CACHE.pop(cache_key, None)
    filters = {"project_id": project_id}
    if req.artifact_types:
        filters["artifact_type"] = req.artifact_types
    try:
        documents = await retriever.retrieve(
            query=req.query,
            k=req.limit,
            requester_id=req.requester_id,
            is_admin=req.is_admin,
            metadata_filters=filters,
        )
    except RetrievalUnavailableError as error:
        raise HTTPException(status_code=503, detail={"code": "KNOWLEDGE_UNAVAILABLE"}) from error
    items = [
        {
            **public_retrieval_metadata(document.get("metadata", {})),
            "text": document.get("text", ""),
            "score": document.get("score", 0),
            "retrieval_source": "knowledge",
        }
        for document in documents
    ]
    try:
        items = await project_artifact_generation_repository.filter_active(items)
    except Exception as error:
        raise HTTPException(status_code=503, detail={"code": "INDEX_MANIFEST_UNAVAILABLE"}) from error
    result = {"items": items, "degraded_mode": "NORMAL", "error_code": None}
    if len(SEARCH_CACHE) >= 512:
        oldest_key = min(SEARCH_CACHE, key=lambda key: SEARCH_CACHE[key][0])
        SEARCH_CACHE.pop(oldest_key, None)
    SEARCH_CACHE[cache_key] = (time.monotonic(), result)
    return result
