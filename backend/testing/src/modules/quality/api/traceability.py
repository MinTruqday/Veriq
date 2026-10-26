from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.design import CoverageSnapshotCreate, TraceLinkCreate
from src.modules.quality.services.traceability import TraceabilityService

router = APIRouter(prefix="/kiem-thu", tags=["Truy vết kiểm thử"])


@router.post("/lien-ket-truy-vet", status_code=201)
@router.post("/du-an/{project_id}/lien-ket-truy-vet", status_code=201)
async def create_trace_link(
    payload: TraceLinkCreate,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await TraceabilityService.create_link(payload, project_id, user))


@router.post("/lien-ket-truy-vet/{link_id}/xac-nhan")
@router.post("/du-an/{project_id}/lien-ket-truy-vet/{link_id}/xac-nhan")
async def confirm_trace_link(
    link_id: str,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await TraceabilityService.confirm_link(link_id, user, project_id))


@router.get("/lien-ket-truy-vet/{link_id}")
async def get_trace_link(link_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await TraceabilityService.get_link(link_id, user))


@router.post("/lien-ket-truy-vet/{link_id}/tu-choi")
@router.post("/du-an/{project_id}/lien-ket-truy-vet/{link_id}/tu-choi")
async def reject_trace_link(
    link_id: str,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await TraceabilityService.reject_link(link_id, user, project_id))


@router.delete("/lien-ket-truy-vet/{link_id}")
@router.delete("/du-an/{project_id}/lien-ket-truy-vet/{link_id}")
async def revoke_trace_link(
    link_id: str,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await TraceabilityService.revoke_link(link_id, project_id, user))


@router.get("/du-an/{project_id}/truy-vet")
async def traceability(
    project_id: str,
    requirement_version_id: str | None = Query(default=None, max_length=200),
    requirement_version_ids: list[str] = Query(default=[], max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await TraceabilityService.matrix(
            project_id, user, requirement_version_id, requirement_version_ids
        )
    )


@router.get("/du-an/{project_id}/do-phu")
async def coverage(
    project_id: str,
    build: str = Query(default="", max_length=200),
    build_id: str = Query(default="", max_length=200),
    release: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await TraceabilityService.coverage(
            project_id, build, build_id, release, release_id, user
        )
    )


@router.get("/yeu-cau/{requirement_id}/do-phu")
async def requirement_coverage(
    requirement_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await TraceabilityService.requirement_coverage(requirement_id, user))


@router.get("/du-an/{project_id}/anh-chup-do-phu")
async def list_coverage_snapshots(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await TraceabilityService.list_snapshots(project_id, limit, user))


@router.post("/du-an/{project_id}/anh-chup-do-phu", status_code=201)
async def create_coverage_snapshot(
    project_id: str,
    payload: CoverageSnapshotCreate,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await TraceabilityService.create_snapshot(project_id, payload, user))


@router.get("/ca-kiem-thu/{test_case_id}/truy-vet")
async def test_case_trace(test_case_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await TraceabilityService.test_case_trace(test_case_id, user))


@router.get("/du-an/{project_id}/truy-vet/xuat")
async def export_traceability(project_id: str, user: CurrentUser = Depends(get_current_user)):
    content, filename = await TraceabilityService.export(project_id, user)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
