import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable
from uuid import uuid4

import httpx
from pymongo import ReturnDocument

from src.core.configuration import settings
from src.core.database import database

logger = logging.getLogger(__name__)

class AICapabilityClient:
    async def evaluate_blueprint_against_reference(
        self,
        project_id: str,
        requester_user_id: str,
        sources: list[dict],
        blueprint: dict,
        output_language: str | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/suy-luan/noi-bo/danh-gia/blueprint",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json={
                    "project_id": project_id,
                    "requester_user_id": requester_user_id,
                    "output_language": output_language or "auto",
                    "sources": sources,
                    "blueprint": blueprint,
                },
            )
            response.raise_for_status()
        value = response.json()
        if not isinstance(value, dict) or value.get("assessment_type") not in {
            "NOT_AVAILABLE", "INDEPENDENT_REFERENCE", "SELF_PREPARED_REFERENCE"
        }:
            raise RuntimeError("BLUEPRINT_BENCHMARK_RESPONSE_INVALID")
        return value

    async def summarize_knowledge_text(self, text: str, output_language: str) -> str:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/suy-luan/noi-bo/tom-tat-tai-lieu-tri-thuc",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json={"text": text, "output_language": output_language},
            )
            response.raise_for_status()
        value = response.json()
        summary = value.get("summary") if isinstance(value, dict) else None
        if not isinstance(summary, str) or not summary.strip():
            raise RuntimeError("DOCUMENT_SUMMARY_RESPONSE_INVALID")
        return summary.strip()

    async def convert_attachment(self, filename: str, content: bytes) -> dict:
        import base64

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/tri-thuc/chuyen-doi",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json={
                    "data": base64.b64encode(content).decode("ascii"),
                    "filename": filename,
                },
            )
            response.raise_for_status()
        payload = response.json()
        value = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(value, dict) or not isinstance(value.get("markdown"), str):
            raise RuntimeError("DOCUMENT_CONVERSION_RESPONSE_INVALID")
        return value

    async def recommend_test_case_owners(
        self,
        output_language: str,
        required_skills: list[str],
        candidates: list[dict],
        task_context: str = "",
    ) -> dict:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/tri-thuc/kiem-thu/goi-y-phan-cong",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json={
                    "output_language": output_language,
                    "task_context": task_context,
                    "required_skills": required_skills,
                    "candidates": candidates,
                },
            )
            response.raise_for_status()
        payload = response.json()
        value = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(value, dict):
            raise RuntimeError("OWNER_RECOMMENDATION_RESPONSE_INVALID")
        return value

    async def request(
        self, payload: dict, stream_sink: Callable[[dict], Awaitable[None]] | None = None
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

ai_capability_client = AICapabilityClient()

async def queue_user_requested_document_ingestion(
    document: dict, user, session=None, idempotency_key: str | None = None,
    output_language: str = "auto",
) -> str:
    document_id = str(document["_id"])
    event_id = (
        f"requirement-document:{document_id}:{document.get('revision', 1)}:"
        f"{hashlib.sha256(idempotency_key.encode('utf-8')).hexdigest()}"
        if idempotency_key
        else f"requirement-document:{document_id}:{document.get('revision', 1)}"
    )
    relationship_path = list(
        dict.fromkeys(
            str(item)
            for item in (
                document.get("source_series_id"),
                document.get("previous_source_version_id"),
                document_id,
            )
            if item
        )
    )
    payload = {
        "event_id": event_id,
        "project_id": document["project_id"],
        "requester_user_id": user.id,
        "trigger": "DOCUMENT_INGESTED",
        "user_requested": True,
        "output_language": output_language or "auto",
        "target_artifact_ids": [document_id],
        "evidence": [
            {
                "artifact_type": "requirement_document",
                "artifact_id": document_id,
                "artifact_version_id": document_id,
                "source": "database",
                "authority": str(document.get("authority") or "PROJECT_REFERENCE"),
                "score": 1,
                "text": str(document.get("normalized_content") or "")[:4000],
                "source_hash": str(document.get("content_hash") or ""),
                "relationship_path": relationship_path,
                "project_id": document["project_id"],
                "artifact_status": str(document.get("status") or "INGESTED"),
            }
        ],
    }
    return await persist_document_ingestion_request(payload, session=session)

async def cancel_pending_document_ingestion(document_id: str, reason: str) -> int:
    """Prevent queued source-ingestion events from starting after consent revoke."""
    result = await database.value.ai_run_outbox.update_many(
        {
            "trigger": "DOCUMENT_INGESTED",
            "status": {"$in": ["PENDING", "DISPATCHING"]},
            "payload.evidence": {
                "$elemMatch": {"artifact_type": "requirement_document", "artifact_id": document_id}
            },
        },
        {
            "$set": {
                "status": "CANCELLED",
                "cancel_reason": reason,
                "updated_at": datetime.now(timezone.utc),
            },
            "$unset": {"payload": "", "dispatch_token": ""},
        },
    )
    return int(result.modified_count)

async def cancel_document_ingestion_runs(document_id: str) -> int:
    """Cancel already-dispatched AI runs for every revision of a source document."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.AI_URL.rstrip('/')}/tac-nhan-ai/noi-bo/"
            f"tai-lieu-yeu-cau/{document_id}/huy-luot-chay",
            headers={"X-Internal-Token": settings.SECRET_KEY},
        )
        response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("cancelled_run_count"), int):
        raise RuntimeError("AI_DOCUMENT_RUN_CANCELLATION_RESPONSE_INVALID")
    return payload["cancelled_run_count"]

async def ai_run_is_active(
    run_id: str, worker_revision: int | None = None
) -> bool:
    """Read the authoritative AI run state before an AI identity mutates Testing data."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.AI_URL.rstrip('/')}/tac-nhan-ai/noi-bo/"
            f"luot-chay/{run_id}/trang-thai-thuc-thi",
            headers={"X-Internal-Token": settings.SECRET_KEY},
        )
        response.raise_for_status()
    payload = response.json()
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("active"), bool)
        or not isinstance(payload.get("revision"), int)
    ):
        raise RuntimeError("AI_RUN_STATUS_RESPONSE_INVALID")
    return payload["active"] and (
        worker_revision is None or payload["revision"] == worker_revision
    )

async def ai_run_allows_bug_trace(run_id: str, project_id: str, user_id: str) -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.AI_URL.rstrip('/')}/tac-nhan-ai/noi-bo/"
            f"luot-chay/{run_id}/trang-thai-thuc-thi",
            headers={"X-Internal-Token": settings.SECRET_KEY},
        )
        response.raise_for_status()
    payload = response.json()
    return bool(
        isinstance(payload, dict)
        and payload.get("active") is True
        and payload.get("user_requested") is True
        and payload.get("project_id") == project_id
        and payload.get("requester_user_id") == user_id
        and payload.get("execution_user_id") == user_id
        and (payload.get("trigger") == "MANUAL" or payload.get("intent") == "link_bug_candidates")
    )

async def persist_document_ingestion_request(payload: dict, session=None) -> str:
    event_id = str(payload["event_id"])
    fingerprint = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    timestamp = datetime.now(timezone.utc)
    result = await database.value.ai_run_outbox.update_one(
        {"_id": event_id},
        {
            "$setOnInsert": {
                "payload": payload,
                "event_fingerprint": fingerprint,
                "status": "PENDING",
                "attempts": 0,
                "next_attempt_at": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        },
        upsert=True,
        **({"session": session} if session is not None else {}),
    )
    if getattr(result, "upserted_id", None) is None:
        existing = await database.value.ai_run_outbox.find_one(
            {"_id": event_id},
            {"event_fingerprint": 1, "payload": 1},
            **({"session": session} if session is not None else {}),
        )
        existing_fingerprint = str((existing or {}).get("event_fingerprint") or "")
        if not existing_fingerprint and isinstance((existing or {}).get("payload"), dict):
            existing_fingerprint = hashlib.sha256(
                json.dumps(
                    existing["payload"],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                ).encode("utf-8")
            ).hexdigest()
        if existing_fingerprint != fingerprint:
            raise ValueError("DOCUMENT_INGESTION_REQUEST_ID_REUSE_CONFLICT")
    return event_id

async def dispatch_requested_document_import(event_id: str) -> bool:
    now = datetime.now(timezone.utc)
    dispatch_token = str(uuid4())
    entry = await database.value.ai_run_outbox.find_one_and_update(
        {
            "_id": event_id,
            "$or": [
                {"status": "PENDING", "next_attempt_at": {"$lte": now}},
                {"status": "DISPATCHING", "updated_at": {"$lte": now - timedelta(seconds=60)}},
            ],
        },
        {"$set": {"status": "DISPATCHING", "dispatch_token": dispatch_token, "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not entry:
        existing = await database.value.ai_run_outbox.find_one({"_id": event_id})
        return bool(existing and existing.get("status") in {"DELIVERED", "SUPPRESSED"})

    last_error = None
    for attempt in range(3):
        try:
            event_payload = entry.get("payload")
            if not isinstance(event_payload, dict):
                raise ValueError("AI_EVENT_RESPONSE_INVALID")
            documents = [
                item
                for item in event_payload.get("evidence", [])
                if isinstance(item, dict)
                and item.get("artifact_type") == "requirement_document"
                and item.get("artifact_id")
            ]
            if (
                event_payload.get("trigger") != "DOCUMENT_INGESTED"
                or event_payload.get("user_requested") is not True
                or len(documents) != 1
            ):
                raise ValueError("AI_DOCUMENT_IMPORT_SOURCE_INVALID")
            document = documents[0]
            request_payload = {
                "project_id": event_payload.get("project_id"),
                "requester_user_id": event_payload.get("requester_user_id"),
                "document_id": document["artifact_id"],
                "source_hash": document.get("source_hash"),
                "idempotency_key": event_payload.get("event_id"),
                "output_language": event_payload.get("output_language") or "auto",
            }
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(
                    f"{settings.AI_URL.rstrip('/')}/tac-nhan-ai/noi-bo/yeu-cau-nhap-tai-lieu",
                    headers={"X-Internal-Token": settings.SECRET_KEY},
                    json=request_payload,
                )
                response.raise_for_status()
                result = response.json()
            if not isinstance(result, dict):
                raise ValueError("AI_EVENT_RESPONSE_INVALID")
            response_status = result.get("status")
            if response_status == "accepted":
                runs = result.get("runs")
                if not isinstance(runs, list) or not runs or any(
                    not isinstance(run, dict)
                    or not isinstance(run.get("ai_run_id"), str)
                    or not run["ai_run_id"].strip()
                    or run.get("project_id") != event_payload.get("project_id")
                    or run.get("requester_user_id") != event_payload.get("requester_user_id")
                    or run.get("intent") != "process_ingested_requirement_document"
                    or run.get("kind") != "ON_DEMAND"
                    or (run.get("constraints") or {}).get("user_requested") is not True
                    for run in runs
                ):
                    raise ValueError("AI_EVENT_RESPONSE_INVALID")
                terminal_status = "DELIVERED"
                extra_set = {"ai_run_ids": [run["ai_run_id"] for run in runs]}
                extra_set["delivered_at"] = datetime.now(timezone.utc)
                extra_unset = {"suppression_reason": ""}
            else:
                raise ValueError("AI_EVENT_RESPONSE_INVALID")
            await database.value.ai_run_outbox.update_one(
                {"_id": event_id, "status": "DISPATCHING", "dispatch_token": dispatch_token},
                {
                    "$set": {
                        "status": terminal_status,
                        "updated_at": datetime.now(timezone.utc),
                        **extra_set,
                    },
                    "$unset": {
                        "payload": "",
                        "last_error": "",
                        **extra_unset,
                        "suppressed_at": "",
                        "suppression_reason": "",
                        "dispatch_token": "",
                    },
                },
            )
            current = await database.value.ai_run_outbox.find_one(
                {"_id": event_id}, {"status": 1, "dispatch_token": 1}
            )
            return bool(current and current.get("status") == "DELIVERED")
        except (httpx.HTTPError, ValueError) as error:
            last_error = error
            if attempt < 2:
                await asyncio.sleep(0.25 * (attempt + 1))
    attempts = int(entry.get("attempts") or 0) + 1
    retry_delay = min(3600, 5 * (2 ** min(attempts, 9)))
    error_code = (
        "AI_EVENT_RESPONSE_INVALID"
        if isinstance(last_error, ValueError)
        else type(last_error).__name__
        if last_error
        else "AI_EVENT_DELIVERY_FAILED"
    )
    await database.value.ai_run_outbox.update_one(
        {"_id": event_id, "status": "DISPATCHING", "dispatch_token": dispatch_token},
        {
            "$set": {
                "status": "PENDING",
                "attempts": attempts,
                "last_error": error_code,
                "next_attempt_at": datetime.now(timezone.utc) + timedelta(seconds=retry_delay),
                "updated_at": datetime.now(timezone.utc),
            },
            "$unset": {"dispatch_token": ""},
        },
    )
    logger.warning("User-requested document AI run delivery deferred for %s", event_id)
    return False
