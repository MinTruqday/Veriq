import unittest
from unittest.mock import patch

from opentelemetry.trace import StatusCode

from src.core.infrastructure import observability


class FakeSpan:
    def __init__(self):
        self.attributes = {}
        self.status = None
        self.recorded_exceptions = []

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def set_status(self, status):
        self.status = status

    def record_exception(self, error):
        self.recorded_exceptions.append(error)


class FakeSpanContext:
    def __init__(self, span):
        self.span = span
        self.exit_info = None

    def __enter__(self):
        return self.span

    def __exit__(self, *exc_info):
        self.exit_info = exc_info
        return False


class FakeTracer:
    def __init__(self, span):
        self.span = span
        self.options = None
        self.context = FakeSpanContext(span)

    def start_as_current_span(self, name, **options):
        self.options = options
        return self.context


class PhoenixObservabilityTests(unittest.TestCase):
    def test_successful_span_records_only_allowlisted_metadata_and_ok_status(self):
        span = FakeSpan()
        tracer = FakeTracer(span)
        with patch.object(observability, "_tracer", tracer):
            with observability.trace_span(
                "automation.run",
                {
                    "automation.run_id": "run-123",
                    "ai.evidence_count": 4,
                    "ai.obligation_count": 2,
                    "ai.clarification_count": 1,
                    "prompt": "private requirement text",
                },
            ) as safe_span:
                safe_span.set_attribute("document.content", "private document text")

        self.assertEqual(
            tracer.options,
            {"record_exception": False, "set_status_on_exception": False},
        )
        self.assertEqual(
            span.attributes,
            {
                "automation.run_id": "run-123",
                "ai.evidence_count": 4,
                "ai.obligation_count": 2,
                "ai.clarification_count": 1,
            },
        )
        self.assertEqual(span.status.status_code, StatusCode.OK)
        self.assertEqual(span.recorded_exceptions, [])

    def test_exception_records_type_and_error_status_without_message_or_stack(self):
        span = FakeSpan()
        tracer = FakeTracer(span)
        failure = ValueError("private source text must not enter the trace")

        with patch.object(observability, "_tracer", tracer):
            with self.assertRaisesRegex(ValueError, "private source text"):
                with observability.trace_span("ai.model_generation"):
                    raise failure

        self.assertEqual(span.attributes, {"veriq.error.type": "ValueError"})
        self.assertEqual(span.status.status_code, StatusCode.ERROR)
        self.assertEqual(span.recorded_exceptions, [])
        self.assertIs(tracer.context.exit_info[1], failure)


if __name__ == "__main__":
    unittest.main()
