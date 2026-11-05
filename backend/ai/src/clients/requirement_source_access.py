import httpx

from src.core.infrastructure.configuration import settings


class RequirementSourceAccessClient:
    async def accessible_many(
        self,
        project_id: str,
        document_ids: list[str],
        requester_id: str,
        is_admin: bool,
    ) -> dict[str, str]:
        if not document_ids:
            return {}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.INTERNAL_API_URL.rstrip('/')}/kiem-thu/noi-bo/tai-lieu-yeu-cau/kiem-tra-quyen-ai",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json={
                    "project_id": project_id,
                    "document_ids": list(dict.fromkeys(map(str, document_ids))),
                    "requester_id": str(requester_id or ""),
                    "is_admin": bool(is_admin),
                },
            )
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        records = data.get("documents") if isinstance(data, dict) else None
        if not isinstance(records, list):
            raise RuntimeError("requirement_source_access_response_invalid")
        accessible = {}
        for record in records:
            if (
                not isinstance(record, dict)
                or not isinstance(record.get("document_id"), str)
                or not isinstance(record.get("content_hash"), str)
                or not record["content_hash"]
            ):
                raise RuntimeError("requirement_source_access_record_invalid")
            accessible[record["document_id"]] = record["content_hash"]
        return accessible


requirement_source_access_client = RequirementSourceAccessClient()
