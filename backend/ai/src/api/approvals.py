import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.agents.runner.graph import canonical_workflow
from src.core.dependency import get_current_user, oauth2_scheme
from src.memory.long_term import long_term_memory
from src.memory.short_term import run_store
from src.runtime.limits import limits
from src.schemas.agent import (
    AgentApprovalStatus,
    AgentRunStatus,
    AgentTask,
    ApprovalDecision,
    VeriqRunState,
)
from src.schemas.auth import CurrentUser
from src.services.agent_metrics import agentops
from src.services.project_access import project_access
from src.services.token_accounting import current_usage, start_accounting
from src.tools.registry import authorize_tool, registered_tools


router = APIRouter(prefix="/tac-tu", tags=["AI Automation approval compatibility"])


@router.post("/luot-chay/{run_id}/quyet-dinh")
async def decide_agent_run(
    run_id: str,
    payload: ApprovalDecision,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    if run.status != AgentRunStatus.APPROVAL_REQUIRED:
        raise HTTPException(status_code=409, detail={"code": "APPROVAL_NOT_REQUIRED"})
    if run.revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": "REVISION_CONFLICT", "current_revision": run.revision},
        )
    role, permissions = await project_access(run.project_id, token)
    run.role = role
    run.permissions = permissions
    tasks = {item["task_id"]: item for item in run.execution_plan}
    actions = (run.proposal or {}).get("actions", [])
    if payload.decision == "EDIT":
        if not payload.action_edits:
            raise HTTPException(status_code=422, detail={"code": "PROPOSAL_EDIT_REQUIRED"})
        action_indexes = {
            (action.get("task_id"), action.get("tool_name")): index
            for index, action in enumerate(actions)
        }
        edited_actions = [dict(action) for action in actions]
        tools = registered_tools()
        for edit in payload.action_edits:
            key = (edit.task_id, edit.tool_name)
            index = action_indexes.get(key)
            raw_task = tasks.get(edit.task_id)
            tool = tools.get(edit.tool_name)
            if index is None or not raw_task or not tool:
                raise HTTPException(status_code=409, detail={"code": "PROPOSAL_ACTION_INVALID"})
            task = AgentTask(**raw_task)
            decision = authorize_tool(
                task,
                edit.tool_name,
                permissions,
                AgentApprovalStatus.APPROVED,
            )
            if not decision.allowed:
                raise HTTPException(status_code=403, detail={"code": decision.reason_code})
            if (
                "project_id" in edit.arguments
                and str(edit.arguments["project_id"]) != run.project_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail={"code": "PROJECT_SCOPE_VIOLATION"},
                )
            try:
                arguments = tool.args_schema.model_validate(edit.arguments).model_dump(
                    mode="python", exclude_unset=True
                )
            except Exception as error:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "TOOL_ARGUMENT_INVALID"},
                ) from error
            edited_actions[index]["arguments"] = arguments
        run.proposal = {**(run.proposal or {}), "actions": edited_actions}
        run.approval_decision = {
            "decision": "EDIT",
            "note": payload.note,
            "user_id": user.id,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        }
        run.observations.append({"phase": "APPROVAL", **run.approval_decision})
        run.revision += 1
        await run_store.save(run)
        return run
    if payload.decision == "APPROVE":
        for action in actions:
            raw_task = tasks.get(action.get("task_id"))
            if not raw_task:
                raise HTTPException(status_code=409, detail={"code": "TASK_NOT_FOUND"})
            decision = authorize_tool(
                AgentTask(**raw_task),
                action.get("tool_name", ""),
                permissions,
                AgentApprovalStatus.APPROVED,
            )
            if not decision.allowed:
                raise HTTPException(status_code=403, detail={"code": decision.reason_code})
    elif "proposal.reject" not in permissions:
        raise HTTPException(status_code=403, detail={"code": "PERMISSION_DENIED"})
    run.approval_status = (
        AgentApprovalStatus.APPROVED
        if payload.decision == "APPROVE"
        else AgentApprovalStatus.REJECTED
    )
    run.approval_decision = {
        "decision": payload.decision,
        "note": payload.note,
        "user_id": user.id,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "proposal": run.proposal if payload.decision == "REJECT" else None,
    }
    run.observations.append({"phase": "APPROVAL", **run.approval_decision})
    run.revision += 1
    start_accounting()
    agentops.record_session_start(run.run_id, user.id)
    try:
        result = await asyncio.wait_for(
            canonical_workflow.ainvoke(
                {
                    "run": run.model_dump(mode="python"),
                    "token": f"Bearer {token}",
                    "evidence": [],
                    "tasks": run.execution_plan,
                    "results": run.agent_results,
                    "success_criteria": (run.proposal or {}).get("success_criteria_met", []),
                }
            ),
            timeout=limits.run_timeout_seconds,
        )
    except TimeoutError:
        run.status = AgentRunStatus.FAILED
        run.error_code = "AGENT_LIMIT_REACHED"
        run.observations.append({"phase": "RESUME", "reason_code": "AGENT_LIMIT_REACHED"})
        previous_usage = run.token_usage
        resumed_usage = current_usage()
        run.token_usage = {
            key: int(previous_usage.get(key, 0)) + int(resumed_usage.get(key, 0))
            for key in set(previous_usage) | set(resumed_usage)
        }
        await run_store.save(run)
        agentops.record_session_end(run.run_id, "failed")
        return run
    completed = VeriqRunState(**result["run"])
    resumed_usage = current_usage()
    completed.token_usage = {
        key: int(run.token_usage.get(key, 0)) + int(resumed_usage.get(key, 0))
        for key in set(run.token_usage) | set(resumed_usage)
    }
    await run_store.save(completed)
    if completed.status == AgentRunStatus.COMPLETED:
        await long_term_memory.record_verified(completed)
    agentops.record_session_end(
        completed.run_id,
        "done" if completed.status == AgentRunStatus.COMPLETED else "failed",
    )
    return completed
