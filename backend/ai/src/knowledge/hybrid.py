import json

from langchain_core.runnables import RunnableConfig

from src.knowledge.evidence import package
from src.memory.long_term import long_term_memory
from src.runtime.limits import limits
from src.schemas.agent import EvidenceItem


async def hybrid_evidence(project_id, query, requester_id, token=None, limit=None):
    maximum = min(limit or limits.evidence_items, limits.evidence_items)
    items = []
    degraded = []
    if token:
        try:
            from src.tools.testing import retrieve_project_evidence

            raw = await retrieve_project_evidence.ainvoke(
                {"project_id": project_id, "instruction": query, "artifact_types": ""},
                config=RunnableConfig(
                    configurable={"token": token, "project_id": project_id}
                ),
            )
            database_result = json.loads(raw)
            for match in database_result.get("items", [])[:maximum]:
                items.append(
                    EvidenceItem(
                        artifact_type=str(match.get("artifact_type") or "Artifact"),
                        artifact_id=str(match.get("artifact_id") or ""),
                        artifact_version_id=match.get("artifact_version_id"),
                        source="database",
                        authority=str(match.get("authority") or "project_source"),
                        score=max(0, min(1, float(match.get("score") or 0))),
                        text=str(match.get("text") or ""),
                        project_id=project_id,
                    )
                )
        except Exception:
            degraded.append("KNOWLEDGE_UNAVAILABLE")
    authoritative_refs = {
        item.artifact_version_id or item.artifact_id
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
        for match in matches:
            metadata = match["metadata"]
            reference = metadata.get("artifact_version_id") or metadata.get("artifact_id")
            if reference not in authoritative_refs:
                continue
            items.append(
                EvidenceItem(
                    artifact_type=str(metadata.get("artifact_type") or "Document"),
                    artifact_id=str(metadata.get("artifact_id") or match["id"]),
                    artifact_version_id=metadata.get("artifact_version_id"),
                    source="vector",
                    authority=str(metadata.get("authority") or "semantic_index"),
                    score=max(0, min(1, float(match.get("score") or 0))),
                    text=str(match.get("text") or ""),
                    project_id=project_id,
                )
            )
    except Exception:
        degraded.append("KNOWLEDGE_UNAVAILABLE")
    try:
        from src.knowledge.graph.repository import graph_repository

        for match in await graph_repository.search(project_id, query, maximum):
            reference = match.get("artifact_version_id") or match.get("artifact_id")
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
    return package(project_id, query, items, degraded, maximum)
