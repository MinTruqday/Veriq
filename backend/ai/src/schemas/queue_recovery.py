from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DeadLetterRedriveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)


class DeadLetterRecoveryAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, max_length=100)
    requested_by: str = Field(min_length=1, max_length=200)
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    origin_queue: Optional[str] = Field(default=None, max_length=200)
    identity_type: Optional[Literal["event_id", "automation_run_id"]] = None
    identity_sha256: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    redrive_count: int = Field(ge=0, strict=True)
    source_delivery_attempt: Optional[int] = Field(default=None, ge=0, strict=True)
    delivery_attempt_reset: bool = False
    status: Literal[
        "RETAINED",
        "PREPARED",
        "PUBLISH_FAILED",
        "PUBLISHED",
        "DELIVERY_UNCERTAIN",
        "ACKNOWLEDGED",
    ]
    reason: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime
    published_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
