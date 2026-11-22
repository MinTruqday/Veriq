from typing import Any, Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.sensitive_data import secret_pattern
from src.schemas.contracts.common import empty_doc, validate_tiptap_document

TestScenarioCategory: TypeAlias = str
TestCaseType: TypeAlias = str
AIRunStatus: TypeAlias = Literal["manual", "candidate", "automated"]

class ScenarioCreate(BaseModel):
    scenario_key: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=2, max_length=300)
    objective: str = Field(default="", max_length=5000)
    risk: str = Field(min_length=1, max_length=100)
    priority: str = Field(min_length=1, max_length=100)
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=200)
    acceptance_criterion_ids: list[str] = Field(default_factory=list, max_length=500)
    test_condition_ids: list[str] = Field(default_factory=list, max_length=500)
    status: Literal["draft", "in_review", "approved", "archived"] = "draft"
    origin: Literal["manual", "ai_generated", "import"] = "manual"
    category: TestScenarioCategory = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=10000)
    actors: list[str] = Field(default_factory=list, max_length=100)
    preconditions: str = Field(default="", max_length=5000)
    business_flow: str = Field(default="", max_length=10000)
    expected_outcome: str = Field(default="", max_length=5000)
    test_data_notes: str = Field(default="", max_length=5000)
    test_level: str | None = Field(default=None, max_length=100)
    test_kind: str = Field(default="", max_length=100)
    owner_id: str | None = Field(default=None, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("Scenario category must not be empty")
        return normalized

    @field_validator("risk", "priority")
    @classmethod
    def normalize_assessment_label(cls, value):
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Mức rủi ro và ưu tiên không được để trống")
        return normalized


class ScenarioPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    objective: str | None = Field(default=None, max_length=5000)
    risk: str | None = Field(default=None, min_length=1, max_length=100)
    priority: str | None = Field(default=None, min_length=1, max_length=100)
    requirement_version_ids: list[str] | None = Field(default=None, max_length=200)
    acceptance_criterion_ids: list[str] | None = Field(default=None, max_length=500)
    test_condition_ids: list[str] | None = Field(default=None, max_length=500)
    category: TestScenarioCategory | None = None
    description: str | None = Field(default=None, max_length=10000)
    actors: list[str] | None = Field(default=None, max_length=100)
    preconditions: str | None = Field(default=None, max_length=5000)
    business_flow: str | None = Field(default=None, max_length=10000)
    expected_outcome: str | None = Field(default=None, max_length=5000)
    test_data_notes: str | None = Field(default=None, max_length=5000)
    test_level: str | None = Field(default=None, max_length=100)
    test_kind: str | None = Field(default=None, max_length=100)
    owner_id: str | None = Field(default=None, max_length=200)
    tags: list[str] | None = Field(default=None, max_length=100)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value):
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Scenario category must not be empty")
        return normalized

    @field_validator("risk", "priority")
    @classmethod
    def normalize_assessment_label(cls, value):
        if value is None:
            return value
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Mức rủi ro và ưu tiên không được để trống")
        return normalized


class TestStep(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    order: int = Field(ge=1)
    action_doc: dict[str, Any] = Field(default_factory=empty_doc)
    test_data: dict[str, Any] = Field(default_factory=dict)
    expected_doc: dict[str, Any] = Field(default_factory=empty_doc)

    @field_validator("action_doc", "expected_doc")
    @classmethod
    def validate_documents(cls, value):
        return validate_tiptap_document(value)


class BddStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=200)
    keyword: Literal["Given", "When", "Then", "And", "But"]
    text: str = Field(min_length=1, max_length=2000)


class BddScenario(BaseModel):
    feature: str = Field(min_length=2, max_length=300)
    scenario: str = Field(min_length=2, max_length=300)
    steps: list[BddStep] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_step_ids(self):
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("Định danh bước BDD không được trùng")
        return self




class EvidenceQuote(BaseModel):
    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=2, max_length=1000)


class TestImportVersionResolution(BaseModel):
    target_version_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=2000)


class TestImportConfirm(BaseModel):
    selected_indexes: list[int] = Field(default_factory=list, max_length=2000)
    separate_indexes: list[int] = Field(default_factory=list, max_length=2000)
    separate_reasons: dict[int, str] = Field(default_factory=dict)
    version_resolutions: dict[int, TestImportVersionResolution] = Field(default_factory=dict)
    accept_incomplete: bool = False


class TestCaseDraftCreate(BaseModel):
    test_case_key: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=2, max_length=300)
    type: TestCaseType = Field(min_length=1, max_length=100)
    test_level: str | None = Field(default=None, max_length=100)
    test_kind: str | None = Field(default=None, max_length=100)
    priority: str = Field(default="unassessed", min_length=1, max_length=100)
    risk: str = Field(default="unassessed", min_length=1, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)
    objective_doc: dict[str, Any] = Field(default_factory=empty_doc)
    preconditions_doc: dict[str, Any] = Field(default_factory=empty_doc)
    steps: list[TestStep] = Field(default_factory=list, max_length=500)
    test_data: dict[str, Any] = Field(default_factory=dict)
    expected_result_doc: dict[str, Any] = Field(default_factory=empty_doc)
    postconditions_doc: dict[str, Any] = Field(default_factory=empty_doc)
    alternate_flows_doc: dict[str, Any] = Field(default_factory=empty_doc)
    exception_flows_doc: dict[str, Any] = Field(default_factory=empty_doc)
    tags: list[str] = Field(default_factory=list, max_length=100)
    owner_id: str | None = Field(default=None, max_length=200)
    techniques: list[str] = Field(default_factory=list, max_length=50)
    automation_status: AIRunStatus = "manual"
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    data_set_version_ids: list[str] = Field(default_factory=list, max_length=100)
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=200)
    acceptance_criterion_ids: list[str] = Field(default_factory=list, max_length=500)
    coverage_item_ids: list[str] = Field(default_factory=list, max_length=500)
    test_condition_ids: list[str] = Field(default_factory=list, max_length=500)
    scenario_id: str | None = None
    bdd: BddScenario | None = None
    origin: Literal["manual", "ai_generated", "clone", "import", "maintenance"] = "manual"
    source_evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    acceptance_criteria_snapshot_ids: list[str] | None = Field(default=None, max_length=500)
    evidence_refs: list[str] = Field(default_factory=list, max_length=200)
    evidence_quotes: list[EvidenceQuote] = Field(default_factory=list, max_length=20)
    suite_signature: str | None = Field(default=None, max_length=128)
    duplicate_reason: str | None = Field(default=None, min_length=2, max_length=2000)
    target_version_id: str | None = Field(default=None, min_length=1, max_length=200)
    version_reason: str | None = Field(default=None, min_length=2, max_length=2000)

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("Test case type must not be empty")
        return normalized

    @field_validator("priority", "risk")
    @classmethod
    def normalize_assessment_labels(cls, value):
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Mức đánh giá không được để trống")
        return normalized

    @field_validator(
        "preconditions_doc", "objective_doc", "expected_result_doc", "postconditions_doc",
        "alternate_flows_doc", "exception_flows_doc",
    )
    @classmethod
    def validate_documents(cls, value):
        return validate_tiptap_document(value)

    @model_validator(mode="after")
    def validate_step_order(self):
        orders = [step.order for step in self.steps]
        if len(orders) != len(set(orders)):
            raise ValueError("Thứ tự bước kiểm thử không được trùng")
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("Định danh bước kiểm thử không được trùng")
        if self.evidence_refs and not set(self.evidence_refs) <= {
            item.get("artifact_version_id") for item in self.source_evidence
        }:
            raise ValueError("Dẫn chứng không nằm trong nguồn của ca kiểm thử")
        source_text_by_ref = {
            item.get("artifact_version_id"): item.get("text", "")
            for item in self.source_evidence
        }
        if any(
            quote.evidence_ref not in self.evidence_refs
            or quote.quote.strip() not in source_text_by_ref.get(quote.evidence_ref, "")
            for quote in self.evidence_quotes
        ):
            raise ValueError("Trích dẫn không nằm trong nguồn của ca kiểm thử")
        return self


class TestCaseDraftBatchComparisonInput(BaseModel):
    items: list[TestCaseDraftCreate] = Field(min_length=2, max_length=100)


class TestCaseDraftPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    type: TestCaseType | None = None
    test_level: str | None = Field(default=None, max_length=100)
    test_kind: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, min_length=1, max_length=100)
    risk: str | None = Field(default=None, min_length=1, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)
    objective_doc: dict[str, Any] | None = None
    preconditions_doc: dict[str, Any] | None = None
    steps: list[TestStep] | None = None
    test_data: dict[str, Any] | None = None
    expected_result_doc: dict[str, Any] | None = None
    postconditions_doc: dict[str, Any] | None = None
    alternate_flows_doc: dict[str, Any] | None = None
    exception_flows_doc: dict[str, Any] | None = None
    tags: list[str] | None = None
    owner_id: str | None = Field(default=None, max_length=200)
    techniques: list[str] | None = None
    automation_status: AIRunStatus | None = None
    attachments: list[dict[str, Any]] | None = None
    data_set_version_ids: list[str] | None = None
    requirement_version_ids: list[str] | None = None
    acceptance_criterion_ids: list[str] | None = None
    coverage_item_ids: list[str] | None = None
    test_condition_ids: list[str] | None = None
    scenario_id: str | None = None
    bdd: BddScenario | None = None
    duplicate_reason: str | None = Field(default=None, min_length=2, max_length=2000)

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value):
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Test case type must not be empty")
        return normalized

    @field_validator("priority", "risk")
    @classmethod
    def normalize_assessment_labels(cls, value):
        if value is None:
            return value
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Mức đánh giá không được để trống")
        return normalized

    @field_validator(
        "preconditions_doc", "objective_doc", "expected_result_doc", "postconditions_doc",
        "alternate_flows_doc", "exception_flows_doc",
    )
    @classmethod
    def validate_documents(cls, value):
        return validate_tiptap_document(value)


class TestCaseFreezeInput(BaseModel):
    expected_revision: int = Field(ge=1)
    change_reason: str = Field(default="Phê duyệt phiên bản kiểm thử", max_length=2000)
    review_note: str = Field(default="", max_length=2000)


class TestCaseMergeChoice(BaseModel):
    field: str = Field(min_length=1, max_length=100)
    step_id: str | None = Field(default=None, max_length=200)
    source: Literal["ORIGINAL", "AI", "MANUAL"]


class TestCaseMergeSave(BaseModel):
    expected_revision: int = Field(ge=1)
    comparison_token: str = Field(min_length=64, max_length=64)
    operation_id: str = Field(min_length=8, max_length=100)
    result: TestCaseDraftCreate
    choices: list[TestCaseMergeChoice] = Field(default_factory=list, max_length=2000)


class TestCaseBatchAcceptItem(BaseModel):
    draft_id: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(ge=1)
    comparison_token: str = Field(min_length=64, max_length=64)


class TestCaseBatchAccept(BaseModel):
    items: list[TestCaseBatchAcceptItem] = Field(min_length=1, max_length=100)
    operation_id: str = Field(min_length=8, max_length=100)
    review_note: str = Field(min_length=2, max_length=2000)

    @model_validator(mode="after")
    def unique_drafts(self):
        if len({item.draft_id for item in self.items}) != len(self.items):
            raise ValueError("Nhóm duyệt không được có bản nháp trùng")
        return self


class TestCaseCloneInput(BaseModel):
    expected_current_version_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=2, max_length=300)


class TestCaseVersionDraftInput(BaseModel):
    expected_current_version_id: str = Field(min_length=1, max_length=200)
    change_reason: str = Field(min_length=2, max_length=2000)
    title: str | None = Field(default=None, min_length=2, max_length=300)


class TestCaseLifecycleInput(BaseModel):
    expected_current_version_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=2000)


class DataSetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    variables: dict[str, Any] = Field(default_factory=dict)
    secret_refs: dict[str, str] = Field(default_factory=dict)
    generation_source: Literal["USER", "AI_ASSISTED"] = "USER"
    source_requirement_version_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_secret_policy(self):
        unsafe_keys = [
            key
            for key in self.variables
            if secret_pattern().search(key)
        ]
        if unsafe_keys:
            raise ValueError("Dữ liệu bí mật phải được khai báo bằng secret_refs")
        invalid_refs = [
            key for key, value in self.secret_refs.items() if not value.startswith("secret://")
        ]
        if invalid_refs:
            raise ValueError("Secret reference phải bắt đầu bằng secret://")
        if len(set(self.source_requirement_version_ids)) != len(self.source_requirement_version_ids):
            raise ValueError("Nguồn yêu cầu không được trùng")
        if self.generation_source == "AI_ASSISTED" and not self.source_requirement_version_ids:
            raise ValueError("Bộ dữ liệu có hỗ trợ AI phải lưu nguồn yêu cầu")
        return self


class DataSetAISuggestionInput(BaseModel):
    requirement_version_ids: list[str] = Field(min_length=1, max_length=20)
    instruction: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def unique_requirement_versions(self):
        if len(set(self.requirement_version_ids)) != len(self.requirement_version_ids):
            raise ValueError("Không được chọn phiên bản yêu cầu trùng")
        return self


class DataSetVersionCreate(DataSetCreate):
    expected_current_version_id: str = Field(min_length=1, max_length=200)
    change_reason: str = Field(min_length=2, max_length=2000)


class DataSetBind(BaseModel):
    test_case_draft_id: str = Field(min_length=1, max_length=200)
    data_set_version_id: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(ge=1)


class DataSetPreview(BaseModel):
    data_set_version_id: str = Field(min_length=1, max_length=200)
    max_rows: int = Field(default=100, ge=1, le=1000)


class DataSetArchive(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=2000)


class TraceLinkCreate(BaseModel):
    project_id: str
    source_type: Literal["requirement_version", "acceptance_criterion", "test_scenario"]
    source_id: str
    target_type: Literal["test_case_version"] = "test_case_version"
    target_id: str
    link_type: Literal["verifies", "covers", "derived_from", "relates_to"] = "verifies"
    confidence: float = Field(default=1, ge=0, le=1)
    origin: Literal["manual", "ai_suggested", "import", "trace_recovery"] = "manual"
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


class CoverageSnapshotCreate(BaseModel):
    label: str = Field(min_length=2, max_length=500)
    release: str = Field(default="", max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    build: str = Field(default="", max_length=200)
    build_id: str | None = Field(default=None, max_length=200)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class ProposalAction(BaseModel):
    expected_revision: int = Field(ge=1)
    patch: dict[str, Any] | None = None
    review_note: str = Field(default="", max_length=2000)
    review_reason_code: Literal[
        "OUT_OF_SCOPE",
        "INCORRECT",
        "INCOMPLETE",
        "DUPLICATE",
        "UNSUPPORTED_BY_SOURCE",
        "RISK_ACCEPTED",
        "OTHER",
    ] | None = None


class ProposalRegenerateInput(BaseModel):
    expected_revision: int = Field(ge=1)
    instruction: str = Field(min_length=2, max_length=5000)


class ImpactOverrideItem(BaseModel):
    test_case_version_id: str = Field(min_length=1, max_length=200)
    classification: Literal["STILL_VALID", "POTENTIALLY_AFFECTED", "NEEDS_UPDATE", "OBSOLETE"]
    reason: str = Field(min_length=2, max_length=2000)


class ImpactReviewInput(BaseModel):
    expected_revision: int = Field(ge=1)
    overrides: list[ImpactOverrideItem] = Field(default_factory=list, max_length=5000)
    review_note: str = Field(default="", max_length=5000)


class ImpactRerunInput(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=2000)
    knowledge_index_version: str | None = Field(default=None, max_length=200)
    algorithm_version: Literal["impact_pipeline"] = "impact_pipeline"


class ChangeSetReviewInput(BaseModel):
    expected_revision: int = Field(ge=1)
    changes: list[dict[str, Any]] = Field(min_length=1, max_length=500)
    review_note: str = Field(default="", max_length=5000)

    @field_validator("changes")
    @classmethod
    def validate_change_facts(cls, values):
        for value in values:
            if not str(value.get("type") or "").strip():
                raise ValueError("ChangeFact phải có type")
        return values


class RegressionApprovalInput(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    selected_test_case_version_ids: list[str] | None = Field(default=None, max_length=5000)
    review_note: str = Field(default="", max_length=5000)
