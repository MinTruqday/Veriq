from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.modules.projects.services.effective_access import get_effective_project_access


router = APIRouter(prefix="/kiem-thu", tags=["Quyền dự án"])


@router.get("/du-an/{project_id}/quyen-hieu-luc")
async def effective_project_access(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    value = await get_effective_project_access(project_id, user)
    return envelope(value, revision=value.get("project_revision"))
