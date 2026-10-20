from typing import Annotated, Any, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectQuestionOutput(BaseModel):
    """Answer in at most five sentences and cite only evidence references actually used"""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["project_question"]
    answer: str = Field(min_length=1, max_length=4000)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)

