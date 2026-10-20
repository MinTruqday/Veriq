from enum import Enum
from typing import Annotated, Any, List, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TestingAutomationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"


class TestingAutomationDegradedMode(str, Enum):
    OUTPUT = "DEGRADED_OUTPUT"
    PROVIDER = "DEGRADED_AI"


class CrossDocumentExpansionRequest(BaseModel):
    question: str = Field(
        min_length=1, max_length=10000, description="Question to decompose across documents"
    )
    document_ids: List[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        min_length=2, max_length=100, description="Ordered document identifiers to retrieve"
    )


class KnowledgeChunkSafetyRequest(BaseModel):
    texts: List[Annotated[str, Field(min_length=1, max_length=4000)]] = Field(
        min_length=1, max_length=500, description="Retrieved chunks to assess for safety"
    )


class KnowledgeDocumentSummaryRequest(BaseModel):
    text: str = Field(
        min_length=1, max_length=15000, description="Document content to summarize for knowledge retrieval"
    )


class TestingEvidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    artifact_type: str = Field(min_length=1, max_length=100)
    artifact_id: str | None = Field(default=None, min_length=1, max_length=200)
    artifact_version_id: str | None = Field(default=None, min_length=1, max_length=200)
    authority: str | None = Field(default=None, min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def require_identifier(self):
        if not self.artifact_id and not self.artifact_version_id:
            raise ValueError("testing_evidence_identifier_required")
        return self


class TestingAutomationRequest(BaseModel):
    capability: str = Field(min_length=1, max_length=100, description="Testing capability to perform")
    project_id: str = Field(
        min_length=1, max_length=128, description="Project identifier that bounds the operation"
    )
    instruction: str = Field(
        default="", max_length=5000, description="Additional user business instruction"
    )
    evidence: List[TestingEvidence] = Field(
        min_length=1,
        max_length=100,
        description="Artifact evidence already bounded to the project",
    )

    @model_validator(mode="after")
    def require_registered_capability(self):
        output_schema(self.capability)
        return self


class TestingAutomationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: str = Field(description="Executed testing capability")
    suggestions: List[dict[str, Any]] = Field(
        default_factory=list,
        max_length=100,
        description="Proposals that remain pending review",
    )
    new_test_candidates: List[dict[str, Any]] = Field(
        default_factory=list,
        max_length=100,
        description="New test case proposals that remain pending review",
    )
    findings: List[dict[str, Any]] = Field(
        default_factory=list,
        max_length=100,
        description="Analysis findings pending acknowledgement",
    )
    readiness: str | None = None
    conflicts: List[dict[str, Any]] = Field(default_factory=list, max_length=100)
    context: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(
        default_factory=list, max_length=200, description="Evidence identifiers supporting the result"
    )
    confidence: float = Field(ge=0, le=1, description="Model confidence for reference")
    warnings: List[str] = Field(
        default_factory=list, max_length=50, description="Evidence limitation and conflict warnings"
    )
    status: TestingAutomationStatus = Field(
        default=TestingAutomationStatus.SUCCESS, description="AI capability operating status"
    )
    degraded_mode: TestingAutomationDegradedMode | None = Field(
        default=None, description="Fallback mode when the provider or retrieval is unavailable"
    )
    provider: str = Field(min_length=1, max_length=100, description="Provider that produced the result")
    model: dict[str, Any] = Field(
        default_factory=dict, description="Model prompt and tool schema version metadata"
    )
    prompt_version: str = Field(min_length=1, max_length=100, description="Prompt version")
    tool_schema_version: str = Field(
        min_length=1, max_length=100, description="Output schema version"
    )
    retrieval_version: str = Field(
        min_length=1, max_length=100, description="Evidence retrieval version"
    )
    created_at: str = Field(min_length=1, max_length=100, description="Result creation time")
    reason_codes: List[str] = Field(
        default_factory=list,
        max_length=100,
        description="Auditable reason codes without hidden reasoning",
    )
    workflow: dict[str, Any] = Field(
        default_factory=dict, description="Auditable observe reason act observe workflow state"
    )
    answer: str = Field(
        default="", max_length=20000, description="Evidence grounded answer for project questions"
    )


class ProjectQuestionOutput(BaseModel):
    """Answer in at most five sentences and cite only evidence references actually used"""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["project_question"]
    answer: str = Field(min_length=1, max_length=4000)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class RequirementQualityFindingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "AMBIGUITY",
        "OMISSION",
        "INCONSISTENCY",
        "CONTRADICTION",
        "UNTESTABLE",
        "MISSING_ACCEPTANCE_CRITERIA",
        "MISSING_ERROR_BEHAVIOR",
        "MISSING_PERMISSION_RULE",
        "MISSING_BOUNDARY",
        "MISSING_STATE_RULE",
        "MISSING_DATA_RULE",
        "MISSING_NON_FUNCTIONAL_CRITERIA",
        "OTHER",
    ]
    severity: Literal["error", "warning", "info"]
    message: str = Field(min_length=2, max_length=5000)
    suggestion: str = Field(min_length=2, max_length=5000)
    evidence_refs: List[str] = Field(min_length=1, max_length=100)
    reason_codes: List[str] = Field(min_length=1, max_length=100)


class RequirementAcceptanceCriterionSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=2, max_length=5000)


class RequirementRevisionSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revised_title: str | None = Field(default=None, min_length=2, max_length=300)
    revised_content: str | None = Field(default=None, min_length=2, max_length=20000)
    revised_actors: List[str] | None = Field(default=None, min_length=1, max_length=100)
    revised_business_rules: List[str] | None = Field(default=None, min_length=1, max_length=200)
    revised_acceptance_criteria: List[RequirementAcceptanceCriterionSuggestionOutput] | None = (
        Field(default=None, min_length=1, max_length=200)
    )
    revised_dependencies: List[str] | None = Field(default=None, max_length=200)
    target_fields: List[
        Literal[
            "title", "content", "actors", "business_rules", "acceptance_criteria", "dependencies"
        ]
    ] = Field(default_factory=list, max_length=6)
    rationale: str = Field(default="", max_length=5000)
    evidence_refs: List[str] = Field(default_factory=list, max_length=100)
    reason_codes: List[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def require_revision_value(self):
        values = {
            "title": self.revised_title,
            "content": self.revised_content,
            "actors": self.revised_actors,
            "business_rules": self.revised_business_rules,
            "acceptance_criteria": self.revised_acceptance_criteria,
            "dependencies": self.revised_dependencies,
        }
        revised_fields = {field for field, value in values.items() if value is not None}
        if not revised_fields:
            raise ValueError("requirement_revision_value_required")
        self.target_fields = [
            field
            for field in (
                "title",
                "content",
                "actors",
                "business_rules",
                "acceptance_criteria",
                "dependencies",
            )
            if field in revised_fields
        ]
        for values in (self.revised_actors, self.revised_business_rules):
            if values is not None and any(not value.strip() for value in values):
                raise ValueError("requirement_revision_blank_list_value")
        return self


class RequirementQualityModelOutput(BaseModel):
    """Evaluate content actors business rules acceptance criteria and dependencies separately. Treat absent behavior actors or business rules as blocking. Return every field finding with an evidence grounded revision, make target_fields match non-null revised values, merge related revisions, and never apply changes automatically."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["requirement_quality_analysis"] = "requirement_quality_analysis"
    suggestions: List[RequirementRevisionSuggestionOutput] = Field(
        default_factory=list,
        max_length=1,
        description="Return an empty list when no concrete revision is justified. Each suggestion must include at least one non-null revised field, and target_fields must contain only the names of those non-null revised fields.",
    )


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


class ImpactClassificationSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_case_version_id: str = Field(min_length=1, max_length=128)
    classification: Literal["STILL_VALID", "POTENTIALLY_AFFECTED", "NEEDS_UPDATE", "OBSOLETE"] = Field(
        description="Use NEEDS_UPDATE only when maintenance_patch contains at least one concrete evidence grounded revision"
    )
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=2, max_length=5000)
    maintenance_patch: "MaintenanceTestCasePatchOutput | None" = None

    @model_validator(mode="after")
    def require_patch_for_update(self):
        if self.classification == "NEEDS_UPDATE" and self.maintenance_patch is None:
            raise ValueError("maintenance_patch_required")
        return self


class MaintenanceTestStepOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=2, max_length=5000)
    expected: str = Field(min_length=2, max_length=5000)
    test_data: dict = Field(default_factory=dict)


class MaintenanceTestCasePatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=2, max_length=300)
    type: Literal[
        "happy_path",
        "negative",
        "boundary",
        "validation",
        "permission",
        "state_transition",
        "integration",
        "error_handling",
        "data_persistence",
        "concurrency",
        "api",
        "ui",
        "custom",
    ] | None = None
    objective: str | None = Field(default=None, min_length=2, max_length=5000)
    preconditions: str | None = Field(default=None, min_length=2, max_length=5000)
    steps: List[MaintenanceTestStepOutput] | None = Field(default=None, min_length=1, max_length=100)
    expected: str | None = Field(default=None, min_length=2, max_length=5000)
    test_data: dict | None = None

    @model_validator(mode="after")
    def require_patch_value(self):
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("maintenance_patch_value_required")
        return self


class NewTestCandidateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=2, max_length=5000)
    confidence: float = Field(ge=0, le=1)
    patch: MaintenanceTestCasePatchOutput

    @model_validator(mode="after")
    def require_complete_test_case(self):
        if not self.patch.title or not self.patch.steps or not self.patch.expected:
            raise ValueError("new_test_candidate_incomplete")
        return self


ImpactClassificationSuggestionOutput.model_rebuild()


class ImpactClassificationOutput(BaseModel):
    """Classify every test case version in evidence. A needs-update result contains only evidence grounded maintenance changes, missing coverage becomes a new test candidate, and no change is applied automatically."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["impact_analysis"]
    suggestions: List[ImpactClassificationSuggestionOutput] = Field(min_length=1, max_length=100)
    new_test_candidates: List[NewTestCandidateOutput] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class SecuritySuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "authorization", "authentication", "input_validation", "session", "data_protection"
    ]
    title: str = Field(min_length=2, max_length=300)
    preconditions: List[str] = Field(min_length=1, max_length=30)
    action: str = Field(min_length=2, max_length=5000)
    expected: str = Field(min_length=2, max_length=5000)
    requirement_version_ids: List[str] = Field(default_factory=list, max_length=100)


class SecuritySuggestionsOutput(BaseModel):
    """Generate concrete evidence grounded security tests in the language of the user instruction. Never claim a vulnerability scan was executed and use only requirement version identifiers present in evidence."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["security_test_generation"]
    suggestions: List[SecuritySuggestionOutput] = Field(min_length=1, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class PerformanceSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workload_type: Literal["baseline", "load", "stress", "spike", "soak"]
    title: str = Field(min_length=2, max_length=300)
    virtual_users: int = Field(ge=1, le=1000000)
    requests_per_second: float | None = Field(default=None, gt=0)
    duration_minutes: int = Field(ge=1, le=10080)
    ramp_pattern: str = Field(min_length=2, max_length=2000)
    actions: List[str] = Field(min_length=1, max_length=50)
    expected: str = Field(min_length=2, max_length=5000)


class PerformanceSuggestionsOutput(BaseModel):
    """Generate an evidence grounded performance plan in the language of the user instruction. Include requested workload types only, do not claim load execution, and do not invent targets outside the instruction."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["performance_plan_generation"]
    suggestions: List[PerformanceSuggestionOutput] = Field(min_length=1, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class AutomationScriptSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=100000)
    secret_placeholders: List[str] = Field(default_factory=list, max_length=100)


class AutomationScriptOutput(BaseModel):
    """Create exactly one complete automation script draft in the requested framework and language without markdown. Use secret placeholders only, use environment variables for unknown locators or URLs, report them in warnings, and never write to a repository."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["automation_script_generation"]
    suggestions: List[AutomationScriptSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class CausalHypothesisSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_cause_category: Literal[
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
    hypothesis: str = Field(min_length=2, max_length=5000)
    contributing_factors: List[str] = Field(default_factory=list, max_length=50)
    five_whys: List[str] = Field(default_factory=list, max_length=5)
    missing_test_conditions: List[str] = Field(default_factory=list, max_length=50)
    missing_test_cases: List[str] = Field(default_factory=list, max_length=50)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)


class CausalHypothesesOutput(BaseModel):
    """Propose root cause hypotheses, defect clusters, contributing factors, and missing test coverage. Never confirm a cause or approve CAPA. Every hypothesis cites evidence references."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["causal_analysis"]
    suggestions: List[CausalHypothesisSuggestionOutput] = Field(min_length=1, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class StatusReportNarrativeSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(min_length=2, max_length=10000)
    progress_summary: str = Field(min_length=2, max_length=10000)
    coverage_summary: str = Field(min_length=2, max_length=10000)
    defect_summary: str = Field(min_length=2, max_length=10000)
    forecast: str = Field(min_length=2, max_length=10000)
    recommendation: Literal[
        "ON_TRACK", "AT_RISK", "BLOCKED", "CONTINUE_TESTING", "READY_WITH_RISK", "NOT_READY"
    ]


class StatusReportNarrativeOutput(BaseModel):
    """Draft only from supplied metrics and evidence. Never alter metrics, approve the report, or add unsupported conclusions."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["status_report_narrative"]
    suggestions: List[StatusReportNarrativeSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class CompletionReportNarrativeSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(min_length=2, max_length=10000)
    closure_summary: str = Field(min_length=2, max_length=10000)
    residual_risk_summary: str = Field(min_length=2, max_length=10000)
    recommendation_rationale: str = Field(min_length=2, max_length=10000)


class CompletionReportNarrativeOutput(BaseModel):
    """Draft only from supplied metrics and evidence. Never change the quality gate recommendation or approve the report."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["completion_report_narrative"]
    suggestions: List[CompletionReportNarrativeSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class LessonsLearnedClusterSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: str = Field(min_length=2, max_length=500)
    category: Literal["WORKED", "FAILED", "BLOCKER", "IMPROVEMENT"]
    summary: str = Field(min_length=2, max_length=5000)
    source_indices: List[int] = Field(min_length=1, max_length=500)
    improvement_candidates: List[str] = Field(default_factory=list, max_length=100)


class LessonsLearnedClustersOutput(BaseModel):
    """Cluster lessons learned by theme, preserve source-index grounding, and propose improvement candidates without applying them."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["lessons_learned_clustering"]
    suggestions: List[LessonsLearnedClusterSuggestionOutput] = Field(min_length=1, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class RequirementTemplateAPIOperationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(min_length=1, max_length=200)
    method: str = Field(min_length=1, max_length=20)
    path: str | None = None
    url_template: str | None = None
    operation_id: str | None = None
    folder: str | None = None


class RequirementTemplateContextOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectives: str = Field(default="", max_length=10000)
    in_scope: str = Field(default="", max_length=10000)
    out_of_scope: str = Field(default="", max_length=10000)
    stakeholders: List[str] = Field(default_factory=list, max_length=200)
    actors_and_systems: List[str] = Field(default_factory=list, max_length=200)
    glossary: List[str] = Field(default_factory=list, max_length=500)
    assumptions: List[str] = Field(default_factory=list, max_length=200)
    constraints: List[str] = Field(default_factory=list, max_length=200)


class RequirementTemplateSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=300)
    type: Literal["functional", "non_functional", "business_rule", "api", "ui", "data", "permission", "integration", "constraint"]
    content: str = Field(min_length=2, max_length=10000)
    evidence_refs: List[str] = Field(min_length=1, max_length=20)
    source_quotes: dict[str, str] = Field(default_factory=dict)
    missing_sections: List[str] = Field(default_factory=list, max_length=20)
    not_applicable_sections: List[str] = Field(default_factory=list, max_length=20)
    acceptance_criteria: List[str] = Field(default_factory=list, max_length=50)
    actors: List[str] = Field(default_factory=list, max_length=50)
    business_rules: List[str] = Field(default_factory=list, max_length=50)
    dependencies: List[str] = Field(default_factory=list, max_length=50)
    user_story_actor: str | None = None
    user_story_goal: str | None = None
    user_story_value: str | None = None
    main_flow: str | None = None
    exception_flow: str | None = None
    data_rules: str | None = None
    integration: str | None = None
    quality_measure: str | None = None
    api_operations: List[RequirementTemplateAPIOperationOutput] = Field(default_factory=list, max_length=50)


class RequirementTemplateSynthesisOutput(BaseModel):
    """Synthesize a Requirements template draft only from supplied documents or templates. Context may contain only objectives in_scope out_of_scope stakeholders actors_and_systems glossary assumptions and constraints. Each proposed requirement must cite exact evidence and a verbatim quote for document evidence. Preserve source distinctions, report duplicates and conflicts, and mark absent applicable information as missing. Never create test cases or approve import."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["requirement_template_synthesis"] = "requirement_template_synthesis"
    context: RequirementTemplateContextOutput = Field(default_factory=RequirementTemplateContextOutput)
    suggestions: List[RequirementTemplateSuggestionOutput] = Field(default_factory=list, max_length=100)
    conflicts: List[dict[str, Any]] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=50)


class RequirementTemplateReviewFindingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_index: int | None = Field(default=None, ge=0)
    field: str = Field(min_length=1, max_length=100)
    issue: str = Field(min_length=2, max_length=1000)
    evidence_refs: List[str] = Field(min_length=1, max_length=20)
    suggested_source_quote: str | None = Field(default=None, min_length=2, max_length=2000)


class RequirementTemplateReviewOutput(BaseModel):
    """Review whether a Requirements template is suitable for import without changing it  Report a missing field only when the source shows that field applies to this specific requirement and its omission prevents import  A field absent from the source is not automatically required  Do not demand data rules dependencies quality measures or User Story fields merely because they exist in the schema  Distinguish missing applicable information from not applicable information  Identify contradictions and unsupported assumptions  Write issue in the requested natural language without raw schema names  Suggest an exact source quote only when it appears in an AI permitted source document  Do not invent fields requirements actors acceptance criteria response codes or quality limits  Do not generate test cases or approve import"""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["requirement_template_review"]
    readiness: Literal["ready_for_import", "needs_information", "conflict"]
    findings: List[RequirementTemplateReviewFindingOutput] = Field(default_factory=list, max_length=50)
    evidence_refs: List[str] = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


def output_schema(capability):
    for schema in BaseModel.__subclasses__():
        if schema.__module__ != __name__ or not schema.__name__.endswith("Output"):
            continue
        field = schema.model_fields.get("capability")
        if field and capability in get_args(field.annotation):
            return schema
    raise ValueError("testing_capability_schema_missing")
