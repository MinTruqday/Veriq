from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.modules.projects.services.project_completeness import (
    get_latest_project_completeness,
    get_project_completeness_scope,
    review_project_completeness,
)
from src.schemas.project_completeness import ProjectCompletenessInput


router = APIRouter(prefix="/kiem-thu", tags=["Hồ sơ dự án"])


@router.get("/du-an/{project_id}/ho-so-ai/pham-vi")
async def completeness_scope(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_project_completeness_scope(project_id, user))


@router.get("/du-an/{project_id}/ho-so-ai")
async def latest_completeness_review(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_latest_project_completeness(project_id, user))


@router.post("/du-an/{project_id}/ho-so-ai/ra-soat")
async def completeness_review(project_id: str, payload: ProjectCompletenessInput, user: CurrentUser = Depends(get_current_user)):
    return envelope(await review_project_completeness(project_id, user, payload))
