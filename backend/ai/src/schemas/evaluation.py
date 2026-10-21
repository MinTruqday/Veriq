from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TaskEvaluation(BaseModel):
    status: Literal["PASS", "FAIL"] = Field(
        description="PASS when the result is accurate complete grounded and safe otherwise FAIL"
    )
    feedback: str = Field(
        description="Specific evidence grounded evaluation feedback"
    )
    revised_task: str = Field(
        default="",
        description="Revised task when status is FAIL and empty when status is PASS",
    )


class DocumentGrade(BaseModel):
    is_relevant: bool = Field(
        description="True when the document directly contains information that addresses the query"
    )


class QualityEvaluation(BaseModel):
    relevance: float = Field(
        ge=0.0,
        le=1.0,
        description="Degree to which the result directly answers the query from zero to one",
    )
    grounding: float = Field(
        ge=0.0,
        le=1.0,
        description="Degree of support from the supplied context from zero to one",
    )
    completeness: float = Field(
        ge=0.0,
        le=1.0,
        description="Coverage of material query elements from zero to one",
    )
    overall: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall quality score from zero to one",
    )
    should_retry: bool = Field(
        description="True when the result is unsafe ungrounded incomplete or below the quality threshold"
    )
    feedback: str = Field(
        description="Specific feedback about deficiencies and how to correct them"
    )


class ErrorMessageJudgment(BaseModel):
    is_error_message: bool = Field(
        description="True when the text is a raw system or technical error"
    )
    reason: str = Field(
        description="Concise reason for the classification"
    )


class HallucinationJudgment(BaseModel):
    is_hallucination_or_refusal: bool = Field(
        description="True when the result refuses or contains unverified information"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Judgment confidence from zero to one",
    )
    explanation: str = Field(
        description="Specific explanation of the unsupported claim or detected refusal"
    )


class RelevanceJudgment(BaseModel):
    is_relevant: bool = Field(
        description="True when the result directly addresses the primary query intent"
    )
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance score from zero to one",
    )
    feedback: str = Field(
        description="Feedback about missing unsupported or relevant content"
    )


class HallucinationGrade(BaseModel):
    is_refusal_or_hallucination: bool = Field(
        description="True when the result refuses or contains unverified information"
    )
    reason: str = Field(
        description="Concise reason for the judgment"
    )


class JudgeScores(BaseModel):
    accuracy: int = Field(
        ge=0,
        le=10,
        description="Accuracy score from zero to ten",
    )
    completeness: int = Field(
        ge=0, le=10, description="Completeness score from zero to ten"
    )
    relevance: int = Field(
        ge=0,
        le=10,
        description="Relevance score from zero to ten",
    )
    explanation: str = Field(
        min_length=1,
        max_length=2000,
        description="Concise evidence for the assigned scores",
    )


class TestabilityBenchmarkCandidate(BaseModel):
    """One system's observable output for a benchmark case."""

    source_quotes: list[str] = Field(default_factory=list, max_length=500)
    clarification_codes: list[str] = Field(default_factory=list, max_length=500)
    clarification_categories: list[str] = Field(default_factory=list, max_length=500)
    obligation_keys: list[str] = Field(default_factory=list, max_length=1000)
    obligation_evidence: dict[str, list[str]] = Field(default_factory=dict)


class TestabilityBenchmarkSource(BaseModel):
    """One independently versioned source document in a benchmark scenario."""

    source_id: str = Field(min_length=1, max_length=200)
    artifact_type: str = Field(default="benchmark_source", min_length=1, max_length=100)
    artifact_version_id: str = Field(min_length=1, max_length=200)
    authority: str = Field(default="benchmark_answer_key_dataset", min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=100_000)


class TestabilityBenchmarkGoldCase(BaseModel):
    """A benchmark scenario contains only its source and human-authored answer key."""

    case_id: str = Field(min_length=1, max_length=200)
    source_text: str = Field(default="", max_length=100_000)
    sources: list[TestabilityBenchmarkSource] = Field(default_factory=list, max_length=20)
    task_instruction: str = Field(default="", max_length=5000)
    expected_source_quotes: list[str] = Field(default_factory=list, max_length=500)
    expected_clarification_codes: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Legacy exact machine codes; prefer stable clarification categories for new datasets",
    )
    expected_clarification_categories: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Canonical Requirement-quality categories used for cross-run comparison",
    )
    expected_clarification_priorities: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Gold clarification categories or codes from highest to lowest priority",
    )
    expected_obligation_keys: list[str] = Field(default_factory=list, max_length=1000)
    expected_obligation_sources: dict[str, str] = Field(
        default_factory=dict,
        description="Human answer key mapping each obligation identifier to its exact source quote",
    )
    expected_clarification_unlocks: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Gold mapping from a clarification code to the obligations it can unlock",
    )

    @model_validator(mode="after")
    def validate_clarification_answer_key(self):
        source_text = "\n".join(
            [self.source_text, *(source.text for source in self.sources)]
        )
        if not source_text.strip():
            raise ValueError("benchmark_case_requires_source_text_or_documents")
        if any(quote not in source_text for quote in self.expected_source_quotes):
            raise ValueError("benchmark_expected_quote_must_appear_in_source")
        if self.expected_obligation_sources:
            if not self.expected_obligation_keys:
                self.expected_obligation_keys = list(self.expected_obligation_sources)
            if set(self.expected_obligation_sources) != set(self.expected_obligation_keys):
                raise ValueError("benchmark_obligation_sources_must_match_expected_obligations")
            if any(quote not in source_text for quote in self.expected_obligation_sources.values()):
                raise ValueError("benchmark_obligation_quote_must_appear_in_source")
        clarification_codes = set(
            self.expected_clarification_categories or self.expected_clarification_codes
        )
        obligation_keys = set(self.expected_obligation_keys)
        if not set(self.expected_clarification_priorities).issubset(clarification_codes):
            raise ValueError("benchmark_priority_must_reference_expected_clarifications")
        if not set(self.expected_clarification_unlocks).issubset(clarification_codes):
            raise ValueError("benchmark_unlocks_must_reference_expected_clarifications")
        if any(
            not set(unlocked).issubset(obligation_keys)
            for unlocked in self.expected_clarification_unlocks.values()
        ):
            raise ValueError("benchmark_unlocks_must_reference_expected_obligations")
        return self


class TestabilityBenchmarkCase(TestabilityBenchmarkGoldCase):
    """Scoring form: gold scenario plus observable outputs from three pipelines."""

    clarification_without_obligation_planning: TestabilityBenchmarkCandidate = Field(
        default_factory=TestabilityBenchmarkCandidate
    )
    compiler: TestabilityBenchmarkCandidate = Field(default_factory=TestabilityBenchmarkCandidate)
    direct_generation: TestabilityBenchmarkCandidate = Field(default_factory=TestabilityBenchmarkCandidate)


class TestabilityBenchmarkRequest(BaseModel):
    cases: list[TestabilityBenchmarkCase] = Field(min_length=1, max_length=500)


class TestabilityBenchmarkReport(BaseModel):
    total_cases: int
    clarification_without_obligation_planning: dict
    compiler: dict
    direct_generation: dict
    cases: list[dict]
    run_id: str | None = None
    dataset_id: str | None = None
    pipeline_metadata: dict = Field(default_factory=dict)
    pipeline_failures: list[dict] = Field(default_factory=list)
    pipeline_rejections: list[dict] = Field(default_factory=list)
    duration_ms: int | None = None
    clarification_savings_vs_baseline: float | None = None
    execution_status: Literal["COMPLETE", "PARTIAL"] = "COMPLETE"
    created_at: str | None = None


class TestabilityBenchmarkDatasetCreate(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    created_by: str = Field(min_length=1, max_length=200)
    cases: list[TestabilityBenchmarkGoldCase] = Field(min_length=1, max_length=100)


class TestabilityBenchmarkDataset(BaseModel):
    dataset_id: str
    title: str
    revision: int = 1
    created_at: str
    created_by: str
    cases: list[TestabilityBenchmarkGoldCase]
