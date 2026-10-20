import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

import httpx
from pymongo import ReturnDocument

from src.core.configuration import settings
from src.core.database import database

logger = logging.getLogger(__name__)
_event_dispatcher_task: asyncio.Task | None = None


class AIAutomationClient:
    async def request(
        self,
        payload: dict,
        stream_sink: Callable[[dict], Awaitable[None]] | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=1800) as client:
            if not stream_sink:
                response = await client.post(
                    f"{settings.AI_URL.rstrip('/')}/suy-luan/noi-bo/kiem-thu/tao-ket-qua",
                    headers={"X-Internal-Token": settings.SECRET_KEY},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

            async with client.stream(
                "POST",
                f"{settings.AI_URL.rstrip('/')}/suy-luan/noi-bo/kiem-thu/tao-ket-qua/stream",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json=payload,
            ) as response:
                if response.is_error:
                    await response.aread()
                response.raise_for_status()
                result = None
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if event.get("type") == "delta":
                        await stream_sink({"type": "delta", "delta": str(event.get("delta") or "")})
                    elif event.get("type") == "result":
                        result = event.get("data")
                    elif event.get("type") == "error":
                        raise RuntimeError(str(event.get("code") or "AI_STREAM_FAILED"))
            if not isinstance(result, dict):
                raise RuntimeError("AI_STREAM_RESULT_MISSING")
            return result


ai_automation_client = AIAutomationClient()


async def emit_requirement_changed(version: dict, user) -> bool:
    if user._ai_automation_run_id:
        return True
    return await emit_event(
        "REQUIREMENT_CHANGED",
        f"requirement-version:{version['_id']}",
        version["project_id"],
        "requirement_version",
        version["requirement_id"],
        version["_id"],
        "requirement",
        version.get("plain_text_projection") or "",
        user.id,
    )


async def emit_test_execution_recorded(result: dict, user) -> bool:
    if user._ai_automation_run_id:
        return True
    return await emit_event(
        "TEST_EXECUTION_RECORDED",
        f"test-result:{result['_id']}:{result.get('revision', 1)}",
        result["project_id"],
        "test_result",
        result["_id"],
        result["_id"],
        "execution",
        " ".join(str(result.get(key) or "") for key in ("status", "note")),
        user.id,
    )


async def emit_defect_recorded(defect: dict, user) -> bool:
    if user._ai_automation_run_id:
        return True
    return await emit_event(
        "DEFECT_RECORDED",
        f"defect:{defect['_id']}:{defect.get('revision', 1)}",
        defect["project_id"],
        "defect",
        defect["_id"],
        defect["_id"],
        "defect",
        " ".join(str(defect.get(key) or "") for key in ("title", "description")),
        user.id,
    )


async def emit_document_ingested(document: dict, user) -> bool:
    if user._ai_automation_run_id:
        return True
    return await emit_event(
        "DOCUMENT_INGESTED",
        f"requirement-document:{document['_id']}:{document.get('revision', 1)}",
        document["project_id"],
        "requirement_document",
        document["_id"],
        document["_id"],
        str(document.get("authority") or "PROJECT_REFERENCE"),
        str(document.get("normalized_content") or ""),
        user.id,
    )


async def emit_work_item_changed(item: dict, user) -> bool:
    return await emit_artifact_event(
        "WORK_ITEM_CHANGED", "work-item", item, user, "work_item",
        ("title", "description", "status", "item_type", "priority"),
    )


async def emit_test_case_changed(case: dict, user) -> bool:
    return await emit_artifact_event(
        "TEST_CASE_CHANGED", "test-case", case, user, "test_case_draft",
        ("title", "description", "status", "test_case_key", "origin"),
    )


async def emit_test_case_approved(version: dict, user) -> bool:
    return await emit_artifact_event(
        "TEST_CASE_APPROVED", "test-case-version", version, user, "test_case_version",
        ("title", "description", "test_steps", "expected_result"),
    )


async def emit_test_plan_changed(plan: dict, user) -> bool:
    return await emit_artifact_event(
        "TEST_PLAN_CHANGED", "test-plan", plan, user, "test_plan",
        ("name", "description", "status", "release_id", "build_id", "environment_id"),
    )


async def emit_test_plan_approved(plan: dict, user) -> bool:
    return await emit_artifact_event(
        "TEST_PLAN_APPROVED", "test-plan", plan, user, "test_plan",
        ("name", "description", "status", "release_id", "build_id", "environment_id"),
    )


async def emit_release_changed(release: dict, user) -> bool:
    return await emit_artifact_event(
        "RELEASE_CHANGED", "release", release, user, "release",
        ("name", "description", "status", "start_date", "due_date"),
    )


async def emit_artifact_event(
    trigger: str,
    event_prefix: str,
    artifact: dict,
    user,
    artifact_type: str,
    fields: tuple[str, ...],
) -> bool:
    if user._ai_automation_run_id:
        return True
    artifact_id = str(artifact.get("_id") or "")
    if not artifact_id or not artifact.get("project_id"):
        return False
    revision = artifact.get("revision", 1)
    content = " ".join(str(artifact.get(key) or "") for key in fields)
    return await emit_event(
        trigger,
        f"{event_prefix}:{artifact_id}:{revision}:{trigger}",
        artifact["project_id"],
        artifact_type,
        artifact_id,
        str(artifact.get("current_version_id") or artifact.get("frozen_version_id") or artifact_id),
        "database",
        content,
        user.id,
    )


async def emit_event(
    trigger: str,
    event_id: str,
    project_id: str,
    artifact_type: str,
    artifact_id: str,
    artifact_version_id: str,
    authority: str,
    text: str,
    requester_user_id: str,
) -> bool:
    payload = {
        "event_id": event_id,
        "project_id": project_id,
        "requester_user_id": requester_user_id,
        "trigger": trigger,
        "target_artifact_ids": [artifact_version_id],
        "evidence": [
            {
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
                "artifact_version_id": artifact_version_id,
                "source": "database",
                "authority": authority,
                "score": 1,
                "text": text[:4000],
                "project_id": project_id,
            }
        ],
    }
    timestamp = datetime.now(timezone.utc)
    await database.value.ai_automation_outbox.update_one(
        {"_id": event_id},
        {
            "$setOnInsert": {
                "payload": payload,
                "status": "PENDING",
                "attempts": 0,
                "next_attempt_at": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        },
        upsert=True,
    )
    existing = await database.value.ai_automation_outbox.find_one({"_id": event_id})
    if existing and existing.get("status") == "DELIVERED":
        return True
    return await _dispatch_event(event_id)


async def _dispatch_event(event_id: str) -> bool:
    now = datetime.now(timezone.utc)
    entry = await database.value.ai_automation_outbox.find_one_and_update(
        {
            "_id": event_id,
            "$or": [
                {"status": "PENDING", "next_attempt_at": {"$lte": now}},
                {"status": "DISPATCHING", "updated_at": {"$lte": now - timedelta(seconds=60)}},
            ],
        },
        {"$set": {"status": "DISPATCHING", "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not entry:
        existing = await database.value.ai_automation_outbox.find_one({"_id": event_id})
        return bool(existing and existing.get("status") == "DELIVERED")

    last_error = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(
                    f"{settings.AI_URL.rstrip('/')}/tu-dong-hoa-ai/noi-bo/su-kien",
                    headers={"X-Internal-Token": settings.SECRET_KEY},
                    json=entry["payload"],
                )
                response.raise_for_status()
            await database.value.ai_automation_outbox.update_one(
                {"_id": event_id, "status": "DISPATCHING"},
                {
                    "$set": {
                        "status": "DELIVERED",
                        "updated_at": datetime.now(timezone.utc),
                        "delivered_at": datetime.now(timezone.utc),
                    },
                    "$unset": {"payload": "", "last_error": ""},
                },
            )
            return True
        except httpx.HTTPError as error:
            last_error = error
            if attempt < 2:
                await asyncio.sleep(0.25 * (attempt + 1))
    attempts = int(entry.get("attempts") or 0) + 1
    retry_delay = min(3600, 5 * (2 ** min(attempts, 9)))
    await database.value.ai_automation_outbox.update_one(
        {"_id": event_id, "status": "DISPATCHING"},
        {
            "$set": {
                "status": "PENDING",
                "attempts": attempts,
                "last_error": type(last_error).__name__ if last_error else "AI_EVENT_DELIVERY_FAILED",
                "next_attempt_at": datetime.now(timezone.utc) + timedelta(seconds=retry_delay),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    logger.warning("AI automation event delivery deferred for %s", event_id)
    return False


async def _dispatch_pending_events() -> None:
    while True:
        try:
            now = datetime.now(timezone.utc)
            entry = await database.value.ai_automation_outbox.find_one(
                {
                    "$or": [
                        {"status": "PENDING", "next_attempt_at": {"$lte": now}},
                        {"status": "DISPATCHING", "updated_at": {"$lte": now - timedelta(seconds=60)}},
                    ]
                },
                sort=[("next_attempt_at", 1)],
            )
            if entry:
                await _dispatch_event(str(entry["_id"]))
                continue
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI automation outbox polling failed")
        await asyncio.sleep(5)


async def start_event_dispatcher() -> None:
    global _event_dispatcher_task
    if not _event_dispatcher_task or _event_dispatcher_task.done():
        _event_dispatcher_task = asyncio.create_task(_dispatch_pending_events())


async def stop_event_dispatcher() -> None:
    global _event_dispatcher_task
    if _event_dispatcher_task:
        _event_dispatcher_task.cancel()
        try:
            await _event_dispatcher_task
        except asyncio.CancelledError:
            pass
        _event_dispatcher_task = None
