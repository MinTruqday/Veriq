from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

CapabilityDomain = Literal["requirement", "test_design", "analysis", "execution", "reporting"]


class AgentTaskStatus(str, Enum):
    COMPLETED = "COMPLETED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"
    LIMIT_REACHED = "LIMIT_REACHED"


class AgentRunStatus(str, Enum):
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ToolExecutionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DENIED = "DENIED"
    NOT_REQUIRED = "NOT_REQUIRED"


def utc_now():
    return datetime.now(timezone.utc)


class EvidenceRelationship(BaseModel):
    model_config = {"extra": "forbid"}

    relationship_id: str = Field(min_length=1, max_length=200)
    relationship_type: Literal["BLOCKS", "RELATES_TO"]
    project_id: str = Field(min_length=1, max_length=200)
    source_artifact_id: str = Field(min_length=1, max_length=200)
    target_artifact_id: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_endpoints(self):
        if self.source_artifact_id == self.target_artifact_id:
            raise ValueError("evidence_relationship_endpoints_must_differ")
        return self


class EvidenceItem(BaseModel):
    artifact_type: str
    artifact_id: str
    artifact_version_id: str | None = None
    source: Literal["database", "document", "vector", "graph", "memory", "tool", "user"]
    authority: str
    score: float = Field(default=1, ge=0, le=1)
    text: str = ""
    relationship_path: list[str] = Field(default_factory=list)
    relationship: EvidenceRelationship | None = None
    project_id: str
    artifact_revision: int | None = Field(default=None, ge=1, strict=True)
    artifact_status: str | None = Field(default=None, max_length=100)
    chunk_id: str | None = None
    chunk_index: int | None = None
    chunk_type: str | None = None
    page_numbers: list[int] = Field(default_factory=list)
    source_spans: list[dict[str, Any]] = Field(default_factory=list)
    source_hash: str | None = None

    @model_validator(mode="after")
    def validate_relationship_scope(self):
        if self.relationship is not None and (
            self.artifact_type != "work_item"
            or self.relationship.project_id != self.project_id
            or self.artifact_id
            not in {
                self.relationship.source_artifact_id,
                self.relationship.target_artifact_id,
            }
        ):
            raise ValueError("evidence_relationship_scope_invalid")
        return self


class EvidencePackage(BaseModel):
    project_id: str
    query: str
    items: list[EvidenceItem] = Field(default_factory=list)
    degraded_flags: list[str] = Field(default_factory=list)


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    task_id: str = Field(default_factory=lambda: f"TASK-{uuid4().hex}")
    run_id: str
    project_id: str
    user_id: str = ""
    domain: CapabilityDomain
    objective: str
    evidence_refs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCall] = Field(default_factory=list)


class PlannedTask(BaseModel):
    domain: CapabilityDomain
    objective: str
    evidence_refs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCall] = Field(default_factory=list)


class AgentResult(BaseModel):
    task_id: str
    status: AgentTaskStatus
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    proposals: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AgentPlan(BaseModel):
    intent: str
    success_criteria: list[str] = Field(default_factory=list)
    tasks: list[PlannedTask] = Field(default_factory=list)


class AgentProposal(BaseModel):
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    success_criteria_met: list[str] = Field(default_factory=list)
    change_simulation_report: dict[str, Any] | None = None


class VeriqRunState(BaseModel):
    run_id: str = Field(default_factory=lambda: f"RUN-{uuid4().hex}")
    project_id: str
    user_id: str
    role: str
    source_event_id: str | None = None
    permissions: list[str] = Field(default_factory=list)
    objective: str
    intent: str = ""
    intent_arguments: dict[str, Any] = Field(default_factory=dict, max_length=100)
    execution_plan: list[dict[str, Any]] = Field(default_factory=list)
    active_task: dict[str, Any] | None = None
    completed_tasks: list[dict[str, Any]] = Field(default_factory=list)
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    proposal: dict[str, Any] | None = None
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    current_step: int = 0
    status: AgentRunStatus = AgentRunStatus.PLANNING
    error_code: str | None = None
    revision: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentRunRequest(BaseModel):
    project_id: str
    objective: str = Field(min_length=3, max_length=4000)
    intent: str = Field(default="", max_length=100)
    target_artifact_ids: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=100)
    constraints: dict[str, Any] = Field(default_factory=dict)


class TestingSkillInput(BaseModel):
    project_id: str = Field(description="Testing project identifier")
    instruction: str = Field(default="", description="Runtime instruction for the current request")


class ToolVerification(BaseModel):
    path: str
    identifier: str
    expected: dict[str, Any]


class ToolAccess(BaseModel):
    name: str
    domains: set[CapabilityDomain]
    owner_domain: CapabilityDomain | None = None
    action: Literal["READ", "PROPOSE", "MUTATE"]
    permission: str
    verification: ToolVerification | None = None


class ToolDecision(BaseModel):
    allowed: bool
    reason_code: str
    access: ToolAccess | None = None
