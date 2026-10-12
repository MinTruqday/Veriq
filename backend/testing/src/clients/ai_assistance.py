import json
from typing import Awaitable, Callable

import httpx

from src.core.configuration import settings


class AIAssistanceClient:
    async def request(
        self,
        payload: dict,
        stream_sink: Callable[[dict], Awaitable[None]] | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=1800) as client:
            if not stream_sink:
                response = await client.post(
                    f"{settings.AI_URL.rstrip('/')}/suy-luan/noi-bo/kiem-thu/ho-tro",
                    headers={"X-Internal-Token": settings.SECRET_KEY},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

            async with client.stream(
                "POST",
                f"{settings.AI_URL.rstrip('/')}/suy-luan/noi-bo/kiem-thu/ho-tro/stream",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json=payload,
            ) as response:
                if response.is_error:
                    await response.aread()
                response.raise_for_status()
                result = None
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if event.get("type") == "delta":
                        await stream_sink({"type": "delta", "delta": str(event.get("delta") or "")})
                    elif event.get("type") == "result":
                        result = event.get("data")
                    elif event.get("type") == "error":
                        raise RuntimeError(str(event.get("code") or "AI_STREAM_FAILED"))
            if not isinstance(result, dict):
                raise RuntimeError("AI_STREAM_RESULT_MISSING")
            return result


ai_assistance_client = AIAssistanceClient()
