import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.infrastructure.mq import RabbitMQClient


class RabbitMQPublishReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_publisher_channel_raises_for_unroutable_messages(self):
        client = RabbitMQClient()
        client.url = "amqp://broker"
        connection = MagicMock()
        connection.channel = AsyncMock(return_value=MagicMock())

        with patch(
            "src.core.infrastructure.mq.aio_pika.connect_robust",
            new=AsyncMock(return_value=connection),
        ):
            await client.connect()

        connection.channel.assert_awaited_once_with(on_return_raises=True)

    async def test_publish_declares_queue_and_requires_routing(self):
        client = RabbitMQClient()
        exchange = MagicMock()
        exchange.publish = AsyncMock()
        client.channel = MagicMock(default_exchange=exchange, is_closed=False)
        client.get_queue = AsyncMock()

        published = await client.publish("ai.automation", {"automation_run_id": "AUT-1"})

        self.assertTrue(published)
        client.get_queue.assert_awaited_once_with("ai.automation")
        message = exchange.publish.await_args.args[0]
        self.assertEqual(message.body, b'{"automation_run_id": "AUT-1"}')
        self.assertEqual(exchange.publish.await_args.kwargs["routing_key"], "ai.automation")
        self.assertTrue(exchange.publish.await_args.kwargs["mandatory"])

    async def test_publish_reports_false_when_queue_declaration_fails(self):
        client = RabbitMQClient()
        publish = AsyncMock()
        client.channel = MagicMock(
            default_exchange=MagicMock(publish=publish), is_closed=False
        )
        client.get_queue = AsyncMock(side_effect=RuntimeError("broker unavailable"))

        self.assertFalse(await client.publish("ai.automation", {"automation_run_id": "AUT-1"}))
        publish.assert_not_awaited()

    async def test_publish_reports_false_when_broker_rejects_routing(self):
        client = RabbitMQClient()
        exchange = MagicMock()
        exchange.publish = AsyncMock(side_effect=RuntimeError("unroutable message"))
        client.channel = MagicMock(default_exchange=exchange, is_closed=False)
        client.get_queue = AsyncMock()

        self.assertFalse(await client.publish("ai.automation", {"automation_run_id": "AUT-1"}))

    async def test_publish_reopens_a_closed_channel_without_reconnecting(self):
        client = RabbitMQClient()
        old_channel = MagicMock(is_closed=True)
        connection = MagicMock(is_closed=False)
        new_channel = MagicMock(
            default_exchange=MagicMock(publish=AsyncMock()), is_closed=False
        )
        connection.channel = AsyncMock(return_value=new_channel)
        client.connection = connection
        client.channel = old_channel
        client.get_queue = AsyncMock()

        published = await client.publish("ai.automation", {"automation_run_id": "AUT-1"})

        self.assertTrue(published)
        connection.channel.assert_awaited_once_with(on_return_raises=True)
        self.assertIs(client.channel, new_channel)
        client.get_queue.assert_awaited_once_with("ai.automation")

    async def test_consume_can_disable_ack_timeout_for_long_running_work(self):
        client = RabbitMQClient()
        consumer_channel = MagicMock(is_closed=False)
        connection = MagicMock(is_closed=False)
        connection.channel = AsyncMock(return_value=consumer_channel)
        client.connection = connection
        queue = MagicMock()
        message = MagicMock(body=b'{"document_id":"doc-1"}')
        queue.get = AsyncMock(return_value=message)
        client.get_queue = AsyncMock(return_value=queue)

        with patch("src.core.infrastructure.mq.create_background_task") as spawn:
            delivery = await client.consume("ai.document_ingestion", ack_timeout_seconds=0)

        self.assertEqual(delivery["payload"], {"document_id": "doc-1"})
        self.assertIn(delivery["delivery_tag"], client.pending_acks)
        spawn.assert_not_called()

    async def test_malformed_persistent_payload_is_rejected_instead_of_stuck_unacked(self):
        client = RabbitMQClient()
        consumer_channel = MagicMock(is_closed=False)
        connection = MagicMock(is_closed=False)
        connection.channel = AsyncMock(return_value=consumer_channel)
        client.connection = connection
        queue = MagicMock()
        message = MagicMock(body=b"not-json")
        message.nack = AsyncMock()
        queue.get = AsyncMock(return_value=message)
        client.get_queue = AsyncMock(return_value=queue)

        delivery = await client.consume("ai.document_ingestion", ack_timeout_seconds=0)

        self.assertIsNone(delivery)
        message.nack.assert_awaited_once_with(requeue=False)

    async def test_ack_timeout_requeues_pending_delivery(self):
        client = RabbitMQClient()
        message = MagicMock()
        message.nack = AsyncMock()
        client.pending_acks["delivery-1"] = message

        with patch("src.core.infrastructure.mq.asyncio.sleep", new=AsyncMock()):
            await client._auto_nack_if_timeout("delivery-1", delay=12)

        message.nack.assert_awaited_once_with(requeue=True)
        self.assertNotIn("delivery-1", client.pending_acks)

    async def test_ack_before_timeout_prevents_late_requeue(self):
        client = RabbitMQClient()
        message = MagicMock()
        message.ack = AsyncMock()
        message.nack = AsyncMock()
        client.pending_acks["delivery-2"] = message

        self.assertTrue(await client.ack("delivery-2"))
        with patch("src.core.infrastructure.mq.asyncio.sleep", new=AsyncMock()):
            await client._auto_nack_if_timeout("delivery-2", delay=12)

        message.ack.assert_awaited_once()
        message.nack.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
