from fastapi import HTTPException
import re

from pydantic import RootModel, ValidationError, field_validator

from src.core.auth import access_policy, permissions_for_role, roles_for_membership
from src.repositories.common import common_repository


class ProjectResponsibilities(RootModel[dict[str, str | None]]):
    @field_validator("root")
    @classmethod
    def validate_entries(cls, value):
        if any(
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,79}", name)
            for name in value
        ):
            raise ValueError("PROJECT_RESPONSIBILITY_INVALID")
        return value


def assignable_responsibilities(membership):
    if not membership or membership.get("status") != "ACTIVE":
        return []
    roles = roles_for_membership(membership)
    policy = access_policy()
    responsibility_permissions = policy.get("responsibility_permissions", {})
    permissions = set().union(
        *(permissions_for_role(role) for role in roles)
    ) if roles else set()
    assignable = set()
    for permission, responsibility in responsibility_permissions.items():
        if permission in permissions:
            assignable.add(responsibility)
    return sorted(assignable)


async def validate_project_responsibilities(settings_value, project_id=None, initial_members=None):
    if "responsibilities" not in settings_value:
        return
    try:
        responsibilities = ProjectResponsibilities.model_validate(settings_value["responsibilities"])
    except ValidationError as error:
        raise HTTPException(422, detail={"code": "PROJECT_RESPONSIBILITIES_INVALID"}) from error
    for responsibility, user_id in responsibilities.root.items():
        if user_id is None:
            continue
        if not user_id.strip() or len(user_id) > 320:
            raise HTTPException(422, detail={"code": "PROJECT_RESPONSIBLE_MEMBER_INVALID"})
        membership = (initial_members or {}).get(user_id) if initial_members is not None else await common_repository.find_membership(project_id, user_id, status="ACTIVE")
        if responsibility not in assignable_responsibilities(membership):
            raise HTTPException(422, detail={"code": "PROJECT_RESPONSIBLE_MEMBER_INVALID", "responsibility": responsibility})
