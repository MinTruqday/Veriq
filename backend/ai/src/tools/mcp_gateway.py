import asyncio
import json
import os
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.security.guardrails import guardrails_engine
from src.repositories.mcp import mcp_repository
from src.runtime.limits import limits
from src.schemas.mcp import MCPConnection
from src.tools.registry import with_tool_access


async def _client_call(endpoint, token, tool_name, arguments):
    from mcp import Client

    if not token:
        async with Client(endpoint) as client:
            return await client.call_tool(tool_name, arguments)

    import httpx2
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

    import httpx2
    from mcp.client.streamable_http import streamable_http_client

    timeout = httpx2.Timeout(limits.task_timeout_seconds, read=limits.task_timeout_seconds)
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=timeout
    ) as http_client:
        transport = streamable_http_client(endpoint, http_client=http_client)
        async with Client(transport) as client:
            return await client.list_tools()


def _result_text(result):
    blocks = []
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if isinstance(text, str) and text:
            blocks.append(text)
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, default=str)
    return "\n".join(blocks)


async def call_read_tool(connection: MCPConnection, tool_name: str, arguments: dict):
    if not connection.enabled or tool_name not in connection.allowed_read_tools:
        return {"status": "denied", "reason_code": "MCP_TOOL_NOT_ALLOWLISTED"}
    token = None
    if connection.credential_environment_variable:
        token = os.environ.get(connection.credential_environment_variable)
        if not token:
            return {"status": "degraded", "reason_code": "MCP_CREDENTIAL_UNAVAILABLE"}
    try:
        async with asyncio.timeout(limits.task_timeout_seconds):
            result = await _client_call(str(connection.endpoint), token, tool_name, arguments)
    except TimeoutError:
        return {"status": "degraded", "reason_code": "MCP_TOOL_TIMEOUT"}
    except Exception:
        return {"status": "degraded", "reason_code": "MCP_SERVER_UNAVAILABLE"}
    if getattr(result, "is_error", False):
        return {"status": "failed", "reason_code": "MCP_TOOL_FAILED"}
    output = _result_text(result)
    if not output:
        return {"status": "failed", "reason_code": "MCP_TOOL_EMPTY_OUTPUT"}
    inspected = await guardrails_engine.async_inspect_input(output)
    if not inspected.get("is_safe", False):
        return {"status": "blocked", "reason_code": "MCP_OUTPUT_REJECTED"}
    return {
        "status": "completed",
        "connection_id": connection.connection_id,
        "server": connection.name,
        "tool_name": tool_name,
        "content": inspected.get("sanitized_text") or output,
    }


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
    """Call a project-scoped MCP tool that was explicitly granted read-only access"""
    configurable = (config or {}).get("configurable", {})
    project_id = configurable.get("project_id")
    if "project.read" not in configurable.get("permissions", []):
        return json.dumps({"status": "denied", "reason_code": "PERMISSION_DENIED"})
    connection = await mcp_repository.get(connection_id)
    if not connection or connection.project_id != project_id:
        return json.dumps({"status": "denied", "reason_code": "MCP_CONNECTION_SCOPE_DENIED"})
    return json.dumps(
        await call_read_tool(connection, tool_name, arguments or {}), ensure_ascii=False
    )


async def discover_project_tools(project_id: str, permissions: list[str]):
    if "project.read" not in permissions:
        return []
    values = []
    for connection in await mcp_repository.list_project(project_id):
        if not connection.enabled:
            continue
        token = (
            os.environ.get(connection.credential_environment_variable)
            if connection.credential_environment_variable
            else None
        )
        if connection.credential_environment_variable and not token:
            continue
        try:
            async with asyncio.timeout(limits.task_timeout_seconds):
                tools = await _client_tools(connection.endpoint, token)
        except Exception:
            continue
        for tool_info in tools.tools:
            name = getattr(tool_info, "name", "")
            if name not in connection.allowed_read_tools:
                continue
            description = str(getattr(tool_info, "description", "") or "")
            schema = getattr(tool_info, "input_schema", None) or {}
            untrusted_metadata = f"{description}\n{json.dumps(schema, ensure_ascii=False, default=str)}"
            inspection = await guardrails_engine.async_inspect_input(
                untrusted_metadata
            )
            if (
                not inspection.get("is_safe", False)
                or inspection.get("sanitized_text") != untrusted_metadata
            ):
                continue
            values.append(
                {
                    "connection_id": connection.connection_id,
                    "server": connection.name,
                    "tool_name": name,
                    "call_tool": "call_mcp_read_tool",
                    "required_arguments": {
                        "connection_id": connection.connection_id,
                        "tool_name": name,
                    },
                    "remote_input_schema": schema,
                    "description": inspection.get("sanitized_text") or description,
                }
            )
    return values
