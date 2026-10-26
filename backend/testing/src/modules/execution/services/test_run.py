from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    now,
    optimistic_patch,
)
from src.core.database import database
from src.repositories.test_run import test_run_repository
from src.repositories.project import project_repository
from src.modules.projects.services.skill_profiles import automatically_assign_test_cases
from src.repositories.skill_profile import skill_profile_repository
from src.modules.execution.services.execution_context import resolve_execution_context
from src.modules.execution.services.execution_state import validate_test_versions
from src.modules.execution.services.test_plan import verified_approved_plan_snapshot
from src.clients.project_knowledge import index_artifact
from src.modules.execution.services.test_run_execution import (
    abort_test_run_record,
    complete_test_run_record,
    correct_test_result_record,
    record_test_result_entry,
    resume_test_run_record,
    start_test_run_record,
    update_test_execution_record,
)
from src.modules.execution.services.test_run_query import (
    build_test_run_report,
    get_test_run_record,
    get_test_result_record,
    list_test_result_records,
    list_test_run_records,
)




__all__ = [
    "abort_test_run_record",
    "build_test_run_report",
    "complete_test_run_record",
    "correct_test_result_record",
    "get_test_run_record",
    "get_test_result_record",
    "list_test_result_records",
    "list_test_run_records",
    "record_test_result_entry",
    "resume_test_run_record",
    "rerun_test_run_record",
    "start_test_run_record",
    "update_test_execution_record",
]


def _idempotent_run_matches(existing, payload, version_ids, context):
    existing_suite_ids = list(dict.fromkeys(existing.get("test_suite_ids", [])))
    expected = {
        "name": payload.name,
        "test_plan_id": payload.test_plan_id,
        "test_suite_ids": list(dict.fromkeys(payload.test_suite_ids)),
        "test_case_version_ids": version_ids,
        "assignment_strategy": payload.assignment_strategy,
        "release_id": context.get("release_id"),
        "build_id": context.get("build_id"),
        "environment_id": context.get("environment_id"),
    }
    expected_suite_ids = expected.pop("test_suite_ids")
    return existing_suite_ids == expected_suite_ids and all(
        existing.get(key, "MANUAL" if key == "assignment_strategy" else None) == value
        for key, value in expected.items()
    )


def _pin_run_to_plan(run, snapshot, snapshot_hash):
    run["test_plan_snapshot_hash"] = snapshot_hash
    run["requirement_version_ids"] = list(snapshot.get("requirement_version_ids", []))
    if snapshot.get("device_matrix_id"):
        run.update(
            {
                "device_matrix_id": snapshot["device_matrix_id"],
                "device_profile_keys": list(snapshot.get("device_profile_keys", [])),
                "device_matrix_snapshot": snapshot.get("device_matrix_snapshot"),
            }
        )
    return run


def _validate_plan_suite_scope(suite_ids, snapshot):
    selected = set(suite_ids or [])
    approved = set(snapshot.get("test_suite_ids", []))
    if not selected.issubset(approved):
        raise HTTPException(
            status_code=422,
            detail={"code": "TEST_RUN_SUITE_OUTSIDE_PLAN_SCOPE"},
        )


def _plan_suite_versions(suite_ids, snapshot):
    records = snapshot.get("test_suite_snapshots")
    if not isinstance(records, list):
        raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_SUITE_SNAPSHOT_INVALID"})
    by_id = {}
    for item in records:
        if not isinstance(item, dict):
            raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_SUITE_SNAPSHOT_INVALID"})
        suite_id = str(item.get("test_suite_id") or "")
        version_ids = item.get("test_case_version_ids")
        if (
            not suite_id
            or suite_id in by_id
            or not isinstance(item.get("revision"), int)
            or isinstance(item.get("revision"), bool)
            or item["revision"] < 1
            or not isinstance(version_ids, list)
            or any(not isinstance(value, str) or not value for value in version_ids)
            or len(version_ids) != len(set(version_ids))
        ):
            raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_SUITE_SNAPSHOT_INVALID"})
        by_id[suite_id] = item
    selected = [str(value) for value in suite_ids or []]
    if any(suite_id not in by_id for suite_id in selected):
        raise HTTPException(status_code=422, detail={"code": "TEST_RUN_SUITE_OUTSIDE_PLAN_SCOPE"})
    return list(
        dict.fromkeys(
            version_id
            for suite_id in selected
            for version_id in by_id[suite_id]["test_case_version_ids"]
        )
    )


async def create_test_run_record(payload, project_id, user):
    
    if project_id is not None and payload.project_id != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    await get_project(payload.project_id, user, 'testrun.create')
    plan = None
    approved_snapshot = None
    approved_snapshot_hash = None
    if payload.test_plan_id:
        plan = await test_run_repository.find_plan(payload.test_plan_id, payload.project_id)
        if not plan:
            raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_PLAN'})
        if plan.get("status") != "APPROVED":
            raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_NOT_APPROVED"})
        approved_snapshot, approved_snapshot_hash = verified_approved_plan_snapshot(
            plan, payload.project_id
        )
    context = await resolve_execution_context(
        payload.project_id,
        user,
        release_id=payload.release_id,
        build_id=payload.build_id,
        environment_id=payload.environment_id,
        release=payload.release,
        build=payload.build,
        environment=payload.environment,
    )
    version_ids = list(dict.fromkeys(payload.test_case_version_ids))
    if payload.test_suite_ids:
        if plan and "test_suite_snapshots" in approved_snapshot:
            version_ids.extend(
                _plan_suite_versions(payload.test_suite_ids, approved_snapshot)
            )
        else:
            suites = await test_run_repository.list_suites(
                payload.project_id, payload.test_suite_ids, 500
            )
            if len(suites) != len(set(payload.test_suite_ids)):
                raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_SUITE'})
            for suite in suites:
                version_ids.extend(suite.get("test_case_version_ids", []))
        version_ids = list(dict.fromkeys(version_ids))
    if plan:
        _validate_plan_suite_scope(payload.test_suite_ids, approved_snapshot)
        approved_scope = set(approved_snapshot.get("test_case_version_ids", []))
        if not approved_scope:
            raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_SCOPE_EMPTY"})
        if not version_ids:
            version_ids = list(approved_scope)
        if not set(version_ids).issubset(approved_scope):
            raise HTTPException(status_code=422, detail={"code": "TEST_RUN_OUTSIDE_PLAN_SCOPE"})
        for field in ("release_id", "build_id", "environment_id"):
            planned_value = approved_snapshot.get(field)
            run_value = context.get(field)
            if planned_value and run_value != planned_value:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "TEST_RUN_CONTEXT_OUTSIDE_PLAN_SCOPE", "field": field},
                )
    await validate_test_versions(payload.project_id, version_ids)
    if payload.idempotency_key:
        existing = await test_run_repository.find_run_by_idempotency_key(
            payload.project_id, payload.idempotency_key
        )
        if existing:
            if not _idempotent_run_matches(existing, payload, version_ids, context):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            return existing
    timestamp = now()
    device_scope = {}
    if approved_snapshot:
        device_scope = {
            "device_matrix_id": approved_snapshot.get("device_matrix_id"),
            "device_profile_keys": approved_snapshot.get("device_profile_keys", []),
            "device_matrix_snapshot": approved_snapshot.get("device_matrix_snapshot"),
        }
        if not device_scope["device_matrix_id"]:
            device_scope = {}
    test_case_assignments = {}
    unassigned_reasons = []
    assignment_decisions = {}
    run = {
        "_id": new_id('TRUN'),
        **payload.model_dump(),
        "test_suite_ids": list(dict.fromkeys(payload.test_suite_ids)),
        **context,
        **device_scope,
        "test_case_version_ids": version_ids,
        "test_case_assignments": test_case_assignments,
        "test_case_assignment_decisions": assignment_decisions,
        "unassigned_assignment_reasons": unassigned_reasons,
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    if plan:
        _pin_run_to_plan(run, approved_snapshot, approved_snapshot_hash)
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                if payload.test_plan_id:
                    current_plan = await test_run_repository.find_plan(
                        payload.test_plan_id, payload.project_id, session=session
                    )
                    current_snapshot, current_snapshot_hash = verified_approved_plan_snapshot(
                        current_plan, payload.project_id
                    )
                    if current_snapshot_hash != approved_snapshot_hash:
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "TEST_PLAN_APPROVED_SNAPSHOT_CHANGED"},
                        )
                    approved_snapshot = current_snapshot
                    _pin_run_to_plan(run, current_snapshot, current_snapshot_hash)
                if payload.assignment_strategy == "CONFIRMED_SKILLS" and version_ids:
                    versions = await test_run_repository.list_versions(
                        version_ids, len(version_ids), session=session
                    )
                    (
                        test_case_assignments,
                        unassigned_reasons,
                        assignment_decisions,
                    ) = await automatically_assign_test_cases(
                        payload.project_id, versions, session=session
                    )
                    stale_members = await project_repository.fence_active_testers(
                        payload.project_id,
                        test_case_assignments.values(),
                        session=session,
                    )
                    if stale_members:
                        raise HTTPException(
                            status_code=409,
                            detail={
                                "code": "TESTER_MEMBERSHIP_CHANGED_RETRY_RUN_CREATION",
                                "user_ids": stale_members,
                            },
                        )
                    selected_profile_revisions = {
                        decision["assignee_id"]: decision.get("skill_profile_revision", 0)
                        for decision in assignment_decisions.values()
                        if decision.get("assignee_id")
                    }
                    if selected_profile_revisions:
                        try:
                            stale_assignees = await skill_profile_repository.fence_assignment_revisions(
                                payload.project_id,
                                selected_profile_revisions,
                                timestamp,
                                session=session,
                            )
                        except DuplicateKeyError as exc:
                            raise HTTPException(
                                status_code=409,
                                detail={
                                    "code": "SKILL_PROFILE_CHANGED_RETRY_RUN_CREATION",
                                    "user_ids": sorted(selected_profile_revisions),
                                },
                            ) from exc
                        if stale_assignees:
                            raise HTTPException(
                                status_code=409,
                                detail={
                                    "code": "SKILL_PROFILE_CHANGED_RETRY_RUN_CREATION",
                                    "user_ids": stale_assignees,
                                },
                            )
                    run["test_case_assignments"] = test_case_assignments
                    run["test_case_assignment_decisions"] = assignment_decisions
                    run["unassigned_assignment_reasons"] = unassigned_reasons
                await test_run_repository.insert_run(run, session=session)
                if version_ids:
                    await test_run_repository.insert_results(
                        [
                            {
                                "_id": new_id('TRES'),
                                "project_id": payload.project_id,
                                "test_run_id": run["_id"],
                                "test_case_version_id": version_id,
                                "environment": context["environment"],
                                "environment_id": context["environment_id"],
                                "release": context["release"],
                                "release_id": context["release_id"],
                                "build": context["build"],
                                "build_id": context["build_id"],
                                "status": 'NOT_RUN',
                                "step_results": [],
                                "actual_result_doc": {"type": "doc", "content": []},
                                "attachments": [],
                                "note": "",
                                "idempotency_key": None,
                                "revision": 1,
                                "executor_id": None,
                                "started_at": None,
                                "completed_at": None,
                                "created_at": timestamp,
                                "updated_at": timestamp,
                            }
                            for version_id in version_ids
                        ],
                        session=session,
                    )
                await audit(
                    user.id,
                    'test_run_created',
                    'TestRun',
                    run["_id"],
                    payload.project_id,
                    {
                        "test_count": len(version_ids),
                        "assignment_strategy": payload.assignment_strategy,
                        "automatically_assigned_count": len(test_case_assignments),
                        "unassigned_count": len(unassigned_reasons),
                    },
                    session=session,
                )
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await test_run_repository.find_run_by_idempotency_key(
                payload.project_id, payload.idempotency_key
            )
            if existing:
                if not _idempotent_run_matches(existing, payload, version_ids, context):
                    raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
                return existing
        raise
    except PyMongoError as exc:
        if exc.has_error_label("TransientTransactionError"):
            code = (
                "SKILL_PROFILE_CHANGED_RETRY_RUN_CREATION"
                if payload.assignment_strategy == "CONFIRMED_SKILLS"
                else "TEST_RUN_CREATION_CONFLICT"
            )
            raise HTTPException(
                status_code=409,
                detail={"code": code, "retryable": True},
            ) from exc
        raise
    await index_artifact(
        payload.project_id,
        'test_execution',
        run["_id"],
        run["_id"],
        run.get("name") or run["_id"],
        " ".join([run.get("name") or run["_id"], run.get("build") or ""]),
        run["status"],
        'PROJECT_REFERENCE',
        run["revision"],
        test_case_version_ids=version_ids,
    )
    return run


async def rerun_test_run_record(project_id, run_id, payload, user):
    source = await get_project_entity("test_runs", run_id, user, "testrun.create")
    if source.get("project_id") != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    if source.get("status") not in {"COMPLETED", "ABORTED"}:
        raise HTTPException(
            status_code=409,
            detail={"code": "TEST_RUN_RERUN_REQUIRES_TERMINAL_SOURCE"},
        )
    existing = await test_run_repository.find_rerun_by_key(
        project_id, run_id, payload.idempotency_key
    )
    if existing:
        return existing
    key_owner = await test_run_repository.find_run_by_idempotency_key(
        project_id, payload.idempotency_key
    )
    if key_owner:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
    version_ids = list(dict.fromkeys(source.get("test_case_version_ids", [])))
    if not version_ids:
        raise HTTPException(status_code=409, detail={"code": "TEST_RUN_SCOPE_EMPTY"})
    await validate_test_versions(project_id, version_ids)
    plan = None
    snapshot_hash = source.get("test_plan_snapshot_hash")
    requirement_version_ids = list(source.get("requirement_version_ids", []))
    if source.get("test_plan_id"):
        plan = await test_run_repository.find_plan(source["test_plan_id"], project_id)
        if not plan or plan.get("status") != "APPROVED":
            raise HTTPException(status_code=409, detail={"code": "TEST_RUN_PLAN_NO_LONGER_APPROVED"})
        snapshot, current_hash = verified_approved_plan_snapshot(plan, project_id)
        if not snapshot_hash or current_hash != snapshot_hash:
            raise HTTPException(status_code=409, detail={"code": "TEST_RUN_PLAN_SNAPSHOT_CHANGED"})
        if not set(version_ids).issubset(set(snapshot.get("test_case_version_ids", []))):
            raise HTTPException(status_code=409, detail={"code": "TEST_RUN_SCOPE_NO_LONGER_IN_PLAN"})
        requirement_version_ids = list(snapshot.get("requirement_version_ids", []))
    timestamp = now()
    rerun = {
        key: source.get(key)
        for key in (
            "project_id", "test_plan_id", "test_suite_ids", "assignment_strategy",
            "environment", "environment_id", "release", "release_id", "build", "build_id",
            "test_case_assignments", "test_case_assignment_decisions", "unassigned_assignment_reasons",
            "assignee_id", "test_plan_snapshot_hash", "device_matrix_id", "device_profile_keys", "device_matrix_snapshot",
        )
        if key in source
    }
    rerun.update({
        "_id": new_id("TRUN"),
        "idempotency_key": payload.idempotency_key,
        "name": f"{source.get('name') or run_id} · chạy lại",
        "test_case_version_ids": version_ids,
        "requirement_version_ids": requirement_version_ids,
        "rerun_of_run_id": run_id,
        "status": "DRAFT",
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    })
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                current_source = await test_run_repository.find_run(
                    run_id, project_id, session=session
                )
                if not current_source or current_source.get("revision") != source.get("revision"):
                    raise HTTPException(status_code=409, detail={"code": "TEST_RUN_SOURCE_CHANGED"})
                existing = await test_run_repository.find_rerun_by_key(
                    project_id, run_id, payload.idempotency_key, session=session
                )
                if existing:
                    return existing
                if plan:
                    current_plan = await test_run_repository.find_plan(
                        source["test_plan_id"], project_id, session=session
                    )
                    _, current_hash = verified_approved_plan_snapshot(current_plan, project_id)
                    if current_hash != snapshot_hash:
                        raise HTTPException(status_code=409, detail={"code": "TEST_RUN_PLAN_SNAPSHOT_CHANGED"})
                await test_run_repository.insert_run(rerun, session=session)
                await test_run_repository.insert_results(
                    [
                        {
                            "_id": new_id("TRES"),
                            "project_id": project_id,
                            "test_run_id": rerun["_id"],
                            "test_case_version_id": version_id,
                            "environment": rerun.get("environment", ""),
                            "environment_id": rerun.get("environment_id"),
                            "release": rerun.get("release", ""),
                            "release_id": rerun.get("release_id"),
                            "build": rerun.get("build", ""),
                            "build_id": rerun.get("build_id"),
                            "status": "NOT_RUN",
                            "step_results": [],
                            "actual_result_doc": {"type": "doc", "content": []},
                            "attachments": [],
                            "note": "",
                            "idempotency_key": None,
                            "revision": 1,
                            "executor_id": None,
                            "started_at": None,
                            "completed_at": None,
                            "created_at": timestamp,
                            "updated_at": timestamp,
                        }
                        for version_id in version_ids
                    ],
                    session=session,
                )
                await audit(
                    user.id,
                    "test_run_rerun_created",
                    "TestRun",
                    rerun["_id"],
                    project_id,
                    {"source_test_run_id": run_id, "test_count": len(version_ids)},
                    session=session,
                )
    except DuplicateKeyError:
        existing = await test_run_repository.find_rerun_by_key(
            project_id, run_id, payload.idempotency_key
        )
        if existing:
            return existing
        key_owner = await test_run_repository.find_run_by_idempotency_key(
            project_id, payload.idempotency_key
        )
        if key_owner:
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        raise
    await index_artifact(
        project_id,
        "test_execution",
        rerun["_id"],
        rerun["_id"],
        rerun["name"],
        " ".join([rerun["name"], rerun.get("build") or ""]),
        rerun["status"],
        "PROJECT_REFERENCE",
        rerun["revision"],
        test_case_version_ids=version_ids,
    )
    return rerun


async def update_test_run_record(project_id, run_id, payload, user):
    
    run = await get_project_entity('test_runs', run_id, user, 'testrun.update')
    if run["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if run.get("status") != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'TEST_RUN_SCOPE_FROZEN'})
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    target_test_plan_id = changes.get("test_plan_id", run.get("test_plan_id"))
    plan = None
    approved_snapshot = None
    approved_plan_snapshot_hash = None
    if target_test_plan_id and "test_suite_ids" in changes:
        plan = await test_run_repository.find_plan(target_test_plan_id, project_id)
        if not plan or plan.get("status") != "APPROVED":
            raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_NOT_APPROVED"})
        approved_snapshot, approved_plan_snapshot_hash = verified_approved_plan_snapshot(
            plan, project_id
        )
    version_ids = list(dict.fromkeys(
        changes.get("test_case_version_ids", run.get("test_case_version_ids", []))
    ))
    if "test_suite_ids" in changes:
        selected_suite_ids = list(dict.fromkeys(changes["test_suite_ids"]))
        if plan and "test_suite_snapshots" in approved_snapshot:
            suite_versions = _plan_suite_versions(selected_suite_ids, approved_snapshot)
        else:
            suites = await test_run_repository.list_suites(
                project_id, selected_suite_ids, 500
            )
            if len(suites) != len(selected_suite_ids):
                raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_SUITE'})
            suite_versions = [
                version_id
                for suite in suites
                for version_id in suite.get("test_case_version_ids", [])
            ]
        version_ids = list(dict.fromkeys([*version_ids, *suite_versions]))
        changes["test_suite_ids"] = selected_suite_ids
        changes["test_case_version_ids"] = version_ids
    if "test_case_version_ids" in changes:
        await validate_test_versions(project_id, version_ids)
    if {"release_id", "build_id", "environment_id", "release", "build", "environment"} & set(
        changes
    ):
        changes.update(
            await resolve_execution_context(
                project_id,
                user,
                release_id=changes.get("release_id", run.get("release_id")),
                build_id=changes.get("build_id", run.get("build_id")),
                environment_id=changes.get("environment_id", run.get("environment_id")),
                release=changes.get("release", run.get("release", "")),
                build=changes.get("build", run.get("build", "")),
                environment=changes.get("environment", run.get("environment", "")),
            )
        )
    if "test_plan_id" in changes and run.get("test_plan_id"):
        if changes.get("test_plan_id") != run.get("test_plan_id"):
            raise HTTPException(
                status_code=409,
                detail={"code": "TEST_RUN_PLAN_BINDING_FROZEN"},
            )
    if target_test_plan_id:
        if plan is None:
            plan = await test_run_repository.find_plan(target_test_plan_id, project_id)
        if not plan or plan.get("status") != "APPROVED":
            raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_NOT_APPROVED"})
        if approved_snapshot is None:
            approved_snapshot, approved_plan_snapshot_hash = verified_approved_plan_snapshot(
                plan, project_id
            )
        plan_snapshot_hash = approved_plan_snapshot_hash
        if run.get("test_plan_snapshot_hash") and (
            run["test_plan_snapshot_hash"] != plan_snapshot_hash
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "TEST_RUN_PLAN_SNAPSHOT_CHANGED"},
            )
        updated_versions = changes.get("test_case_version_ids", run.get("test_case_version_ids", []))
        _validate_plan_suite_scope(
            changes.get("test_suite_ids", run.get("test_suite_ids", [])), approved_snapshot
        )
        if not set(updated_versions).issubset(
            set(approved_snapshot.get("test_case_version_ids", []))
        ):
            raise HTTPException(status_code=422, detail={"code": "TEST_RUN_OUTSIDE_PLAN_SCOPE"})
        for field in ("release_id", "build_id", "environment_id"):
            planned_value = approved_snapshot.get(field)
            if planned_value and changes.get(field, run.get(field)) != planned_value:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "TEST_RUN_CONTEXT_OUTSIDE_PLAN_SCOPE", "field": field},
                )
        _pin_run_to_plan(changes, approved_snapshot, plan_snapshot_hash)
    if "test_case_version_ids" in changes:
        changes["test_case_version_ids"] = version_ids

    previous_version_ids = set(run.get("test_case_version_ids", []))
    next_version_ids = set(version_ids)
    removed_version_ids = previous_version_ids - next_version_ids
    effective_run = {**run, **changes}
    timestamp = now()
    context_fields = (
        "environment",
        "environment_id",
        "release",
        "release_id",
        "build",
        "build_id",
    )
    context_changed = any(
        field in changes and changes[field] != run.get(field)
        for field in context_fields
    )

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            current_run = await test_run_repository.find_run(
                run_id, project_id, session=session
            )
            if (
                not current_run
                or current_run.get("revision") != payload.expected_revision
                or current_run.get("status") != "DRAFT"
            ):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "TEST_RUN_SCOPE_CHANGED_RETRY"},
                )

            if target_test_plan_id:
                current_plan = await test_run_repository.find_plan(
                    target_test_plan_id, project_id, session=session
                )
                _, current_plan_hash = verified_approved_plan_snapshot(
                    current_plan, project_id
                )
                if current_plan_hash != approved_plan_snapshot_hash:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "TEST_RUN_PLAN_SNAPSHOT_CHANGED"},
                    )

            current_results = await test_run_repository.list_results(
                {"project_id": project_id, "test_run_id": run_id},
                10000,
                session=session,
            )
            results_by_version = {
                item.get("test_case_version_id"): item for item in current_results
            }

            def result_has_execution_history(result):
                return bool(
                    result.get("status") != "NOT_RUN"
                    or result.get("executor_id")
                    or result.get("executed_by")
                    or result.get("started_at")
                    or result.get("completed_at")
                    or result.get("executed_at")
                    or result.get("step_results")
                    or result.get("attachments")
                    or result.get("note")
                    or result.get("idempotency_key")
                    or result.get("actual_result_doc")
                    not in (None, {"type": "doc", "content": []})
                )

            for version_id in removed_version_ids:
                result = results_by_version.get(version_id)
                if result and result_has_execution_history(result):
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "TEST_RUN_RESULT_HISTORY_FROZEN"},
                    )

            if context_changed:
                for version_id in next_version_ids & set(results_by_version):
                    result = results_by_version[version_id]
                    if result_has_execution_history(result):
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "TEST_RUN_RESULT_CONTEXT_FROZEN"},
                        )
                    result_context = {
                        field: effective_run.get(field)
                        for field in context_fields
                    }
                    result_context["updated_at"] = timestamp
                    refreshed = await test_run_repository.update_result(
                        {
                            "_id": result["_id"],
                            "project_id": project_id,
                            "revision": result.get("revision", 1),
                            "status": "NOT_RUN",
                        },
                        result_context,
                        session=session,
                    )
                    if not refreshed:
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "TEST_RUN_RESULT_CONTEXT_CHANGED"},
                        )

            if removed_version_ids:
                await test_run_repository.delete_results_for_versions(
                    run_id, project_id, list(removed_version_ids), session=session
                )

            added_version_ids = next_version_ids - previous_version_ids
            missing_result_ids = added_version_ids - set(results_by_version)
            if missing_result_ids:
                await test_run_repository.insert_results(
                    [
                        {
                            "_id": new_id("TRES"),
                            "project_id": project_id,
                            "test_run_id": run_id,
                            "test_case_version_id": version_id,
                            "environment": effective_run.get("environment", ""),
                            "environment_id": effective_run.get("environment_id"),
                            "release": effective_run.get("release", ""),
                            "release_id": effective_run.get("release_id"),
                            "build": effective_run.get("build", ""),
                            "build_id": effective_run.get("build_id"),
                            "status": "NOT_RUN",
                            "step_results": [],
                            "actual_result_doc": {"type": "doc", "content": []},
                            "attachments": [],
                            "note": "",
                            "idempotency_key": None,
                            "revision": 1,
                            "executor_id": None,
                            "started_at": None,
                            "completed_at": None,
                            "created_at": timestamp,
                            "updated_at": timestamp,
                        }
                        for version_id in sorted(missing_result_ids)
                    ],
                    session=session,
                )

            if removed_version_ids:
                for field in (
                    "test_case_assignments",
                    "test_case_assignment_decisions",
                ):
                    assignments = dict(effective_run.get(field) or {})
                    for version_id in removed_version_ids:
                        assignments.pop(version_id, None)
                    changes[field] = assignments
                changes["unassigned_assignment_reasons"] = [
                    reason
                    for reason in effective_run.get("unassigned_assignment_reasons", [])
                    if not isinstance(reason, dict)
                    or reason.get("test_case_version_id") not in removed_version_ids
                ]

            if added_version_ids and effective_run.get("assignment_strategy") == "CONFIRMED_SKILLS":
                unassigned_reasons = list(
                    changes.get(
                        "unassigned_assignment_reasons",
                        effective_run.get("unassigned_assignment_reasons", []),
                    )
                )
                assignments = dict(
                    changes.get(
                        "test_case_assignments",
                        effective_run.get("test_case_assignments", {}),
                    )
                    or {}
                )
                unresolved_ids = {
                    item.get("test_case_version_id")
                    for item in unassigned_reasons
                    if isinstance(item, dict)
                }
                for version_id in sorted(added_version_ids - set(assignments) - unresolved_ids):
                    unassigned_reasons.append(
                        {
                            "test_case_version_id": version_id,
                            "reason": "ASSIGNMENT_REQUIRED_AFTER_SCOPE_CHANGE",
                        }
                    )
                changes["unassigned_assignment_reasons"] = unassigned_reasons

            updated = await optimistic_patch(
                "test_runs",
                run_id,
                project_id,
                payload.expected_revision,
                changes,
                session=session,
            )
            await audit(
                user.id,
                "test_run_updated",
                "TestRun",
                run_id,
                project_id,
                session=session,
            )
    return updated


async def assign_test_run_record(project_id, run_id, payload, user):
    run = await get_project_entity('test_runs', run_id, user, 'testrun.assign')
    if run["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if payload.assignee_id:
        assignee = await test_run_repository.find_active_tester(
            project_id,
            payload.assignee_id,
            'ACTIVE',
            'TESTER',
        )
        if not assignee:
            raise HTTPException(
                status_code=422,
                detail={"code": 'INVALID_TEST_RUN_ASSIGNEE', "user_id": payload.assignee_id},
            )
    assigned_users = set(payload.test_case_assignments.values())
    if assigned_users:
        valid_members = await test_run_repository.count_active_testers(
            project_id,
            list(assigned_users),
            'ACTIVE',
            'TESTER',
        )
        if valid_members != len(assigned_users):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_CASE_ASSIGNEE'})
    unknown = set(payload.test_case_assignments) - set(run.get("test_case_version_ids", []))
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={"code": 'TEST_NOT_IN_RUN_SNAPSHOT', "test_case_version_ids": sorted(unknown)},
        )
    expected_profile_revisions = payload.expected_skill_profile_revisions
    guarded_assignees = set(expected_profile_revisions)
    if guarded_assignees - (assigned_users | {payload.assignee_id}):
        raise HTTPException(
            status_code=422,
            detail={"code": "SKILL_PROFILE_REVISION_SCOPE_INVALID"},
        )
    async with await database.client.start_session() as session:
        try:
            async with session.start_transaction():
                stale_members = await project_repository.fence_active_testers(
                    project_id,
                    assigned_users | {payload.assignee_id},
                    session=session,
                )
                if stale_members:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "TESTER_MEMBERSHIP_CHANGED_RECOMMEND_AGAIN",
                            "user_ids": stale_members,
                        },
                    )
                if expected_profile_revisions:
                    stale_assignees = await skill_profile_repository.fence_assignment_revisions(
                        project_id,
                        expected_profile_revisions,
                        now(),
                        session=session,
                    )
                    if stale_assignees:
                        raise HTTPException(
                            status_code=409,
                            detail={
                                "code": "SKILL_PROFILE_CHANGED_RECOMMEND_AGAIN",
                                "user_ids": stale_assignees,
                            },
                        )
                updated = await optimistic_patch(
                    'test_runs',
                    run_id,
                    project_id,
                    payload.expected_revision,
                    {
                        "assignee_id": payload.assignee_id,
                        "test_case_assignments": payload.test_case_assignments,
                    },
                    session=session,
                )
                await audit(
                    user.id,
                    'test_run_assigned',
                    'TestRun',
                    run_id,
                    project_id,
                    {"assignee_id": payload.assignee_id},
                    session=session,
                )
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "SKILL_PROFILE_CHANGED_RECOMMEND_AGAIN",
                    "user_ids": sorted(expected_profile_revisions),
                },
            ) from exc
        except PyMongoError as exc:
            if exc.has_error_label("TransientTransactionError"):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "SKILL_PROFILE_CHANGED_RECOMMEND_AGAIN",
                        "user_ids": sorted(expected_profile_revisions),
                    },
                ) from exc
            raise
    return updated
