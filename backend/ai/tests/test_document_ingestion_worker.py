import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException

from src.runtime.document_ingestion_worker import (
    DocumentIngestionWorker,
    _ingestion_retry_delay_seconds,
    _retryable_ingestion_error,
)


class DocumentIngestionWorkerTests(unittest.IsolatedAsyncioTestCase):
    def test_retry_delay_uses_bounded_exponential_backoff(self):
        with (
            patch(
                "src.runtime.document_ingestion_worker.limits",
                SimpleNamespace(
                    queue_retry_base_seconds=15,
                    queue_retry_max_seconds=300,
                ),
            ),
        ):
            self.assertEqual(
                [_ingestion_retry_delay_seconds(attempt) for attempt in range(7)],
                [15, 30, 60, 120, 240, 300, 300],
            )

    def test_transient_http_statuses_retry_but_other_client_errors_do_not(self):
        request = httpx.Request("POST", "https://content.invalid/index")

        for status_code in (408, 425, 429, 500, 503):
            with self.subTest(status_code=status_code):
                error = httpx.HTTPStatusError(
                    "upstream response",
                    request=request,
                    response=httpx.Response(status_code, request=request),
                )
                self.assertTrue(_retryable_ingestion_error(error))

        for status_code in (400, 401, 403, 404, 409, 422):
            with self.subTest(status_code=status_code):
                error = httpx.HTTPStatusError(
                    "upstream response",
                    request=request,
                    response=httpx.Response(status_code, request=request),
                )
                self.assertFalse(_retryable_ingestion_error(error))

        for status_code in (408, 425, 429, 500, 503):
            with self.subTest(application_status_code=status_code):
                self.assertTrue(_retryable_ingestion_error(HTTPException(status_code)))

        for status_code in (400, 401, 403, 404, 409, 422):
            with self.subTest(application_status_code=status_code):
                self.assertFalse(_retryable_ingestion_error(HTTPException(status_code)))

    async def test_malformed_attempt_counters_are_rejected_without_indexing(self):
        worker = DocumentIngestionWorker()
        for invalid_attempt in (True, 1.5, "2", -1, None):
            with self.subTest(attempt=invalid_attempt):
                with (
                    patch(
                        "src.runtime.document_ingestion_worker.index_document",
                        new=AsyncMock(),
                    ) as index,
                    patch(
                        "src.runtime.document_ingestion_worker.mq.reject",
                        new=AsyncMock(return_value=True),
                    ) as reject,
                ):
                    await worker._process(
                        {
                            "delivery_tag": "delivery-invalid-attempt",
                            "payload": {
                                "event_id": "event-invalid-attempt",
                                "document_id": "document-invalid-attempt",
                                "attempt": invalid_attempt,
                            },
                        }
                    )

                index.assert_not_awaited()
                reject.assert_awaited_once_with(
                    "delivery-invalid-attempt", requeue=False
                )

    async def test_idle_queue_yields_instead_of_busy_spinning(self):
        worker = DocumentIngestionWorker()
        sleeps = []

        async def sleep(delay):
            sleeps.append(delay)
            worker._stopping = True

        with (
            patch(
                "src.runtime.document_ingestion_worker.mq.consume",
                new=AsyncMock(return_value=None),
            ),
            patch("src.runtime.document_ingestion_worker.asyncio.sleep", new=sleep),
        ):
            await worker._run()

        self.assertEqual(sleeps, [0.25])

    async def test_replacement_is_indexed_before_previous_source_is_removed(self):
        worker = DocumentIngestionWorker()
        operations = []

        async def index(document_id, requester_id, is_admin, dispatch_event_id):
            operations.append(("index", document_id))
            return {"status": "indexed"}

        async def remove(document_id, requester_id, is_admin):
            operations.append(("remove", document_id))
            return {"status": "deleted"}

        message = {
            "delivery_tag": "delivery-1",
            "payload": {
                "event_id": "event-1",
                "document_id": "document-new",
                "user_id": "user-1",
                "superseded_document_id": "document-old",
                "attempt": 0,
            },
        }
        with (
            patch("src.runtime.document_ingestion_worker.index_document", new=index),
            patch("src.runtime.document_ingestion_worker.remove_document", new=remove),
            patch(
                "src.runtime.document_ingestion_worker.mq.ack",
                new=AsyncMock(return_value=True),
            ) as ack,
        ):
            await worker._process(message)

        self.assertEqual(
            operations,
            [("index", "document-new"), ("remove", "document-old")],
        )
        ack.assert_awaited_once_with("delivery-1")

    async def test_busy_document_is_scheduled_after_lease_without_consuming_attempt(self):
        worker = DocumentIngestionWorker()
        payload = {
            "event_id": "event-busy",
            "document_id": "document-busy",
            "user_id": "user-1",
            "attempt": 1,
        }
        with (
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(
                    return_value={"status": "busy", "retry_after_seconds": 47.5}
                ),
            ) as index,
            patch(
                "src.runtime.document_ingestion_worker.mq.publish_delayed",
                new=AsyncMock(return_value=True),
            ) as publish_delayed,
            patch(
                "src.runtime.document_ingestion_worker.mq.ack",
                new=AsyncMock(return_value=True),
            ) as ack,
            patch(
                "src.runtime.document_ingestion_worker.mq.reject",
                new=AsyncMock(),
            ) as reject,
        ):
            await worker._process({"delivery_tag": "delivery-busy", "payload": payload})

        index.assert_awaited_once_with(
            "document-busy", "user-1", False, "event-busy"
        )
        publish_delayed.assert_awaited_once_with(
            "ai.document_ingestion", payload, 47.5
        )
        ack.assert_awaited_once_with("delivery-busy")
        reject.assert_not_awaited()

    async def test_busy_document_is_dead_lettered_if_delayed_retry_cannot_be_published(self):
        worker = DocumentIngestionWorker()
        payload = {
            "event_id": "event-busy-publish-failed",
            "document_id": "document-busy",
            "user_id": "user-1",
            "attempt": 1,
        }
        with (
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(
                    return_value={"status": "busy", "retry_after_seconds": 47.5}
                ),
            ),
            patch(
                "src.runtime.document_ingestion_worker.mq.publish_delayed",
                new=AsyncMock(return_value=False),
            ) as publish_delayed,
            patch(
                "src.runtime.document_ingestion_worker.mq.reject",
                new=AsyncMock(return_value=True),
            ) as reject,
            patch("src.runtime.document_ingestion_worker.mq.ack", new=AsyncMock()) as ack,
        ):
            await worker._process({"delivery_tag": "delivery-busy-failed", "payload": payload})

        publish_delayed.assert_awaited_once_with(
            "ai.document_ingestion", payload, 47.5
        )
        reject.assert_awaited_once_with("delivery-busy-failed", requeue=False)
        ack.assert_not_awaited()

    async def test_degraded_replacement_keeps_previous_source_searchable(self):
        worker = DocumentIngestionWorker()
        message = {
            "delivery_tag": "delivery-degraded-replacement",
            "payload": {
                "event_id": "event-degraded-replacement",
                "document_id": "document-new",
                "user_id": "user-1",
                "superseded_document_id": "document-old",
                "attempt": 1,
            },
        }
        with (
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(return_value={"status": "degraded"}),
            ) as index,
            patch(
                "src.runtime.document_ingestion_worker.remove_document",
                new=AsyncMock(),
            ) as remove,
            patch(
                "src.runtime.document_ingestion_worker.mq.ack",
                new=AsyncMock(return_value=True),
            ) as ack,
        ):
            await worker._process(message)

        index.assert_awaited_once_with(
            "document-new", "user-1", False, "event-degraded-replacement"
        )
        remove.assert_not_awaited()
        ack.assert_awaited_once_with("delivery-degraded-replacement")

    async def test_retryable_failure_republishes_attempt_and_keeps_old_source(self):
        worker = DocumentIngestionWorker()
        message = {
            "delivery_tag": "delivery-2",
            "payload": {
                "event_id": "event-2",
                "document_id": "document-new",
                "user_id": "user-1",
                "superseded_document_id": "document-old",
                "attempt": 1,
            },
        }
        with (
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(side_effect=RuntimeError("temporary failure")),
            ) as index,
            patch(
                "src.runtime.document_ingestion_worker.remove_document",
                new=AsyncMock(),
            ) as remove,
            patch(
                "src.runtime.document_ingestion_worker.mq.publish_delayed",
                new=AsyncMock(return_value=True),
            ) as publish_delayed,
            patch(
                "src.runtime.document_ingestion_worker.limits",
                SimpleNamespace(
                    queue_retry_base_seconds=15,
                    queue_retry_max_seconds=300,
                ),
            ),
            patch(
                "src.runtime.document_ingestion_worker.mq.ack",
                new=AsyncMock(return_value=True),
            ) as ack,
        ):
            await worker._process(message)

        index.assert_awaited_once()
        remove.assert_not_awaited()
        publish_delayed.assert_awaited_once_with(
            "ai.document_ingestion", {**message["payload"], "attempt": 2}, 30
        )
        ack.assert_awaited_once_with("delivery-2")

    async def test_retryable_failure_is_dead_lettered_if_retry_publish_fails(self):
        worker = DocumentIngestionWorker()
        message = {
            "delivery_tag": "delivery-retry-publish-failed",
            "payload": {
                "event_id": "event-retry-publish-failed",
                "document_id": "document-1",
                "user_id": "user-1",
                "attempt": 0,
            },
        }
        with (
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(side_effect=RuntimeError("temporary failure")),
            ),
            patch(
                "src.runtime.document_ingestion_worker.mq.publish_delayed",
                new=AsyncMock(return_value=False),
            ) as publish_delayed,
            patch(
                "src.runtime.document_ingestion_worker.mq.reject",
                new=AsyncMock(return_value=True),
            ) as reject,
            patch("src.runtime.document_ingestion_worker.mq.ack", new=AsyncMock()) as ack,
        ):
            await worker._process(message)

        publish_delayed.assert_awaited_once_with(
            "ai.document_ingestion", {**message["payload"], "attempt": 1}, 15
        )
        reject.assert_awaited_once_with("delivery-retry-publish-failed", requeue=False)
        ack.assert_not_awaited()

    async def test_document_ingestion_retry_limit_uses_runtime_configuration(self):
        worker = DocumentIngestionWorker()
        message = {
            "delivery_tag": "delivery-retry-limit",
            "payload": {
                "event_id": "event-retry-limit",
                "document_id": "document-1",
                "user_id": "user-1",
                "attempt": 1,
            },
        }
        with (
            patch(
                "src.runtime.document_ingestion_worker.settings.DOCUMENT_INGESTION_MAX_DELIVERY_ATTEMPTS",
                2,
            ),
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(side_effect=RuntimeError("temporary failure")),
            ),
            patch(
                "src.runtime.document_ingestion_worker.mq.publish",
                new=AsyncMock(),
            ) as publish,
            patch(
                "src.runtime.document_ingestion_worker.mq.reject",
                new=AsyncMock(return_value=True),
            ) as reject,
        ):
            await worker._process(message)

        publish.assert_not_awaited()
        reject.assert_awaited_once_with("delivery-retry-limit", requeue=False)

    async def test_cleanup_failure_does_not_mark_successfully_indexed_document_failed(self):
        worker = DocumentIngestionWorker()
        message = {
            "delivery_tag": "delivery-cleanup-failure",
            "payload": {
                "event_id": "event-cleanup-failure",
                "document_id": "document-new",
                "user_id": "user-1",
                "superseded_document_id": "document-old",
                "attempt": 3,
            },
        }
        with (
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(return_value={"status": "indexed"}),
            ) as index,
            patch(
                "src.runtime.document_ingestion_worker.remove_document",
                new=AsyncMock(side_effect=RuntimeError("old source cleanup failed")),
            ) as remove,
            patch(
                "src.runtime.document_ingestion_worker.mq.reject",
                new=AsyncMock(return_value=True),
            ) as reject,
            patch(
                "src.runtime.document_ingestion_worker.mq.ack",
                new=AsyncMock(return_value=True),
            ) as ack,
        ):
            await worker._process(message)

        index.assert_awaited_once_with(
            "document-new", "user-1", False, "event-cleanup-failure"
        )
        remove.assert_awaited_once_with("document-old", "user-1", False)
        reject.assert_awaited_once_with("delivery-cleanup-failure", requeue=False)
        ack.assert_not_awaited()

    async def test_superseded_outbox_delivery_is_acknowledged_without_reindexing(self):
        worker = DocumentIngestionWorker()
        message = {
            "delivery_tag": "delivery-superseded",
            "payload": {
                "event_id": "old-dispatch-event",
                "document_id": "document-1",
                "user_id": "user-1",
                "attempt": 0,
            },
        }
        with (
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(return_value={"status": "superseded"}),
            ) as index,
            patch(
                "src.runtime.document_ingestion_worker.mq.ack",
                new=AsyncMock(return_value=True),
            ) as ack,
            patch(
                "src.runtime.document_ingestion_worker.mq.publish", new=AsyncMock()
            ) as publish,
        ):
            await worker._process(message)

        index.assert_awaited_once_with(
            "document-1", "user-1", False, "old-dispatch-event"
        )
        ack.assert_awaited_once_with("delivery-superseded")
        publish.assert_not_awaited()

    async def test_malformed_delivery_is_sent_to_dead_letter(self):
        worker = DocumentIngestionWorker()
        with patch(
            "src.runtime.document_ingestion_worker.mq.reject",
            new=AsyncMock(return_value=True),
        ) as reject:
            await worker._process(
                {"delivery_tag": "delivery-3", "payload": {"document_id": "document-1"}}
            )

        reject.assert_awaited_once_with("delivery-3", requeue=False)

    async def test_non_object_payload_is_sent_to_dead_letter_without_worker_crash(self):
        worker = DocumentIngestionWorker()
        with (
            patch(
                "src.runtime.document_ingestion_worker.mq.reject",
                new=AsyncMock(return_value=True),
            ) as reject,
            patch(
                "src.runtime.document_ingestion_worker.index_document",
                new=AsyncMock(),
            ) as index,
        ):
            await worker._process(
                {"delivery_tag": "delivery-invalid-payload", "payload": ["doc-1"]}
            )

        reject.assert_awaited_once_with("delivery-invalid-payload", requeue=False)
        index.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
