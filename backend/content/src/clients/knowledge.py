import httpx
from fastapi import HTTPException

from src.core.infrastructure.configuration import settings


class KnowledgeClient:
    async def index_document(
        self,
        document_id: str,
        user_id: str,
        superseded_document_id: str = "",
        event_id: str = "",
    ):
        params = {"document_id": document_id, "user_id": user_id}
        if event_id:
            params["event_id"] = event_id
        if superseded_document_id:
            params["superseded_document_id"] = superseded_document_id
        async with httpx.AsyncClient(
            timeout=20
        ) as client:
            response = await client.post(
                f"{settings.AI_URL}/su-kien/moc-goi/tai-lieu-dang-tai",
                params=params,
                headers={"X-Internal-Token": settings.SECRET_KEY},
            )
        response.raise_for_status()
        return response.json()

    async def delete_document(self, document_id: str, requester_id: str, is_admin: bool = False):
        try:
            async with httpx.AsyncClient(
                timeout=20
            ) as client:
                response = await client.delete(
                    f"{settings.AI_URL}/tri-thuc/tai-lieu/{document_id}",
                    headers={"X-Internal-Token": settings.SECRET_KEY},
                    params={"requester_id": requester_id, "is_admin": str(is_admin).lower()},
                )
        except httpx.HTTPError as error:
            raise HTTPException(status_code=503, detail="Không thể xóa chỉ mục tài liệu") from error
        if response.status_code >= 400:
            raise HTTPException(status_code=503, detail="Không thể xóa chỉ mục tài liệu")
        return response.json()


knowledge_client = KnowledgeClient()
