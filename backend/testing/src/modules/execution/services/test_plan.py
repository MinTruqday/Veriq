import hashlib
import json
import re

from fastapi import HTTPException
from pydantic import ValidationError
from pymongo import ReturnDocument

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    now,
    optimistic_patch,
    sort_spec,
)
from src.core.database import database
from src.core.human_decisions import (
    can_auto_approve_project_content,
    content_authorship_changes,
    require_ai_publication_authority,
    require_independent_review,
)
from src.modules.design.services.test_case_records import require_current_baselined_version
from src.modules.execution.services.execution_context import resolve_execution_context
from src.modules.execution.services.test_period import touch_open_test_period
from src.repositories.project import project_repository
from src.repositories.test_plan import test_plan_repository
from src.repositories.test_run import test_run_repository
from src.schemas.contracts.planning import TestPlanCreate, TestPlanSuiteSnapshot

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
    'project_id', 'name', 'objective', 'scope_out',
    'requirement_version_ids', 'test_suite_ids', 'test_case_version_ids',
    'test_suite_snapshots', 'environment', 'environment_id',
    'entry_criteria', 'exit_criteria', 'test_types', 'members',
    'strategy_version_id', 'strategy_id', 'strategy_version', 'strategy_snapshot_hash',
    'test_level',
    'assumptions', 'constraints', 'dependencies', 'estimation', 'schedule',
    'risk_register', 'communication_plan',
    'owner_id', 'scenario_ids',
)

def plan_snapshot(plan):
    snapshot = {field: plan[field] for field in PLAN_SNAPSHOT_FIELDS if field in plan}
    if plan.get("test_period_id"):
        snapshot["test_period_id"] = plan["test_period_id"]
        if plan.get("test_period_snapshot"):
            snapshot["test_period_snapshot"] = plan["test_period_snapshot"]
    for field in ("test_techniques",):
        if field in plan:
            snapshot[field] = plan[field]
    if plan.get("carry_over_items"):
        snapshot["carry_over_items"] = plan["carry_over_items"]
    return snapshot


async def validate_carry_over_items(project_id, items, target_period_id=None):
    carry_items = [item.model_dump() if hasattr(item, "model_dump") else dict(item) for item in items or []]
    if carry_items and not target_period_id:
        raise HTTPException(status_code=422, detail={"code": "CARRY_OVER_TARGET_PERIOD_REQUIRED"})
    seen = set()
    for item in carry_items:
        version_id = item["test_case_version_id"]
        if version_id in seen:
            raise HTTPException(status_code=422, detail={"code": "DUPLICATE_CARRY_OVER_CASE"})
        seen.add(version_id)
        source_run_id = item.get("source_test_run_id")
        source_plan_id = item.get("source_test_plan_id")
        if bool(source_run_id) == bool(source_plan_id):
            raise HTTPException(status_code=422, detail={"code": "CARRY_OVER_REQUIRES_ONE_SOURCE"})
        source = None
        source_plan = None
        if source_run_id:
            source = await test_run_repository.find_run(source_run_id, project_id)
            if not source or version_id not in set(source.get("test_case_version_ids", [])):
                raise HTTPException(status_code=422, detail={"code": "INVALID_CARRY_OVER_SOURCE_CASE"})
            source_period_id = source.get("test_period_id")
        else:
            source_plan = await test_run_repository.find_plan(source_plan_id, project_id)
            snapshot = (source_plan or {}).get("approved_snapshot") or source_plan or {}
            if not source_plan or version_id not in set(snapshot.get("test_case_version_ids", [])):
                raise HTTPException(status_code=422, detail={"code": "INVALID_CARRY_OVER_SOURCE_CASE"})
            source_period_id = source_plan.get("test_period_id")
        if not source_period_id:
            raise HTTPException(status_code=422, detail={"code": "CARRY_OVER_SOURCE_PERIOD_REQUIRED"})
        if source_period_id == target_period_id:
            raise HTTPException(status_code=422, detail={"code": "CARRY_OVER_PERIOD_MUST_DIFFER"})
        source_period = await database.value.test_periods.find_one(
            {"_id": source_period_id, "project_id": project_id}
        )
        if not source_period or source_period.get("status") != "CLOSED":
            raise HTTPException(status_code=422, detail={"code": "CARRY_OVER_SOURCE_PERIOD_NOT_CLOSED"})
        item["source_period_id"] = source_period_id
        item["source_period_name"] = (
            (source_period or {}).get("name")
            or ((source or {}).get("test_period_snapshot") or {}).get("name")
            or ((source_plan or {}).get("test_period_snapshot") or {}).get("name")
            or ""
        )
        result = (
            await test_run_repository.find_result_for_case(source["_id"], version_id)
            if source else None
        )
        status = (result or {}).get("status", "NOT_RUN")
        if status not in {"NOT_RUN", "IN_PROGRESS", "FAIL", "BLOCKED", "SKIPPED"}:
            raise HTTPException(status_code=422, detail={"code": "CARRY_OVER_CASE_NOT_ELIGIBLE", "status": status})
        item["source_status"] = status
        item["source_run_name"] = (source or {}).get("name", "")
        item["source_plan_name"] = (source_plan or {}).get("name", "")
    return carry_items

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

def _prior_plan_snapshot_hash(snapshot):
    fields = (
        *LEGACY_PLAN_SNAPSHOT_FIELDS,
        'test_suite_snapshots',
        'device_matrix_id', 'device_profile_keys', 'device_matrix_snapshot',
    )
    canonical_snapshot = {field: snapshot.get(field) for field in fields}
    canonical_snapshot.update({
        field: snapshot[field]
        for field in (
            'test_data_plan', 'defect_management', 'owner_id', 'scenario_ids',
            'test_techniques', 'phase', 'carry_over_items', 'test_period_id',
            'test_period_snapshot',
        )
        if field in snapshot
    })
    canonical = json.dumps(
        canonical_snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
        default=str,
    )
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

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
    if 'test_suite_snapshots' in snapshot:
        digest = plan_snapshot_hash(snapshot)
        if digest != approved_digest:
            digest = _prior_plan_snapshot_hash(snapshot)
    elif all(
        field in snapshot
        for field in ('device_matrix_id', 'device_profile_keys', 'device_matrix_snapshot')
    ):
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
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "TEST_PLAN_APPROVED_SNAPSHOT_INVALID"},
        )
    return snapshot, digest

def plan_completeness(plan):
    checks = [
        ('TEST_PLAN_OBJECTIVE_REQUIRED', bool(str(plan.get('objective') or '').strip())),
        ('TEST_PLAN_REQUIREMENT_SCOPE_REQUIRED', bool(plan.get('requirement_version_ids'))),
    ]
    findings = [
        {"code": code, "blocks_approval": True}
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

async def validate_plan_links(project_id, owner_id, scenario_ids):
    if owner_id:
        members = await project_repository.list_members(project_id)
        if not any(
            member.get("user_id") == owner_id and member.get("status") == "ACTIVE"
            for member in members
        ):
            raise HTTPException(status_code=422, detail={"code": "TEST_PLAN_OWNER_NOT_ACTIVE"})
    scenario_ids = list(dict.fromkeys(scenario_ids or []))
    if scenario_ids and await database.value.test_scenarios.count_documents(
        {"project_id": project_id, "_id": {"$in": scenario_ids}, "status": {"$ne": "archived"}}
    ) != len(scenario_ids):
        raise HTTPException(status_code=422, detail={"code": "INVALID_TEST_PLAN_SCENARIO_SCOPE"})
    return scenario_ids


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

async def create_test_plan_record(payload, project_id, user):
    
    if project_id and project_id != payload.project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_SCOPE_MISMATCH'})
    await get_project(payload.project_id, user, "testplan.create")
    if payload.new_test_period and payload.test_period_id:
        raise HTTPException(status_code=422, detail={"code": "TEST_PERIOD_SELECTION_CONFLICT"})
    period_id = payload.test_period_id or (new_id("CYCLE") if payload.new_test_period else None)
    period = None
    if payload.test_period_id:
        period = await database.value.test_periods.find_one(
            {"_id": payload.test_period_id, "project_id": payload.project_id}
        )
        if not period:
            raise HTTPException(status_code=422, detail={"code": "TEST_PERIOD_NOT_FOUND"})
        if period.get("status") == "CLOSED":
            raise HTTPException(status_code=409, detail={"code": "TEST_PERIOD_CLOSED"})
    source_period = None
    if payload.new_test_period and payload.new_test_period.source_period_id:
        source_period = await database.value.test_periods.find_one(
            {
                "_id": payload.new_test_period.source_period_id,
                "project_id": payload.project_id,
                "status": "CLOSED",
            }
        )
        if not source_period:
            raise HTTPException(
                status_code=422, detail={"code": "TEST_PERIOD_SOURCE_NOT_CLOSED"}
            )
    context = await resolve_execution_context(
        payload.project_id,
        user,
        environment_id=payload.environment_id,
    )
    scenario_ids = await validate_plan_links(payload.project_id, payload.owner_id, payload.scenario_ids)
    await validate_effort_allocation_members(payload.project_id, payload.estimation)
    selected_carry_over = list(payload.carry_over_items)
    if not selected_carry_over and period:
        selected_carry_over = list(period.get("carry_over_items", []))
    if not selected_carry_over and source_period:
        selected_carry_over = list(source_period.get("carry_over_items", []))
    carry_over_items = await validate_carry_over_items(
        payload.project_id, selected_carry_over, period_id
    )
    scope = await validate_plan_scope(
        payload.project_id,
        payload.requirement_version_ids,
        payload.test_suite_ids,
        list(dict.fromkeys([*payload.test_case_version_ids, *(item["test_case_version_id"] for item in carry_over_items)])),
    )
    if not payload.save_as_draft:
        completeness = plan_completeness(payload.model_dump())
        if not completeness["ready_for_approval"]:
            raise HTTPException(status_code=422, detail={"code": "TEST_PLAN_INCOMPLETE", "message": "Nhập mục tiêu và liên kết ít nhất một phiên bản yêu cầu trước khi lưu kế hoạch.", **completeness})
    timestamp = now()
    plan = {
        "_id": new_id('TP'),
        **payload.model_dump(exclude={"save_as_draft", "new_test_period"}),
        "test_period_id": period_id,
        "carry_over_items": carry_over_items,
        "scenario_ids": scenario_ids,
        "test_level": payload.test_level,
        "test_types": payload.test_types,
        **scope,
        "environment": context["environment"],
        "environment_id": context["environment_id"],
        "status": 'DRAFT' if payload.save_as_draft else 'READY',
        "approval_history": [],
        "revision": 1,
        "created_by": user.id,
        "content_author_ids": [user.id],
        "content_authorship_status": "VERIFIED",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    if period:
        plan["test_period_snapshot"] = {
            "_id": period["_id"],
            "name": period["name"],
            "sequence": period["sequence"],
        }

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            if payload.new_test_period:
                counter = await database.value.test_period_counters.find_one_and_update(
                    {"_id": payload.project_id},
                    {"$inc": {"sequence": 1}},
                    upsert=True,
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )
                period = {
                    "_id": period_id,
                    "project_id": payload.project_id,
                    **payload.new_test_period.model_dump(),
                    "sequence": counter["sequence"],
                    "status": "PLANNED",
                    "revision": 1,
                    "created_by": user.id,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "carry_over_items": [],
                }
                period.pop("source_period_id", None)
                if source_period:
                    period["source_period_id"] = source_period["_id"]
                    period["carry_over_items"] = [
                        dict(item) for item in carry_over_items
                    ]
                await database.value.test_periods.insert_one(period, session=session)
                await audit(
                    user.id,
                    "test_period_created",
                    "TestPeriod",
                    period["_id"],
                    payload.project_id,
                    session=session,
                )
                plan["test_period_id"] = period["_id"]
                plan["test_period_snapshot"] = {
                    "_id": period["_id"],
                    "name": period["name"],
                    "sequence": period["sequence"],
                }
            elif period_id:
                await touch_open_test_period(payload.project_id, period_id, session)
            await test_plan_repository.insert_plan(plan, session=session)
            await audit(
                user.id,
                "test_plan_created",
                "TestPlan",
                plan["_id"],
                payload.project_id,
                session=session,
            )
    if not payload.save_as_draft and await can_auto_approve_project_content(payload.project_id, user):
        from src.schemas.contracts.requirements import ReviewTransitionInput

        review = ReviewTransitionInput(expected_revision=plan["revision"], review_note="")
        return await submit_test_plan_record(plan["_id"], review, user)
    return plan

async def list_test_plan_records(
    project_id,
    user,
    q="",
    environment_id="",
    test_period_id="",
    status="",
    sort="-updated_at",
):
    
    await get_project(project_id, user, "testplan.read")
    query = {"project_id": project_id}
    if q:
        query["$or"] = [
            {"_id": {"$regex": re.escape(q), "$options": "i"}},
            {"name": {"$regex": re.escape(q), "$options": "i"}},
        ]
    for field, value in {
        "environment_id": environment_id,
        "test_period_id": test_period_id,
        "status": status,
    }.items():
        if value:
            query[field] = value
    sort_field, direction = sort_spec(
        sort,
        set(['name', 'status', 'created_at', 'updated_at']),
    )
    return await test_plan_repository.list_plans(
        query, sort_field, direction, 500
    )

async def get_test_plan_record(plan_id, user, permission="testplan.read"):
    return await get_project_entity("test_plans", plan_id, user, permission)

async def validate_test_plan_record(plan_id, user):
    plan = await get_test_plan_record(plan_id, user, "testplan.read")
    return plan_completeness(plan)

async def update_test_plan_record(plan_id, payload, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.update")
    if plan.get("status") not in ('DRAFT', 'READY'):
        raise HTTPException(status_code=409, detail={"code": 'TEST_PLAN_NOT_DRAFT'})
    existing_period_id = plan.get("test_period_id")
    if existing_period_id:
        existing_period = await database.value.test_periods.find_one(
            {"_id": existing_period_id, "project_id": plan["project_id"]},
            {"status": 1},
        )
        if not existing_period or existing_period.get("status") == "CLOSED":
            raise HTTPException(status_code=409, detail={"code": "TEST_PERIOD_UNAVAILABLE"})
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "test_period_id" in changes and changes["test_period_id"]:
        period = await database.value.test_periods.find_one(
            {"_id": changes["test_period_id"], "project_id": plan["project_id"]}
        )
        if not period:
            raise HTTPException(status_code=422, detail={"code": "TEST_PERIOD_NOT_FOUND"})
        if period.get("status") == "CLOSED":
            raise HTTPException(status_code=409, detail={"code": "TEST_PERIOD_CLOSED"})
        changes["test_period_snapshot"] = {
            "_id": period["_id"],
            "name": period["name"],
            "sequence": period["sequence"],
        }
    elif changes.get("test_period_id") is None:
        changes["test_period_snapshot"] = None
    if "test_period_id" in changes and "carry_over_items" not in changes:
        target_period_id = changes.get("test_period_id")
        target_period = await database.value.test_periods.find_one(
            {"_id": target_period_id, "project_id": plan["project_id"]}
        ) if target_period_id else None
        changes["carry_over_items"] = (target_period or {}).get("carry_over_items", [])
    if {"carry_over_items", "test_period_id"} & set(changes):
        changes["carry_over_items"] = await validate_carry_over_items(
            plan["project_id"],
            changes.get("carry_over_items", plan.get("carry_over_items", [])),
            changes.get("test_period_id", plan.get("test_period_id")),
        )
        changes["test_case_version_ids"] = list(dict.fromkeys([
            *changes.get("test_case_version_ids", plan.get("test_case_version_ids", [])),
            *(item["test_case_version_id"] for item in changes["carry_over_items"]),
        ]))
    if "estimation" in changes:
        await validate_effort_allocation_members(
            plan["project_id"], TestPlanCreate.model_validate({**plan, **changes}).estimation
        )
    if "environment_id" in changes:
        environment_context = await resolve_execution_context(
            plan["project_id"],
            user,
            environment_id=changes.get("environment_id", plan.get("environment_id")),
        )
        changes.update(
            {
                "environment": environment_context["environment"],
                "environment_id": environment_context["environment_id"],
            }
        )
    if {"requirement_version_ids", "test_suite_ids", "test_case_version_ids", "carry_over_items"} & set(changes):
        carry_items = changes.get("carry_over_items", plan.get("carry_over_items", [])) or []
        scope = await validate_plan_scope(
            plan["project_id"],
            changes.get("requirement_version_ids", plan.get("requirement_version_ids", [])),
            changes.get("test_suite_ids", plan.get("test_suite_ids", [])),
            list(dict.fromkeys([
                *changes.get("test_case_version_ids", plan.get("test_case_version_ids", [])),
                *(item["test_case_version_id"] for item in carry_items),
            ])),
        )
        changes.update(scope)
    if {"owner_id", "scenario_ids"} & changes.keys():
        scenario_ids = await validate_plan_links(
            plan["project_id"],
            changes.get("owner_id", plan.get("owner_id")),
            changes.get("scenario_ids", plan.get("scenario_ids")),
        )
        if "scenario_ids" in changes:
            changes["scenario_ids"] = scenario_ids
    validation_data = {}
    for field in TestPlanCreate.model_fields:
        if field in changes:
            validation_data[field] = changes[field]
        elif field in plan:
            validation_data[field] = plan[field]
    TestPlanCreate.model_validate(validation_data)
    if plan.get("status") == 'READY' and not plan_completeness({**plan, **changes})["ready_for_approval"]:
        raise HTTPException(status_code=422, detail={"code": "TEST_PLAN_INCOMPLETE", "message": "Nhập mục tiêu và liên kết ít nhất một phiên bản yêu cầu trước khi lưu kế hoạch."})
    changes = content_authorship_changes(plan, user, changes)

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            period_ids = {
                value
                for value in (
                    existing_period_id,
                    changes.get("test_period_id", existing_period_id),
                )
                if value
            }
            for period_id in sorted(period_ids):
                await touch_open_test_period(plan["project_id"], period_id, session)
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
    return updated

async def submit_test_plan_record(plan_id, payload, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.submit_review")
    if plan.get("status") not in ('DRAFT', 'READY'):
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            if plan.get("test_period_id"):
                await touch_open_test_period(
                    plan["project_id"], plan["test_period_id"], session
                )
            updated = await optimistic_patch(
                "test_plans",
                plan_id,
                plan["project_id"],
                payload.expected_revision,
                {
                    "status": 'IN_REVIEW',
                    "review_note": payload.review_note,
                    "submitted_by": user.id,
                    "submitted_at": now(),
                },
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
    if await can_auto_approve_project_content(plan["project_id"], user):
        approval = payload.model_copy(update={"expected_revision": updated["revision"]})
        return await approve_test_plan_record(plan_id, approval, user)
    return updated

async def approve_test_plan_record(plan_id, payload, user):
    require_ai_publication_authority(user, 'testplan.approve')
    
    plan = await get_test_plan_record(plan_id, user, "testplan.approve")
    if plan.get("status") != 'IN_REVIEW':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    await require_independent_review(plan, user, "TEST_PLAN_SELF_REVIEW_FORBIDDEN")
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
    completeness = plan_completeness(plan)
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

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            if plan.get("test_period_id"):
                await touch_open_test_period(
                    plan["project_id"], plan["test_period_id"], session
                )
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
    return updated

async def request_test_plan_revision(plan_id, payload, user):
    plan = await get_test_plan_record(plan_id, user, 'testplan.review')
    if plan.get('status') != 'IN_REVIEW':
        raise HTTPException(409, detail={'code': 'INVALID_STATE_TRANSITION'})
    await require_independent_review(plan, user, 'TEST_PLAN_SELF_REVIEW_FORBIDDEN')
    if not payload.review_note.strip():
        raise HTTPException(422, detail={'code': 'TEST_PLAN_REVISION_REASON_REQUIRED'})
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            if plan.get("test_period_id"):
                await touch_open_test_period(
                    plan["project_id"], plan["test_period_id"], session
                )
            updated = await optimistic_patch(
                'test_plans', plan_id, plan['project_id'], payload.expected_revision,
                {'status': 'DRAFT', 'review_note': payload.review_note,
                 'approval_history': [*plan.get('approval_history', []),
                                      {'actor_id': user.id, 'action': 'CHANGES_REQUESTED', 'note': payload.review_note, 'at': now()}]},
                session=session,
            )
            await audit(user.id, 'test_plan_changes_requested', 'TestPlan', plan_id, plan['project_id'], session=session)
    return updated

async def archive_test_plan_record(plan_id, payload, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.archive")

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            if plan.get("test_period_id"):
                await touch_open_test_period(
                    plan["project_id"], plan["test_period_id"], session
                )
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
        "content_author_ids": [user.id],
        "content_authorship_status": "VERIFIED",
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

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            if cloned.get("test_period_id"):
                await touch_open_test_period(
                    plan["project_id"], cloned["test_period_id"], session
                )
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
    return cloned
