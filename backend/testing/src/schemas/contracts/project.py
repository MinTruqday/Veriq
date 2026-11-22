from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    project_owner_user_id: str | None = Field(default=None, min_length=1, max_length=320)
    key: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z][A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    project_type: str = Field(min_length=1, max_length=100)
    locale: str | None = Field(
        default=None, min_length=2, max_length=35, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"
    )
    timezone: str = Field(min_length=2, max_length=80)
    settings: dict[str, Any] = Field(default_factory=dict)
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


class ProjectPatch(BaseModel):
    project_owner_user_id: str | None = Field(default=None, min_length=1, max_length=320)
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
    project_role: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    project_roles: list[str] | None = Field(default=None, min_length=1, max_length=10)

    @field_validator("project_role")
    @classmethod
    def normalize_project_role(cls, value):
        return value.strip().upper() if value else value

    @field_validator("project_roles")
    @classmethod
    def normalize_project_roles(cls, values):
        if values is None:
            return values
        normalized = list(dict.fromkeys(value.strip().upper() for value in values if value.strip()))
        if len(normalized) != len(values):
            raise ValueError("DUPLICATE_OR_EMPTY_PROJECT_ROLE")
        return normalized

    @model_validator(mode="after")
    def require_project_roles(self):
        roles = self.project_roles or ([self.project_role] if self.project_role else [])
        if not roles:
            raise ValueError("PROJECT_ROLE_REQUIRED")
        if self.project_role and self.project_role not in roles:
            raise ValueError("PROJECT_ROLE_LIST_MISMATCH")
        self.project_roles = roles
        self.project_role = roles[0] if len(roles) == 1 else None
        return self


class ProjectMemberPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    project_role: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    project_roles: list[str] | None = Field(default=None, min_length=1, max_length=10)
    status: Literal["ACTIVE", "INACTIVE"] | None = None

    @field_validator("project_role")
    @classmethod
    def normalize_project_role(cls, value):
        return value.strip().upper() if value else value

    @field_validator("project_roles")
    @classmethod
    def normalize_project_roles(cls, values):
        if values is None:
            return values
        normalized = list(dict.fromkeys(value.strip().upper() for value in values if value.strip()))
        if len(normalized) != len(values):
            raise ValueError("DUPLICATE_OR_EMPTY_PROJECT_ROLE")
        return normalized

    @model_validator(mode="after")
    def validate_project_roles(self):
        if self.project_roles is not None:
            if self.project_role and self.project_role not in self.project_roles:
                raise ValueError("PROJECT_ROLE_LIST_MISMATCH")
            self.project_role = self.project_roles[0] if len(self.project_roles) == 1 else None
        elif self.project_role:
            self.project_roles = [self.project_role]
        return self
