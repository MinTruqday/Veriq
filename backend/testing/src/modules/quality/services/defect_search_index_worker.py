import asyncio
import logging

from src.clients.project_knowledge import remove_artifact
from src.core.configuration import settings
from src.modules.quality.services.defect_search import index_defect_for_search
from src.repositories.defect import defect_repository
from src.repositories.defect_search_index import defect_search_index_repository

logger = logging.getLogger(__name__)
_worker_task: asyncio.Task | None = None


async def process_next_defect_search_index() -> bool:
    entry = await defect_search_index_repository.claim_next(
        settings.DEFECT_SEARCH_INDEX_LEASE_SECONDS
    )
    if not entry:
        return False

    project_id = entry["project_id"]
    defect_id = entry["defect_id"]
    try:
        defect = await defect_repository.find_defect(defect_id, project_id)
        if defect is None:
            if not await remove_artifact(project_id, defect_id):
                raise RuntimeError("DEFECT_SEARCH_INDEX_REMOVE_FAILED")
            completed = await defect_search_index_repository.complete(
                entry, None, status="REMOVED"
            )
            return completed

        indexed = await index_defect_for_search(project_id, defect)
        if not indexed:
            raise RuntimeError("DEFECT_SEARCH_INDEX_UNAVAILABLE")

        latest = await defect_repository.find_defect(defect_id, project_id)
        if latest is None:
            if not await remove_artifact(project_id, defect_id):
                raise RuntimeError("DEFECT_SEARCH_INDEX_REMOVE_FAILED")
            latest_revision = None
        else:
            latest_revision = int(latest.get("revision") or 1)
            if latest_revision != int(defect.get("revision") or 1):
                await defect_search_index_repository.enqueue(latest)

        return await defect_search_index_repository.complete(
            entry,
            int(defect.get("revision") or 1),
            status="COMPLETED" if latest_revision is not None else "REMOVED",
        )
    except asyncio.CancelledError:
        raise
    except Exception as error:
        await defect_search_index_repository.defer(entry, "INDEX_SYNC_FAILED")
        logger.warning(
            "Defect search indexing deferred project=%s defect=%s error_type=%s",
            project_id,
            defect_id,
            type(error).__name__,
        )
        return True


async def _poll_defect_search_indexes() -> None:
    while True:
        try:
            processed = await process_next_defect_search_index()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.warning("Defect search index polling failed error_type=%s", type(error).__name__)
            processed = False
        if not processed:
            await asyncio.sleep(settings.DEFECT_SEARCH_INDEX_POLL_SECONDS)


async def start_defect_search_index_worker() -> None:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_poll_defect_search_indexes())


async def stop_defect_search_index_worker() -> None:
    global _worker_task
    if _worker_task is None:
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    _worker_task = None
