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

    @model_validator(mode="after")
    def require_reason_for_exception(self):
        if self.status in {"NOT_APPLICABLE", "WAIVED"} and len(self.reason.strip()) < 2:
            raise ValueError("Cần nêu lý do cho quyết định ngoại lệ")
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
    defect_id: str | None = Field(default=None, max_length=200)
    note: str = Field(default="", max_length=2000)

