from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.schemas.agent import AgentResult, AgentTask, EvidenceItem, VeriqRunState
from src.schemas.inference_requirements import TestabilityBlueprintCompilationOutput


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
    API_OPERATION_CONFIRMED = "API_OPERATION_CONFIRMED"
    REQUIREMENT_CHANGED = "REQUIREMENT_CHANGED"
    TEST_EXECUTION_RECORDED = "TEST_EXECUTION_RECORDED"
    DEFECT_RECORDED = "DEFECT_RECORDED"
    DEFECT_CHANGED = "DEFECT_CHANGED"
    WORK_ITEM_CHANGED = "WORK_ITEM_CHANGED"
    TEST_CASE_CHANGED = "TEST_CASE_CHANGED"
    TEST_CASE_APPROVED = "TEST_CASE_APPROVED"
    TEST_PLAN_CHANGED = "TEST_PLAN_CHANGED"
    TEST_PLAN_APPROVED = "TEST_PLAN_APPROVED"
    STATUS_REPORT_CREATED = "STATUS_REPORT_CREATED"
    TEST_COMPLETION_REPORT_CREATED = "TEST_COMPLETION_REPORT_CREATED"
    PERFORMANCE_CONFIGURATION_APPROVED = "PERFORMANCE_CONFIGURATION_APPROVED"
    RELEASE_CHANGED = "RELEASE_CHANGED"


class AutomationStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    AWAITING_INPUT = "AWAITING_INPUT"
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AutomationCheckpointPhase(str, Enum):
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


class AutomationFact(BaseModel):
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


class ExtractedAutomationFact(BaseModel):
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


class AutomationUncertainty(BaseModel):
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


class AutomationFactExtraction(BaseModel):
    facts: list[ExtractedAutomationFact] = Field(default_factory=list)
    uncertainties: list[AutomationUncertainty] = Field(default_factory=list)


class AutomationGraphSnapshot(BaseModel):
    completed_phase: AutomationCheckpointPhase
    run: VeriqRunState
    evidence: list[EvidenceItem] = Field(default_factory=list)
    degraded_flags: list[str] = Field(default_factory=list)
    target_artifact_ids: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    tasks: list[AgentTask] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    results: list[AgentResult] = Field(default_factory=list)
    source_facts: list[AutomationFact] = Field(default_factory=list)
    uncertainties: list[AutomationUncertainty] = Field(default_factory=list)
    automation_phases: list[str] = Field(default_factory=list)
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


class AutomationRunRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=3, max_length=4000)
    intent: str = Field(default="", max_length=100)
    intent_arguments: dict[str, Any] = Field(default_factory=dict, max_length=100)
    kind: AutomationKind = AutomationKind.ON_DEMAND
    target_artifact_ids: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=100)
    constraints: dict[str, Any] = Field(default_factory=dict)
    change_simulation: ChangeSimulationInput | None = None

    @model_validator(mode="after")
    def validate_change_simulation(self):
        if self.intent_arguments and not self.intent:
            raise ValueError("intent_arguments_require_intent")
        if self.kind == AutomationKind.CHANGE_SIMULATION:
            if self.change_simulation is None:
                raise ValueError("change_simulation_input_required")
            if self.change_simulation.base_requirement_version_id not in self.target_artifact_ids:
                raise ValueError("change_simulation_baseline_must_be_targeted")
            source_refs = {item.artifact_version_id or item.artifact_id for item in self.evidence}
            if self.change_simulation.base_requirement_version_id not in source_refs:
                raise ValueError("change_simulation_baseline_evidence_required")
        elif self.change_simulation is not None:
            raise ValueError("change_simulation_input_only_allowed_for_simulation")
        return self


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
    parent_automation_run_id: str | None = Field(default=None, max_length=200)
    target_artifact_ids: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=100)


class AutomationRetryRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class AutomationClarificationResponseRequest(BaseModel):
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


class AutomationCancelRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class AutomationCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: f"ACP-{uuid4().hex}")
    automation_run_id: str
    checkpoint_sequence: int = Field(default=0, ge=0, strict=True)
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
    input_artifact_refs: list[str] = Field(default_factory=list)
    input_artifact_version_ids: list[str] = Field(default_factory=list)
    output_evidence_refs: list[str] = Field(default_factory=list)
    output_artifact_version_ids: list[str] = Field(default_factory=list)
    tool_name: str | None = None
    verification_status: str
    reason_code: str | None = None


class BlueprintClaimLineage(BaseModel):
    claim_type: Literal["OBLIGATION", "CLARIFICATION"]
    claim_key: str = Field(min_length=1, max_length=160)
    source_fact_ids: list[str] = Field(min_length=1)
    source_quote_sha256: str = Field(min_length=64, max_length=64)


class BlueprintArtifactLineage(BaseModel):
    obligation_key: str = Field(min_length=1, max_length=160)
    source_fact_ids: list[str] = Field(min_length=1)
    artifact_type: Literal["requirement_version", "test_case", "test_case_version"]
    artifact_id: str = Field(min_length=1, max_length=200)


class DerivationReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: f"DR-{uuid4().hex}")
    automation_run_id: str
    project_id: str
    agent_run_id: str
    source_fact_ids: list[str] = Field(default_factory=list)
    transformation_steps: list[str] = Field(default_factory=list)
    steps: list[DerivationStep] = Field(default_factory=list)
    output_evidence_refs: list[str] = Field(default_factory=list)
    testability_blueprint: TestabilityBlueprintCompilationOutput | None = None
    blueprint_claim_lineage: list[BlueprintClaimLineage] = Field(default_factory=list)
    blueprint_artifact_lineage: list[BlueprintArtifactLineage] = Field(default_factory=list)
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    outcome: str
    created_at: datetime = Field(default_factory=utc_now)


class BlueprintSourceRevision(BaseModel):
    artifact_type: str = Field(min_length=1, max_length=100)
    artifact_id: str = Field(min_length=1, max_length=200)
    artifact_version_id: str = Field(min_length=1, max_length=200)
    source_fact_ids: list[str] = Field(min_length=1)
    quote_sha256: list[str] = Field(min_length=1)


class ProjectTestabilityBlueprint(BaseModel):
    """Immutable, project-scoped history of source-grounded blueprint compilations."""

    blueprint_id: str = Field(default_factory=lambda: f"PTB-{uuid4().hex}")
    project_id: str = Field(min_length=1, max_length=200)
    version: int = Field(ge=1)
    automation_run_ids: list[str] = Field(min_length=1)
    source_fact_ids: list[str] = Field(min_length=1)
    source_revisions: list[BlueprintSourceRevision] = Field(min_length=1)
    source_digest: str = Field(min_length=64, max_length=64)
    compilation: TestabilityBlueprintCompilationOutput
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_revision_references(self):
        references = {revision.artifact_version_id for revision in self.source_revisions}
        if not set(self.compilation.evidence_refs).issubset(references):
            raise ValueError("blueprint_evidence_must_resolve_to_source_revision")
        if not set(self.source_fact_ids).issuperset(
            fact_id for revision in self.source_revisions for fact_id in revision.source_fact_ids
        ):
            raise ValueError("blueprint_source_fact_reference_invalid")
        return self


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
    intent_arguments: dict[str, Any] = Field(default_factory=dict, max_length=100)
    target_artifact_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    change_simulation: ChangeSimulationInput | None = None
    status: AutomationStatus = AutomationStatus.QUEUED
    agent_run_id: str | None = None
    trace_id: str | None = None
    result: dict[str, Any] | None = None
    error_code: str | None = None
    automatic_retry_count: int = Field(default=0, ge=0, strict=True)
    revision: int = 1
    checkpoint_sequence: int = Field(default=0, ge=0, strict=True, exclude=True)
    worker_lease_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AutomationEventAcceptedResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    runs: list[AutomationRun] = Field(min_length=1)


class AutomationEventSuppressedResponse(BaseModel):
    status: Literal["suppressed"] = "suppressed"
    reason_code: Literal["AUTOMATION_TRIGGER_DISABLED"]
    runs: list[AutomationRun] = Field(default_factory=list, max_length=0)


AutomationEventResponse = AutomationEventAcceptedResponse | AutomationEventSuppressedResponse


class AutomationWorkflowRun(BaseModel):
    automation_run_id: str
    parent_automation_run_id: str | None = None
    trigger: AutomationTrigger | None = None
    status: AutomationStatus
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class AutomationWorkflowSnapshot(BaseModel):
    root_automation_run_id: str
    status: AutomationStatus
    terminal: bool
    succeeded: bool
    truncated: bool = False
    run_count: int = Field(ge=1)
    active_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    runs: list[AutomationWorkflowRun]


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
