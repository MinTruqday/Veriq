from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceQuoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=2, max_length=1000)


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

    workload_type: Literal["baseline", "load", "stress", "spike", "soak"]
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
    progress_summary: str = Field(min_length=2, max_length=10000)
    coverage_summary: str = Field(min_length=2, max_length=10000)
    defect_summary: str = Field(min_length=2, max_length=10000)
    forecast: str = Field(min_length=2, max_length=10000)
    recommendation: Literal[
        "ON_TRACK", "AT_RISK", "BLOCKED", "CONTINUE_TESTING", "READY_WITH_RISK", "NOT_READY"
    ]

class StatusReportNarrativeOutput(BaseModel):
    """Structured status report narrative draft."""
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
    """Structured completion report narrative draft."""
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
    """Structured lessons-learned clusters."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["lessons_learned_clustering"]
    suggestions: List[LessonsLearnedClusterSuggestionOutput] = Field(min_length=1, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)

