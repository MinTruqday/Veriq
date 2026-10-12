import asyncio

from src.prompts.agents import agent_execution_prompt
from src.runtime.limits import limits
from src.schemas.agent import AgentResult, AgentTaskStatus, ToolExecutionStatus
from src.runtime.output import normalize_narrative, normalize_narratives
from src.services.inference import structured
from src.tools.registry import authorize_tool, invoke_tool


async def execute_task(task, evidence, permissions, token, approval_status=None):
    observations = []
    pending_actions = []
    errors = 0
    bounded_calls = task.tool_calls[: min(limits.tool_calls_per_task, limits.agent_steps)]
    for index, tool_call in enumerate(bounded_calls):
        decision = authorize_tool(task, tool_call.tool_name, permissions, approval_status)
        if decision.reason_code == "APPROVAL_REQUIRED":
            pending_actions.append({"task_id": task.task_id, **tool_call.model_dump()})
            continue
        try:
            observation = await asyncio.wait_for(
                invoke_tool(
                    task,
                    tool_call.tool_name,
                    tool_call.arguments,
                    permissions,
                    token,
                    approval_status,
                    [item.model_dump(mode="python") for item in evidence],
                ),
                timeout=limits.task_timeout_seconds,
            )
        except Exception as error:
            observation = {
                "status": ToolExecutionStatus.FAILED,
                "tool_name": tool_call.tool_name,
                "reason_code": type(error).__name__,
            }
        observations.append(observation)
        if observation.get("status") in {ToolExecutionStatus.FAILED, ToolExecutionStatus.DENIED}:
            errors += 1
        if errors >= limits.tool_errors:
            break
    try:
        result = await structured(
            agent_execution_prompt(
                task.model_dump(mode="json"),
                [item.model_dump(mode="json") for item in evidence],
                observations,
            ),
            AgentResult,
            max_tokens=1200,
            timeout_seconds=limits.task_timeout_seconds,
            provider_schema=True,
        )
        result.task_id = task.task_id
    except Exception:
        completed = [
            item for item in observations if item.get("status") == ToolExecutionStatus.COMPLETED
        ]
        result = AgentResult(
            task_id=task.task_id,
            status=(
                AgentTaskStatus.COMPLETED
                if completed or pending_actions
                else AgentTaskStatus.INSUFFICIENT_EVIDENCE
            ),
            summary="Tool observations collected" if completed else "Insufficient evidence",
            evidence_refs=[item.artifact_version_id or item.artifact_id for item in evidence],
            reason_codes=[item.get("reason_code", "TOOL_RESULT") for item in observations],
            proposals=pending_actions,
            warnings=["AI_PROVIDER_UNAVAILABLE"],
        )
    if pending_actions:
        result.proposals.extend(action for action in pending_actions if action not in result.proposals)
    completed_observations = [
        item for item in observations if item.get("status") == ToolExecutionStatus.COMPLETED
    ]
    if task.tool_calls and not completed_observations and not pending_actions:
        result.status = AgentTaskStatus.INSUFFICIENT_EVIDENCE
        result.reason_codes = list(dict.fromkeys([*result.reason_codes, "TOOL_FAILED"]))
    allowed_refs = {item.artifact_version_id or item.artifact_id for item in evidence}
    result.evidence_refs = [reference for reference in result.evidence_refs if reference in allowed_refs]
    if evidence and not result.evidence_refs:
        result.evidence_refs = [item.artifact_version_id or item.artifact_id for item in evidence]
    result.summary = normalize_narrative(result.summary)
    result.warnings = normalize_narratives(result.warnings)
    return result, observations
