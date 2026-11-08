import httpx

from src.core.infrastructure.configuration import settings


def service_url(service_name: str, path: str = "") -> str:
    setting_name = f"{service_name.upper()}_INTERNAL_URL"
    base_url = getattr(settings, setting_name, None)
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError(f"Unknown internal service {service_name}")
    if path:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    return base_url.rstrip("/")


async def internal_request(
    method: str,
    service_name: str,
    path: str,
    *,
    params: dict | None = None,
    payload: dict | None = None,
    timeout: float | None = None,
) -> httpx.Response:
    request_timeout = timeout or 20
    async with httpx.AsyncClient(timeout=request_timeout) as client:
        return await client.request(
            method,
            service_url(service_name, path),
            headers={"X-Internal-Token": settings.SECRET_KEY},
            params=params,
            json=payload,
        )


async def health_request(service_name: str) -> httpx.Response:
    return await internal_request("GET", service_name, "/san-sang")
