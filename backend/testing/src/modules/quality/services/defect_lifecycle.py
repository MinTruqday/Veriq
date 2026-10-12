from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    now,
    optimistic_patch,
    require_action_policy,
)
from src.repositories.defect import defect_repository
from src.modules.execution.services.execution_context import resolve_execution_context
from src.modules.execution.services.execution_state import defect_transitions





async def update_defect_record(defect_id, payload, project_id, user):
    payload = payload.model_dump(exclude_unset=True)
    defect = await get_project_entity(
        'defects',
        defect_id,
        user,
        'defect.update',
        assigned_role='DEVELOPER',
        assigned_user_field="assignee",
    )
    if project_id is not None and defect["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    expected_revision = payload.get("expected_revision")
    if not isinstance(expected_revision, int):
        raise HTTPException(status_code=422, detail={"code": 'EXPECTED_REVISION_REQUIRED'})
    if "assignee" in payload:
        await get_project(defect["project_id"], user, 'defect.assign')
    if any(
        field in payload
        for field in {
            "linked_test_result_id",
            "linked_test_case_version_id",
            "linked_requirement_version_ids",
        }
    ):
        await get_project(
            defect["project_id"],
            user,
            'defect.trace.manage',
            assigned_role='DEVELOPER',
            assigned_user_id=defect.get("assignee"),
        )
    if "attachments" in payload:
        await get_project(
            defect["project_id"],
            user,
            'attachment.manage',
            assigned_role='DEVELOPER',
            assigned_user_id=defect.get("assignee"),
        )
    if "linked_test_result_id" in payload and payload["linked_test_result_id"]:
        result = await defect_repository.find_test_result(
            payload["linked_test_result_id"], defect["project_id"]
        )
        if not result or result.get("status") != 'FAIL':
            raise HTTPException(status_code=422, detail={"code": 'DEFECT_REQUIRES_FAILED_RESULT'})
    if "linked_test_case_version_id" in payload and payload["linked_test_case_version_id"]:
        version = await defect_repository.find_test_case_version(
            payload["linked_test_case_version_id"], defect["project_id"]
        )
        if not version:
            raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_CASE_VERSION'})
    if "linked_requirement_version_ids" in payload:
        requirement_ids = list(dict.fromkeys(payload.get("linked_requirement_version_ids") or []))
        count = await defect_repository.count_requirement_versions(
            defect["project_id"], requirement_ids
        )
        if count != len(requirement_ids):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_REQUIREMENT_VERSION'})
    changes = {key: value for key, value in payload.items() if key in ['title',
 'description_doc',
 'steps_to_reproduce',
 'actual_result_doc',
 'expected_result_doc',
 'severity',
 'priority',
 'environment',
 'environment_id',
 'release',
 'release_id',
 'build',
 'build_id',
 'assignee',
 'attachments',
 'linked_test_result_id',
 'linked_test_case_version_id',
 'linked_requirement_version_ids',
 'root_cause_category',
 'root_cause_detail',
 'injected_phase',
 'detected_phase',
 'escape_reason',
 'prevention_candidate']}
    if {"release_id", "build_id", "environment_id", "release", "build", "environment"} & set(
        changes
    ):
        changes.update(
            await resolve_execution_context(
                defect["project_id"],
                user,
                release_id=changes.get("release_id", defect.get("release_id")),
                build_id=changes.get("build_id", defect.get("build_id")),
                environment_id=changes.get("environment_id", defect.get("environment_id")),
                release=changes.get("release", defect.get("release", "")),
                build=changes.get("build", defect.get("build", "")),
                environment=changes.get("environment", defect.get("environment", "")),
            )
        )
    updated = await optimistic_patch(
        'defects', defect_id, defect["project_id"], expected_revision, changes
    )
    await audit(user.id, 'defect_updated', 'Defect', defect_id, defect["project_id"])
    return updated


async def transition_defect_record(defect_id, payload, user):
    
    permission = {'CONFIRMED': 'defect.triage',
 'REJECTED': 'defect.triage',
 'DUPLICATE': 'defect.triage',
 'IN_PROGRESS': 'defect.transition.developer',
 'RESOLVED': 'defect.transition.developer',
 'READY_FOR_RETEST': 'defect.retest',
 'REOPENED': 'defect.retest',
 'CLOSED': 'defect.close'}.get(
        payload.to_status, 'defect.update'
    )
    defect = await get_project_entity(
        'defects',
        defect_id,
        user,
        permission,
        assigned_role='DEVELOPER'
        if permission == 'defect.transition.developer'
        else None,
        assigned_user_field="assignee"
        if permission == 'defect.transition.developer'
        else None,
    )
    if payload.to_status in ['REJECTED', 'DUPLICATE']:
        await require_action_policy(
            defect["project_id"],
            user,
            f"defect.{payload.to_status.lower()}",
            set(['QA']),
        )
    allowed = defect_transitions().get(defect["status"], set())
    if payload.to_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'INVALID_STATE_TRANSITION',
                "from": defect["status"],
                "to": payload.to_status,
            },
        )
    updated = await defect_repository.transition_defect(
        defect_id,
        defect["project_id"],
        defect["status"],
        payload.expected_revision,
        {
            "status": payload.to_status,
            "transition_reason": payload.reason,
            "transitioned_by": user.id,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'defect_transitioned',
        'Defect',
        defect_id,
        defect["project_id"],
        {"from": defect["status"], "to": payload.to_status, "reason": payload.reason},
    )
    return updated


async def retest_defect_record(project_id, defect_id, payload, user):
    
    defect = await get_project_entity('defects', defect_id, user, 'defect.retest')
    if defect["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    existing = await defect_repository.find_retest(defect_id, payload.idempotency_key)
    if existing:
        return {
            "defect": await defect_repository.find_defect(defect_id, project_id),
            "retest": existing,
        }
    if defect["status"] != 'READY_FOR_RETEST':
        raise HTTPException(
            status_code=409,
            detail={"code": 'DEFECT_NOT_READY_FOR_RETEST', "status": defect["status"]},
        )
    result = await defect_repository.find_test_result(payload.test_result_id, project_id)
    if not result:
        raise HTTPException(status_code=422, detail={"code": 'INVALID_RETEST_RESULT'})
    if result.get("status") not in ['PASS', 'FAIL']:
        raise HTTPException(status_code=422, detail={"code": 'RETEST_RESULT_MUST_PASS_OR_FAIL'})
    linked_version_id = defect.get("linked_test_case_version_id")
    if linked_version_id and result.get("test_case_version_id") != linked_version_id:
        raise HTTPException(status_code=422, detail={"code": 'RETEST_CASE_VERSION_MISMATCH'})
    target_status = {'PASS': 'CLOSED', 'FAIL': 'REOPENED'}[result["status"]]
    event = {
        "_id": new_id('DRT'),
        "project_id": project_id,
        "defect_id": defect_id,
        "test_result_id": result["_id"],
        "test_run_id": result["test_run_id"],
        "test_case_version_id": result["test_case_version_id"],
        "outcome": result["status"],
        "from_status": defect["status"],
        "to_status": target_status,
        "note": payload.note,
        "idempotency_key": payload.idempotency_key,
        "retested_by": user.id,
        "application_status": 'PENDING',
        "created_at": now(),
    }
    try:
        await defect_repository.insert_retest(event)
    except DuplicateKeyError:
        existing = await defect_repository.find_retest(defect_id, payload.idempotency_key)
        return {
            "defect": await defect_repository.find_defect(defect_id, project_id),
            "retest": existing,
        }
    updated = await defect_repository.apply_retest(
        defect_id,
        project_id,
        'READY_FOR_RETEST',
        payload.expected_revision,
        target_status,
        event["_id"],
        result["_id"],
        now(),
    )
    if not updated:
        await defect_repository.delete_retest(
            event["_id"], 'PENDING'
        )
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    event["application_status"] = 'APPLIED'
    await defect_repository.mark_retest_applied(
        event["_id"], 'APPLIED'
    )
    await audit(
        user.id,
        'defect_retested',
        'Defect',
        defect_id,
        project_id,
        {"test_result_id": result["_id"], "outcome": result["status"], "to": target_status},
    )
    return {"defect": updated, "retest": event}
