from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from src.schemas.identity import SystemRole


class ActionReason(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class ConfigUpdate(BaseModel):
    values: dict[str, Any]
    reason: str = Field(min_length=3, max_length=1000)


class AccountUpdate(BaseModel):
    system_role: SystemRole | None = None
    is_active: bool | None = None
    reason: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def validate_change(self):
        if self.system_role is None and self.is_active is None:
            raise ValueError("Cần cung cấp thay đổi vai trò hoặc trạng thái")
        return self


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    reason: str = Field(min_length=3, max_length=1000)


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    reason: str = Field(min_length=3, max_length=1000)


class SystemRoleUpdate(BaseModel):
    system_role: SystemRole
    reason: str = Field(min_length=3, max_length=1000)


class ProjectPolicyUpdate(BaseModel):
    project_creation_policy: str = Field(pattern="^(AUTHENTICATED|ADMIN_ONLY)$")
    reason: str = Field(min_length=3, max_length=1000)


class ProviderUpdate(BaseModel):
    enabled: bool | None = None
    model: str | None = Field(default=None, min_length=1, max_length=200)
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)
    max_output_tokens: int | None = Field(default=None, ge=128, le=131072)
    secret_reference: str | None = Field(default=None, min_length=1, max_length=300)
    reason: str = Field(min_length=3, max_length=1000)


class ModelRegistryEntry(BaseModel):
    provider_id: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    version: str | None = Field(default=None, max_length=100)
    enabled: bool = True
    capabilities: list[str] = Field(default_factory=list, max_length=30)
    reason: str = Field(min_length=3, max_length=1000)


class ProjectStatusUpdate(BaseModel):
    status: str = Field(pattern="^(ACTIVE|SUSPENDED)$")
    reason: str = Field(min_length=3, max_length=1000)


class ProjectQuotaUpdate(BaseModel):
    storage_bytes: int | None = Field(default=None, ge=0)
    ai_requests_per_day: int | None = Field(default=None, ge=0)
    concurrent_jobs: int | None = Field(default=None, ge=0, le=10000)
    reason: str = Field(min_length=3, max_length=1000)


class UserDeleteRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=320)
    reason: str = Field(min_length=3, max_length=1000)


class BulkUserPreviewRequest(BaseModel):
    action: Literal["DISABLE", "INVITE", "REVOKE_SESSIONS"]
    user_ids: list[str] = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=1000)


class BulkUserConfirmRequest(BaseModel):
    confirmation: Literal["CONFIRM"]


class ProjectDeleteRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=1000)


class BreakGlassCreateRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=128)
    permissions: list[str] = Field(min_length=1, max_length=100)
    ttl_minutes: int = Field(ge=5, le=240)
    reason: str = Field(min_length=10, max_length=1000)


class ServiceIdentityRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    secret_reference: str = Field(min_length=1, max_length=500)
    scopes: list[str] = Field(default_factory=list, max_length=100)
    reason: str = Field(min_length=3, max_length=1000)


class ServiceIdentityRotateRequest(BaseModel):
    secret_reference: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=1000)


class SecretReferenceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    provider: str = Field(min_length=2, max_length=100)
    reference: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=1000)


class SecretReferenceRotateRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=1000)


class EmergencyRevokeRequest(BaseModel):
    scope: Literal["USER", "ALL_USERS", "SERVICE_IDENTITY", "ALL_SERVICE_IDENTITIES"]
    target_id: str | None = Field(default=None, max_length=128)
    confirmation: Literal["EMERGENCY_REVOKE"]
    reason: str = Field(min_length=10, max_length=1000)

    @model_validator(mode="after")
    def validate_target(self):
        if self.scope in {"USER", "SERVICE_IDENTITY"} and not self.target_id:
            raise ValueError("Cần cung cấp đối tượng cần thu hồi")
        return self


class SmtpTestRequest(BaseModel):
    recipient: EmailStr
    reason: str = Field(min_length=3, max_length=1000)


class RagReindexRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=128)
    artifact_version_ids: list[str] = Field(default_factory=list, max_length=1000)
    reason: str = Field(min_length=3, max_length=1000)


class CacheClearRequest(BaseModel):
    scope: Literal["RATE_LIMITS", "PROJECT_METADATA", "SAFE_ALL"]
    confirmation: Literal["CLEAR_SAFE_CACHE"]
    reason: str = Field(min_length=3, max_length=1000)


class MaintenanceModeRequest(BaseModel):
    enabled: bool
    banner: str = Field(default="", max_length=500)
    reason: str = Field(min_length=3, max_length=1000)
