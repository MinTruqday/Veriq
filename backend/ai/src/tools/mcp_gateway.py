import asyncio
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Annotated

import httpx2
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import Field

from src.core.security.guardrails import guardrails_engine
from src.core.security.scanning import security
from src.repositories.mcp import mcp_repository
from src.runtime.limits import limits
from src.schemas.mcp import (
    MCPConnection,
    MCPToolCallAudit,
    is_valid_mcp_tool_name,
    validate_mcp_endpoint,
)
from src.tools.registry import with_tool_access

_MCP_ARGUMENT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,99}$")
_MCP_SCHEMA_TYPES = {"array", "boolean", "integer", "number", "object", "string"}
_MCP_SCHEMA_MAX_NODES = 512
_MCP_SCHEMA_MAX_BYTES = 65_536
_MCP_OUTPUT_MAX_BYTES = 1_048_576
_MCP_SCHEMA_ANNOTATIONS = {
    "$comment",
    "$id",
    "$schema",
    "default",
    "deprecated",
    "description",
    "examples",
    "readOnly",
    "title",
    "writeOnly",
}


def _safe_mcp_input_schema(value, depth=0, budget=None):
    if budget is None:
        budget = [0]
    budget[0] += 1
    if budget[0] > _MCP_SCHEMA_MAX_NODES:
        return None
    if not isinstance(value, dict) or depth > 4:
        return None
    schema_type = value.get("type") or "object"
    if schema_type not in _MCP_SCHEMA_TYPES:
        return None
    supported_keywords = set(_MCP_SCHEMA_ANNOTATIONS) | {"type", "enum"}
    if schema_type == "object":
        supported_keywords.update({"properties", "required", "additionalProperties"})
    elif schema_type == "array":
        supported_keywords.update({"items", "minItems", "maxItems"})
    elif schema_type == "string":
        supported_keywords.update({"minLength", "maxLength"})
    elif schema_type in {"integer", "number"}:
        supported_keywords.update({"minimum", "maximum"})
    if set(value).difference(supported_keywords):
        return None
    result = {"type": schema_type}
    enum = value.get("enum")
    if "enum" in value and (
        not isinstance(enum, list)
        or len(enum) > 100
        or not all(
            item is None
            or isinstance(item, (str, int, bool))
            or (isinstance(item, float) and math.isfinite(item))
            for item in enum
        )
    ):
        return None
    if "enum" in value:
        result["enum"] = enum
    for key in ("minLength", "maxLength", "minItems", "maxItems"):
        constraint = value.get(key)
        if key in value and (
            not isinstance(constraint, int)
            or isinstance(constraint, bool)
            or constraint < 0
        ):
            return None
    for key in ("minimum", "maximum"):
        constraint = value.get(key)
        if key in value and (
            not isinstance(constraint, int | float)
            or isinstance(constraint, bool)
            or not math.isfinite(constraint)
        ):
            return None
    if (
        "minLength" in value
        and "maxLength" in value
        and value["minLength"] > value["maxLength"]
    ) or (
        "minItems" in value
        and "maxItems" in value
        and value["minItems"] > value["maxItems"]
    ) or (
        "minimum" in value
        and "maximum" in value
        and value["minimum"] > value["maximum"]
    ):
        return None
    for key in ("minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems"):
        constraint = value.get(key)
        if isinstance(constraint, int | float) and not isinstance(constraint, bool):
            result[key] = constraint
    if schema_type == "object":
        additional_properties = value.get("additionalProperties", False)
        if not isinstance(additional_properties, bool):
            return None
        raw_properties = value.get("properties", {})
        if not isinstance(raw_properties, dict) or len(raw_properties) > 100:
            return None
        properties = {}
        for name, definition in raw_properties.items():
            if not isinstance(name, str) or not _MCP_ARGUMENT_NAME.fullmatch(name):
                return None
            safe_definition = _safe_mcp_input_schema(definition, depth + 1, budget)
            if safe_definition is None:
                return None
            properties[name] = safe_definition
        result["properties"] = properties
        if "additionalProperties" in value:
            result["additionalProperties"] = additional_properties
        required = value.get("required", [])
        if not isinstance(required, list) or any(
            not isinstance(name, str) or name not in properties for name in required
        ):
            return None
        result["required"] = required
    elif schema_type == "array":
        if "items" not in value:
            return None
        safe_items = _safe_mcp_input_schema(value["items"], depth + 1, budget)
        if safe_items is None:
            return None
        result["items"] = safe_items
    try:
        if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")) > _MCP_SCHEMA_MAX_BYTES:
            return None
    except (TypeError, ValueError, OverflowError):
        return None
    return result


def _matches_mcp_enum(value, allowed_values):
    for allowed_value in allowed_values:
        if isinstance(value, bool) or isinstance(allowed_value, bool):
            if isinstance(value, bool) and isinstance(allowed_value, bool) and value == allowed_value:
                return True
            continue
        if isinstance(value, int | float) and isinstance(allowed_value, int | float):
            if value == allowed_value:
                return True
            continue
        if type(value) is type(allowed_value) and value == allowed_value:
            return True
    return False


def _matches_mcp_schema(value, schema):
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties") or {}
        if any(not isinstance(name, str) for name in value):
            return False
        extra_properties = set(value).difference(properties)
        if extra_properties and not schema.get("additionalProperties", False):
            return False
        if set(schema.get("required") or ()).difference(value):
            return False
        return all(
            _matches_mcp_schema(item, properties[name])
            if name in properties
            else _matches_untyped_json(item)
            for name, item in value.items()
        )
    if schema_type == "array":
        if not isinstance(value, list):
            return False
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            return False
        return all(_matches_mcp_schema(item, schema["items"]) for item in value)
    if schema_type == "string":
        if not isinstance(value, str):
            return False
        if (
            len(value) < schema.get("minLength", 0)
            or len(value) > schema.get("maxLength", float("inf"))
        ):
            return False
        return "enum" not in schema or _matches_mcp_enum(value, schema["enum"])
    if schema_type == "boolean":
        return isinstance(value, bool) and (
            "enum" not in schema or _matches_mcp_enum(value, schema["enum"])
        )
    if schema_type == "integer":
        matches = isinstance(value, int) and not isinstance(value, bool)
    elif schema_type == "number":
        matches = isinstance(value, int | float) and not isinstance(value, bool)
    else:
        return False
    if not matches or (isinstance(value, float) and not math.isfinite(value)):
        return False
    if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
        return False
    return "enum" not in schema or _matches_mcp_enum(value, schema["enum"])


def _matches_untyped_json(value, depth=0):
    if depth > 8:
        return False
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return len(value) <= 1000 and all(
            _matches_untyped_json(item, depth + 1) for item in value
        )
    if isinstance(value, dict):
        return len(value) <= 100 and all(
            isinstance(key, str) and _matches_untyped_json(item, depth + 1)
            for key, item in value.items()
        )
    return False


def _mcp_json_within_byte_limit(value, remaining=None):
    if remaining is None:
        remaining = [_MCP_OUTPUT_MAX_BYTES]
    if isinstance(value, str):
        remaining[0] -= len(value.encode("utf-8"))
        return remaining[0] >= 0
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return False
            remaining[0] -= len(key.encode("utf-8"))
            if remaining[0] < 0 or not _mcp_json_within_byte_limit(item, remaining):
                return False
        return True
    if isinstance(value, list):
        return all(_mcp_json_within_byte_limit(item, remaining) for item in value)
    if isinstance(value, int) and not isinstance(value, bool):
        if value.bit_length() > _MCP_OUTPUT_MAX_BYTES * 3:
            return False
        remaining[0] -= len(str(value))
        return remaining[0] >= 0
    return value is None or isinstance(value, (bool, int, float))


async def _client_call(endpoint, token, tool_name, arguments):
    from mcp import Client

    if not token:
        async with Client(endpoint) as client:
            return await client.call_tool(tool_name, arguments)

    from mcp.client.streamable_http import streamable_http_client

    timeout = httpx2.Timeout(limits.task_timeout_seconds, read=limits.task_timeout_seconds)
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=timeout
    ) as http_client:
        transport = streamable_http_client(endpoint, http_client=http_client)
        async with Client(transport) as client:
            return await client.call_tool(tool_name, arguments)


async def _client_tools(endpoint, token):
    from mcp import Client

    if not token:
        async with Client(endpoint) as client:
            return await client.list_tools()

    from mcp.client.streamable_http import streamable_http_client

    timeout = httpx2.Timeout(limits.task_timeout_seconds, read=limits.task_timeout_seconds)
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=timeout
    ) as http_client:
        transport = streamable_http_client(endpoint, http_client=http_client)
        async with Client(transport) as client:
            return await client.list_tools()


async def probe_connection(connection: MCPConnection):
    """Verify an MCP endpoint and its configured read-only tool allowlist."""
    if not connection.enabled:
        return {"status": "disabled", "reason_code": "MCP_CONNECTION_DISABLED"}
    try:
        validate_mcp_endpoint(connection.endpoint)
    except ValueError:
        return {
            "status": "blocked",
            "reason_code": "MCP_ENDPOINT_CONTAINS_CREDENTIALS_OR_QUERY",
            "available_tools": [],
            "missing_allowed_tools": list(connection.allowed_read_tools),
        }
    token = None
    if connection.credential_environment_variable:
        token = os.environ.get(connection.credential_environment_variable)
        if not token:
            return {
                "status": "degraded",
                "reason_code": "MCP_CREDENTIAL_UNAVAILABLE",
                "available_tools": [],
                "missing_allowed_tools": list(connection.allowed_read_tools),
            }
    try:
        async with asyncio.timeout(limits.task_timeout_seconds):
            result = await _client_tools(str(connection.endpoint), token)
    except TimeoutError:
        return {
            "status": "degraded",
            "reason_code": "MCP_TOOL_TIMEOUT",
            "available_tools": [],
            "missing_allowed_tools": list(connection.allowed_read_tools),
        }
    except Exception:
        return {
            "status": "degraded",
            "reason_code": "MCP_SERVER_UNAVAILABLE",
            "available_tools": [],
            "missing_allowed_tools": list(connection.allowed_read_tools),
        }

    available = sorted(
        {
            str(getattr(tool, "name", "")).strip()
            for tool in getattr(result, "tools", [])
            if str(getattr(tool, "name", "")).strip()
        }
    )
    allowed = sorted(set(connection.allowed_read_tools))
    missing = sorted(set(allowed) - set(available))
    return {
        "status": "connected" if not missing else "incomplete",
        "reason_code": None if not missing else "MCP_ALLOWED_TOOLS_NOT_FOUND",
        "available_tools": available,
        "allowed_tools": allowed,
        "missing_allowed_tools": missing,
    }

def _result_text(result):
    blocks = []
    byte_count = 0
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if not isinstance(text, str):
            return None, "MCP_TOOL_OUTPUT_UNSUPPORTED_CONTENT"
        if isinstance(text, str) and text:
            byte_count += len(text.encode("utf-8")) + (1 if blocks else 0)
            if byte_count > _MCP_OUTPUT_MAX_BYTES:
                return None, "MCP_TOOL_OUTPUT_TOO_LARGE"
            if len(blocks) >= 10_000:
                return None, "MCP_TOOL_OUTPUT_TOO_LARGE"
            blocks.append(text)
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        if not _matches_untyped_json(structured):
            return None, "MCP_TOOL_OUTPUT_INVALID"
        if not _mcp_json_within_byte_limit(structured):
            return None, "MCP_TOOL_OUTPUT_TOO_LARGE"
        output = json.dumps(structured, ensure_ascii=False, allow_nan=False)
        if len(output.encode("utf-8")) > _MCP_OUTPUT_MAX_BYTES:
            return None, "MCP_TOOL_OUTPUT_TOO_LARGE"
        return output, None
    return "\n".join(blocks), None


async def call_read_tool(
    connection: MCPConnection,
    tool_name: str,
    arguments: dict,
    *,
    project_id: str | None = None,
    verify_connection_revision: bool = False,
):
    if not connection.enabled or tool_name not in connection.allowed_read_tools:
        return {"status": "denied", "reason_code": "MCP_TOOL_NOT_ALLOWLISTED"}
    try:
        validate_mcp_endpoint(connection.endpoint)
    except ValueError:
        return {
            "status": "blocked",
            "reason_code": "MCP_ENDPOINT_CONTAINS_CREDENTIALS_OR_QUERY",
        }
    current_connection = connection
    if verify_connection_revision:
        try:
            current_connection = await mcp_repository.get(connection.connection_id)
        except Exception:
            return {"status": "degraded", "reason_code": "MCP_CONNECTION_REVALIDATION_FAILED"}
        if (
            not current_connection
            or not current_connection.enabled
            or current_connection.revision != connection.revision
            or current_connection.project_id not in {None, project_id}
        ):
            return {"status": "denied", "reason_code": "MCP_CONNECTION_CHANGED_OR_REVOKED"}
        if tool_name not in current_connection.allowed_read_tools:
            return {"status": "denied", "reason_code": "MCP_TOOL_NOT_ALLOWLISTED"}
    token = None
    if current_connection.credential_environment_variable:
        token = os.environ.get(current_connection.credential_environment_variable)
        if not token:
            return {"status": "degraded", "reason_code": "MCP_CREDENTIAL_UNAVAILABLE"}
    try:
        async with asyncio.timeout(limits.task_timeout_seconds):
            advertised = await _client_tools(str(current_connection.endpoint), token)
    except TimeoutError:
        return {"status": "degraded", "reason_code": "MCP_TOOL_TIMEOUT"}
    except Exception:
        return {"status": "degraded", "reason_code": "MCP_TOOL_DISCOVERY_FAILED"}
    tool_info = next(
        (
            item
            for item in getattr(advertised, "tools", [])
            if getattr(item, "name", None) == tool_name
        ),
        None,
    )
    if tool_info is None:
        return {"status": "denied", "reason_code": "MCP_TOOL_NOT_FOUND"}
    if not _mcp_json_within_byte_limit(arguments):
        return {"status": "failed", "reason_code": "MCP_TOOL_ARGUMENT_INVALID"}
    schema = _safe_mcp_input_schema(getattr(tool_info, "input_schema", None) or {})
    if schema is None:
        return {"status": "blocked", "reason_code": "MCP_TOOL_SCHEMA_UNSUPPORTED"}
    if not _matches_mcp_schema(arguments, schema):
        return {"status": "failed", "reason_code": "MCP_TOOL_ARGUMENT_INVALID"}
    if verify_connection_revision:
        try:
            latest_connection = await mcp_repository.get(connection.connection_id)
        except Exception:
            return {"status": "degraded", "reason_code": "MCP_CONNECTION_REVALIDATION_FAILED"}
        if (
            not latest_connection
            or not latest_connection.enabled
            or latest_connection.revision != current_connection.revision
            or latest_connection.project_id not in {None, project_id}
            or tool_name not in latest_connection.allowed_read_tools
        ):
            return {"status": "denied", "reason_code": "MCP_CONNECTION_CHANGED_OR_REVOKED"}
        current_connection = latest_connection
        if current_connection.credential_environment_variable:
            token = os.environ.get(current_connection.credential_environment_variable)
            if not token:
                return {"status": "degraded", "reason_code": "MCP_CREDENTIAL_UNAVAILABLE"}
    try:
        async with asyncio.timeout(limits.task_timeout_seconds):
            result = await _client_call(str(current_connection.endpoint), token, tool_name, arguments)
    except TimeoutError:
        return {"status": "degraded", "reason_code": "MCP_TOOL_TIMEOUT"}
    except Exception:
        return {"status": "degraded", "reason_code": "MCP_SERVER_UNAVAILABLE"}
    if getattr(result, "is_error", False):
        return {"status": "failed", "reason_code": "MCP_TOOL_FAILED"}
    output, output_error = _result_text(result)
    if output_error:
        return {"status": "blocked", "reason_code": output_error}
    if not output:
        return {"status": "failed", "reason_code": "MCP_TOOL_EMPTY_OUTPUT"}
    privacy_scan = await security.inspect_external_tool_output(output)
    if privacy_scan.status == "BLOCKED" or not privacy_scan.sanitized_text:
        return {
            "status": "blocked",
            "reason_code": privacy_scan.reason_code or "EXTERNAL_TOOL_OUTPUT_REJECTED",
        }
    inspected = await guardrails_engine.async_inspect_tool_output(
        privacy_scan.sanitized_text
    )
    if not inspected.get("is_safe", False):
        return {"status": "blocked", "reason_code": "MCP_OUTPUT_REJECTED"}
    sanitized_output = inspected.get("sanitized_text")
    if not isinstance(sanitized_output, str):
        return {"status": "blocked", "reason_code": "MCP_OUTPUT_REJECTED"}
    return {
        "status": "completed",
        "connection_id": connection.connection_id,
        "server": connection.name,
        "tool_name": tool_name,
        "content": sanitized_output,
        "content_redacted": privacy_scan.status == "REDACTED",
    }


async def _call_mcp_read_tool(
    connection_id: Annotated[str, Field(min_length=1, max_length=128)],
    tool_name: Annotated[str, Field(min_length=1, max_length=200)],
    arguments: Annotated[dict | None, Field(max_length=100)] = None,
    config: RunnableConfig = None,
) -> str:
    configurable = (config or {}).get("configurable", {})
    project_id = configurable.get("project_id")
    token = configurable.get("token")
    automation_run_id = configurable.get("automation_run_id")
    if not project_id or not isinstance(token, str) or not token.strip():
        return json.dumps({"status": "denied", "reason_code": "PROJECT_AUTHORIZATION_CONTEXT_MISSING"})
    if "project.read" not in configurable.get("permissions", []):
        return json.dumps({"status": "denied", "reason_code": "PERMISSION_DENIED"})

    from fastapi import HTTPException

    from src.services.project_access import project_access

    raw_token = token[7:].strip() if token.casefold().startswith("bearer ") else token
    try:
        _, live_permissions = await project_access(
            project_id, raw_token, automation_run_id
        )
    except HTTPException as error:
        detail = error.detail
        reason_code = detail.get("code") if isinstance(detail, dict) else None
        return json.dumps({
            "status": "denied",
            "reason_code": reason_code or "PROJECT_ACCESS_DENIED",
        })
    except Exception:
        return json.dumps({
            "status": "degraded",
            "reason_code": "PROJECT_AUTHORIZATION_CHECK_FAILED",
        })
    if "project.read" not in live_permissions:
        return json.dumps({"status": "denied", "reason_code": "PERMISSION_REVOKED"})

    connection = await mcp_repository.get(connection_id)
    if not connection or connection.project_id not in {None, project_id}:
        return json.dumps({"status": "denied", "reason_code": "MCP_CONNECTION_SCOPE_DENIED"})
    result = await call_read_tool(
        connection,
        tool_name,
        arguments or {},
        project_id=project_id,
        verify_connection_revision=True,
    )
    if result.get("status") != "completed":
        return json.dumps(result, ensure_ascii=False)

    try:
        _, current_permissions = await project_access(
            project_id, raw_token, automation_run_id
        )
    except HTTPException as error:
        detail = error.detail
        reason_code = detail.get("code") if isinstance(detail, dict) else None
        return json.dumps(
            {
                "status": "denied",
                "reason_code": reason_code or "PROJECT_ACCESS_REVOKED_AFTER_MCP_CALL",
            }
        )
    except Exception:
        return json.dumps(
            {"status": "degraded", "reason_code": "PROJECT_AUTHORIZATION_RECHECK_FAILED"}
        )
    if "project.read" not in current_permissions:
        return json.dumps(
            {"status": "denied", "reason_code": "PROJECT_ACCESS_REVOKED_AFTER_MCP_CALL"}
        )

    try:
        latest_connection = await mcp_repository.get(connection_id)
    except Exception:
        return json.dumps(
            {"status": "degraded", "reason_code": "MCP_CONNECTION_REVALIDATION_FAILED"}
        )
    if (
        not latest_connection
        or not latest_connection.enabled
        or latest_connection.revision != connection.revision
        or latest_connection.project_id not in {None, project_id}
        or tool_name not in latest_connection.allowed_read_tools
    ):
        return json.dumps(
            {"status": "denied", "reason_code": "MCP_CONNECTION_CHANGED_OR_REVOKED"}
        )

    result["_audit_connection_revision"] = connection.revision
    return json.dumps(result, ensure_ascii=False)


@with_tool_access(
    ("requirement", "test_design", "analysis", "execution", "reporting"),
    "READ",
    "project.read",
    owner_domain="analysis",
    label="Đọc công cụ MCP được cấp phép",
)
async def call_mcp_read_tool(
    connection_id: Annotated[str, Field(min_length=1, max_length=128)],
    tool_name: Annotated[str, Field(min_length=1, max_length=200)],
    arguments: Annotated[dict | None, Field(max_length=100)] = None,
    config: RunnableConfig = None,
) -> str:
    """Call one allow-listed MCP read tool with project authorization and audit."""
    configurable = (config or {}).get("configurable", {})
    project_id = configurable.get("project_id")
    user_id = configurable.get("user_id")
    automation_run_id = configurable.get("automation_run_id")
    task_id = configurable.get("task_id")
    started_at = datetime.now(timezone.utc)
    safe_arguments = arguments or {}
    try:
        canonical_arguments = json.dumps(
            safe_arguments, sort_keys=True, ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError, OverflowError):
        canonical_arguments = f"invalid-arguments:{type(safe_arguments).__name__}"
    arguments_hash = hashlib.sha256(canonical_arguments.encode("utf-8")).hexdigest()
    audit = MCPToolCallAudit(
        project_id=str(project_id) if project_id else None,
        connection_id=connection_id,
        automation_run_id=str(automation_run_id) if automation_run_id else None,
        task_id=str(task_id) if task_id else None,
        user_id=str(user_id) if user_id else None,
        tool_name=tool_name,
        arguments_sha256=arguments_hash,
        status="running",
        started_at=started_at,
    )
    try:
        await mcp_repository.record_call_audit(audit)
    except Exception:
        logger.exception("MCP call blocked because its start audit could not be persisted")
        return json.dumps(
            {"status": "degraded", "reason_code": "MCP_AUDIT_PERSISTENCE_FAILED"}
        )

    try:
        output = await _call_mcp_read_tool(
            connection_id, tool_name, safe_arguments, config
        )
    except asyncio.CancelledError:
        interrupted_output = json.dumps(
            {"status": "degraded", "reason_code": "MCP_TOOL_CALL_CANCELLED"}
        )
        try:
            await mcp_repository.complete_call_audit(
                audit.audit_id,
                status="degraded",
                reason_code="MCP_TOOL_CALL_CANCELLED",
                connection_revision=None,
                output_sha256=hashlib.sha256(
                    interrupted_output.encode("utf-8")
                ).hexdigest(),
                completed_at=datetime.now(timezone.utc),
            )
        except Exception:
            logger.exception("Could not persist cancelled MCP call audit")
        raise
    except Exception:
        logger.exception(
            "MCP read tool failed before returning a result connection_id={} tool_name={}",
            connection_id,
            tool_name,
        )
        output = json.dumps(
            {"status": "degraded", "reason_code": "MCP_TOOL_CALL_FAILED"}
        )

    try:
        result = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        result = {"status": "failed", "reason_code": "MCP_TOOL_RESULT_INVALID"}
        output = json.dumps(result)
    if not isinstance(result, dict):
        result = {"status": "failed", "reason_code": "MCP_TOOL_RESULT_INVALID"}
        output = json.dumps(result)

    connection_revision = result.pop("_audit_connection_revision", None)
    result["audit_id"] = audit.audit_id
    user_visible_output = json.dumps(result, ensure_ascii=False)
    final_status = str(result.get("status") or "failed")
    if final_status not in {"completed", "denied", "degraded", "failed", "blocked"}:
        final_status = "failed"
        result = {"status": final_status, "reason_code": "MCP_TOOL_RESULT_INVALID"}
        user_visible_output = json.dumps(result, ensure_ascii=False)
    try:
        audit_completed = await mcp_repository.complete_call_audit(
            audit.audit_id,
            status=final_status,
            reason_code=(
                str(result["reason_code"]) if result.get("reason_code") else None
            ),
            connection_revision=connection_revision,
            output_sha256=hashlib.sha256(user_visible_output.encode("utf-8")).hexdigest(),
            completed_at=datetime.now(timezone.utc),
        )
    except Exception:
        logger.exception(
            "MCP result withheld because its audit record could not be persisted"
        )
        audit_completed = False
    if not audit_completed:
        return json.dumps(
            {"status": "degraded", "reason_code": "MCP_AUDIT_PERSISTENCE_FAILED"}
        )
    return user_visible_output


async def discover_project_tools_with_diagnostics(
    project_id: str,
    permissions: list[str],
    token: str | None = None,
    automation_run_id: str | None = None,
):
    if "project.read" not in permissions or not isinstance(token, str) or not token.strip():
        return {"tools": [], "issues": []}
    from src.services.project_access import project_access

    raw_token = token[7:].strip() if token.casefold().startswith("bearer ") else token
    try:
        _, live_permissions = await project_access(
            project_id, raw_token, automation_run_id
        )
    except Exception:
        return {
            "tools": [],
            "issues": [{"reason_code": "MCP_PROJECT_AUTHORIZATION_UNAVAILABLE"}],
        }
    if "project.read" not in live_permissions:
        return {"tools": [], "issues": [{"reason_code": "MCP_PROJECT_ACCESS_REVOKED"}]}
    try:
        connections = await mcp_repository.list_project(project_id)
    except Exception:
        return {
            "tools": [],
            "issues": [{"reason_code": "MCP_CONNECTION_DISCOVERY_UNAVAILABLE"}],
        }
    values = []
    issues = []
    for connection in connections:
        if not connection.enabled:
            continue
        try:
            validate_mcp_endpoint(connection.endpoint)
        except ValueError:
            issues.append(
                {
                    "connection_id": connection.connection_id,
                    "reason_code": "MCP_ENDPOINT_CONTAINS_CREDENTIALS_OR_QUERY",
                }
            )
            continue
        credential = (
            os.environ.get(connection.credential_environment_variable)
            if connection.credential_environment_variable
            else None
        )
        if connection.credential_environment_variable and not credential:
            issues.append({
                "connection_id": connection.connection_id,
                "reason_code": "MCP_CREDENTIAL_UNAVAILABLE",
            })
            continue
        try:
            async with asyncio.timeout(limits.task_timeout_seconds):
                tools = await _client_tools(connection.endpoint, credential)
        except TimeoutError:
            issues.append({
                "connection_id": connection.connection_id,
                "reason_code": "MCP_DISCOVERY_TIMEOUT",
            })
            continue
        except Exception:
            issues.append({
                "connection_id": connection.connection_id,
                "reason_code": "MCP_DISCOVERY_FAILED",
            })
            continue
        discovered_allowed_tool = False
        for tool_info in tools.tools:
            name = getattr(tool_info, "name", "")
            if (
                not isinstance(name, str)
                or not is_valid_mcp_tool_name(name)
                or name not in connection.allowed_read_tools
            ):
                continue
            discovered_allowed_tool = True
            schema = _safe_mcp_input_schema(
                getattr(tool_info, "input_schema", None) or {}
            )
            if schema is None:
                issues.append({
                    "connection_id": connection.connection_id,
                    "tool_name": name,
                    "reason_code": "MCP_TOOL_SCHEMA_UNSUPPORTED",
                })
                continue
            values.append(
                {
                    "connection_id": connection.connection_id,
                    "tool_name": name,
                    "call_tool": "call_mcp_read_tool",
                    "required_arguments": {
                        "connection_id": connection.connection_id,
                        "tool_name": name,
                    },
                    "remote_input_schema": schema,
                }
            )
        if connection.allowed_read_tools and not discovered_allowed_tool:
            issues.append({
                "connection_id": connection.connection_id,
                "reason_code": "MCP_ALLOWED_TOOLS_NOT_ADVERTISED",
            })
    return {"tools": values, "issues": issues}


async def discover_project_tools(
    project_id: str,
    permissions: list[str],
    token: str | None = None,
    automation_run_id: str | None = None,
):
    result = await discover_project_tools_with_diagnostics(
        project_id,
        permissions,
        token=token,
        automation_run_id=automation_run_id,
    )
    return result["tools"]
