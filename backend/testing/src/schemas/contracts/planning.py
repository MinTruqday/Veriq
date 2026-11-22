from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TestPlanAIDraftInput(BaseModel):
    requirement_version_ids: list[str] = Field(min_length=1, max_length=200)
    instruction: str = Field(default="", max_length=5000)
    current_test_plan: dict[str, Any] = Field(default_factory=dict)

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


class TestPlanEstimation(BaseModel):
    method: Literal["expert_judgment", "three_point", "historical", "custom"] = "expert_judgment"
    planned_effort_hours: float = Field(default=0, ge=0)
    basis: str = Field(default="", max_length=5000)
    effort_allocations: list["TestPlanEffortAllocation"] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_effort_allocations(self):
        allocation_ids = [item.user_id for item in self.effort_allocations]
        if len(allocation_ids) != len(set(allocation_ids)):
            raise ValueError("TEST_PLAN_EFFORT_ALLOCATION_DUPLICATE_USER")
        if self.effort_allocations:
            allocation_total = sum(item.planned_hours for item in self.effort_allocations)
            if round(allocation_total, 2) != round(self.planned_effort_hours, 2):
                raise ValueError("TEST_PLAN_EFFORT_ALLOCATION_TOTAL_MUST_MATCH_PLAN")
        return self


class TestPlanEffortAllocation(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    planned_hours: float = Field(gt=0, le=100000)


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


class TestPlanCommunication(BaseModel):
    channel: str = Field(default="", max_length=200)
    status_report_frequency: str = Field(default="", max_length=200)
    recipients: list[str] = Field(default_factory=list, max_length=500)
    escalation_roles: list[str] = Field(default_factory=list, max_length=100)


class TestPlanCreate(BaseModel):
    owner_id: str | None = Field(default=None, max_length=200)
    scenario_ids: list[str] = Field(default_factory=list, max_length=1000)
    project_id: str
    name: str = Field(min_length=2, max_length=300)
    objective: str = Field(default="", max_length=5000)
    scope_in: list[str] = Field(default_factory=list, max_length=500)
    scope_out: list[str] = Field(default_factory=list, max_length=500)
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=2000)
    test_suite_ids: list[str] = Field(default_factory=list, max_length=500)
    test_case_version_ids: list[str] = Field(default_factory=list, max_length=5000)
    environment: str = Field(default="", max_length=200)
    environment_id: str | None = Field(default=None, max_length=200)
    entry_criteria: list[str] = Field(default_factory=list, max_length=200)
    exit_criteria: list[str] = Field(default_factory=list, max_length=200)
    test_types: list[str] = Field(default_factory=list, max_length=100)
    members: list[str] = Field(default_factory=list, max_length=500)
    release: str = Field(default="", max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    build: str = Field(default="", max_length=200)
    build_id: str | None = Field(default=None, max_length=200)
    strategy_version_id: str | None = Field(default=None, max_length=200)
    test_level: str | None = Field(default=None, min_length=1, max_length=100)
    test_approach: str = Field(default="", max_length=10000)
    assumptions: list[str] = Field(default_factory=list, max_length=200)
    constraints: list[str] = Field(default_factory=list, max_length=200)
    dependencies: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    estimation: TestPlanEstimation = Field(default_factory=TestPlanEstimation)
    schedule: TestPlanSchedule = Field(default_factory=TestPlanSchedule)
    quality_targets: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    risk_register: list[TestPlanRisk] = Field(default_factory=list, max_length=500)
    communication_plan: TestPlanCommunication = Field(default_factory=TestPlanCommunication)
