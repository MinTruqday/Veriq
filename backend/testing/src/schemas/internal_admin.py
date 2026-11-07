from pydantic import BaseModel, Field


class ProjectStatusChange(BaseModel):
    status: str = Field(pattern="^(ACTIVE|SUSPENDED)$")
    reason: str
    actor_id: str


class ProjectQuotaChange(BaseModel):
    quota: dict
    actor_id: str


class ProjectDelete(BaseModel):
    confirmation: str


class BreakGlassGrant(BaseModel):
    project_id: str
    user_id: str
    permissions: list[str]
    reason: str
    actor_id: str
    ttl_minutes: int = Field(ge=5, le=240)


class BreakGlassRevoke(BaseModel):
    reason: str
    actor_id: str


class ReindexCandidates(BaseModel):
    project_id: str
    artifact_version_ids: list[str] = Field(default_factory=list)
