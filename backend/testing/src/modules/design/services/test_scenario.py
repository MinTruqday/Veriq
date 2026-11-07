import re

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    next_key,
    now,
    optimistic_patch,
    plain_text,
    sort_spec,
)
from src.core.database import database
from src.core.sensitive_data import redact_sensitive_text
from src.clients.project_knowledge import index_artifact, remove_artifact
from src.repositories.test_design import test_design_repository
from src.core.human_decisions import require_automation_publication_authority
from src.core.human_decisions import require_independent_review
from src.core.human_decisions import content_authorship_changes
from src.modules.design.services.design_authorization import require_assigned_design_draft
from src.core.ai_automation import ai_contract_metadata
from src.modules.design.services.generation import generate_requirement_drafts, select_generation_criteria
from src.modules.design.services.test_case_records import validate_design_sources, validate_test_case_owner, require_current_baselined_version


def scenario_search_text(scenario):
    fields = (
        scenario.get("scenario_key"),
        scenario.get("title"),
        scenario.get("objective"),
        scenario.get("description"),
        scenario.get("actors"),
        scenario.get("preconditions"),
        scenario.get("business_flow"),
        scenario.get("expected_outcome"),
        scenario.get("test_data_notes"),
        scenario.get("tags"),
    )
    values = []
    for field in fields:
        if isinstance(field, list):
            values.extend(str(value) for value in field if str(value or "").strip())
        elif str(field or "").strip():
            values.append(str(field).strip())
    return redact_sensitive_text("\n".join(values))


async def index_approved_scenario(scenario):
    text = scenario_search_text(scenario)
    indexed = False
    if text:
        try:
            indexed = await index_artifact(
                scenario["project_id"],
                "test_scenario",
                scenario["_id"],
                scenario["_id"],
                scenario.get("title") or scenario.get("scenario_key") or "Kịch bản kiểm thử",
                text,
                "approved",
                "APPROVED_SOURCE",
                scenario.get("revision", 1),
                module=scenario.get("category") or "",
                scenario_key=scenario.get("scenario_key"),
                risk=scenario.get("risk"),
                priority=scenario.get("priority"),
                test_level=scenario.get("test_level"),
                test_kind=scenario.get("test_kind"),
                linked_requirement_version_ids=scenario.get("requirement_version_ids") or [],
                linked_acceptance_criterion_ids=scenario.get("acceptance_criterion_ids") or [],
                linked_test_condition_ids=scenario.get("test_condition_ids") or [],
            )
        except Exception:
            indexed = False
    status = "INDEXED" if indexed else "INDEX_PENDING"
    await database.value.test_scenarios.update_one(
        {"_id": scenario["_id"], "project_id": scenario["project_id"], "revision": scenario.get("revision", 1), "status": "approved"},
        {"$set": {"index_status": status}},
    )
    return status





async def create_test_scenario_record(project_id, payload, user):
    await get_project(project_id, user, "testscenario.create")
    if payload.status != 'draft':
        raise HTTPException(422, detail={"code": "SCENARIO_DRAFT_REQUIRED"})
    await validate_test_case_owner(project_id, payload.owner_id)
    await validate_design_sources(
        project_id,
        payload.requirement_version_ids,
        payload.acceptance_criterion_ids,
        test_condition_ids=payload.test_condition_ids,
    )
    scenario = {
        "_id": new_id('TS'),
        "project_id": project_id,
        **payload.model_dump(),
        "scenario_key": payload.scenario_key
        or await next_key(
            project_id,
            'scenario',
            'TS',
        ),
        "revision": 1,
        "created_by": user.id,
        "content_author_ids": [user.id],
        "content_authorship_status": "VERIFIED",
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        await test_design_repository.insert_scenario(scenario)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, detail={"code": 'SCENARIO_KEY_EXISTS'}
        )
    await audit(user.id, "test_scenario_created", "TestScenario", scenario["_id"], project_id)
    return scenario


async def create_test_scenario_draft_batch(project_id, payloads, user):
    await get_project(project_id, user, "testscenario.create")
    if not payloads or len(payloads) > 100:
        raise HTTPException(422, detail={"code": "SCENARIO_BATCH_SIZE_INVALID"})
    scenarios = []
    for payload in payloads:
        if payload.status != "draft":
            raise HTTPException(422, detail={"code": "SCENARIO_DRAFT_REQUIRED"})
        await validate_test_case_owner(project_id, payload.owner_id)
        await validate_design_sources(
            project_id,
            payload.requirement_version_ids,
            payload.acceptance_criterion_ids,
            test_condition_ids=payload.test_condition_ids,
        )
        for version_id in payload.requirement_version_ids:
            version = await get_project_entity(
                "requirement_versions", version_id, user, "requirement.read"
            )
            await require_current_baselined_version(version)
        scenarios.append({
            "_id": new_id("TS"),
            "project_id": project_id,
            **payload.model_dump(),
            "scenario_key": payload.scenario_key or await next_key(project_id, "scenario", "TS"),
            "revision": 1,
            "created_by": user.id,
            "content_author_ids": [user.id],
            "content_authorship_status": "VERIFIED",
            "created_at": now(),
            "updated_at": now(),
        })
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await test_design_repository.insert_scenarios(scenarios, session=session)
                for scenario in scenarios:
                    await audit(
                        user.id, "test_scenario_created", "TestScenario",
                        scenario["_id"], project_id, session=session,
                    )
    except DuplicateKeyError as error:
        raise HTTPException(409, detail={"code": "SCENARIO_KEY_EXISTS"}) from error
    return scenarios


async def list_test_scenario_records(
    project_id, user, q="", status="", category="", risk="", sort="-updated_at", limit=100
):
    await get_project(project_id, user, "testscenario.read")
    query = {"project_id": project_id}
    if q:
        query["$or"] = [
            {"scenario_key": {"$regex": re.escape(q), "$options": "i"}},
            {"title": {"$regex": re.escape(q), "$options": "i"}},
        ]
    for field, value in {"status": status, "category": category, "risk": risk}.items():
        if value:
            query[field] = value
    sort_field, direction = sort_spec(
        sort, set(['scenario_key', 'title', 'category', 'risk', 'status', 'created_at', 'updated_at'])
    )
    return await test_design_repository.list_scenarios(
        query, sort_field, direction, limit
    )


async def get_test_scenario_record(scenario_id, user):
    scenario = await get_project_entity("test_scenarios", scenario_id, user, "testscenario.read")
    cases = await test_design_repository.list_scenario_cases(
        scenario["project_id"], scenario_id
    )
    return {**scenario, "test_cases": cases}


async def update_test_scenario_record(scenario_id, payload, user):
    changes = payload.model_dump(exclude_unset=True)
    scenario = await require_assigned_design_draft("test_scenarios", scenario_id, user, "testscenario.update", changes)
    if scenario.get("status") != "draft":
        raise HTTPException(
            status_code=409, detail={"code": 'IMMUTABLE_SCENARIO'}
        )
    if payload.owner_id is not None:
        await validate_test_case_owner(scenario["project_id"], payload.owner_id)
    await validate_design_sources(
        scenario["project_id"],
        payload.requirement_version_ids
        if payload.requirement_version_ids is not None
        else scenario.get("requirement_version_ids", []),
        payload.acceptance_criterion_ids
        if payload.acceptance_criterion_ids is not None
        else scenario.get("acceptance_criterion_ids", []),
        test_condition_ids=payload.test_condition_ids
        if payload.test_condition_ids is not None
        else scenario.get("test_condition_ids", []),
    )
    updated = await optimistic_patch(
        "test_scenarios",
        scenario_id,
        scenario["project_id"],
        payload.expected_revision,
        {**changes, **content_authorship_changes(scenario, user, changes)},
    )
    await audit(user.id, "test_scenario_updated", "TestScenario", scenario_id, scenario["project_id"])
    return updated


async def clone_test_scenario_record(scenario_id, user):
    scenario = await get_project_entity("test_scenarios", scenario_id, user, "testscenario.clone")
    timestamp = now()
    cloned = {
        **scenario,
        "_id": new_id('TS'),
        "scenario_key": await next_key(
            scenario["project_id"],
            'scenario',
            'TS',
        ),
        "title": f"{scenario['title']} bản sao",
        "status": "draft",
        "origin": "manual",
        "review_history": [],
        "review_note": "",
        "revision": 1,
        "created_by": user.id,
        "content_author_ids": [user.id],
        "content_authorship_status": "VERIFIED",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    cloned.pop("index_status", None)
    await test_design_repository.insert_scenario(cloned)
    await audit(
        user.id,
        "test_scenario_cloned",
        "TestScenario",
        cloned["_id"],
        scenario["project_id"],
        {"source_scenario_id": scenario_id},
    )
    return cloned


async def archive_test_scenario_record(scenario_id, payload, user):
    scenario = await get_project_entity("test_scenarios", scenario_id, user, "testscenario.archive")
    updated = await optimistic_patch(
        "test_scenarios",
        scenario_id,
        scenario["project_id"],
        payload.expected_revision,
        {
            "status": "archived",
            "archive_reason": payload.reason,
            "archived_by": user.id,
            "archived_at": now(),
        },
    )
    removed = await remove_artifact(scenario["project_id"], scenario_id)
    index_status = "REMOVED" if removed else "REMOVE_PENDING"
    await database.value.test_scenarios.update_one(
        {"_id": scenario_id, "project_id": scenario["project_id"], "revision": updated.get("revision")},
        {"$set": {"index_status": index_status}},
    )
    updated["index_status"] = index_status
    await audit(user.id, "test_scenario_archived", "TestScenario", scenario_id, scenario["project_id"])
    return updated


async def generate_test_scenario_records(version_id, payload, user):
    if not payload.preview_only:
        raise HTTPException(
            422,
            detail={"code": "SCENARIO_PREVIEW_REQUIRED", "message": "Cần xem trước và chọn kịch bản trước khi lưu"},
        )
    version = await get_project_entity(
        "requirement_versions", version_id, user, "ai.generate_scenario"
    )
    await get_project(version["project_id"], user, "testscenario.create")
    await require_current_baselined_version(version)
    criteria = await test_design_repository.list_acceptance_criteria(version_id)
    criteria = select_generation_criteria(criteria, payload.acceptance_criterion_ids)
    drafts, result = await generate_requirement_drafts(version, criteria, payload, scenario=True)
    await require_current_baselined_version(version)
    current_criteria = select_generation_criteria(
        await test_design_repository.list_acceptance_criteria(version_id),
        payload.acceptance_criterion_ids,
    )
    if sorted((item["_id"], item.get("plain_text") or plain_text(item.get("content_doc", {}))) for item in current_criteria) != sorted(
        (item["_id"], item.get("plain_text") or plain_text(item.get("content_doc", {}))) for item in criteria
    ):
        raise HTTPException(409, detail={"code": "SCENARIO_PREVIEW_STALE"})
    created = [{"draft": item.model_dump()} for item in drafts]
    return {
        "items": created,
        "evidence": criteria,
        **ai_contract_metadata(result),
        "generation_status": result["status"],
    }


async def transition_test_scenario_record(scenario_id, payload, user, action):
    if action == "submit":
        scenario = await require_assigned_design_draft('test_scenarios', scenario_id, user, 'testscenario.update')
    else:
        scenario = await get_project_entity('test_scenarios', scenario_id, user, 'testscenario.update')
    transitions = {
        'submit': ('draft', 'in_review'),
        'approve': ('in_review', 'approved'),
        'revise': ('in_review', 'draft'),
    }
    previous, target = transitions[action]
    if scenario.get('status') != previous:
        raise HTTPException(409, detail={'code': 'INVALID_STATE_TRANSITION'})
    if action in {'approve', 'revise'}:
        require_independent_review(scenario, user, 'TEST_SCENARIO_SELF_REVIEW_FORBIDDEN')
    if action == 'approve':
        require_automation_publication_authority(user, 'testscenario.update')
        if not scenario.get('objective') or not scenario.get('requirement_version_ids'):
            raise HTTPException(409, detail={'code': 'SCENARIO_INCOMPLETE'})
        await validate_design_sources(
            scenario['project_id'], scenario.get('requirement_version_ids', []),
            scenario.get('acceptance_criterion_ids', []),
            test_condition_ids=scenario.get('test_condition_ids', []),
        )
        for version_id in scenario['requirement_version_ids']:
            version = await get_project_entity('requirement_versions', version_id, user, 'requirement.read')
            await require_current_baselined_version(version)
        await validate_test_case_owner(scenario['project_id'], scenario.get('owner_id'))
    changes = {'status': target, 'review_note': payload.review_note,
               'review_history': [*scenario.get('review_history', []),
                                  {'action': action, 'actor_id': user.id, 'note': payload.review_note, 'at': now()}]}
    if action == 'submit':
        changes['submitted_by'] = user.id
        changes['submitted_at'] = now()
    updated = await optimistic_patch(
        'test_scenarios', scenario_id, scenario['project_id'], payload.expected_revision,
        changes,
    )
    if action == "approve":
        updated["index_status"] = await index_approved_scenario(updated)
    await audit(user.id, f'test_scenario_{action}', 'TestScenario', scenario_id, scenario['project_id'])
    return updated
