from typing import Annotated, Any, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GeneratedStepOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=2, max_length=5000)
    expected: str = Field(min_length=2, max_length=5000)
    test_data: dict[str, Any] = Field(default_factory=dict, description="Use an empty object when this step has no separate test data")

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
    evidence_refs: List[str] = Field(default_factory=list, max_length=100)
    evidence_quotes: List[GeneratedEvidenceQuoteOutput] = Field(min_length=1, max_length=20)

class GeneratedCasesOutput(BaseModel):
    """When categories are supplied generate exactly the requested count for each category  When selected_design_techniques are supplied without categories generate only evidence supported cases up to maximum_cases and identify one or more selected techniques for each case  Each case needs specific coverage_obligations cited evidence_refs and one or more evidence_quotes  Every evidence_quotes quote must be a contiguous exact substring of the text identified by its evidence_ref and must directly support the proposed behavior  Use every selected technique only when evidence supports it and otherwise report the missing prerequisite in warnings  A case may use more than one selected technique when the same concrete input and expected outcome genuinely demonstrate each technique  Do not require a separate case for each technique but never attach a technique label just to satisfy the selection  When maximum_cases is too small to demonstrate every supported technique prioritize distinct coverage and report any remaining limitation  Return an empty suggestions list with a specific warning when no case is supported  Challenge hypotheses in the user instruction are unverified proposals and never evidence  When a cited source supports a distinguishing input and expected outcome use them to design a case that could expose the hypothetical fault  Record the targeted challenge technique in challenge_techniques only when this case actually uses the distinguishing input and verifies the source supported outcome  Never repeat or paraphrase hypothetical_fault as product behavior in title objective preconditions steps expected result or coverage obligations  The generated case must differ in concrete input or verified outcome from every cited existing case because an unchanged case cannot test the challenge  Otherwise omit the hypothesis and report why in warnings  Every candidate needs concrete input and a verifiable result and may use only acceptance criterion identifiers present in evidence  Derive equivalence classes boundaries decision rules states and error hypotheses only from evidence  A successful flow does not imply any specific failure behavior  If a selected technique needs an undocumented failure condition omit that technique and report the missing information in warnings  Write interface neutral actions and preconditions when the source does not specify an interface  Do not invent undocumented values or generic templates"""
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
    """Review every generated test case against the provided requirement and acceptance criteria  Flag any claimed behavior expected outcome message data store limit precondition or failure response that the evidence does not establish  Copy each unsupported phrase exactly from the proposed case in its original language  Do not paraphrase or explain it  Concrete example test data may be proposed but must not be presented as a documented rule  Return one review for every case in input order  An empty unsupported_claims list means the case is grounded"""
    model_config = ConfigDict(extra="forbid")

    cases: List[GeneratedCaseGroundingReview] = Field(min_length=1, max_length=100)

class TestDesignChallengeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(min_length=1, max_length=200)
    source_quote: str = Field(min_length=2, max_length=1000, description="Copy one contiguous substring from the cited requirement or acceptance criterion exactly including capitalization conjunctions and punctuation Do not paraphrase or combine fragments")
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
    """Assess which test design techniques fit each requirement from cited evidence and existing tests  Distinguish behavior explicitly stated in evidence from hypothetical possibilities  Only evidence typed existing_test_case represents active coverage  Evidence typed test_case_draft is unapproved and must not count as current coverage or as an existing case in a challenge  Mark a technique recommended only when the source defines enough input classes rules boundaries or states to apply it concretely  When prerequisites are absent mark possible or insufficient_evidence and name the missing information  Expected and incremental coverage must describe only behavior supported by cited evidence  Do not assume empty inputs unchanged data extra states reverse transitions numeric limits or defect history  For each supported technique propose at most one challenge only when a concrete hypothetical faulty implementation could pass at least one cited existing case while violating an exact quote from a requirement or acceptance criterion  source_quote must be copied as one contiguous substring of the text attached to source_ref with every character unchanged  Prefer the entire cited source text when it fits the source_quote field limit  Never shorten a quote by deleting words from its middle and never join separate source fragments  Cite only existing case identifiers actually present in evidence  Never propose a challenge when no existing case is available  A challenge is a hypothesis for human review and not a proven defect or a completed test  Omit the challenge when the source cannot establish a distinguishing input and correct result  Never generate or save test cases"""
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

class TestConditionSuggestionsOutput(BaseModel):
    """Generate only condition candidates. Include evidence grounded positive, negative, and boundary coverage with concrete title, description, coverage item, level, type, risk, priority, techniques, and testability. Never invent limits or behavior."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["test_condition_generation"]
    condition_candidates: List[TestConditionSuggestionOutput] = Field(
        min_length=1,
        max_length=100,
        description="Include at least one POSITIVE, one NEGATIVE, and one BOUNDARY candidate.",
    )
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def require_coverage_categories(self):
        categories = {candidate.category for candidate in self.condition_candidates}
        required = {"POSITIVE", "NEGATIVE", "BOUNDARY"}
        if not required.issubset(categories):
            raise ValueError("test_condition_category_coverage_required")
        return self

