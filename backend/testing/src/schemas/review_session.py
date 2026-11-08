from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.schemas.contracts.common import (
    ReviewDecision as ReviewDecisionStatus,
    ReviewFindingStatus,
    ReviewTerminalStatus,
)

ReviewType = Literal[
    "REQUIREMENT",
    "TEST_STRATEGY",
    "TEST_PLAN",
    "TEST_CONDITION",
    "TEST_CASE",
    "IMPACT_ANALYSIS",
    "STATUS_REPORT",
    "COMPLETION_REPORT",
    "REQUIREMENT_REVIEW",
    "TEST_STRATEGY_REVIEW",
    "TEST_PLAN_REVIEW",
    "TEST_CONDITION_REVIEW",
    "TEST_CASE_REVIEW",
    "IMPACT_REVIEW",
    "COMPLETION_REVIEW",
]
class ReviewSessionCreate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    review_type: ReviewType
    artifact_type: str = Field(min_length=2, max_length=100)
    artifact_id: str = Field(min_length=1, max_length=200)
    artifact_version_id: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=2, max_length=5000)
    checklist_version: str = Field(min_length=1, max_length=100)
    moderator_id: str = Field(min_length=1, max_length=200)
    author_id: str = Field(min_length=1, max_length=200)
    reviewers: list[str] = Field(min_length=1, max_length=100)
    scribe_id: str | None = Field(default=None, max_length=200)
    planned_at: datetime | None = None
    checklist: list[dict[str, Any]] = Field(default_factory=list, max_length=200)

    @model_validator(mode="before")
    @classmethod
    def normalize_review_type(cls, value):
        if isinstance(value, dict):
            normalized = dict(value)
            normalized["review_type"] = {
                "REQUIREMENT_REVIEW": "REQUIREMENT",
                "TEST_STRATEGY_REVIEW": "TEST_STRATEGY",
                "TEST_PLAN_REVIEW": "TEST_PLAN",
                "TEST_CONDITION_REVIEW": "TEST_CONDITION",
                "TEST_CASE_REVIEW": "TEST_CASE",
                "IMPACT_REVIEW": "IMPACT_ANALYSIS",
                "COMPLETION_REVIEW": "COMPLETION_REPORT",
            }.get(normalized.get("review_type"), normalized.get("review_type"))
            return normalized
        return value

    @model_validator(mode="after")
    def validate_participants(self):
        self.reviewers = list(dict.fromkeys(self.reviewers))
        if self.moderator_id in self.reviewers or self.author_id in self.reviewers:
            raise ValueError("Người rà soát phải độc lập với người điều phối và tác giả")
        return self


class ReviewerAssignment(BaseModel):
    expected_revision: int = Field(ge=1)
    moderator_id: str = Field(min_length=1, max_length=200)
    reviewer_ids: list[str] = Field(min_length=1, max_length=100)
    scribe_id: str | None = Field(default=None, max_length=200)


class ReviewSessionPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    objective: str | None = Field(default=None, min_length=2, max_length=5000)
    checklist_version: str | None = Field(default=None, min_length=1, max_length=100)
    moderator_id: str | None = Field(default=None, min_length=1, max_length=200)
    reviewers: list[str] | None = Field(default=None, min_length=1, max_length=100)
    scribe_id: str | None = Field(default=None, max_length=200)
    planned_at: datetime | None = None
    checklist: list[dict[str, Any]] | None = Field(default=None, max_length=200)


class ReviewFindingCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    severity: str = Field(min_length=1, max_length=80)
    blocks_acceptance: bool = False
    anchor: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(min_length=2, max_length=5000)
    suggested_action: str = Field(default="", max_length=5000)
    owner_id: str | None = Field(default=None, max_length=200)
    due_at: datetime | None = None

    @model_validator(mode="after")
    def normalize_taxonomy_labels(self):
        self.category = " ".join(self.category.split())
        self.severity = " ".join(self.severity.split())
        if not self.category or not self.severity:
            raise ValueError("REVIEW_FINDING_LABEL_REQUIRED")
        return self


class ReviewFindingPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    status: ReviewFindingStatus
    resolution: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def validate_resolution(self):
        if (
            self.status in {ReviewFindingStatus.RESOLVED, ReviewFindingStatus.VERIFIED}
            and not self.resolution.strip()
        ):
            raise ValueError("Finding đã xử lý phải có kết quả")
        return self


class ReviewFindingAssignment(BaseModel):
    expected_revision: int = Field(ge=1)
    owner_id: str = Field(min_length=1, max_length=200)


class ReviewFindingResolution(BaseModel):
    expected_revision: int = Field(ge=1)
    resolution: str = Field(min_length=2, max_length=5000)


class ReviewFindingVerification(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(min_length=2, max_length=5000)


class ReviewDecision(BaseModel):
    expected_revision: int = Field(ge=1)
    decision: ReviewDecisionStatus
    note: str = Field(default="", max_length=5000)


class ReviewFollowUpCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)
    objective: str = Field(min_length=2, max_length=5000)
    moderator_id: str = Field(min_length=1, max_length=200)
    reviewer_ids: list[str] = Field(min_length=1, max_length=100)
    scribe_id: str | None = Field(default=None, max_length=200)
    planned_at: datetime | None = None


class ReviewTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=5000)
    decision: ReviewDecisionStatus | None = None


class ReviewTerminalTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    target_status: ReviewTerminalStatus
    note: str = Field(min_length=2, max_length=5000)
