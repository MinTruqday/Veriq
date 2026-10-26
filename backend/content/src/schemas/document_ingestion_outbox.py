from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DocumentIngestionDispatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"


class DocumentIngestionDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    user_id: str = ""
    superseded_document_id: str = ""
    status: DocumentIngestionDispatchStatus = DocumentIngestionDispatchStatus.PENDING
    attempts: int = Field(default=0, ge=0)
    available_at: datetime
    created_at: datetime
    updated_at: datetime
