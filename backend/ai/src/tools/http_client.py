import asyncio
import uuid
from typing import Optional
from urllib.parse import urlsplit

import httpx
from loguru import logger

from src.core.infrastructure.configuration import settings

INTERNAL_API_URL = settings.INTERNAL_API_URL

_http_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(20),
        )
    return _http_client


async def make_api_request(method: str, url: str, **kwargs) -> httpx.Response:
    if method.upper() in ["POST", "PUT", "PATCH", "DELETE"]:
        headers = kwargs.get("headers", {})
        if "Idempotency-Key" not in headers:
            headers["Idempotency-Key"] = str(uuid.uuid4())
        kwargs["headers"] = headers

    max_retries = 3 if method.upper() == "GET" else 1
    client = get_client()
    parsed_url = urlsplit(url)
    target = f"{parsed_url.hostname or 'unknown'}{parsed_url.path}"
    logger.info(
        "Internal API request started method={} target={} max_attempts={}",
        method.upper(),
        target,
        max_retries,
    )
    for attempt in range(max_retries):
        started_at = asyncio.get_running_loop().time()
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in [429, 500, 502, 503, 504]:
                logger.info(
                    "Internal API request completed method={} target={} status={} attempt={} duration_ms={}",
                    method.upper(),
                    target,
                    response.status_code,
                    attempt + 1,
                    int((asyncio.get_running_loop().time() - started_at) * 1000),
                )
                return response
            if attempt == max_retries - 1:
                response.raise_for_status()
            logger.warning(
                "Internal API retry scheduled method={} target={} status={} attempt={}",
                method.upper(),
                target,
                response.status_code,
                attempt + 1,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.warning(
                "Internal API transient failure method={} target={} attempt={} error_type={}",
                method.upper(),
                target,
                attempt + 1,
                type(exc).__name__,
            )
            if attempt == max_retries - 1:
                logger.exception(
                    "Internal API request exhausted retries method={} target={} attempts={}",
                    method.upper(),
                    target,
                    max_retries,
                )
                raise
        except Exception:
            logger.exception(
                "Internal API request failed method={} target={} attempt={}",
                method.upper(),
                target,
                attempt + 1,
            )
            raise
        await asyncio.sleep(2**attempt)
    raise RuntimeError("Internal API request ended without a response")
