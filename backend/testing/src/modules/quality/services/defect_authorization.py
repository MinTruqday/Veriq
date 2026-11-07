from fastapi import HTTPException

from src.core.auth import permissions_for_membership
from src.repositories.common import common_repository


async def require_defect_editor_assignment(defect, user):
    project = await common_repository.find_project(
        defect["project_id"], {"settings": 1}
    )
    membership = await common_repository.find_membership(
        defect["project_id"], user.id, status="ACTIVE"
    )
    permissions = permissions_for_membership(
        membership, (project or {}).get("settings")
    )
    if "defect.triage" not in permissions and defect.get("assignee") != user.id:
        raise HTTPException(403, detail={"code": "DEFECT_ASSIGNMENT_REQUIRED"})
    return permissions
