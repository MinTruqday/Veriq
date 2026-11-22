from typing import Any, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator



class GeneratedStepOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=2, max_length=5000)
    expected: str = Field(min_length=2, max_length=5000)
    test_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data values associated with this step.",
    )

    @field_validator("test_data", mode="before")
    @classmethod
    def empty_test_data(cls, value):
        return {} if value is None else value

class GeneratedEvidenceQuoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=2, max_length=1000)


class GeneratedCaseOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=300)
    category: str = Field(min_length=1, max_length=100)
    risk: str = Field(default="unassessed", min_length=1, max_length=100)
    priority: str = Field(default="unassessed", min_length=1, max_length=100)
    objective: str = Field(min_length=2, max_length=5000)
    preconditions: str = Field(default="", max_length=5000)
    alternate_flows: str = Field(default="", max_length=5000)
    exception_flows: str = Field(default="", max_length=5000)
    steps: List[GeneratedStepOutput] = Field(min_length=1, max_length=50)
    expected: str = Field(min_length=2, max_length=5000)
    acceptance_criterion_ids: List[str] = Field(default_factory=list, max_length=100)
    techniques: List[Literal[
        "equivalence_partitioning", "boundary_value", "decision_table",
        "state_transition", "error_guessing",
    ]] = Field(default_factory=list, max_length=5)
    evidence_refs: List[str] = Field(default_factory=list, max_length=100)
    evidence_quotes: List[GeneratedEvidenceQuoteOutput] = Field(min_length=1, max_length=20)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("test_case_category_must_not_be_empty")
        return normalized

class GeneratedCasesOutput(BaseModel):
    """Structured response containing generated Test Case candidates."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["scenario_generation", "test_generation"]
    suggestions: List[GeneratedCaseOutput] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)
class GeneratedCaseGroundingReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    unsupported_claims: List[str] = Field(default_factory=list)

class GeneratedCasesGroundingReview(BaseModel):
    """Grounding review result for one generated Test Case."""
    model_config = ConfigDict(extra="forbid")

    cases: List[GeneratedCaseGroundingReview] = Field(min_length=1, max_length=100)

class TechniqueRecommendationItemOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technique: Literal[
        "equivalence_partitioning", "boundary_value", "decision_table",
        "state_transition", "error_guessing",
    ]
    suitability: Literal["recommended", "possible", "insufficient_evidence", "not_applicable"]
    rationale: str = Field(min_length=2, max_length=2000)
    expected_coverage: List[str] = Field(default_factory=list, max_length=20)
    incremental_coverage: List[str] = Field(default_factory=list, max_length=20)
    existing_coverage_refs: List[str] = Field(default_factory=list, max_length=100)
    missing_information: List[str] = Field(default_factory=list, max_length=20)
    evidence_refs: List[str] = Field(default_factory=list, max_length=100)
class TechniqueRecommendationsOutput(BaseModel):
    """Structured recommendations for evidence-supported test-design techniques."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["technique_recommendation"]
    suggestions: List[TechniqueRecommendationItemOutput] = Field(min_length=1, max_length=5)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)

class TestConditionSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=300)
    description: str = Field(min_length=2, max_length=5000)
    category: str = Field(min_length=1, max_length=100)
    coverage_item: str = Field(min_length=1, max_length=500)
    test_level: str = Field(min_length=1, max_length=100)
    test_type: str = Field(min_length=1, max_length=100)
    risk: str = Field(min_length=1, max_length=100)
    priority: str = Field(min_length=1, max_length=100)
    technique_candidates: List[str] = Field(default_factory=list, max_length=100)
    testability_status: Literal["TESTABLE", "CONDITIONALLY_TESTABLE", "UNTESTABLE"]
    evidence_quotes: List[GeneratedEvidenceQuoteOutput] = Field(min_length=1, max_length=20)

class TestConditionSuggestionsOutput(BaseModel):
    """Structured evidence-grounded test-condition candidates."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["test_condition_generation"]
    condition_candidates: List[TestConditionSuggestionOutput] = Field(
        default_factory=list,
        max_length=100,
        description="Test-condition candidates grouped by evidence-supported category.",
    )
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)
