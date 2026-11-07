from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class ReportingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportPeriod(ReportingModel):
    start_at: datetime
    end_at: datetime
    timezone: str

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("REPORT_TIMEZONE_REQUIRED")
        if self.start_at >= self.end_at:
            raise ValueError("REPORT_PERIOD_INVALID")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("REPORT_TIMEZONE_INVALID") from error
        return self


class ReportRecipient(ReportingModel):
    user_id: str = Field(min_length=1, max_length=200)
    access: Literal["VIEW", "COMMENT"] = "VIEW"
    can_download: bool = False
    acknowledgment_required: bool = False


class ReportParticipants(ReportingModel):
    owner_id: str = Field(min_length=1, max_length=200)
    editor_ids: list[str] = Field(default_factory=list, max_length=100)
    reviewer_id: str = Field(min_length=1, max_length=200)
    recipients: list[ReportRecipient] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def unique_people(self):
        ids = [recipient.user_id for recipient in self.recipients]
        if len(ids) != len(set(ids)) or len(self.editor_ids) != len(set(self.editor_ids)):
            raise ValueError("REPORT_PARTICIPANTS_DUPLICATE")
        return self


class ReportAssignmentPatch(ReportingModel):
    expected_revision: int = Field(ge=1)
    participants: ReportParticipants
    reason: str = Field(min_length=1, max_length=3000)


class ReportCreate(ReportParticipants):
    title: str = Field(min_length=2, max_length=300)
    kind: Literal["PERSONAL", "TEAM", "PROJECT"]
    period: ReportPeriod
    subject_ids: list[str] = Field(default_factory=list, max_length=100)
    template_version_id: str = Field(min_length=1, max_length=200)
    output_language: str = Field(min_length=2, max_length=35, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    due_at: datetime | None = None
    idempotency_key: str = Field(min_length=8, max_length=200)

    @field_validator("due_at")
    @classmethod
    def aware_deadline(cls, value):
        if value and value.tzinfo is None:
            raise ValueError("REPORT_TIMEZONE_REQUIRED")
        return value


class ReportPatch(ReportingModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    content_doc: dict[str, Any] | None = None
    participants: ReportParticipants | None = None
    refresh_snapshot: bool = False
    reason: str = Field(default="", max_length=3000)


class ReportAction(ReportingModel):
    expected_revision: int = Field(ge=1)
    action: Literal["SUBMIT", "REQUEST_CHANGES", "APPROVE", "PUBLISH", "ARCHIVE", "NEW_VERSION"]
    note: str = Field(default="", max_length=3000)
    idempotency_key: str = Field(min_length=8, max_length=200)


class ReportComment(ReportingModel):
    body: str = Field(min_length=1, max_length=10000)
    parent_id: str | None = Field(default=None, max_length=200)
    block_id: str | None = Field(default=None, max_length=200)
    mentioned_user_ids: list[str] = Field(default_factory=list, max_length=50)
    idempotency_key: str = Field(min_length=8, max_length=200)


class ReportExportRequest(ReportingModel):
    expected_revision: int = Field(ge=1)
    format: Literal["docx", "pdf"]
    idempotency_key: str = Field(min_length=8, max_length=200)


class ReportTemplateCreate(ReportingModel):
    template_id: str | None = Field(default=None, max_length=200)
    name: str = Field(min_length=2, max_length=200)
    kind: Literal["PERSONAL", "TEAM", "PROJECT"]
    content_doc: dict[str, Any]
    expected_revision: int | None = Field(default=None, ge=1)
    import_preview_id: str | None = Field(default=None, max_length=200)
    accepted_warnings: list[str] = Field(default_factory=list, max_length=100)


class ReportingSettings(ReportingModel):
    expected_revision: int = Field(ge=0)
    enabled: bool
    timezone: str
    allowed_kinds: list[Literal["PERSONAL", "TEAM", "PROJECT"]] = Field(default_factory=lambda: ["PERSONAL", "TEAM", "PROJECT"])
    reminder_hours_before: int = Field(default=24, ge=0, le=720)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("REPORT_TIMEZONE_INVALID") from error
        return value


class ReportScheduleCreate(ReportingModel):
    name: str = Field(min_length=2, max_length=200)
    report: ReportCreate
    cadence: Literal["ONCE", "HOUR", "DAY", "WEEK", "MONTH", "QUARTER", "YEAR"]
    period_mode: Literal["PREVIOUS_INTERVAL", "CUSTOM_ANCHORED"] = "PREVIOUS_INTERVAL"
    interval: int = Field(default=1, ge=1, le=365)
    first_run_at: datetime
    due_hours_after: int = Field(default=24, ge=1, le=8760)
    formats: list[Literal["docx", "pdf"]] = Field(default_factory=lambda: ["docx", "pdf"], min_length=1, max_length=2)
    idempotency_key: str = Field(min_length=8, max_length=200)

    @field_validator("first_run_at")
    @classmethod
    def aware_run(cls, value):
        if value.tzinfo is None:
            raise ValueError("REPORT_TIMEZONE_REQUIRED")
        return value


class ReportSchedulePatch(ReportingModel):
    expected_revision: int = Field(ge=1)
    enabled: bool


class ReportAIDraft(ReportingModel):
    expected_revision: int = Field(ge=1)
    mode: Literal["DRAFT", "REVIEW", "SUMMARY", "TRANSLATE"]
    instruction: str = Field(default="", max_length=5000)
    output_language: str = Field(min_length=2, max_length=35, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    idempotency_key: str = Field(min_length=8, max_length=200)


class ReportDeliveryPatch(ReportingModel):
    user_id: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(ge=0)
    access: Literal["VIEW", "COMMENT"] = "VIEW"
    can_download: bool = False
    acknowledgment_required: bool = False
    revoked: bool = False


class ReportCommentPatch(ReportingModel):
    expected_revision: int = Field(ge=1)
    resolved: bool


class ReportExportRetry(ReportingModel):
    expected_generation: int = Field(ge=0)


class ReportAIApply(ReportingModel):
    expected_revision: int = Field(ge=1)
    proposal_id: str = Field(min_length=1, max_length=200)
    section_indices: list[int] = Field(min_length=1, max_length=40)
    idempotency_key: str = Field(min_length=8, max_length=200)

    @field_validator("section_indices")
    @classmethod
    def unique_sections(cls, value):
        if len(set(value)) != len(value) or any(item < 0 for item in value):
            raise ValueError("REPORT_AI_SECTIONS_INVALID")
        return value
