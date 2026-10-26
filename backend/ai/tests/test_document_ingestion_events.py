import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.api.events import document_uploaded_webhook, manual_trigger, receive_webhook
from src.runtime.events import AgentEvent, EventHandler, EventProcessor, EventType
from src.schemas.events import ManualTriggerRequest, WebhookPayload


class DocumentIngestionEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_ingestion_dispatch_is_not_marked_as_processed(self):
        processor = EventProcessor()

        async def fail_dispatch(event):
            raise RuntimeError("document_ingestion_queue_unavailable")

        processor.register_handler(
            EventHandler(
                event_type=EventType.DOCUMENT_UPLOADED,
                handler=fail_dispatch,
                description="document ingestion dispatch",
            )
        )
        event = AgentEvent(
            event_id="event-failed-dispatch",
            event_type=EventType.DOCUMENT_UPLOADED,
            payload={"document_id": "doc-1"},
        )

        await processor.handle_event(event)

        self.assertFalse(event.processed)
        self.assertIn("document_ingestion_queue_unavailable", event.error)
        self.assertEqual(processor.get_recent_events()[0]["error"], event.error)

    async def test_manual_ingestion_trigger_returns_unavailable_when_dispatch_fails(self):
        async def fail_dispatch(event):
            event.error = "document ingestion dispatch: document_ingestion_queue_unavailable"

        with (
            patch(
                "src.api.events.event_processor.handle_event",
                new=AsyncMock(side_effect=fail_dispatch),
            ),
            self.assertRaises(HTTPException) as raised,
        ):
            await manual_trigger("document_uploaded", ManualTriggerRequest(payload={"document_id": "doc-1"}))

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["code"], "EVENT_HANDLER_FAILED")

    async def test_document_webhook_persists_event_before_returning_accepted(self):
        with patch(
            "src.core.infrastructure.mq.mq.publish", new=AsyncMock(return_value=True)
        ) as publish:
            response = await document_uploaded_webhook(
                " doc-1 ",
                user_id="user-1",
                superseded_document_id="doc-old",
                event_id="outbox-event-1",
            )

        self.assertEqual(response["status"], "accepted")
        queue_name, payload = publish.await_args.args
        self.assertEqual(queue_name, "ai.document_ingestion")
        self.assertEqual(payload["document_id"], "doc-1")
        self.assertEqual(payload["user_id"], "user-1")
        self.assertEqual(payload["superseded_document_id"], "doc-old")
        self.assertEqual(payload["attempt"], 0)
        self.assertEqual(payload["event_id"], "outbox-event-1")
        self.assertEqual(payload["event_id"], response["event_id"])

    async def test_document_webhook_rejects_empty_identifier_without_publishing(self):
        with (
            patch(
                "src.core.infrastructure.mq.mq.publish", new=AsyncMock()
            ) as publish,
            self.assertRaises(HTTPException) as raised,
        ):
            await document_uploaded_webhook("   ")

        self.assertEqual(raised.exception.status_code, 422)
        publish.assert_not_awaited()

    async def test_generic_document_event_uses_durable_queue(self):
        payload = WebhookPayload(
            event_type="document_uploaded",
            source="content_service",
            payload={"document_id": "doc-2", "user_id": "user-2"},
        )
        with (
            patch(
                "src.core.infrastructure.mq.mq.publish", new=AsyncMock(return_value=True)
            ) as publish,
            patch("src.api.events.event_processor.emit_event", new=AsyncMock()) as emit,
        ):
            response = await receive_webhook(payload)

        self.assertEqual(response["event_type"], "document_uploaded")
        publish.assert_awaited_once()
        emit.assert_not_awaited()

    async def test_unavailable_queue_is_not_reported_as_accepted(self):
        with (
            patch(
                "src.core.infrastructure.mq.mq.publish", new=AsyncMock(return_value=False)
            ),
            self.assertRaises(HTTPException) as raised,
        ):
            await document_uploaded_webhook("doc-3")

        self.assertEqual(raised.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
