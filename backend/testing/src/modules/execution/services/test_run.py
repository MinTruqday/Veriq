from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    now,
    optimistic_patch,
)
from src.repositories.test_run import test_run_repository
from src.modules.execution.services.execution_context import resolve_execution_context
from src.modules.execution.services.execution_state import validate_test_versions
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
    "start_test_run_record",
    "update_test_execution_record",
]


async def create_test_run_record(payload, project_id, user):
    
    if project_id is not None and payload.project_id != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    await get_project(payload.project_id, user, 'testrun.create')
    plan = None
    if payload.test_plan_id:
        plan = await test_run_repository.find_plan(payload.test_plan_id, payload.project_id)
        if not plan:
            raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_PLAN'})
        if plan.get("status") != "APPROVED":
            raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_NOT_APPROVED"})
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
        suites = await test_run_repository.list_suites(
            payload.project_id, payload.test_suite_ids, 500
        )
        if len(suites) != len(set(payload.test_suite_ids)):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_SUITE'})
        for suite in suites:
            version_ids.extend(suite.get("test_case_version_ids", []))
        version_ids = list(dict.fromkeys(version_ids))
    if plan:
        approved_snapshot = plan.get("approved_snapshot") or plan
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
            expected = {
                "test_plan_id": payload.test_plan_id,
                "test_case_version_ids": version_ids,
                "release_id": context.get("release_id"),
                "build_id": context.get("build_id"),
                "environment_id": context.get("environment_id"),
            }
            if any(existing.get(key) != value for key, value in expected.items()):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            return existing
    timestamp = now()
    device_scope = (
        {
            "device_matrix_id": plan.get("device_matrix_id"),
            "device_profile_keys": plan.get("device_profile_keys", []),
            "device_matrix_snapshot": plan.get("device_matrix_snapshot"),
        }
        if plan and plan.get("device_matrix_id")
        else {}
    )
    run = {
        "_id": new_id('TRUN'),
        **payload.model_dump(),
        **context,
        **device_scope,
        "test_case_version_ids": version_ids,
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await test_run_repository.insert_run(run)
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await test_run_repository.find_run_by_idempotency_key(
                payload.project_id, payload.idempotency_key
            )
            if existing:
                expected = {
                    "test_plan_id": payload.test_plan_id,
                    "test_case_version_ids": version_ids,
                    "release_id": context.get("release_id"),
                    "build_id": context.get("build_id"),
                    "environment_id": context.get("environment_id"),
                }
                if any(existing.get(key) != value for key, value in expected.items()):
                    raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
                return existing
        raise
    if version_ids:
        try:
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
                ]
            )
        except Exception:
            await test_run_repository.delete_run_results(run["_id"], payload.project_id)
            await test_run_repository.delete_run(run["_id"], payload.project_id)
            raise
    await audit(
        user.id,
        'test_run_created',
        'TestRun',
        run["_id"],
        payload.project_id,
        {"test_count": len(version_ids)},
    )
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


async def update_test_run_record(project_id, run_id, payload, user):
    
    run = await get_project_entity('test_runs', run_id, user, 'testrun.update')
    if run["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if run.get("status") != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'TEST_RUN_SCOPE_FROZEN'})
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    version_ids = changes.get("test_case_version_ids", run.get("test_case_version_ids", []))
    if "test_suite_ids" in changes:
        suites = await test_run_repository.list_suites(
            project_id, changes["test_suite_ids"], 500
        )
        if len(suites) != len(set(changes["test_suite_ids"])):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_SUITE'})
        version_ids = list(
            dict.fromkeys(
                [
                    *version_ids,
                    *[item for suite in suites for item in suite.get("test_case_version_ids", [])],
                ]
            )
        )
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
    if run.get("test_plan_id"):
        plan = await test_run_repository.find_plan(run["test_plan_id"], project_id)
        if not plan or plan.get("status") != "APPROVED":
            raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_NOT_APPROVED"})
        approved_snapshot = plan.get("approved_snapshot") or plan
        updated_versions = changes.get("test_case_version_ids", run.get("test_case_version_ids", []))
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
    updated = await optimistic_patch(
        'test_runs', run_id, project_id, payload.expected_revision, changes
    )
    await audit(user.id, 'test_run_updated', 'TestRun', run_id, project_id)
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
    updated = await optimistic_patch(
        'test_runs',
        run_id,
        project_id,
        payload.expected_revision,
        {
            "assignee_id": payload.assignee_id,
            "test_case_assignments": payload.test_case_assignments,
        },
    )
    await audit(
        user.id,
        'test_run_assigned',
        'TestRun',
        run_id,
        project_id,
        {"assignee_id": payload.assignee_id},
    )
    return updated
