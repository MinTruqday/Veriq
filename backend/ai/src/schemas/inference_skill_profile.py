
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SkillProfileSourceBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(min_length=1, max_length=300)
    page_no: int | None = Field(default=None, ge=1)
    text: str = Field(min_length=1, max_length=3000)


class SkillProfileExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    source_blocks: list[SkillProfileSourceBlock] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def require_unique_source_block_ids(self):
        block_ids = [item.block_id for item in self.source_blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("cv_source_block_id_duplicate")
        return self


class ExtractedSkillCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    evidence_quote: str = Field(min_length=3, max_length=1000)
    source_block_id: str = Field(min_length=1, max_length=300)
    page_no: int | None = Field(default=None, ge=1)


class ExtractedExperienceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    period: str = Field(default="", max_length=120)
    domain: str = Field(default="", max_length=120)
    technologies: list[str] = Field(default_factory=list, max_length=50)
    responsibilities: str = Field(default="", max_length=2000)
    evidence_quote: str = Field(min_length=3, max_length=1000)
    source_block_id: str = Field(min_length=1, max_length=300)
    page_no: int | None = Field(default=None, ge=1)


class SkillProfileExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[ExtractedSkillCandidate] = Field(default_factory=list, max_length=100)
    experiences: list[ExtractedExperienceCandidate] = Field(default_factory=list, max_length=50)
    warnings: list[str] = Field(default_factory=list, max_length=30)
