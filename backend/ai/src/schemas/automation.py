from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from src.schemas.agent import AgentResult, EvidenceItem, PlannedTask, VeriqRunState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AutomationKind(str, Enum):
    ON_DEMAND = "ON_DEMAND"
    EVENT = "EVENT"
    SOURCE_INGESTION = "SOURCE_INGESTION"
    CHANGE_SIMULATION = "CHANGE_SIMULATION"


class AutomationTrigger(str, Enum):
    MANUAL = "MANUAL"
    DOCUMENT_INGESTED = "DOCUMENT_INGESTED"
    REQUIREMENT_CHANGED = "REQUIREMENT_CHANGED"
    TEST_EXECUTION_RECORDED = "TEST_EXECUTION_RECORDED"
    DEFECT_RECORDED = "DEFECT_RECORDED"
    WORK_ITEM_CHANGED = "WORK_ITEM_CHANGED"
    TEST_CASE_CHANGED = "TEST_CASE_CHANGED"
    TEST_CASE_APPROVED = "TEST_CASE_APPROVED"
    TEST_PLAN_CHANGED = "TEST_PLAN_CHANGED"
    TEST_PLAN_APPROVED = "TEST_PLAN_APPROVED"
    RELEASE_CHANGED = "RELEASE_CHANGED"


class AutomationStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AutomationCheckpointPhase(str, Enum):
    QUEUED = "QUEUED"
    OBSERVED = "OBSERVED"
    FACTS_EXTRACTED = "FACTS_EXTRACTED"
    UNCERTAINTY_ASSESSED = "UNCERTAINTY_ASSESSED"
    PLAN_CREATED = "PLAN_CREATED"
    ACTION_STARTED = "ACTION_STARTED"
    ACTIONS_EXECUTED = "ACTIONS_EXECUTED"
    ACTIONS_VERIFIED = "ACTIONS_VERIFIED"
    GRAPH_COMPLETED = "GRAPH_COMPLETED"
    FINALIZED = "FINALIZED"


class AutomationFact(BaseModel):
    artifact_type: str
    artifact_id: str
    artifact_version_id: str | None = None
    source: str
    authority: str
    quote: str = Field(min_length=1)
    fact_kind: str = "source_evidence"
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)


class AutomationUncertainty(BaseModel):
    code: str = Field(min_length=1)
    question: str = ""
    reason: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    blocking: bool = True


class AutomationFactExtraction(BaseModel):
    facts: list[AutomationFact] = Field(default_factory=list)
    uncertainties: list[AutomationUncertainty] = Field(default_factory=list)


class AutomationGraphSnapshot(BaseModel):
    completed_phase: AutomationCheckpointPhase
    run: VeriqRunState
    evidence: list[EvidenceItem] = Field(default_factory=list)
    degraded_flags: list[str] = Field(default_factory=list)
    target_artifact_ids: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    tasks: list[PlannedTask] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    results: list[AgentResult] = Field(default_factory=list)
    source_facts: list[AutomationFact] = Field(default_factory=list)
    uncertainties: list[AutomationUncertainty] = Field(default_factory=list)
    automation_phases: list[str] = Field(default_factory=list)
    automatic: bool = False
    source_event_verified: bool = False
    planning_round: int = 0


class AutomationRunRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=3, max_length=4000)
    intent: str = Field(default="", max_length=100)
    kind: AutomationKind = AutomationKind.ON_DEMAND
    target_artifact_ids: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=100)
    constraints: dict[str, Any] = Field(default_factory=dict)


class AutomationDefinitionRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=3, max_length=160)
    trigger: AutomationTrigger
    objective: str = Field(min_length=3, max_length=4000)
    intent: str = Field(default="", max_length=100)
    enabled: bool = True


class AutomationDefinitionPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=3, max_length=160)
    objective: str | None = Field(default=None, min_length=3, max_length=4000)
    intent: str | None = Field(default=None, max_length=100)
    enabled: bool | None = None


class AutomationEventRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=200)
    project_id: str = Field(min_length=1, max_length=200)
    requester_user_id: str = Field(min_length=1, max_length=200)
    trigger: AutomationTrigger
    target_artifact_ids: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=100)


class AutomationRetryRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class AutomationCancelRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class AutomationCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: f"ACP-{uuid4().hex}")
    automation_run_id: str
    phase: AutomationCheckpointPhase
    status: AutomationStatus
    detail: dict[str, Any] = Field(default_factory=dict)
    state_snapshot: AutomationGraphSnapshot | None = None
    created_at: datetime = Field(default_factory=utc_now)


class SourceFact(BaseModel):
    source_fact_id: str = Field(default_factory=lambda: f"FACT-{uuid4().hex}")
    automation_run_id: str
    project_id: str
    artifact_type: str
    artifact_id: str
    artifact_version_id: str | None = None
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)
    source: str
    authority: str
    quote: str = Field(min_length=1)
    fact_kind: str = "source_evidence"
    quote_sha256: str | None = Field(default=None, min_length=64, max_length=64)
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
    output_evidence_refs: list[str] = Field(default_factory=list)
    tool_name: str | None = None
    verification_status: str
    reason_code: str | None = None


class DerivationReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: f"DR-{uuid4().hex}")
    automation_run_id: str
    project_id: str
    agent_run_id: str
    source_fact_ids: list[str] = Field(default_factory=list)
    transformation_steps: list[str] = Field(default_factory=list)
    steps: list[DerivationStep] = Field(default_factory=list)
    output_evidence_refs: list[str] = Field(default_factory=list)
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    outcome: str
    created_at: datetime = Field(default_factory=utc_now)


class AutomationRun(BaseModel):
    automation_run_id: str = Field(default_factory=lambda: f"AUT-{uuid4().hex}")
    project_id: str
    requester_user_id: str
    requester_role: str
    requester_permissions: list[str] = Field(default_factory=list)
    execution_user_id: str | None = None
    execution_role: str | None = None
    execution_permissions: list[str] = Field(default_factory=list)
    kind: AutomationKind
    trigger: AutomationTrigger | None = None
    definition_id: str | None = None
    source_event_id: str | None = None
    source_event_verified: bool = False
    objective: str
    intent: str = ""
    target_artifact_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    status: AutomationStatus = AutomationStatus.QUEUED
    agent_run_id: str | None = None
    trace_id: str | None = None
    result: dict[str, Any] | None = None
    error_code: str | None = None
    revision: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AutomationDefinition(BaseModel):
    definition_id: str = Field(default_factory=lambda: f"ADF-{uuid4().hex}")
    project_id: str
    owner_user_id: str
    owner_role: str
    owner_permissions: list[str] = Field(default_factory=list)
    name: str
    trigger: AutomationTrigger
    objective: str
    intent: str = ""
    enabled: bool = True
    revision: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
