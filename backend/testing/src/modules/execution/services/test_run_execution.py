import hashlib
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.core.common import (
    audit,
    get_project_entity,
    new_id,
    now,
    plain_text,
)
from src.core.database import database
from src.repositories.test_run import test_run_repository
from src.repositories.project import project_repository
from src.repositories.defect import defect_repository
from src.repositories.execution_context import execution_context_repository
from src.modules.execution.services.execution_state import (
    execution_transitions,
    enforce_not_applicable_policy,
    frozen_run_scope,
    frozen_run_scope_hash,
    require_case_execution_assignment,
    replay_resume_event,
    select_resume_execution,
)
from src.modules.execution.services.test_period import register_period_activity
from src.modules.execution.services.test_plan import verified_approved_plan_snapshot
from src.clients.project_knowledge import index_artifact

def _idempotency_fingerprint(payload):
    request = payload.model_dump(
        mode="json", exclude={"idempotency_key", "expected_revision"}
    )
    canonical = json.dumps(
        request, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _stored_result_matches_request(result, payload):
    fingerprint = _idempotency_fingerprint(payload)
    if result.get("idempotency_request_hash"):
        return result["idempotency_request_hash"] == fingerprint
    persisted = {
        key: result.get(key)
        for key in ("status", "step_results", "actual_result_doc", "attachments", "note")
    }
    requested = payload.model_dump(
        mode="json", exclude={"idempotency_key", "expected_revision"}
    )
    return persisted == requested

def _verify_idempotency_replay(existing, payload, *, entity, actor_id, actor_field):
    if existing.get(actor_field) != actor_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH", "entity": entity},
        )
    request_hash = existing.get("request_hash")
    if request_hash and request_hash != _idempotency_fingerprint(payload):
        raise HTTPException(
            status_code=409,
            detail={"code": "IDEMPOTENCY_KEY_REUSED", "entity": entity},
        )
    if not request_hash:
        raise HTTPException(
            status_code=409,
            detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE", "entity": entity},
        )

def _verify_result_replay_actor(result, actor_id):
    executor_id = result.get("executed_by") or result.get("executor_id")
    if executor_id != actor_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH", "entity": "TEST_RESULT"},
        )

def _verify_resume_replay(existing, payload, actor_id):
    if existing.get("resumed_by") != actor_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH", "entity": "TEST_RUN_RESUME"},
        )
    recorded_revision = existing.get("expected_revision")
    if recorded_revision is None and existing.get("run_revision") is not None:
        recorded_revision = existing["run_revision"] - 1
    if recorded_revision is not None and recorded_revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": "IDEMPOTENCY_KEY_REUSED", "entity": "TEST_RUN_RESUME"},
        )


async def link_existing_defect_to_result(project_id, result_id, payload, user):
    result = await get_project_entity("test_results", result_id, user, "testrun.execute")
    defect = await get_project_entity("defects", payload.defect_id, user, "defect.read")
    if result.get("project_id") != project_id or defect.get("project_id") != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    await get_project(project_id, user, "defect.trace.manage")
    run = await test_run_repository.find_run(result.get("test_run_id"), project_id)
    if not run or result.get("test_case_version_id") not in run.get("test_case_version_ids", []):
        raise HTTPException(status_code=409, detail={"code": "TEST_NOT_IN_RUN_SNAPSHOT"})
    await require_case_execution_assignment(run, result["test_case_version_id"], user)
    if result.get("status") != "FAIL":
        raise HTTPException(status_code=409, detail={"code": "DEFECT_REQUIRES_FAILED_RESULT"})
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            current_defect = await database.value.defects.find_one(
                {"_id": payload.defect_id, "project_id": project_id}, session=session
            )
            if not current_defect:
                raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
            current_result = await defect_repository.find_test_result(
                result_id, project_id, session=session
            )
            if (
                not current_result
                or current_result.get("status") != "FAIL"
                or current_result.get("test_run_id") != run["_id"]
                or current_result.get("test_case_version_id")
                != result.get("test_case_version_id")
            ):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "DEFECT_TEST_RESULT_CONTEXT_CHANGED"},
                )
            already_linked = payload.defect_id in current_result.get(
                "linked_defect_ids", []
            )
            linked_case_version_id = current_defect.get(
                "linked_test_case_version_id"
            )
            linked_source_result_id = current_defect.get("linked_test_result_id")
            if linked_case_version_id and linked_case_version_id != result.get(
                "test_case_version_id"
            ):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "DEFECT_TEST_CASE_CONTEXT_MISMATCH"},
                )
            if linked_source_result_id:
                source_result = await defect_repository.find_test_result(
                    linked_source_result_id, project_id, session=session
                )
                if (
                    not source_result
                    or source_result.get("test_case_version_id")
                    != result.get("test_case_version_id")
                ):
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "DEFECT_TEST_CASE_CONTEXT_MISMATCH"},
                    )
            updated = current_result if already_linked else await defect_repository.link_failed_result_to_defect(
                result_id, project_id, payload.expected_revision, run["_id"],
                result["test_case_version_id"], payload.defect_id, now(), session,
            )
            if not updated:
                raise HTTPException(status_code=409, detail={"code": "DEFECT_TEST_RESULT_CONTEXT_CHANGED"})
            source_changes = {}
            if not linked_case_version_id:
                source_changes["linked_test_case_version_id"] = result[
                    "test_case_version_id"
                ]
            if not linked_source_result_id:
                source_changes["linked_test_result_id"] = result_id
            if source_changes:
                linked_defect = await defect_repository.set_retest_source(
                    payload.defect_id,
                    project_id,
                    current_defect.get("revision", 1),
                    source_changes,
                    now(),
                    session=session,
                )
                if not linked_defect:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "DEFECT_TEST_RESULT_CONTEXT_CHANGED"},
                    )
            if not already_linked:
                await test_run_repository.touch_run(
                    run["_id"], project_id, now(), session=session
                )
            await audit(user.id, "test_result_defect_linked", "TestResult", result_id, project_id,
                        {"defect_id": payload.defect_id}, session=session)
    return updated

async def start_test_run_record(run_id, user):
    
    run = await get_project_entity(
        'test_runs', run_id, user, 'testrun.start'
    )
    if run["status"] == 'IN_PROGRESS':
        return run
    if run["status"] not in ['DRAFT', 'READY']:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    if not run.get("test_case_version_ids"):
        raise HTTPException(
            status_code=409,
            detail={"code": "TEST_RUN_SCOPE_EMPTY"},
        )
    case_assignments = run.get("test_case_assignments") or {}
    unassigned_versions = [
        version_id
        for version_id in run["test_case_version_ids"]
        if not case_assignments.get(version_id) and not run.get("assignee_id")
    ]
    if unassigned_versions:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TEST_RUN_ASSIGNMENTS_REQUIRED",
                "unassigned_count": len(unassigned_versions),
            },
        )
    assigned_users = set(case_assignments.values())
    if run.get("assignee_id"):
        assigned_users.add(run["assignee_id"])
    active_assignees = await project_repository.list_active_members_with_permission(
        run["project_id"], "testrun.execute", assigned_users
    )
    active_assignee_ids = {item.get("user_id") for item in active_assignees}
    inactive_assignees = assigned_users - active_assignee_ids
    if inactive_assignees:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TEST_RUN_ASSIGNEE_UNAVAILABLE",
                "user_ids": sorted(inactive_assignees),
            },
        )
    if not run.get("test_plan_id"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TEST_RUN_PLAN_REQUIRED",
                "message": "Liên kết Test Run với kế hoạch đã duyệt trước khi bắt đầu.",
            },
        )
    plan = await test_run_repository.find_plan(run["test_plan_id"], run["project_id"])
    snapshot, snapshot_hash = verified_approved_plan_snapshot(plan, run["project_id"])
    if run.get("test_plan_snapshot_hash") != snapshot_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TEST_RUN_PLAN_SNAPSHOT_CHANGED",
                "message": "Kế hoạch liên kết đã thay đổi. Tạo lại Test Run từ phiên bản kế hoạch đã duyệt.",
            },
        )
    approved_cases = set(snapshot.get("test_case_version_ids") or [])
    if not set(run.get("test_case_version_ids") or []).issubset(approved_cases):
        raise HTTPException(
            status_code=409,
            detail={"code": "TEST_RUN_OUTSIDE_PLAN_SCOPE"},
        )
    if run.get("environment_id"):
        environment = await test_run_repository.find_environment(
            run["environment_id"], run["project_id"]
        )
        if not environment:
            raise HTTPException(
                status_code=409,
                detail={"code": "TEST_ENVIRONMENT_NOT_FOUND"},
            )
        if environment.get("status") == "ARCHIVED":
            raise HTTPException(
                status_code=409,
                detail={"code": "TEST_ENVIRONMENT_ARCHIVED"},
            )
        if environment.get("availability", "AVAILABLE") != 'AVAILABLE':
            raise HTTPException(
                status_code=409,
                detail={"code": 'TEST_ENVIRONMENT_UNAVAILABLE'},
            )
    scope = frozen_run_scope(run)
    scope_fingerprint = frozen_run_scope_hash(scope)
    timestamp = now()
    async def persist_start(session):
        updated = await test_run_repository.transition_run(
            {"_id": run_id, "status": run["status"], "revision": run.get("revision", 1)},
            {
                "status": 'IN_PROGRESS',
                "frozen_scope": scope,
                "frozen_scope_hash": scope_fingerprint,
                "started_at": timestamp,
                "started_by": user.id,
                "updated_at": timestamp,
            },
            session=session,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
        await audit(
            user.id,
            'test_run_started',
            'TestRun',
            run_id,
            run["project_id"],
            session=session,
        )
        return updated

    async with await database.client.start_session() as session:
        updated = await session.with_transaction(persist_start)
    return updated

async def resume_test_run_record(project_id, run_id, payload, user):
    
    run = await get_project_entity(
        'test_runs', run_id, user, 'testrun.execute'
    )
    if run["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    existing = await test_run_repository.find_resume_event(run_id, payload.idempotency_key)
    if existing:
        _verify_resume_replay(existing, payload, user.id)
        current_run = await test_run_repository.find_run(run_id, project_id)
        if not current_run:
            raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
        return await replay_resume_event(current_run, existing), current_run.get("revision", 1)
    if run.get("status") != 'IN_PROGRESS':
        raise HTTPException(status_code=409, detail={"code": 'TEST_RUN_NOT_IN_PROGRESS'})
    if run.get("revision", 1) != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_revision": run.get("revision", 1),
            },
        )
    scope = frozen_run_scope(run)
    scope_fingerprint = frozen_run_scope_hash(scope)
    if run.get("frozen_scope_hash") and run["frozen_scope_hash"] != scope_fingerprint:
        raise HTTPException(status_code=409, detail={"code": 'TEST_RUN_SCOPE_CHANGED'})
    selected = await select_resume_execution(run, user)
    timestamp = now()
    event = {
        "_id": new_id('RSM'),
        "project_id": project_id,
        "test_run_id": run_id,
        "idempotency_key": payload.idempotency_key,
        "expected_revision": payload.expected_revision,
        "scope_fingerprint": scope_fingerprint,
        "current_execution_id": (
            selected["current_execution"]["_id"] if selected["current_execution"] else None
        ),
        "current_test_case_version_id": (
            selected["current_test_case_version"]["_id"]
            if selected["current_test_case_version"]
            else None
        ),
        "position": selected["position"],
        "total_count": selected["total_count"],
        "remaining_count": selected["remaining_count"],
        "assignment_mode": selected["assignment_mode"],
        "resumed_by": user.id,
        "created_at": timestamp,
    }

    async def persist_resume(session):
        event["run_revision"] = payload.expected_revision + 1
        await test_run_repository.insert_resume_event(event, session=session)
        updated = await test_run_repository.transition_run(
            {
                "_id": run_id,
                "project_id": project_id,
                "status": 'IN_PROGRESS',
                "revision": payload.expected_revision,
            },
            {
                "frozen_scope": run.get("frozen_scope") or scope,
                "frozen_scope_hash": scope_fingerprint,
                "last_resumed_at": timestamp,
                "last_resumed_by": user.id,
                "last_resume_event_id": event["_id"],
                "updated_at": timestamp,
            },
            session=session,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
        await audit(
            user.id,
            'test_run_resumed',
            'TestRun',
            run_id,
            project_id,
            {
                "resume_event_id": event["_id"],
                "current_test_case_version_id": event["current_test_case_version_id"],
                "scope_fingerprint": scope_fingerprint,
            },
            session=session,
        )
        return updated

    try:
        async with await database.client.start_session() as session:
            updated = await session.with_transaction(persist_resume)
    except DuplicateKeyError:
        existing = await test_run_repository.find_resume_event(run_id, payload.idempotency_key)
        if not existing:
            raise
        _verify_resume_replay(existing, payload, user.id)
        current_run = await test_run_repository.find_run(run_id, project_id)
        if not current_run:
            raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
        return await replay_resume_event(current_run, existing), current_run.get("revision", 1)
    return (
        {"run": updated, "resume_event": event, **selected, "scope_fingerprint": scope_fingerprint},
        updated["revision"],
    )

async def record_test_result_entry(run_id, test_case_version_id, payload, user):
    
    run = await get_project_entity(
        'test_runs', run_id, user, 'testrun.execute'
    )
    if run["status"] != 'IN_PROGRESS':
        raise HTTPException(status_code=409, detail={"code": 'TEST_RUN_NOT_IN_PROGRESS'})
    if run.get("execution_paused"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'TEST_RUN_PAUSED',
            },
        )
    if test_case_version_id not in run["test_case_version_ids"]:
        raise HTTPException(status_code=422, detail={"code": 'TEST_NOT_IN_RUN_SNAPSHOT'})
    await require_case_execution_assignment(run, test_case_version_id, user)
    existing = await test_run_repository.find_result_for_case(run_id, test_case_version_id)
    if existing and existing.get("idempotency_key") == payload.idempotency_key:
        _verify_result_replay_actor(existing, user.id)
        if not _stored_result_matches_request(existing, payload):
            raise HTTPException(
                status_code=409,
                detail={"code": "IDEMPOTENCY_KEY_REUSED", "entity": "TEST_RESULT"},
            )
        return existing
    if payload.status == "FAIL" and not plain_text(payload.actual_result_doc).strip():
        raise HTTPException(status_code=422, detail={"code": "FAIL_ACTUAL_RESULT_REQUIRED", "message": "Nhập kết quả thực tế khi ca kiểm thử thất bại."})
    await enforce_not_applicable_policy(run["project_id"], payload.status, payload.step_results)
    if existing:
        if existing.get("status") != 'NOT_RUN':
            raise HTTPException(status_code=409, detail={"code": 'RESULT_ALREADY_RECORDED'})
        timestamp = now()
    else:
        timestamp = now()
        result = {
            "_id": new_id('TRES'),
            "project_id": run["project_id"],
            "test_run_id": run_id,
            "test_case_version_id": test_case_version_id,
            "environment": run.get("environment"),
            "build": run.get("build"),
            **payload.model_dump(),
            "idempotency_request_hash": _idempotency_fingerprint(payload),
            "revision": 1,
            "executor_id": user.id,
            "executed_by": user.id,
            "started_at": timestamp,
            "completed_at": timestamp,
            "executed_at": timestamp,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    async def persist_result(session):
        nonlocal result
        current_run = await test_run_repository.find_run(
            run_id, run["project_id"], session=session
        )
        if not current_run or current_run.get("status") != "IN_PROGRESS":
            raise HTTPException(
                status_code=409, detail={"code": "TEST_RUN_NOT_IN_PROGRESS"}
            )
        if current_run.get("execution_paused"):
            raise HTTPException(status_code=409, detail={"code": "TEST_RUN_PAUSED"})
        if test_case_version_id not in current_run.get("test_case_version_ids", []):
            raise HTTPException(
                status_code=409, detail={"code": "TEST_NOT_IN_RUN_SNAPSHOT"}
            )
        await require_case_execution_assignment(
            current_run, test_case_version_id, user
        )
        if existing:
            result = await test_run_repository.update_result(
                {
                    "_id": existing["_id"],
                    "project_id": run["project_id"],
                    "status": 'NOT_RUN',
                    "revision": existing.get("revision", 1),
                },
                {
                    **payload.model_dump(),
                    "idempotency_request_hash": _idempotency_fingerprint(payload),
                    "executor_id": user.id,
                    "executed_by": user.id,
                    "started_at": existing.get("started_at") or timestamp,
                    "completed_at": timestamp,
                    "executed_at": timestamp,
                    "updated_at": timestamp,
                },
                session=session,
            )
            if not result:
                raise HTTPException(status_code=409, detail={"code": 'EXECUTION_CONFLICT'})
        else:
            await test_run_repository.insert_result(result, session=session)
        run_touched = await test_run_repository.touch_run(
            run_id,
            run["project_id"],
            now(),
            session=session,
            expected_status="IN_PROGRESS",
            require_unpaused=True,
        )
        if not run_touched:
            raise HTTPException(
                status_code=409, detail={"code": "TEST_RUN_NOT_IN_PROGRESS"}
            )
        await audit(
            user.id,
            'test_result_recorded',
            'TestResult',
            result["_id"],
            run["project_id"],
            {"status": payload.status},
            session=session,
        )
        return result

    try:
        async with await database.client.start_session() as session:
            result = await session.with_transaction(persist_result)
    except PyMongoError as error:
        if not isinstance(error, DuplicateKeyError) and not error.has_error_label(
            "TransientTransactionError"
        ):
            raise
        concurrent_result = await test_run_repository.find_result_for_case(
            run_id, test_case_version_id
        )
        if not concurrent_result:
            current_run = await test_run_repository.find_run(run_id, run["project_id"])
            if not current_run or current_run.get("status") != "IN_PROGRESS":
                raise HTTPException(
                    status_code=409,
                    detail={"code": "TEST_RUN_NOT_IN_PROGRESS"},
                ) from error
            raise HTTPException(
                status_code=409, detail={"code": "EXECUTION_CONFLICT"}
            ) from error
        if concurrent_result.get("idempotency_key") == payload.idempotency_key:
            _verify_result_replay_actor(concurrent_result, user.id)
            if not _stored_result_matches_request(concurrent_result, payload):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "IDEMPOTENCY_KEY_REUSED", "entity": "TEST_RESULT"},
                )
            return concurrent_result
        if concurrent_result.get("status") != "NOT_RUN":
            raise HTTPException(status_code=409, detail={"code": 'RESULT_ALREADY_RECORDED'})
        raise HTTPException(status_code=409, detail={"code": 'EXECUTION_CONFLICT'})
    await index_artifact(
        run["project_id"],
        'test_result',
        result["_id"],
        result["_id"],
        result["_id"],
        " ".join(
            [
                str(result.get("status") or ""),
                plain_text(result.get("actual_result_doc", {})),
                str(result.get("note") or ""),
            ]
        ),
        result["status"],
        'PROJECT_REFERENCE',
        result.get("revision", 1),
        test_run_id=run_id,
        test_case_version_id=test_case_version_id,
    )
    return result

async def update_test_execution_record(project_id, execution_id, payload, user):
    
    result = await get_project_entity(
        'test_results', execution_id, user, 'testrun.execute'
    )
    if result["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    existing_event = await test_run_repository.find_execution_update(
        execution_id, payload.idempotency_key
    )
    if existing_event:
        _verify_idempotency_replay(
            existing_event,
            payload,
            entity="TEST_EXECUTION_UPDATE",
            actor_id=user.id,
            actor_field="updated_by",
        )
        return {
            "execution": await test_run_repository.find_result(execution_id),
            "update": existing_event,
        }
    if payload.status == "FAIL" and not plain_text(payload.actual_result_doc).strip():
        raise HTTPException(status_code=422, detail={"code": "FAIL_ACTUAL_RESULT_REQUIRED", "message": "Nhập kết quả thực tế khi ca kiểm thử thất bại."})
    await enforce_not_applicable_policy(project_id, payload.status, payload.step_results)
    run = await test_run_repository.find_run(result["test_run_id"], project_id)
    if not run or run.get("status") != 'IN_PROGRESS':
        raise HTTPException(status_code=409, detail={"code": 'TEST_RUN_NOT_IN_PROGRESS'})
    await require_case_execution_assignment(run, result["test_case_version_id"], user)
    executor_id = result.get("executed_by") or result.get("executor_id")
    if executor_id and executor_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"code": 'TEST_RESULT_EXECUTOR_MISMATCH'},
        )
    if run.get("execution_paused"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'TEST_RUN_PAUSED',
            },
        )
    allowed = execution_transitions().get(result.get("status"), set())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'INVALID_EXECUTION_TRANSITION',
                "from": result.get("status"),
                "to": payload.status,
            },
        )
    expected_revision = payload.expected_revision or result.get("revision", 1)
    timestamp = now()
    terminal = payload.status in ['PASS', 'FAIL', 'BLOCKED', 'SKIPPED', 'NOT_APPLICABLE']
    event = {
        "_id": new_id('TEU'),
        "project_id": project_id,
        "test_result_id": execution_id,
        "from_status": result.get("status"),
        "to_status": payload.status,
        "idempotency_key": payload.idempotency_key,
        "request_hash": _idempotency_fingerprint(payload),
        "updated_by": user.id,
        "created_at": now(),
    }
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                current_run = await test_run_repository.find_run(
                    result["test_run_id"], project_id, session=session
                )
                if not current_run or current_run.get("status") != "IN_PROGRESS":
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "TEST_RUN_NOT_IN_PROGRESS"},
                    )
                if current_run.get("execution_paused"):
                    raise HTTPException(
                        status_code=409, detail={"code": "TEST_RUN_PAUSED"}
                    )
                if result["test_case_version_id"] not in current_run.get(
                    "test_case_version_ids", []
                ):
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "TEST_NOT_IN_RUN_SNAPSHOT"},
                    )
                await require_case_execution_assignment(
                    current_run, result["test_case_version_id"], user
                )
                updated = await test_run_repository.update_result(
                    {"_id": execution_id, "project_id": project_id, "revision": expected_revision},
                    {
                        "status": payload.status,
                        "step_results": [item.model_dump() for item in payload.step_results],
                        "actual_result_doc": payload.actual_result_doc,
                        "attachments": payload.attachments,
                        "note": payload.note,
                        "executor_id": user.id,
                        "executed_by": user.id,
                        "started_at": result.get("started_at") or timestamp,
                        "completed_at": timestamp if terminal else None,
                        "executed_at": timestamp if terminal else result.get("executed_at"),
                        "updated_at": timestamp,
                        "last_updated_by": user.id,
                    },
                    session=session,
                )
                if not updated:
                    raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
                await test_run_repository.insert_execution_update(event, session=session)
                run_touched = await test_run_repository.touch_run(
                    result["test_run_id"],
                    project_id,
                    now(),
                    session=session,
                    expected_status="IN_PROGRESS",
                    require_unpaused=True,
                )
                if not run_touched:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "TEST_RUN_NOT_IN_PROGRESS"},
                    )
                await audit(
                    user.id,
                    'test_execution_updated',
                    'TestExecution',
                    execution_id,
                    project_id,
                    {"status": payload.status},
                    session=session,
                )
    except DuplicateKeyError:
        event = await test_run_repository.find_execution_update(
            execution_id, payload.idempotency_key
        )
        if not event:
            raise HTTPException(status_code=409, detail={"code": "EXECUTION_CONFLICT"})
        _verify_idempotency_replay(
            event,
            payload,
            entity="TEST_EXECUTION_UPDATE",
            actor_id=user.id,
            actor_field="updated_by",
        )
        return {
            "execution": await test_run_repository.find_result(execution_id),
            "update": event,
        }
    except PyMongoError as error:
        if not (
            error.has_error_label("TransientTransactionError")
            or getattr(error, "code", None) == 112
        ):
            raise
        current_run = await test_run_repository.find_run(
            result["test_run_id"], project_id
        )
        if not current_run or current_run.get("status") != "IN_PROGRESS":
            raise HTTPException(
                status_code=409,
                detail={"code": "TEST_RUN_NOT_IN_PROGRESS"},
            ) from error
        raise HTTPException(
            status_code=409, detail={"code": "EXECUTION_CONFLICT"}
        ) from error
    return {"execution": updated, "update": event}

async def correct_test_result_record(result_id, payload, user):
    
    result = await get_project_entity(
        'test_results', result_id, user, 'testresult.correct'
    )
    run = await test_run_repository.find_run(result.get("test_run_id"), result["project_id"])
    if not run:
        raise HTTPException(status_code=404, detail={"code": "TEST_RUN_NOT_FOUND"})
    await require_case_execution_assignment(run, result.get("test_case_version_id"), user)
    existing = await test_run_repository.find_correction(result_id, payload.idempotency_key)
    if existing:
        _verify_idempotency_replay(
            existing,
            payload,
            entity="TEST_RESULT_CORRECTION",
            actor_id=user.id,
            actor_field="corrected_by",
        )
        return {
            "result": await test_run_repository.find_result(result_id),
            "correction": existing,
        }
    if payload.status == "FAIL" and not plain_text(result.get("actual_result_doc")).strip():
        raise HTTPException(
            status_code=422,
            detail={
                "code": "FAIL_ACTUAL_RESULT_REQUIRED",
                "message": "Nhập kết quả thực tế khi ca kiểm thử thất bại.",
            },
        )
    await enforce_not_applicable_policy(result["project_id"], payload.status)
    event = {
        "_id": new_id('TRC'),
        "project_id": result["project_id"],
        "test_result_id": result_id,
        "from_status": result.get("status"),
        "to_status": payload.status,
        "reason": payload.reason,
        "idempotency_key": payload.idempotency_key,
        "request_hash": _idempotency_fingerprint(payload),
        "corrected_by": user.id,
        "created_at": now(),
    }
    timestamp = now()
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await test_run_repository.insert_correction(event, session=session)
                corrected = await test_run_repository.update_result(
                    {
                        "_id": result_id,
                        "project_id": result["project_id"],
                        "revision": result.get("revision", 1),
                    },
                    {
                        "status": payload.status,
                        "corrected": True,
                        "last_correction_id": event["_id"],
                        "completed_at": timestamp,
                        "updated_at": timestamp,
                    },
                    {"correction_event_ids": event["_id"]},
                    session=session,
                )
                if not corrected:
                    raise HTTPException(status_code=409, detail={"code": 'EXECUTION_CONFLICT'})
                if run.get("test_period_id"):
                    await register_period_activity(
                        result["project_id"], run["test_period_id"], session
                    )
                await audit(
                    user.id,
                    'test_result_corrected',
                    'TestResult',
                    result_id,
                    result["project_id"],
                    {"from": result.get("status"), "to": payload.status, "correction_id": event["_id"]},
                    session=session,
                )
    except DuplicateKeyError:
        event = await test_run_repository.find_correction(result_id, payload.idempotency_key)
        if not event:
            raise HTTPException(status_code=409, detail={"code": "EXECUTION_CONFLICT"})
        _verify_idempotency_replay(
            event,
            payload,
            entity="TEST_RESULT_CORRECTION",
            actor_id=user.id,
            actor_field="corrected_by",
        )
        return {
            "result": await test_run_repository.find_result(result_id),
            "correction": event,
        }
    return {
        "result": corrected,
        "correction": event,
    }

async def complete_test_run_record(run_id, user):
    
    run = await get_project_entity(
        'test_runs', run_id, user, 'testrun.complete'
    )
    if run["status"] == 'COMPLETED':
        return run
    if run["status"] != 'IN_PROGRESS':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    result_count = await test_run_repository.count_results_by_status(
        run_id, ['PASS', 'FAIL', 'BLOCKED', 'SKIPPED', 'NOT_APPLICABLE']
    )
    total_count = len(run["test_case_version_ids"])
    project = await test_run_repository.project_settings(run["project_id"])
    partial_allowed = bool(
        (project.get("settings") or {}).get(
            'partial_complete_allowed', False
        )
    )
    if result_count < total_count and not partial_allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'PARTIAL_EXECUTION',
                "completed": result_count,
                "total": total_count,
            },
        )
    partial_completion = result_count < total_count
    timestamp = now()
    updated = await test_run_repository.update_run(
        run_id,
        {
            "status": 'COMPLETED',
            "completed_at": timestamp,
            "completed_by": user.id,
            "completed_result_count": result_count,
            "total_result_count": total_count,
            "partial_completion": partial_completion,
            "updated_at": timestamp,
        },
        expected_revision=run.get("revision", 1),
        expected_status="IN_PROGRESS",
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        'test_run_completed',
        'TestRun',
        run_id,
        run["project_id"],
        {"completed": result_count, "total": total_count, "partial_completion": partial_completion},
    )
    return updated

async def abort_test_run_record(run_id, reason, user):
    
    run = await get_project_entity(
        'test_runs', run_id, user, 'testrun.abort'
    )
    if run["status"] not in ['DRAFT', 'READY', 'IN_PROGRESS']:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    timestamp = now()
    updated = await test_run_repository.update_run(
        run_id,
        {
            "status": 'ABORTED',
            "abort_reason": reason,
            "aborted_by": user.id,
            "aborted_at": timestamp,
            "updated_at": timestamp,
        },
        expected_revision=run.get("revision", 1),
        expected_status=run.get("status"),
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        'test_run_aborted',
        'TestRun',
        run_id,
        run["project_id"],
        {"reason": reason},
    )
    return updated
