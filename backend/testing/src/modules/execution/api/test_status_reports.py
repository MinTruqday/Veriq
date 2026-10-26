from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.modules.execution.services.test_status_report import (
    attach_status_report_evidence,
    compare_status_reports,
    generate_status_report,
    generate_status_report_narrative,
    get_report_for_user,
    latest_status_report_narrative,
    list_status_reports,
    transition_status_report,
    update_status_report,
)
from src.modules.execution.services.test_status_report_export import export_status_report
from src.schemas.test_status_report import (
    TestStatusReportAiDraft,
    TestStatusReportEvidence,
    TestStatusReportGenerate,
    TestStatusReportPatch,
    TestStatusReportTransition,
)

router = APIRouter(prefix="/kiem-thu", tags=["Báo cáo trạng thái kiểm thử"])


@router.get("/du-an/{project_id}/bao-cao-trang-thai")
async def list_test_status_reports(
    project_id: str,
    test_plan_id: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    status: str = Query(default="", pattern="^(DRAFT|IN_REVIEW|APPROVED|PUBLISHED|ARCHIVED)?$"),
    limit: int = Query(default=200, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_status_reports(
            project_id, test_plan_id or None, release_id or None, status or None, limit, user
        )
    )


@router.post("/du-an/{project_id}/bao-cao-trang-thai/tao-tu-anh-chup", status_code=201)
async def generate_test_status_report(
    project_id: str,
    payload: TestStatusReportGenerate,
    user: CurrentUser = Depends(get_current_user),
):
    value = await generate_status_report(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/bao-cao-trang-thai/{report_id}")
async def get_test_status_report(report_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await get_report_for_user(report_id, user)
    return envelope(value, revision=value["revision"])


@router.patch("/bao-cao-trang-thai/{report_id}")
async def patch_test_status_report(
    report_id: str, payload: TestStatusReportPatch, user: CurrentUser = Depends(get_current_user)
):
    value = await update_status_report(report_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/bao-cao-trang-thai/{report_id}/ai/ban-nhap")
async def draft_test_status_report_narrative(
    report_id: str, payload: TestStatusReportAiDraft, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await generate_status_report_narrative(report_id, payload, user))


@router.get("/bao-cao-trang-thai/{report_id}/ai/ban-nhap")
async def get_test_status_report_ai_narrative(
    report_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await latest_status_report_narrative(report_id, user))


@router.post("/bao-cao-trang-thai/{report_id}/bang-chung")
async def attach_test_status_report_evidence(
    report_id: str, payload: TestStatusReportEvidence, user: CurrentUser = Depends(get_current_user)
):
    value = await attach_status_report_evidence(report_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/bao-cao-trang-thai/{report_id}/gui-ra-soat")
async def submit_test_status_report_review(
    report_id: str,
    payload: TestStatusReportTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_status_report(report_id, payload, user, "submit")
    return envelope(value, revision=value["revision"])


@router.post("/bao-cao-trang-thai/{report_id}/yeu-cau-chinh-sua")
async def request_test_status_report_changes(
    report_id: str,
    payload: TestStatusReportTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_status_report(report_id, payload, user, "request_changes")
    return envelope(value, revision=value["revision"])


@router.post("/bao-cao-trang-thai/{report_id}/phe-duyet")
async def approve_test_status_report(
    report_id: str,
    payload: TestStatusReportTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_status_report(report_id, payload, user, "approve")
    return envelope(value, revision=value["revision"])


@router.post("/bao-cao-trang-thai/{report_id}/phat-hanh")
async def publish_test_status_report(
    report_id: str,
    payload: TestStatusReportTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_status_report(report_id, payload, user, "publish")
    return envelope(value, revision=value["revision"])


@router.post("/bao-cao-trang-thai/{report_id}/luu-tru")
async def archive_test_status_report(
    report_id: str,
    payload: TestStatusReportTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_status_report(report_id, payload, user, "archive")
    return envelope(value, revision=value["revision"])


@router.get("/bao-cao-trang-thai/{report_id}/so-sanh")
async def compare_test_status_report(
    report_id: str,
    other_report_id: str = Query(min_length=1, max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await compare_status_reports(report_id, other_report_id, user))


@router.get("/bao-cao-trang-thai/{report_id}/xuat")
async def export_test_status_report(
    report_id: str,
    format: str = Query(default="pdf", pattern="^(pdf|docx|csv)$"),
    user: CurrentUser = Depends(get_current_user),
):
    report = await get_report_for_user(report_id, user, "report.export")
    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "csv": "text/csv; charset=utf-8",
    }
    content = export_status_report(report, format)
    return StreamingResponse(
        iter([content]),
        media_type=media_types[format],
        headers={
            "Content-Disposition": f'attachment; filename="test-status-report-{report_id}.{format}"'
        },
    )
