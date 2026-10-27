import asyncio
import math
from collections.abc import Mapping
from contextlib import suppress

import httpx
from fastapi import HTTPException
from loguru import logger

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.mq import mq
from src.core.infrastructure.observability import trace_span
from src.runtime.limits import limits
from src.runtime.queue_names import DOCUMENT_INGESTION_QUEUE
from src.services.ingestion import index_document, remove_document


def _retryable_ingestion_error(error: Exception) -> bool:
    if isinstance(error, (ValueError, PermissionError)):
        return False
    if isinstance(error, HTTPException):
        status_code = error.status_code
        return status_code in {408, 425, 429} or status_code >= 500
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        return status_code in {408, 425, 429} or status_code >= 500
    return True


def _ingestion_retry_delay_seconds(attempt: int) -> int:
    base_delay = limits.queue_retry_base_seconds
    maximum_delay = limits.queue_retry_max_seconds
    if attempt < 0 or base_delay < 1 or maximum_delay < base_delay:
        raise ValueError("document_ingestion_retry_delay_configuration_invalid")
    maximum_doublings = (maximum_delay // base_delay).bit_length()
    delay = base_delay * (1 << min(attempt, maximum_doublings))
    return min(delay, maximum_delay)


class DocumentIngestionWorker:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stopping = False

    async def start(self):
        if self._task and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._run(), name="ai-document-ingestion-worker")

    async def stop(self):
        self._stopping = True
        task, self._task = self._task, None
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def _run(self):
        while not self._stopping:
            try:
                message = await mq.consume(
                    DOCUMENT_INGESTION_QUEUE,
                    timeout=5,
                    ack_timeout_seconds=0,
                )
                if message:
                    await self._process(message)
                else:
                    await asyncio.sleep(0.25)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Document ingestion queue worker iteration failed")
                await asyncio.sleep(2)

    async def _process(self, message: dict):
        payload = message.get("payload") if isinstance(message, Mapping) else {}
        payload = payload if isinstance(payload, Mapping) else {}
        with trace_span(
            "document.ingestion.delivery",
            {
                "event.status": "received",
            },
        ) as span:
            await self._process_delivery(message, span)

    async def _process_delivery(self, message: dict, delivery_span=None):
        message = message if isinstance(message, Mapping) else {}
        raw_payload = message.get("payload")
        payload = raw_payload if isinstance(raw_payload, Mapping) else {}
        delivery_tag = str(message.get("delivery_tag") or "")
        document_id = str(payload.get("document_id") or "")
        event_id = str(payload.get("event_id") or "")
        raw_attempt = payload.get("attempt", 0)
        attempt = (
            raw_attempt
            if isinstance(raw_attempt, int)
            and not isinstance(raw_attempt, bool)
            and raw_attempt >= 0
            else -1
        )
        if (
            not delivery_tag
            or not isinstance(raw_payload, Mapping)
            or not document_id
            or not event_id
            or attempt < 0
        ):
            if delivery_tag:
                await mq.reject(delivery_tag, requeue=False)
            logger.error("Rejected malformed durable document ingestion event")
            return

        user_id = str(payload.get("user_id") or "")
        requester_id = user_id or "platform-system"
        is_admin = not bool(user_id)
        try:
            superseded_document_id = str(payload.get("superseded_document_id") or "")
            with trace_span(
                "document.ingestion.dispatch",
                {
                    "event.status": "dispatching",
                },
            ):
                result = await index_document(
                    document_id, requester_id, is_admin, event_id
                )
            if delivery_span is not None:
                delivery_span.set_attribute(
                    "document.ingestion.status", str(result.get("status") or "unknown")
                )
            if result.get("status") not in {"indexed", "degraded", "superseded", "busy"}:
                raise RuntimeError("document_indexing_status_invalid")
            if result.get("status") == "busy":
                retry_after_seconds = result.get("retry_after_seconds")
                if (
                    isinstance(retry_after_seconds, bool)
                    or not isinstance(retry_after_seconds, (int, float))
                    or not math.isfinite(retry_after_seconds)
                    or retry_after_seconds <= 0
                ):
                    raise RuntimeError("document_index_busy_retry_delay_invalid")
                queued = await mq.publish_delayed(
                    DOCUMENT_INGESTION_QUEUE,
                    payload,
                    retry_after_seconds,
                )
                if queued:
                    if not await mq.ack(delivery_tag):
                        logger.warning(
                            "Document busy retry was scheduled but delivery ACK failed document_id={}",
                            document_id,
                        )
                else:
                    if not await mq.reject(delivery_tag, requeue=False):
                        logger.error(
                            "Document busy retry could not be scheduled or dead-lettered document_id={} event_id={}",
                            document_id,
                            event_id,
                        )
                    else:
                        logger.error(
                            "Document busy retry moved to dead letter after delayed scheduling failed document_id={} event_id={}",
                            document_id,
                            event_id,
                        )
                return
            retryable_degraded = result.get("status") == "degraded" and any(
                result.get(section)
                for section in (
                    "failed_chunks",
                    "unprocessed_blocks",
                    "index_cleanup_pending",
                )
            )
            if (
                retryable_degraded
                and attempt + 1 < settings.DOCUMENT_INGESTION_MAX_DELIVERY_ATTEMPTS
            ):
                retry_payload = {**payload, "attempt": attempt + 1}
                try:
                    retry_queued = await mq.publish_delayed(
                        DOCUMENT_INGESTION_QUEUE,
                        retry_payload,
                        _ingestion_retry_delay_seconds(attempt),
                    )
                except Exception:
                    logger.exception(
                        "Degraded document ingestion retry publication raised document_id={}",
                        document_id,
                    )
                    retry_queued = False
                if retry_queued:
                    await mq.ack(delivery_tag)
                    logger.warning(
                        "Degraded document indexing retry queued document_id={} attempt={}",
                        document_id,
                        attempt + 1,
                    )
                    return
                rejected = await mq.reject(delivery_tag, requeue=False)
                logger.error(
                    "Degraded document indexing retry could not be published; dead_lettered={} document_id={} event_id={}",
                    rejected,
                    document_id,
                    event_id,
                )
                return
            if retryable_degraded:
                logger.error(
                    "Document indexing remains degraded after retries document_id={} attempts={}",
                    document_id,
                    attempt + 1,
                )
            if (
                result.get("status") == "indexed"
                and superseded_document_id
                and superseded_document_id != document_id
            ):
                await remove_document(superseded_document_id, requester_id, is_admin)
            elif superseded_document_id and result.get("status") == "degraded":
                logger.warning(
                    "Keeping superseded source searchable because replacement indexing is degraded "
                    "document_id={} superseded_document_id={}",
                    document_id,
                    superseded_document_id,
                )
        except asyncio.CancelledError:
            await mq.reject(delivery_tag, requeue=True)
            raise
        except Exception as error:
            if (
                _retryable_ingestion_error(error)
                and attempt + 1 < settings.DOCUMENT_INGESTION_MAX_DELIVERY_ATTEMPTS
            ):
                retry_payload = {**payload, "attempt": attempt + 1}
                try:
                    retry_queued = await mq.publish_delayed(
                        DOCUMENT_INGESTION_QUEUE,
                        retry_payload,
                        _ingestion_retry_delay_seconds(attempt),
                    )
                except Exception:
                    logger.exception(
                        "Document ingestion retry publication raised document_id={}",
                        document_id,
                    )
                    retry_queued = False
                if retry_queued:
                    await mq.ack(delivery_tag)
                    logger.warning(
                        "Document ingestion retry queued document_id={} attempt={} error_type={}",
                        document_id,
                        attempt + 1,
                        type(error).__name__,
                    )
                    return
                rejected = await mq.reject(delivery_tag, requeue=False)
                logger.error(
                    "Document ingestion retry could not be published; dead_lettered={} document_id={} event_id={}",
                    rejected,
                    document_id,
                    event_id,
                )
                return

            await mq.reject(delivery_tag, requeue=False)
            logger.error(
                "Document ingestion stopped document_id={} attempts={} error_type={}",
                document_id,
                attempt + 1,
                type(error).__name__,
            )
            return

        if not await mq.ack(delivery_tag):
            logger.warning(
                "Document ingestion completed but queue acknowledgement failed document_id={}",
                document_id,
            )


document_ingestion_worker = DocumentIngestionWorker()
