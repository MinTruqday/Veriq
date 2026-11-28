import httpx

from src.core.infrastructure.configuration import settings


class NotificationClient:
    async def send(
        self,
        target_user_id: str,
        title: str,
        body: str,
        notification_type: str,
        idempotency_key: str | None = None,
    ):
        if not settings.NOTIFICATION_URL:
            return None
        async with httpx.AsyncClient(
            timeout=20
        ) as client:
            response = await client.post(
                f"{settings.NOTIFICATION_URL}/thong-bao/gui-di",
                json={
                    "target_user_id": target_user_id,
                    "title": title,
                    "body": body,
                    "type": notification_type,
                    "idempotency_key": idempotency_key,
                },
                headers={"X-Internal-Token": settings.SECRET_KEY},
            )
        response.raise_for_status()
        return response.json()


notification_client = NotificationClient()
