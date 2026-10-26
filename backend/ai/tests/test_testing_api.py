import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.tools import testing_api


class TestingApiErrorHandlingTests(unittest.IsolatedAsyncioTestCase):
    async def test_string_error_detail_is_preserved_as_a_safe_upstream_failure(self):
        response = SimpleNamespace(
            status_code=403,
            json=lambda: {"detail": "Project access denied"},
        )
        with patch(
            "src.tools.testing_api.make_api_request", new=AsyncMock(return_value=response)
        ):
            result = await testing_api.call("GET", "/du-an/p1", {"configurable": {"token": "Bearer x"}})

        decoded = json.loads(result)
        self.assertEqual(decoded["status"], "qa_operation_failed")
        self.assertEqual(decoded["upstream_status"], 403)
        self.assertEqual(decoded["error"]["code"], "UPSTREAM_REQUEST_FAILED")
        self.assertEqual(decoded["error"]["message"], "Project access denied")

    async def test_typed_upstream_error_code_survives_normalization(self):
        response = SimpleNamespace(
            status_code=409,
            json=lambda: {"detail": {"code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"}},
        )
        with patch(
            "src.tools.testing_api.make_api_request", new=AsyncMock(return_value=response)
        ):
            result = await testing_api.call("POST", "/principal", {"configurable": {"token": "Bearer x"}})

        self.assertEqual(json.loads(result)["error"], {"code": "PROJECT_QA_EXECUTOR_UNAVAILABLE"})


if __name__ == "__main__":
    unittest.main()
