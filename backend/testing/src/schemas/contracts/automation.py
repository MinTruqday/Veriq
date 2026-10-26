from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.schemas.contracts.common import AutomationExecutionStatus

class AutomationScriptGenerateInput(BaseModel):
    framework: Literal["playwright", "cypress", "selenium"]
    language: Literal["typescript", "javascript", "python"]
    test_case_version_id: str = Field(min_length=1, max_length=200)
    source_event_key: str = Field(min_length=1, max_length=200)
    source_event_revision: int = Field(ge=1)
    context: str = Field(default="", max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=200)

    @model_validator(mode="after")
    def validate_framework_language(self):
        if self.framework == "selenium" and self.language != "python":
            raise ValueError("Selenium chỉ hỗ trợ Python trong bản dựng này")
        if self.framework in {"playwright", "cypress"} and self.language == "python":
            raise ValueError("Playwright và Cypress dùng TypeScript hoặc JavaScript")
        return self


class AutomationScriptPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    source: str | None = Field(default=None, min_length=1, max_length=500000)
    filename: str | None = Field(default=None, min_length=1, max_length=300)
    secret_placeholders: list[str] | None = Field(default=None, max_length=100)
    review_note: str | None = Field(default=None, max_length=5000)


class AutomationScriptApproval(BaseModel):
    expected_revision: int = Field(ge=1)
    review_note: str = Field(min_length=2, max_length=5000)


class ProjectConnectorCreate(BaseModel):
    provider: Literal["jira", "github", "gitlab", "azure_devops"]
    connector_reference: str = Field(min_length=15, max_length=500)
    external_target: str = Field(min_length=2, max_length=500)
    confirm_external_target: bool
    field_mapping: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_platform_connector(self):
        if not self.connector_reference.startswith("connector://"):
            raise ValueError("Kết nối phải dùng tham chiếu connector của nền tảng")
        if not self.confirm_external_target:
            raise ValueError("Phải xác nhận chính xác đích bên ngoài")
        return self


class ProjectConnectorPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    external_target: str | None = Field(default=None, min_length=2, max_length=500)
    confirm_external_target: bool = False
    field_mapping: dict[str, str] | None = None
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_target_confirmation(self):
        if self.external_target is not None and not self.confirm_external_target:
            raise ValueError("Phải xác nhận chính xác đích bên ngoài")
        return self


class ProjectConnectorUnbind(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=2000)
    confirm_external_target: bool


class ConnectorSyncInput(BaseModel):
    direction: Literal["PULL", "PUSH", "BIDIRECTIONAL"]
    scopes: list[Literal["requirements", "defects", "statuses"]] = Field(min_length=1, max_length=3)
    idempotency_key: str = Field(min_length=8, max_length=200)


class ConnectorConflictResolution(BaseModel):
    expected_revision: int = Field(ge=1)
    resolution: Literal["KEEP_LOCAL", "KEEP_REMOTE", "MERGED"]
    merged_value: dict[str, Any] | None = None
    reason: str = Field(min_length=2, max_length=2000)

    @model_validator(mode="after")
    def validate_merged_value(self):
        if self.resolution == "MERGED" and self.merged_value is None:
            raise ValueError("Phải cung cấp dữ liệu đã hợp nhất")
        return self


class AutomationExecutionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    runner: Literal["newman", "playwright"] = "newman"
    postman_artifact_id: str | None = Field(default=None, min_length=1, max_length=200)
    automation_script_id: str | None = Field(default=None, min_length=1, max_length=200)
    environment_id: str | None = Field(default=None, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=200)

    @model_validator(mode="after")
    def validate_runner_artifact(self):
        if self.runner == "newman" and (not self.postman_artifact_id or self.automation_script_id):
            raise ValueError("Newman yêu cầu đúng một collection Postman")
        if self.runner == "playwright" and (
            not self.automation_script_id or self.postman_artifact_id
        ):
            raise ValueError("Playwright yêu cầu đúng một kịch bản đã phê duyệt")
        return self


class AutomationExecutionAction(BaseModel):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)


class AutomationExecutionResultInput(BaseModel):
    execution_id: str = Field(min_length=1, max_length=200)
    operation_id: str = Field(min_length=1, max_length=200)
    status: AutomationExecutionStatus
    summary: dict[str, Any] = Field(default_factory=dict)
    results: list[dict[str, Any]] = Field(default_factory=list, max_length=100000)
    logs: list[str] = Field(default_factory=list, max_length=10000)
    artifact_refs: list[str] = Field(default_factory=list, max_length=1000)
    context_signature: str = Field(min_length=64, max_length=64)


class JUnitUnresolvedMappingInput(BaseModel):
    expected_revision: int = Field(ge=1)
    unresolved_index: int = Field(ge=0)
    test_case_version_id: str = Field(min_length=1, max_length=200)


class CiCdBindingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    connector_id: str = Field(min_length=1, max_length=200)
    pipeline_reference: str = Field(min_length=12, max_length=500)
    postman_artifact_id: str | None = Field(default=None, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    test_case_version_ids: list[str] = Field(default_factory=list, max_length=5000)

    @field_validator("pipeline_reference")
    @classmethod
    def validate_pipeline_reference(cls, value):
        if not value.startswith("pipeline://"):
            raise ValueError("Pipeline phải dùng tham chiếu cấu hình của nền tảng")
        return value


class CiCdBindingPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    pipeline_reference: str | None = Field(default=None, min_length=12, max_length=500)
    postman_artifact_id: str | None = Field(default=None, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    test_case_version_ids: list[str] | None = Field(default=None, max_length=5000)
    enabled: bool | None = None

    @field_validator("pipeline_reference")
    @classmethod
    def validate_optional_pipeline_reference(cls, value):
        if value is not None and not value.startswith("pipeline://"):
            raise ValueError("Pipeline phải dùng tham chiếu cấu hình của nền tảng")
        return value


class CiCdTriggerInput(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    binding_id: str = Field(min_length=1, max_length=200)
    external_run_id: str = Field(min_length=1, max_length=300)
    commit_reference: str | None = Field(default=None, max_length=300)
    idempotency_key: str = Field(min_length=8, max_length=200)
    context_signature: str = Field(min_length=64, max_length=64)


class CiCdResultInput(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    pipeline_run_id: str = Field(min_length=1, max_length=200)
    status: AutomationExecutionStatus
    summary: dict[str, Any] = Field(default_factory=dict)
    results: list[dict[str, Any]] = Field(default_factory=list, max_length=100000)
    logs: list[str] = Field(default_factory=list, max_length=10000)
    context_signature: str = Field(min_length=64, max_length=64)


class CiCdRetryInput(BaseModel):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)
    reason: str = Field(min_length=2, max_length=2000)


class CollaborationPresenceInput(BaseModel):
    artifact_type: Literal["requirement", "test_case"]
    artifact_id: str = Field(min_length=1, max_length=200)
    client_id: str = Field(min_length=8, max_length=200)


class CollaborationOperationInput(BaseModel):
    base_revision: int = Field(ge=1)
    operation_id: str = Field(min_length=8, max_length=200)
    changes: dict[str, Any] = Field(min_length=1, max_length=100)


class CollaborationConflictResolution(BaseModel):
    expected_revision: int = Field(ge=1)
    resolution: Literal["KEEP_CURRENT", "APPLY_INCOMING", "MERGED"]
    merged_changes: dict[str, Any] | None = None
    reason: str = Field(min_length=2, max_length=2000)

    @model_validator(mode="after")
    def validate_collaboration_merge(self):
        if self.resolution == "MERGED" and self.merged_changes is None:
            raise ValueError("Phải cung cấp nội dung hợp nhất")
        return self
