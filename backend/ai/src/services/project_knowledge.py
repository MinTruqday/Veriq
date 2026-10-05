import hashlib
import time
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException

from src.schemas.project import ProjectArtifactIndexRequest, ProjectKnowledgeSearchRequest
from src.services.chunking import chunker
from src.services.embedding import embedder
from src.services.retrieval import RetrievalUnavailableError, retriever
from src.store.bm25 import bm25_store
from src.store.vector import vector_store

SEARCH_CACHE: dict[tuple, tuple[float, dict]] = {}


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
    return {
        **req.metadata,
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
        "source_hash": req.metadata.get("source_hash")
        or hashlib.sha256(req.text.encode("utf-8")).hexdigest(),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }


async def index_project_artifact(project_id: str, req: ProjectArtifactIndexRequest):
    metadata = project_artifact_metadata(project_id, req)
    bounded_text = req.text[:50000]
    chunks = await chunker.chunk_document(bounded_text, metadata)
    documents = [chunk["text"] for chunk in chunks]
    vectors = await embedder.embed_batch([f"{req.title} {text}" for text in documents])
    ids = [
        str(uuid5(NAMESPACE_URL, f"{project_id}:{req.artifact_version_id}:{index}"))
        for index in range(len(chunks))
    ]
    metadatas = [
        {**metadata, **chunk.get("metadata", {}), "chunk_index": index}
        for index, chunk in enumerate(chunks)
    ]
    old_ids = await vector_store.ids_by_artifact_version(project_id, req.artifact_version_id)
    await vector_store.delete_ids(old_ids)
    await bm25_store.delete_ids(old_ids)
    await vector_store.upsert(ids, vectors, documents, metadatas)
    await bm25_store.upsert(
        [
            {"id": point_id, "text": text, "metadata": item_metadata}
            for point_id, text, item_metadata in zip(ids, documents, metadatas)
        ]
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
                "text": bounded_text,
                "status": req.status,
                "authority": req.authority,
            },
        )
    except Exception:
        graph_status = {"status": "UNAVAILABLE", "reason_code": "GRAPH_UNAVAILABLE"}
    for key in tuple(SEARCH_CACHE):
        if key[0] == project_id:
            SEARCH_CACHE.pop(key, None)
    return {
        "status": "indexed",
        "project_id": project_id,
        "artifact_version_id": req.artifact_version_id,
        "chunks_count": len(chunks),
        "graph": graph_status,
    }


async def remove_project_artifact(project_id: str, artifact_version_id: str):
    point_ids = await vector_store.ids_by_artifact_version(project_id, artifact_version_id)
    await vector_store.delete_ids(point_ids)
    await bm25_store.delete_ids(point_ids)
    for key in tuple(SEARCH_CACHE):
        if key[0] == project_id:
            SEARCH_CACHE.pop(key, None)
    from src.knowledge.graph.repository import graph_repository

    graph_result = await graph_repository.delete_artifact_version(project_id, artifact_version_id)
    return {
        "status": "removed",
        "artifact_version_id": artifact_version_id,
        "graph_removed": graph_result[0]["removed"] if graph_result else 0,
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
        return cached[1]
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
            **document.get("metadata", {}),
            "text": document.get("text", ""),
            "score": document.get("score", 0),
            "retrieval_source": "knowledge",
        }
        for document in documents
    ]
    result = {"items": items, "degraded_mode": "NORMAL", "error_code": None}
    if len(SEARCH_CACHE) >= 512:
        oldest_key = min(SEARCH_CACHE, key=lambda key: SEARCH_CACHE[key][0])
        SEARCH_CACHE.pop(oldest_key, None)
    SEARCH_CACHE[cache_key] = (time.monotonic(), result)
    return result
