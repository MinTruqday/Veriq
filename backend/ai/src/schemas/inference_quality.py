import re
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceQuoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=2, max_length=1000)


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
        "constraints",
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
