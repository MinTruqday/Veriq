import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger

from src.core.infrastructure.configuration import settings
from src.repositories.jobs import worker_job_repository


async def maintain_execution_lease(job_id: str, lease_token: str):
    while True:
        await asyncio.sleep(settings.WORKER_EXECUTION_HEARTBEAT_SECONDS)
        now = datetime.now(timezone.utc)
        renewed = await worker_job_repository.renew_execution_lease(
            job_id,
            lease_token,
            now,
            now + timedelta(seconds=settings.WORKER_EXECUTION_LEASE_SECONDS),
        )
        if not renewed or renewed.matched_count != 1:
            logger.error("Worker execution lease lost job_id={}", job_id)
            return


async def recover_expired_executions():
    while True:
        try:
            now = datetime.now(timezone.utc)
            result = await worker_job_repository.mark_expired_executions_for_reconciliation(now)
            if result.modified_count:
                logger.error(
                    "Worker executions require reconciliation count={}",
                    result.modified_count,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Worker execution lease recovery scan failed")
        await asyncio.sleep(settings.WORKER_EXECUTION_RECOVERY_POLL_SECONDS)
