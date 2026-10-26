import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.schemas.contracts.common import (
    CompletionRecommendation,
    ImprovementActionStatus,
    ResidualRiskStatus,
    ResidualRiskTreatment,
    TestwareHandoverStatus,
)


class ResidualRisk(BaseModel):
    risk_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=2, max_length=500)
    description: str = Field(default="", max_length=5000)
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    probability: Literal["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW"] = "MEDIUM"
    impact: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    source_refs: list[str] = Field(default_factory=list, max_length=500)
    owner_id: str = Field(min_length=1, max_length=200)
    treatment: ResidualRiskTreatment = ResidualRiskTreatment.PENDING
    acceptance: ResidualRiskTreatment = ResidualRiskTreatment.PENDING
    acceptance_reason: str = Field(default="", max_length=5000)
    accepted_by: str | None = Field(default=None, max_length=200)
    accepted_at: datetime | None = None
    expiry_at: datetime | None = None
    status: ResidualRiskStatus = ResidualRiskStatus.OPEN

    @model_validator(mode="before")
    @classmethod
    def normalize_treatment(cls, value):
        if isinstance(value, dict):
            normalized = dict(value)
            treatment = (
                normalized.get("treatment")
                or normalized.get("acceptance")
                or ResidualRiskTreatment.PENDING
            )
            normalized["treatment"] = treatment
            normalized["acceptance"] = treatment
            return normalized
        return value

    @model_validator(mode="after")
    def validate_acceptance(self):
        if self.treatment != ResidualRiskTreatment.PENDING and (
            not self.acceptance_reason.strip() or not self.accepted_by
        ):
            raise ValueError("Residual risk đã xử lý phải có lý do và người chấp nhận")
        return self


class TestwareHandoverItem(BaseModel):
    artifact_type: str = Field(min_length=1, max_length=100)
    artifact_id: str = Field(min_length=1, max_length=200)
    artifact_version_id: str | None = Field(default=None, max_length=200)
    handover_to: str = Field(min_length=1, max_length=500)
    storage_location: str = Field(min_length=1, max_length=2000)
    status: TestwareHandoverStatus = TestwareHandoverStatus.PENDING
    note: str = Field(default="", max_length=5000)


class LessonsLearnedItem(BaseModel):
    lesson_id: str | None = Field(default=None, max_length=200)
    category: Literal["WORKED", "FAILED", "BLOCKER", "IMPROVEMENT", "OTHER"] = "OTHER"
    observation: str = Field(min_length=2, max_length=5000)
    impact: str = Field(default="", max_length=5000)
    recommendation: str = Field(default="", max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=500)
    owner_id: str | None = Field(default=None, max_length=200)
    convert_to_improvement: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_observation(cls, value):
        if isinstance(value, dict) and not value.get("observation"):
            normalized = dict(value)
            normalized["observation"] = normalized.get("text") or normalized.get("lesson") or ""
            return normalized
        return value


class UnexecutedScopeItem(BaseModel):
    item_id: str = Field(min_length=1, max_length=200)
    item_type: str = Field(min_length=1, max_length=100)
    reason: str = Field(default="", max_length=5000)
    source_refs: list[str] = Field(default_factory=list, max_length=500)


class ImprovementAction(BaseModel):
    action_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=2, max_length=500)
    owner_id: str = Field(min_length=1, max_length=200)
    due_at: datetime | None = None
    status: ImprovementActionStatus = ImprovementActionStatus.OPEN
    evidence_refs: list[str] = Field(default_factory=list, max_length=500)


class TestCompletionCreate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    snapshot_id: str = Field(min_length=1, max_length=200)
    build_id: str = Field(min_length=1, max_length=200)
    unresolved_items: list[dict[str, Any] | str] = Field(default_factory=list, max_length=1000)
    unexecuted_scope: list[UnexecutedScopeItem] = Field(default_factory=list, max_length=1000)
    residual_risks: list[ResidualRisk] = Field(default_factory=list, max_length=500)
    deviations: list[dict[str, Any] | str] = Field(default_factory=list, max_length=500)
    testware_handover: list[TestwareHandoverItem] = Field(default_factory=list, max_length=1000)
    archived_artifacts: list[dict[str, Any] | str] = Field(default_factory=list, max_length=1000)
    environment_closure: list[dict[str, Any] | str] = Field(default_factory=list, max_length=500)
    lessons_learned: list[LessonsLearnedItem] = Field(default_factory=list, max_length=500)
    improvement_actions: list[ImprovementAction] = Field(default_factory=list, max_length=500)
    recommendation: CompletionRecommendation | None = None


class TestCompletionPatch(BaseModel):
    model_config = {"extra": "forbid"}

    expected_revision: int = Field(ge=1)
    unresolved_items: list[dict[str, Any] | str] | None = Field(default=None, max_length=1000)
    unexecuted_scope: list[UnexecutedScopeItem] | None = Field(default=None, max_length=1000)
    residual_risks: list[ResidualRisk] | None = Field(default=None, max_length=500)
    testware_handover: list[TestwareHandoverItem] | None = Field(default=None, max_length=1000)
    lessons_learned: list[LessonsLearnedItem] | None = Field(default=None, max_length=500)
    improvement_actions: list[ImprovementAction] | None = Field(default=None, max_length=500)
    executive_summary: str | None = Field(default=None, max_length=10000)
    closure_summary: str | None = Field(default=None, max_length=10000)
    residual_risk_summary: str | None = Field(default=None, max_length=10000)
    recommendation_rationale: str | None = Field(default=None, max_length=10000)


class ResidualRiskCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    risk: ResidualRisk


class LessonLearnedCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    lesson: LessonsLearnedItem


class TestwareHandoverManage(BaseModel):
    expected_revision: int = Field(ge=1)
    item: TestwareHandoverItem


class CompletionTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=5000)


class CompletionSignOff(BaseModel):
    expected_revision: int = Field(ge=1)
    decision: Literal["APPROVE", "REJECT"]
    note: str = Field(default="", max_length=5000)


class ResidualRiskDecision(BaseModel):
    expected_revision: int = Field(ge=1)
    acceptance: ResidualRiskTreatment
    reason: str = Field(min_length=2, max_length=5000)


class TestCompletionAiDraft(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    instruction: str = Field(default="", max_length=5000)
    source_event_id: str = Field(min_length=1, max_length=200)
    source_event_revision: int = Field(ge=1)
    source_event_trigger: Literal["TEST_COMPLETION_REPORT_CREATED"]


def completion_snapshot(report):
    excluded = {
        "status",
        "revision",
        "created_by",
        "created_at",
        "updated_at",
        "submitted_by",
        "submitted_at",
        "reviewed_by",
        "reviewed_at",
        "approved_by",
        "approved_at",
        "closed_by",
        "closed_at",
        "approval_history",
        "review_history",
        "approved_snapshot",
        "approved_snapshot_hash",
        "automation_gate_snapshot",
        "automation_gate_hash",
        "change_request",
    }
    return {key: value for key, value in report.items() if key not in excluded}


def completion_hash(report):
    canonical = json.dumps(
        completion_snapshot(report),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
