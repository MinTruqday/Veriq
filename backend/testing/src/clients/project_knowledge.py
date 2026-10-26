import math

import httpx
from fastapi.encoders import jsonable_encoder

from src.core.configuration import settings


async def index_artifact(
    project_id,
    artifact_type,
    artifact_id,
    artifact_version_id,
    title,
    text,
    status,
    authority,
    version=None,
    module="",
    source_structure=None,
    **metadata,
) -> bool:
    if not str(text or "").strip():
        return False
    payload = jsonable_encoder(
        {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "artifact_version_id": artifact_version_id,
            "title": title,
            "text": str(text),
            "status": status,
            "authority": authority,
            "version": version,
            "module": module,
            "source_structure": source_structure or [],
            "metadata": metadata,
        }
    )
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/tri-thuc/du-an/{project_id}/doi-tuong",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
        return isinstance(result, dict) and result.get("status") == "indexed"
    except httpx.HTTPError:
        return False


async def remove_artifact(project_id, artifact_version_id) -> bool:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.delete(
                f"{settings.AI_URL.rstrip('/')}/tri-thuc/du-an/{project_id}/doi-tuong/{artifact_version_id}",
                headers={"X-Internal-Token": settings.SECRET_KEY},
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


async def search_project_with_status(project_id, query, artifact_types, limit, user) -> dict:
    try:
        async with httpx.AsyncClient(
            timeout=20
        ) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/tri-thuc/du-an/{project_id}/tim-kiem",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json={
                    "query": query,
                    "artifact_types": artifact_types or [],
                    "limit": limit,
                    "requester_id": user.id,
                    "is_admin": user.is_system_admin,
                },
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        return {
            "items": [],
            "degraded_mode": "DEGRADED_KNOWLEDGE",
            "error_code": "KNOWLEDGE_UNAVAILABLE",
        }


async def search_project(project_id, query, artifact_types, limit, user) -> list:
    result = await search_project_with_status(project_id, query, artifact_types, limit, user)
    return result.get("items", [])


async def list_project_artifact_chunks(
    project_id: str,
    artifact_version_id: str,
    limit: int,
    cursor: str | None,
) -> dict:
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{settings.AI_URL.rstrip('/')}/tri-thuc/du-an/{project_id}/doi-tuong/{artifact_version_id}/cac-doan",
            headers={"X-Internal-Token": settings.SECRET_KEY},
            params=params,
        )
        response.raise_for_status()
        result = response.json()
    if not isinstance(result, dict) or not isinstance(result.get("items"), list):
        raise RuntimeError("KNOWLEDGE_CHUNK_LIST_RESPONSE_INVALID")
    return result


async def compare_project_text_semantics(query: str, passages: list[str]) -> list[float]:
    if not query.strip() or not passages:
        return []
    base_url = settings.AI_URL.rstrip("/")
    headers = {"X-Internal-Token": settings.SECRET_KEY}
    async with httpx.AsyncClient(timeout=60) as client:
        query_response = await client.post(
            f"{base_url}/tri-thuc/bieu-dien-vector/truy-van",
            headers=headers,
            json={"text": query},
        )
        query_response.raise_for_status()
        query_vector = query_response.json()["data"]["embedding"]
        passage_response = await client.post(
            f"{base_url}/tri-thuc/bieu-dien-vector/hang-loat",
            headers=headers,
            json={"texts": passages},
        )
        passage_response.raise_for_status()
        passage_vectors = passage_response.json()["data"]["embeddings"]
    query_norm = math.sqrt(sum(value * value for value in query_vector))
    scores = []
    for vector in passage_vectors:
        vector_norm = math.sqrt(sum(value * value for value in vector))
        scores.append(
            sum(left * right for left, right in zip(query_vector, vector))
            / max(query_norm * vector_norm, 1e-12)
        )
    if len(scores) != len(passages):
        raise RuntimeError("SEMANTIC_MATCH_VECTOR_COUNT_INVALID")
    return scores
