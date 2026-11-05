from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError

from src.core.auth import roles_for_membership
from src.repositories.common import common_repository


class ProjectResponsibilities(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business_confirmation: str | None = None
    release_decision: str | None = None


async def validate_project_responsibilities(settings_value, project_id=None, initial_members=None):
    if "responsibilities" not in settings_value:
        return
    try:
        responsibilities = ProjectResponsibilities.model_validate(settings_value["responsibilities"])
    except ValidationError as error:
        raise HTTPException(422, detail={"code": "PROJECT_RESPONSIBILITIES_INVALID"}) from error
    for responsibility, user_id in responsibilities.model_dump().items():
        if user_id is None:
            continue
        if not user_id.strip() or len(user_id) > 320:
            raise HTTPException(422, detail={"code": "PROJECT_RESPONSIBLE_MEMBER_INVALID"})
        membership = (initial_members or {}).get(user_id) if initial_members is not None else await common_repository.find_membership(project_id, user_id, status="ACTIVE")
        allowed = {"BA"} if responsibility == "business_confirmation" else {"BA", "QA"}
        if not membership or membership.get("status") != "ACTIVE" or not roles_for_membership(membership).intersection(allowed):
            raise HTTPException(422, detail={"code": "PROJECT_RESPONSIBLE_MEMBER_INVALID", "responsibility": responsibility})
