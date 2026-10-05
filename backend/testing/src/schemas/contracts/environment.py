from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.schemas.contracts.common import WebhookDeliveryStatus

class ReleaseCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=300)
    version: str = Field(min_length=1, max_length=120)
    notes: str = Field(default="", max_length=5000)
    planned_start_at: str | None = Field(default=None, max_length=80)
    planned_end_at: str | None = Field(default=None, max_length=80)
    scope_in: list[str] = Field(default_factory=list, max_length=500)
    scope_out: list[str] = Field(default_factory=list, max_length=500)


class ReleasePatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    version: str | None = Field(default=None, min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=5000)
    planned_start_at: str | None = Field(default=None, max_length=80)
    planned_end_at: str | None = Field(default=None, max_length=80)
    scope_in: list[str] | None = Field(default=None, max_length=500)
    scope_out: list[str] | None = Field(default=None, max_length=500)


class ReleaseTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(default="", max_length=2000)


class BuildCreate(BaseModel):
    identifier: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=120)
    release_id: str | None = Field(default=None, max_length=200)
    commit_ref: str | None = Field(default=None, max_length=300)
    notes: str = Field(default="", max_length=5000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class BuildPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    notes: str | None = Field(default=None, max_length=5000)
    commit_ref: str | None = Field(default=None, max_length=300)


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    environment_type: Literal["development", "testing", "staging", "production", "custom"] = (
        "testing"
    )
    base_url: str | None = Field(default=None, max_length=2000)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    availability: Literal["AVAILABLE", "UNAVAILABLE", "MAINTENANCE"] = "AVAILABLE"
    secret_refs: dict[str, str] = Field(default_factory=dict)

    @field_validator("secret_refs")
    @classmethod
    def validate_secret_refs(cls, value):
        if any(not str(ref).startswith("secret://") for ref in value.values()):
            raise ValueError("Secret reference phải bắt đầu bằng secret://")
        return value


class EnvironmentPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    environment_type: (
        Literal["development", "testing", "staging", "production", "custom"] | None
    ) = None
    base_url: str | None = Field(default=None, max_length=2000)
    capabilities: dict[str, Any] | None = None
    availability: Literal["AVAILABLE", "UNAVAILABLE", "MAINTENANCE"] | None = None


class EnvironmentSecretRefs(BaseModel):
    expected_revision: int = Field(ge=1)
    secret_refs: dict[str, str]

    @field_validator("secret_refs")
    @classmethod
    def validate_secret_refs(cls, value):
        if any(not str(ref).startswith("secret://") for ref in value.values()):
            raise ValueError("Secret reference phải bắt đầu bằng secret://")
        return value


class DeviceProfileInput(BaseModel):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=2, max_length=200)
    device_type: Literal["desktop", "laptop", "tablet", "mobile", "other"]
    operating_system: str = Field(min_length=1, max_length=120)
    operating_system_version: str = Field(default="", max_length=120)
    browser: str = Field(default="", max_length=120)
    browser_version: str = Field(default="", max_length=120)
    viewport_width: int | None = Field(default=None, ge=1, le=20000)
    viewport_height: int | None = Field(default=None, ge=1, le=20000)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class DeviceMatrixCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    profiles: list[DeviceProfileInput] = Field(min_length=1, max_length=500)

    @field_validator("profiles")
    @classmethod
    def validate_profile_keys(cls, value):
        keys = [item.key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("Mã hồ sơ thiết bị không được trùng nhau")
        return value


class DeviceMatrixPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    profiles: list[DeviceProfileInput] | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("profiles")
    @classmethod
    def validate_profile_keys(cls, value):
        if value is None:
            return value
        keys = [item.key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("Mã hồ sơ thiết bị không được trùng nhau")
        return value


class DeviceMatrixArchive(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=2000)


class DeviceMatrixAssignment(BaseModel):
    target_type: Literal["test_plan", "test_run"]
    target_id: str = Field(min_length=1, max_length=200)
    expected_target_revision: int = Field(ge=1)
    profile_keys: list[str] = Field(default_factory=list, max_length=500)


class NotificationWatchInput(BaseModel):
    watching: bool = True


class ProjectNotificationRulePatch(BaseModel):
    expected_revision: int = Field(ge=0)
    enabled_events: list[str] = Field(default_factory=list, max_length=200)
    channels: list[Literal["in_app", "email", "webhook"]] = Field(
        default_factory=lambda: ["in_app"], max_length=3
    )
    target_roles: list[Literal["QA", "TESTER", "BA", "DEVELOPER", "VIEWER"]] = Field(
        default_factory=lambda: ["QA"], max_length=5
    )
    escalation_minutes: int | None = Field(default=None, ge=1, le=10080)


class ProjectNotificationPreferencePatch(BaseModel):
    expected_revision: int = Field(ge=0)
    digest_frequency: Literal["immediate", "daily", "weekly", "off"] = "immediate"
    channels: list[Literal["in_app", "email"]] = Field(
        default_factory=lambda: ["in_app"], max_length=2
    )
    muted_events: list[str] = Field(default_factory=list, max_length=200)
    quiet_hours_start: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(default="Asia/Ho_Chi_Minh", min_length=2, max_length=80)


class SecurityTestSuggestionInput(BaseModel):
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=500)
    categories: list[
        Literal["authorization", "authentication", "input_validation", "session", "data_protection"]
    ] = Field(
        default_factory=lambda: ["authorization", "input_validation", "session"],
        min_length=1,
        max_length=5,
    )
    context: str = Field(default="", max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=200)


class PerformancePlanDraftInput(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    objective: str = Field(default="", max_length=5000)
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=500)
    workload_types: list[Literal["baseline", "load", "stress", "spike", "soak"]] = Field(
        default_factory=lambda: ["baseline", "load", "stress"], min_length=1, max_length=5
    )
    target_virtual_users: int = Field(ge=1, le=1000000)
    target_requests_per_second: float | None = Field(default=None, gt=0, le=1000000)
    duration_minutes: int = Field(ge=1, le=10080)
    response_time_p95_ms: int | None = Field(default=None, ge=1, le=3600000)
    maximum_error_rate: float | None = Field(default=None, ge=0, le=1)
    context: str = Field(default="", max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=200)


class WebhookSubscriptionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    endpoint_reference: str = Field(min_length=12, max_length=500)
    secret_reference: str = Field(min_length=10, max_length=500)
    events: list[str] = Field(min_length=1, max_length=200)
    enabled: bool = True

    @model_validator(mode="after")
    def validate_references(self):
        if not self.endpoint_reference.startswith("endpoint://"):
            raise ValueError("Điểm cuối phải dùng endpoint reference của nền tảng")
        if not self.secret_reference.startswith("secret://"):
            raise ValueError("Bí mật phải dùng secret reference của nền tảng")
        return self


class WebhookSubscriptionPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    endpoint_reference: str | None = Field(default=None, min_length=12, max_length=500)
    secret_reference: str | None = Field(default=None, min_length=10, max_length=500)
    events: list[str] | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_references(self):
        if self.endpoint_reference is not None and not self.endpoint_reference.startswith(
            "endpoint://"
        ):
            raise ValueError("Điểm cuối phải dùng endpoint reference của nền tảng")
        if self.secret_reference is not None and not self.secret_reference.startswith("secret://"):
            raise ValueError("Bí mật phải dùng secret reference của nền tảng")
        return self


class WebhookReplayInput(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    reason: str = Field(min_length=2, max_length=2000)


class WebhookDeliveryRecordInput(BaseModel):
    delivery_id: str = Field(min_length=1, max_length=200)
    project_id: str = Field(min_length=1, max_length=200)
    subscription_id: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=200)
    status: WebhookDeliveryStatus
    attempt: int = Field(default=1, ge=1, le=1000)
    response_status: int | None = Field(default=None, ge=100, le=599)
    error_code: str | None = Field(default=None, max_length=200)
    payload_hash: str = Field(min_length=16, max_length=200)
    duration_ms: float | None = Field(default=None, ge=0, le=3600000)
