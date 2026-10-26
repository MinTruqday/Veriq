from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.schemas.contracts.common import PreventionActionStatus

RootCauseCategory = Literal[
    "REQUIREMENT",
    "DESIGN",
    "IMPLEMENTATION",
    "CONFIGURATION",
    "TEST_DATA",
    "TEST_CASE_GAP",
    "ENVIRONMENT",
    "INTEGRATION",
    "DEPLOYMENT",
    "PROCESS",
    "THIRD_PARTY",
    "UNKNOWN",
]


class CausalAnalysisCreate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    defect_ids: list[str] = Field(default_factory=list, max_length=500)
    source_event_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_event_revision: int | None = Field(default=None, ge=1)
    source_event_trigger: Literal["DEFECT_RECORDED", "DEFECT_CHANGED"] | None = None
    problem_statement: str = Field(min_length=2, max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=1000)
    evidence: list[dict[str, Any] | str] = Field(default_factory=list, max_length=1000)
    owner_id: str = Field(min_length=1, max_length=200)
    effectiveness_review_at: datetime | None = None

    @model_validator(mode="after")
    def normalize_evidence(self):
        event_fields = (self.source_event_id, self.source_event_revision, self.source_event_trigger)
        if any(value is not None for value in event_fields) and not all(
            value is not None for value in event_fields
        ):
            raise ValueError("Thông tin sự kiện nguồn phải được cung cấp đầy đủ")
        if not self.evidence_refs:
            self.evidence_refs = [str(item) for item in self.evidence]
        if not self.evidence_refs:
            raise ValueError("Phân tích nguyên nhân phải có bằng chứng")
        return self


class CausalAnalysisPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    problem_statement: str | None = Field(default=None, min_length=2, max_length=10000)
    evidence_refs: list[str] | None = Field(default=None, min_length=1, max_length=1000)
    owner_id: str | None = Field(default=None, min_length=1, max_length=200)
    effectiveness_review_at: datetime | None = None


class CausalDefectLink(BaseModel):
    expected_revision: int = Field(ge=1)
    defect_ids: list[str] = Field(min_length=1, max_length=500)


class CausalFiveWhyInput(BaseModel):
    expected_revision: int = Field(ge=1)
    why: str = Field(min_length=2, max_length=5000)


class CausalRootCauseInput(BaseModel):
    expected_revision: int = Field(ge=1)
    category: RootCauseCategory
    detail: str = Field(min_length=2, max_length=5000)
    contributing_factors: list[str] = Field(default_factory=list, max_length=500)
    evidence_refs: list[str] = Field(min_length=1, max_length=500)


class PreventionActionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    description: str = Field(min_length=2, max_length=5000)
    due_at: datetime
    evidence_refs: list[str] = Field(default_factory=list, max_length=500)


class PreventionActionAssign(BaseModel):
    expected_revision: int = Field(ge=1)
    owner_id: str = Field(min_length=1, max_length=200)


class PreventionActionPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    status: PreventionActionStatus
    result: str = Field(default="", max_length=5000)
    evidence_refs: list[str] | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_result(self):
        if (
            self.status
            in {
                PreventionActionStatus.IMPLEMENTED,
                PreventionActionStatus.EFFECTIVENESS_REVIEW,
                PreventionActionStatus.CLOSED,
            }
            and not self.result.strip()
        ):
            raise ValueError("Hành động đã triển khai phải có kết quả")
        return self


class CausalReviewInput(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(min_length=2, max_length=5000)


class CausalApproval(BaseModel):
    expected_revision: int = Field(ge=1)
    decision: Literal["APPROVE", "REQUEST_CHANGES"]
    note: str = Field(min_length=2, max_length=5000)


class CausalEffectivenessInput(BaseModel):
    expected_revision: int = Field(ge=1)
    decision: Literal["EFFECTIVE", "INEFFECTIVE"]
    result: str = Field(min_length=2, max_length=5000)
    evidence_refs: list[str] = Field(min_length=1, max_length=500)
    reviewed_at: datetime


class CausalAiRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    instruction: str = Field(default="", max_length=5000)
