from fastapi import APIRouter, Depends, Query

from src.core.internal import require_internal_token
from src.schemas.internal_admin import (
    BreakGlassGrant,
    BreakGlassRevoke,
    ProjectDelete,
    ProjectQuotaChange,
    ProjectStatusChange,
    ReindexCandidates,
)
from src.modules.operations.services.internal_admin import InternalAdminService

router = APIRouter(
    prefix="/kiem-thu/noi-bo/quan-tri",
    tags=["Quản trị nội bộ kiểm thử"],
    dependencies=[Depends(require_internal_token)],
)


@router.get("/nguoi-dung/{user_id}/thanh-vien")
async def user_memberships(user_id: str):
    return await InternalAdminService.user_memberships(user_id)


@router.get("/du-an")
async def projects(
    search: str = Query(default="", max_length=200),
    status: str = Query(default="", max_length=30),
    limit: int = Query(default=200, ge=1, le=1000),
):
    return await InternalAdminService.projects(search, status, limit)


@router.get("/du-an/{project_id}")
async def project(project_id: str):
    return await InternalAdminService.project(project_id)


@router.patch("/du-an/{project_id}/trang-thai")
async def change_project_status(project_id: str, payload: ProjectStatusChange):
    return await InternalAdminService.change_status(project_id, payload)


@router.patch("/du-an/{project_id}/han-muc")
async def change_project_quota(project_id: str, payload: ProjectQuotaChange):
    return await InternalAdminService.change_quota(project_id, payload)


@router.get("/du-an/{project_id}/thanh-vien")
async def project_memberships(project_id: str):
    return await InternalAdminService.project_memberships(project_id)


@router.delete("/du-an/{project_id}")
async def delete_project(project_id: str, payload: ProjectDelete):
    return await InternalAdminService.delete_project(project_id, payload)


@router.get("/truy-cap-khan-cap")
async def break_glass_grants(active_only: bool = True):
    return await InternalAdminService.break_glass_grants(active_only)


@router.post("/truy-cap-khan-cap")
async def create_break_glass_grant(payload: BreakGlassGrant):
    return await InternalAdminService.create_break_glass_grant(payload)


@router.post("/truy-cap-khan-cap/{grant_id}/thu-hoi")
async def revoke_break_glass_grant(grant_id: str, payload: BreakGlassRevoke):
    return await InternalAdminService.revoke_break_glass_grant(grant_id, payload)


@router.get("/so-lieu")
async def operations_metrics():
    return await InternalAdminService.operations_metrics()


@router.get("/rag")
async def rag_status():
    return await InternalAdminService.rag_status()


@router.post("/rag/ung-vien")
async def reindex_candidates(payload: ReindexCandidates):
    return await InternalAdminService.reindex_candidates(payload)


@router.get("/dung-luong-luu-tru")
async def storage_usage():
    return await InternalAdminService.storage_usage()
