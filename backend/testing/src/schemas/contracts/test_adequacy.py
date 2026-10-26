from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


CoverageStatus = Literal[
    "UNASSESSED",
    "COVERED_PENDING_REVIEW",
    "VERIFIED_COVERED",
    "MISSING_INFORMATION",
    "NOT_APPLICABLE",
    "WAIVED",
]


class AdequacyRevisionInput(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=2000)


class CoverageDecisionInput(BaseModel):
    expected_revision: int = Field(ge=1)
    status: Literal["MISSING_INFORMATION", "NOT_APPLICABLE", "WAIVED"]
    reason: str = Field(default="", max_length=2000)
    clarification_id: str | None = Field(default=None, min_length=1, max_length=200)
    waiver_owner_id: str | None = Field(default=None, min_length=1, max_length=320)
    waiver_expires_at: datetime | None = None
    waiver_review_at: datetime | None = None

    @model_validator(mode="after")
    def require_reason_for_exception(self):
        if self.status == "MISSING_INFORMATION" and not self.clarification_id:
            raise ValueError("Thiếu thông tin phải gắn với Phiếu làm rõ")
        if self.status in {"NOT_APPLICABLE", "WAIVED"} and len(self.reason.strip()) < 2:
            raise ValueError("Cần nêu lý do cho quyết định ngoại lệ")
        if self.status == "WAIVED":
            if not self.waiver_owner_id or not self.waiver_expires_at or not self.waiver_review_at:
                raise ValueError("Waiver cần người chịu trách nhiệm, hạn hiệu lực và ngày rà soát lại")
            if self.waiver_review_at > self.waiver_expires_at:
                raise ValueError("Ngày rà soát lại không được sau hạn hiệu lực")
        if self.status != "WAIVED" and any((self.waiver_owner_id, self.waiver_expires_at, self.waiver_review_at)):
            raise ValueError("Thông tin waiver chỉ áp dụng cho quyết định chấp nhận có điều kiện")
        if self.status != "MISSING_INFORMATION" and self.clarification_id:
            raise ValueError("Phiếu làm rõ chỉ áp dụng khi còn thiếu thông tin")
        return self


class CoverageExecutionFeedbackInput(BaseModel):
    expected_revision: int = Field(ge=1)
    test_case_version_id: str = Field(min_length=1, max_length=200)
    outcome: Literal[
        "CAUGHT_DEFECT",
        "DID_NOT_DIFFERENTIATE",
        "NOT_EXECUTED",
        "NEEDS_TEST_ADDITION",
    ]
    test_result_id: str | None = Field(default=None, max_length=200)
    test_result_revision: int | None = Field(default=None, ge=1)
    defect_id: str | None = Field(default=None, max_length=200)
    note: str = Field(default="", max_length=2000)

