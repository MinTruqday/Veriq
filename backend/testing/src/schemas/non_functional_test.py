from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator


class NonFunctionalTestPlanCreate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    plan_type: Literal["SECURITY_TEST_PLAN", "PERFORMANCE_TEST_PLAN"]
    name: str = Field(min_length=2, max_length=500)
    objective: str = Field(min_length=2, max_length=5000)
    scope: list[str] = Field(min_length=1, max_length=500)
    approach: str = Field(min_length=2, max_length=10000)
    entry_criteria: list[str] = Field(default_factory=list, max_length=200)
    exit_criteria: list[str] = Field(default_factory=list, max_length=200)
    test_conditions: list[str] = Field(
        default_factory=list,
        max_length=1000,
        validation_alias=AliasChoices("test_conditions", "test_condition_ids"),
    )
    test_cases: list[str] = Field(
        default_factory=list,
        max_length=5000,
        validation_alias=AliasChoices("test_cases", "test_case_version_ids"),
    )
    requirement_refs: list[str] = Field(
        default_factory=list,
        max_length=5000,
        validation_alias=AliasChoices("requirement_refs", "requirement_version_ids"),
    )
    source_ai_result_ids: list[str] = Field(default_factory=list, max_length=100)
    tool_refs: list[str] = Field(
        default_factory=list, max_length=100, validation_alias=AliasChoices("tool_refs", "tools")
    )
    risk_refs: list[str] = Field(default_factory=list, max_length=500)
    categories: list[str] = Field(default_factory=list, max_length=100)
    environment: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any] | str] = Field(default_factory=list, max_length=1000)
    result_summary: dict[str, Any] = Field(default_factory=dict)
    residual_risk: list[dict[str, Any] | str] = Field(default_factory=list, max_length=500)
    workload_model: dict[str, Any] = Field(default_factory=dict)
    baseline: dict[str, Any] = Field(default_factory=dict)
    load: dict[str, Any] = Field(default_factory=dict)
    stress: dict[str, Any] = Field(default_factory=dict)
    spike: dict[str, Any] = Field(default_factory=dict)
    soak: dict[str, Any] = Field(default_factory=dict)
    concurrency: int | dict[str, Any] | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)
    throughput_target: float | None = Field(default=None, ge=0)
    response_time_target: float | dict[str, Any] | None = None
    error_rate_target: float | None = Field(default=None, ge=0, le=100)
    data: dict[str, Any] = Field(default_factory=dict)
    external_tool_ref: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_trace(self):
        if not self.test_conditions and not self.test_cases:
            raise ValueError("Kế hoạch NFR phải truy vết tới TestCondition hoặc TestCase")
        return self


class NonFunctionalTestPlanPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=500)
    objective: str | None = Field(default=None, min_length=2, max_length=5000)
    scope: list[str] | None = Field(default=None, min_length=1, max_length=500)
    approach: str | None = Field(default=None, min_length=2, max_length=10000)
    entry_criteria: list[str] | None = Field(default=None, max_length=200)
    exit_criteria: list[str] | None = Field(default=None, max_length=200)
    test_conditions: list[str] | None = Field(
        default=None,
        max_length=1000,
        validation_alias=AliasChoices("test_conditions", "test_condition_ids"),
    )
    test_cases: list[str] | None = Field(
        default=None,
        max_length=5000,
        validation_alias=AliasChoices("test_cases", "test_case_version_ids"),
    )
    requirement_refs: list[str] | None = Field(
        default=None,
        max_length=5000,
        validation_alias=AliasChoices("requirement_refs", "requirement_version_ids"),
    )
    tool_refs: list[str] | None = Field(
        default=None, max_length=100, validation_alias=AliasChoices("tool_refs", "tools")
    )
    risk_refs: list[str] | None = Field(default=None, max_length=500)
    categories: list[str] | None = Field(default=None, max_length=100)
    environment: dict[str, Any] | None = None
    evidence: list[dict[str, Any] | str] | None = Field(default=None, max_length=1000)
    result_summary: dict[str, Any] | None = None
    residual_risk: list[dict[str, Any] | str] | None = Field(default=None, max_length=500)
    workload_model: dict[str, Any] | None = None
    baseline: dict[str, Any] | None = None
    load: dict[str, Any] | None = None
    stress: dict[str, Any] | None = None
    spike: dict[str, Any] | None = None
    soak: dict[str, Any] | None = None
    concurrency: int | dict[str, Any] | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)
    throughput_target: float | None = Field(default=None, ge=0)
    response_time_target: float | dict[str, Any] | None = None
    error_rate_target: float | None = Field(default=None, ge=0, le=100)
    data: dict[str, Any] | None = None
    external_tool_ref: str | None = Field(default=None, max_length=1000)


class NonFunctionalTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=5000)


class ApprovedPerformanceConfigurationGeneration(BaseModel):
    plan_id: str = Field(min_length=1, max_length=200)
    source_event_id: str = Field(min_length=1, max_length=240)
    source_event_revision: int = Field(ge=1)


class ExternalTestEvidenceImport(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    provider: Literal["GENERIC", "K6", "JMETER", "OWASP_ZAP", "PLAYWRIGHT"] = "GENERIC"
    external_run_ref: str = Field(min_length=1, max_length=500)
    executed_at: datetime
    evidence_refs: list[str] = Field(min_length=1, max_length=1000)
    result_summary: dict[str, Any] = Field(min_length=1, max_length=500)
    raw_result_hash: str = Field(min_length=32, max_length=128)

    @model_validator(mode="after")
    def validate_executed_at(self):
        if self.executed_at.tzinfo is None:
            raise ValueError("Thời điểm thực thi phải có múi giờ")
        return self
