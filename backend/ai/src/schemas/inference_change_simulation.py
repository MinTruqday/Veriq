from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChangeSimulationPatchStepOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: str = Field(min_length=1, max_length=2000)
    expected: str = Field(min_length=1, max_length=2000)
    test_data: dict = Field(default_factory=dict)


class ChangeSimulationPatchOutput(BaseModel):
    """Preview-only subset of Test Case fields supported by maintenance updates."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

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
    test_data: dict | None = None
    objective: str | None = Field(default=None, min_length=1, max_length=5000)
    preconditions: str | None = Field(default=None, min_length=1, max_length=5000)
    expected: str | None = Field(default=None, min_length=1, max_length=5000)
    steps: list[ChangeSimulationPatchStepOutput] | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_patch_content(self):
        meaningful = any(
            (isinstance(value, str) and bool(value.strip()))
            or (isinstance(value, dict) and bool(value))
            or (isinstance(value, list) and bool(value))
            for value in self.model_dump(exclude_none=True).values()
        )
        if not meaningful:
            raise ValueError("change_simulation_patch_content_required")
        return self


class ChangeSimulationEvidenceQuoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: Literal["BASELINE_REQUIREMENT", "PROPOSED_REQUIREMENT", "TEST_CASE_VERSION"]
    artifact_version_id: str = Field(min_length=1, max_length=160)
    quote: str = Field(min_length=2, max_length=2000)


class ChangeSimulationClassificationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_case_version_id: str = Field(min_length=1, max_length=160)
    classification: Literal[
        "STILL_VALID",
        "POTENTIALLY_AFFECTED",
        "NEEDS_UPDATE",
        "OBSOLETE",
        "INSUFFICIENT_EVIDENCE",
    ]
    reason: str = Field(min_length=2, max_length=3000)
    evidence: list[ChangeSimulationEvidenceQuoteOutput] = Field(min_length=1, max_length=12)
    proposed_patch: ChangeSimulationPatchOutput | None = None
    proposed_patch_evidence: list[ChangeSimulationEvidenceQuoteOutput] = Field(
        default_factory=list, max_length=12
    )

    @model_validator(mode="after")
    def validate_patch_status(self):
        if self.classification == "NEEDS_UPDATE" and not self.proposed_patch:
            raise ValueError("change_simulation_patch_required_for_update")
        if self.classification == "NEEDS_UPDATE" and not self.proposed_patch_evidence:
            raise ValueError("change_simulation_patch_evidence_required_for_update")
        if self.classification != "NEEDS_UPDATE" and (
            self.proposed_patch is not None or self.proposed_patch_evidence
        ):
            raise ValueError("change_simulation_patch_only_allowed_for_update")
        classification_evidence = {
            (item.source_type, item.artifact_version_id, item.quote)
            for item in self.evidence
        }
        if any(
            (item.source_type, item.artifact_version_id, item.quote)
            not in classification_evidence
            for item in self.proposed_patch_evidence
        ):
            raise ValueError("change_simulation_patch_evidence_not_in_classification_evidence")
        if self.classification == "NEEDS_UPDATE" and not {
            "PROPOSED_REQUIREMENT",
            "TEST_CASE_VERSION",
        }.issubset({item.source_type for item in self.proposed_patch_evidence}):
            raise ValueError("change_simulation_patch_evidence_scope_incomplete")
        return self


class ChangeSimulationReportOutput(BaseModel):
    """Classify every supplied linked Test Case version without mutating project data."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["change_simulation_report"] = "change_simulation_report"
    baseline_requirement_version_id: str = Field(min_length=1, max_length=160)
    classifications: list[ChangeSimulationClassificationOutput] = Field(max_length=100)
    unresolved: list[str] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=30)
