from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from src.core.dependency import require_system_admin
from src.runtime.queue_names import DEAD_LETTER_QUEUE
from src.schemas.auth import CurrentUser
from src.schemas.queue_recovery import DeadLetterRedriveRequest
from src.services.dead_letter_recovery import dead_letter_recovery

router = APIRouter(prefix="/hang-chet", tags=["Queue Recovery"])


@router.get("", dependencies=[Depends(require_system_admin)])
async def dead_letter_status():
    return {
        "queue": DEAD_LETTER_QUEUE,
        "pending_messages": await dead_letter_recovery.depth(),
    }


@router.get("/nhat-ky", dependencies=[Depends(require_system_admin)])
async def dead_letter_audit(limit: int = Query(default=50, ge=1, le=200)):
    return {"actions": await dead_letter_recovery.list_audit(limit=limit)}


@router.post("/phat-lai", dependencies=[Depends(require_system_admin)])
async def redrive_dead_letters(
    req: DeadLetterRedriveRequest,
    current_user: CurrentUser = Depends(require_system_admin),
):
    try:
        return await dead_letter_recovery.redrive(
            limit=req.limit,
            requested_by=str(current_user.id),
        )
    except Exception as error:
        logger.error("Dead-letter redrive failed error_type={}", type(error).__name__)
        raise HTTPException(
            status_code=503,
            detail={"code": "DEAD_LETTER_REDRIVE_UNAVAILABLE"},
        ) from error
