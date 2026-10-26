from enum import Enum
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field, PrivateAttr


class SystemRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class CurrentUser(BaseModel):
    _access_token: str = PrivateAttr(default="")
    _ai_automation_run_id: str = PrivateAttr(default="")
    _ai_automation_trigger: str = PrivateAttr(default="")
    _ai_automation_source_event_id: str = PrivateAttr(default="")
    _ai_automation_initiator_id: str = PrivateAttr(default="")
    _ai_automation_definition_id: str = PrivateAttr(default="")
    _ai_automation_publication_permissions: list[str] = PrivateAttr(default_factory=list)
    id: str = Field(alias="_id")
    email: str = ""
    system_role: SystemRole = SystemRole.USER

    @property
    def is_system_admin(self):
        return self.system_role == SystemRole.ADMIN


def empty_doc():
    return {"type": "doc", "content": []}


KnowledgeSourceType = Literal[
    "SRS",
    "BRD",
    "USER_STORY",
    "ACCEPTANCE_CRITERIA",
    "BUSINESS_RULE",
    "API_SPEC",
    "UI_SPEC",
    "ARCHITECTURE",
    "MEETING_NOTE",
    "RELEASE_NOTE",
    "BUG_HISTORY",
    "TEST_ARTIFACT",
    "REGULATION",
    "REFERENCE",
    "OTHER",
]
KnowledgeAuthority = Literal[
    "APPROVED_SOURCE",
    "CONTROLLED_SOURCE",
    "PROJECT_REFERENCE",
    "SUPPLEMENTAL",
    "DRAFT",
    "UNVERIFIED",
]


class KnowledgeApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


TestOutcome: TypeAlias = Literal["PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_APPLICABLE"]
TestExecutionStatus: TypeAlias = Literal[
    "PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_APPLICABLE", "IN_PROGRESS", "NOT_RUN"
]
NOT_APPLICABLE_OUTCOME = "NOT_APPLICABLE"
FAILED_OUTCOME = "FAIL"


class CompletionRecommendation(str, Enum):
    READY_FOR_RELEASE = "READY_FOR_RELEASE"
    READY_WITH_RISK = "READY_WITH_RISK"
    NOT_READY = "NOT_READY"
    CONTINUE_TESTING = "CONTINUE_TESTING"


class ResidualRiskTreatment(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    MITIGATE = "MITIGATE"
    TRANSFER = "TRANSFER"
    AVOID = "AVOID"


class ResidualRiskStatus(str, Enum):
    OPEN = "OPEN"
    MONITORING = "MONITORING"
    CLOSED = "CLOSED"


class TestwareHandoverStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    HANDED_OVER = "HANDED_OVER"
    ACCEPTED = "ACCEPTED"


class ImprovementActionStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class PreventionActionStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    IMPLEMENTED = "IMPLEMENTED"
    EFFECTIVENESS_REVIEW = "EFFECTIVENESS_REVIEW"
    CLOSED = "CLOSED"


class EnvironmentIncidentStatus(str, Enum):
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TestabilityStatus(str, Enum):
    TESTABLE = "TESTABLE"
    TESTABLE_WITH_RISK = "TESTABLE_WITH_RISK"
    NOT_TESTABLE = "NOT_TESTABLE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class AnalysisFindingStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    ACCEPTED_RISK = "ACCEPTED_RISK"


class ReviewFindingStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    VERIFIED = "VERIFIED"


class ReviewDecision(str, Enum):
    ACCEPTED = "ACCEPTED"
    ACCEPTED_WITH_ACTIONS = "ACCEPTED_WITH_ACTIONS"
    REWORK_REQUIRED = "REWORK_REQUIRED"
    REJECTED = "REJECTED"


class ReviewTerminalStatus(str, Enum):
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class ControlActionStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class AutomationExecutionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TestPlanRiskStatus(str, Enum):
    OPEN = "OPEN"
    MITIGATING = "MITIGATING"
    ACCEPTED = "ACCEPTED"
    CLOSED = "CLOSED"


class WebhookDeliveryStatus(str, Enum):
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class RequirementCandidateStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
