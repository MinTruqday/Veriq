import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.schemas.contracts.common import ControlActionStatus


class MonitoringSnapshotCreate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    test_plan_id: str = Field(min_length=1, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    actual_effort: float | None = Field(default=None, ge=0)
    expected_completion: datetime | None = None
    risks: list[dict[str, Any] | str] = Field(default_factory=list, max_length=500)
    blockers: list[dict[str, Any] | str] = Field(default_factory=list, max_length=500)


class ControlActionCreate(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=200)
    type: Literal[
        "PAUSE_EXECUTION",
        "RESUME_EXECUTION",
        "REQUEST_RETEST",
        "CREATE_ADDITIONAL_TEST_SCOPE",
        "REQUEST_NEW_BUILD",
        "BLOCK_RELEASE",
        "ACCEPT_RISK",
        "ESCALATE_DEFECT",
        "REPRIORITIZE_REGRESSION",
        "EXTEND_TEST_WINDOW",
    ]
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(default="", max_length=5000)
    owner_id: str = Field(min_length=1, max_length=200)
    due_at: datetime
    priority: str = Field(min_length=1, max_length=100)
    decision_reason: str = Field(min_length=2, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=500)


class ControlActionPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    owner_id: str | None = Field(default=None, min_length=1, max_length=200)
    due_at: datetime | None = None
    priority: str | None = Field(default=None, min_length=1, max_length=100)
    status: ControlActionStatus | None = None
    decision_reason: str | None = Field(default=None, min_length=2, max_length=5000)
    evidence_refs: list[str] | None = Field(default=None, max_length=500)


class ExitCriterionOverride(BaseModel):
    expected_revision: int = Field(ge=1)
    criterion_id: str = Field(min_length=1, max_length=200)
    status: Literal["PASS", "FAIL"]
    reason: str = Field(min_length=2, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=500)


class ExitCriterionDefinition(BaseModel):
    criterion_id: str = Field(min_length=1, max_length=200)
    criterion: str = Field(min_length=1, max_length=500)
    type: Literal[
        "EXECUTION_PERCENT_MIN",
        "PASS_RATE_MIN",
        "OPEN_BLOCKER_MAX",
        "OPEN_CRITICAL_MAX",
        "REQUIREMENT_COVERAGE_MIN",
        "AC_COVERAGE_MIN",
        "CONDITION_COVERAGE_MIN",
        "STALE_TESTCASE_MAX",
        "ENVIRONMENT_INCIDENT_MAX",
        "REQUIRED_RUNS_COMPLETED",
        "CUSTOM_MANUAL_GATE",
    ]
    threshold: float | int | list[str] | bool

    @model_validator(mode="after")
    def validate_threshold(self):
        if self.type == "REQUIRED_RUNS_COMPLETED" and not isinstance(self.threshold, list):
            raise ValueError("REQUIRED_RUNS_COMPLETED cần danh sách run")
        if self.type == "CUSTOM_MANUAL_GATE" and not isinstance(self.threshold, bool):
            raise ValueError("CUSTOM_MANUAL_GATE cần ngưỡng boolean")
        if self.type not in {"REQUIRED_RUNS_COMPLETED", "CUSTOM_MANUAL_GATE"} and isinstance(
            self.threshold, (list, bool)
        ):
            raise ValueError("Ngưỡng số không hợp lệ")
        return self


class QualityDecisionCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    decision: Literal["APPROVE_RELEASE", "BLOCK_RELEASE", "ACCEPT_RISK"]
    reason: str = Field(min_length=2, max_length=5000)
    risk_acceptance: dict[str, Any] | None = None
    override_reason: str | None = Field(default=None, min_length=2, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=500)
    supersedes_decision_id: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_risk_acceptance(self):
        if self.decision == "ACCEPT_RISK":
            value = self.risk_acceptance or {}
            if not value.get("risks") or not value.get("owner_id") or not value.get("expiry_at"):
                raise ValueError(
                    "Chấp nhận rủi ro cần danh sách rủi ro người chịu trách nhiệm và ngày hết hạn"
                )
        return self


def source_fingerprint(value):
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
