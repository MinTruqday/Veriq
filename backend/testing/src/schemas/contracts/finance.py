from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PayrollColumnMapping(BaseModel):
    employee: str = Field(min_length=1, max_length=200)
    hourly_cost: str = Field(min_length=1, max_length=200)
    currency: str = Field(min_length=1, max_length=200)
    valid_from: str = Field(min_length=1, max_length=200)
    valid_until: str | None = Field(default=None, max_length=200)


class PayrollRowResolution(BaseModel):
    row_number: int = Field(ge=2)
    action: Literal["SKIP", "APPLY"]


class PayrollImportApply(BaseModel):
    expected_revision: int = Field(ge=1)
    resolutions: list[PayrollRowResolution] = Field(default_factory=list, max_length=5000)


class CustomerCommercialTerms(BaseModel):
    expected_revision: int = Field(ge=0)
    contract_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    currency: str = Field(min_length=3, max_length=3)
    tax_included: bool
    scope_note: str = Field(default="", max_length=5000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value):
        return value.strip().upper()


class CapacityEntry(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    available_hours: Decimal = Field(ge=0, max_digits=8, decimal_places=2)


class CapacityUpdate(BaseModel):
    expected_revision: int = Field(ge=0)
    period_start: date
    period_end: date
    entries: list[CapacityEntry] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_period_and_users(self):
        if self.period_end < self.period_start:
            raise ValueError("CAPACITY_PERIOD_INVALID")
        user_ids = [entry.user_id for entry in self.entries]
        if len(user_ids) != len(set(user_ids)):
            raise ValueError("CAPACITY_USER_DUPLICATE")
        return self
