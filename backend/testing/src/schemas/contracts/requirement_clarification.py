from typing import Literal

from pydantic import BaseModel, Field


class RequirementClarificationCreate(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    reason: str = Field(min_length=2, max_length=4000)
    coverage_item_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_ref: str | None = Field(default=None, min_length=1, max_length=500)
    source_quote: str | None = Field(default=None, min_length=1, max_length=10000)
    unlocks_obligation_keys: list[str] = Field(default_factory=list, max_length=100)
    unlocks_source_quotes: list[str] = Field(default_factory=list, max_length=100)
    unlocks_coverage_item_ids: list[str] = Field(default_factory=list, max_length=100)


class RequirementClarificationAnswer(BaseModel):
    expected_revision: int = Field(ge=1)
    answer: str = Field(min_length=2, max_length=10000)


class RequirementClarificationResolution(BaseModel):
    expected_revision: int = Field(ge=1)
    requirement_version_id: str = Field(min_length=1, max_length=200)
    evidence_quote: str = Field(min_length=2, max_length=10000)


class RequirementClarificationDecision(BaseModel):
    expected_revision: int = Field(ge=1)
    status: Literal["NOT_APPLICABLE", "WAIVED"]
    reason: str = Field(min_length=2, max_length=4000)
