import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.text_matching import source_quote_spans


def validate_unique_benchmark_case_ids(cases):
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("benchmark_case_ids_must_be_unique")


def benchmark_quote_occurs_in_source(source_text, quote):
    normalized_source = unicodedata.normalize("NFC", source_text)
    normalized_quote = unicodedata.normalize("NFC", quote)
    return bool(source_quote_spans(normalized_source, normalized_quote))


def benchmark_answer_key_review_covers_cases(cases, review):
    if not review:
        return False
    if isinstance(review, list):
        reviews = review
    else:
        reviews = review.get("case_reviews") if isinstance(review, dict) else review.case_reviews
    if not isinstance(reviews, list):
        return False
    return benchmark_answer_key_review_has_case_coverage(cases, reviews) and all(
        (item.get("source_quotes_verified") if isinstance(item, dict) else item.source_quotes_verified)
        and (item.get("obligations_verified") if isinstance(item, dict) else item.obligations_verified)
        and (item.get("clarifications_verified") if isinstance(item, dict) else item.clarifications_verified)
        for item in reviews
    )


def benchmark_answer_key_review_has_case_coverage(cases, reviews):
    case_ids = {
        str(case.get("case_id") if isinstance(case, dict) else case.case_id)
        for case in cases
    }
    if not isinstance(reviews, list):
        return False
    reviewed_ids = [
        str(item.get("case_id") if isinstance(item, dict) else item.case_id)
        for item in reviews
    ]
    return (
        bool(case_ids)
        and len(reviewed_ids) == len(set(reviewed_ids))
        and set(reviewed_ids) == case_ids
    )


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
    )
    completeness: int = Field(
        ge=0,
        le=10,
    )
    relevance: int = Field(
        ge=0,
        le=10,
    )
    explanation: str = Field(
        min_length=1,
        max_length=2000,
    )


class TestabilityBenchmarkCitation(BaseModel):
    quote: str = Field(min_length=1, max_length=2000)
    source_ref: str = Field(min_length=1, max_length=200)


class TestabilityBenchmarkCandidate(BaseModel):
    """One system's observable output for a benchmark case."""

    source_quotes: list[str] = Field(default_factory=list, max_length=500)
    source_quote_citations: list[TestabilityBenchmarkCitation] = Field(
        default_factory=list, max_length=500
    )
    clarification_codes: list[str] = Field(default_factory=list, max_length=500)
    clarification_categories: list[str] = Field(default_factory=list, max_length=500)
    obligation_keys: list[str] = Field(default_factory=list, max_length=1000)
    obligation_evidence: dict[str, list[str]] = Field(default_factory=dict)
    obligation_citations: dict[str, list[TestabilityBenchmarkCitation]] = Field(
        default_factory=dict
    )


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
    scenario_family: Literal[
        "COMPLETE",
        "MISSING_OR_AMBIGUOUS",
        "DUPLICATE_OR_CONFLICT",
    ] | None = None
    source_text: str = Field(default="", max_length=100_000)
    sources: list[TestabilityBenchmarkSource] = Field(default_factory=list, max_length=20)
    task_instruction: str = Field(default="", max_length=5000)
    expected_source_quotes: list[str] = Field(default_factory=list, max_length=500)
    expected_source_quote_sources: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Optional answer key mapping a source quote to the source versions that support it",
    )
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
    expected_obligation_source_refs: dict[str, str] = Field(
        default_factory=dict,
        description="Optional answer key mapping an obligation identifier to its source version reference",
    )
    expected_clarification_unlocks: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Gold mapping from a clarification code to the obligations it can unlock",
    )

    @model_validator(mode="after")
    def validate_clarification_answer_key(self):
        for field_name in (
            "expected_source_quotes",
            "expected_clarification_codes",
            "expected_clarification_categories",
            "expected_clarification_priorities",
            "expected_obligation_keys",
        ):
            values = getattr(self, field_name)
            normalized_values = []
            for value in values:
                normalized = unicodedata.normalize("NFC", " ".join(value.split()))
                if field_name == "expected_source_quotes":
                    normalized = normalized.rstrip(".!?。！？").rstrip()
                normalized_values.append(normalized)
            if len(normalized_values) != len(set(normalized_values)):
                raise ValueError(f"benchmark_{field_name}_must_be_unique")
        if self.sources:
            source_ids = [source.source_id for source in self.sources]
            source_version_ids = [source.artifact_version_id for source in self.sources]
            if len(source_ids) != len(set(source_ids)):
                raise ValueError("benchmark_source_ids_must_be_unique")
            if len(source_version_ids) != len(set(source_version_ids)):
                raise ValueError("benchmark_source_version_ids_must_be_unique")
            source_texts = [source.text for source in self.sources if source.text.strip()]
        else:
            source_texts = [self.source_text] if self.source_text.strip() else []
        if not source_texts:
            raise ValueError("benchmark_case_requires_source_text_or_documents")
        if self.expected_obligation_sources and not self.expected_source_quotes:
            self.expected_source_quotes = list(dict.fromkeys(self.expected_obligation_sources.values()))
        if any(
            not quote.strip()
            or not any(
                benchmark_quote_occurs_in_source(source_text, quote)
                for source_text in source_texts
            )
            for quote in self.expected_source_quotes
        ):
            raise ValueError("benchmark_expected_quote_must_appear_in_source")
        if self.expected_obligation_sources:
            if not self.expected_obligation_keys:
                self.expected_obligation_keys = list(self.expected_obligation_sources)
            if set(self.expected_obligation_sources) != set(self.expected_obligation_keys):
                raise ValueError("benchmark_obligation_sources_must_match_expected_obligations")
            if any(
                not quote.strip()
                or not any(
                    benchmark_quote_occurs_in_source(source_text, quote)
                    for source_text in source_texts
                )
                for quote in self.expected_obligation_sources.values()
            ):
                raise ValueError("benchmark_obligation_quote_must_appear_in_source")
        if self.expected_obligation_source_refs:
            if not self.sources:
                raise ValueError("benchmark_source_reference_answer_key_requires_explicit_sources")
            if not set(self.expected_obligation_source_refs).issubset(
                self.expected_obligation_sources
            ):
                raise ValueError("benchmark_source_reference_must_match_expected_obligations")
            allowed_source_refs = {source.artifact_version_id for source in self.sources}
            if not set(self.expected_obligation_source_refs.values()).issubset(
                allowed_source_refs
            ):
                raise ValueError("benchmark_expected_source_reference_not_found")
            source_text_by_ref = {
                source.artifact_version_id: source.text for source in self.sources
            }
            if any(
                not benchmark_quote_occurs_in_source(
                    source_text_by_ref[source_ref],
                    self.expected_obligation_sources[obligation_key],
                )
                for obligation_key, source_ref in self.expected_obligation_source_refs.items()
            ):
                raise ValueError("benchmark_obligation_quote_not_in_cited_source")
        if self.expected_source_quote_sources:
            if not self.sources:
                raise ValueError("benchmark_quote_source_answer_key_requires_explicit_sources")
            expected_quotes = {
                unicodedata.normalize("NFC", " ".join(quote.split()))
                .rstrip(".!?。！？")
                .casefold()
                for quote in self.expected_source_quotes
            }
            mapped_quotes = {
                unicodedata.normalize("NFC", " ".join(quote.split()))
                .rstrip(".!?。！？")
                .casefold()
                for quote in self.expected_source_quote_sources
            }
            if mapped_quotes != expected_quotes:
                raise ValueError("benchmark_quote_source_answer_key_must_cover_all_expected_quotes")
            allowed_source_refs = {source.artifact_version_id for source in self.sources}
            source_text_by_ref = {
                source.artifact_version_id: source.text for source in self.sources
            }
            for quote, source_refs in self.expected_source_quote_sources.items():
                normalized_quote = unicodedata.normalize(
                    "NFC", " ".join(quote.split())
                ).rstrip(".!?。！？").casefold()
                if normalized_quote not in expected_quotes:
                    raise ValueError("benchmark_quote_source_answer_key_quote_not_expected")
                if not source_refs or len(source_refs) != len(set(source_refs)):
                    raise ValueError("benchmark_quote_source_answer_key_refs_must_be_unique")
                for source_ref in source_refs:
                    source_text = source_text_by_ref.get(source_ref)
                    if source_text is None:
                        raise ValueError("benchmark_expected_source_reference_not_found")
                    if not benchmark_quote_occurs_in_source(source_text, quote):
                        raise ValueError("benchmark_expected_quote_not_in_cited_source")
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

    def validate_for_scoring(self):
        has_scored_behavior = bool(
            self.expected_clarification_codes
            or self.expected_clarification_categories
            or self.expected_obligation_keys
            or self.expected_obligation_sources
        )
        if not has_scored_behavior:
            raise ValueError("benchmark_case_requires_answer_key")
        if not self.expected_source_quotes:
            raise ValueError("benchmark_case_requires_source_quote_answer_key")
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

    @model_validator(mode="after")
    def validate_cases_for_scoring(self):
        validate_unique_benchmark_case_ids(self.cases)
        for case in self.cases:
            case.validate_for_scoring()
        return self


class TestabilityBenchmarkReport(BaseModel):
    total_cases: int
    clarification_without_obligation_planning: dict
    compiler: dict
    direct_generation: dict
    cases: list[dict]
    run_id: str | None = None
    dataset_id: str | None = None
    dataset_revision: int | None = Field(default=None, ge=1)
    answer_key_review: "TestabilityBenchmarkAnswerKeyReview | None" = None
    pipeline_metadata: dict = Field(
        default_factory=dict,
        description=(
            "Run-level provider/model metadata and raw candidates; model_metadata_by_capability "
            "maps each pipeline capability to case_id to the model metadata for that case."
        ),
    )
    pipeline_failures: list[dict] = Field(default_factory=list)
    pipeline_rejections: list[dict] = Field(default_factory=list)
    pipeline_case_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    metric_case_counts: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Number of cases with a defined answer-key score for each pipeline metric.",
    )
    paired_pipeline_comparisons: dict[str, dict] = Field(
        default_factory=dict,
        description=(
            "Metrics recomputed on the same cases accepted by both pipelines; use these "
            "for fair pipeline comparison instead of comparing independently selected cohorts."
        ),
    )
    scoring_method: dict = Field(
        default_factory=dict,
        description=(
            "Machine-readable definitions for the reported metrics and their limitations; "
            "scores are descriptive and are not an accuracy guarantee."
        ),
    )
    benchmark_design: dict = Field(default_factory=dict)
    scenario_family_counts: dict[str, int] = Field(default_factory=dict)
    duration_ms: int | None = None
    clarification_savings_vs_baseline: float | None = Field(
        default=None,
        description=(
            "Average clarification count in the baseline minus the compiler count, only for cases "
            "where both pipelines were accepted. Positive means fewer questions; this is not a quality score."
        ),
    )
    clarification_savings_paired_cases: int = Field(
        default=0,
        ge=0,
        description="Number of cases accepted by both compared pipelines; denominator for clarification savings.",
    )
    execution_status: Literal["COMPLETE", "PARTIAL"] = "COMPLETE"
    created_at: str | None = None


class TestabilityBenchmarkMetricRepeatStats(BaseModel):
    observed_runs: int = Field(ge=0)
    mean: float | None = None
    population_stddev: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    paired_case_count: int | None = Field(default=None, ge=0)
    paired_case_ids: list[str] = Field(default_factory=list)


class TestabilityBenchmarkPipelineRepeatStats(BaseModel):
    runs_with_scores: int = Field(ge=0)
    stable_case_count: int = Field(default=0, ge=0)
    stable_case_ids: list[str] = Field(default_factory=list)
    runs_with_failures: int = Field(ge=0)
    rejected_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    metrics: dict[str, TestabilityBenchmarkMetricRepeatStats]


class TestabilityBenchmarkRepeatedReport(BaseModel):
    dataset_id: str
    dataset_revision: int | None = Field(default=None, ge=1)
    answer_key_review: "TestabilityBenchmarkAnswerKeyReview | None" = None
    requested_repetitions: int = Field(ge=1, le=5)
    completed_repetitions: int = Field(ge=0)
    partial_repetitions: int = Field(ge=0)
    failed_repetitions: int = Field(ge=0)
    run_ids: list[str]
    repetition_failures: list[dict] = Field(default_factory=list)
    pipeline_statistics: dict[str, TestabilityBenchmarkPipelineRepeatStats]
    paired_pipeline_statistics: dict[str, dict] = Field(
        default_factory=dict,
        description=(
            "Repeated descriptive statistics computed only from per-run cases accepted "
            "by both pipelines in each comparison."
        ),
    )
    clarification_savings_vs_baseline: TestabilityBenchmarkMetricRepeatStats = Field(
        default_factory=TestabilityBenchmarkMetricRepeatStats
    )
    execution_status: Literal["COMPLETE", "PARTIAL"]
    interpretation: str = (
        "Thống kê mô tả độ biến thiên giữa các lần chạy; không tự chứng minh khác biệt có ý nghĩa "
        "thống kê hoặc chất lượng của đáp án chuẩn."
    )
    benchmark_design: dict = Field(default_factory=dict)


class TestabilityBenchmarkDatasetCreate(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    cases: list[TestabilityBenchmarkGoldCase] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_cases_for_scoring(self):
        validate_unique_benchmark_case_ids(self.cases)
        for case in self.cases:
            case.validate_for_scoring()
        return self


class TestabilityBenchmarkDatasetUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    cases: list[TestabilityBenchmarkGoldCase] | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def strip_benchmark_dataset_title(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("benchmark_dataset_title_required")
        return value

    @model_validator(mode="after")
    def validate_dataset_update(self):
        if self.title is None and self.cases is None:
            raise ValueError("benchmark_dataset_update_requires_changes")
        if self.cases is not None:
            validate_unique_benchmark_case_ids(self.cases)
            for case in self.cases:
                case.validate_for_scoring()
        return self


class TestabilityBenchmarkCaseAnswerKeyReview(BaseModel):
    case_id: str = Field(min_length=1, max_length=200)
    source_quotes_verified: bool
    obligations_verified: bool
    clarifications_verified: bool
    rationale: str = Field(min_length=20, max_length=2000)

    @field_validator("rationale")
    @classmethod
    def strip_case_review_rationale(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("benchmark_case_review_rationale_required")
        return value


class TestabilityBenchmarkAnswerKeyReview(BaseModel):
    reviewer_id: str
    reviewer_identity_verified: bool = False
    decision: Literal["APPROVE", "RETURN_FOR_CORRECTION"] = "APPROVE"
    reviewed_revision: int = Field(ge=1)
    rationale: str
    reviewed_at: str
    case_reviews: list["TestabilityBenchmarkCaseAnswerKeyReview"] = Field(default_factory=list)


class TestabilityBenchmarkDatasetReview(BaseModel):
    expected_revision: int = Field(ge=1)
    decision: Literal["APPROVE", "RETURN_FOR_CORRECTION"] = "APPROVE"
    case_reviews: list[TestabilityBenchmarkCaseAnswerKeyReview] = Field(
        min_length=1, max_length=100
    )
    rationale: str = Field(
        min_length=20,
        max_length=2000,
        description="Review record covering source quotes, obligations, and clarification labels",
    )

    @field_validator("rationale")
    @classmethod
    def strip_review_values(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("benchmark_answer_key_review_field_required")
        return value

    @model_validator(mode="after")
    def validate_unique_reviewed_cases(self):
        case_ids = [item.case_id for item in self.case_reviews]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("benchmark_answer_key_review_case_ids_must_be_unique")
        return self


class TestabilityBenchmarkDataset(BaseModel):
    dataset_id: str
    title: str
    revision: int = 1
    created_at: str
    created_by: str
    creator_identity_verified: bool = False
    updated_at: str | None = None
    updated_by: str | None = None
    cases: list[TestabilityBenchmarkGoldCase]
    answer_key_review: TestabilityBenchmarkAnswerKeyReview | None = None
