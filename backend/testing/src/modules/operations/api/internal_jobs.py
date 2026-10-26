from fastapi import APIRouter, Depends, Header, HTTPException

from src.core.common import envelope
from src.core.internal import require_internal_token
from src.modules.operations.services.job_execution import process_delegated_job
from src.repositories.ai_automation_access import ai_automation_access_repository

router = APIRouter(prefix="/kiem-thu/noi-bo/tac-vu", tags=["Tác vụ nội bộ kiểm thử"])


@router.post("/ai-luot-chay/{run_id}/thu-hoi-quyen")
async def revoke_ai_run_access(
    run_id: str,
    _: None = Depends(require_internal_token),
):
    drained = await ai_automation_access_repository.revoke_and_wait(f"run:{run_id}")
    if not drained:
        raise HTTPException(
            status_code=503,
            detail={"code": "AI_AUTOMATION_REQUESTS_STILL_ACTIVE", "retryable": True},
        )
    return envelope({"automation_run_id": run_id, "access_revoked": True, "drained": True})


@router.post("/{event}")
async def process_job(
    event: str,
    body: dict,
    x_requester_id: str = Header(default=""),
    x_requester_email: str = Header(default=""),
    _: None = Depends(require_internal_token),
):
    result = await process_delegated_job(
        event, body, x_requester_id, x_requester_email
    )
    if result.get("status") == "FAILED" and result.get("retryable"):
        raise HTTPException(
            status_code=503,
            detail={
                "code": result.get("error_code") or "DELEGATED_JOB_FAILED",
                "retryable": True,
                "state_after_failure": result.get("state_after_failure"),
            },
        )
    return envelope(result)
