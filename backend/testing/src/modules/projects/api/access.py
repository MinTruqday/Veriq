from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel, Field

from src.core.auth import CurrentUser, access_policy, get_current_user, refresh_access_policy
from src.core.common import audit, envelope
from src.core.database import database
from src.schemas.project_access import ProjectAccessControl
from src.modules.projects.services.effective_access import get_effective_project_access


router = APIRouter(prefix="/kiem-thu", tags=["Quyền dự án"])
SUPPORTED_PROJECT_ROLES = {"BA", "TESTER", "SYSTEM_ADMIN"}


@router.get("/quan-tri/vai-tro-du-an")
async def project_role_permissions(user: CurrentUser = Depends(get_current_user)):
    if not user.is_system_admin:
        raise HTTPException(status_code=403, detail={"code": "SYSTEM_ADMIN_REQUIRED"})
    policy = access_policy()
    return envelope({"role_permissions": policy.get("role_permissions", {}), "permissions": policy.get("project_permissions", []), "revision": policy["revision"]})


class RolePermissionsUpdate(BaseModel):
    revision: int = Field(ge=1)
    role_permissions: dict[str, list[str]]


@router.put("/quan-tri/vai-tro-du-an")
async def update_project_role_permissions(payload: RolePermissionsUpdate, user: CurrentUser = Depends(get_current_user)):
    if not user.is_system_admin:
        raise HTTPException(status_code=403, detail={"code": "SYSTEM_ADMIN_REQUIRED"})
    document = await database.value.project_access_control.find_one({"_id": "active"})
    if not document or document.get("revision", 1) != payload.revision:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    access = ProjectAccessControl.model_validate({key: document[key] for key in ProjectAccessControl.model_fields if key in document})
    if set(payload.role_permissions) != SUPPORTED_PROJECT_ROLES or set(payload.role_permissions) != {grant.role for grant in access.role_grants}:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_ROLES_MISMATCH"})
    fields = access.model_dump()
    fields["role_grants"] = [{"role": grant.role, "permissions": payload.role_permissions[grant.role]} for grant in access.role_grants]
    fields["revision"] = payload.revision + 1
    try:
        updated = ProjectAccessControl.model_validate(fields)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "INVALID_PROJECT_PERMISSIONS"}) from error
    result = await database.value.project_access_control.update_one({"_id": "active", "revision": payload.revision}, {"$set": {**updated.model_dump(), "role_grants_managed_by_admin": True}})
    if not result.modified_count:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    refresh_access_policy()
    await audit(user.id, "project_role_permissions_updated", "ProjectAccessControl", "active", None, {"revision": updated.revision})
    return envelope({"role_permissions": updated.permission_values()["role_permissions"], "permissions": updated.permission_values()["project_permissions"], "revision": updated.revision})


@router.get("/du-an/{project_id}/quyen-hieu-luc")
async def effective_project_access(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    value = await get_effective_project_access(project_id, user)
    return envelope(value, revision=value.get("project_revision"))
