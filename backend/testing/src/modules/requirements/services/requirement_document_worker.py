import asyncio
import logging
from datetime import timedelta

from fastapi import HTTPException

from src.core.auth import CurrentUser
from src.core.common import audit, get_project, now
from src.core.configuration import settings
from src.modules.requirements.services.requirement_documents import (
    ParseRequirementDocumentCommand,
    retry_requirement_document_parse_record,
)
from src.repositories.requirement_document import requirement_document_repository

logger = logging.getLogger(__name__)

_worker_task: asyncio.Task | None = None


async def process_next_requirement_document_parse() -> bool:
    current_time = now()
    stale_before = current_time - timedelta(
        seconds=settings.DOCUMENT_PARSE_LEASE_SECONDS
    )
    document = await requirement_document_repository.next_parse_candidate(
        stale_before, current_time
    )
    if not document:
        return False

    owner_id = str(document.get("created_by") or "")
    user = CurrentUser(_id=owner_id, email="")
    try:
        await get_project(
            document["project_id"], user, "requirement_document.extract"
        )
    except HTTPException as error:
        if error.status_code == 423:
            return await requirement_document_repository.defer_parse_attempt(
                document,
                current_time
                + timedelta(seconds=settings.REQUIREMENT_DOCUMENT_PARSE_POLL_SECONDS),
                stale_before,
            )
        if error.status_code not in {403, 404}:
            raise
        failed = await requirement_document_repository.fail_unavailable_owner_parse(
            document,
            "DOCUMENT_OWNER_ACCESS_UNAVAILABLE",
            now(),
            stale_before,
        )
        if failed:
            await audit(
                "SYSTEM",
                "requirement_document_parse_blocked",
                "RequirementDocument",
                document["_id"],
                document["project_id"],
                {"error_code": "DOCUMENT_OWNER_ACCESS_UNAVAILABLE"},
            )
        return True

    try:
        await retry_requirement_document_parse_record(
            document["_id"],
            ParseRequirementDocumentCommand(
                expected_revision=int(document.get("revision") or 1)
            ),
            user,
            _document=document,
        )
    except HTTPException as error:
        if error.status_code != 409:
            logger.warning(
                "Requirement parse worker deferred document=%s status=%s",
                document.get("_id"),
                error.status_code,
            )
    except Exception:
        logger.exception(
            "Requirement parse worker failed document=%s", document.get("_id")
        )
    return True


async def _poll_requirement_document_parses() -> None:
    while True:
        try:
            await process_next_requirement_document_parse()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Requirement document parse polling failed")
        await asyncio.sleep(settings.REQUIREMENT_DOCUMENT_PARSE_POLL_SECONDS)


async def start_requirement_document_parse_worker() -> None:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_poll_requirement_document_parses())


async def stop_requirement_document_parse_worker() -> None:
    global _worker_task
    if _worker_task is None:
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    _worker_task = None
