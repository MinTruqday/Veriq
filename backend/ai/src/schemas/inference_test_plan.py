from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TestPlanEvidenceQuoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=2, max_length=1000)


class TestPlanRiskSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=500)
    description: str = Field(default="", max_length=2000)
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    evidence_quotes: list[TestPlanEvidenceQuoteOutput] = Field(min_length=1, max_length=10)


class TestPlanFieldEvidenceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal[
        "objective", "scope_out", "entry_criteria", "exit_criteria", "test_types", "test_level"
    ]
    value: str = Field(min_length=1, max_length=5000)
    evidence_quotes: list[TestPlanEvidenceQuoteOutput] = Field(min_length=1, max_length=10)


class TestPlanSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=2, max_length=5000)
    scope_out: list[str] = Field(default_factory=list, max_length=100)
    entry_criteria: list[str] = Field(default_factory=list, max_length=100)
    exit_criteria: list[str] = Field(default_factory=list, max_length=100)
    test_types: list[
        Literal["functional", "non_functional", "black_box", "white_box"]
    ] = Field(default_factory=list, max_length=4)
    test_level: Literal[
        "component", "component_integration", "system", "system_integration", "acceptance"
    ] | None = None
    risks: list[TestPlanRiskSuggestionOutput] = Field(default_factory=list, max_length=50)
    evidence_refs: list[str] = Field(min_length=1, max_length=100)
    field_evidence: list[TestPlanFieldEvidenceOutput] = Field(min_length=1, max_length=100)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=30)


class TestPlanGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["test_plan_generation"] = "test_plan_generation"
    suggestion: TestPlanSuggestionOutput
    evidence_refs: list[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list, max_length=50)
