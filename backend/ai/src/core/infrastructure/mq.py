import asyncio
import json
import math
from typing import Any, Dict, Optional

import aio_pika
from loguru import logger
from uuid6 import uuid7

from src.core.infrastructure.configuration import settings
from src.runtime.limits import limits
from src.runtime.queue_names import DEAD_LETTER_QUEUE
from src.utils.background import create_background_task


class RabbitMQClient:
    def __init__(self):
        self.url = settings.RABBITMQ_URI
        self.connection = None
        self.channel = None
        self.consumer_channels = {}
        self.pending_acks = {}

    async def connect(self):
        if self.connection and not self.connection.is_closed:
            if not self.channel or self.channel.is_closed:
                self.channel = await self.connection.channel(on_return_raises=True)
            return

        max_retries = 10
        for attempt in range(max_retries):
            try:
                self.connection = await aio_pika.connect_robust(self.url)
                self.channel = await self.connection.channel(on_return_raises=True)
                logger.info("RabbitMQ connection successful")
                return
            except Exception as e:
                logger.exception("RabbitMQ connection failed, retrying")
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(3)

    async def _ensure_publisher_channel(self):
        if self.channel and not self.channel.is_closed:
            return
        if not self.connection or self.connection.is_closed:
            await self.connect()
        elif not self.channel or self.channel.is_closed:
            self.channel = await self.connection.channel(on_return_raises=True)

    async def get_queue(self, queue_name: str, channel=None):
        if channel is None:
            channel = self.channel
        if channel is None:
            await self.connect()
            channel = self.channel

        dlx = await channel.declare_exchange("dlx", aio_pika.ExchangeType.DIRECT)
        dlq = await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
        await dlq.bind(dlx, DEAD_LETTER_QUEUE)
        queue_args = {
            "x-dead-letter-exchange": "dlx",
            "x-dead-letter-routing-key": DEAD_LETTER_QUEUE,
        }
        return await channel.declare_queue(queue_name, durable=True, arguments=queue_args)

    async def publish(self, queue_name: str, payload: dict) -> bool:
        try:
            await self._ensure_publisher_channel()
            await self.get_queue(queue_name)
            message = aio_pika.Message(
                body=json.dumps(payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            await self.channel.default_exchange.publish(
                message, routing_key=queue_name, mandatory=True
            )
            return True
        except Exception:
            logger.exception("Error distributing message to RabbitMQ")
            return False

    async def publish_delayed(
        self, queue_name: str, payload: dict, delay_seconds: float
    ) -> bool:
        if (
            not queue_name
            or isinstance(delay_seconds, bool)
            or not isinstance(delay_seconds, (int, float))
        ):
            return False
        try:
            normalized_delay_seconds = float(delay_seconds)
        except (OverflowError, ValueError):
            return False
        if not math.isfinite(normalized_delay_seconds) or normalized_delay_seconds <= 0:
            return False
        try:
            delay_bucket_seconds = math.ceil(normalized_delay_seconds)
            await self._ensure_publisher_channel()
            target_queue = await self.get_queue(queue_name)
            retry_exchange = await self.channel.declare_exchange(
                f"{queue_name}.retry",
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            await target_queue.bind(retry_exchange, routing_key=queue_name)
            delayed_queue_name = (
                f"{queue_name}.delayed.{delay_bucket_seconds}s"
            )
            delayed_queue = await self.channel.declare_queue(
                delayed_queue_name,
                durable=True,
                arguments={
                    "x-message-ttl": delay_bucket_seconds * 1000,
                    "x-dead-letter-exchange": retry_exchange.name,
                    "x-dead-letter-routing-key": queue_name,
                },
            )
            message = aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await self.channel.default_exchange.publish(
                message, routing_key=delayed_queue.name, mandatory=True
            )
            return True
        except Exception:
            logger.exception("Error scheduling delayed RabbitMQ message queue={}", queue_name)
            return False

    async def consume(
        self,
        queue_name: str,
        timeout: int = 30,
        ack_timeout_seconds: int = limits.message_ack_timeout_seconds,
    ) -> Optional[Dict[str, Any]]:
        if not self.connection or self.connection.is_closed:
            await self.connect()
        channel = self.consumer_channels.get(queue_name)
        if not channel or channel.is_closed:
            channel = await self.connection.channel()
            self.consumer_channels[queue_name] = channel
        queue = await self.get_queue(queue_name, channel)
        try:
            message = await queue.get(timeout=timeout)
            if message:
                try:
                    payload = json.loads(message.body.decode())
                except (UnicodeDecodeError, json.JSONDecodeError):
                    logger.exception("Rejecting malformed RabbitMQ message queue={}", queue_name)
                    await message.nack(requeue=False)
                    return None
                if not isinstance(payload, dict):
                    logger.error("Rejecting non-object RabbitMQ message queue={}", queue_name)
                    await message.nack(requeue=False)
                    return None
                ack_id = str(uuid7())

                self.pending_acks[ack_id] = message

                if ack_timeout_seconds > 0:
                    create_background_task(
                        self._auto_nack_if_timeout(ack_id, delay=ack_timeout_seconds),
                        f"rabbitmq-auto-nack-{ack_id}",
                    )

                return {"payload": payload, "delivery_tag": ack_id}
            return None
        except aio_pika.exceptions.QueueEmpty:
            return None
        except asyncio.TimeoutError:
            return None
        except Exception:
            logger.exception("Error fetching message from RabbitMQ")
            return None

    async def _auto_nack_if_timeout(self, ack_id: str, delay: int):
        await asyncio.sleep(delay)
        message = self.pending_acks.pop(ack_id, None)
        if message:
            logger.warning(
                f"Timeout waiting for ACK/NACK for message {ack_id} from RabbitMQ, retrying"
            )
            try:
                await message.nack(requeue=True)
            except Exception:
                logger.exception("RabbitMQ automatic NACK failed")

    async def ack(self, delivery_tag: str) -> bool:
        message = self.pending_acks.pop(delivery_tag, None)
        if message:
            try:
                await message.ack()
                return True
            except Exception:
                logger.exception("Error sending ACK response to RabbitMQ")
                return False
        return False

    async def reject(self, delivery_tag: str, requeue: bool = False) -> bool:
        message = self.pending_acks.pop(delivery_tag, None)
        if message:
            try:
                await message.nack(requeue=requeue)
                return True
            except Exception:
                logger.exception("Error rejecting RabbitMQ message")
                return False
        return False

    async def health_check(self) -> bool:
        try:
            await self.connect()
            return True
        except Exception:
            return False

    async def aclose(self):
        for channel in self.consumer_channels.values():
            if not channel.is_closed:
                await channel.close()
        self.consumer_channels.clear()
        self.pending_acks.clear()
        if self.connection:
            await self.connection.close()


mq = RabbitMQClient()
