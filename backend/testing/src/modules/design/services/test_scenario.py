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
    sort_spec,
)
from src.repositories.test_design import test_design_repository
from src.core.ai_automation import ai_contract_metadata, require_ai_automation_event
from src.modules.design.services.generation import generate_requirement_drafts, select_generation_criteria
from src.modules.design.services.test_case_records import validate_design_sources





async def create_test_scenario_record(project_id, payload, user):
    await get_project(project_id, user, "testscenario.create")
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
    scenario = await get_project_entity("test_scenarios", scenario_id, user, "testscenario.update")
    if scenario.get("status") != "draft":
        raise HTTPException(
            status_code=409, detail={"code": 'IMMUTABLE_SCENARIO'}
        )
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
        payload.model_dump(),
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
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
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
    await audit(user.id, "test_scenario_archived", "TestScenario", scenario_id, scenario["project_id"])
    return updated


async def generate_test_scenario_records(version_id, payload, user):
    require_ai_automation_event(
        user,
        {"DOCUMENT_INGESTED", "REQUIREMENT_BASELINED", "REQUIREMENT_CHANGED"},
    )
    version = await get_project_entity(
        "requirement_versions", version_id, user, "ai.generate_scenario"
    )
    await get_project(version["project_id"], user, "testscenario.create")
    criteria = await test_design_repository.list_acceptance_criteria(version_id)
    criteria = select_generation_criteria(criteria, payload.acceptance_criterion_ids)
    drafts, result = await generate_requirement_drafts(version, criteria, payload, scenario=True)
    created = [
        await create_test_scenario_record(version["project_id"], draft, user) for draft in drafts
    ]
    await audit(
        user.id,
        "scenario_drafts_generated",
        "RequirementVersion",
        version_id,
        version["project_id"],
        {"count": len(created), "model": result.get("model", {})},
    )
    return {
        "items": created,
        "evidence": criteria,
        **ai_contract_metadata(result),
        "generation_status": result["status"],
    }
