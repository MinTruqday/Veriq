from datetime import date
from pydantic import BaseModel, Field, field_validator, model_validator


class TestPeriodCreate(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=2, max_length=200)
    objective: str = Field(default="", max_length=3000)
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    source_period_id: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("TEST_PERIOD_NAME_REQUIRED")
        return cleaned

    @model_validator(mode="after")
    def validate_dates(self):
        if self.planned_start_date and self.planned_end_date:
            if self.planned_start_date > self.planned_end_date:
                raise ValueError("TEST_PERIOD_END_BEFORE_START")
        return self


class TestPeriodPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    objective: str | None = Field(default=None, max_length=3000)
    planned_start_date: date | None = None
    planned_end_date: date | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("TEST_PERIOD_NAME_REQUIRED")
        return cleaned


class TestPeriodCarryOverSelection(BaseModel):
    source_test_run_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_test_plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    test_case_version_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def require_one_source(self):
        if bool(self.source_test_run_id) == bool(self.source_test_plan_id):
            raise ValueError("TEST_PERIOD_CARRY_OVER_REQUIRES_ONE_SOURCE")
        return self

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("TEST_PERIOD_CARRY_OVER_REASON_REQUIRED")
        return cleaned


class TestPeriodCloseInput(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=2000)
    carry_over_items: list[TestPeriodCarryOverSelection] = Field(default_factory=list, max_length=5000)


