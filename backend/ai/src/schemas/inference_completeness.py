from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from shared.completeness import COMPLETENESS_AREA, COMPLETENESS_AREAS


class CompletenessQuoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=1, max_length=500)


class CompletenessFindingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: COMPLETENESS_AREA
    kind: Literal["NEEDS_DETAIL", "NEEDS_SOURCE", "POTENTIAL_CONFLICT", "QUESTION"]
    title: str = Field(min_length=2, max_length=300)
    rationale: str = Field(min_length=2, max_length=1500)
    requested_document: str = Field(default="", max_length=500)
    requested_details: list[str] = Field(min_length=1, max_length=8)
    priority: str | None = Field(default=None, max_length=80)
    evidence_quotes: list[CompletenessQuoteOutput] = Field(min_length=1, max_length=4)


class CompletenessCoverageOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: COMPLETENESS_AREA
    status: Literal["EVIDENCE_FOUND", "NEEDS_CONFIRMATION", "NOT_APPLICABLE"]
    explanation: str = Field(min_length=2, max_length=1200)
    evidence_quotes: list[CompletenessQuoteOutput] = Field(default_factory=list, max_length=4)


class ProjectCompletenessSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=2, max_length=2500)
    findings: list[CompletenessFindingOutput] = Field(default_factory=list, max_length=30)
    coverage: list[CompletenessCoverageOutput] = Field(
        min_length=len(COMPLETENESS_AREAS), max_length=len(COMPLETENESS_AREAS)
    )

    @model_validator(mode="after")
    def validate_area_coverage(self):
        if {item.area for item in self.coverage} != set(COMPLETENESS_AREAS):
            raise ValueError("COMPLETENESS_AREA_COVERAGE_INVALID")
        for item in self.coverage:
            if item.status != "NEEDS_CONFIRMATION" and not item.evidence_quotes:
                raise ValueError("COMPLETENESS_COVERAGE_EVIDENCE_REQUIRED")
        for item in self.findings:
            if any(not value.strip() or len(value) > 1000 for value in item.requested_details):
                raise ValueError("COMPLETENESS_REQUESTED_DETAIL_INVALID")
            if item.kind == "POTENTIAL_CONFLICT" and len(item.evidence_quotes) < 2:
                raise ValueError("COMPLETENESS_CONFLICT_TWO_SOURCES_REQUIRED")
        return self


class ProjectCompletenessOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["project_completeness_review"]
    suggestions: list[ProjectCompletenessSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=30)
