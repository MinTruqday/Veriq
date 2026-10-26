import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _normalized_evidence(value):
    return " ".join(unicodedata.normalize("NFC", str(value or "")).casefold().split())


def _evidence_supports_claim(claim, evidence):
    normalized_claim = _normalized_evidence(claim)
    if not normalized_claim:
        return True
    pattern = rf"(?<!\w){re.escape(normalized_claim)}(?!\w)"
    return re.search(pattern, _normalized_evidence(evidence), flags=re.UNICODE) is not None


class ConfirmedSkill(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: Literal["NOT_ASSESSED", "BEGINNER", "INTERMEDIATE", "ADVANCED"] = "NOT_ASSESSED"
    evidence: str = Field(default="", max_length=1000)
    source_block_id: str | None = Field(default=None, min_length=1, max_length=300)
    source_page_no: int | None = Field(default=None, ge=1)
    source_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    confirmed: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value):
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_source_reference(self):
        if self.source_page_no is not None and self.source_block_id is None:
            raise ValueError("skill_profile_source_page_requires_block")
        if self.source_block_id is not None and not self.evidence.strip():
            raise ValueError("skill_profile_source_block_requires_evidence")
        if self.source_sha256 is not None and self.source_block_id is None:
            raise ValueError("skill_profile_source_hash_requires_block")
        if self.source_block_id is not None:
            evidence = _normalized_evidence(self.evidence)
            if not _evidence_supports_claim(self.name, evidence):
                raise ValueError("skill_profile_source_does_not_support_skill")
        return self


class RelevantExperience(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    domain: str = Field(default="", max_length=120)
    technologies: list[str] = Field(default_factory=list, max_length=50)
    responsibilities: str = Field(default="", max_length=2000)
    evidence: str = Field(default="", max_length=1000)
    source_block_id: str | None = Field(default=None, min_length=1, max_length=300)
    source_page_no: int | None = Field(default=None, ge=1)
    source_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    confirmed: bool = False

    @model_validator(mode="after")
    def validate_source_reference(self):
        if self.source_page_no is not None and self.source_block_id is None:
            raise ValueError("skill_profile_source_page_requires_block")
        if self.source_block_id is not None and not self.evidence.strip():
            raise ValueError("skill_profile_source_block_requires_evidence")
        if self.source_sha256 is not None and self.source_block_id is None:
            raise ValueError("skill_profile_source_hash_requires_block")
        if self.source_block_id is not None:
            evidence = _normalized_evidence(self.evidence)
            claims = [self.title, self.domain, *self.technologies, self.responsibilities]
            if any(
                not _evidence_supports_claim(claim, evidence)
                for claim in claims
                if str(claim or "").strip()
            ):
                raise ValueError("skill_profile_source_does_not_support_experience")
        return self


class SkillProfilePatch(BaseModel):
    expected_revision: int = Field(ge=0)
    skills: list[ConfirmedSkill] = Field(default_factory=list, max_length=100)
    experiences: list[RelevantExperience] = Field(default_factory=list, max_length=50)
    availability: Literal["AVAILABLE", "LIMITED", "UNAVAILABLE"] = "AVAILABLE"


class AssignmentRecommendationInput(BaseModel):
    expected_run_revision: int | None = Field(default=None, ge=1)
    required_skills: list[str] = Field(default_factory=list, max_length=50)
