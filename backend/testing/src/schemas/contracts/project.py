from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

class ProjectCreate(BaseModel):
    key: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z][A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    project_type: Literal["web", "mobile", "api", "desktop", "embedded", "other"] = "web"
    locale: str = Field(default="vi-VN", min_length=2, max_length=20)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", min_length=2, max_length=80)
    settings: dict[str, Any] = Field(default_factory=dict)
    initial_qa_user_id: str = Field(min_length=1, max_length=320)
    planning_method: Literal["SCRUM", "KANBAN"] = "SCRUM"
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    automation_framework: Literal["playwright", "cypress", "selenium"] | None = None
    automation_language: Literal["typescript", "javascript", "python"] | None = None

    @model_validator(mode="after")
    def validate_automation_runtime(self):
        framework = self.automation_framework
        language = self.automation_language
        if (framework is None) != (language is None):
            raise ValueError("Phải cấu hình đồng thời công cụ và ngôn ngữ tự động hóa")
        if framework == "selenium" and language != "python":
            raise ValueError("Selenium yêu cầu Python")
        if framework in {"playwright", "cypress"} and language == "python":
            raise ValueError("Playwright và Cypress yêu cầu TypeScript hoặc JavaScript")
        return self


class ProjectCapabilities(BaseModel):
    can_create_project: bool


class ProjectPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    project_type: Literal["web", "mobile", "api", "desktop", "embedded", "other"] | None = None
    locale: str | None = Field(default=None, min_length=2, max_length=20)
    timezone: str | None = Field(default=None, min_length=2, max_length=80)
    settings: dict[str, Any] | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    automation_framework: Literal["playwright", "cypress", "selenium"] | None = None
    automation_language: Literal["typescript", "javascript", "python"] | None = None

    @model_validator(mode="after")
    def validate_automation_runtime(self):
        fields_set = self.model_fields_set
        if not ({"automation_framework", "automation_language"} & fields_set):
            return self
        if not {"automation_framework", "automation_language"}.issubset(fields_set):
            raise ValueError("Phải cập nhật đồng thời công cụ và ngôn ngữ tự động hóa")
        framework = self.automation_framework
        language = self.automation_language
        if (framework is None) != (language is None):
            raise ValueError("Phải cấu hình đồng thời công cụ và ngôn ngữ tự động hóa")
        if framework == "selenium" and language != "python":
            raise ValueError("Selenium yêu cầu Python")
        if framework in {"playwright", "cypress"} and language == "python":
            raise ValueError("Playwright và Cypress yêu cầu TypeScript hoặc JavaScript")
        return self


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
    priority: Literal["LOW", "MEDIUM", "HIGH", "HIGHEST"] = "MEDIUM"
    estimate: float | None = Field(default=None, gt=0, le=1_000_000)
    assignee_id: str | None = Field(default=None, min_length=1, max_length=200)
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    due_at: datetime | None = None
    requirement_ids: list[str] = Field(default_factory=list, max_length=500)
    release_id: str | None = Field(default=None, min_length=1, max_length=200)


class WorkItemPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    priority: Literal["LOW", "MEDIUM", "HIGH", "HIGHEST"] | None = None
    estimate: float | None = Field(default=None, gt=0, le=1_000_000)
    assignee_id: str | None = Field(default=None, min_length=1, max_length=200)
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    due_at: datetime | None = None
    requirement_ids: list[str] | None = Field(default=None, max_length=500)
    release_id: str | None = Field(default=None, min_length=1, max_length=200)


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
    allowed_roles: list[Literal["BA", "DEVELOPER"]] = Field(min_length=1, max_length=2)


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
    status: Literal["NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"] = "NOT_STARTED"


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
    project_role: Literal["QA", "TESTER", "BA", "DEVELOPER", "VIEWER"]


class ProjectMemberPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    project_role: Literal["QA", "TESTER", "BA", "DEVELOPER", "VIEWER"] | None = None
    status: Literal["ACTIVE", "INACTIVE"] | None = None

