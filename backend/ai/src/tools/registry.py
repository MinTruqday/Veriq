import json
import time
from functools import lru_cache
from typing import Any, Callable, Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from src.schemas.agent import (
    AgentTask,
    CapabilityDomain,
    ToolAccess,
    ToolDecision,
    ToolExecutionStatus,
)
from src.services.agent_metrics import agentops
from src.services.token_accounting import add_tool_usage


def with_tool_access(
    domains: tuple[CapabilityDomain, ...],
    action: Literal["READ", "PROPOSE", "MUTATE"],
    permission: str,
    verification: dict[str, Any] | None = None,
    owner_domain: CapabilityDomain | None = None,
    label: str | None = None,
    user_selectable: bool = False,
) -> Callable:
    def decorate(function: Callable):
        value = tool(function)
        value.metadata = {
            "domains": list(domains),
            "owner_domain": owner_domain,
            "action": action,
            "permission": permission,
            "verification": verification,
            "label": label or function.__name__,
            "user_selectable": user_selectable,
        }
        return value

    return decorate


def tool_access(value) -> ToolAccess | None:
    if not value or not value.metadata:
        return None
    try:
        return ToolAccess(name=value.name, **value.metadata)
    except Exception:
        return None


@lru_cache(maxsize=1)
def registered_tools():
    from src.tools import tools

    return {item.name: item for item in tools if tool_access(item)}


def authorize_tool(task, tool_name, permissions):
    access = tool_access(registered_tools().get(tool_name))
    if not access:
        return ToolDecision(allowed=False, reason_code="TOOL_UNAVAILABLE")
    if task.domain not in access.domains:
        return ToolDecision(allowed=False, reason_code="TOOL_DOMAIN_DENIED", access=access)
    if access.permission not in permissions:
        return ToolDecision(allowed=False, reason_code="PERMISSION_DENIED", access=access)
    return ToolDecision(allowed=True, reason_code="ALLOWED", access=access)


def audit_arguments(arguments):
    values = {}
    for key, value in arguments.items():
        if key.endswith("_id") or key == "project_id":
            values[key] = str(value)
        elif isinstance(value, bool | int | float) or value is None:
            values[key] = value
        else:
            try:
                size = len(value)
            except TypeError:
                size = len(str(value))
            values[key] = {"type": type(value).__name__, "size": size}
    return values


def nested_value(value, path):
    current = value
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def resolved_value(reference, task, arguments, result):
    if not isinstance(reference, str) or not reference.startswith("$"):
        return reference
    source, _, path = reference[1:].partition(".")
    values = {"project": {"id": task.project_id}, "arguments": arguments, "result": result}
    return nested_value(values.get(source, {}), path)


async def verify_application(
    task, tool_name, arguments, outcome, token, automation_run_id=None
):
    access = tool_access(registered_tools().get(tool_name))
    specification = access.verification if access else None
    result = outcome.get("result") or {}
    if not specification:
        composite = result.get("verification") if isinstance(result, dict) else None
        if not isinstance(composite, dict):
            return {"status": ToolExecutionStatus.NOT_REQUIRED}
        verified = (
            composite.get("status") == ToolExecutionStatus.COMPLETED
            and composite.get("project_id") == task.project_id
            and bool(composite.get("artifact_ids"))
        )
        return {
            "status": ToolExecutionStatus.COMPLETED if verified else ToolExecutionStatus.FAILED,
            "reason_code": "COMPOSITE_READBACK_VERIFIED" if verified else "COMPOSITE_READBACK_INVALID",
            "project_id": composite.get("project_id"),
            "artifact_ids": composite.get("artifact_ids", []),
            "checks": composite.get("checks", []),
        }
    identifier = resolved_value(specification.identifier, task, arguments, result)
    if not identifier:
        return {
            "status": ToolExecutionStatus.FAILED,
            "reason_code": "POSTCONDITION_IDENTIFIER_MISSING",
        }
    from src.tools.testing import call, parse

    configurable = {
        "token": token,
        "project_id": task.project_id,
        "run_id": task.run_id,
    }
    if automation_run_id:
        configurable["automation_run_id"] = automation_run_id
    config = RunnableConfig(configurable=configurable)
    readback = parse(
        await call(
            "GET",
            specification.path.format(identifier=identifier, project_id=task.project_id),
            config,
        )
    )
    if not readback:
        return {
            "status": ToolExecutionStatus.FAILED,
            "reason_code": "POSTCONDITION_READBACK_FAILED",
        }
    mismatches = []
    for field, reference in specification.expected.items():
        expected = resolved_value(reference, task, arguments, result)
        actual = nested_value(readback, field)
        if actual != expected:
            mismatches.append(field)
    return {
        "status": ToolExecutionStatus.COMPLETED
        if not mismatches
        else ToolExecutionStatus.FAILED,
        "reason_code": "POSTCONDITION_VERIFIED" if not mismatches else "POSTCONDITION_MISMATCH",
        "artifact_id": str(identifier),
        "project_id": readback.get("project_id"),
        "revision": readback.get("revision"),
        "mismatches": mismatches,
    }


async def invoke_tool(
    task: AgentTask,
    tool_name: str,
    arguments: dict,
    permissions: list[str],
    token: str,
    evidence: list[dict] | None = None,
    automation_run_id: str | None = None,
):
    decision = authorize_tool(task, tool_name, permissions)
    if not decision.allowed:
        return {
            "status": ToolExecutionStatus.DENIED,
            "reason_code": decision.reason_code,
            "tool_name": tool_name,
        }
    tool = registered_tools().get(tool_name)
    if not tool:
        return {
            "status": ToolExecutionStatus.FAILED,
            "reason_code": "TOOL_UNAVAILABLE",
            "tool_name": tool_name,
        }
    if "project_id" in arguments and str(arguments["project_id"]) != task.project_id:
        return {
            "status": ToolExecutionStatus.DENIED,
            "reason_code": "PROJECT_SCOPE_VIOLATION",
            "tool_name": tool_name,
        }
    try:
        arguments = tool.args_schema.model_validate(arguments).model_dump(
            mode="python", exclude_unset=True
        )
    except Exception:
        return {
            "status": ToolExecutionStatus.FAILED,
            "reason_code": "TOOL_ARGUMENT_INVALID",
            "tool_name": tool_name,
        }
    configurable = {
            "token": token,
            "project_id": task.project_id,
            "run_id": task.run_id,
            "user_id": task.user_id,
            "evidence": evidence or [],
            "permissions": permissions,
        }
    if automation_run_id:
        configurable["automation_run_id"] = automation_run_id
    config = RunnableConfig(configurable=configurable)
    started = time.monotonic()
    try:
        result = await tool.ainvoke(arguments, config=config)
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                parsed = result
        else:
            parsed = result
        failed_statuses = {
            "authentication_required",
            "invalid_payload",
            "qa_operation_failed",
            "automation_blocked",
            "automation_partial_failure",
            "degraded",
            "insufficient_evidence",
        }
        result_status = (
            str(parsed.get("status") or "").casefold()
            if isinstance(parsed, dict)
            else ""
        )
        if isinstance(parsed, dict) and result_status in failed_statuses:
            reason_code = (
                (parsed.get("error") or {}).get("code")
                or parsed.get("reason_code")
                or str(parsed.get("status")).upper()
            )
            outcome = {
                "status": ToolExecutionStatus.FAILED,
                "tool_name": tool_name,
                "reason_code": reason_code,
                "result": parsed,
            }
        else:
            outcome = {
                "status": ToolExecutionStatus.COMPLETED,
                "tool_name": tool_name,
                "result": parsed,
            }
    except Exception:
        agentops.record_tool_call(
            task.run_id,
            tool_name,
            int((time.monotonic() - started) * 1000),
            False,
        )
        raise
    duration_ms = int((time.monotonic() - started) * 1000)
    agentops.record_tool_call(
        task.run_id,
        tool_name,
        duration_ms,
        outcome["status"] == ToolExecutionStatus.COMPLETED,
    )
    outcome["duration_ms"] = duration_ms
    add_tool_usage(max(1, len(json.dumps(outcome, ensure_ascii=False, default=str)) // 4))
    return outcome
