from fastapi import APIRouter, Depends, HTTPException

from src.core.dependency import get_current_user, oauth2_scheme
from src.repositories.automation import automation_repository
from src.schemas.agent import AgentRunRequest
from src.schemas.auth import CurrentUser
from src.services.project_access import project_access
from src.services.automation import automation_service
from src.tools.registry import registered_tools, requires_human_decision, tool_access

router = APIRouter(prefix="/tac-tu", tags=["AI Agent"])


@router.get("/du-an/{project_id}/nang-luc")
async def list_agent_capabilities(
    project_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    _, permissions = await project_access(project_id, token)
    capabilities = []
    for tool in registered_tools().values():
        access = tool_access(tool)
        if not access or requires_human_decision(access.permission) or (access.action == "MUTATE" and not access.draft_only) or access.permission not in permissions or not tool.metadata.get("user_selectable"):
            continue
        capabilities.append({"name": access.name, "label": tool.metadata.get("label", access.name)})
    return sorted(capabilities, key=lambda item: item["label"])


@router.post("/luot-chay", status_code=201)
async def create_agent_run(
    payload: AgentRunRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    role, permissions = await project_access(payload.project_id, token)
    if any(item.project_id != payload.project_id for item in payload.evidence):
        raise HTTPException(status_code=422, detail={"code": "AGENT_EVIDENCE_PROJECT_MISMATCH"})
    return await automation_service.create_user_run(payload, user.id, role, permissions)


@router.get("/luot-chay/{run_id}")
async def get_agent_run(
    run_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await automation_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    if run.requester_user_id != user.id and user.system_role.value != "ADMIN":
        _, permissions = await project_access(run.project_id, token)
        if "proposal.read" not in permissions:
            raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    return run
