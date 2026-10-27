import sys
from contextlib import contextmanager
from threading import Lock

from loguru import logger

from src.core.infrastructure.configuration import settings

_lock = Lock()
_provider = None
_tracer = None
_SAFE_TRACE_ATTRIBUTE_KEYS = frozenset(
    {
        "automation.run_id",
        "automation.kind",
        "automation.trigger",
        "automation.node",
        "ai.result.status",
        "ai.capability",
        "ai.review_type",
        "ai.evidence_count",
        "ai.candidate_count",
        "ai.obligation_count",
        "ai.clarification_count",
        "document.ingestion.status",
        "event.status",
        "mcp.operation",
        "mcp.status",
        "mcp.audit_persisted",
        "veriq.error.type",
    }
)


class _SafeSpan:
    def __init__(self, span):
        self._span = span

    def set_attribute(self, key, value):
        if key not in _SAFE_TRACE_ATTRIBUTE_KEYS or value is None:
            return
        if isinstance(value, str):
            if len(value.encode("utf-8")) > 256:
                return
        elif not isinstance(value, (bool, int, float)):
            return
        try:
            self._span.set_attribute(key, value)
        except Exception as error:
            logger.warning("AI trace attribute unavailable: {}", type(error).__name__)

    def record_error(self, error):
        self.set_attribute("veriq.error.type", type(error).__name__)
        try:
            from opentelemetry.trace import Status, StatusCode

            self._span.set_status(Status(StatusCode.ERROR))
        except Exception as trace_error:
            logger.warning("AI trace error status unavailable: {}", type(trace_error).__name__)

    def mark_completed(self):
        try:
            from opentelemetry.trace import Status, StatusCode

            self._span.set_status(Status(StatusCode.OK))
        except Exception as trace_error:
            logger.warning("AI trace completion status unavailable: {}", type(trace_error).__name__)


def initialize_tracing():
    global _provider, _tracer
    if not settings.AI_TRACE_ENABLED:
        return False
    with _lock:
        if _tracer is not None:
            return True
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            endpoint = settings.AI_TRACE_ENDPOINT.rstrip("/")
            if not endpoint.endswith("/v1/traces"):
                endpoint = f"{endpoint}/v1/traces"
            provider = TracerProvider(
                resource=Resource.create(
                    {
                        "service.name": "veriq-ai",
                        "openinference.project.name": settings.AI_TRACE_PROJECT,
                    }
                )
            )
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
            )
            trace.set_tracer_provider(provider)
            _provider = provider
            _tracer = trace.get_tracer("veriq.ai.automation")
            logger.info("AI trace exporter initialized")
            return True
        except Exception as error:
            logger.warning("AI trace exporter unavailable: {}", type(error).__name__)
            return False


@contextmanager
def trace_span(name: str, attributes: dict | None = None):
    if _tracer is None:
        yield None
        return
    try:
        span_context = _tracer.start_as_current_span(
            name,
            record_exception=False,
            set_status_on_exception=False,
        )
        span = _SafeSpan(span_context.__enter__())
    except Exception as error:
        logger.warning("AI trace span unavailable: {}", type(error).__name__)
        yield None
        return
    try:
        for key, value in (attributes or {}).items():
            span.set_attribute(key, value)
        try:
            yield span
        except BaseException as error:
            span.record_error(error)
            raise
        else:
            span.mark_completed()
    finally:
        try:
            span_context.__exit__(*sys.exc_info())
        except Exception as error:
            logger.warning("AI trace span close issue: {}", type(error).__name__)


def shutdown_tracing():
    global _provider, _tracer
    provider = _provider
    _provider = None
    _tracer = None
    if provider is None:
        return
    try:
        provider.force_flush(timeout_millis=5000)
        provider.shutdown()
    except Exception as error:
        logger.warning("AI trace exporter shutdown issue: {}", type(error).__name__)
