from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.modules.execution.services.test_plan_progress import get_live_plan_progress

router = APIRouter(prefix="/kiem-thu", tags=["Tiến độ kế hoạch"])


@router.get("/du-an/{project_id}/ke-hoach-kiem-thu/{plan_id}/tien-do")
async def get_plan_progress(
    project_id: str,
    plan_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await get_live_plan_progress(project_id, plan_id, user))
