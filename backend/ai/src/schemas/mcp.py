from datetime import datetime, timezone
from uuid import uuid4

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MCPConnectionCreate(BaseModel):
    project_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    endpoint: AnyHttpUrl
    credential_environment_variable: str | None = Field(default=None, max_length=120)
    allowed_read_tools: list[str] = Field(min_length=1, max_length=100)

    @field_validator("endpoint")
    @classmethod
    def require_tls_endpoint(cls, value):
        if value.scheme != "https":
            raise ValueError("mcp_endpoint_requires_https")
        return value

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
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("mcp_tool_name_required")
        if len(normalized) != len(set(normalized)):
            raise ValueError("mcp_tool_name_duplicate")
        return normalized


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
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("mcp_tool_name_required")
        if len(normalized) != len(set(normalized)):
            raise ValueError("mcp_tool_name_duplicate")
        return normalized

    @field_validator("endpoint")
    @classmethod
    def require_tls_endpoint(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("mcp_endpoint_requires_https")
        return value


class MCPConnection(BaseModel):
    connection_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    name: str
    endpoint: str
    credential_environment_variable: str | None = None
    allowed_read_tools: list[str]
    enabled: bool = True
    revision: int = 1
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MCPToolCallRequest(BaseModel):
    connection_id: str = Field(min_length=1, max_length=128)
    tool_name: str = Field(min_length=1, max_length=200)
    arguments: dict = Field(default_factory=dict, max_length=100)
