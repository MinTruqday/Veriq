from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.modules.execution.services.test_period import (
    create_test_period_record,
    close_test_period_record,
    get_test_period_record,
    get_test_period_summary,
    list_test_period_records,
    update_test_period_record,
)
from src.schemas.contracts.test_period import TestPeriodCloseInput, TestPeriodCreate, TestPeriodPatch

router = APIRouter(prefix="/kiem-thu", tags=["Đợt kiểm thử"])


@router.get("/du-an/{project_id}/chu-ky-kiem-thu")
async def list_test_periods(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await list_test_period_records(project_id, user))


@router.post("/chu-ky-kiem-thu", status_code=201)
async def create_test_period(
    payload: TestPeriodCreate, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await create_test_period_record(payload, user), revision=1)


@router.get("/chu-ky-kiem-thu/{period_id}")
async def get_test_period(period_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_test_period_record(period_id, user))


@router.get("/chu-ky-kiem-thu/{period_id}/tong-ket")
async def test_period_summary(period_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_test_period_summary(period_id, user))


@router.post("/chu-ky-kiem-thu/{period_id}/dong")
async def close_test_period(
    period_id: str,
    payload: TestPeriodCloseInput,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await close_test_period_record(period_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.patch("/chu-ky-kiem-thu/{period_id}")
async def update_test_period(
    period_id: str, payload: TestPeriodPatch, user: CurrentUser = Depends(get_current_user)
):
    updated = await update_test_period_record(period_id, payload, user)
    return envelope(updated, revision=updated["revision"])


