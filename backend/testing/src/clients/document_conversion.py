import base64

import httpx

from src.core.configuration import settings
from src.schemas.document_source import DocumentConversionResult


async def convert_requirement_source(
    data: bytes,
    filename: str,
    page_range: tuple[int, int] | None = None,
    document_id: str | None = None,
    project_id: str | None = None,
    owner_id: str | None = None,
    ocr_language: str | None = None,
) -> DocumentConversionResult:
    """Reuse the internal deterministic parser; never silently substitute plain text."""
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.DOCUMENT_PARSE_TIMEOUT_SECONDS, connect=10)
    ) as client:
        response = await client.post(
            f"{settings.AI_URL.rstrip('/')}/tri-thuc/chuyen-doi",
            headers={"X-Internal-Token": settings.SECRET_KEY},
            json={
                "data": base64.b64encode(data).decode("ascii"),
                "filename": filename,
                "page_range": page_range,
                "document_id": document_id,
                "project_id": project_id,
                "owner_id": owner_id,
                "ocr_language": ocr_language,
            },
        )
        response.raise_for_status()
    return DocumentConversionResult.model_validate(response.json()["data"])


async def clear_requirement_conversion_checkpoints(
    document_id: str, project_id: str, owner_id: str, source_hash: str
) -> None:
    async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5)) as client:
        response = await client.request(
            "DELETE",
            f"{settings.AI_URL.rstrip('/')}/tri-thuc/chuyen-doi/checkpoints",
            headers={"X-Internal-Token": settings.SECRET_KEY},
            json={
                "document_id": document_id,
                "project_id": project_id,
                "owner_id": owner_id,
                "source_hash": source_hash,
            },
        )
        response.raise_for_status()


async def read_requirement_source_image(
    project_id: str,
    document_id: str,
    asset_key: str,
) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=5)) as client:
        response = await client.get(
            f"{settings.AI_URL.rstrip('/')}/tri-thuc/tai-lieu/{document_id}/anh-nguon",
            headers={"X-Internal-Token": settings.SECRET_KEY},
            params={"project_id": project_id, "asset_key": asset_key},
        )
        response.raise_for_status()
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
    if content_type != "image/png" or not response.content:
        raise RuntimeError("REQUIREMENT_SOURCE_IMAGE_RESPONSE_INVALID")
    return response.content, content_type
