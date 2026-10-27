import hashlib
import json
from contextlib import suppress
from datetime import datetime, timezone
from uuid import uuid4

import aio_pika

from src.core.infrastructure.mongo import mongo
from src.core.infrastructure.mq import mq
from src.repositories.automation import automation_repository
from src.runtime.limits import limits
from src.runtime.queue_names import (
    AUTOMATION_QUEUE,
    DEAD_LETTER_QUEUE,
    DOCUMENT_INGESTION_QUEUE,
    RECOVERABLE_QUEUES,
)
from src.schemas.automation import AutomationStatus
from src.schemas.events import DeadLetterRecoveryAudit


def _header(headers, name):
    if not isinstance(headers, dict):
        return None
    return headers.get(name, headers.get(name.encode()))


def _origin_queue(headers):
    deaths = _header(headers, "x-death")
    if not isinstance(deaths, list) or not deaths or not isinstance(deaths[0], dict):
        return None
    queue = _header(deaths[0], "queue")
    if isinstance(queue, bytes):
        queue = queue.decode("utf-8", errors="replace")
    queue = str(queue or "").strip()
    return queue if queue in RECOVERABLE_QUEUES else None


def _payload_identity(payload):
    for field in ("event_id", "automation_run_id"):
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return field, value.strip()
    return None, None


class DeadLetterRecovery:
    def __init__(self):
        self.collection = "dead_letter_recovery_audit"

    async def depth(self):
        await mq.connect()
        channel = await mq.connection.channel()
        try:
            queue = await channel.declare_queue(
                DEAD_LETTER_QUEUE, durable=True, passive=True
            )
            result = queue.declaration_result
            return int(getattr(result, "message_count", 0) or 0)
        finally:
            await channel.close()

    async def list_audit(self, *, limit: int):
        cursor = mongo.find(
            self.collection,
            {},
            sort=[("created_at", -1)],
            limit=limit,
        )
        records = await cursor.to_list(length=limit)
        return [
            {"action_id": str(record.pop("_id")), **record}
            for record in records
        ]

    async def redrive(self, *, limit: int, requested_by: str):
        await mq.connect()
        channel = await mq.connection.channel(on_return_raises=True)
        queue = await channel.declare_queue(
            DEAD_LETTER_QUEUE, durable=True, passive=True
        )
        summary = {
            "examined": 0,
            "redriven": 0,
            "retained": 0,
            "stopped_reason": None,
            "actions": [],
        }
        try:
            for _ in range(limit):
                message = await queue.get(timeout=0.2, fail=False)
                if message is None:
                    break
                summary["examined"] += 1
                payload_hash = hashlib.sha256(message.body).hexdigest()
                action_id = str(uuid4())
                headers = dict(message.headers or {})
                origin_queue = _origin_queue(headers)
                redrive_count = _header(headers, "x-veriq-redrive-count") or 0
                if isinstance(redrive_count, bool) or not isinstance(redrive_count, int):
                    redrive_count = limits.dead_letter_max_redrives
                try:
                    payload = json.loads(message.body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    payload = None
                identity_type, identity = (
                    _payload_identity(payload) if isinstance(payload, dict) else (None, None)
                )
                blocked_reason = None
                redrive_body = message.body
                source_delivery_attempt = None
                delivery_attempt_reset = False
                if origin_queue is None:
                    blocked_reason = "UNSUPPORTED_ORIGIN_QUEUE"
                elif not identity:
                    blocked_reason = "IDEMPOTENCY_ID_MISSING"
                elif redrive_count >= limits.dead_letter_max_redrives:
                    blocked_reason = "MAX_REDRIVE_ATTEMPTS_REACHED"
                elif (
                    origin_queue == DOCUMENT_INGESTION_QUEUE
                    and identity_type != "event_id"
                ) or (
                    origin_queue == AUTOMATION_QUEUE
                    and identity_type != "automation_run_id"
                ):
                    blocked_reason = "QUEUE_IDENTITY_MISMATCH"
                elif origin_queue == AUTOMATION_QUEUE:
                    run = await automation_repository.get_run(identity)
                    if run is None:
                        blocked_reason = "AUTOMATION_RUN_NOT_FOUND"
                    elif run.status != AutomationStatus.QUEUED:
                        blocked_reason = "AUTOMATION_RUN_NOT_QUEUED"
                elif origin_queue == DOCUMENT_INGESTION_QUEUE:
                    if not str(payload.get("document_id") or "").strip():
                        blocked_reason = "DOCUMENT_ID_MISSING"
                    else:
                        source_delivery_attempt = payload.get("attempt", 0)
                        if (
                            isinstance(source_delivery_attempt, bool)
                            or not isinstance(source_delivery_attempt, int)
                            or source_delivery_attempt < 0
                        ):
                            blocked_reason = "INVALID_DELIVERY_ATTEMPT"
                            source_delivery_attempt = None
                        elif source_delivery_attempt:
                            redrive_body = json.dumps(
                                {**payload, "attempt": 0},
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ).encode("utf-8")
                            delivery_attempt_reset = True
                audit = DeadLetterRecoveryAudit(
                    action_id=action_id,
                    requested_by=requested_by,
                    payload_sha256=payload_hash,
                    origin_queue=origin_queue,
                    identity_type=identity_type,
                    identity_sha256=hashlib.sha256(identity.encode()).hexdigest()
                    if identity
                    else None,
                    redrive_count=redrive_count,
                    source_delivery_attempt=source_delivery_attempt,
                    delivery_attempt_reset=delivery_attempt_reset,
                    status="RETAINED" if blocked_reason else "PREPARED",
                    reason=blocked_reason,
                    created_at=datetime.now(timezone.utc),
                ).model_dump(mode="python")
                audit["_id"] = audit.pop("action_id")
                await mongo.insert_one(self.collection, audit)
                if blocked_reason:
                    await message.nack(requeue=True)
                    summary["retained"] += 1
                    summary["stopped_reason"] = blocked_reason
                    summary["actions"].append({"action_id": action_id, "status": "RETAINED"})
                    break
                headers["x-veriq-redrive-count"] = redrive_count + 1
                headers["x-veriq-redrive-action"] = action_id
                try:
                    await mq.get_queue(origin_queue, channel=channel)
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=redrive_body,
                            headers=headers,
                            message_id=message.message_id or identity,
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            content_type=message.content_type or "application/json",
                            correlation_id=message.correlation_id,
                        ),
                        routing_key=origin_queue,
                        mandatory=True,
                    )
                except Exception:
                    with suppress(Exception):
                        await message.nack(requeue=True)
                    await mongo.update_one(
                        self.collection,
                        {"_id": action_id, "status": "PREPARED"},
                        {
                            "$set": {
                                "status": "PUBLISH_FAILED",
                                "updated_at": datetime.now(timezone.utc),
                            }
                        },
                    )
                    summary["retained"] += 1
                    summary["stopped_reason"] = "PUBLISH_FAILED"
                    summary["actions"].append(
                        {"action_id": action_id, "status": "PUBLISH_FAILED"}
                    )
                    break
                try:
                    await mongo.update_one(
                        self.collection,
                        {"_id": action_id, "status": "PREPARED"},
                        {
                            "$set": {
                                "status": "PUBLISHED",
                                "published_at": datetime.now(timezone.utc),
                            }
                        },
                    )
                    await message.ack(multiple=False)
                except Exception:
                    with suppress(Exception):
                        await message.nack(requeue=True)
                    with suppress(Exception):
                        await mongo.update_one(
                            self.collection,
                            {"_id": action_id, "status": {"$in": ["PREPARED", "PUBLISHED"]}},
                            {
                                "$set": {
                                    "status": "DELIVERY_UNCERTAIN",
                                    "updated_at": datetime.now(timezone.utc),
                                }
                            },
                        )
                    summary["retained"] += 1
                    summary["stopped_reason"] = "DELIVERY_UNCERTAIN"
                    summary["actions"].append(
                        {"action_id": action_id, "status": "DELIVERY_UNCERTAIN"}
                    )
                    break
                try:
                    await mongo.update_one(
                        self.collection,
                        {"_id": action_id, "status": "PUBLISHED"},
                        {
                            "$set": {
                                "status": "ACKNOWLEDGED",
                                "acknowledged_at": datetime.now(timezone.utc),
                            }
                        },
                    )
                except Exception:
                    summary["redriven"] += 1
                    summary["actions"].append(
                        {"action_id": action_id, "status": "ACKNOWLEDGED_AUDIT_PENDING"}
                    )
                    continue
                summary["redriven"] += 1
                summary["actions"].append({"action_id": action_id, "status": "ACKNOWLEDGED"})
            return summary
        finally:
            await channel.close()


dead_letter_recovery = DeadLetterRecovery()
