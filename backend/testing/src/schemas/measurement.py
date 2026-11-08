from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MetricKey = Literal[
    "REQUIREMENT_COVERAGE",
    "AC_COVERAGE",
    "ACCEPTANCE_CRITERION_COVERAGE",
    "CONDITION_COVERAGE",
    "TEST_CONDITION_COVERAGE",
    "RISK_COVERAGE",
    "EXECUTION_PROGRESS",
    "PASS_RATE",
    "BLOCKED_RATE",
    "DEFECT_REOPEN_RATE",
    "CRITICAL_DEFECT_AGING",
    "MEAN_TIME_TO_RETEST",
    "STALE_TEST_RATIO",
    "REQUIREMENT_VOLATILITY",
    "IMPACT_PROPOSAL_ACCEPTANCE_RATE",
    "REGRESSION_EFFECTIVENESS",
    "AUTOMATION_COVERAGE",
    "AUTOMATION_STABILITY",
    "AUTOMATION_PASS_STABILITY",
    "ESCAPED_DEFECT_RATE",
    "DEFECT_REMOVAL_EFFICIENCY",
]
def validate_threshold_order(key, target, warning_threshold, critical_threshold):
    if (
        warning_threshold is not None
        and critical_threshold is not None
        and warning_threshold == critical_threshold
    ):
        raise ValueError("Ngưỡng cảnh báo và nghiêm trọng phải khác nhau")
    populated = [
        value for value in (target, warning_threshold, critical_threshold) if value is not None
    ]
    expected = sorted(populated) if key in {"BLOCKED_RATE", "DEFECT_REOPEN_RATE", "CRITICAL_DEFECT_AGING", "MEAN_TIME_TO_RETEST", "STALE_TEST_RATIO", "REQUIREMENT_VOLATILITY", "ESCAPED_DEFECT_RATE"} else sorted(populated, reverse=True)
    if populated != expected:
        raise ValueError("Thứ tự ngưỡng không phù hợp với chiều đánh giá của metric")


class MeasurementDefinitionCreate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    key: MetricKey
    name: str = Field(min_length=2, max_length=300)
    objective: str = Field(min_length=2, max_length=2000)
    description: str = Field(default="", max_length=5000)
    formula_type: Literal[
        "BUILT_IN", "RATIO", "COUNT", "DURATION", "PERCENTILE", "CUSTOM_SAFE_EXPRESSION"
    ] = "BUILT_IN"
    formula: str = Field(min_length=1, max_length=1000)
    unit: str = Field(min_length=1, max_length=50)
    data_sources: list[str] = Field(min_length=1, max_length=50)
    dimensions: list[str] = Field(default_factory=list, max_length=50)
    aggregation: Literal["LATEST", "SUM", "AVERAGE", "RATIO", "COUNT", "DURATION", "PERCENTILE"]
    period: Literal["ON_DEMAND", "DAILY", "WEEKLY", "SPRINT", "RELEASE"]
    target: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    owner_role: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")

    @field_validator("owner_role")
    @classmethod
    def normalize_owner_role(cls, value):
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_thresholds(self):
        validate_threshold_order(
            self.key, self.target, self.warning_threshold, self.critical_threshold
        )
        return self


class MeasurementDefinitionPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    objective: str | None = Field(default=None, min_length=2, max_length=2000)
    description: str | None = Field(default=None, max_length=5000)
    formula_type: (
        Literal["BUILT_IN", "RATIO", "COUNT", "DURATION", "PERCENTILE", "CUSTOM_SAFE_EXPRESSION"]
        | None
    ) = None
    formula: str | None = Field(default=None, min_length=1, max_length=1000)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    data_sources: list[str] | None = Field(default=None, min_length=1, max_length=50)
    dimensions: list[str] | None = Field(default=None, max_length=50)
    aggregation: (
        Literal["LATEST", "SUM", "AVERAGE", "RATIO", "COUNT", "DURATION", "PERCENTILE"] | None
    ) = None
    period: Literal["ON_DEMAND", "DAILY", "WEEKLY", "SPRINT", "RELEASE"] | None = None
    target: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    owner_role: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")

    @field_validator("owner_role")
    @classmethod
    def normalize_owner_role(cls, value):
        return value.strip().upper() if value else value


class MeasurementTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    status: Literal["ACTIVE", "ARCHIVED"]
    note: str = Field(default="", max_length=2000)


class MeasurementSnapshotCreate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    definition_id: str = Field(min_length=1, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    dimensions: dict[str, Any] = Field(default_factory=dict)


class MeasurementVersionCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)
    note: str = Field(default="", max_length=2000)


class MetricDashboardPin(BaseModel):
    pinned: bool = True
