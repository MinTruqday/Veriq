from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.design import (
    DataSetArchive,
    DataSetBind,
    DataSetCreate,
    DataSetPreview,
    DataSetVersionCreate,
)
from src.modules.design.services.data_set import DataSetService

router = APIRouter(prefix="/kiem-thu", tags=["Dữ liệu kiểm thử"])


@router.post("/du-an/{project_id}/du-lieu-kiem-thu", status_code=201, openapi_extra={"x-function-ids": ["DATA-02"]})
async def create_data_set(project_id: str, payload: DataSetCreate, user: CurrentUser = Depends(get_current_user)):
    value = await DataSetService.create(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/du-lieu-kiem-thu", openapi_extra={"x-function-ids": ["DATA-01"]})
async def list_data_sets(
    project_id: str,
    q: str = Query(default="", max_length=300),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await DataSetService.list(project_id, q, limit, user))


@router.get("/du-lieu-kiem-thu/{data_set_id}", openapi_extra={"x-function-ids": ["DATA-01"]})
async def get_data_set(data_set_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await DataSetService.get(data_set_id, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-lieu-kiem-thu/{data_set_id}/phien-ban", openapi_extra={"x-function-ids": ["DATA-01"]})
async def list_data_set_versions(data_set_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await DataSetService.list_versions(data_set_id, user))


@router.post("/du-lieu-kiem-thu/{data_set_id}/phien-ban", status_code=201, openapi_extra={"x-function-ids": ["DATA-03"]})
async def create_data_set_version(
    data_set_id: str,
    payload: DataSetVersionCreate,
    user: CurrentUser = Depends(get_current_user),
):
    value, revision = await DataSetService.create_version(data_set_id, payload, user)
    return envelope(value, revision=revision)


@router.post("/du-an/{project_id}/du-lieu-kiem-thu/{data_set_id}/gan-ca-kiem-thu", openapi_extra={"x-function-ids": ["DATA-04"]})
async def bind_data_set(
    project_id: str,
    data_set_id: str,
    payload: DataSetBind,
    user: CurrentUser = Depends(get_current_user),
):
    value = await DataSetService.bind(project_id, data_set_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/du-lieu-kiem-thu/{data_set_id}/xem-truoc", openapi_extra={"x-function-ids": ["DATA-05"]})
async def preview_data_set(
    project_id: str,
    data_set_id: str,
    payload: DataSetPreview,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await DataSetService.preview(project_id, data_set_id, payload, user))


@router.post("/du-an/{project_id}/du-lieu-kiem-thu/{data_set_id}/luu-tru", openapi_extra={"x-function-ids": ["DATA-06"]})
async def archive_data_set(
    project_id: str,
    data_set_id: str,
    payload: DataSetArchive,
    user: CurrentUser = Depends(get_current_user),
):
    value = await DataSetService.archive(project_id, data_set_id, payload, user)
    return envelope(value, revision=value.get("revision", 1))
