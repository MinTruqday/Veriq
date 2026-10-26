import json

from langchain_core.runnables import RunnableConfig

from src.knowledge.evidence import package
from src.memory.long_term import long_term_memory
from src.repositories.project_artifact_generation import (
    project_artifact_generation_repository,
)
from src.runtime.limits import limits
from src.schemas.agent import EvidenceItem


async def hybrid_evidence(
    project_id, query, requester_id, token=None, limit=None, automation_run_id=None
):
    maximum = min(limit or limits.evidence_items, limits.evidence_items)
    items = []
    degraded = []
    vector_generation_by_item = {}
    if token:
        try:
            from src.tools.knowledge_tools import retrieve_project_evidence

            raw = await retrieve_project_evidence.ainvoke(
                {"project_id": project_id, "instruction": query, "artifact_types": ""},
                config=RunnableConfig(
                    configurable={
                        "token": token,
                        "project_id": project_id,
                        "automation_run_id": automation_run_id,
                    }
                ),
            )
            database_result = json.loads(raw)
            for match in database_result.get("items", [])[:maximum]:
                passages = match.get("retrieved_passages") or [match]
                for passage in passages:
                    items.append(
                        EvidenceItem(
                            artifact_type=str(match.get("artifact_type") or "Artifact"),
                            artifact_id=str(match.get("artifact_id") or ""),
                            artifact_version_id=match.get("artifact_version_id"),
                            source="database",
                            authority=str(match.get("authority") or "project_source"),
                            score=max(
                                0,
                                min(
                                    1,
                                    float(passage.get("score", match.get("score")) or 0),
                                ),
                            ),
                            text=str(passage.get("text") or match.get("text") or ""),
                            chunk_id=passage.get("chunk_id", match.get("chunk_id")),
                            chunk_index=passage.get("chunk_index", match.get("chunk_index")),
                            chunk_type=passage.get("chunk_type", match.get("chunk_type")),
                            page_numbers=list(
                                passage.get("page_numbers", match.get("page_numbers")) or []
                            ),
                            source_spans=list(
                                passage.get("source_spans", match.get("source_spans")) or []
                            ),
                            source_hash=passage.get("source_hash", match.get("source_hash")),
                            project_id=project_id,
                        )
                    )
        except Exception:
            degraded.append("KNOWLEDGE_UNAVAILABLE")
    authoritative_refs = {
        (item.artifact_type, item.artifact_version_id or item.artifact_id)
        for item in items
        if item.source == "database"
    }
    try:
        from src.services.embedding import embedder
        from src.store.vector import vector_store

        vector = await embedder.embed_query(query)
        matches = await vector_store.query(
            vector,
            limit=maximum,
            requester_id=requester_id,
            metadata_filters={"project_id": project_id},
        )
        matches = await project_artifact_generation_repository.filter_active(matches)
        for match in matches:
            metadata = match["metadata"]
            reference = (
                metadata.get("artifact_type"),
                metadata.get("artifact_version_id") or metadata.get("artifact_id"),
            )
            if reference not in authoritative_refs:
                continue
            evidence_item = EvidenceItem(
                artifact_type=str(metadata.get("artifact_type") or "Document"),
                artifact_id=str(metadata.get("artifact_id") or match["id"]),
                artifact_version_id=metadata.get("artifact_version_id"),
                source="vector",
                authority=str(metadata.get("authority") or "semantic_index"),
                score=max(0, min(1, float(match.get("score") or 0))),
                text=str(match.get("text") or ""),
                chunk_id=metadata.get("chunk_id"),
                chunk_index=metadata.get("chunk_index"),
                chunk_type=metadata.get("chunk_type"),
                page_numbers=list(metadata.get("page_numbers") or []),
                source_spans=list(metadata.get("source_spans") or []),
                source_hash=metadata.get("source_hash"),
                project_id=project_id,
            )
            items.append(evidence_item)
            vector_generation_by_item[id(evidence_item)] = {
                "metadata": {
                    "project_id": project_id,
                    "artifact_version_id": metadata.get("artifact_version_id"),
                    "index_generation": metadata.get("index_generation"),
                }
            }
    except Exception:
        degraded.append("KNOWLEDGE_UNAVAILABLE")
    try:
        from src.knowledge.graph.repository import graph_repository

        for match in await graph_repository.search(project_id, query, maximum):
            reference = (
                match.get("artifact_type"),
                match.get("artifact_version_id") or match.get("artifact_id"),
            )
            if reference not in authoritative_refs:
                continue
            items.append(
                EvidenceItem(
                    artifact_type=str(match.get("artifact_type") or "Artifact"),
                    artifact_id=str(match.get("artifact_id") or ""),
                    artifact_version_id=match.get("artifact_version_id"),
                    source="graph",
                    authority=str(match.get("authority") or "graph"),
                    score=1 / (1 + int(match.get("distance") or 0)),
                    text=str(match.get("text") or ""),
                    relationship_path=list(match.get("relationship_path") or []),
                    project_id=project_id,
                )
            )
    except Exception:
        degraded.append("GRAPH_UNAVAILABLE")
    try:
        for memory in await long_term_memory.list(project_id, requester_id, maximum):
            text = str(memory.get("proposal") or memory.get("objective") or "")
            if query.lower() in text.lower():
                items.append(
                    EvidenceItem(
                        artifact_type="LongTermMemory",
                        artifact_id=str(memory["_id"]),
                        source="memory",
                        authority="verified_outcome",
                        score=0.8,
                        text=text,
                        project_id=project_id,
                    )
                )
    except Exception:
        degraded.append("MEMORY_UNAVAILABLE")
    if vector_generation_by_item:
        try:
            active_vector_generations = await project_artifact_generation_repository.filter_active(
                list(vector_generation_by_item.values())
            )
            active_keys = {
                (
                    str(record["metadata"].get("artifact_version_id") or ""),
                    str(record["metadata"].get("index_generation") or "LEGACY"),
                )
                for record in active_vector_generations
            }
            items = [
                item
                for item in items
                if item.source != "vector"
                or (
                    str(item.artifact_version_id or ""),
                    str(
                        vector_generation_by_item[id(item)]["metadata"].get("index_generation")
                        or "LEGACY"
                    ),
                )
                in active_keys
            ]
        except Exception:
            degraded.append("KNOWLEDGE_UNAVAILABLE")
            items = [item for item in items if item.source != "vector"]
    return package(project_id, query, items, degraded, maximum)
