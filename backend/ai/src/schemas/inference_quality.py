from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceQuoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=2, max_length=1000)


class AutomationScriptSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=100000)
    secret_placeholders: List[str] = Field(default_factory=list, max_length=100)


class AutomationScriptOutput(BaseModel):
    """Structured automation script draft."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["automation_script_generation"]
    suggestions: List[AutomationScriptSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class TestDataSuggestionItemOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable_name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=2, max_length=1000)
    value_type: Literal["text", "integer", "decimal", "boolean", "date", "enum"]
    category: Literal["positive", "negative", "boundary"]
    values: List[str] = Field(min_length=1, max_length=30)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=10)


class TestDataSuggestionsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["test_data_generation"]
    suggestions: List[TestDataSuggestionItemOutput] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=30)


class ExecutionAssistanceObservationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["OBSERVED", "POSSIBLE_INTERPRETATION", "LIMITATION"]
    step_id: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=2, max_length=4000)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=10)


class ExecutionAssistanceDefectDraftOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=300)
    description: str = Field(min_length=2, max_length=5000)
    steps_to_reproduce: List[str] = Field(min_length=1, max_length=50)
    expected_result: str = Field(min_length=2, max_length=3000)
    actual_result: str = Field(min_length=2, max_length=3000)
    evidence_quotes: List[EvidenceQuoteOutput] = Field(min_length=1, max_length=15)


class ExecutionAssistanceSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: List[ExecutionAssistanceObservationOutput] = Field(min_length=1, max_length=50)
    missing_information: List[str] = Field(default_factory=list, max_length=50)
    defect_draft: ExecutionAssistanceDefectDraftOutput | None = None


class ExecutionAssistanceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["execution_assistance"]
    suggestions: List[ExecutionAssistanceSuggestionOutput] = Field(min_length=1, max_length=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=100)
    warnings: List[str] = Field(default_factory=list, max_length=30)
