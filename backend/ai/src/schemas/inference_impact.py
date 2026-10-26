from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImpactClassificationSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_case_version_id: str = Field(min_length=1, max_length=128)
    classification: Literal["STILL_VALID", "POTENTIALLY_AFFECTED", "NEEDS_UPDATE", "OBSOLETE"]
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=2, max_length=5000)
    maintenance_patch: "MaintenanceTestCasePatchOutput | None" = None

    @model_validator(mode="after")
    def require_patch_for_update(self):
        if self.classification == "NEEDS_UPDATE" and self.maintenance_patch is None:
            raise ValueError("maintenance_patch_required")
        return self

class MaintenanceTestStepOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=2, max_length=5000)
    expected: str = Field(min_length=2, max_length=5000)
    test_data: dict = Field(default_factory=dict)

class MaintenanceTestCasePatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=2, max_length=300)
    type: Literal[
        "happy_path",
        "negative",
        "boundary",
        "validation",
        "permission",
        "state_transition",
        "integration",
        "error_handling",
        "data_persistence",
        "concurrency",
        "api",
        "ui",
        "custom",
    ] | None = None
    objective: str | None = Field(default=None, min_length=2, max_length=5000)
    preconditions: str | None = Field(default=None, min_length=2, max_length=5000)
    steps: List[MaintenanceTestStepOutput] | None = Field(default=None, max_length=100)
    expected: str | None = Field(default=None, min_length=2, max_length=5000)
    test_data: dict | None = None

    @model_validator(mode="after")
    def require_patch_value(self):
        if not any(
            value is not None
            and value != ""
            and value != []
            and value != {}
            and not (isinstance(value, str) and not value.strip())
            for value in self.model_dump().values()
        ):
            raise ValueError("patch_content_required")
        return self

class NewTestCandidateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=2, max_length=5000)
    confidence: float = Field(ge=0, le=1)
    patch: MaintenanceTestCasePatchOutput

    @model_validator(mode="after")
    def require_complete_test_case(self):
        if not self.patch.title or not self.patch.steps or not self.patch.expected:
            raise ValueError("new_test_candidate_incomplete")
        return self


ImpactClassificationSuggestionOutput.model_rebuild()

class ImpactClassificationOutput(BaseModel):
    """Structured Test Case impact classifications and maintenance candidates."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["impact_analysis"]
    suggestions: List[ImpactClassificationSuggestionOutput] = Field(default_factory=list, max_length=100)
    new_test_candidates: List[NewTestCandidateOutput] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)

