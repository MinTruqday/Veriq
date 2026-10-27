from pydantic import BaseModel, ConfigDict, Field, model_validator


class StaffingEvidenceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=300)


class StaffingCandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=200)
    confirmed_skills: list[str] = Field(default_factory=list, max_length=100)
    relevant_experience: list[str] = Field(default_factory=list, max_length=50)
    evidence_facts: list[StaffingEvidenceFact] = Field(default_factory=list, max_length=100)
    availability: str = Field(min_length=1, max_length=30)
    active_project_count: int = Field(ge=0)
    active_case_count: int = Field(ge=0)
    active_run_count: int = Field(ge=0)
    hourly_cost: str | None = Field(default=None, max_length=40)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    payroll_effective_date: str | None = Field(default=None, max_length=10)


class StaffingRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    output_language: str = Field(
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    required_skills: list[str] = Field(default_factory=list, max_length=50)
    candidates: list[StaffingCandidateInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_candidates(self):
        ids = [item.candidate_id for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("staffing_candidate_ids_must_be_unique")
        if any(
            len({fact.fact_id for fact in item.evidence_facts}) != len(item.evidence_facts)
            for item in self.candidates
        ):
            raise ValueError("staffing_evidence_fact_ids_must_be_unique")
        return self


class StaffingCandidateRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=3, max_length=500)
    supporting_facts: list[str] = Field(min_length=1, max_length=20)


class StaffingRecommendationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendations: list[StaffingCandidateRecommendation] = Field(min_length=1, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_unique_recommendations(self):
        ids = [item.candidate_id for item in self.recommendations]
        if len(ids) != len(set(ids)):
            raise ValueError("staffing_recommendations_must_be_unique")
        return self
