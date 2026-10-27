import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aio_pika

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

    async def test_delayed_publish_uses_durable_dead_letter_queue(self):
        client = RabbitMQClient()
        exchange = MagicMock()
        exchange.publish = AsyncMock()
        delayed_queue = MagicMock(name="ai.document_ingestion.delayed.48s")
        delayed_queue.name = "ai.document_ingestion.delayed.48s"
        retry_exchange = MagicMock()
        retry_exchange.name = "ai.document_ingestion.retry"
        channel = MagicMock(
            default_exchange=exchange,
            is_closed=False,
            declare_queue=AsyncMock(return_value=delayed_queue),
            declare_exchange=AsyncMock(return_value=retry_exchange),
        )
        client.channel = channel
        target_queue = MagicMock()
        target_queue.bind = AsyncMock()
        client.get_queue = AsyncMock(return_value=target_queue)

        published = await client.publish_delayed(
            "ai.document_ingestion",
            {"document_id": "doc-1", "event_id": "event-1"},
            47.5,
        )

        self.assertTrue(published)
        client.get_queue.assert_awaited_once_with("ai.document_ingestion")
        channel.declare_exchange.assert_awaited_once_with(
            "ai.document_ingestion.retry",
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        target_queue.bind.assert_awaited_once_with(
            retry_exchange, routing_key="ai.document_ingestion"
        )
        channel.declare_queue.assert_awaited_once_with(
            "ai.document_ingestion.delayed.48s",
            durable=True,
            arguments={
                "x-message-ttl": 48000,
                "x-dead-letter-exchange": "ai.document_ingestion.retry",
                "x-dead-letter-routing-key": "ai.document_ingestion",
            },
        )
        message = exchange.publish.await_args.args[0]
        self.assertIsNone(message.expiration)
        self.assertEqual(
            exchange.publish.await_args.kwargs["routing_key"],
            delayed_queue.name,
        )
        self.assertTrue(exchange.publish.await_args.kwargs["mandatory"])

    async def test_delayed_publish_rejects_invalid_delay(self):
        client = RabbitMQClient()
        client.channel = MagicMock(is_closed=False)
        client.get_queue = AsyncMock()

        self.assertFalse(
            await client.publish_delayed("ai.document_ingestion", {}, float("inf"))
        )
        self.assertFalse(
            await client.publish_delayed("ai.document_ingestion", {}, 10**1000)
        )
        client.get_queue.assert_not_awaited()

    async def test_delayed_publish_uses_separate_fixed_ttl_queues(self):
        client = RabbitMQClient()
        exchange = MagicMock()
        exchange.publish = AsyncMock()
        retry_exchange = MagicMock()
        retry_exchange.name = "ai.document_ingestion.retry"
        delayed_queue = MagicMock()
        delayed_queue.name = "ai.document_ingestion.delayed.6s"
        target_queue = MagicMock()
        target_queue.bind = AsyncMock()
        channel = MagicMock(
            default_exchange=exchange,
            is_closed=False,
            declare_queue=AsyncMock(return_value=delayed_queue),
            declare_exchange=AsyncMock(return_value=retry_exchange),
        )
        client.channel = channel
        client.get_queue = AsyncMock(return_value=target_queue)

        short_delay_queued = await client.publish_delayed(
            "ai.document_ingestion", {"event_id": "short"}, 5.1
        )
        long_delay_queued = await client.publish_delayed(
            "ai.document_ingestion", {"event_id": "long"}, 47.5
        )

        self.assertTrue(short_delay_queued)
        self.assertTrue(long_delay_queued)
        queue_declarations = channel.declare_queue.await_args_list
        self.assertEqual(
            [entry.args[0] for entry in queue_declarations],
            [
                "ai.document_ingestion.delayed.6s",
                "ai.document_ingestion.delayed.48s",
            ],
        )
        self.assertEqual(
            [entry.kwargs["arguments"]["x-message-ttl"] for entry in queue_declarations],
            [6000, 48000],
        )

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
