from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    key: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z][A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    project_type: str = Field(min_length=1, max_length=100)
    locale: str | None = Field(
        default=None, min_length=2, max_length=35, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"
    )
    timezone: str = Field(min_length=2, max_length=80)
    settings: dict[str, Any] = Field(default_factory=dict)
    planning_method: Literal["SCRUM", "KANBAN"] = "SCRUM"
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None

    @field_validator("project_type")
    @classmethod
    def normalize_project_type(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("Project type is required")
        return normalized


class ProjectCapabilities(BaseModel):
    can_create_project: bool


class ProjectComplexityAssessmentInput(BaseModel):
    model_config = {"extra": "forbid"}

    instruction: str = Field(default="", max_length=5000)
    output_language: str | None = Field(
        default=None,
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    idempotency_key: str = Field(min_length=8, max_length=200)
    document_ids: list[str] = Field(max_length=5000)
    requirement_version_ids: list[str] = Field(max_length=5000)

    @field_validator("document_ids", "requirement_version_ids")
    @classmethod
    def validate_scope_ids(cls, values):
        if len(values) != len(set(values)) or any(
            not value.strip() or len(value) > 200 for value in values
        ):
            raise ValueError("INVALID_PROJECT_COMPLEXITY_SCOPE_IDS")
        return values

    @model_validator(mode="after")
    def require_scope(self):
        if not self.document_ids and not self.requirement_version_ids:
            raise ValueError("PROJECT_COMPLEXITY_SOURCE_SCOPE_REQUIRED")
        return self


class ProjectPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    project_lead_user_id: str | None = Field(default=None, min_length=1, max_length=320)
    description: str | None = Field(default=None, max_length=5000)
    project_type: str | None = Field(default=None, min_length=1, max_length=100)
    locale: str | None = Field(default=None, min_length=2, max_length=20)
    timezone: str | None = Field(default=None, min_length=2, max_length=80)
    settings: dict[str, Any] | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    @field_validator("project_type")
    @classmethod
    def normalize_project_type(cls, value):
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Project type cannot be empty")
        return normalized

class WorkItemType(str, Enum):
    INITIATIVE = "INITIATIVE"
    EPIC = "EPIC"
    STORY = "STORY"
    TASK = "TASK"
    BUG = "BUG"
    SUBTASK = "SUBTASK"


class WorkItemStatus(str, Enum):
    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class WorkItemCreate(BaseModel):
    item_type: WorkItemType
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(default="", max_length=5000)
    parent_id: str | None = Field(default=None, min_length=1, max_length=200)
    priority: str | None = Field(default=None, min_length=1, max_length=100)
    estimate: float | None = Field(default=None, gt=0, le=1_000_000)
    assignee_id: str | None = Field(default=None, min_length=1, max_length=200)
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    due_at: datetime | None = None
    requirement_ids: list[str] = Field(default_factory=list, max_length=500)
    release_id: str | None = Field(default=None, min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values):
        normalized = []
        seen = set()
        for value in values:
            label = value.strip()
            if not label or len(label) > 40:
                raise ValueError("Mỗi thẻ phải có từ 1 đến 40 ký tự")
            identity = label.casefold()
            if identity not in seen:
                seen.add(identity)
                normalized.append(label)
        return normalized

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value):
        if value is None:
            return None
        normalized = " ".join(str(value).split())
        return normalized or None


class WorkItemPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    priority: str | None = Field(default=None, min_length=1, max_length=100)
    estimate: float | None = Field(default=None, gt=0, le=1_000_000)
    assignee_id: str | None = Field(default=None, min_length=1, max_length=200)
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    due_at: datetime | None = None
    requirement_ids: list[str] | None = Field(default=None, max_length=500)
    release_id: str | None = Field(default=None, min_length=1, max_length=200)
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values):
        if values is None:
            return values
        normalized = []
        seen = set()
        for value in values:
            label = value.strip()
            if not label or len(label) > 40:
                raise ValueError("Mỗi thẻ phải có từ 1 đến 40 ký tự")
            identity = label.casefold()
            if identity not in seen:
                seen.add(identity)
                normalized.append(label)
        return normalized

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value):
        if value is None:
            return None
        normalized = " ".join(str(value).split())
        return normalized or None


class WorkItemTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    status: str = Field(min_length=1, max_length=100)
    reason: str = Field(default="", max_length=2000)


class WorkItemRankUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    before_item_id: str | None = Field(default=None, min_length=1, max_length=200)


class BoardColumnInput(BaseModel):
    status: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=2, max_length=100)
    position: int = Field(ge=0, le=100)
    wip_limit: int | None = Field(default=None, ge=1, le=10000)


class PlanningBoardUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    columns: list[BoardColumnInput] = Field(min_length=1, max_length=20)


class WorkflowTransitionInput(BaseModel):
    from_status: str = Field(min_length=1, max_length=100)
    to_status: str = Field(min_length=1, max_length=100)
    allowed_roles: list[str] = Field(min_length=1, max_length=100)

    @field_validator("allowed_roles")
    @classmethod
    def normalize_allowed_roles(cls, values):
        normalized = [" ".join(value.split()).upper() for value in values]
        if any(not value or len(value) > 80 for value in normalized):
            raise ValueError("WORKFLOW_ROLE_INVALID")
        if len(normalized) != len(set(normalized)):
            raise ValueError("WORKFLOW_ROLE_DUPLICATE")
        return normalized


class WorkflowStatusInput(BaseModel):
    key: str = Field(min_length=1, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=2, max_length=100)
    counts_as_completed: bool = False


class PlanningWorkflowUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    statuses: list[WorkflowStatusInput] = Field(min_length=1, max_length=50)
    transitions: list[WorkflowTransitionInput] = Field(min_length=1, max_length=100)


class WorkItemDependencyCreate(BaseModel):
    target_item_id: str = Field(min_length=1, max_length=200)
    dependency_type: Literal["BLOCKS", "RELATES_TO"]


class SprintCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    goal: str = Field(default="", max_length=2000)
    start_at: datetime
    end_at: datetime


class SprintPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    goal: str | None = Field(default=None, max_length=2000)
    start_at: datetime | None = None
    end_at: datetime | None = None


class SprintTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    action: Literal["START", "COMPLETE"]
    reason: str = Field(default="", max_length=2000)
    unfinished_action: Literal["BACKLOG", "NEXT_SPRINT", "CANCEL"] | None = None
    target_sprint_id: str | None = Field(default=None, min_length=1, max_length=200)
    target_status: str | None = Field(default=None, min_length=1, max_length=100)


class SprintScopePatch(BaseModel):
    expected_revision: int = Field(ge=1)
    work_item_ids: list[str] = Field(default_factory=list, max_length=1000)


class ProjectTaskMigrationMapping(BaseModel):
    legacy_status: str = Field(min_length=1, max_length=100)
    target_status: str = Field(min_length=1, max_length=100)


class ProjectTaskMigrationInput(BaseModel):
    mappings: list[ProjectTaskMigrationMapping] = Field(min_length=1, max_length=50)


class ProjectProgressPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    project_completion_percent: int = Field(ge=0, le=100)
    note: str = Field(min_length=2, max_length=2000)


class ProjectTaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(default="", max_length=5000)
    weight: float = Field(gt=0, le=1_000_000)
    assignee_id: str | None = Field(default=None, min_length=1, max_length=200)
    due_at: str | None = Field(default=None, max_length=80)
    status: Literal["NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"] = (
        "NOT_STARTED"
    )


class ProjectTaskPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    weight: float | None = Field(default=None, gt=0, le=1_000_000)
    assignee_id: str | None = Field(default=None, min_length=1, max_length=200)
    due_at: str | None = Field(default=None, max_length=80)
    status: Literal["NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"] | None = None


class ProjectTaskDelete(BaseModel):
    expected_revision: int = Field(ge=1)


class ProjectArchiveInput(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=2000)


class ProjectMemberCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    project_role: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")

    @field_validator("project_role")
    @classmethod
    def normalize_project_role(cls, value):
        return value.strip().upper()


class ProjectMemberPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    project_role: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    status: Literal["ACTIVE", "INACTIVE"] | None = None

    @field_validator("project_role")
    @classmethod
    def normalize_project_role(cls, value):
        return value.strip().upper() if value else value
