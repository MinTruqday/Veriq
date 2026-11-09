from typing import List

from pydantic import BaseModel, ConfigDict, Field


class StructuredRouting(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CrossDocumentQueries(StructuredRouting):
    queries: List[str] = Field(
        min_length=2,
        max_length=100,
    )
