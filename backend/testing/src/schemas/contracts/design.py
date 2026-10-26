from typing import Any, Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from src.schemas.contracts.common import empty_doc
from src.schemas.contracts.utility import TestDesignChallengeInput

RiskLevel: TypeAlias = Literal["critical", "high", "medium", "low"]
TestCaseAssessmentLevel: TypeAlias = Literal[
    "unassessed", "critical", "high", "medium", "low"
]
TestScenarioCategory: TypeAlias = Literal[
    "happy_path", "negative", "boundary", "validation", "permission",
    "state_transition", "integration", "error_handling", "data_persistence",
    "concurrency",
]
TestCaseType: TypeAlias = Literal[
    "happy_path", "negative", "boundary", "validation", "permission",
    "state_transition", "integration", "error_handling", "data_persistence",
    "concurrency", "api", "ui", "custom",
]
AutomationStatus: TypeAlias = Literal["manual", "candidate", "automated"]

class ScenarioCreate(BaseModel):
    scenario_key: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=2, max_length=300)
    objective: str = Field(default="", max_length=5000)
    risk: RiskLevel = "medium"
    priority: RiskLevel = "medium"
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=200)
    acceptance_criterion_ids: list[str] = Field(default_factory=list, max_length=500)
    test_condition_ids: list[str] = Field(default_factory=list, max_length=500)
    status: Literal["draft", "in_review", "approved", "archived"] = "draft"
    origin: Literal["manual", "ai_generated", "import"] = "manual"
    category: TestScenarioCategory = "happy_path"


class ScenarioPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    objective: str | None = Field(default=None, max_length=5000)
    risk: RiskLevel | None = None
    priority: RiskLevel | None = None
    requirement_version_ids: list[str] | None = Field(default=None, max_length=200)
    acceptance_criterion_ids: list[str] | None = Field(default=None, max_length=500)
    test_condition_ids: list[str] | None = Field(default=None, max_length=500)
    category: TestScenarioCategory | None = None


class TestStep(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    order: int = Field(ge=1)
    action_doc: dict[str, Any] = Field(default_factory=empty_doc)
    test_data: dict[str, Any] = Field(default_factory=dict)
    expected_doc: dict[str, Any] = Field(default_factory=empty_doc)

    @field_validator("action_doc", "expected_doc")
    @classmethod
    def validate_documents(cls, value):
        if value.get("type") != "doc" or not isinstance(value.get("content", []), list):
            raise ValueError("Tiptap JSON không hợp lệ")
        return value


class BddStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=200)
    keyword: Literal["Given", "When", "Then", "And", "But"]
    text: str = Field(min_length=1, max_length=2000)
    reusable_step_version_id: str | None = Field(default=None, max_length=200)


class BddScenario(BaseModel):
    feature: str = Field(min_length=2, max_length=300)
    scenario: str = Field(min_length=2, max_length=300)
    steps: list[BddStep] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_step_ids(self):
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("Định danh bước BDD không được trùng")
        return self


class TestRepositoryNodeCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=300)
    parent_id: str | None = Field(default=None, max_length=200)


class TestRepositoryNodePatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    parent_id: str | None = Field(default=None, max_length=200)


class ReusableStepCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=2, max_length=300)
    action_doc: dict[str, Any] = Field(default_factory=empty_doc)
    expected_doc: dict[str, Any] = Field(default_factory=empty_doc)


class ReusableStepPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    action_doc: dict[str, Any] | None = None
    expected_doc: dict[str, Any] | None = None


class EvidenceQuote(BaseModel):
    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=2, max_length=1000)


class TestCaseObligationEvidence(BaseModel):
    obligation_key: str = Field(min_length=1, max_length=200)
    evidence_quotes: list[EvidenceQuote] = Field(min_length=1, max_length=20)


class TestCaseCustomFieldCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=2, max_length=200)
    value_type: Literal["text", "number", "boolean", "date", "choice"]
    required: bool = False
    choices: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_choices(self):
        if self.value_type == "choice" and not self.choices:
            raise ValueError("Trường lựa chọn phải có ít nhất một giá trị")
        if self.value_type != "choice" and self.choices:
            raise ValueError("Chỉ trường lựa chọn mới được khai báo danh sách giá trị")
        if len(self.choices) != len(set(self.choices)):
            raise ValueError("Giá trị lựa chọn không được trùng")
        return self


class TestCaseCustomFieldPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    label: str | None = Field(default=None, min_length=2, max_length=200)
    required: bool | None = None
    status: Literal["ACTIVE", "INACTIVE"] | None = None

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value):
        if value is None:
            return value
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Tên trường phải có ít nhất 2 ký tự")
        return normalized

    @model_validator(mode="after")
    def require_update(self):
        fields = self.model_fields_set - {"expected_revision"}
        if not fields:
            raise ValueError("Cần có ít nhất một thay đổi")
        if any(getattr(self, name) is None for name in fields):
            raise ValueError("Không thể xóa giá trị cấu hình bằng null")
        return self


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
    type: TestCaseType = "happy_path"
    test_level: Literal["UNIT", "INTEGRATION", "SYSTEM", "ACCEPTANCE"] | None = None
    test_kind: Literal["functional", "performance", "security", "usability", "compatibility", "reliability", "accessibility"] | None = None
    expected_impact: Literal["unassessed", "low", "medium", "high", "critical"] = "unassessed"
    assessment_reason: str = Field(default="", max_length=2000)
    priority: TestCaseAssessmentLevel = "unassessed"
    risk: TestCaseAssessmentLevel = "unassessed"
    objective_doc: dict[str, Any] = Field(default_factory=empty_doc)
    preconditions_doc: dict[str, Any] = Field(default_factory=empty_doc)
    steps: list[TestStep] = Field(default_factory=list, max_length=500)
    test_data: dict[str, Any] = Field(default_factory=dict)
    expected_result_doc: dict[str, Any] = Field(default_factory=empty_doc)
    postconditions_doc: dict[str, Any] = Field(default_factory=empty_doc)
    tags: list[str] = Field(default_factory=list, max_length=100)
    required_skills: list[str] = Field(default_factory=list, max_length=50)
    custom_values: dict[str, Any] = Field(default_factory=dict, max_length=100)
    owner_id: str | None = Field(default=None, max_length=200)
    techniques: list[str] = Field(default_factory=list, max_length=50)
    automation_status: AutomationStatus = "manual"
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    data_set_version_ids: list[str] = Field(default_factory=list, max_length=100)
    requirement_version_ids: list[str] = Field(default_factory=list, max_length=200)
    acceptance_criterion_ids: list[str] = Field(default_factory=list, max_length=500)
    coverage_item_ids: list[str] = Field(default_factory=list, max_length=500)
    test_condition_ids: list[str] = Field(default_factory=list, max_length=500)
    scenario_id: str | None = None
    repository_node_id: str | None = Field(default=None, max_length=200)
    bdd: BddScenario | None = None
    origin: Literal["manual", "ai_generated", "clone", "import", "maintenance"] = "manual"
    source_evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    acceptance_criteria_snapshot_ids: list[str] | None = Field(default=None, max_length=500)
    coverage_obligations: list[str] = Field(default_factory=list, max_length=100)
    obligation_evidence: list[TestCaseObligationEvidence] = Field(default_factory=list, max_length=100)
    evidence_refs: list[str] = Field(default_factory=list, max_length=200)
    evidence_quotes: list[EvidenceQuote] = Field(default_factory=list, max_length=20)
    challenge_hypotheses: list[TestDesignChallengeInput] = Field(default_factory=list, max_length=5)
    suite_signature: str | None = Field(default=None, max_length=128)
    duplicate_reason: str | None = Field(default=None, min_length=2, max_length=2000)
    target_version_id: str | None = Field(default=None, min_length=1, max_length=200)
    version_reason: str | None = Field(default=None, min_length=2, max_length=2000)

    @field_validator(
        "preconditions_doc", "objective_doc", "expected_result_doc", "postconditions_doc"
    )
    @classmethod
    def validate_documents(cls, value):
        if value.get("type") != "doc" or not isinstance(value.get("content", []), list):
            raise ValueError("Tiptap JSON không hợp lệ")
        return value

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
        obligation_keys = [item.obligation_key for item in self.obligation_evidence]
        if len(obligation_keys) != len(set(obligation_keys)):
            raise ValueError("Dẫn chứng nghĩa vụ không được trùng")
        if not set(obligation_keys) <= set(self.coverage_obligations):
            raise ValueError("Dẫn chứng phải thuộc nghĩa vụ của ca kiểm thử")
        if self.origin == "ai_generated" and self.coverage_obligations and set(
            obligation_keys
        ) != set(self.coverage_obligations):
            raise ValueError("Mỗi nghĩa vụ AI phải có dẫn chứng riêng")
        case_quotes = {(item.evidence_ref, item.quote) for item in self.evidence_quotes}
        if any(
            (quote.evidence_ref, quote.quote) not in case_quotes
            for item in self.obligation_evidence
            for quote in item.evidence_quotes
        ):
            raise ValueError("Dẫn chứng nghĩa vụ không nằm trong trích dẫn của ca")
        return self

    @field_validator("required_skills")
    @classmethod
    def normalize_required_skills(cls, values):
        normalized = []
        seen = set()
        for value in values:
            item = " ".join(str(value).split())
            key = item.casefold()
            if item and key not in seen:
                normalized.append(item)
                seen.add(key)
        if any(len(value) > 120 for value in normalized):
            raise ValueError("Kỹ năng yêu cầu không được dài quá 120 ký tự")
        return normalized


class TestCaseDraftBatchComparisonInput(BaseModel):
    items: list[TestCaseDraftCreate] = Field(min_length=2, max_length=100)


class TestCaseDraftPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    type: TestCaseType | None = None
    test_level: Literal["UNIT", "INTEGRATION", "SYSTEM", "ACCEPTANCE"] | None = None
    test_kind: Literal["functional", "performance", "security", "usability", "compatibility", "reliability", "accessibility"] | None = None
    expected_impact: Literal["unassessed", "low", "medium", "high", "critical"] | None = None
    assessment_reason: str | None = Field(default=None, max_length=2000)
    priority: TestCaseAssessmentLevel | None = None
    risk: TestCaseAssessmentLevel | None = None
    objective_doc: dict[str, Any] | None = None
    preconditions_doc: dict[str, Any] | None = None
    steps: list[TestStep] | None = None
    test_data: dict[str, Any] | None = None
    expected_result_doc: dict[str, Any] | None = None
    postconditions_doc: dict[str, Any] | None = None
    tags: list[str] | None = None
    required_skills: list[str] | None = Field(default=None, max_length=50)
    custom_values: dict[str, Any] | None = Field(default=None, max_length=100)
    owner_id: str | None = Field(default=None, max_length=200)
    techniques: list[str] | None = None
    automation_status: AutomationStatus | None = None
    attachments: list[dict[str, Any]] | None = None
    data_set_version_ids: list[str] | None = None
    requirement_version_ids: list[str] | None = None
    acceptance_criterion_ids: list[str] | None = None
    coverage_item_ids: list[str] | None = None
    test_condition_ids: list[str] | None = None
    scenario_id: str | None = None
    repository_node_id: str | None = Field(default=None, max_length=200)
    bdd: BddScenario | None = None
    duplicate_reason: str | None = Field(default=None, min_length=2, max_length=2000)

    @field_validator(
        "preconditions_doc", "objective_doc", "expected_result_doc", "postconditions_doc"
    )
    @classmethod
    def validate_documents(cls, value):
        if value is not None and (
            value.get("type") != "doc" or not isinstance(value.get("content", []), list)
        ):
            raise ValueError("Tiptap JSON không hợp lệ")
        return value

    @field_validator("required_skills")
    @classmethod
    def normalize_required_skills(cls, values):
        if values is None:
            return values
        normalized = []
        seen = set()
        for value in values:
            item = " ".join(str(value).split())
            key = item.casefold()
            if item and key not in seen:
                normalized.append(item)
                seen.add(key)
        if any(len(value) > 120 for value in normalized):
            raise ValueError("Kỹ năng yêu cầu không được dài quá 120 ký tự")
        return normalized


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

    @model_validator(mode="after")
    def validate_secret_policy(self):
        sensitive_markers = ("password", "passwd", "token", "secret", "api_key", "private_key")
        unsafe_keys = [
            key
            for key in self.variables
            if any(marker in key.lower() for marker in sensitive_markers)
        ]
        if unsafe_keys:
            raise ValueError("Dữ liệu bí mật phải được khai báo bằng secret_refs")
        invalid_refs = [
            key for key, value in self.secret_refs.items() if not value.startswith("secret://")
        ]
        if invalid_refs:
            raise ValueError("Secret reference phải bắt đầu bằng secret://")
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


class RiskRankingGenerate(BaseModel):
    max_items: int | None = Field(default=None, ge=1, le=5000)


class RiskRankingPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    test_case_version_id: str = Field(min_length=1, max_length=200)
    included: bool
    reason: str = Field(min_length=2, max_length=2000)


class RiskRankingApproval(BaseModel):
    expected_revision: int = Field(ge=1)
    review_note: str = Field(default="", max_length=5000)


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
