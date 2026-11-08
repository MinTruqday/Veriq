from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.schemas.contracts.common import EnvironmentIncidentStatus


class EnvironmentIncidentCreate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    environment_id: str = Field(min_length=1, max_length=200)
    build_id: str | None = Field(default=None, max_length=200)
    observed_at: datetime
    severity: str = Field(min_length=1, max_length=100)
    type: Literal[
        "UNAVAILABLE",
        "DEPLOYMENT_FAILURE",
        "TEST_DATA_FAILURE",
        "NETWORK",
        "DEPENDENCY",
        "CONFIGURATION",
        "CAPACITY",
        "CERTIFICATE",
        "ACCESS",
        "OTHER",
    ]
    description: str = Field(min_length=2, max_length=10000)
    affected_run_ids: list[str] = Field(default_factory=list, max_length=1000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=1000)
    owner_id: str = Field(min_length=1, max_length=200)

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("incident_severity_required")
        return value

    @model_validator(mode="after")
    def validate_observed_at(self):
        if self.observed_at.tzinfo is None:
            raise ValueError("Thời điểm quan sát phải có múi giờ")
        return self


class EnvironmentIncidentPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    severity: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=2, max_length=10000)
    affected_run_ids: list[str] | None = Field(default=None, max_length=1000)
    evidence_refs: list[str] | None = Field(default=None, max_length=1000)
    owner_id: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value):
        if value is None:
            return value
        value = " ".join(value.split())
        if not value:
            raise ValueError("incident_severity_required")
        return value


class EnvironmentIncidentTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    status: EnvironmentIncidentStatus
    resolution: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def validate_resolution(self):
        if (
            self.status
            in {EnvironmentIncidentStatus.RESOLVED, EnvironmentIncidentStatus.CLOSED}
            and not self.resolution.strip()
        ):
            raise ValueError("Incident đã xử lý phải có kết quả")
        return self
