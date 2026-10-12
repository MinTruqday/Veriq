from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.utility import DelegatedJobEnqueueInput
from src.modules.operations.services.delegated_jobs import DelegatedJobService

router = APIRouter(prefix="/kiem-thu", tags=["Tác vụ kiểm thử bất đồng bộ"])


@router.post("/du-an/{project_id}/tac-vu", status_code=202)
async def enqueue_job(
    project_id: str,
    payload: DelegatedJobEnqueueInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await DelegatedJobService.enqueue(project_id, payload, user))


@router.get("/tac-vu/{job_id}")
async def get_job(job_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await DelegatedJobService.get(job_id, user))
