import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.schemas.contracts.common import AnalysisFindingStatus, TestabilityStatus


def normalize_testability_status(value):
    return {"CONDITIONALLY_TESTABLE": "TESTABLE_WITH_RISK", "UNTESTABLE": "NOT_TESTABLE"}.get(
        value, value
    )


class GeneratedStep(BaseModel):
    action: str = Field(min_length=2, max_length=5000)
    expected: str = Field(min_length=2, max_length=5000)
    test_data: dict = Field(default_factory=dict)


class SecurityCandidate(BaseModel):
    category: str
    title: str = Field(min_length=2, max_length=300)
    preconditions: list[str] = Field(min_length=1, max_length=30)
    action: str = Field(min_length=2, max_length=5000)
    expected: str = Field(min_length=2, max_length=5000)
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value):
        if value not in ['authorization', 'authentication', 'input_validation', 'session', 'data_protection']:
            raise ValueError('INVALID_GENERATION_CATEGORIES')
        return value


class PerformanceScenario(BaseModel):
    workload_type: str
    title: str = Field(min_length=2, max_length=300)
    virtual_users: int = Field(ge=1, le=1000000)
    requests_per_second: float | None = Field(default=None, gt=0)
    duration_minutes: int = Field(ge=1, le=10080)
    ramp_pattern: str = Field(min_length=2, max_length=2000)
    actions: list[str] = Field(min_length=1, max_length=50)
    expected: str = Field(min_length=2, max_length=5000)

    @field_validator("workload_type")
    @classmethod
    def validate_workload_type(cls, value):
        if value not in ['baseline', 'load', 'stress', 'spike', 'soak']:
            raise ValueError('INVALID_GENERATION_CATEGORIES')
        return value


class GeneratedCase(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    category: str
    objective: str = Field(min_length=2, max_length=5000)
    preconditions: str = Field(default="", max_length=5000)
    steps: list[GeneratedStep] = Field(min_length=1, max_length=50)
    expected: str = Field(min_length=2, max_length=5000)
    acceptance_criterion_ids: list[str] = Field(default_factory=list)
    techniques: list[str] = Field(default_factory=list)
    coverage_obligations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class TestBasisRef(BaseModel):
    artifact_type: Literal[
        "REQUIREMENT_VERSION",
        "ACCEPTANCE_CRITERION",
        "API_OPERATION",
        "KNOWLEDGE_SOURCE",
        "BUSINESS_RULE",
        "RISK_RANKING",
        "DEFECT",
        "REGULATION",
    ]
    artifact_id: str = Field(min_length=1, max_length=200)
    artifact_version_id: str | None = Field(default=None, max_length=200)
    relationship: str = Field(default="DERIVED_FROM", min_length=1, max_length=100)
    source_span: dict[str, Any] | None = None


class AnalysisFinding(BaseModel):
    finding_id: str = Field(min_length=1, max_length=200)
    finding_type: Literal[
        "AMBIGUITY",
        "OMISSION",
        "INCONSISTENCY",
        "CONTRADICTION",
        "UNTESTABLE",
        "MISSING_ACCEPTANCE_CRITERIA",
        "MISSING_ERROR_BEHAVIOR",
        "MISSING_PERMISSION_RULE",
        "MISSING_BOUNDARY",
        "MISSING_NON_FUNCTIONAL_CRITERIA",
    ]
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    source_ref: TestBasisRef
    description: str = Field(min_length=2, max_length=5000)
    suggestion: str = Field(default="", max_length=5000)
    status: AnalysisFindingStatus = AnalysisFindingStatus.OPEN
    resolved_by: str | None = Field(default=None, max_length=200)
    resolution_ref: str | None = Field(default=None, max_length=500)


class TestConditionCreate(BaseModel):
    condition_key: str | None = Field(default=None, max_length=80, pattern=r"^[A-Z][A-Z0-9_-]+$")
    title: str = Field(min_length=2, max_length=300)
    category: Literal["POSITIVE", "NEGATIVE", "BOUNDARY"] | None = None
    description_doc: dict[str, Any]
    basis_refs: list[TestBasisRef] = Field(min_length=1, max_length=200)
    coverage_item: str = Field(min_length=1, max_length=500)
    test_level: str = Field(min_length=1, max_length=100)
    test_type: str = Field(min_length=1, max_length=100)
    risk: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    technique_candidates: list[str] = Field(default_factory=list, max_length=100)
    testability_status: TestabilityStatus = TestabilityStatus.TESTABLE
    analysis_findings: list[AnalysisFinding] = Field(default_factory=list, max_length=200)
    origin: Literal["MANUAL", "AI_CANDIDATE_CONFIRMED"] = "MANUAL"
    ai_result_id: str | None = Field(default=None, max_length=200)

    @field_validator("description_doc")
    @classmethod
    def validate_description_doc(cls, value):
        if value.get("type") != "doc" or not isinstance(value.get("content", []), list):
            raise ValueError("Tiptap JSON không hợp lệ")
        return value

    @field_validator("testability_status", mode="before")
    @classmethod
    def normalize_testability(cls, value):
        return normalize_testability_status(value)


class TestConditionPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    category: Literal["POSITIVE", "NEGATIVE", "BOUNDARY"] | None = None
    description_doc: dict[str, Any] | None = None
    basis_refs: list[TestBasisRef] | None = Field(default=None, min_length=1, max_length=200)
    coverage_item: str | None = Field(default=None, min_length=1, max_length=500)
    test_level: str | None = Field(default=None, min_length=1, max_length=100)
    test_type: str | None = Field(default=None, min_length=1, max_length=100)
    risk: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None
    technique_candidates: list[str] | None = Field(default=None, max_length=100)
    testability_status: TestabilityStatus | None = None
    analysis_findings: list[AnalysisFinding] | None = Field(default=None, max_length=200)

    @field_validator("testability_status", mode="before")
    @classmethod
    def normalize_testability(cls, value):
        return normalize_testability_status(value)


class TestConditionTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=5000)


class FindingResolutionInput(BaseModel):
    expected_revision: int = Field(ge=1)
    status: AnalysisFindingStatus
    resolution_ref: str = Field(min_length=2, max_length=500)
    note: str = Field(min_length=2, max_length=5000)


class TestAnalysisAIInput(BaseModel):
    basis_refs: list[TestBasisRef] = Field(min_length=1, max_length=100)
    instruction: str = Field(default="", max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=200)


class TestAnalysisInput(BaseModel):
    basis_refs: list[TestBasisRef] = Field(min_length=1, max_length=100)


class AnalysisFindingCreate(BaseModel):
    artifact_type: str = Field(min_length=1, max_length=100)
    artifact_id: str = Field(min_length=1, max_length=200)
    artifact_version_id: str | None = Field(default=None, max_length=200)
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
        "DUPLICATE",
        "OTHER",
    ]
    severity: Literal["BLOCKER", "MAJOR", "MINOR", "INFO"]
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(min_length=2, max_length=5000)
    source_span: dict[str, Any] | None = None
    suggestion: str = Field(default="", max_length=5000)
    owner_id: str | None = Field(default=None, max_length=200)


class AnalysisFindingAssignment(BaseModel):
    expected_revision: int = Field(ge=1)
    owner_id: str = Field(min_length=1, max_length=200)


class AnalysisFindingTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    resolution: str = Field(min_length=2, max_length=5000)
    resolution_ref: str | None = Field(default=None, max_length=500)


class TestConditionBulkPriorityInput(BaseModel):
    items: list[dict[str, Any]] = Field(min_length=1, max_length=500)

    @field_validator("items")
    @classmethod
    def validate_items(cls, values):
        allowed = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        for value in values:
            if (
                not value.get("condition_id")
                or value.get("priority") not in allowed
                or int(value.get("expected_revision", 0)) < 1
            ):
                raise ValueError("Mục ưu tiên TestCondition không hợp lệ")
        return values


def condition_snapshot(value):
    return {
        "condition_id": value["_id"],
        "project_id": value["project_id"],
        "condition_key": value["condition_key"],
        **{field: value.get(field) for field in TestConditionCreate.model_fields},
        "basis_snapshots": value.get("basis_snapshots", []),
    }


def condition_hash(value):
    canonical = json.dumps(
        condition_snapshot(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
