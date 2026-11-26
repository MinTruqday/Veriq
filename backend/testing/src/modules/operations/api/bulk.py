from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.utility import (
    BulkArchiveInput,
    BulkReviewRequiredInput,
    BulkSuiteInput,
    BulkTagInput,
)
from src.modules.operations.services.bulk_operation import BulkOperationService

router = APIRouter(prefix="/kiem-thu", tags=["Tác vụ kiểm thử hàng loạt"])


@router.post("/du-an/{project_id}/hang-loat/nhan")
async def bulk_tags(
    project_id: str, payload: BulkTagInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await BulkOperationService.tags(project_id, payload, user))


@router.post("/du-an/{project_id}/hang-loat/ca-kiem-thu/them-vao-bo-kiem-thu")
async def bulk_add_to_suite(
    project_id: str, payload: BulkSuiteInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await BulkOperationService.add_to_suite(project_id, payload, user))


@router.post("/du-an/{project_id}/hang-loat/ca-kiem-thu/danh-dau-can-ra-soat")
async def bulk_mark_review_required(
    project_id: str,
    payload: BulkReviewRequiredInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await BulkOperationService.mark_review_required(project_id, payload, user))


@router.post("/du-an/{project_id}/hang-loat/luu-tru")
async def bulk_archive(
    project_id: str, payload: BulkArchiveInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await BulkOperationService.archive(project_id, payload, user))
