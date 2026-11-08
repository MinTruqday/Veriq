from fastapi import HTTPException

from src.core.auth import (
    access_policy,
    archive_read_permissions,
    permissions_for_membership,
    roles_for_membership,
)
from src.core.common import get_project
from src.core.project_settings import resolve_project_settings
from src.repositories.common import common_repository


def explain_project_access(project, membership, user_id):
    values = access_policy()
    settings = resolve_project_settings(project.get("settings"))
    responsibilities = settings.get("responsibilities") or {}
    responsibility_permissions = values.get("responsibility_permissions", {})
    roles = roles_for_membership(membership)
    permissions = permissions_for_membership(membership, settings)
    archived = str(project.get("status", "active")).lower() == "archived"
    archived_permissions = archive_read_permissions()
    capabilities = []
    allowed = []
    for permission in sorted(values.get("project_permissions", [])):
        responsibility = responsibility_permissions.get(permission)
        reason = None
        if responsibility and responsibilities.get(responsibility) != user_id:
            reason = "RESPONSIBILITY_NOT_ASSIGNED"
        elif permission not in permissions:
            reason = "PERMISSION_NOT_GRANTED"
        elif archived and permission not in archived_permissions and permission != "project.restore":
            reason = "PROJECT_ARCHIVED"
        elif (
            archived
            and permission in archived_permissions
            and permission != "project.read"
            and settings["read_after_archive_policy"] == "DENY_READ"
        ):
            reason = "PROJECT_ARCHIVED_READ_DENIED"
        if reason is None:
            allowed.append(permission)
        capabilities.append({
            "permission": permission,
            "allowed": reason is None,
            "reason_code": reason,
            "responsibility": responsibility,
        })
    return {
        "project_id": project["_id"],
        "project_revision": project.get("revision"),
        "roles": sorted(roles),
        "scope": "PROJECT_CAPABILITY",
        "object_checks_required": True,
        "permissions": allowed,
        "capabilities": capabilities,
        "responsibilities": [
            {
                "name": name,
                "configured": bool(responsibilities.get(name)),
                "assigned_to_you": responsibilities.get(name) == user_id,
            }
            for name in sorted(set(responsibility_permissions.values()))
        ],
    }


async def get_effective_project_access(project_id, user):
    project = await get_project(project_id, user, "project.read")
    membership = await common_repository.find_membership(
        project_id,
        user.id,
        status="ACTIVE",
        projection={"user_id": 1, "project_role": 1, "project_roles": 1, "status": 1},
    )
    if not membership:
        raise HTTPException(status_code=403, detail={"code": "PROJECT_MEMBERSHIP_REQUIRED"})
    if not roles_for_membership(membership):
        raise HTTPException(status_code=403, detail={"code": "PROJECT_PERMISSION_DENIED"})
    return explain_project_access(project, membership, user.id)
