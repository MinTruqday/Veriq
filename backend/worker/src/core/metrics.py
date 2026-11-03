import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.infrastructure.configuration import settings


class MetricsCollector:
    def __init__(self):
        self._request_count = defaultdict(int)
        self._request_duration = defaultdict(float)
        self._error_count = defaultdict(int)
        self._queue_depth = defaultdict(int, {settings.WORKER_QUEUE_NAME: 0})

    def change_queue_depth(self, queue_name: str, amount: int):
        self._queue_depth[queue_name] = max(0, self._queue_depth[queue_name] + amount)

    def record(self, method: str, path: str, status: int, duration: float):
        key = f"{method}_{path}"
        self._request_count[key] += 1
        self._request_duration[key] += duration
        if status >= 500:
            self._error_count[key] += 1

    def render(self, service_name: str) -> str:
        lines = []
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for key, count in self._request_count.items():
            method, path = key.split("_", 1)
            lines.append(
                f'http_requests_total{{service="{service_name}",method="{method}",path="{path}"}} {count}'
            )
        lines.append("# HELP http_request_duration_seconds_total Total request duration in seconds")
        lines.append("# TYPE http_request_duration_seconds_total counter")
        for key, duration in self._request_duration.items():
            method, path = key.split("_", 1)
            lines.append(
                f'http_request_duration_seconds_total{{service="{service_name}",method="{method}",path="{path}"}} {duration:.4f}'
            )
        lines.append("# HELP http_errors_total Total HTTP 5xx errors")
        lines.append("# TYPE http_errors_total counter")
        for key, count in self._error_count.items():
            method, path = key.split("_", 1)
            lines.append(
                f'http_errors_total{{service="{service_name}",method="{method}",path="{path}"}} {count}'
            )
        lines.append("# HELP worker_queue_depth Number of queued testing jobs")
        lines.append("# TYPE worker_queue_depth gauge")
        for queue_name, depth in self._queue_depth.items():
            lines.append(f'worker_queue_depth{{queue="{queue_name}"}} {depth}')
        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/so-lieu":
            return await call_next(request)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            metrics_collector.record(
                method=request.method,
                path=path,
                status=status_code,
                duration=time.perf_counter() - start,
            )


def metrics_endpoint(service_name: str):
    async def handler(request: Request):
        return PlainTextResponse(
            content=metrics_collector.render(service_name), media_type="text/plain; version=0.0.4"
        )

    return handler
