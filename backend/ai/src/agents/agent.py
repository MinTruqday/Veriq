import asyncio
import re
from fastapi import HTTPException

from src.prompts.agents import agent_execution_prompt
from src.runtime.limits import limits
from src.schemas.agent import AgentResult, AgentTaskStatus, ToolExecutionStatus
from src.runtime.output import normalize_narrative, normalize_narratives
from src.services.inference import structured
from src.tools.registry import authorize_tool, invoke_tool


def execution_error_code(error):
    code = getattr(error, "reason_code", None)
    if code:
        return str(code)
    if not isinstance(error, HTTPException):
        return type(error).__name__.upper()
    detail = error.detail
    if isinstance(detail, dict):
        code = detail.get("code")
        return str(code) if isinstance(code, str) and code else "HTTP_EXCEPTION"
    if isinstance(detail, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,119}", detail):
        return detail.upper().replace("-", "_")
    return "HTTP_EXCEPTION"


async def execute_task(
    task, evidence, permissions, token, automation_run_id=None, automatic=False,
    checkpoint_action=None,
):
    observations = []
    errors = 0
    bounded_calls = task.tool_calls[: min(limits.tool_calls_per_task, limits.agent_steps)]
    for index, tool_call in enumerate(bounded_calls):
        decision = authorize_tool(task, tool_call.tool_name, permissions)
        try:
            if checkpoint_action:
                await checkpoint_action(
                    tool_call.tool_name,
                    index,
                    decision.access.action if decision.access else "UNKNOWN",
                    tool_call.arguments,
                )
            observation = await asyncio.wait_for(
                invoke_tool(
                    task,
                    tool_call.tool_name,
                    tool_call.arguments,
                    permissions,
                    token,
                    [item.model_dump(mode="python") for item in evidence],
                    automation_run_id=automation_run_id,
                ),
                timeout=limits.task_timeout_seconds,
            )
        except Exception as error:
            observation = {
                "status": ToolExecutionStatus.FAILED,
                "tool_name": tool_call.tool_name,
                "reason_code": execution_error_code(error),
            }
        observations.append(observation)
        access = decision.access
        if (
            observation.get("status") == ToolExecutionStatus.COMPLETED
            and access
            and access.action == "MUTATE"
        ):
            from src.tools.registry import verify_application

            verification = await verify_application(
                task,
                tool_call.tool_name,
                tool_call.arguments,
                observation,
                token,
                automation_run_id=automation_run_id,
            )
            if verification.get("status") == ToolExecutionStatus.NOT_REQUIRED:
                verification = {
                    "status": ToolExecutionStatus.FAILED,
                    "reason_code": "POSTCONDITION_VERIFICATION_UNAVAILABLE",
                }
            observation["verification"] = verification
            if verification.get("status") != ToolExecutionStatus.COMPLETED:
                observation["status"] = ToolExecutionStatus.FAILED
                observation["reason_code"] = verification.get(
                    "reason_code", "POSTCONDITION_VERIFICATION_FAILED"
                )
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
                automatic=True,
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
                if completed
                else AgentTaskStatus.INSUFFICIENT_EVIDENCE
            ),
            summary="Tool observations collected" if completed else "Insufficient evidence",
            evidence_refs=[item.artifact_version_id or item.artifact_id for item in evidence],
            reason_codes=[item.get("reason_code", "TOOL_RESULT") for item in observations],
            warnings=["AI_PROVIDER_UNAVAILABLE"],
        )
    completed_observations = [
        item for item in observations if item.get("status") == ToolExecutionStatus.COMPLETED
    ]
    failed_observations = [
        item
        for item in observations
        if item.get("status") in {ToolExecutionStatus.FAILED, ToolExecutionStatus.DENIED}
    ]
    if task.tool_calls and not completed_observations:
        result.status = AgentTaskStatus.INSUFFICIENT_EVIDENCE
        result.reason_codes = list(dict.fromkeys([*result.reason_codes, "TOOL_FAILED"]))
    elif failed_observations:
        result.status = AgentTaskStatus.FAILED
        result.reason_codes = list(
            dict.fromkeys(
                [
                    *result.reason_codes,
                    *(str(item.get("reason_code") or "TOOL_FAILED") for item in failed_observations),
                ]
            )
        )
    allowed_refs = {item.artifact_version_id or item.artifact_id for item in evidence}
    result.evidence_refs = [reference for reference in result.evidence_refs if reference in allowed_refs]
    if evidence and not result.evidence_refs:
        result.evidence_refs = [item.artifact_version_id or item.artifact_id for item in evidence]
    result.summary = normalize_narrative(result.summary)
    result.warnings = normalize_narratives(result.warnings)
    return result, observations
