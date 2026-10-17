from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.schemas.agent import EvidenceItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AutomationKind(str, Enum):
    ON_DEMAND = "ON_DEMAND"
    SOURCE_INGESTION = "SOURCE_INGESTION"
    CHANGE_SIMULATION = "CHANGE_SIMULATION"


class AutomationStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    AWAITING_HUMAN_DECISION = "AWAITING_HUMAN_DECISION"
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AutomationCheckpointPhase(str, Enum):
    QUEUED = "QUEUED"
    CONTEXT_LOADED = "CONTEXT_LOADED"
    GRAPH_COMPLETED = "GRAPH_COMPLETED"
    FINALIZED = "FINALIZED"


class AutomationRunRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=3, max_length=4000)
    intent: str = Field(default="", max_length=100)
    kind: AutomationKind = AutomationKind.ON_DEMAND
    target_artifact_ids: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=100)
    constraints: dict[str, Any] = Field(default_factory=dict)


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
    created_at: datetime = Field(default_factory=utc_now)


class SourceFact(BaseModel):
    source_fact_id: str = Field(default_factory=lambda: f"FACT-{uuid4().hex}")
    automation_run_id: str
    project_id: str
    artifact_type: str
    artifact_id: str
    artifact_version_id: str | None = None
    source: str
    authority: str
    quote: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class DerivationReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: f"DR-{uuid4().hex}")
    automation_run_id: str
    project_id: str
    agent_run_id: str
    source_fact_ids: list[str] = Field(default_factory=list)
    output_evidence_refs: list[str] = Field(default_factory=list)
    outcome: str
    created_at: datetime = Field(default_factory=utc_now)


class AutomationRun(BaseModel):
    automation_run_id: str = Field(default_factory=lambda: f"AUT-{uuid4().hex}")
    project_id: str
    requester_user_id: str
    requester_role: str
    requester_permissions: list[str] = Field(default_factory=list)
    kind: AutomationKind
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
