from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TestingJobEvent(str, Enum):
    DOCUMENT_PARSE = "document.parse.requested"
    REQUIREMENT_EXTRACT = "requirement.extract.requested"
    REQUIREMENT_SEMANTIC_DIFF = "requirement.semantic_diff.requested"
    TEST_GENERATE = "test.generate.requested"
    DUPLICATE_SCAN = "duplicate.scan.requested"
    IMPACT_ANALYSIS = "impact.analysis.requested"
    KNOWLEDGE_INDEX = "knowledge.index.requested"
    AUTOMATION_NEWMAN = "automation.newman.requested"
    AUTOMATION_PLAYWRIGHT = "automation.playwright.requested"


class WorkerJobStatus(str, Enum):
    QUEUED = "queued"
    CANCELED = "canceled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class AutomationExecutionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "failed"


class TestingJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    event: TestingJobEvent
    project_id: str = Field(min_length=1, max_length=128)
    artifact_version_id: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=128)
    requester_id: str = Field(min_length=1, max_length=128)
    requester_email: str = Field(min_length=1, max_length=320)
    payload: dict


class DiscardJobRequest(BaseModel):
    actor_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=3, max_length=1000)
