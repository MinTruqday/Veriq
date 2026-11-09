from src.schemas.agent import EvidencePackage


def deduplicate(items):
    selected = {}
    for item in items:
        artifact_ref = item.artifact_version_id or item.artifact_id
        key = (
            item.artifact_type,
            artifact_ref,
            item.chunk_id if item.chunk_id else None,
        )
        previous = selected.get(key)
        candidate_rank = (item.source == "database", item.score)
        previous_rank = (
            (previous.source == "database", previous.score) if previous is not None else None
        )
        if previous is None or candidate_rank > previous_rank:
            selected[key] = item
    return sorted(selected.values(), key=lambda item: item.score, reverse=True)


def package(project_id, query, items, degraded_flags=None, limit=100):
    scoped = [item for item in items if item.project_id == project_id]
    ranked_by_source = {}
    for item in scoped:
        ranked_by_source.setdefault(item.source, []).append(item)
    normalized = []
    for source_items in ranked_by_source.values():
        source_items.sort(key=lambda item: item.score, reverse=True)
        normalized.extend(
            item.model_copy(update={"score": 1 / rank})
            for rank, item in enumerate(source_items, start=1)
        )
    return EvidencePackage(
        project_id=project_id,
        query=query,
        items=deduplicate(normalized)[:limit],
        degraded_flags=list(dict.fromkeys(degraded_flags or [])),
    )
