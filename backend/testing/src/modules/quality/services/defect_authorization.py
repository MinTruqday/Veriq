from fastapi import HTTPException

from src.core.auth import project_membership_permissions
from src.repositories.common import common_repository


async def require_defect_editor_assignment(defect, user, allowed_unassigned_permissions=()):
    project = await common_repository.find_project(
        defect["project_id"], {"settings": 1, "project_lead_user_id": 1}
    )
    membership = await common_repository.find_membership(
        defect["project_id"], user.id, status="ACTIVE"
    )
    permissions = project_membership_permissions(project or {}, membership, user.is_system_admin)
    if (
        "defect.triage" not in permissions
        and defect.get("assignee") != user.id
        and not set(allowed_unassigned_permissions).intersection(permissions)
    ):
        raise HTTPException(403, detail={"code": "DEFECT_ASSIGNMENT_REQUIRED"})
    return permissions
