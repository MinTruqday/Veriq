import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

REQUESTS = Counter("qa_http_requests_total", "QA HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("qa_http_request_duration_seconds", "QA HTTP latency", ["path"])
KNOWLEDGE_LATENCY = Histogram(
    "knowledge_latency", "Project knowledge operation latency", ["operation"]
)
AI_GENERATION_LATENCY = Histogram(
    "ai_generation_latency", "AI generation operation latency", ["operation"]
)
AI_REQUESTS = Counter("testing_ai_requests_total", "Testing AI requests", ["operation", "status"])
IMPACT_LATENCY = Histogram("impact_latency", "Impact analysis latency")
IMPACT_FAILED = Counter("impact_failed", "Failed impact analyses")
PROPOSAL_ACCEPTANCE_RATE = Gauge(
    "proposal_acceptance_rate", "Accepted or edited proposals divided by reviewed proposals"
)
TRACE_ACCEPTANCE_RATE = Gauge(
    "trace_acceptance_rate", "Confirmed trace links divided by reviewed trace links"
)
UNCOVERED = Gauge("requirements_uncovered", "Requirements without confirmed tests")
STALE = Gauge("tests_stale", "Test cases needing maintenance")


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started_at = time.perf_counter()
        status_code = 500
        response = None
        failed = False
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            failed = True
            raise
        finally:
            route = request.scope.get("route")
            path = getattr(route, "path", None) or "unmatched"
            is_impact_analysis = path.endswith("/phan-tich-anh-huong") or (
                route is None and request.url.path.endswith("/phan-tich-anh-huong")
            )
            elapsed = time.perf_counter() - started_at
            LATENCY.labels(path).observe(elapsed)
            if is_impact_analysis:
                IMPACT_LATENCY.observe(elapsed)
                if failed or status_code >= 400:
                    IMPACT_FAILED.inc()
            REQUESTS.labels(request.method, path, status_code).inc()


async def metrics_endpoint(request=None):
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
