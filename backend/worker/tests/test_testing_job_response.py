import unittest

from src.jobs.task import (
    PermanentTaskError,
    raise_for_testing_response,
    validate_testing_job_response,
)


class TestingJobResponseTests(unittest.TestCase):
    def test_legacy_http_success_with_retryable_failed_result_is_retried(self):
        with self.assertRaisesRegex(RuntimeError, "KNOWLEDGE_INDEX_FAILED"):
            validate_testing_job_response(
                {
                    "data": {
                        "status": "FAILED",
                        "error_code": "KNOWLEDGE_INDEX_FAILED",
                        "retryable": True,
                    },
                    "status": "SUCCESS",
                }
            )

    def test_nonretryable_failure_is_terminal(self):
        with self.assertRaisesRegex(PermanentTaskError, "PERMISSION_REVOKED"):
            validate_testing_job_response(
                {
                    "data": {
                        "status": "FAILED",
                        "error_code": "PERMISSION_REVOKED",
                        "retryable": False,
                    }
                }
            )

    def test_success_result_is_returned(self):
        result = validate_testing_job_response(
            {"data": {"status": "COMPLETED", "result": {"indexed": True}}}
        )
        self.assertTrue(result["result"]["indexed"])

    def test_malformed_success_payload_is_not_accepted(self):
        with self.assertRaises(PermanentTaskError):
            validate_testing_job_response({"status": "SUCCESS", "data": None})

    def test_permanent_client_error_is_not_retried(self):
        class Response:
            status_code = 403

            def raise_for_status(self):
                raise AssertionError("permanent 4xx should not rely on HTTP retry")

        with self.assertRaisesRegex(PermanentTaskError, "testing_api_http_403"):
            raise_for_testing_response(Response())

    def test_retryable_http_status_uses_transport_error_path(self):
        class Response:
            status_code = 503

            def raise_for_status(self):
                raise RuntimeError("retryable server response")

        with self.assertRaisesRegex(RuntimeError, "retryable server response"):
            raise_for_testing_response(Response())


if __name__ == "__main__":
    unittest.main()
