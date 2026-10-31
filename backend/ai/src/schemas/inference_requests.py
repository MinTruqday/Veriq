from enum import Enum
from typing import Annotated, Any, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TESTING_AUTOMATION_MAX_EVIDENCE_ITEMS = 100


class TestingAutomationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"

class TestingAutomationDegradedMode(str, Enum):
    OUTPUT = "DEGRADED_OUTPUT"
    PROVIDER = "DEGRADED_AI"

class CrossDocumentExpansionRequest(BaseModel):
    question: str = Field(
        min_length=1, max_length=10000, description="Question to decompose across documents"
    )
    document_ids: List[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        min_length=2, max_length=100, description="Ordered document identifiers to retrieve"
    )

class KnowledgeChunkSafetyRequest(BaseModel):
    texts: List[Annotated[str, Field(min_length=1, max_length=4000)]] = Field(
        min_length=1, max_length=500, description="Retrieved chunks to assess for safety"
    )

class KnowledgeDocumentSummaryRequest(BaseModel):
    text: str = Field(
        min_length=1, max_length=15000, description="Document content to summarize for knowledge retrieval"
    )
    output_language: str | None = Field(default=None, min_length=2, max_length=80)


class VerifiedSourceFactCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_fact_id: str | None = Field(default=None, min_length=1, max_length=200)
    fact_kind: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=4000)
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)
    source_offset_basis: Literal[
        "CANONICAL_TEXT", "RETRIEVED_CHUNK", "SOURCE_CITATION", "UNKNOWN"
    ] = "UNKNOWN"

    @model_validator(mode="after")
    def validate_source_span(self):
        if (self.source_start is None) != (self.source_end is None):
            raise ValueError("verified_fact_span_requires_both_offsets")
        if self.source_start is not None and self.source_end <= self.source_start:
            raise ValueError("verified_fact_span_invalid")
        return self


class TestingEvidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    artifact_type: str = Field(min_length=1, max_length=100)
    artifact_id: str | None = Field(default=None, min_length=1, max_length=200)
    artifact_version_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_version: str | None = Field(default=None, max_length=100)
    authority: str | None = Field(default=None, min_length=1, max_length=100)
    relationship_paths: list[list[str]] = Field(default_factory=list, max_length=100)
    verified_facts: list[VerifiedSourceFactCitation] = Field(default_factory=list, max_length=500)
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("relationship_paths")
    @classmethod
    def validate_relationship_paths(cls, values):
        if any(
            not path
            or len(path) > 50
            or any(
                not isinstance(scope_id, str) or not scope_id or len(scope_id) > 200
                for scope_id in path
            )
            for path in values
        ):
            raise ValueError("testing_evidence_relationship_path_invalid")
        return values

    @model_validator(mode="after")
    def require_identifier(self):
        if not self.artifact_id and not self.artifact_version_id:
            raise ValueError("testing_evidence_identifier_required")
        return self

class TestingAutomationRequest(BaseModel):
    capability: str = Field(min_length=1, max_length=100, description="Testing capability to perform")
    project_id: str = Field(
        min_length=1, max_length=128, description="Project identifier that bounds the operation"
    )
    instruction: str = Field(
        default="", max_length=5000, description="Additional user business instruction"
    )
    output_language: str | None = Field(
        default=None,
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
        description="Trusted user or project locale for generated natural-language fields",
    )
    evidence: List[TestingEvidence] = Field(
        min_length=1,
        max_length=TESTING_AUTOMATION_MAX_EVIDENCE_ITEMS,
        description="Artifact evidence already bounded to the project",
    )

    @model_validator(mode="after")
    def require_registered_capability(self):
        from src.schemas.inference import output_schema

        output_schema(self.capability)
        return self

class TestingAutomationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: str = Field(description="Executed testing capability")
    suggestions: List[dict[str, Any]] = Field(
        default_factory=list,
        max_length=100,
        description="Proposals that remain pending review",
    )
    new_test_candidates: List[dict[str, Any]] = Field(
        default_factory=list,
        max_length=100,
        description="New test case proposals that remain pending review",
    )
    findings: List[dict[str, Any]] = Field(
        default_factory=list,
        max_length=100,
        description="Analysis findings pending acknowledgement",
    )
    obligations: List[dict[str, Any]] = Field(
        default_factory=list,
        max_length=300,
        description="Source-grounded testability obligations produced by the compiler capability",
    )
    clarifications: List[dict[str, Any]] = Field(
        default_factory=list,
        max_length=100,
        description="Evidence-grounded clarification questions produced by AI capabilities",
    )
    readiness: str | None = None
    conflicts: List[dict[str, Any]] = Field(default_factory=list, max_length=100)
    context: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(
        default_factory=list, max_length=200, description="Evidence identifiers supporting the result"
    )
    confidence: float = Field(ge=0, le=1, description="Model confidence for reference")
    warnings: List[str] = Field(
        default_factory=list, max_length=50, description="Evidence limitation and conflict warnings"
    )
    status: TestingAutomationStatus = Field(
        default=TestingAutomationStatus.SUCCESS, description="AI capability operating status"
    )
    degraded_mode: TestingAutomationDegradedMode | None = Field(
        default=None, description="Fallback mode when the provider or retrieval is unavailable"
    )
    provider: str = Field(min_length=1, max_length=100, description="Provider that produced the result")
    model: dict[str, Any] = Field(
        default_factory=dict, description="Model prompt and tool schema version metadata"
    )
    prompt_version: str = Field(min_length=1, max_length=100, description="Prompt version")
    tool_schema_version: str = Field(
        min_length=1, max_length=100, description="Output schema version"
    )
    retrieval_version: str = Field(
        min_length=1, max_length=100, description="Evidence retrieval version"
    )
    created_at: str = Field(min_length=1, max_length=100, description="Result creation time")
    reason_codes: List[str] = Field(
        default_factory=list,
        max_length=100,
        description="Auditable reason codes without hidden reasoning",
    )
    workflow: dict[str, Any] = Field(
        default_factory=dict, description="Auditable observe reason act observe workflow state"
    )
    answer: str = Field(
        default="", max_length=20000, description="Evidence grounded answer for project questions"
    )

