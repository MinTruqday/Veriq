import hashlib
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project_entity, new_id, now, plain_text
from src.core.database import database
from src.repositories.test_run import test_run_repository
from src.repositories.execution_context import execution_context_repository
from src.modules.execution.services.execution_state import (
    execution_transitions,
    enforce_not_applicable_policy,
    frozen_run_scope,
    frozen_run_scope_hash,
    replay_resume_event,
    select_resume_execution,
)
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


def _verify_idempotency_replay(existing, payload, *, entity):
    if existing.get("request_hash") != _idempotency_fingerprint(payload):
        raise HTTPException(
            status_code=409,
            detail={"code": "IDEMPOTENCY_KEY_REUSED", "entity": entity},
        )





async def start_test_run_record(run_id, user):
    
    run = await get_project_entity(
        'test_runs', run_id, user, 'testrun.execute'
    )
    if run["status"] == 'IN_PROGRESS':
        return run
    if run["status"] not in ['DRAFT', 'READY']:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    if run.get("environment_id"):
        environment = await test_run_repository.find_environment(
            run["environment_id"], run["project_id"]
        )
        if environment and environment.get("availability") != 'AVAILABLE':
            raise HTTPException(
                status_code=409,
                detail={"code": 'TEST_ENVIRONMENT_UNAVAILABLE'},
            )
    scope = frozen_run_scope(run)
    scope_fingerprint = frozen_run_scope_hash(scope)
    timestamp = now()
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
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(user.id, 'test_run_started', 'TestRun', run_id, run["project_id"])
    return updated


async def resume_test_run_record(project_id, run_id, payload, user):
    
    run = await get_project_entity(
        'test_runs', run_id, user, 'testrun.execute'
    )
    if run["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    existing = await test_run_repository.find_resume_event(run_id, payload.idempotency_key)
    if existing:
        return await replay_resume_event(run, existing), run.get("revision", 1)
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
    try:
        await test_run_repository.insert_resume_event(event)
    except DuplicateKeyError:
        existing = await test_run_repository.find_resume_event(run_id, payload.idempotency_key)
        return await replay_resume_event(run, existing), run.get("revision", 1)
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
    )
    if not updated:
        await test_run_repository.delete_resume_event(event["_id"])
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await test_run_repository.set_resume_event_revision(event["_id"], updated["revision"])
    event["run_revision"] = updated["revision"]
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
    )
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
                "code": 'TEST_RUN_PAUSED_BY_ENVIRONMENT_INCIDENT',
                "incident_id": run.get("paused_by_environment_incident_id"),
            },
        )
    if test_case_version_id not in run["test_case_version_ids"]:
        raise HTTPException(status_code=422, detail={"code": 'TEST_NOT_IN_RUN_SNAPSHOT'})
    existing = await test_run_repository.find_result_for_case(run_id, test_case_version_id)
    if existing and existing.get("idempotency_key") == payload.idempotency_key:
        if not _stored_result_matches_request(existing, payload):
            raise HTTPException(
                status_code=409,
                detail={"code": "IDEMPOTENCY_KEY_REUSED", "entity": "TEST_RESULT"},
            )
        return existing
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
    release = None
    if run.get("release_id"):
        release = await execution_context_repository.find_release(
            run["project_id"], run["release_id"]
        )
    from src.clients.ai_automation import (
        emit_release_gate_recheck,
        emit_test_execution_recorded,
    )

    async with await database.client.start_session() as session:
        async with session.start_transaction():
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
            await test_run_repository.touch_run(run_id, None, now(), session=session)
            await audit(
                user.id,
                'test_result_recorded',
                'TestResult',
                result["_id"],
                run["project_id"],
                {"status": payload.status},
                session=session,
            )
            await emit_test_execution_recorded(result, user, session=session)
            if release and release.get("status") == "ACTIVE":
                await emit_release_gate_recheck(release, result, user, session=session)
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
        _verify_idempotency_replay(existing_event, payload, entity="TEST_EXECUTION_UPDATE")
        return {
            "execution": await test_run_repository.find_result(execution_id),
            "update": existing_event,
        }
    await enforce_not_applicable_policy(project_id, payload.status, payload.step_results)
    run = await test_run_repository.find_run(result["test_run_id"], project_id)
    if not run or run.get("status") != 'IN_PROGRESS':
        raise HTTPException(status_code=409, detail={"code": 'TEST_RUN_NOT_IN_PROGRESS'})
    if run.get("execution_paused"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'TEST_RUN_PAUSED_BY_ENVIRONMENT_INCIDENT',
                "incident_id": run.get("paused_by_environment_incident_id"),
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
    release = None
    if run.get("release_id"):
        release = await execution_context_repository.find_release(project_id, run["release_id"])
    from src.clients.ai_automation import emit_release_gate_recheck, emit_test_execution_recorded

    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
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
                await test_run_repository.touch_run(result["test_run_id"], project_id, now(), session=session)
                await audit(
                    user.id,
                    'test_execution_updated',
                    'TestExecution',
                    execution_id,
                    project_id,
                    {"status": payload.status},
                    session=session,
                )
                await emit_test_execution_recorded(updated, user, session=session)
                if release and release.get("status") == "ACTIVE":
                    await emit_release_gate_recheck(release, updated, user, session=session)
    except DuplicateKeyError:
        event = await test_run_repository.find_execution_update(
            execution_id, payload.idempotency_key
        )
        if not event:
            raise HTTPException(status_code=409, detail={"code": "EXECUTION_CONFLICT"})
        _verify_idempotency_replay(event, payload, entity="TEST_EXECUTION_UPDATE")
        return {
            "execution": await test_run_repository.find_result(execution_id),
            "update": event,
        }
    return {"execution": updated, "update": event}


async def correct_test_result_record(result_id, payload, user):
    
    result = await get_project_entity(
        'test_results', result_id, user, 'testresult.correct'
    )
    existing = await test_run_repository.find_correction(result_id, payload.idempotency_key)
    if existing:
        _verify_idempotency_replay(existing, payload, entity="TEST_RESULT_CORRECTION")
        return {
            "result": await test_run_repository.find_result(result_id),
            "correction": existing,
        }
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
    run = await test_run_repository.find_run(result.get("test_run_id"), result["project_id"])
    release = None
    if run and run.get("release_id"):
        release = await execution_context_repository.find_release(
            result["project_id"], run["release_id"]
        )
    from src.clients.ai_automation import emit_release_gate_recheck, emit_test_execution_recorded

    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await test_run_repository.insert_correction(event, session=session)
                corrected = await test_run_repository.update_result(
                    {"_id": result_id, "project_id": result["project_id"]},
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
                await audit(
                    user.id,
                    'test_result_corrected',
                    'TestResult',
                    result_id,
                    result["project_id"],
                    {"from": result.get("status"), "to": payload.status, "correction_id": event["_id"]},
                    session=session,
                )
                await emit_test_execution_recorded(corrected, user, session=session)
                if release and release.get("status") == "ACTIVE":
                    await emit_release_gate_recheck(release, corrected, user, session=session)
    except DuplicateKeyError:
        event = await test_run_repository.find_correction(result_id, payload.idempotency_key)
        if not event:
            raise HTTPException(status_code=409, detail={"code": "EXECUTION_CONFLICT"})
        _verify_idempotency_replay(event, payload, entity="TEST_RESULT_CORRECTION")
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
        'test_runs', run_id, user, 'testrun.execute'
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
    )
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
    )
    await audit(
        user.id,
        'test_run_aborted',
        'TestRun',
        run_id,
        run["project_id"],
        {"reason": reason},
    )
    return updated
