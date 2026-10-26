import asyncio
import os
import re
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import uuid4

import httpx


_ALLOWED_HOSTS = {
    "cloud.langfuse.com",
    "us.cloud.langfuse.com",
    "jp.cloud.langfuse.com",
    "hipaa.cloud.langfuse.com",
}
_ALLOWED_STEPS = {
    "intake",
    "permission_check",
    "source_extract",
    "document_parse",
    "blueprint",
    "generation",
    "validation",
    "deduplication",
    "impact_analysis",
    "publication",
    "execution",
    "verification",
    "benchmark",
    "retrieval",
    "provider_call",
    "tool_call",
    "automation_run",
    "resume",
    "checkpoint",
    "indexing",
}
_ALLOWED_STATUSES = {"ok", "error", "cancelled", "waiting_input"}
_ALLOWED_ERROR_CODES = {
    "provider_timeout",
    "provider_unavailable",
    "invalid_output",
    "permission_denied",
    "grounding_failed",
    "rate_limited",
    "cancelled",
    "unknown",
}
_SAFE_MODEL = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


@dataclass(frozen=True)
class SafeTraceMetadata:
    run_id: str
    step: str
    model: str | None
    duration_ms: int
    status: str
    retry_count: int = 0
    error_code: str | None = None


class LangfuseCloudExporter:
    def __init__(self):
        self.enabled = os.getenv("AI_TRACE_EXPORT_ENABLED", "false").strip().lower() == "true"
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
        configured_host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").strip()
        parsed_host = urlparse(configured_host)
        try:
            allowed_port = parsed_host.port in (None, 443)
        except ValueError:
            allowed_port = False
        self.host = configured_host.rstrip("/")
        self.configured = (
            self.enabled
            and bool(self.public_key)
            and bool(self.secret_key)
            and parsed_host.scheme == "https"
            and parsed_host.hostname in _ALLOWED_HOSTS
            and parsed_host.username is None
            and parsed_host.password is None
            and allowed_port
            and parsed_host.path in ("", "/")
            and parsed_host.query == ""
            and parsed_host.fragment == ""
        )
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    @staticmethod
    def new_run_id() -> str:
        return uuid4().hex

    @staticmethod
    def _metadata(value: SafeTraceMetadata) -> SafeTraceMetadata:
        run_id = value.run_id.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise ValueError("run_id must be an opaque 128-bit hexadecimal identifier")
        step = value.step.strip()
        if step not in _ALLOWED_STEPS:
            step = "other"
        model = value.model.strip() if value.model else None
        if model and not _SAFE_MODEL.fullmatch(model):
            model = None
        status = value.status if value.status in _ALLOWED_STATUSES else "error"
        error_code = value.error_code if value.error_code in _ALLOWED_ERROR_CODES else None
        if status == "error" and error_code is None:
            error_code = "unknown"
        duration_ms = max(0, min(int(value.duration_ms), 86_400_000))
        retry_count = max(0, min(int(value.retry_count), 100))
        return SafeTraceMetadata(
            run_id=run_id,
            step=step,
            model=model,
            duration_ms=duration_ms,
            status=status,
            retry_count=retry_count,
            error_code=error_code,
        )

    @staticmethod
    def _attribute(key: str, value: str | int) -> dict:
        typed_value = {"stringValue": value} if isinstance(value, str) else {"intValue": str(value)}
        return {"key": key, "value": typed_value}

    def _payload(self, metadata: SafeTraceMetadata) -> dict:
        trace_id = metadata.run_id
        span_id = secrets.token_hex(8)
        end_ns = time.time_ns()
        start_ns = end_ns - metadata.duration_ms * 1_000_000
        attributes = [
            self._attribute("veriq.step", metadata.step),
            self._attribute("veriq.status", metadata.status),
            self._attribute("veriq.retry_count", metadata.retry_count),
        ]
        if metadata.model:
            attributes.append(self._attribute("gen_ai.request.model", metadata.model))
        if metadata.error_code:
            attributes.append(self._attribute("veriq.error_code", metadata.error_code))
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [self._attribute("service.name", "veriq-ai")]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "veriq.ai.safe-tracing"},
                            "spans": [
                                {
                                    "traceId": trace_id,
                                    "spanId": span_id,
                                    "name": metadata.step,
                                    "kind": 1,
                                    "startTimeUnixNano": str(start_ns),
                                    "endTimeUnixNano": str(end_ns),
                                    "attributes": attributes,
                                    "status": {
                                        "code": (
                                            1
                                            if metadata.status == "ok"
                                            else 2
                                            if metadata.status == "error"
                                            else 0
                                        )
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]
        }

    async def export(self, value: SafeTraceMetadata) -> bool:
        if not self.configured:
            return False
        try:
            metadata = self._metadata(value)
            async with self._lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=2.0))
                response = await self._client.post(
                    f"{self.host}/api/public/otel/v1/traces",
                    json=self._payload(metadata),
                    auth=(self.public_key, self.secret_key),
                    headers={
                        "content-type": "application/json",
                        "x-langfuse-ingestion-version": "4",
                    },
                )
            return 200 <= response.status_code < 300
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError, TypeError, OverflowError):
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


langfuse_cloud_exporter = LangfuseCloudExporter()
