import re
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceQuoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=2, max_length=1000)


class SecuritySuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=2, max_length=300)
    preconditions: List[str] = Field(min_length=1, max_length=30)
    action: str = Field(min_length=2, max_length=5000)
    expected: str = Field(min_length=2, max_length=5000)
    requirement_version_ids: List[str] = Field(default_factory=list, max_length=100)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=20)


class SecuritySuggestionsOutput(BaseModel):
    """Structured security test candidates."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["security_test_generation"]
    suggestions: List[SecuritySuggestionOutput] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class PerformanceSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workload_type: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=2, max_length=300)
    virtual_users: int | None = Field(default=None, ge=1, le=1000000)
    requests_per_second: float | None = Field(default=None, gt=0)
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)
    ramp_pattern: str = Field(min_length=2, max_length=2000)
    actions: List[str] = Field(min_length=1, max_length=50)
    expected: str = Field(min_length=2, max_length=5000)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=20)


class PerformanceSuggestionsOutput(BaseModel):
    """Structured performance workload candidates."""

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
    """Structured automation script draft."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["automation_script_generation"]
    suggestions: List[AutomationScriptSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class CausalHypothesisSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_cause_category: str = Field(min_length=1, max_length=200)
    hypothesis: str = Field(min_length=2, max_length=5000)
    contributing_factors: List[str] = Field(default_factory=list, max_length=50)
    five_whys: List[str] = Field(default_factory=list, max_length=5)
    missing_test_conditions: List[str] = Field(default_factory=list, max_length=50)
    missing_test_cases: List[str] = Field(default_factory=list, max_length=50)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)


class CausalHypothesesOutput(BaseModel):
    """Structured causal analysis hypotheses."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["causal_analysis"]
    suggestions: List[CausalHypothesisSuggestionOutput] = Field(min_length=1, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class StatusReportNarrativeSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(min_length=2, max_length=10000)
    risk_explanation: str = Field(min_length=2, max_length=10000)
    forecast: str = Field(min_length=2, max_length=10000)
    recommendation_narrative: str = Field(min_length=2, max_length=10000)


class StatusReportNarrativeOutput(BaseModel):
    """Structured status report narrative draft."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["status_report_narrative"]
    suggestions: List[StatusReportNarrativeSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def reject_machine_status_values(self):
        machine_values = (
            "ON_TRACK",
            "AT_RISK",
            "BLOCKED",
            "CONTINUE_TESTING",
            "READY_WITH_RISK",
            "NOT_READY",
            "NOT_MET",
        )
        for suggestion in self.suggestions:
            for field in (
                suggestion.executive_summary,
                suggestion.risk_explanation,
                suggestion.forecast,
                suggestion.recommendation_narrative,
            ):
                if any(
                    re.search(
                        rf"\b{value}\b",
                        field,
                        flags=0 if value == "BLOCKED" else re.IGNORECASE,
                    )
                    for value in machine_values
                ):
                    raise ValueError("status_report_machine_status_value_exposed")
        return self


class CompletionReportNarrativeSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(min_length=2, max_length=10000)
    closure_summary: str = Field(min_length=2, max_length=10000)
    residual_risk_summary: str = Field(min_length=2, max_length=10000)
    recommendation_rationale: str = Field(min_length=2, max_length=10000)


class CompletionReportNarrativeOutput(BaseModel):
    """Structured completion report narrative draft."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["completion_report_narrative"]
    suggestions: List[CompletionReportNarrativeSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class TestPlanFieldEvidenceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal[
        "objective", "scope_in", "scope_out", "test_approach", "test_level", "test_types",
        "environment", "entry_criteria", "exit_criteria", "risks", "assumptions",
        "constraints", "data_sources", "data_preparation", "data_privacy", "data_reset",
        "role_guidance", "milestones", "deliverables", "tools", "defect_reporting",
        "defect_classification", "defect_triage", "defect_retest", "defect_closure",
    ]
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=20)


class TestPlanDraftSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(default="", max_length=5000)
    scope_in: List[str] = Field(default_factory=list, max_length=100)
    scope_out: List[str] = Field(default_factory=list, max_length=100)
    test_approach: str = Field(default="", max_length=5000)
    test_level: str = Field(default="", max_length=100)
    test_types: List[str] = Field(default_factory=list, max_length=50)
    environment: str = Field(default="", max_length=200)
    entry_criteria: List[str] = Field(default_factory=list, max_length=100)
    exit_criteria: List[str] = Field(default_factory=list, max_length=100)
    risks: List[str] = Field(default_factory=list, max_length=100)
    assumptions: List[str] = Field(default_factory=list, max_length=100)
    constraints: List[str] = Field(default_factory=list, max_length=100)
    data_sources: List[str] = Field(default_factory=list, max_length=100)
    data_preparation: str = Field(default="", max_length=5000)
    data_privacy: str = Field(default="", max_length=5000)
    data_reset: str = Field(default="", max_length=5000)
    role_guidance: List[str] = Field(default_factory=list, max_length=100)
    milestones: List[str] = Field(default_factory=list, max_length=100)
    deliverables: List[str] = Field(default_factory=list, max_length=100)
    tools: List[str] = Field(default_factory=list, max_length=100)
    defect_reporting: str = Field(default="", max_length=5000)
    defect_classification: str = Field(default="", max_length=5000)
    defect_triage: str = Field(default="", max_length=5000)
    defect_retest: str = Field(default="", max_length=5000)
    defect_closure: str = Field(default="", max_length=5000)
    field_evidence: List[TestPlanFieldEvidenceOutput] = Field(default_factory=list, max_length=100)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(default_factory=list, max_length=100)


class TestPlanDraftOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["test_plan_draft_generation"]
    suggestions: List[TestPlanDraftSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(default_factory=list, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=30)


class TestDataSuggestionItemOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable_name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=2, max_length=1000)
    value_type: Literal["text", "integer", "decimal", "boolean", "date", "enum"]
    category: Literal["positive", "negative", "boundary"]
    values: List[str] = Field(min_length=1, max_length=30)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=10)


class TestDataSuggestionsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["test_data_generation"]
    suggestions: List[TestDataSuggestionItemOutput] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=30)


class LessonsLearnedClusterSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: str = Field(min_length=2, max_length=500)
    category: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=2, max_length=5000)
    source_indices: List[int] = Field(min_length=1, max_length=500)
    improvement_candidates: List[str] = Field(default_factory=list, max_length=100)


class LessonsLearnedClustersOutput(BaseModel):
    """Structured lessons-learned clusters."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["lessons_learned_clustering"]
    suggestions: List[LessonsLearnedClusterSuggestionOutput] = Field(min_length=1, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class ProjectComplexityDimensionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1, max_length=100)
    level: Literal["LOW", "MEDIUM", "HIGH", "INSUFFICIENT_EVIDENCE"]
    explanation: str = Field(min_length=2, max_length=4000)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(default_factory=list, max_length=30)
    uncertainty: List[str] = Field(default_factory=list, max_length=30)
    testing_impacts: List[str] = Field(default_factory=list, max_length=30)
    confidence: float = Field(ge=0, le=1)


class ProjectComplexityAssessmentSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensions: List[ProjectComplexityDimensionOutput] = Field(min_length=1, max_length=100)
    readiness_summary: str = Field(min_length=2, max_length=5000)
    unresolved_questions: List[str] = Field(default_factory=list, max_length=100)
    source_gaps: List[str] = Field(default_factory=list, max_length=100)
    recommended_follow_ups: List[
        Literal[
            "REQUIREMENT_CLARIFICATION",
            "TEST_OBLIGATION_ANALYSIS",
            "TEST_PLAN_DRAFT",
            "SCENARIO_OR_TEST_CASE_DRAFT",
            "CHANGE_IMPACT_REVIEW",
            "STAFFING_REVIEW",
        ]
    ] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_dimension_coverage(self):
        received = [item.dimension_id for item in self.dimensions]
        if len(set(received)) != len(received):
            raise ValueError("project_complexity_dimension_ids_must_be_unique")
        return self


class ProjectComplexityAssessmentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["project_complexity_assessment"]
    suggestions: List[ProjectComplexityAssessmentSuggestionOutput] = Field(
        min_length=1, max_length=1
    )
    evidence_refs: List[str] = Field(min_length=1, max_length=500)
    warnings: List[str] = Field(default_factory=list, max_length=50)


class ExecutionAssistanceObservationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["OBSERVED", "POSSIBLE_INTERPRETATION", "LIMITATION"]
    step_id: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=2, max_length=4000)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=10)


class ExecutionAssistanceDefectDraftOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=300)
    description: str = Field(min_length=2, max_length=5000)
    steps_to_reproduce: List[str] = Field(min_length=1, max_length=50)
    expected_result: str = Field(min_length=2, max_length=3000)
    actual_result: str = Field(min_length=2, max_length=3000)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=15)


class ExecutionAssistanceSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: List[ExecutionAssistanceObservationOutput] = Field(min_length=1, max_length=50)
    missing_information: List[str] = Field(default_factory=list, max_length=50)
    defect_draft: ExecutionAssistanceDefectDraftOutput | None = None


class ExecutionAssistanceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["execution_assistance"]
    suggestions: List[ExecutionAssistanceSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=100)
    warnings: List[str] = Field(default_factory=list, max_length=30)


class WorkReportSectionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=12000)
    evidence_refs: List[str] = Field(default_factory=list, max_length=100)


class WorkReportSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: List[WorkReportSectionOutput] = Field(default_factory=list, max_length=40)
    missing_information: List[str] = Field(default_factory=list, max_length=100)
    inconsistencies: List[str] = Field(default_factory=list, max_length=100)


class WorkReportNarrativeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["work_report_narrative"]
    suggestions: List[WorkReportSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=100)
