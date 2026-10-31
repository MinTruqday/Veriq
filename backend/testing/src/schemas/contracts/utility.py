from typing import Any, Literal

from pydantic import BaseModel, Field


class DelegatedJobEnqueueInput(BaseModel):
    event: Literal[
        "impact.analysis.requested",
        "duplicate.scan.requested",
        "test.generate.requested",
        "requirement.semantic_diff.requested",
        "knowledge.index.requested",
        "requirement.extract.requested",
        "document.parse.requested",
        "document.summary.requested",
    ]
    artifact_version_id: str = Field(min_length=1, max_length=200)
    model_version: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)

class TestDesignChallengeInput(BaseModel):
    technique: Literal[
        "equivalence_partitioning", "boundary_value", "decision_table",
        "state_transition", "error_guessing",
    ]
    source_ref: str = Field(min_length=1, max_length=200)
    source_quote: str = Field(min_length=2, max_length=1000)
    hypothetical_fault: str = Field(min_length=2, max_length=2000)
    distinguishing_input: str = Field(min_length=2, max_length=2000)
    expected_result: str = Field(min_length=2, max_length=2000)
    existing_case_refs: list[str] = Field(min_length=1, max_length=100)


class GenerateInput(BaseModel):
    categories: list[str] = Field(default_factory=list, max_length=20)
    acceptance_criterion_ids: list[str] = Field(default_factory=list, max_length=500)
    techniques: list[Literal[
        "equivalence_partitioning", "boundary_value", "decision_table",
        "state_transition", "error_guessing",
    ]] = Field(default_factory=list, max_length=5)
    count_per_category: int = Field(default=1, ge=1, le=20)
    max_cases: int | None = Field(default=None, ge=1, le=100)
    instruction: str = Field(default="", max_length=5000)
    challenge_hypotheses: list[TestDesignChallengeInput] = Field(default_factory=list, max_length=5)
    challenge_suite_signature: str | None = Field(default=None, max_length=128)
    preview_only: bool = False


class TechniqueRecommendationInput(BaseModel):
    instruction: str = Field(default="", max_length=5000)


class TestCaseGenerateInput(GenerateInput):
    requirement_version_id: str = Field(min_length=1, max_length=200)


class SearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    artifact_types: list[str] = Field(default_factory=list, max_length=20)
    limit: int = Field(default=20, ge=1, le=100)


class ProjectQuestionInput(BaseModel):
    question: str = Field(min_length=2, max_length=5000)
    artifact_types: list[str] = Field(default_factory=list, max_length=20)
    evidence_limit: int = Field(default=20, ge=1, le=50)


class BulkTagInput(BaseModel):
    artifact_type: Literal["requirement", "test_case"]
    ids: list[str] = Field(min_length=1, max_length=5000)
    add_tags: list[str] = Field(default_factory=list, max_length=100)
    remove_tags: list[str] = Field(default_factory=list, max_length=100)
    preview: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class BulkSuiteInput(BaseModel):
    suite_id: str = Field(min_length=1, max_length=200)
    test_case_ids: list[str] = Field(min_length=1, max_length=5000)
    expected_revision: int = Field(ge=1)
    preview: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class BulkReviewRequiredInput(BaseModel):
    test_case_ids: list[str] = Field(min_length=1, max_length=5000)
    reason: str = Field(min_length=2, max_length=2000)
    preview: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class BulkArchiveInput(BaseModel):
    artifact_type: Literal["requirement", "test_case"]
    ids: list[str] = Field(min_length=1, max_length=5000)
    reason: str = Field(min_length=2, max_length=2000)
    preview: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class BulkProposalGenerateInput(BaseModel):
    impact_analysis_ids: list[str] = Field(min_length=1, max_length=5000)
    preview: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class BulkProposalApproveInput(BaseModel):
    proposal_ids: list[str] = Field(min_length=1, max_length=5000)
    review_note: str = Field(min_length=2, max_length=2000)
    preview: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
