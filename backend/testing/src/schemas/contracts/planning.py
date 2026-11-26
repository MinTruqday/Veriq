from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


from src.schemas.contracts.common import TestPlanRiskStatus


class TestPlanSuiteSnapshot(BaseModel):
    test_suite_id: str = Field(min_length=1, max_length=200)
    revision: int = Field(ge=1)
    test_case_version_ids: list[str] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def unique_test_case_versions(self):
        if len(self.test_case_version_ids) != len(set(self.test_case_version_ids)):
            raise ValueError("TEST_PLAN_SUITE_SNAPSHOT_VERSIONS_MUST_BE_UNIQUE")
        return self


class TestPlanSchedule(BaseModel):
    planned_start_at: str | None = Field(default=None, max_length=80)
    planned_end_at: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_schedule_order(self):
        if self.planned_start_at and self.planned_end_at:
            try:
                start = datetime.fromisoformat(self.planned_start_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(self.planned_end_at.replace("Z", "+00:00"))
                if (start.tzinfo is None) != (end.tzinfo is None):
                    raise ValueError("TEST_PLAN_SCHEDULE_TIMEZONE_MISMATCH")
                if start > end:
                    raise ValueError("TEST_PLAN_SCHEDULE_END_BEFORE_START")
            except (TypeError, ValueError) as error:
                if str(error).startswith("TEST_PLAN_SCHEDULE_"):
                    raise
                raise ValueError("TEST_PLAN_SCHEDULE_INVALID") from error
        return self


class TestPlanSuggestionInput(BaseModel):
    requirement_version_ids: list[str] = Field(min_length=1, max_length=100)
    instruction: str = Field(default="", max_length=5000)

    @field_validator("requirement_version_ids")
    @classmethod
    def unique_requirement_versions(cls, values):
        normalized = [str(value).strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("TEST_PLAN_REQUIREMENT_VERSION_ID_REQUIRED")
        if len(normalized) != len(set(normalized)):
            raise ValueError("TEST_PLAN_REQUIREMENT_VERSION_IDS_MUST_BE_UNIQUE")
        return normalized


class TestPlanRisk(BaseModel):
    category: Literal["PRODUCT", "PROJECT"] | None = None
    risk_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    probability: float | None = Field(default=None, ge=0)
    impact: float | None = Field(default=None, ge=0)
    exposure: float | None = Field(default=None, ge=0)
    response: str = Field(default="", max_length=5000)
    owner_id: str | None = Field(default=None, max_length=200)
    status: TestPlanRiskStatus = TestPlanRiskStatus.OPEN
    due_at: str | None = Field(default=None, max_length=80)


class TestPlanCarryOver(BaseModel):
    source_test_run_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_test_plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    test_case_version_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def require_one_source(self):
        if bool(self.source_test_run_id) == bool(self.source_test_plan_id):
            raise ValueError("CARRY_OVER_REQUIRES_ONE_SOURCE")
        return self

    @field_validator("reason")
    @classmethod
    def require_non_blank_reason(cls, value):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("CARRY_OVER_REASON_REQUIRED")
        return cleaned


class TestPlanInlinePeriodCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    source_period_id: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("TEST_PERIOD_NAME_REQUIRED")
        return cleaned


class TestPlanCreate(BaseModel):
    save_as_draft: bool = True
    test_period_id: str | None = Field(default=None, max_length=200)
    new_test_period: "TestPlanInlinePeriodCreate | None" = None
    carry_over_items: list[TestPlanCarryOver] = Field(default_factory=list, max_length=5000)
    owner_id: str | None = Field(default=None, max_length=200)
    project_id: str
    name: str = Field(min_length=2, max_length=300)
    objective: str = Field(default="", max_length=5000)
    scope_out: list[str] = Field(default_factory=list, max_length=500)
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=2000)
    test_suite_ids: list[str] = Field(default_factory=list, max_length=500)
    test_case_version_ids: list[str] = Field(default_factory=list, max_length=5000)
    environment_id: str | None = Field(default=None, max_length=200)
    entry_criteria: list[str] = Field(default_factory=list, max_length=200)
    exit_criteria: list[str] = Field(default_factory=list, max_length=200)
    test_types: list[str] = Field(default_factory=list, max_length=100)
    test_level: str | None = Field(default=None, min_length=1, max_length=100)
    schedule: TestPlanSchedule = Field(default_factory=TestPlanSchedule)
    risk_register: list[TestPlanRisk] = Field(default_factory=list, max_length=500)
