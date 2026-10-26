from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_entity, new_id, now, optimistic_patch
from src.modules.quality.services.defect_analysis import build_defect_trace_candidates
from src.repositories.defect import defect_repository


async def suggest_defect_trace_record(project_id, defect_id, payload, user):
    defect = await get_project_entity("defects", defect_id, user, "ai.suggest_bug_trace")
    if defect["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    if (
        not getattr(user, "_ai_automation_run_id", "")
        or getattr(user, "_ai_automation_trigger", "") != payload.source_event_trigger
    ):
        raise HTTPException(status_code=403, detail={"code": "VERIFIED_DEFECT_EVENT_REQUIRED"})
    expected_event_id = f"defect:{defect_id}:{payload.source_event_revision}"
    if (
        payload.source_event_id != expected_event_id
        or defect.get("revision") != payload.source_event_revision
    ):
        raise HTTPException(status_code=409, detail={"code": "DEFECT_TRACE_SOURCE_CHANGED"})
    existing = await defect_repository.find_ai_result_by_idempotency(
        project_id, payload.idempotency_key
    )
    if existing:
        if (
            existing.get("subject_id") != defect_id
            or existing.get("result_type") != "BUG_TRACE_SUGGESTION"
            or existing.get("source_event_id") != payload.source_event_id
            or existing.get("source_event_revision") != payload.source_event_revision
            or existing.get("source_event_trigger") != payload.source_event_trigger
        ):
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        return existing
    requirement_candidates, test_case_candidates = await build_defect_trace_candidates(defect)
    result = {
        "_id": new_id("AIR"),
        "project_id": project_id,
        "result_type": "BUG_TRACE_SUGGESTION",
        "subject_type": "defect",
        "subject_id": defect_id,
        "source_event_id": payload.source_event_id,
        "source_event_revision": payload.source_event_revision,
        "source_event_trigger": payload.source_event_trigger,
        "status": "SUCCESS",
        "candidate_only": True,
        "human_confirmation_required": True,
        "requirement_candidates": requirement_candidates,
        "test_case_candidates": test_case_candidates,
        "model": {
            "provider": "hybrid-deterministic",
            "model": "defect_trace_evidence",
            "prompt_version": "defect_trace",
            "tool_schema_version": "1",
            "retrieval_version": "project_evidence",
        },
        "idempotency_key": payload.idempotency_key,
        "review_status": "PENDING",
        "revision": 1,
        "created_by": user.id,
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        await defect_repository.insert_ai_result(result)
    except DuplicateKeyError:
        existing = await defect_repository.find_ai_result_by_idempotency(
            project_id, payload.idempotency_key
        )
        if not existing:
            raise
        if (
            existing.get("subject_id") != defect_id
            or existing.get("result_type") != "BUG_TRACE_SUGGESTION"
            or existing.get("source_event_id") != payload.source_event_id
            or existing.get("source_event_revision") != payload.source_event_revision
            or existing.get("source_event_trigger") != payload.source_event_trigger
        ):
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        return existing
    await audit(
        user.id,
        "bug_trace_suggestion_generated",
        "AIResult",
        result["_id"],
        project_id,
        {
            "defect_id": defect_id,
            "requirement_candidate_count": len(requirement_candidates),
            "test_case_candidate_count": len(test_case_candidates),
        },
    )
    return result


async def list_defect_trace_suggestions(project_id, defect_ids, user):
    await get_project(project_id, user, "ai.suggest_bug_trace")
    normalized_ids = list(dict.fromkeys(str(value) for value in defect_ids if str(value)))
    if not normalized_ids:
        return []
    if len(normalized_ids) > 500:
        raise HTTPException(status_code=422, detail={"code": "DEFECT_ID_LIMIT_EXCEEDED"})
    values = await defect_repository.list_ai_results_for_defects(project_id, normalized_ids)
    latest_by_defect = {}
    for item in values:
        latest_by_defect.setdefault(item["subject_id"], item)
    return list(latest_by_defect.values())


async def list_defect_trace_candidates(defect_id, user):
    defect = await get_project_entity("defects", defect_id, user, "ai.suggest_bug_trace")
    _, test_case_candidates = await build_defect_trace_candidates(defect)
    return test_case_candidates


async def update_defect_trace_record(project_id, defect_id, payload, user):
    defect = await get_project_entity(
        "defects",
        defect_id,
        user,
        "defect.trace.manage",
        assigned_role="DEVELOPER",
        assigned_user_field="assignee",
    )
    if defect["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    changes = {}
    fields = payload.model_fields_set
    if "linked_test_result_id" in fields:
        if payload.linked_test_result_id:
            result = await defect_repository.find_test_result(
                payload.linked_test_result_id, project_id, "FAIL"
            )
            if not result:
                raise HTTPException(
                    status_code=422, detail={"code": "DEFECT_REQUIRES_FAILED_RESULT"}
                )
        changes["linked_test_result_id"] = payload.linked_test_result_id
    if "linked_test_case_version_id" in fields:
        if payload.linked_test_case_version_id:
            version = await defect_repository.find_test_case_version(
                payload.linked_test_case_version_id, project_id
            )
            if not version:
                raise HTTPException(status_code=422, detail={"code": "INVALID_TEST_CASE_VERSION"})
        changes["linked_test_case_version_id"] = payload.linked_test_case_version_id
    if "linked_requirement_version_ids" in fields:
        requirement_ids = list(dict.fromkeys(payload.linked_requirement_version_ids or []))
        count = await defect_repository.count_requirement_versions(project_id, requirement_ids)
        if count != len(requirement_ids):
            raise HTTPException(status_code=422, detail={"code": "INVALID_REQUIREMENT_VERSION"})
        changes["linked_requirement_version_ids"] = requirement_ids
    ai_result = None
    if payload.ai_result_id:
        ai_result = await defect_repository.find_ai_result(
            payload.ai_result_id, project_id, "BUG_TRACE_SUGGESTION", defect_id
        )
        if not ai_result:
            raise HTTPException(status_code=422, detail={"code": "INVALID_AI_RESULT"})
        candidates = ai_result.get("requirement_candidates", []) + ai_result.get(
            "test_case_candidates", []
        )
        candidate_ids = {item.get("candidate_id") for item in candidates}
        if (
            not payload.accepted_candidate_ids
            or not set(payload.accepted_candidate_ids) <= candidate_ids
        ):
            raise HTTPException(status_code=422, detail={"code": "INVALID_AI_CANDIDATE"})
        accepted = {
            item["candidate_id"]: item
            for item in candidates
            if item.get("candidate_id") in payload.accepted_candidate_ids
        }
        accepted_requirements = {
            item["artifact_id"]
            for item in accepted.values()
            if item.get("artifact_type") == "requirement_version"
        }
        accepted_test_cases = {
            item["artifact_id"]
            for item in accepted.values()
            if item.get("artifact_type") == "test_case_version"
        }
        new_requirements = set(changes.get("linked_requirement_version_ids", [])) - set(
            defect.get("linked_requirement_version_ids", [])
        )
        selected_test_case = changes.get("linked_test_case_version_id")
        if not new_requirements <= accepted_requirements or (
            selected_test_case
            and selected_test_case != defect.get("linked_test_case_version_id")
            and selected_test_case not in accepted_test_cases
        ):
            raise HTTPException(status_code=422, detail={"code": "AI_CANDIDATE_CHANGE_MISMATCH"})
    updated = await optimistic_patch(
        "defects", defect_id, project_id, payload.expected_revision, changes
    )
    if ai_result:
        timestamp = now()
        await defect_repository.review_ai_result(
            ai_result["_id"],
            project_id,
            {
                "review_status": "REVIEWED",
                "accepted_candidate_ids": list(dict.fromkeys(payload.accepted_candidate_ids)),
                "review_reason": payload.reason,
                "reviewed_by": user.id,
                "reviewed_at": timestamp,
                "updated_at": timestamp,
            },
        )
    await audit(
        user.id,
        "defect_trace_updated",
        "Defect",
        defect_id,
        project_id,
        {
            "reason": payload.reason,
            "changed_fields": sorted(changes),
            "ai_result_id": payload.ai_result_id,
            "accepted_candidate_ids": payload.accepted_candidate_ids,
        },
    )
    return updated
