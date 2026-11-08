from typing import Optional
from urllib.parse import quote

import httpx

from src.core.infrastructure.configuration import settings


class AccountClient:
    @staticmethod
    async def session_is_valid(user_id: str, session_id: str) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=20
            ) as client:
                response = await client.get(
                    f"{settings.AUTHENTICATION_URL}/xac-thuc/noi-bo/phien/{quote(session_id, safe='')}/nguoi-dung/{quote(user_id, safe='')}",
                    headers={"X-Internal-Token": settings.SECRET_KEY},
                )
            response.raise_for_status()
            return bool(response.json().get("data", {}).get("valid"))
        except (httpx.HTTPError, ValueError):
            return False

    @staticmethod
    async def get_by_email(email: str) -> Optional[dict]:
        return await AccountClient._get(
            f"/xac-thuc/noi-bo/tai-khoan/thu-dien-tu/{quote(email, safe='')}"
        )

    @staticmethod
    async def _get(path: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(
                timeout=20
            ) as client:
                response = await client.get(
                    f"{settings.AUTHENTICATION_URL}{path}",
                    headers={"X-Internal-Token": settings.SECRET_KEY},
                )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json().get("data")
        except (httpx.HTTPError, ValueError):
            return None
