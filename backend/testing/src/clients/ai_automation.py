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
_event_dispatcher_task: asyncio.Task | None = None


def _requirement_event_text(version: dict) -> str:
    """Serialize saved Requirement text fields into source-readable event evidence."""
    parts = []
    content = str(version.get("plain_text_projection") or "").strip()
    if content:
        parts.append(content)

    parts.extend(
        str(item.get("plain_text") or "").strip()
        for item in version.get("acceptance_criteria") or []
        if isinstance(item, dict) and str(item.get("plain_text") or "").strip()
    )

    for field in ("business_rules", "actors", "dependencies"):
        values = version.get(field) or []
        if isinstance(values, str):
            values = [values]
        parts.extend(str(value).strip() for value in values if str(value or "").strip())

    def collect_strings(value):
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, dict):
            return [text for child in value.values() for text in collect_strings(child)]
        if isinstance(value, (list, tuple)):
            return [text for child in value for text in collect_strings(child)]
        return []

    for field in ("details", "custom_values"):
        parts.extend(collect_strings(version.get(field)))
    return "\n".join(parts)


class AIAutomationClient:
    async def convert_attachment(self, filename: str, content: bytes) -> dict:
        import base64

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/tri-thuc/tiep-nap/chuyen-doi",
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

    async def extract_skill_profile(self, project_id: str, source_blocks: list[dict]) -> dict:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/tri-thuc/ho-so-nang-luc/trich-xuat-cv",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json={"project_id": project_id, "source_blocks": source_blocks},
            )
            response.raise_for_status()
        payload = response.json()
        value = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(value, dict):
            raise RuntimeError("AI_CV_EXTRACTION_RESPONSE_INVALID")
        return value

    async def recommend_test_case_owners(
        self,
        project_id: str,
        output_language: str,
        required_skills: list[str],
        candidates: list[dict],
    ) -> dict:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{settings.AI_URL.rstrip('/')}/tri-thuc/kiem-thu/goi-y-phan-cong",
                headers={"X-Internal-Token": settings.SECRET_KEY},
                json={
                    "project_id": project_id,
                    "output_language": output_language,
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


ai_automation_client = AIAutomationClient()


async def emit_requirement_changed(version: dict, user) -> bool:
    if user._ai_automation_run_id:
        return True
    return await emit_event(
        "REQUIREMENT_CHANGED",
        f"requirement-version:{version['_id']}:{version.get('revision', 1)}:{version.get('status', 'DRAFT')}",
        version["project_id"],
        "requirement_version",
        version["requirement_id"],
        version["_id"],
        "requirement",
        _requirement_event_text(version),
        user.id,
        artifact_revision=version.get("revision", 1),
        artifact_status=str(version.get("status") or "DRAFT"),
    )


async def queue_requirement_changed(version: dict, user, session) -> str | None:
    """Persist a Requirement automation event in the caller's Mongo transaction."""
    if user._ai_automation_run_id:
        return None
    event_id = (
        f"requirement-version:{version['_id']}:{version.get('revision', 1)}:"
        f"{version.get('status', 'DRAFT')}"
    )
    return await queue_event(
        "REQUIREMENT_CHANGED",
        event_id,
        version["project_id"],
        "requirement_version",
        version["requirement_id"],
        version["_id"],
        "requirement",
        _requirement_event_text(version),
        user.id,
        session,
        artifact_revision=version.get("revision", 1),
        artifact_status=str(version.get("status") or "DRAFT"),
    )


async def emit_test_execution_recorded(result: dict, user, session=None) -> bool:
    if user._ai_automation_run_id:
        return True
    event = (
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
    if session is not None:
        return await queue_event(
            *event,
            session=session,
            artifact_revision=result.get("revision", 1),
            artifact_status=str(result.get("status") or ""),
        )
    return await emit_event(
        *event,
        artifact_revision=result.get("revision", 1),
        artifact_status=str(result.get("status") or ""),
    )


async def emit_defect_recorded(defect: dict, user, session=None) -> bool:
    if user._ai_automation_run_id:
        return True
    revision = int(defect.get("revision") or 1)
    event = (
        "DEFECT_RECORDED",
        f"defect:{defect['_id']}:{revision}",
        defect["project_id"],
        "defect",
        defect["_id"],
        defect["_id"],
        "defect",
        " ".join(str(defect.get(key) or "") for key in ("title", "description")),
        user.id,
    )
    if session is not None:
        return await queue_event(
            *event,
            session=session,
            artifact_revision=revision,
            artifact_status=str(defect.get("status") or ""),
        )
    return await emit_event(
        *event,
        artifact_revision=revision,
        artifact_status=str(defect.get("status") or ""),
    )


async def emit_defect_changed(defect: dict, user, session=None) -> bool:
    if user._ai_automation_run_id:
        return True
    revision = int(defect.get("revision") or 0)
    if revision < 2:
        raise ValueError("DEFECT_CHANGE_REVISION_REQUIRED")
    event = (
        "DEFECT_CHANGED",
        f"defect:{defect['_id']}:{revision}",
        defect["project_id"],
        "defect",
        defect["_id"],
        defect["_id"],
        "defect",
        " ".join(
            str(defect.get(key) or "")
            for key in (
                "title",
                "description_doc",
                "steps_to_reproduce",
                "actual_result_doc",
                "expected_result_doc",
                "linked_test_result_id",
                "linked_test_case_version_id",
                "linked_requirement_version_ids",
            )
        ),
        user.id,
    )
    if session is not None:
        return await queue_event(
            *event,
            session=session,
            artifact_revision=revision,
            artifact_status=str(defect.get("status") or ""),
        )
    return await emit_event(
        *event,
        artifact_revision=revision,
        artifact_status=str(defect.get("status") or ""),
    )


async def queue_api_operation_confirmed(operation: dict, user, session) -> str | None:
    if user._ai_automation_run_id:
        return None
    operation_id = str(operation.get("_id") or "")
    project_id = str(operation.get("project_id") or "")
    if not operation_id or not project_id:
        raise ValueError("API_OPERATION_EVENT_IDENTITY_REQUIRED")
    revision = operation.get("revision")
    if type(revision) is not int or revision < 1:
        raise ValueError("API_OPERATION_EVENT_REVISION_REQUIRED")
    text = " ".join(
        str(operation.get(field) or "").strip()
        for field in ("method", "path", "operation_id", "summary")
    ).strip()
    return await queue_event(
        "API_OPERATION_CONFIRMED",
        f"api-operation:{operation_id}:r{revision}",
        project_id,
        "api_operation",
        operation_id,
        operation_id,
        "api_definition",
        text,
        user.id,
        session=session,
        artifact_revision=revision,
        artifact_status="CONFIRMED",
    )


async def emit_document_ingested(document: dict, user, session=None) -> bool:
    if user._ai_automation_run_id:
        return True
    event = (
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
    relationship_path = list(
        dict.fromkeys(
            str(item)
            for item in (
                document.get("source_series_id"),
                document.get("previous_source_version_id"),
                document.get("_id"),
            )
            if item
        )
    )
    if session is not None:
        return await queue_event(
            *event,
            session=session,
            relationship_path=relationship_path,
            artifact_status=str(document.get("status") or "INGESTED"),
        )
    return await emit_event(
        *event,
        relationship_path=relationship_path,
        artifact_status=str(document.get("status") or "INGESTED"),
    )


async def cancel_pending_document_ingestion(document_id: str, reason: str) -> int:
    """Prevent queued source-ingestion events from starting after consent revoke."""
    result = await database.value.ai_automation_outbox.update_many(
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
            f"{settings.AI_URL.rstrip('/')}/tu-dong-hoa-ai/noi-bo/"
            f"tai-lieu-yeu-cau/{document_id}/huy-luot-chay",
            headers={"X-Internal-Token": settings.SECRET_KEY},
        )
        response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("cancelled_run_count"), int):
        raise RuntimeError("AI_DOCUMENT_RUN_CANCELLATION_RESPONSE_INVALID")
    return payload["cancelled_run_count"]


async def automation_run_is_active(
    run_id: str, worker_revision: int | None = None
) -> bool:
    """Read the authoritative AI run state before an AI identity mutates Testing data."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.AI_URL.rstrip('/')}/tu-dong-hoa-ai/noi-bo/"
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
        raise RuntimeError("AI_AUTOMATION_STATUS_RESPONSE_INVALID")
    return payload["active"] and (
        worker_revision is None or payload["revision"] == worker_revision
    )


async def emit_work_item_changed(item: dict, user, session=None) -> bool:
    return await emit_artifact_event(
        "WORK_ITEM_CHANGED",
        "work-item",
        item,
        user,
        "work_item",
        ("title", "description", "status", "item_type", "priority", "backlog_rank"),
        session=session,
        artifact_revision=item.get("revision"),
    )


async def emit_work_item_dependency_changed(
    dependency: dict, source: dict, target: dict, user, session=None
) -> bool:
    """Queue one scoped impact event for each endpoint of a saved dependency edge."""
    if user._ai_automation_run_id:
        return True
    project_id = str(dependency.get("project_id") or "")
    dependency_id = str(dependency.get("_id") or "")
    source_id = str(source.get("_id") or "")
    target_id = str(target.get("_id") or "")
    dependency_type = str(dependency.get("dependency_type") or "")
    if (
        not project_id
        or not dependency_id
        or not source_id
        or not target_id
        or source.get("project_id") != project_id
        or target.get("project_id") != project_id
        or dependency_type not in {"BLOCKS", "RELATES_TO"}
    ):
        return False
    relationship = {
        "relationship_id": dependency_id,
        "relationship_type": dependency_type,
        "project_id": project_id,
        "source_artifact_id": source_id,
        "target_artifact_id": target_id,
    }

    results = []
    for item, opposite_id in ((source, target_id), (target, source_id)):
        item_id = str(item["_id"])
        version_id = str(item.get("current_version_id") or item.get("frozen_version_id") or item_id)
        event_id = f"work-item-dependency:{dependency_id}:{item_id}:WORK_ITEM_CHANGED"
        text = " ".join(
            part
            for part in (
                (
                    f"Work Item {target_id} blocks Work Item {source_id}."
                    if dependency_type == "BLOCKS"
                    else f"Work Item {source_id} is related to Work Item {target_id}."
                ),
                f"Affected endpoint: {item_id}.",
                f"Related endpoint: {opposite_id}.",
                str(item.get("title") or "").strip(),
                str(item.get("description") or "").strip(),
            )
            if part
        )
        event = (
            "WORK_ITEM_CHANGED",
            event_id,
            project_id,
            "work_item",
            item_id,
            version_id,
            "database",
            text,
            user.id,
        )
        if session is not None:
            results.append(
                await queue_event(
                    *event,
                    session=session,
                    relationship_path=[source_id, target_id],
                    relationship=relationship,
                    artifact_revision=item.get("revision"),
                    artifact_status=str(item.get("status") or ""),
                )
            )
        else:
            results.append(
                await emit_event(
                    *event,
                    relationship_path=[source_id, target_id],
                    relationship=relationship,
                    artifact_revision=item.get("revision"),
                    artifact_status=str(item.get("status") or ""),
                )
            )
    return all(results)


async def emit_test_case_changed(
    case: dict, user, previous_case: dict | None = None, session=None
) -> bool:
    if user._ai_automation_run_id:
        return True
    case_id = str(case.get("_id") or "")
    project_id = str(case.get("project_id") or "")
    if not case_id or not project_id:
        return False

    def render(value):
        if isinstance(value, dict):
            if isinstance(value.get("text"), str):
                return value["text"]
            return " ".join(fragment for item in value.values() if (fragment := render(item)))
        if isinstance(value, (list, tuple)):
            return " ".join(fragment for item in value if (fragment := render(item)))
        return str(value).strip() if value is not None else ""

    fields = (
        "title",
        "type",
        "objective_doc",
        "preconditions_doc",
        "steps",
        "test_data",
        "expected_result_doc",
        "postconditions_doc",
        "requirement_version_ids",
        "acceptance_criterion_ids",
        "coverage_item_ids",
        "test_condition_ids",
        "evidence_refs",
        "source_evidence",
        "coverage_obligations",
        "challenge_hypotheses",
        "bdd",
    )
    changed_fields = [
        name
        for name in fields
        if previous_case is not None and previous_case.get(name) != case.get(name)
    ]
    revision = int(case.get("revision") or 1)
    event_kind = "CREATED" if previous_case is None else "UPDATED"
    lines = [
        f"Event type: TEST_CASE_{event_kind}",
        f"Test Case: {case.get('test_case_key') or case_id}",
        f"Current revision: {revision}",
    ]
    if previous_case is None:
        lines.append("Previous revision: unavailable; this event records initial creation")
        event_fields = fields
    else:
        lines.append(f"Previous revision: {int(previous_case.get('revision') or 1)}")
        lines.append("Changed fields: " + (", ".join(changed_fields) or "none"))
        event_fields = list(
            dict.fromkeys(
                [
                    "title",
                    *changed_fields,
                    "requirement_version_ids",
                    "acceptance_criterion_ids",
                    "coverage_item_ids",
                    "test_condition_ids",
                    "evidence_refs",
                    "source_evidence",
                ]
            )
        )
    for label, source in (("Before", previous_case), ("Current", case)):
        if source is None:
            continue
        lines.append(f"{label} Test Case content:")
        for name in event_fields:
            value = render(source.get(name))
            if value:
                lines.append(f"{name}: {value}")

    event = (
        "TEST_CASE_CHANGED",
        f"test-case:{case_id}:{revision}:TEST_CASE_CHANGED",
        project_id,
        "test_case_draft",
        case_id,
        str(case.get("current_version_id") or case_id),
        "database",
        "\n".join(lines),
        user.id,
    )
    if session is not None:
        return await queue_event(
            *event,
            session=session,
            artifact_revision=revision,
            artifact_status=str(case.get("status") or "DRAFT"),
        )
    return await emit_event(
        *event,
        artifact_revision=revision,
        artifact_status=str(case.get("status") or "DRAFT"),
    )


async def emit_test_case_approved(version: dict, user) -> bool:
    return await emit_artifact_event(
        "TEST_CASE_APPROVED",
        "test-case-version",
        version,
        user,
        "test_case_version",
        ("title", "description", "test_steps", "expected_result"),
    )


async def queue_test_case_approved(version: dict, user, session) -> str | None:
    """Persist approval automation in the caller's transaction for crash-safe delivery."""
    if user._ai_automation_run_id:
        return None
    artifact_id = str(version.get("_id") or "")
    project_id = str(version.get("project_id") or "")
    if not artifact_id or not project_id:
        raise ValueError("TEST_CASE_APPROVAL_EVENT_CONTEXT_MISSING")
    revision = version.get("revision", 1)
    event_id = f"test-case-version:{artifact_id}:{revision}:TEST_CASE_APPROVED"
    content = str(version.get("plain_text_projection") or version.get("title") or "").strip()
    version_id = str(
        version.get("current_version_id") or version.get("frozen_version_id") or artifact_id
    )
    return await queue_event(
        "TEST_CASE_APPROVED",
        event_id,
        project_id,
        "test_case_version",
        artifact_id,
        version_id,
        "database",
        content,
        user.id,
        session=session,
        artifact_revision=revision if type(revision) is int else None,
        artifact_status=str(version.get("status") or "APPROVED"),
    )


async def emit_test_plan_changed(plan: dict, user, session=None) -> bool:
    return await emit_artifact_event(
        "TEST_PLAN_CHANGED",
        "test-plan",
        plan,
        user,
        "test_plan",
        ("name", "description", "status", "release_id", "build_id", "environment_id"),
        session=session,
    )


async def emit_test_plan_approved(plan: dict, user, session=None) -> bool:
    return await emit_artifact_event(
        "TEST_PLAN_APPROVED",
        "test-plan",
        plan,
        user,
        "test_plan",
        ("name", "description", "status", "release_id", "build_id", "environment_id"),
        session=session,
    )


async def emit_status_report_created(report: dict, user, session=None) -> bool:
    return await emit_artifact_event(
        "STATUS_REPORT_CREATED",
        "status-report",
        report,
        user,
        "test_status_report",
        (
            "executive_summary",
            "progress_summary",
            "coverage_summary",
            "defect_summary",
            "recommendation",
            "blockers",
            "risks",
        ),
        session=session,
    )


async def emit_test_completion_report_created(report: dict, user, session=None) -> bool:
    return await emit_artifact_event(
        "TEST_COMPLETION_REPORT_CREATED",
        "completion-report",
        report,
        user,
        "test_completion_report",
        (
            "execution_summary",
            "coverage_summary",
            "defect_summary",
            "quality_gate_status",
            "recommendation",
            "lessons_learned",
        ),
        session=session,
    )


async def emit_performance_configuration_approved(plan: dict, user, session=None) -> bool:
    return await emit_artifact_event(
        "PERFORMANCE_CONFIGURATION_APPROVED",
        "performance-configuration",
        plan,
        user,
        "non_functional_test_plan",
        (
            "name",
            "objective",
            "plan_type",
            "requirement_refs",
            "workload_model",
            "baseline",
            "load",
            "stress",
            "spike",
            "soak",
            "concurrency",
            "duration_minutes",
            "throughput_target",
            "response_time_target",
            "error_rate_target",
        ),
        session=session,
    )


async def emit_release_changed(release: dict, user, session=None) -> bool:
    return await emit_artifact_event(
        "RELEASE_CHANGED",
        "release",
        release,
        user,
        "release",
        ("name", "description", "status", "start_date", "due_date"),
        session=session,
    )


async def emit_release_gate_recheck(
    release: dict,
    source_artifact: dict,
    user,
    session=None,
    artifact_type="test_result",
) -> bool:
    if user._ai_automation_run_id or release.get("status") != "ACTIVE":
        return True
    release_id = str(release.get("_id") or "")
    source_type = artifact_type
    source_id = str(source_artifact.get("_id") or "")
    source_revision = source_artifact.get("revision")
    if (
        not release_id
        or not source_id
        or source_type not in {"test_result", "defect"}
        or type(source_revision) is not int
        or source_revision < 1
        or release.get("project_id") != source_artifact.get("project_id")
    ):
        return False
    event_source_type = source_type.replace("_", "-")
    event = (
        "RELEASE_CHANGED",
        f"release-gate:{release_id}:{event_source_type}:{source_id}:r{source_revision}",
        release["project_id"],
        "release",
        release_id,
        release_id,
        "release_gate",
        f"{source_type} {source_id} changed to {source_artifact.get('status') or 'unknown'}; re-evaluate Release completion gates.",
        user.id,
    )
    revision = release.get("revision")
    if type(revision) is not int or revision < 1:
        return False
    if session is not None:
        return await queue_event(
            *event,
            session=session,
            artifact_revision=revision,
            artifact_status=str(release.get("status") or ""),
        )
    return await emit_event(
        *event,
        artifact_revision=revision,
        artifact_status=str(release.get("status") or ""),
    )


async def emit_artifact_event(
    trigger: str,
    event_prefix: str,
    artifact: dict,
    user,
    artifact_type: str,
    fields: tuple[str, ...],
    session=None,
    artifact_revision: int | None = None,
) -> bool:
    if user._ai_automation_run_id:
        return True
    artifact_id = str(artifact.get("_id") or "")
    if not artifact_id or not artifact.get("project_id"):
        return False
    revision = artifact.get("revision", 1)
    revision = (
        artifact_revision if type(artifact_revision) is int and artifact_revision >= 1 else revision
    )
    verified_revision = revision if type(revision) is int and revision >= 1 else None
    content = " ".join(str(artifact.get(key) or "") for key in fields)
    event = (
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
    if session is not None:
        return await queue_event(
            *event,
            session=session,
            artifact_revision=verified_revision,
            artifact_status=str(artifact.get("status") or ""),
        )
    return await emit_event(
        *event,
        artifact_revision=verified_revision,
        artifact_status=str(artifact.get("status") or ""),
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
    relationship_path: list[str] | None = None,
    relationship: dict | None = None,
    artifact_revision: int | None = None,
    artifact_status: str | None = None,
) -> bool:
    await queue_event(
        trigger,
        event_id,
        project_id,
        artifact_type,
        artifact_id,
        artifact_version_id,
        authority,
        text,
        requester_user_id,
        relationship_path=relationship_path,
        relationship=relationship,
        artifact_revision=artifact_revision,
        artifact_status=artifact_status,
    )
    existing = await database.value.ai_automation_outbox.find_one({"_id": event_id})
    if existing and existing.get("status") in {"DELIVERED", "SUPPRESSED"}:
        return True
    return await _dispatch_event(event_id)


async def queue_event(
    trigger: str,
    event_id: str,
    project_id: str,
    artifact_type: str,
    artifact_id: str,
    artifact_version_id: str,
    authority: str,
    text: str,
    requester_user_id: str,
    session=None,
    relationship_path: list[str] | None = None,
    relationship: dict | None = None,
    artifact_revision: int | None = None,
    artifact_status: str | None = None,
) -> str:
    """Idempotently persist an event; pass a session to make it atomic with domain writes."""
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
                "relationship_path": list(relationship_path or []),
                **({"relationship": relationship} if relationship is not None else {}),
                "project_id": project_id,
                **(
                    {"artifact_revision": artifact_revision}
                    if type(artifact_revision) is int and artifact_revision >= 1
                    else {}
                ),
                **({"artifact_status": artifact_status} if artifact_status else {}),
            }
        ],
    }
    event_fingerprint = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    timestamp = datetime.now(timezone.utc)
    result = await database.value.ai_automation_outbox.update_one(
        {"_id": event_id},
        {
            "$setOnInsert": {
                "payload": payload,
                "event_fingerprint": event_fingerprint,
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
        existing = await database.value.ai_automation_outbox.find_one(
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
            await database.value.ai_automation_outbox.update_one(
                {"_id": event_id, "event_fingerprint": {"$exists": False}},
                {"$set": {"event_fingerprint": existing_fingerprint}},
                **({"session": session} if session is not None else {}),
            )
        if existing_fingerprint != event_fingerprint:
            existing_payload = (existing or {}).get("payload")
            compatible_legacy_test_case_event = False
            if (
                trigger == "TEST_CASE_CHANGED"
                and type(artifact_revision) is int
                and artifact_revision >= 1
                and isinstance(existing_payload, dict)
                and isinstance(existing_payload.get("evidence"), list)
                and isinstance(payload.get("evidence"), list)
            ):
                old_evidence = existing_payload["evidence"]
                new_evidence = payload["evidence"]
                compatible_legacy_test_case_event = bool(old_evidence) and all(
                    isinstance(item, dict) and "artifact_revision" not in item
                    for item in old_evidence
                )
                if compatible_legacy_test_case_event:
                    old_payload_without_revision = {
                        **existing_payload,
                        "evidence": old_evidence,
                    }
                    new_payload_without_revision = {
                        **payload,
                        "evidence": [
                            {
                                key: value
                                for key, value in item.items()
                                if key != "artifact_revision"
                            }
                            for item in new_evidence
                        ],
                    }
                    compatible_legacy_test_case_event = (
                        all(
                            item.get("artifact_revision") == artifact_revision
                            for item in new_evidence
                        )
                        and old_payload_without_revision == new_payload_without_revision
                    )
            if not compatible_legacy_test_case_event:
                raise ValueError("AI_AUTOMATION_EVENT_ID_REUSE_CONFLICT")
    return event_id


async def _dispatch_event(event_id: str) -> bool:
    now = datetime.now(timezone.utc)
    dispatch_token = str(uuid4())
    entry = await database.value.ai_automation_outbox.find_one_and_update(
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
        existing = await database.value.ai_automation_outbox.find_one({"_id": event_id})
        return bool(existing and existing.get("status") in {"DELIVERED", "SUPPRESSED"})

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
                result = response.json()
            if not isinstance(result, dict):
                raise ValueError("AI_EVENT_RESPONSE_INVALID")
            response_status = result.get("status")
            if response_status == "accepted":
                runs = result.get("runs")
                event_payload = entry.get("payload")
                if not isinstance(event_payload, dict):
                    raise ValueError("AI_EVENT_RESPONSE_INVALID")
                if (
                    not isinstance(runs, list)
                    or not runs
                    or any(
                        not isinstance(run, dict)
                        or not isinstance(run.get("automation_run_id"), str)
                        or not run["automation_run_id"].strip()
                        or run.get("project_id") != event_payload.get("project_id")
                        or run.get("source_event_id") != event_payload.get("event_id")
                        or run.get("trigger") != event_payload.get("trigger")
                        or run.get("kind") != "EVENT"
                        or run.get("source_event_verified") is not True
                        for run in runs
                    )
                ):
                    raise ValueError("AI_EVENT_RESPONSE_INVALID")
                terminal_status = "DELIVERED"
                extra_set = {"automation_run_ids": [run["automation_run_id"] for run in runs]}
                extra_set["delivered_at"] = datetime.now(timezone.utc)
                extra_unset = {"suppression_reason": ""}
            elif response_status == "suppressed":
                reason_code = result.get("reason_code")
                if reason_code != "AUTOMATION_TRIGGER_DISABLED" or result.get("runs") != []:
                    raise ValueError("AI_EVENT_RESPONSE_INVALID")
                terminal_status = "SUPPRESSED"
                extra_set = {"suppression_reason": reason_code}
                extra_set["suppressed_at"] = datetime.now(timezone.utc)
                extra_unset = {"automation_run_ids": ""}
            else:
                raise ValueError("AI_EVENT_RESPONSE_INVALID")
            await database.value.ai_automation_outbox.update_one(
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
                        **(
                            {"suppressed_at": ""}
                            if terminal_status == "DELIVERED"
                            else {"delivered_at": ""}
                        ),
                        "dispatch_token": "",
                    },
                },
            )
            current = await database.value.ai_automation_outbox.find_one(
                {"_id": event_id}, {"status": 1, "dispatch_token": 1}
            )
            return bool(current and current.get("status") in {"DELIVERED", "SUPPRESSED"})
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
    await database.value.ai_automation_outbox.update_one(
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
                        {
                            "status": "DISPATCHING",
                            "updated_at": {"$lte": now - timedelta(seconds=60)},
                        },
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
