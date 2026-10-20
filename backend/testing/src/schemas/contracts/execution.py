from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.schemas.contracts.common import (
    NOT_APPLICABLE_OUTCOME,
    TestExecutionStatus,
    TestOutcome,
    empty_doc,
)
from src.schemas.contracts.planning import (
    TestPlanCommunication,
    TestPlanEstimation,
    TestPlanMilestone,
    TestPlanResponsibility,
    TestPlanRisk,
    TestPlanSchedule,
)

class TestPlanPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    objective: str | None = Field(default=None, max_length=5000)
    scope_in: list[str] | None = Field(default=None, max_length=500)
    scope_out: list[str] | None = Field(default=None, max_length=500)
    requirement_version_ids: list[str] | None = Field(default=None, max_length=2000)
    test_suite_ids: list[str] | None = Field(default=None, max_length=500)
    test_case_version_ids: list[str] | None = Field(default=None, max_length=5000)
    environment: str | None = Field(default=None, max_length=200)
    environment_id: str | None = Field(default=None, max_length=200)
    entry_criteria: list[str] | None = Field(default=None, max_length=200)
    exit_criteria: list[str] | None = Field(default=None, max_length=200)
    risks: list[str] | None = Field(default=None, max_length=200)
    test_types: list[str] | None = Field(default=None, max_length=100)
    members: list[str] | None = Field(default=None, max_length=500)
    release: str | None = Field(default=None, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    build: str | None = Field(default=None, max_length=200)
    build_id: str | None = Field(default=None, max_length=200)
    strategy_version_id: str | None = Field(default=None, max_length=200)
    test_level: str | None = Field(default=None, min_length=1, max_length=100)
    test_approach: str | None = Field(default=None, max_length=10000)
    assumptions: list[str] | None = Field(default=None, max_length=200)
    constraints: list[str] | None = Field(default=None, max_length=200)
    dependencies: list[dict[str, Any]] | None = Field(default=None, max_length=500)
    stakeholders: list[dict[str, Any]] | None = Field(default=None, max_length=500)
    responsibility_matrix: list[TestPlanResponsibility] | None = Field(default=None, max_length=500)
    estimation: TestPlanEstimation | None = None
    schedule: TestPlanSchedule | None = None
    milestones: list[TestPlanMilestone] | None = Field(default=None, max_length=500)
    deliverables: list[dict[str, Any] | str] | None = Field(default=None, max_length=500)
    tools: list[dict[str, Any] | str] | None = Field(default=None, max_length=200)
    suspension_criteria: list[str] | None = Field(default=None, max_length=200)
    resumption_criteria: list[str] | None = Field(default=None, max_length=200)
    monitoring_metrics: list[dict[str, Any]] | None = Field(default=None, max_length=200)
    quality_targets: list[dict[str, Any]] | None = Field(default=None, max_length=200)
    risk_register: list[TestPlanRisk] | None = Field(default=None, max_length=500)
    communication_plan: TestPlanCommunication | None = None


class TestSuiteCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=2, max_length=300)
    suite_type: Literal[
        "smoke", "regression", "sanity", "feature", "api", "ui", "integration", "custom"
    ]
    test_case_version_ids: list[str] = Field(default_factory=list, max_length=5000)


class TestSuitePatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    suite_type: (
        Literal["smoke", "regression", "sanity", "feature", "api", "ui", "integration", "custom"]
        | None
    ) = None
    test_case_version_ids: list[str] | None = Field(default=None, max_length=5000)


class TestRunCreate(BaseModel):
    project_id: str
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    name: str = Field(min_length=2, max_length=300)
    test_plan_id: str | None = None
    test_suite_ids: list[str] = Field(default_factory=list, max_length=500)
    test_case_version_ids: list[str] = Field(default_factory=list, max_length=5000)
    environment: str = Field(default="staging", max_length=200)
    environment_id: str | None = Field(default=None, max_length=200)
    release: str = Field(default="", max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    build: str = Field(default="", max_length=200)
    build_id: str | None = Field(default=None, max_length=200)


class TestRunPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    test_plan_id: str | None = None
    test_suite_ids: list[str] | None = Field(default=None, max_length=500)
    test_case_version_ids: list[str] | None = Field(default=None, max_length=5000)
    environment: str | None = Field(default=None, max_length=200)
    environment_id: str | None = Field(default=None, max_length=200)
    release: str | None = Field(default=None, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    build: str | None = Field(default=None, max_length=200)
    build_id: str | None = Field(default=None, max_length=200)


class TestRunAssignmentInput(BaseModel):
    expected_revision: int = Field(ge=1)
    assignee_id: str = Field(min_length=1, max_length=200)
    test_case_assignments: dict[str, str] = Field(default_factory=dict)


class TestRunResumeInput(BaseModel):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)


class TestStepResultInput(BaseModel):
    step_id: str = Field(min_length=1, max_length=200)
    status: TestOutcome
    actual_doc: dict[str, Any] = Field(default_factory=empty_doc)
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def require_not_applicable_reason(self):
        if self.status == NOT_APPLICABLE_OUTCOME and len(self.note.strip()) < 2:
            raise ValueError("Kết quả Không áp dụng của bước phải có lý do")
        return self


class TestResultInput(BaseModel):
    status: TestOutcome
    step_results: list[TestStepResultInput] = Field(default_factory=list, max_length=500)
    actual_result_doc: dict[str, Any] = Field(default_factory=empty_doc)
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    note: str = Field(default="", max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=200)

    @model_validator(mode="after")
    def require_not_applicable_reason(self):
        if self.status == NOT_APPLICABLE_OUTCOME and len(self.note.strip()) < 2:
            raise ValueError("Kết quả Không áp dụng phải có lý do")
        return self


class TestExecutionPatch(BaseModel):
    status: TestExecutionStatus
    step_results: list[TestStepResultInput] = Field(default_factory=list, max_length=500)
    actual_result_doc: dict[str, Any] = Field(default_factory=empty_doc)
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    note: str = Field(default="", max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=200)
    expected_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_not_applicable_reason(self):
        if self.status == NOT_APPLICABLE_OUTCOME and len(self.note.strip()) < 2:
            raise ValueError("Kết quả Không áp dụng phải có lý do")
        return self


class TestResultCorrectionInput(BaseModel):
    status: TestOutcome
    reason: str = Field(min_length=2, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=200)
