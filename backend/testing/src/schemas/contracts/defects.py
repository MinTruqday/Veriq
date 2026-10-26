from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.schemas.contracts.common import empty_doc


class DefectCreate(BaseModel):
    project_id: str
    defect_key: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=2, max_length=300)
    description_doc: dict[str, Any] = Field(default_factory=empty_doc)
    steps_to_reproduce: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    actual_result_doc: dict[str, Any] = Field(default_factory=empty_doc)
    expected_result_doc: dict[str, Any] = Field(default_factory=empty_doc)
    severity: Literal["blocker", "critical", "major", "minor", "trivial"] = "major"
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    environment: str = Field(default="", max_length=500)
    environment_id: str | None = Field(default=None, max_length=200)
    release: str = Field(default="", max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    build: str = Field(default="", max_length=200)
    build_id: str | None = Field(default=None, max_length=200)
    assignee: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    linked_test_result_id: str | None = None
    linked_test_case_version_id: str | None = None
    linked_requirement_version_ids: list[str] = Field(default_factory=list, max_length=200)
    root_cause_category: Literal[
        "REQUIREMENT",
        "DESIGN",
        "IMPLEMENTATION",
        "CONFIGURATION",
        "TEST_DATA",
        "TEST_CASE_GAP",
        "ENVIRONMENT",
        "INTEGRATION",
        "DEPLOYMENT",
        "PROCESS",
        "THIRD_PARTY",
        "UNKNOWN",
    ] = "UNKNOWN"
    root_cause_detail: str = Field(default="", max_length=5000)
    injected_phase: str = Field(default="", max_length=200)
    detected_phase: str = Field(default="", max_length=200)
    escape_reason: str = Field(default="", max_length=5000)
    prevention_candidate: bool = False


class DefectPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=300)
    description_doc: dict[str, Any] | None = None
    steps_to_reproduce: list[dict[str, Any]] | None = Field(default=None, max_length=500)
    actual_result_doc: dict[str, Any] | None = None
    expected_result_doc: dict[str, Any] | None = None
    severity: Literal["blocker", "critical", "major", "minor", "trivial"] | None = None
    priority: Literal["critical", "high", "medium", "low"] | None = None
    environment: str | None = Field(default=None, max_length=500)
    environment_id: str | None = Field(default=None, max_length=200)
    release: str | None = Field(default=None, max_length=200)
    release_id: str | None = Field(default=None, max_length=200)
    build: str | None = Field(default=None, max_length=200)
    build_id: str | None = Field(default=None, max_length=200)
    assignee: str | None = Field(default=None, max_length=200)
    attachments: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    linked_test_result_id: str | None = Field(default=None, max_length=200)
    linked_test_case_version_id: str | None = Field(default=None, max_length=200)
    linked_requirement_version_ids: list[str] | None = Field(default=None, max_length=200)
    root_cause_category: (
        Literal[
            "REQUIREMENT",
            "DESIGN",
            "IMPLEMENTATION",
            "CONFIGURATION",
            "TEST_DATA",
            "TEST_CASE_GAP",
            "ENVIRONMENT",
            "INTEGRATION",
            "DEPLOYMENT",
            "PROCESS",
            "THIRD_PARTY",
            "UNKNOWN",
        ]
        | None
    ) = None
    root_cause_detail: str | None = Field(default=None, max_length=5000)
    injected_phase: str | None = Field(default=None, max_length=200)
    detected_phase: str | None = Field(default=None, max_length=200)
    escape_reason: str | None = Field(default=None, max_length=5000)
    prevention_candidate: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if self.model_fields_set == {"expected_revision"}:
            raise ValueError("Phải có ít nhất một trường cần cập nhật")
        return self


class DefectTransition(BaseModel):
    expected_revision: int = Field(ge=1)
    to_status: Literal[
        "NEW",
        "CONFIRMED",
        "IN_PROGRESS",
        "RESOLVED",
        "READY_FOR_RETEST",
        "REOPENED",
        "CLOSED",
        "REJECTED",
        "DUPLICATE",
    ]
    reason: str = Field(min_length=2, max_length=2000)


class DefectRetestInput(BaseModel):
    test_result_id: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=200)


class BugTraceSuggestionInput(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    source_event_id: str = Field(min_length=1, max_length=200)
    source_event_revision: int = Field(ge=1)
    source_event_trigger: Literal["DEFECT_RECORDED", "DEFECT_CHANGED"]


class DefectTraceUpdateInput(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=2000)
    linked_test_result_id: str | None = Field(default=None, max_length=200)
    linked_test_case_version_id: str | None = Field(default=None, max_length=200)
    linked_requirement_version_ids: list[str] | None = Field(default=None, max_length=200)
    ai_result_id: str | None = Field(default=None, max_length=200)
    accepted_candidate_ids: list[str] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def require_trace_change(self):
        trace_fields = {
            "linked_test_result_id",
            "linked_test_case_version_id",
            "linked_requirement_version_ids",
        }
        if not trace_fields & self.model_fields_set:
            raise ValueError("Phải chọn ít nhất một liên kết truy vết cần thay đổi")
        return self
