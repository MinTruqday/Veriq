import re
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator

_MCP_TOOL_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,199}$")


def is_valid_mcp_tool_name(value: object) -> bool:
    return isinstance(value, str) and bool(_MCP_TOOL_NAME.fullmatch(value))


def _validate_allowed_read_tools(values: list[str]) -> list[str]:
    normalized = [value.strip() for value in values]
    if any(not value for value in normalized):
        raise ValueError("mcp_tool_name_required")
    if any(not is_valid_mcp_tool_name(value) for value in normalized):
        raise ValueError("mcp_tool_name_invalid")
    if len(normalized) != len(set(normalized)):
        raise ValueError("mcp_tool_name_duplicate")
    return normalized


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_mcp_endpoint(value):
    if value is None:
        return value
    parsed = urlsplit(str(value))
    if parsed.scheme != "https":
        raise ValueError("mcp_endpoint_requires_https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("mcp_endpoint_must_not_contain_credentials_or_query")
    return value


class MCPConnectionCreate(BaseModel):
    project_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Leave empty to make this MCP connection available to every project",
    )
    name: str = Field(min_length=1, max_length=120)
    endpoint: AnyHttpUrl
    credential_environment_variable: str | None = Field(default=None, max_length=120)
    allowed_read_tools: list[str] = Field(min_length=1, max_length=100)

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value):
        return validate_mcp_endpoint(value)

    @field_validator("credential_environment_variable")
    @classmethod
    def validate_credential_reference(cls, value):
        if value is not None and (
            not value.startswith("MCP_")
            or not value.replace("_", "").isalnum()
            or value.upper() != value
        ):
            raise ValueError("mcp_credential_environment_reference_invalid")
        return value

    @field_validator("allowed_read_tools")
    @classmethod
    def unique_tool_names(cls, values):
        return _validate_allowed_read_tools(values)


class MCPConnectionPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    endpoint: AnyHttpUrl | None = None
    credential_environment_variable: str | None = Field(default=None, max_length=120)
    allowed_read_tools: list[str] | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None

    @field_validator("credential_environment_variable")
    @classmethod
    def validate_credential_reference(cls, value):
        if value is not None and (
            not value.startswith("MCP_")
            or not value.replace("_", "").isalnum()
            or value.upper() != value
        ):
            raise ValueError("mcp_credential_environment_reference_invalid")
        return value

    @field_validator("allowed_read_tools")
    @classmethod
    def validate_tool_names(cls, values):
        if values is None:
            return values
        return _validate_allowed_read_tools(values)

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value):
        return validate_mcp_endpoint(value)


class MCPConnection(BaseModel):
    connection_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str | None = None
    name: str
    endpoint: str
    credential_environment_variable: str | None = None
    allowed_read_tools: list[str]
    enabled: bool = True
    revision: int = 1
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MCPToolCallAudit(BaseModel):
    audit_id: str = Field(default_factory=lambda: f"MCPA-{uuid4().hex}")
    project_id: str | None = None
    connection_id: str
    connection_revision: int | None = Field(default=None, ge=1)
    automation_run_id: str | None = None
    task_id: str | None = None
    user_id: str | None = None
    tool_name: str
    arguments_sha256: str = Field(min_length=64, max_length=64)
    output_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    status: Literal["running", "completed", "denied", "degraded", "failed", "blocked"]
    reason_code: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class MCPToolCallRequest(BaseModel):
    connection_id: str = Field(min_length=1, max_length=128)
    tool_name: str = Field(min_length=1, max_length=200)
    arguments: dict = Field(default_factory=dict, max_length=100)
