import os
import unittest
from unittest.mock import patch

from src.core.infrastructure.observability import LangfuseCloudExporter


class TestLangfuseCloudExporterConfiguration(unittest.TestCase):
    def test_only_standard_allowlisted_https_endpoint_is_enabled(self):
        environment = {
            "AI_TRACE_EXPORT_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "public-test-key",
            "LANGFUSE_SECRET_KEY": "secret-test-key",
        }
        with patch.dict(os.environ, environment):
            for endpoint in (
                "https://user@cloud.langfuse.com",
                "https://user:password@cloud.langfuse.com",
                "https://cloud.langfuse.com:8443",
                "https://cloud.langfuse.com:invalid",
            ):
                with self.subTest(endpoint=endpoint), patch.dict(
                    os.environ, {"LANGFUSE_HOST": endpoint}
                ):
                    self.assertFalse(LangfuseCloudExporter().configured)

            with patch.dict(
                os.environ, {"LANGFUSE_HOST": "https://cloud.langfuse.com"}
            ):
                self.assertTrue(LangfuseCloudExporter().configured)
