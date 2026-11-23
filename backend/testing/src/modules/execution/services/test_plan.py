import hashlib
import json
import re

from fastapi import HTTPException
from pydantic import ValidationError

from src.core.ai_capabilities import ai_contract_metadata, request_ai_capability
from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    now,
    optimistic_patch,
    plain_text,
    sort_spec,
)
from src.core.database import database
from src.core.human_decisions import (
    content_authorship_changes,
    require_ai_publication_authority,
    require_independent_review,
)
from src.core.source_evidence import split_source_evidence
from src.modules.design.services.test_case_records import require_current_baselined_version
from src.modules.execution.services.execution_context import resolve_execution_context
from src.repositories.project import project_repository
from src.repositories.test_plan import test_plan_repository
from src.repositories.test_analysis import test_analysis_repository
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
    'project_id', 'name', 'objective', 'scope_in', 'scope_out',
    'requirement_version_ids', 'test_suite_ids', 'test_case_version_ids',
    'test_suite_snapshots', 'environment', 'environment_id',
    'entry_criteria', 'exit_criteria', 'test_types', 'members',
    'strategy_version_id', 'strategy_id', 'strategy_version', 'strategy_snapshot_hash',
    'test_level', 'test_approach',
    'assumptions', 'constraints', 'dependencies', 'estimation', 'schedule',
    'quality_targets', 'risk_register', 'communication_plan',
    'owner_id', 'scenario_ids',
)

def plan_snapshot(plan):
    snapshot = {field: plan.get(field) for field in PLAN_SNAPSHOT_FIELDS}
    for field in ("test_data_notes", "environment_notes"):
        if field in plan:
            snapshot[field] = plan[field]
    return snapshot

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
        for field in ('test_data_plan', 'defect_management', 'owner_id', 'scenario_ids')
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
        (
            'TEST_PLAN_APPROACH_REQUIRED',
            bool(str(plan.get('test_approach') or '').strip()),
        ),
        ('TEST_PLAN_OBJECTIVE_REQUIRED', bool(str(plan.get('objective') or '').strip())),
        ('TEST_PLAN_SCOPE_REQUIRED', any(str(item or '').strip() for item in (plan.get('scope_in') or []))),
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
    context = await resolve_execution_context(
        payload.project_id,
        user,
        environment_id=payload.environment_id,
        environment=payload.environment,
    )
    scenario_ids = await validate_plan_links(payload.project_id, payload.owner_id, payload.scenario_ids)
    await validate_effort_allocation_members(payload.project_id, payload.estimation)
    scope = await validate_plan_scope(
        payload.project_id,
        payload.requirement_version_ids,
        payload.test_suite_ids,
        payload.test_case_version_ids,
    )
    if not payload.save_as_draft:
        completeness = plan_completeness(payload.model_dump())
        if not completeness["ready_for_approval"]:
            raise HTTPException(status_code=422, detail={"code": "TEST_PLAN_INCOMPLETE", "message": "Nhập mục tiêu, phạm vi kiểm thử và cách tiếp cận trước khi lưu kế hoạch.", **completeness})
    timestamp = now()
    plan = {
        "_id": new_id('TP'),
        **payload.model_dump(exclude={"save_as_draft"}),
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
    return plan

async def list_test_plan_records(
    project_id,
    user,
    q="",
    environment_id="",
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
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "estimation" in changes:
        await validate_effort_allocation_members(
            plan["project_id"], TestPlanCreate.model_validate({**plan, **changes}).estimation
        )
    if {"environment_id", "environment"} & set(changes):
        environment_context = await resolve_execution_context(
            plan["project_id"],
            user,
            environment_id=changes.get("environment_id", plan.get("environment_id")),
            environment=changes.get("environment", plan.get("environment", "")),
        )
        changes.update(
            {
                "environment": environment_context["environment"],
                "environment_id": environment_context["environment_id"],
            }
        )
    if {"requirement_version_ids", "test_suite_ids", "test_case_version_ids"} & set(changes):
        scope = await validate_plan_scope(
            plan["project_id"],
            changes.get("requirement_version_ids", plan.get("requirement_version_ids", [])),
            changes.get("test_suite_ids", plan.get("test_suite_ids", [])),
            changes.get("test_case_version_ids", plan.get("test_case_version_ids", [])),
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
        raise HTTPException(status_code=422, detail={"code": "TEST_PLAN_INCOMPLETE", "message": "Nhập mục tiêu, phạm vi kiểm thử và cách tiếp cận trước khi lưu kế hoạch."})
    changes = content_authorship_changes(plan, user, changes)

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
    return updated

async def submit_test_plan_record(plan_id, payload, user):
    
    plan = await get_test_plan_record(plan_id, user, "testplan.submit_review")
    if plan.get("status") not in ('DRAFT', 'READY'):
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})

    async with await database.client.start_session() as session:
        async with session.start_transaction():
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

def validate_test_plan_ai_field_grounding(proposal, source_text):
    fields = (
        "objective", "scope_in", "scope_out", "test_approach",
    )
    field_evidence = {}
    unsupported_fields = []
    for item in proposal.get("field_evidence") or []:
        field_name = item.get("field")
        if field_name not in fields:
            continue
        if field_name in field_evidence:
            raise HTTPException(502, detail={"code": "TEST_PLAN_AI_FIELD_EVIDENCE_DUPLICATE"})
        quotes = item.get("evidence_quotes") or []
        grounded_quotes = []
        for quote in quotes:
            source = source_text.get(quote.get("evidence_ref"))
            text = str(quote.get("quote") or "").strip()
            if source and text and text in source:
                grounded_quotes.append(quote)
        if grounded_quotes:
            field_evidence[field_name] = grounded_quotes
        else:
            unsupported_fields.append(field_name)
    for field_name in fields:
        value = proposal.get(field_name)
        has_value = (
            any(str(item or "").strip() for item in value)
            if isinstance(value, list)
            else bool(str(value or "").strip())
        )
        if has_value and field_name not in field_evidence:
            proposal[field_name] = [] if isinstance(value, list) else ""
            unsupported_fields.append(field_name)
        elif not has_value and field_name in field_evidence:
            field_evidence.pop(field_name, None)
    proposal["field_evidence"] = [
        {"field": field_name, "evidence_quotes": quotes}
        for field_name, quotes in field_evidence.items()
    ]
    # Keep the response schema compatible while returning only the concise
    # project-plan fields supported by Requirement evidence.
    for field_name in (
        "test_level", "test_types", "environment", "entry_criteria",
        "exit_criteria", "risks", "assumptions", "constraints",
    ):
        proposal[field_name] = [] if isinstance(proposal.get(field_name), list) else ""
    return list(dict.fromkeys(unsupported_fields))

async def generate_test_plan_draft_suggestion(project_id, payload, user):
    from src.modules.design.services.test_case_records import require_current_design_source

    await get_project(project_id, user, "testplan.create")
    requirement_ids = list(dict.fromkeys(payload.requirement_version_ids))
    if len(requirement_ids) != len(payload.requirement_version_ids):
        raise HTTPException(422, detail={"code": "DUPLICATE_REQUIREMENT_VERSION"})
    allowed_statuses = ["READY", "BASELINED"]
    if getattr(user, "_ai_capability_intent", "") == "process_ingested_requirement_document":
        allowed_statuses.append("DRAFT")
    versions = await database.value.requirement_versions.find({
        "project_id": project_id,
        "_id": {"$in": requirement_ids},
        "status": {"$in": allowed_statuses},
    }).to_list(len(requirement_ids))
    if len(versions) != len(requirement_ids):
        raise HTTPException(422, detail={"code": "TEST_PLAN_REQUIREMENT_NOT_BASELINED"})
    for version in versions:
        await require_current_design_source(version, user)
    criteria = await database.value.acceptance_criteria.find({
        "project_id": project_id,
        "requirement_version_id": {"$in": requirement_ids},
    }).to_list(1001)
    if len(criteria) > 1000:
        raise HTTPException(422, detail={"code": "TEST_PLAN_ACCEPTANCE_CRITERIA_LIMIT_EXCEEDED"})
    evidence = []
    source_text = {}
    for version in versions:
        content = str(version.get("plain_text_projection") or plain_text(version.get("content_doc", {}))).strip()
        if not content:
            raise HTTPException(422, detail={"code": "TEST_PLAN_REQUIREMENT_CONTENT_EMPTY"})
        evidence.extend(split_source_evidence("requirement_version", version["_id"], content))
        source_text[version["_id"]] = content
    for criterion in criteria:
        content = str(criterion.get("plain_text") or plain_text(criterion.get("content_doc", {}))).strip()
        if content:
            evidence.extend(split_source_evidence("acceptance_criterion", criterion["_id"], content))
            source_text[criterion["_id"]] = content
    current_plan = payload.current_test_plan
    if len(json.dumps(current_plan, ensure_ascii=False)) > 12000:
        raise HTTPException(422, detail={"code": "TEST_PLAN_DRAFT_CONTEXT_LIMIT_EXCEEDED"})
    draft_text = "\n".join(
        str(value).strip()
        for value in current_plan.values()
        if isinstance(value, (str, int, float)) and str(value).strip()
    )
    for field_name, value in current_plan.items():
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            if serialized not in draft_text:
                draft_text = "\n".join(part for part in (draft_text, serialized) if part)
    if draft_text:
        evidence.extend(
            split_source_evidence("user_authored_test_plan_draft", "USER_DRAFT", draft_text)
        )
        source_text["USER_DRAFT"] = draft_text
    if not evidence:
        raise HTTPException(422, detail={"code": "TEST_PLAN_EVIDENCE_REQUIRED"})
    if len(evidence) > 100:
        raise HTTPException(422, detail={"code": "TEST_PLAN_EVIDENCE_LIMIT_EXCEEDED"})
    ai_instruction = json.dumps({
        "user_instruction": payload.instruction,
        "current_test_plan_draft": current_plan,
        "consistency_rules": [
            "Suggest only objective, included/excluded scope, and test approach when directly supported by the supplied Requirement evidence.",
            "Do not propose risk register entries, priority, dates, effort, people, environment, quality targets, or generic planning boilerplate. These are project decisions, not facts inferred from Requirement text.",
            "Use only the exact requirement versions, acceptance criteria, and current draft supplied in this request.",
            "Use the current Test Plan draft as context for suggestions. Preserve entered values unless the user explicitly applies a field suggestion.",
            "If sources disagree and none explicitly establishes which value governs, report the conflict and ask for clarification; do not silently choose a side or assume the Test Plan is wrong.",
        ],
    }, ensure_ascii=False)
    result = await request_ai_capability(
        "test_plan_draft_generation", project_id, ai_instruction, evidence
    )
    if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
        raise HTTPException(503, detail={"code": "AI_PROVIDER_UNAVAILABLE", "retryable": True})
    suggestions = result.get("suggestions") or []
    if len(suggestions) != 1:
        raise HTTPException(502, detail={"code": "TEST_PLAN_AI_RESPONSE_INVALID"})
    if set(result.get("evidence_refs") or []) - set(source_text):
        raise HTTPException(502, detail={"code": "TEST_PLAN_AI_EVIDENCE_REFERENCE_INVALID"})
    proposal = suggestions[0]
    unsupported_fields = validate_test_plan_ai_field_grounding(proposal, source_text)
    valid_evidence_quotes = []
    for quote in proposal.get("evidence_quotes") or []:
        source = source_text.get(quote.get("evidence_ref"))
        quote_text = str(quote.get("quote") or "").strip()
        if source and quote_text and quote_text in source:
            valid_evidence_quotes.append(quote)
    proposal["evidence_quotes"] = valid_evidence_quotes
    if unsupported_fields:
        warnings = list(proposal.get("warnings") or [])
        warnings.append(
            "Một số trường chưa có trích dẫn khớp nguồn nên đã được để trống: "
            + ", ".join(unsupported_fields)
        )
        proposal["warnings"] = list(dict.fromkeys(warnings))
    if not any(
        any(str(item or "").strip() for item in value)
        if isinstance(value, list)
        else bool(str(value or "").strip())
        for field_name, value in proposal.items()
        if field_name in {
            "objective", "scope_in", "scope_out", "test_approach",
        }
    ):
        raise HTTPException(502, detail={"code": "TEST_PLAN_AI_NO_GROUNDED_FIELDS"})
    await get_project(project_id, user, "testplan.create")
    latest_versions = await database.value.requirement_versions.find({
        "project_id": project_id,
        "_id": {"$in": requirement_ids},
        "status": {"$in": allowed_statuses},
    }).to_list(len(requirement_ids))
    if len(latest_versions) != len(requirement_ids):
        raise HTTPException(409, detail={"code": "TEST_PLAN_SOURCE_CHANGED", "retryable": True})
    for version in latest_versions:
        await require_current_design_source(version, user)
    latest_criteria = await database.value.acceptance_criteria.find({
        "project_id": project_id,
        "requirement_version_id": {"$in": requirement_ids},
    }).to_list(1001)
    if len(latest_criteria) > 1000:
        raise HTTPException(409, detail={"code": "TEST_PLAN_SOURCE_CHANGED", "retryable": True})
    latest_source_text = {}
    for version in latest_versions:
        content = str(version.get("plain_text_projection") or plain_text(version.get("content_doc", {}))).strip()
        if content:
            latest_source_text[version["_id"]] = content
    for criterion in latest_criteria:
        content = str(criterion.get("plain_text") or plain_text(criterion.get("content_doc", {}))).strip()
        if content:
            latest_source_text[criterion["_id"]] = content
    if draft_text:
        latest_source_text["USER_DRAFT"] = draft_text
    if latest_source_text != source_text:
        raise HTTPException(409, detail={"code": "TEST_PLAN_SOURCE_CHANGED", "retryable": True})
    return {
        "project_id": project_id,
        "requirement_version_ids": requirement_ids,
        "suggestion": proposal,
        "evidence": [
            {"artifact_type": item["artifact_type"], "artifact_version_id": item["artifact_version_id"]}
            for item in evidence
        ],
        **ai_contract_metadata(result),
        "saved": False,
        "approved": False,
    }
