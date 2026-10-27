import hashlib
import json
import re

from fastapi import HTTPException
from pydantic import ValidationError

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    now,
    optimistic_patch,
    require_action_policy,
    sort_spec,
)
from src.core.database import database
from src.schemas.contracts.planning import TestPlanCreate, TestPlanSuiteSnapshot
from src.repositories.test_plan import test_plan_repository
from src.repositories.project import project_repository
from src.modules.execution.services.execution_context import resolve_execution_context


LEGACY_PLAN_SNAPSHOT_FIELDS = (
    'project_id', 'name', 'objective', 'scope_in', 'scope_out',
    'requirement_version_ids', 'test_suite_ids', 'test_case_version_ids',
    'environment', 'environment_id', 'entry_criteria', 'exit_criteria', 'risks',
    'test_types', 'members', 'release', 'release_id', 'build', 'build_id',
    'strategy_version_id', 'strategy_id', 'strategy_version',
    'strategy_snapshot_hash', 'test_level', 'test_approach', 'assumptions',
    'constraints', 'dependencies', 'stakeholders', 'responsibility_matrix',
    'estimation', 'schedule', 'milestones', 'deliverables', 'tools',
    'suspension_criteria', 'resumption_criteria', 'monitoring_metrics',
    'quality_targets', 'risk_register', 'communication_plan',
)
LEGACY_DEVICE_PLAN_SNAPSHOT_FIELDS = (
    *LEGACY_PLAN_SNAPSHOT_FIELDS,
    'device_matrix_id', 'device_profile_keys', 'device_matrix_snapshot',
)
PLAN_SNAPSHOT_FIELDS = (
    *LEGACY_PLAN_SNAPSHOT_FIELDS,
    'test_suite_snapshots',
    'device_matrix_id', 'device_profile_keys', 'device_matrix_snapshot',
)


def plan_snapshot(plan):
    return {field: plan.get(field) for field in PLAN_SNAPSHOT_FIELDS}


def plan_snapshot_hash(plan):
    canonical = json.dumps(
        plan_snapshot(plan), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _legacy_plan_snapshot_hash(snapshot):
    canonical_snapshot = {
        field: snapshot.get(field) for field in LEGACY_PLAN_SNAPSHOT_FIELDS
    }
    canonical = json.dumps(
        canonical_snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verified_approved_plan_snapshot(plan, project_id):
    """Return the immutable approved scope only when its stored digest matches."""
    if not plan or plan.get("status") != "APPROVED":
        raise HTTPException(status_code=409, detail={"code": "TEST_PLAN_NOT_APPROVED"})
    snapshot = plan.get("approved_snapshot")
    if not isinstance(snapshot, dict):
        snapshot = {
            field: plan.get(field) for field in LEGACY_PLAN_SNAPSHOT_FIELDS
        }
    approved_digest = plan.get("approved_snapshot_hash") or plan.get("baseline_hash")
    device_snapshot_fields = (
        "device_matrix_id",
        "device_profile_keys",
        "device_matrix_snapshot",
    )
    has_any_device_snapshot = any(field in snapshot for field in device_snapshot_fields)
    has_device_snapshot = all(field in snapshot for field in device_snapshot_fields)
    if 'test_suite_snapshots' in snapshot:
        digest = plan_snapshot_hash(snapshot)
    elif has_device_snapshot:
        legacy_snapshot = {
            field: snapshot.get(field)
            for field in LEGACY_DEVICE_PLAN_SNAPSHOT_FIELDS
        }
        canonical = json.dumps(
            legacy_snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(',', ':'),
            default=str,
        )
        digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    else:
        digest = _legacy_plan_snapshot_hash(snapshot)
    if (
        snapshot.get("project_id") != project_id
        or not approved_digest
        or digest != approved_digest
        or (plan.get("approved_snapshot_hash") and plan["approved_snapshot_hash"] != digest)
        or (plan.get("baseline_hash") and plan["baseline_hash"] != digest)
        or (has_any_device_snapshot and not has_device_snapshot)
        or (
            not has_device_snapshot
            and plan.get("device_matrix_id")
        )
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "TEST_PLAN_APPROVED_SNAPSHOT_INVALID"},
        )
    return snapshot, digest


def plan_completeness(plan, settings=None):
    settings = settings or {}
    
    checks = [
        (
            'TEST_PLAN_STRATEGY_REQUIRED',
            all(plan.get(field) for field in ['strategy_version_id', 'strategy_snapshot_hash']),
        ),
        *[
            (requirement["code"], bool(plan.get(requirement["field"])))
            for requirement in [{'code': 'TEST_PLAN_OBJECTIVE_REQUIRED', 'field': 'objective'},
 {'code': 'TEST_PLAN_SCOPE_REQUIRED', 'field': 'scope_in'},
 {'code': 'TEST_PLAN_REQUIREMENT_SCOPE_REQUIRED', 'field': 'requirement_version_ids'},
 {'code': 'TEST_PLAN_ENTRY_CRITERIA_REQUIRED', 'field': 'entry_criteria'},
 {'code': 'TEST_PLAN_EXIT_CRITERIA_REQUIRED', 'field': 'exit_criteria'},
 {'code': 'TEST_PLAN_TEST_TYPE_REQUIRED', 'field': 'test_types'},
 {'code': 'TEST_PLAN_QUALITY_TARGET_REQUIRED', 'field': 'quality_targets'}]
        ],
        (
            'TEST_PLAN_SCHEDULE_REQUIRED',
            all(
                (plan.get('schedule') or {}).get(field)
                for field in ['planned_start_at', 'planned_end_at']
            ),
        ),
    ]
    for requirement in [{'setting': 'require_release_for_test_plan',
  'default': True,
  'code': 'TEST_PLAN_RELEASE_REQUIRED',
  'field': 'release_id'},
 {'setting': 'require_environment_for_test_plan',
  'default': True,
  'code': 'TEST_PLAN_ENVIRONMENT_REQUIRED',
  'field': 'environment_id'}]:
        if settings.get(requirement["setting"], requirement["default"]):
            checks.append((requirement["code"], bool(plan.get(requirement["field"]))))
    findings = [
        {"code": code, "severity": 'MAJOR'}
        for code, passed in checks
        if not passed
    ]
    return {"ready_for_approval": not findings, "findings": findings}


async def validate_effort_allocation_members(project_id, estimation, session=None):
    allocation_ids = {
        item.user_id for item in (estimation.effort_allocations or [])
    }
    if not allocation_ids:
        return
    members = await project_repository.list_members(project_id, session=session)
    active_ids = {
        item.get("user_id")
        for item in members
        if item.get("status") == "ACTIVE"
    }
    unknown = sorted(allocation_ids - active_ids)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={"code": "TEST_PLAN_EFFORT_MEMBER_NOT_ACTIVE", "user_ids": unknown},
        )


async def validate_plan_scope(project_id, requirement_version_ids, test_suite_ids, test_case_version_ids):
    requirement_ids = list(dict.fromkeys(requirement_version_ids or []))
    if requirement_ids and await test_plan_repository.count_requirement_versions(project_id, requirement_ids) != len(requirement_ids):
        raise HTTPException(status_code=422, detail={"code": "INVALID_BASELINED_REQUIREMENT_SCOPE"})
    suite_ids = list(dict.fromkeys(test_suite_ids or []))
    suites = await test_plan_repository.list_suites(project_id, suite_ids) if suite_ids else []
    if len(suites) != len(suite_ids):
        raise HTTPException(status_code=422, detail={"code": "INVALID_TEST_SET_SCOPE"})
    suites_by_id = {str(suite.get('_id')): suite for suite in suites}
    if any(
        not isinstance(suites_by_id[suite_id].get('revision'), int)
        or isinstance(suites_by_id[suite_id].get('revision'), bool)
        for suite_id in suite_ids
    ):
        raise HTTPException(status_code=409, detail={"code": "TEST_SET_REVISION_INVALID"})
    try:
        suite_snapshots = [
            TestPlanSuiteSnapshot(
                test_suite_id=suite_id,
                revision=suites_by_id[suite_id].get('revision'),
                test_case_version_ids=list(
                    dict.fromkeys(suites_by_id[suite_id].get('test_case_version_ids', []))
                ),
            ).model_dump()
            for suite_id in suite_ids
        ]
    except ValidationError as error:
        raise HTTPException(
            status_code=409, detail={"code": "TEST_SET_REVISION_INVALID"}
        ) from error
    versions = list(dict.fromkeys([
        *(test_case_version_ids or []),
        *[
            version_id
            for suite in suite_snapshots
            for version_id in suite['test_case_version_ids']
        ],
    ]))
    if versions and await test_plan_repository.count_test_case_versions(project_id, versions) != len(versions):
        raise HTTPException(status_code=422, detail={"code": "INVALID_TEST_CASE_SCOPE"})
    return {
        "requirement_version_ids": requirement_ids,
        "test_suite_ids": suite_ids,
        "test_case_version_ids": versions,
        "test_suite_snapshots": suite_snapshots,
    }


async def resolve_strategy_binding(project_id, strategy_version_id, auto_bind=False):
    
    strategy = None
    if strategy_version_id:
        strategy = await test_plan_repository.find_strategy(
            project_id, strategy_version_id
        )
        if not strategy:
            raise HTTPException(status_code=422, detail={"code": 'INVALID_STRATEGY_VERSION'})
        if strategy.get("status") != 'APPROVED' or not strategy.get(
            "snapshot_hash"
        ):
            raise HTTPException(
                status_code=409, detail={"code": 'STRATEGY_VERSION_NOT_APPROVED'}
            )
    elif auto_bind:
        strategy = await test_plan_repository.find_active_strategy(
            project_id, 'APPROVED'
        )
    if not strategy:
        return {
            "strategy_version_id": None,
            "strategy_id": None,
            "strategy_version": None,
            "strategy_snapshot_hash": None,
        }
    return {
        "strategy_version_id": strategy["_id"],
        "strategy_id": strategy["lineage_id"],
        "strategy_version": strategy["version"],
        "strategy_snapshot_hash": strategy["snapshot_hash"],
    }


async def create_test_plan_record(payload, project_id, user):
    
    if project_id and project_id != payload.project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_SCOPE_MISMATCH'})
    await get_project(payload.project_id, user, "testplan.create")
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
    if payload.members:
        await require_action_policy(
            payload.project_id,
            user,
            "testplan.assignments",
            set(['QA']),
        )
    await validate_effort_allocation_members(payload.project_id, payload.estimation)
    strategy_binding = await resolve_strategy_binding(
        payload.project_id,
        payload.strategy_version_id,
        auto_bind=True,
    )
    scope = await validate_plan_scope(
        payload.project_id,
        payload.requirement_version_ids,
        payload.test_suite_ids,
        payload.test_case_version_ids,
    )
    timestamp = now()
    plan = {
        "_id": new_id('TP'),
        **payload.model_dump(),
        **scope,
        **context,
        **strategy_binding,
        "status": 'DRAFT',
        "approval_history": [],
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    from src.clients.ai_automation import emit_test_plan_changed

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            await test_plan_repository.insert_plan(plan, session=session)
            await audit(
                user.id,
                "test_plan_created",
                "TestPlan",
                plan["_id"],
                payload.project_id,
                session=session,
            )
            await emit_test_plan_changed(plan, user, session=session)
    return plan


async def list_test_plan_records(
    project_id,
    user,
    q="",
    release="",
    release_id="",
    build_id="",
    environment_id="",
    status="",
    sort="-updated_at",
):
    
    await get_project(project_id, user, "testplan.read")
    query = {"project_id": project_id}
    if q:
        query["$or"] = [
            {"name": {"$regex": re.escape(q), "$options": "i"}},
            {"objective": {"$regex": re.escape(q), "$options": "i"}},
        ]
    for field, value in {
        "release": release,
        "release_id": release_id,
        "build_id": build_id,
        "environment_id": environment_id,
        "status": status,
    }.items():
        if value:
            query[field] = value
    sort_field, direction = sort_spec(
        sort,
        set(['name', 'release', 'status', 'created_at', 'updated_at']),
    )
    return await test_plan_repository.list_plans(
        query, sort_field, direction, 500
    )


async def get_test_plan_record(plan_id, user, permission="testplan.read"):
    return await get_project_entity("test_plans", plan_id, user, permission)


async def validate_test_plan_record(plan_id, user):
    plan = await get_test_plan_record(plan_id, user, "testplan.review")
    settings = await test_plan_repository.find_project_settings(plan["project_id"])
    return plan_completeness(plan, settings)


async def update_test_plan_record(plan_id, payload, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.update")
    if plan.get("status") != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'TEST_PLAN_NOT_DRAFT'})
    if payload.members is not None:
        await require_action_policy(
            plan["project_id"],
            user,
            "testplan.assignments",
            set(['QA']),
        )
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "estimation" in changes:
        await validate_effort_allocation_members(
            plan["project_id"], TestPlanCreate.model_validate({**plan, **changes}).estimation
        )
    if "strategy_version_id" in changes:
        changes.update(
            await resolve_strategy_binding(
                plan["project_id"],
                changes.get("strategy_version_id"),
                auto_bind=False,
            )
        )
    if {"requirement_version_ids", "test_suite_ids", "test_case_version_ids"} & set(changes):
        scope = await validate_plan_scope(
            plan["project_id"],
            changes.get("requirement_version_ids", plan.get("requirement_version_ids", [])),
            changes.get("test_suite_ids", plan.get("test_suite_ids", [])),
            changes.get("test_case_version_ids", plan.get("test_case_version_ids", [])),
        )
        changes.update(scope)
    if {"release_id", "build_id", "environment_id", "release", "build", "environment"} & set(
        changes
    ):
        changes.update(
            await resolve_execution_context(
                plan["project_id"],
                user,
                release_id=changes.get("release_id", plan.get("release_id")),
                build_id=changes.get("build_id", plan.get("build_id")),
                environment_id=changes.get("environment_id", plan.get("environment_id")),
                release=changes.get("release", plan.get("release", "")),
                build=changes.get("build", plan.get("build", "")),
                environment=changes.get("environment", plan.get("environment", "")),
            )
        )
    validation_data = {}
    for field in TestPlanCreate.model_fields:
        if field in changes:
            validation_data[field] = changes[field]
        elif field in plan:
            validation_data[field] = plan[field]
    TestPlanCreate.model_validate(validation_data)
    from src.clients.ai_automation import emit_test_plan_changed

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await optimistic_patch(
                "test_plans",
                plan_id,
                plan["project_id"],
                payload.expected_revision,
                changes,
                session=session,
            )
            await audit(
                user.id,
                "test_plan_updated",
                "TestPlan",
                plan_id,
                plan["project_id"],
                session=session,
            )
            await emit_test_plan_changed(updated, user, session=session)
    return updated


async def submit_test_plan_record(plan_id, payload, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.submit_review")
    if plan.get("status") != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    from src.clients.ai_automation import emit_test_plan_changed

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await optimistic_patch(
                "test_plans",
                plan_id,
                plan["project_id"],
                payload.expected_revision,
                {"status": 'IN_REVIEW', "review_note": payload.review_note},
                session=session,
            )
            await audit(
                user.id,
                "test_plan_submitted",
                "TestPlan",
                plan_id,
                plan["project_id"],
                session=session,
            )
            await emit_test_plan_changed(updated, user, session=session)
    return updated


async def approve_test_plan_record(plan_id, payload, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.approve")
    if plan.get("status") not in ['DRAFT', 'IN_REVIEW']:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    scope = await validate_plan_scope(
        plan['project_id'],
        plan.get('requirement_version_ids', []),
        plan.get('test_suite_ids', []),
        plan.get('test_case_version_ids', []),
    )
    if (
        'test_suite_snapshots' in plan
        and plan['test_suite_snapshots'] != scope['test_suite_snapshots']
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "TEST_SET_CHANGED_REVIEW_REQUIRED"},
        )
    plan = {**plan, **scope}
    settings = await test_plan_repository.find_project_settings(plan["project_id"])
    completeness = plan_completeness(plan, settings)
    scope_findings = [
        finding
        for finding in completeness["findings"]
        if finding["code"] == "TEST_PLAN_REQUIREMENT_SCOPE_REQUIRED"
    ]
    if scope_findings or settings.get("strict_test_plan_approval", False):
        if not completeness["ready_for_approval"]:
            raise HTTPException(
                status_code=409,
                detail={"code": 'TEST_PLAN_INCOMPLETE', **completeness},
            )
    timestamp = now()
    approved_hash = plan_snapshot_hash(plan)
    approval = {
        "actor_id": user.id,
        "action": 'APPROVED',
        "note": payload.review_note,
        "at": timestamp,
    }
    from src.clients.ai_automation import emit_test_plan_approved

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await optimistic_patch(
                "test_plans",
                plan_id,
                plan["project_id"],
                payload.expected_revision,
                {
                    **scope,
                    "status": 'APPROVED',
                    "approved_by": user.id,
                    "approved_at": timestamp,
                    "approved_snapshot": plan_snapshot(plan),
                    "approved_snapshot_hash": approved_hash,
                    "baseline_hash": approved_hash,
                    "approval_history": [*plan.get("approval_history", []), approval],
                    "review_note": payload.review_note,
                },
                session=session,
            )
            await audit(
                user.id,
                "test_plan_approved",
                "TestPlan",
                plan_id,
                plan["project_id"],
                session=session,
            )
            await emit_test_plan_approved(updated, user, session=session)
    return updated


async def archive_test_plan_record(plan_id, payload, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.archive")
    from src.clients.ai_automation import emit_test_plan_changed

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await optimistic_patch(
                "test_plans",
                plan_id,
                plan["project_id"],
                payload.expected_revision,
                {
                    "status": 'ARCHIVED',
                    "archive_reason": payload.reason,
                    "archived_by": user.id,
                    "archived_at": now(),
                },
                session=session,
            )
            await audit(
                user.id,
                "test_plan_archived",
                "TestPlan",
                plan_id,
                plan["project_id"],
                session=session,
            )
            await emit_test_plan_changed(updated, user, session=session)
    return updated


async def clone_test_plan_record(plan_id, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.create")
    timestamp = now()
    cloned = {
        **plan,
        "_id": new_id('TP'),
        "name": f"{plan['name']}{' bản sao'}",
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    for field in (
        "approved_at",
        "approved_by",
        "approved_snapshot",
        "approved_snapshot_hash",
        "baseline_hash",
        "approval_history",
        "archived_at",
        "archived_by",
        "archive_reason",
        "reviewed_at",
        "reviewed_by",
    ):
        cloned.pop(field, None)
    cloned["approval_history"] = []
    from src.clients.ai_automation import emit_test_plan_changed

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            await test_plan_repository.insert_plan(cloned, session=session)
            await audit(
                user.id,
                "test_plan_cloned",
                "TestPlan",
                cloned["_id"],
                plan["project_id"],
                {"source_plan_id": plan_id},
                session=session,
            )
            await emit_test_plan_changed(cloned, user, session=session)
    return cloned
