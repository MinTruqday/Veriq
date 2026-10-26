from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.schemas.contracts.common import (
    KnowledgeApprovalStatus,
    KnowledgeAuthority,
    KnowledgeSourceType,
    RequirementCandidateStatus,
    empty_doc,
)

class AcceptanceCriterionInput(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    content_doc: dict[str, Any] = Field(default_factory=empty_doc)
    status: Literal["draft", "approved", "obsolete"] = "draft"
    source_span: dict[str, Any] | None = None


class RequirementCreate(BaseModel):
    requirement_key: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=2, max_length=300)
    type: Literal[
        "functional",
        "non_functional",
        "business_rule",
        "api",
        "ui",
        "data",
        "permission",
        "integration",
        "constraint",
    ] = "functional"
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    risk: Literal["critical", "high", "medium", "low"] = "medium"
    content_doc: dict[str, Any] = Field(default_factory=empty_doc)
    acceptance_criteria: list[AcceptanceCriterionInput] = Field(
        default_factory=list, max_length=200
    )
    business_rules: list[str] = Field(default_factory=list, max_length=200)
    actors: list[str] = Field(default_factory=list, max_length=100)
    dependencies: list[str] = Field(default_factory=list, max_length=200)
    source_refs: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=100)
    owner_id: str | None = Field(default=None, max_length=200)
    details: dict[str, Any] = Field(default_factory=dict)
    section_states: dict[str, Literal["provided", "missing", "not_applicable"]] = Field(default_factory=dict)
    custom_values: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_section_states(self):
        for key, state in self.section_states.items():
            if key in type(self).model_fields and key not in {"details", "section_states"}:
                value = getattr(self, key)
            else:
                value = self.details
                for part in key.split("."):
                    value = value.get(part) if isinstance(value, dict) else None
            present = any(bool(item) for item in value.values()) if isinstance(value, dict) else bool(value)
            if state == "provided" and not present:
                raise ValueError(f"Section {key} is marked provided without content")
            if state in ("missing", "not_applicable") and present:
                raise ValueError(f"Section {key} conflicts with its content")
        return self


class RequirementDraftPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    requirement_key: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    type: str | None = None
    priority: str | None = None
    risk: str | None = None
    content_doc: dict[str, Any] | None = None
    acceptance_criteria: list[AcceptanceCriterionInput] | None = Field(default=None, max_length=200)
    business_rules: list[str] | None = Field(default=None, max_length=200)
    actors: list[str] | None = Field(default=None, max_length=100)
    dependencies: list[str] | None = Field(default=None, max_length=200)
    source_refs: list[dict[str, Any]] | None = Field(default=None, max_length=200)
    tags: list[str] | None = Field(default=None, max_length=100)
    owner_id: str | None = Field(default=None, max_length=200)
    details: dict[str, Any] | None = None
    section_states: dict[str, Literal["provided", "missing", "not_applicable"]] | None = None
    custom_values: dict[str, Any] | None = None


class RequirementCustomFieldCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=2, max_length=200)
    value_type: Literal["text", "number", "boolean", "date", "choice"]
    required: bool = False
    choices: list[str] = Field(default_factory=list, max_length=100)
    requirement_types: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_choices(self):
        if self.value_type == "choice" and not self.choices:
            raise ValueError("Choice field needs options")
        if self.value_type != "choice" and self.choices:
            raise ValueError("Only choice fields may define options")
        return self


class RequirementTemplateContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectives: str = Field(default="", max_length=10000)
    in_scope: str = Field(default="", max_length=10000)
    out_of_scope: str = Field(default="", max_length=10000)
    stakeholders: list[str] = Field(default_factory=list, max_length=200)
    actors_and_systems: list[str] = Field(default_factory=list, max_length=200)
    glossary: list[str] = Field(default_factory=list, max_length=500)
    assumptions: list[str] = Field(default_factory=list, max_length=200)
    constraints: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("stakeholders", "actors_and_systems", "glossary", "assumptions", "constraints", mode="before")
    @classmethod
    def normalize_lines(cls, value):
        if isinstance(value, str):
            value = value.splitlines()
        if not isinstance(value, list):
            raise ValueError("Template context list is invalid")
        return [str(item).strip() for item in value if str(item).strip()]


class RequirementTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    product_types: list[Literal["web", "mobile", "api", "desktop", "embedded", "other"]] = Field(min_length=1, max_length=6)
    context: RequirementTemplateContext = Field(default_factory=RequirementTemplateContext)
    requirements: list[RequirementCreate] = Field(default_factory=list, max_length=100)
    source_document_ids: list[str] = Field(default_factory=list, max_length=100)
    source_template_ids: list[str] = Field(default_factory=list, max_length=20)


class RequirementTemplateUpdate(RequirementTemplateCreate):
    expected_version: int = Field(ge=1)
    conflict_resolutions: list[str] = Field(default_factory=list, max_length=100)


class RequirementTemplateSynthesis(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    product_types: list[Literal["web", "mobile", "api", "desktop", "embedded", "other"]] = Field(min_length=1, max_length=6)
    source_document_ids: list[str] = Field(default_factory=list, max_length=100)
    source_template_ids: list[str] = Field(default_factory=list, max_length=20)
    instruction: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def require_source(self):
        if not self.source_document_ids and not self.source_template_ids:
            raise ValueError("At least one source is required")
        return self


class RequirementTemplatePublish(BaseModel):
    expected_version: int = Field(ge=1)
    public_template: RequirementTemplateCreate


class RequirementTemplateConsent(BaseModel):
    document_id: str = Field(min_length=1, max_length=200)
    approved: bool


class RequirementAIAnalysisInput(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    instruction: str = Field(default="", max_length=5000)


class RequirementAISuggestionApply(BaseModel):
    expected_revision: int = Field(ge=1)
    ai_result_id: str = Field(min_length=1, max_length=200)
    suggestion_id: str = Field(min_length=1, max_length=200)


class RequirementVersionCreate(RequirementCreate):
    change_reason: str = Field(min_length=2, max_length=2000)
    expected_current_version_id: str


class RequirementBaselineInput(BaseModel):
    expected_revision: int = Field(ge=1)
    review_note: str = Field(default="", max_length=2000)


class RequirementObsoleteInput(BaseModel):
    expected_current_version_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=2000)


class RequirementRestoreInput(BaseModel):
    expected_current_version_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=2000)


class ReviewTransitionInput(BaseModel):
    expected_revision: int = Field(ge=1)
    review_note: str = Field(default="", max_length=2000)


class RequirementCompareInput(BaseModel):
    from_version_id: str
    to_version_id: str


class RequirementDependencyInput(BaseModel):
    dependency_requirement_id: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(ge=1)


class RequirementSplitInput(BaseModel):
    expected_source_version_id: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=200)
    reason: str = Field(min_length=2, max_length=2000)
    drafts: list[RequirementCreate] = Field(min_length=2, max_length=20)


class RequirementMergeInput(BaseModel):
    source_requirement_ids: list[str] = Field(min_length=2, max_length=20)
    expected_source_version_ids: dict[str, str] = Field(min_length=2, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=200)
    reason: str = Field(min_length=2, max_length=2000)
    draft: RequirementCreate


class RequirementDuplicateCheckInput(BaseModel):
    requirement_ids: list[str] = Field(default_factory=list, max_length=500)
    threshold: float = Field(default=0.72, ge=0.3, le=1)
    limit: int = Field(default=100, ge=1, le=1000)


class ImportCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=300)
    format: Literal["pdf", "docx", "md", "txt", "csv", "xlsx", "openapi", "postman"]
    content: str | dict[str, Any] | list[Any]
    visibility: Literal["private", "project", "shared"] = "private"
    shared_with: list[str] = Field(default_factory=list, max_length=100)
    ai_enabled: bool = False
    ocr_language: str | None = Field(default=None, min_length=2, max_length=32)
    source_type: KnowledgeSourceType = "REFERENCE"
    supersedes_document_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_access(self):
        if self.visibility == "shared" and not self.shared_with:
            raise ValueError("Tài liệu chia sẻ phải có ít nhất một thành viên")
        if self.visibility != "shared" and self.shared_with:
            raise ValueError("Chỉ tài liệu chia sẻ mới có danh sách thành viên")
        return self


class RequirementExtractionInput(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)


class RequirementParseRetry(BaseModel):
    expected_revision: int = Field(ge=1)


class RequirementDocumentPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    source_type: KnowledgeSourceType | None = None
    authority: KnowledgeAuthority | None = None
    owner_id: str | None = Field(default=None, max_length=200)
    module: str | None = Field(default=None, max_length=200)
    component: str | None = Field(default=None, max_length=200)
    product_area: str | None = Field(default=None, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    external_source_id: str | None = Field(default=None, max_length=500)
    approval_status: KnowledgeApprovalStatus | None = None
    approved_by: str | None = Field(default=None, max_length=200)
    approved_at: datetime | None = None
    source_version: str | None = Field(default=None, max_length=100)
    effective_from: datetime | None = None
    tags: list[str] | None = Field(default=None, max_length=100)


class RequirementDocumentAccessPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    visibility: Literal["private", "project", "shared"]
    shared_with: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_access(self):
        if self.visibility == "shared" and not self.shared_with:
            raise ValueError("Tài liệu chia sẻ phải có ít nhất một thành viên")
        if self.visibility != "shared" and self.shared_with:
            raise ValueError("Chỉ tài liệu chia sẻ mới có danh sách thành viên")
        return self


class RequirementDocumentAIReadPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    ai_enabled: bool


class KnowledgeSourceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content: str = Field(min_length=1, max_length=2_000_000)
    source_type: KnowledgeSourceType = "REFERENCE"
    authority: KnowledgeAuthority = "PROJECT_REFERENCE"
    source_url: str | None = Field(default=None, max_length=2000)
    owner_id: str | None = Field(default=None, max_length=200)
    module: str | None = Field(default=None, max_length=200)
    component: str | None = Field(default=None, max_length=200)
    product_area: str | None = Field(default=None, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    external_source_id: str | None = Field(default=None, max_length=500)
    approval_status: KnowledgeApprovalStatus = KnowledgeApprovalStatus.DRAFT
    approved_by: str | None = Field(default=None, max_length=200)
    approved_at: datetime | None = None
    source_version: str = Field(default="1", min_length=1, max_length=100)
    effective_from: datetime | None = None
    tags: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_approval(self):
        if self.approval_status == KnowledgeApprovalStatus.APPROVED and (
            not self.approved_by or not self.approved_at
        ):
            raise ValueError("Nguồn đã phê duyệt phải có người và thời điểm phê duyệt")
        return self


class AttachmentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2000)
    item_id: str | None = Field(default=None, max_length=200)
    size: int = Field(default=0, ge=0)
    content_type: str = Field(default="application/octet-stream", max_length=200)
    artifact_type: str | None = Field(default=None, max_length=80)
    artifact_id: str | None = Field(default=None, max_length=200)


class AttachmentModeration(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class ReviewCommentCreate(BaseModel):
    artifact_type: str = Field(min_length=1, max_length=80)
    artifact_id: str = Field(min_length=1, max_length=200)
    body_doc: dict[str, Any] = Field(default_factory=empty_doc)
    anchor: dict[str, Any] | None = None
    parent_comment_id: str | None = None


class ReviewCommentAction(BaseModel):
    reason: str = Field(default="", max_length=2000)


class ReviewCommentPatch(BaseModel):
    body_doc: dict[str, Any]

    @field_validator("body_doc")
    @classmethod
    def validate_body(cls, value):
        if value.get("type") != "doc" or not isinstance(value.get("content", []), list):
            raise ValueError("Tiptap JSON không hợp lệ")
        return value


class ImportConfirm(BaseModel):
    selected_indexes: list[int] = Field(default_factory=list, max_length=2000)
    separate_indexes: list[int] = Field(default_factory=list, max_length=2000)
    separate_reasons: dict[int, str] = Field(default_factory=dict)
    accept_incomplete: bool = False
    expected_revision: int = Field(ge=1)


class RequirementImportResolution(BaseModel):
    expected_revision: int = Field(ge=1)
    target_requirement_id: str = Field(min_length=1, max_length=200)
    expected_target_version_id: str = Field(min_length=1, max_length=200)
    action: Literal["link_source", "create_version"]
    reason: str = Field(min_length=2, max_length=2000)


class APIArtifactReview(BaseModel):
    expected_revision: int = Field(ge=1)
    selected_indexes: list[int] = Field(default_factory=list, max_length=5000)
    review_note: str = Field(default="", max_length=2000)


class APIArtifactConfirm(BaseModel):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)


class APIArtifactArchive(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=2000)


class APIArtifactImpact(BaseModel):
    from_artifact_id: str = Field(min_length=1, max_length=200)
    to_artifact_id: str = Field(min_length=1, max_length=200)


class RequirementCandidateReview(RequirementCreate):
    candidate_id: str | None = Field(default=None, max_length=200)
    candidate_status: RequirementCandidateStatus = RequirementCandidateStatus.ACTIVE
    candidate_revision: int = Field(default=1, ge=1)
    candidate_relation: str | None = Field(default=None, max_length=80)
    parent_candidate_ids: list[str] = Field(default_factory=list, max_length=500)


class RequirementImportReview(BaseModel):
    expected_revision: int = Field(ge=1)
    preview: list[RequirementCandidateReview] = Field(min_length=1, max_length=500)
    review_note: str = Field(default="", max_length=2000)


class RequirementCandidateMergeInput(BaseModel):
    expected_revision: int = Field(ge=1)
    candidate_ids: list[str] = Field(min_length=2, max_length=500)
    merged: RequirementCreate
    reason: str = Field(default="", max_length=2000)


class RequirementCandidateSplitInput(BaseModel):
    expected_revision: int = Field(ge=1)
    drafts: list[RequirementCreate] = Field(min_length=2, max_length=100)
    reason: str = Field(default="", max_length=2000)


class RequirementCandidateRejectInput(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(default="", max_length=2000)
