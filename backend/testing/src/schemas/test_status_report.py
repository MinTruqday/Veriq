import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Recommendation = Literal[
    "ON_TRACK", "AT_RISK", "BLOCKED", "CONTINUE_TESTING", "READY_WITH_RISK", "NOT_READY"
]


class ReportingPeriod(BaseModel):
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("Kỳ báo cáo phải có múi giờ")
        if self.end_at < self.start_at:
            raise ValueError("Thời điểm kết thúc kỳ báo cáo phải sau thời điểm bắt đầu")
        return self


class StatusForecast(BaseModel):
    expected_completion_at: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list, max_length=200)


class TestStatusReportGenerate(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    snapshot_id: str = Field(min_length=1, max_length=200)
    build_id: str = Field(min_length=1, max_length=200)
    reporting_period: ReportingPeriod
    executive_summary: str = Field(default="", max_length=10000)
    forecast: StatusForecast | str = Field(default_factory=StatusForecast)
    recommendation: Recommendation | None = None
    distribution: list[str] = Field(default_factory=list, max_length=500)
    evidence_refs: list[str] = Field(default_factory=list, max_length=500)


class TestStatusReportPatch(BaseModel):
    model_config = {"extra": "forbid"}

    expected_revision: int = Field(ge=1)
    executive_summary: str | None = Field(default=None, max_length=10000)
    risk_explanation: str | None = Field(default=None, max_length=10000)
    forecast: StatusForecast | str | None = None
    recommendation_narrative: str | None = Field(default=None, max_length=10000)
    distribution: list[str] | None = Field(default=None, max_length=500)


class TestStatusReportEvidence(BaseModel):
    expected_revision: int = Field(ge=1)
    evidence_refs: list[str] = Field(min_length=1, max_length=500)


class TestStatusReportTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=5000)


class TestStatusReportAiDraft(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    instruction: str = Field(default="", max_length=5000)
    source_event_id: str = Field(min_length=1, max_length=200)
    source_event_revision: int = Field(ge=1)
    source_event_trigger: Literal["STATUS_REPORT_CREATED"]


def status_report_snapshot(report):
    excluded = {
        "approved_snapshot",
        "approved_snapshot_hash",
        "approval_history",
        "review_history",
        "status",
        "revision",
        "created_by",
        "created_at",
        "updated_at",
        "submitted_by",
        "submitted_at",
        "reviewed_by",
        "reviewed_at",
        "approved_by",
        "approved_at",
        "published_by",
        "published_at",
        "change_request",
    }
    return {key: value for key, value in report.items() if key not in excluded}


def status_report_hash(report):
    canonical = json.dumps(
        status_report_snapshot(report),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
