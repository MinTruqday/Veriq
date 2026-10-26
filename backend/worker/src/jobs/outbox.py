import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from loguru import logger

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.mq import mq
from src.core.metrics import metrics_collector
from src.repositories.jobs import worker_job_repository


async def dispatch_outbox_once() -> bool:
    now = datetime.now(timezone.utc)
    lease_token = str(uuid4())
    entry = await worker_job_repository.claim_next_outbox(
        lease_token,
        now,
        now + timedelta(seconds=settings.WORKER_OUTBOX_LEASE_SECONDS),
    )
    if not entry:
        return False

    try:
        published = await mq.publish(settings.WORKER_QUEUE_NAME, entry["payload"])
        if not published:
            raise RuntimeError("RabbitMQ did not confirm publishing the worker job")
    except Exception as error:
        attempt = max(1, int(entry.get("attempt_count", 1)))
        backoff_seconds = min(
            2 ** min(attempt - 1, 30),
            settings.WORKER_OUTBOX_MAX_BACKOFF_SECONDS,
        )
        await worker_job_repository.reschedule_outbox(
            entry["_id"],
            lease_token,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds),
            error,
        )
        logger.warning(
            "Worker outbox publish failed job_id={} generation={} attempt={} retry_seconds={}",
            entry.get("job_id"),
            entry.get("dispatch_generation"),
            attempt,
            backoff_seconds,
        )
        return True

    marked = await worker_job_repository.mark_outbox_published(
        entry["_id"], lease_token, datetime.now(timezone.utc)
    )
    if marked and marked.matched_count == 1:
        metrics_collector.change_queue_depth(settings.WORKER_QUEUE_NAME, 1)
    return True


async def dispatch_worker_job_outbox():
    while True:
        try:
            dispatched = await dispatch_outbox_once()
            if not dispatched:
                await asyncio.sleep(settings.WORKER_OUTBOX_POLL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Worker job outbox dispatcher failed")
            await asyncio.sleep(settings.WORKER_OUTBOX_POLL_SECONDS)
