from pydantic import BaseModel, ConfigDict, Field


class SecurityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_safe: bool
    risk_score: float = Field(ge=0, le=1)
    threat_category: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_:-]+$",
    )
    reason: str = Field(min_length=1, max_length=2000)
