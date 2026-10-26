from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.modules.execution.services.test_completion import (
    add_completion_lesson,
    add_completion_residual_risk,
    cluster_completion_lessons,
    create_completion_report,
    decide_residual_risk,
    generate_completion_narrative,
    get_completion_for_user,
    latest_completion_ai_result,
    list_completion_reports,
    manage_completion_handover,
    sign_off_completion,
    transition_completion,
    update_completion_report,
)
from src.modules.execution.services.test_completion_export import export_completion_report
from src.schemas.test_completion import (
    CompletionSignOff,
    CompletionTransition,
    LessonLearnedCreate,
    ResidualRiskCreate,
    ResidualRiskDecision,
    TestCompletionAiDraft,
    TestCompletionCreate,
    TestCompletionPatch,
    TestwareHandoverManage,
)

router = APIRouter(prefix="/kiem-thu", tags=["Hoàn tất kiểm thử"])


@router.get("/du-an/{project_id}/hoan-tat-kiem-thu")
async def list_test_completion_reports(
    project_id: str,
    release_id: str = Query(default="", max_length=200),
    status: str = Query(default="", pattern="^(DRAFT|IN_REVIEW|APPROVED|CLOSED)?$"),
    limit: int = Query(default=200, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_completion_reports(project_id, release_id or None, status or None, limit, user)
    )


@router.post("/du-an/{project_id}/hoan-tat-kiem-thu", status_code=201)
async def create_test_completion_report(
    project_id: str, payload: TestCompletionCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await create_completion_report(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/hoan-tat-kiem-thu/{report_id}")
async def get_test_completion_report(report_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await get_completion_for_user(report_id, user)
    return envelope(value, revision=value["revision"])


@router.patch("/hoan-tat-kiem-thu/{report_id}")
async def patch_test_completion_report(
    report_id: str, payload: TestCompletionPatch, user: CurrentUser = Depends(get_current_user)
):
    value = await update_completion_report(report_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/hoan-tat-kiem-thu/{report_id}/rui-ro", status_code=201)
async def add_test_completion_residual_risk(
    report_id: str, payload: ResidualRiskCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await add_completion_residual_risk(report_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/hoan-tat-kiem-thu/{report_id}/bai-hoc", status_code=201)
async def add_test_completion_lesson(
    report_id: str, payload: LessonLearnedCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await add_completion_lesson(report_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.put("/hoan-tat-kiem-thu/{report_id}/ban-giao")
async def manage_test_completion_handover(
    report_id: str, payload: TestwareHandoverManage, user: CurrentUser = Depends(get_current_user)
):
    value = await manage_completion_handover(report_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/hoan-tat-kiem-thu/{report_id}/ai/ban-nhap")
async def draft_test_completion_narrative(
    report_id: str, payload: TestCompletionAiDraft, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await generate_completion_narrative(report_id, payload, user))


@router.post("/hoan-tat-kiem-thu/{report_id}/ai/gom-bai-hoc")
async def cluster_test_completion_lessons(
    report_id: str, payload: TestCompletionAiDraft, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await cluster_completion_lessons(report_id, payload, user))


@router.get("/hoan-tat-kiem-thu/{report_id}/ai/ban-nhap")
async def get_test_completion_narrative(
    report_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(
        await latest_completion_ai_result(report_id, "COMPLETION_REPORT_NARRATIVE", user)
    )


@router.get("/hoan-tat-kiem-thu/{report_id}/ai/gom-bai-hoc")
async def get_test_completion_lesson_clusters(
    report_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(
        await latest_completion_ai_result(report_id, "LESSONS_LEARNED_CLUSTERING", user)
    )


@router.post("/hoan-tat-kiem-thu/{report_id}/gui-ra-soat")
async def submit_test_completion_review(
    report_id: str, payload: CompletionTransition, user: CurrentUser = Depends(get_current_user)
):
    value = await transition_completion(report_id, payload, user, "submit_review")
    return envelope(value, revision=value["revision"])


@router.post("/hoan-tat-kiem-thu/{report_id}/yeu-cau-chinh-sua")
async def request_test_completion_changes(
    report_id: str, payload: CompletionTransition, user: CurrentUser = Depends(get_current_user)
):
    value = await transition_completion(report_id, payload, user, "request_changes")
    return envelope(value, revision=value["revision"])


@router.post("/hoan-tat-kiem-thu/{report_id}/ky-xac-nhan")
async def sign_off_test_completion(
    report_id: str, payload: CompletionSignOff, user: CurrentUser = Depends(get_current_user)
):
    value = await sign_off_completion(report_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/hoan-tat-kiem-thu/{report_id}/rui-ro/{risk_id}/xu-ly")
async def decide_test_completion_residual_risk(
    report_id: str,
    risk_id: str,
    payload: ResidualRiskDecision,
    user: CurrentUser = Depends(get_current_user),
):
    value = await decide_residual_risk(report_id, risk_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/hoan-tat-kiem-thu/{report_id}/phe-duyet")
async def approve_test_completion_report(
    report_id: str, payload: CompletionTransition, user: CurrentUser = Depends(get_current_user)
):
    value = await transition_completion(report_id, payload, user, "approve")
    return envelope(value, revision=value["revision"])


@router.post("/hoan-tat-kiem-thu/{report_id}/dong")
async def close_test_completion_report(
    report_id: str, payload: CompletionTransition, user: CurrentUser = Depends(get_current_user)
):
    value = await transition_completion(report_id, payload, user, "close")
    return envelope(value, revision=value["revision"])


@router.get("/hoan-tat-kiem-thu/{report_id}/xuat")
async def export_test_completion_report(
    report_id: str,
    format: str = Query(default="pdf", pattern="^(pdf|docx|csv)$"),
    user: CurrentUser = Depends(get_current_user),
):
    report = await get_completion_for_user(report_id, user, "report.export")
    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "csv": "text/csv; charset=utf-8",
    }
    content = export_completion_report(report, format)
    return StreamingResponse(
        iter([content]),
        media_type=media_types[format],
        headers={
            "Content-Disposition": f'attachment; filename="test-completion-{report_id}.{format}"'
        },
    )
