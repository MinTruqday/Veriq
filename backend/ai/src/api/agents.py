import asyncio
from fastapi import APIRouter, Depends, HTTPException

from src.agents.runner.graph import canonical_workflow
from src.core.dependency import get_current_user, oauth2_scheme
from src.memory.long_term import long_term_memory
from src.memory.short_term import run_store
from src.runtime.limits import limits
from src.schemas.agent import AgentRunRequest, AgentRunStatus, VeriqRunState
from src.schemas.auth import CurrentUser
from src.services.agent_metrics import agentops
from src.services.inference import model_metadata
from src.services.project_access import project_access
from src.services.token_accounting import current_usage, start_accounting
from src.tools.registry import registered_tools, tool_access


router = APIRouter(prefix="/tac-tu", tags=["Tác tử kiểm thử"])


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
    role, permissions = await project_access(payload.project_id, token)
    run = VeriqRunState(
        project_id=payload.project_id,
        user_id=user.id,
        role=role,
        permissions=permissions,
        objective=payload.objective,
        intent=payload.intent,
        model_metadata=model_metadata(),
    )
    start_accounting()
    agentops.record_session_start(run.run_id, user.id)
    try:
        result = await asyncio.wait_for(
            canonical_workflow.ainvoke(
                {
                    "run": run.model_dump(mode="python"),
                    "token": f"Bearer {token}",
                    "evidence": [item.model_dump(mode="python") for item in payload.evidence],
                    "target_artifact_ids": payload.target_artifact_ids,
                    "constraints": payload.constraints,
                    "tasks": [],
                    "results": [],
                }
            ),
            timeout=limits.run_timeout_seconds,
        )
    except TimeoutError:
        run.status = AgentRunStatus.FAILED
        run.error_code = "AGENT_LIMIT_REACHED"
        run.observations.append({"phase": "RUN", "reason_code": "AGENT_LIMIT_REACHED"})
        run.token_usage = current_usage()
        await run_store.save(run)
        agentops.record_session_end(run.run_id, "failed")
        return run
    completed = VeriqRunState(**result["run"])
    completed.token_usage = current_usage()
    await run_store.save(completed)
    if completed.status == AgentRunStatus.COMPLETED:
        await long_term_memory.record_verified(completed)
    agentops.record_session_end(
        completed.run_id,
        "done"
        if completed.status
        in {AgentRunStatus.COMPLETED, AgentRunStatus.APPROVAL_REQUIRED}
        else "failed",
    )
    return completed


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
