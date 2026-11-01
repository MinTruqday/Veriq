def split_source_evidence(artifact_type, artifact_version_id, text, limit=3900):
    normalized = str(text or "").strip()
    if not normalized:
        return []
    chunks = []
    offset = 0
    while offset < len(normalized):
        end = min(offset + limit, len(normalized))
        if end < len(normalized):
            boundary = max(
                normalized.rfind("\n", offset, end),
                normalized.rfind(" ", offset, end),
            )
            if boundary > offset:
                end = boundary
        chunk = normalized[offset:end].strip()
        if chunk:
            chunks.append({
                "artifact_type": artifact_type,
                "artifact_version_id": artifact_version_id,
                "chunk_index": len(chunks),
                "text": chunk,
            })
        offset = end
        while offset < len(normalized) and normalized[offset].isspace():
            offset += 1
    return chunks
