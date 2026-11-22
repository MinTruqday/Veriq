from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.schemas.agent import AgentResult, AgentTask, EvidenceItem, VeriqRunState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AIRunKind(str, Enum):
    ON_DEMAND = "ON_DEMAND"
    EVENT = "EVENT"
    SOURCE_INGESTION = "SOURCE_INGESTION"
    CHANGE_SIMULATION = "CHANGE_SIMULATION"


class AIRunTrigger(str, Enum):
    MANUAL = "MANUAL"
    DOCUMENT_INGESTED = "DOCUMENT_INGESTED"
    API_OPERATION_CONFIRMED = "API_OPERATION_CONFIRMED"
    REQUIREMENT_CHANGED = "REQUIREMENT_CHANGED"
    TEST_EXECUTION_RECORDED = "TEST_EXECUTION_RECORDED"
    DEFECT_RECORDED = "DEFECT_RECORDED"
    DEFECT_CHANGED = "DEFECT_CHANGED"
    TEST_CASE_CHANGED = "TEST_CASE_CHANGED"
    TEST_CASE_APPROVED = "TEST_CASE_APPROVED"
    TEST_PLAN_CHANGED = "TEST_PLAN_CHANGED"
    TEST_PLAN_APPROVED = "TEST_PLAN_APPROVED"
    STATUS_REPORT_CREATED = "STATUS_REPORT_CREATED"
    TEST_COMPLETION_REPORT_CREATED = "TEST_COMPLETION_REPORT_CREATED"
    RELEASE_CHANGED = "RELEASE_CHANGED"


class AIRunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    AWAITING_INPUT = "AWAITING_INPUT"
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AIRunPhase(str, Enum):
    QUEUED = "QUEUED"
    WORKER_STARTED = "WORKER_STARTED"
    OBSERVED = "OBSERVED"
    FACTS_EXTRACTED = "FACTS_EXTRACTED"
    UNCERTAINTY_ASSESSED = "UNCERTAINTY_ASSESSED"
    PLAN_CREATED = "PLAN_CREATED"
    ACTION_STARTED = "ACTION_STARTED"
    ACTIONS_EXECUTED = "ACTIONS_EXECUTED"
    ACTIONS_VERIFIED = "ACTIONS_VERIFIED"
    GRAPH_COMPLETED = "GRAPH_COMPLETED"
    FINALIZED = "FINALIZED"


class AgentFact(BaseModel):
    """Verified runtime fact; relationship metadata is copied from source evidence."""

    artifact_type: str
    artifact_id: str
    artifact_version_id: str | None = None
    source: str
    authority: str
    relationship_path: list[str] = Field(default_factory=list, max_length=50)
    quote: str = Field(min_length=1)
    fact_kind: str = "source_evidence"
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)
    source_chunk_id: str | None = None
    source_chunk_index: int | None = Field(default=None, ge=0, strict=True)
    source_chunk_type: str | None = None
    source_page_numbers: list[int] = Field(default_factory=list)
    source_spans: list[dict[str, Any]] = Field(default_factory=list)
    source_hash: str | None = None
    source_offset_basis: Literal[
        "CANONICAL_TEXT", "RETRIEVED_CHUNK", "SOURCE_CITATION", "UNKNOWN"
    ] = "UNKNOWN"


class ExtractedAgentFact(BaseModel):
    """Model-claimed fact fields; source lineage is deliberately not model-authored."""

    model_config = ConfigDict(extra="forbid")

    artifact_type: str
    artifact_id: str
    artifact_version_id: str | None = None
    source: str
    authority: str
    quote: str = Field(min_length=1)
    fact_kind: str = "source_evidence"
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)


class AgentUncertainty(BaseModel):
    code: str = Field(min_length=1)
    question: str = ""
    reason: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    blocking: bool = True
    response_allowed: bool = True
    resolution_status: Literal["OPEN", "USER_ANSWERED"] = "OPEN"
    answer: str | None = Field(default=None, max_length=4000)
    answered_by: str | None = Field(default=None, max_length=200)
    answered_at: datetime | None = None


class AgentFactExtraction(BaseModel):
    facts: list[ExtractedAgentFact] = Field(default_factory=list)
    uncertainties: list[AgentUncertainty] = Field(default_factory=list)


class AIRunStateSnapshot(BaseModel):
    completed_phase: AIRunPhase
    run: VeriqRunState
    evidence: list[EvidenceItem] = Field(default_factory=list)
    degraded_flags: list[str] = Field(default_factory=list)
    target_artifact_ids: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    tasks: list[AgentTask] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    results: list[AgentResult] = Field(default_factory=list)
    source_facts: list[AgentFact] = Field(default_factory=list)
    uncertainties: list[AgentUncertainty] = Field(default_factory=list)
    completed_phases: list[str] = Field(default_factory=list)
    automatic: bool = False
    source_event_verified: bool = False
    planning_round: int = 0
    worker_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="before")
    @classmethod
    def bind_resumable_task_identity(cls, value):
        if not isinstance(value, dict):
            return value
        run = value.get("run")
        run_values = (
            run
            if isinstance(run, dict)
            else (run.model_dump(mode="python") if isinstance(run, VeriqRunState) else {})
        )
        tasks = value.get("tasks")
        if not isinstance(tasks, list):
            return value
        bound_tasks = []
        for item in tasks:
            if not isinstance(item, dict):
                bound_tasks.append(item)
                continue
            task = dict(item)
            for field in ("run_id", "project_id", "user_id"):
                if run_values.get(field):
                    task[field] = run_values[field]
            bound_tasks.append(task)
        return {**value, "tasks": bound_tasks}


class ChangeSimulationInput(BaseModel):
    """Uncommitted proposed source text compared with one authoritative baseline."""

    base_requirement_version_id: str = Field(min_length=1, max_length=200)
    proposed_source_text: str = Field(min_length=1, max_length=100_000)

    @field_validator("base_requirement_version_id", "proposed_source_text")
    @classmethod
    def reject_blank_simulation_input(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("change_simulation_input_must_not_be_blank")
        return normalized




class AIRunRetryRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class AIRunClarificationResponseRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    uncertainty_code: str = Field(min_length=1, max_length=160)
    answer: str = Field(min_length=1, max_length=4000)

    @field_validator("uncertainty_code", "answer")
    @classmethod
    def reject_blank_clarification_values(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("clarification_value_must_not_be_blank")
        return normalized


class AIRunCancelRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class AIRunCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: f"ACP-{uuid4().hex}")
    ai_run_id: str
    checkpoint_sequence: int = Field(default=0, ge=0, strict=True)
    phase: AIRunPhase
    status: AIRunStatus
    detail: dict[str, Any] = Field(default_factory=dict)
    state_snapshot: AIRunStateSnapshot | None = None
    created_at: datetime = Field(default_factory=utc_now)


class SourceFact(BaseModel):
    source_fact_id: str = Field(default_factory=lambda: f"FACT-{uuid4().hex}")
    ai_run_id: str
    project_id: str
    artifact_type: str
    artifact_id: str
    artifact_version_id: str | None = None
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)
    source: str
    authority: str
    relationship_path: list[str] = Field(default_factory=list, max_length=50)
    quote: str = Field(min_length=1)
    fact_kind: str = "source_evidence"
    quote_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    source_chunk_id: str | None = None
    source_chunk_index: int | None = Field(default=None, ge=0, strict=True)
    source_chunk_type: str | None = None
    source_page_numbers: list[int] = Field(default_factory=list)
    source_spans: list[dict[str, Any]] = Field(default_factory=list)
    source_hash: str | None = None
    source_offset_basis: Literal[
        "CANONICAL_TEXT", "RETRIEVED_CHUNK", "SOURCE_CITATION", "UNKNOWN"
    ] = "UNKNOWN"
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_source_span(self):
        if (self.source_start is None) != (self.source_end is None):
            raise ValueError("Source span needs both boundaries")
        if self.source_start is not None and self.source_end <= self.source_start:
            raise ValueError("Source span is empty or reversed")
        return self


class DerivationStep(BaseModel):
    name: str
    source_fact_ids: list[str] = Field(default_factory=list)
    control_event_refs: list[str] = Field(default_factory=list)
    input_artifact_refs: list[str] = Field(default_factory=list)
    input_artifact_version_ids: list[str] = Field(default_factory=list)
    output_evidence_refs: list[str] = Field(default_factory=list)
    output_artifact_version_ids: list[str] = Field(default_factory=list)
    tool_name: str | None = None
    verification_status: str
    reason_code: str | None = None


class DerivationReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: f"DR-{uuid4().hex}")
    ai_run_id: str
    project_id: str
    source_fact_ids: list[str] = Field(default_factory=list)
    transformation_steps: list[str] = Field(default_factory=list)
    steps: list[DerivationStep] = Field(default_factory=list)
    output_evidence_refs: list[str] = Field(default_factory=list)
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    outcome: str
    created_at: datetime = Field(default_factory=utc_now)



class AIRun(BaseModel):
    ai_run_id: str = Field(default_factory=lambda: f"RUN-{uuid4().hex}")
    project_id: str
    requester_user_id: str
    requester_role: str
    requester_permissions: list[str] = Field(default_factory=list)
    execution_user_id: str | None = None
    execution_role: str | None = None
    execution_permissions: list[str] = Field(default_factory=list)
    kind: AIRunKind
    trigger: AIRunTrigger | None = None
    definition_id: str | None = None
    source_event_id: str | None = None
    source_event_verified: bool = False
    objective: str
    intent: str = ""
    intent_arguments: dict[str, Any] = Field(default_factory=dict, max_length=100)
    target_artifact_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    change_simulation: ChangeSimulationInput | None = None
    status: AIRunStatus = AIRunStatus.QUEUED
    trace_id: str | None = None
    result: dict[str, Any] | None = None
    error_code: str | None = None
    automatic_retry_count: int = Field(default=0, ge=0, strict=True)
    revision: int = 1
    checkpoint_sequence: int = Field(default=0, ge=0, strict=True, exclude=True)
    worker_lease_expires_at: datetime | None = None
    queue_dispatch_lease_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AIRunAcceptedResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    runs: list[AIRun] = Field(min_length=1)
