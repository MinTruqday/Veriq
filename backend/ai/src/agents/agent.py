import asyncio
import re
import traceback

from fastapi import HTTPException
from loguru import logger

from src.prompts.agent_execution import agent_execution_prompt
from src.runtime.limits import limits
from src.runtime.output import normalize_narrative, normalize_narratives
from src.schemas.agent import AgentResult, AgentTaskStatus, ToolExecutionStatus
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
            if str(error) == "AUTOMATION_WORKER_FENCE_LOST":
                raise
            frames = traceback.extract_tb(error.__traceback__)
            frame = frames[-1] if frames else None
            logger.error(
                "Automation tool invocation failed run_id={} tool={} error_type={} source={} line={} function={}",
                automation_run_id or "",
                tool_call.tool_name,
                type(error).__name__,
                frame.filename if frame else "",
                frame.lineno if frame else 0,
                frame.name if frame else "",
            )
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
        result_payload = observation.get("result")
        if (
            isinstance(result_payload, dict)
            and result_payload.get("status")
            in {"automation_partial_failure", "automation_blocked"}
        ):
            break
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
            summary=(
                "Đã thu thập kết quả từ công cụ"
                if completed
                else "Chưa có đủ bằng chứng để kết luận"
            ),
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
    decision_outcomes = [
        item.get("result") or {}
        for item in completed_observations
        if (item.get("result") or {}).get("status") in {
            "automation_waiting_for_decision",
            "automation_waiting_for_input",
        }
    ]
    if decision_outcomes:
        decision_codes = [
            str(item.get("reason_code") or "BUSINESS_DECISION_REQUIRED")
            for item in decision_outcomes
        ]
        result.status = AgentTaskStatus.INSUFFICIENT_EVIDENCE
        result.reason_codes = list(dict.fromkeys([*result.reason_codes, *decision_codes]))
        awaiting_input = any(
            item.get("status") == "automation_waiting_for_input"
            for item in decision_outcomes
        )
        warning = "CLARIFICATION_REQUIRED" if awaiting_input else "USER_DECISION_REQUIRED"
        result.warnings = list(dict.fromkeys([*result.warnings, warning]))
        result.summary = (
            "Đã lưu kết quả có căn cứ và các câu hỏi làm rõ; luồng sẽ tiếp tục khi thông tin nguồn được cập nhật"
            if awaiting_input
            else "Đã giữ nguyên dữ liệu hiện có và lưu các mâu thuẫn nguồn để người dùng quyết định trước khi tiếp tục"
        )
    partial_failure_outcomes = [
        item.get("result") or {}
        for item in completed_observations
        if (item.get("result") or {}).get("status") == "automation_partial_failure"
    ]
    if partial_failure_outcomes and not decision_outcomes:
        partial_codes = [
            str(item.get("reason_code") or "AUTOMATION_PARTIAL_FAILURE")
            for item in partial_failure_outcomes
        ]
        result.status = AgentTaskStatus.INSUFFICIENT_EVIDENCE
        result.reason_codes = list(dict.fromkeys([*result.reason_codes, *partial_codes]))
        result.warnings = list(
            dict.fromkeys([*result.warnings, "AUTOMATION_PARTIAL_FAILURE"])
        )
        result.summary = (
            "Tự động hóa đã dừng an toàn vì chưa đủ căn cứ để hoàn tất; "
            "không công bố kết quả như một lượt thành công."
        )
    blocked_outcomes = [
        item.get("result") or {}
        for item in completed_observations
        if (item.get("result") or {}).get("status") == "automation_blocked"
    ]
    if blocked_outcomes and not decision_outcomes and not partial_failure_outcomes:
        blocked_codes = [
            str(item.get("reason_code") or "AUTOMATION_BLOCKED")
            for item in blocked_outcomes
        ]
        result.status = AgentTaskStatus.FAILED
        result.reason_codes = list(dict.fromkeys([*result.reason_codes, *blocked_codes]))
        result.warnings = list(dict.fromkeys([*result.warnings, "AUTOMATION_BLOCKED"]))
        result.summary = "Tự động hóa bị chặn bởi điều kiện nghiệp vụ hoặc quyền; không ghi nhận hoàn tất."
    allowed_refs = {item.artifact_version_id or item.artifact_id for item in evidence}
    result.evidence_refs = [reference for reference in result.evidence_refs if reference in allowed_refs]
    if evidence and not result.evidence_refs:
        result.evidence_refs = [item.artifact_version_id or item.artifact_id for item in evidence]
    result.summary = normalize_narrative(result.summary)
    result.warnings = normalize_narratives(result.warnings)
    return result, observations
