from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProjectCompletenessInput(BaseModel):
    model_config = {"extra": "forbid"}

    document_ids: list[str] = Field(default_factory=list, max_length=5000)
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=5000)
    stage: Literal["REQUIREMENTS", "TEST_PLANNING", "TEST_DESIGN", "EXECUTION_READINESS", "RELEASE_READINESS"]
    scope_description: str = Field(min_length=5, max_length=1500)
    out_of_scope: str = Field(default="", max_length=1000)
    instruction: str = Field(default="", max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=150)
    output_language: str | None = Field(default=None, min_length=2, max_length=35, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")

    @field_validator("document_ids", "requirement_version_ids")
    @classmethod
    def validate_source_ids(cls, values):
        if len(values) != len(set(values)) or any(not value.strip() or len(value) > 200 for value in values):
            raise ValueError("PROJECT_COMPLETENESS_SOURCE_IDS_INVALID")
        return values

    @field_validator("scope_description")
    @classmethod
    def validate_scope_description(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("PROJECT_COMPLETENESS_SCOPE_REQUIRED")
        return value
