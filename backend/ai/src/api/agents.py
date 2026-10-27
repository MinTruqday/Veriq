from fastapi import APIRouter, Depends, HTTPException

from src.core.dependency import get_current_user, oauth2_scheme
from src.memory.short_term import run_store
from src.schemas.agent import AgentRunRequest
from src.schemas.auth import CurrentUser
from src.services.project_access import project_access
from src.tools.registry import registered_tools, tool_access

router = APIRouter(prefix="/tac-tu", tags=["AI Automation compatibility"])


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
        if not access or access.permission not in permissions or not tool.metadata.get("user_selectable"):
            continue
        capabilities.append({"name": access.name, "label": tool.metadata.get("label", access.name)})
    return sorted(capabilities, key=lambda item: item["label"])


@router.post("/luot-chay", status_code=201)
async def create_agent_run(
    payload: AgentRunRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    raise HTTPException(
        status_code=410,
        detail={"code": "DIRECT_AGENT_RUN_RETIRED", "replacement": "tu-dong-hoa-ai/noi-bo/su-kien"},
    )


@router.get("/luot-chay/{run_id}")
async def get_agent_run(
    run_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    if run.user_id != user.id and user.system_role.value != "ADMIN":
        _, permissions = await project_access(run.project_id, token)
        if "proposal.read" not in permissions:
            raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    return run
