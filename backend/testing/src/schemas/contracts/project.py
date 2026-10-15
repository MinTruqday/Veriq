from typing import Any, Literal

from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    key: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z][A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    project_type: Literal["web", "mobile", "api", "desktop", "embedded", "other"] = "web"
    locale: str = Field(default="vi-VN", min_length=2, max_length=20)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", min_length=2, max_length=80)
    settings: dict[str, Any] = Field(default_factory=dict)
    initial_qa_user_id: str = Field(min_length=1, max_length=320)


class ProjectPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    project_type: Literal["web", "mobile", "api", "desktop", "embedded", "other"] | None = None
    locale: str | None = Field(default=None, min_length=2, max_length=20)
    timezone: str | None = Field(default=None, min_length=2, max_length=80)
    settings: dict[str, Any] | None = None


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

