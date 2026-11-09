from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class CapacityEntry(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    available_hours: Decimal = Field(ge=0, max_digits=8, decimal_places=2)
    max_concurrent_projects: int | None = Field(default=None, ge=1)


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
