from typing import Any, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class GeneratedObligationEvidenceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_key: str = Field(min_length=1, max_length=200)
    evidence_quotes: List[GeneratedEvidenceQuoteOutput] = Field(min_length=1, max_length=20)

class GeneratedCaseOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=300)
    category: Literal[
        "happy_path", "negative", "boundary", "validation", "permission",
        "state_transition", "integration", "error_handling", "data_persistence",
        "concurrency", "api", "ui", "custom",
    ]
    objective: str = Field(min_length=2, max_length=5000)
    preconditions: str = Field(default="", max_length=5000)
    steps: List[GeneratedStepOutput] = Field(min_length=1, max_length=50)
    expected: str = Field(min_length=2, max_length=5000)
    acceptance_criterion_ids: List[str] = Field(default_factory=list, max_length=100)
    techniques: List[Literal[
        "equivalence_partitioning", "boundary_value", "decision_table",
        "state_transition", "error_guessing",
    ]] = Field(default_factory=list, max_length=5)
    challenge_techniques: List[Literal[
        "equivalence_partitioning", "boundary_value", "decision_table",
        "state_transition", "error_guessing",
    ]] = Field(default_factory=list, max_length=5)
    coverage_obligations: List[str] = Field(default_factory=list, max_length=20)
    obligation_evidence: List[GeneratedObligationEvidenceOutput] = Field(
        default_factory=list, max_length=20
    )
    evidence_refs: List[str] = Field(default_factory=list, max_length=100)
    evidence_quotes: List[GeneratedEvidenceQuoteOutput] = Field(min_length=1, max_length=20)

    @field_validator("coverage_obligations")
    @classmethod
    def unique_coverage_obligations(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("test_case_coverage_obligations_must_be_unique")
        return value

    @model_validator(mode="after")
    def validate_obligation_evidence(self):
        evidence_by_obligation = {
            item.obligation_key: item for item in self.obligation_evidence
        }
        if len(evidence_by_obligation) != len(self.obligation_evidence):
            raise ValueError("test_case_obligation_evidence_keys_must_be_unique")
        if not set(evidence_by_obligation).issubset(self.coverage_obligations):
            raise ValueError("test_case_obligation_evidence_must_reference_case_obligations")
        test_case_quotes = {
            (item.evidence_ref, item.quote) for item in self.evidence_quotes
        }
        if any(
            (quote.evidence_ref, quote.quote) not in test_case_quotes
            for item in self.obligation_evidence
            for quote in item.evidence_quotes
        ):
            raise ValueError("test_case_obligation_evidence_must_reference_case_evidence")
        return self

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

class TestDesignChallengeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(min_length=1, max_length=200)
    source_quote: str = Field(min_length=2, max_length=1000)
    hypothetical_fault: str = Field(min_length=2, max_length=2000)
    distinguishing_input: str = Field(min_length=2, max_length=2000)
    expected_result: str = Field(min_length=2, max_length=2000)
    existing_case_refs: List[str] = Field(default_factory=list, max_length=100)

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
    challenge: TestDesignChallengeOutput | None = None

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
    category: Literal["POSITIVE", "NEGATIVE", "BOUNDARY"]
    coverage_item: str = Field(min_length=1, max_length=500)
    test_level: str = Field(min_length=1, max_length=100)
    test_type: str = Field(min_length=1, max_length=100)
    risk: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
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
        description="Test-condition candidates grouped by supported category.",
    )
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)
