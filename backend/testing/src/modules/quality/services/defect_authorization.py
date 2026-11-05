from fastapi import HTTPException

from src.core.common import get_project_roles


async def require_defect_editor_assignment(defect, user):
    roles = await get_project_roles(defect["project_id"], user.id)
    if "DEVELOPER" in roles and defect.get("assignee") != user.id:
        raise HTTPException(403, detail={"code": "ASSIGNED_DEVELOPER_REQUIRED"})
    return roles
