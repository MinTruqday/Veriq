from fastapi import HTTPException

from src.core.common import get_project, get_project_entity


async def require_assigned_design_draft(collection, artifact_id, user, permission, proposed_changes=None):
    artifact = await get_project_entity(
        collection, artifact_id, user, permission,
        assigned_user_field="owner_id",
    )
    if (
        proposed_changes
        and "owner_id" in proposed_changes
        and proposed_changes["owner_id"] != artifact.get("owner_id")
    ):
        await get_project(artifact["project_id"], user, "project.members.read")
    return artifact


async def require_test_case_creation_scope(project_id, payload, user):
    if not payload.scenario_id:
        await get_project(project_id, user, "testcase.create")
        return payload
    scenario = await get_project_entity("test_scenarios", payload.scenario_id, user, "testscenario.read")
    if scenario["project_id"] != project_id:
        raise HTTPException(403, detail={"code": "DESIGN_ASSIGNMENT_REQUIRED"})
    if scenario.get("status") == "archived":
        raise HTTPException(409, detail={"code": "IMMUTABLE_SCENARIO"})
    await get_project(
        project_id,
        user,
        "testcase.create",
        assigned_user_id=scenario.get("owner_id"),
    )
    if scenario.get("owner_id") == user.id:
        if payload.owner_id not in {None, user.id}:
            raise HTTPException(403, detail={"code": "DESIGN_REASSIGNMENT_DENIED"})
        return payload.model_copy(update={"owner_id": user.id})
    return payload
