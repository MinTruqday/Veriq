from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class JUnitUnresolvedMappingInput(BaseModel):
    expected_revision: int = Field(ge=1)
    unresolved_index: int = Field(ge=0)
    test_case_version_id: str = Field(min_length=1, max_length=200)


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
