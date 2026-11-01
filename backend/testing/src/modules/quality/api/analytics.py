from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, new_id
from src.modules.quality.services.analytics import AnalyticsService
from src.schemas.contracts.utility import ProjectQuestionInput, SearchInput

router = APIRouter(prefix="/kiem-thu", tags=["Phân tích kiểm thử"])


@router.get("/du-an/{project_id}/tim-kiem", openapi_extra={"x-function-ids": ["SRCH-01"]})
async def search_project(
    project_id: str,
    q: str = Query(min_length=1, max_length=1000),
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await AnalyticsService.search(project_id, q, limit, user))


@router.get(
    "/du-an/{project_id}/tong-quan",
    openapi_extra={"x-function-ids": ["PRJ-03", "RPT-01", "RPT-02"]},
)
async def dashboard(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await AnalyticsService.dashboard(project_id, user))


@router.post("/du-an/{project_id}/tri-thuc/tim-kiem")
async def search_knowledge(
    project_id: str, payload: SearchInput, user: CurrentUser = Depends(get_current_user)
):
    data, metadata = await AnalyticsService.search_knowledge(project_id, payload, user)
    return envelope(data, **metadata)


@router.post("/du-an/{project_id}/ai/hoi-dap")
async def ask_project(
    project_id: str, payload: ProjectQuestionInput, user: CurrentUser = Depends(get_current_user)
):
    trace_id = new_id("TRC")
    data, metadata = await AnalyticsService.ask_project(project_id, payload, user, trace_id)
    return envelope(data, trace_id=trace_id, **metadata)


@router.get("/du-an/{project_id}/nhat-ky", openapi_extra={"x-function-ids": ["AUD-01"]})
async def project_audit(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    entity_type: str = Query(default="", max_length=100),
    entity_id: str = Query(default="", max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await AnalyticsService.project_audit(
            project_id, limit, user, entity_type=entity_type, entity_id=entity_id
        )
    )


@router.get("/du-an/{project_id}/phan-tich-bao-tri")
async def maintenance_analytics(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await AnalyticsService.maintenance(project_id, user))


@router.get("/du-an/{project_id}/phan-tich-ai")
async def ai_analytics(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await AnalyticsService.ai(project_id, user))


@router.get("/du-an/{project_id}/bao-cao/thuc-thi")
async def execution_report(
    project_id: str,
    release: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    environment: str = Query(default="", max_length=500),
    environment_id: str = Query(default="", max_length=200),
    build: str = Query(default="", max_length=200),
    build_id: str = Query(default="", max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await AnalyticsService.execution_report(
            project_id, release, release_id, environment, environment_id, build, build_id, user
        )
    )


@router.get("/du-an/{project_id}/bao-cao/loi")
async def defect_report(
    project_id: str,
    release: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    environment: str = Query(default="", max_length=500),
    environment_id: str = Query(default="", max_length=200),
    build: str = Query(default="", max_length=200),
    build_id: str = Query(default="", max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await AnalyticsService.defect_report(
            project_id, release, release_id, environment, environment_id, build, build_id, user
        )
    )


@router.get("/du-an/{project_id}/hoat-dong", openapi_extra={"x-function-ids": ["ACT-01"]})
async def project_activity(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await AnalyticsService.activity(project_id, limit, user))
