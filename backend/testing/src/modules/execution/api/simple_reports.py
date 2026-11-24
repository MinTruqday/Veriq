import asyncio
import io
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, get_project, get_project_permissions, now
from src.core.database import database
from src.modules.execution.services.report_document import convert_report_pdf, export_report_docx, legacy_report_document
from src.modules.execution.services.test_monitoring_snapshot import parse_datetime
from src.modules.execution.services.test_plan import verified_approved_plan_snapshot

router = APIRouter(prefix="/kiem-thu", tags=["Báo cáo kiểm thử"])

class ReportInput(BaseModel):
    preview_hash: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    type: Literal["PROGRESS", "COMPLETION"]
    title: str = Field(min_length=2, max_length=300)
    test_plan_id: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    summary: str = Field(default="", max_length=10000)
    obstacles: str = Field(default="", max_length=10000)
    next_steps: str = Field(default="", max_length=10000)
    evaluation: str = Field(default="", max_length=10000)
    remaining_risks: str = Field(default="", max_length=10000)
    lessons: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def check_period(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None or self.start_at > self.end_at:
            raise ValueError("Kỳ báo cáo không hợp lệ hoặc thiếu múi giờ")
        if self.end_at > datetime.now(timezone.utc):
            raise ValueError("Thời điểm kết thúc không thể ở tương lai")
        return self

async def report_permissions(project_id, user, report_type, write=False):
    prefix = "teststatusreport" if report_type == "PROGRESS" else "testcompletion"
    return await get_project(project_id, user, f"{prefix}.{'create' if write else 'read'}")

async def build_report(project_id, payload, user):
    project = await report_permissions(project_id, user, payload.type, True)
    await get_project(project_id, user, "testplan.read")
    await get_project(project_id, user, "testrun.read")
    plan = await database.value.test_plans.find_one({"_id": payload.test_plan_id, "project_id": project_id})
    if not plan or plan.get("status") != "APPROVED":
        raise HTTPException(422, detail={"code": "INVALID_TEST_PLAN", "message": "Chọn kế hoạch kiểm thử đã duyệt."})
    snapshot, plan_snapshot_hash = verified_approved_plan_snapshot(plan, project_id)
    scope = list(dict.fromkeys(snapshot.get("test_case_version_ids") or []))
    scope_ids = set(scope)
    runs = await database.value.test_runs.find({"project_id": project_id, "test_plan_id": plan["_id"]}).to_list(10001)
    if len(runs) > 10000:
        raise HTTPException(422, detail={"code": "REPORT_SCOPE_TOO_LARGE"})
    excluded_run_count = sum(run.get("test_plan_snapshot_hash") != plan_snapshot_hash for run in runs)
    runs = [run for run in runs if run.get("test_plan_snapshot_hash") == plan_snapshot_hash]
    run_ids = [run["_id"] for run in runs]
    results = await database.value.test_results.find({"project_id": project_id, "test_run_id": {"$in": run_ids}}).to_list(50001)
    if len(results) > 50000:
        raise HTTPException(422, detail={"code": "REPORT_SCOPE_TOO_LARGE"})
    latest = {}
    period_results = []
    for result in results:
        case_id = result.get("test_case_version_id")
        timestamp = parse_datetime(result.get("completed_at") or result.get("executed_at"))
        updated = parse_datetime(result.get("updated_at"))
        created = parse_datetime(result.get("created_at"))
        if case_id in scope_ids and created and created <= payload.end_at and updated and updated > payload.end_at:
            raise HTTPException(409, detail={"code": "REPORT_HISTORICAL_RESULT_CHANGED", "message": "Có kết quả đã thay đổi sau thời điểm kết thúc; không thể dựng chính xác báo cáo kỳ này từ dữ liệu hiện tại."})
        if case_id not in scope_ids or not timestamp or not payload.start_at <= timestamp <= payload.end_at:
            continue
        if result.get("status") not in {"PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_APPLICABLE"}:
            continue
        period_results.append(result)
        rank = (timestamp, str(result.get("_id", "")))
        if case_id not in latest or rank > latest[case_id][0]:
            latest[case_id] = (rank, result)
    counts = {status: 0 for status in ("PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_APPLICABLE", "NOT_RUN")}
    for case in scope:
        counts[latest[case][1]["status"] if case in latest else "NOT_RUN"] += 1
    permissions = await get_project_permissions(project_id, user.id)
    defects = None
    if "defect.read" in permissions:
        result_ids = [item["_id"] for item in period_results]
        defect_ids = [defect_id for item in period_results for defect_id in item.get("linked_defect_ids", [])]
        linked = await database.value.defects.find({"project_id": project_id, "$or": [{"linked_test_result_id": {"$in": result_ids}}, {"_id": {"$in": defect_ids}}]}, {"status": 1}).to_list(50001)
        if len(linked) > 50000:
            raise HTTPException(422, detail={"code": "REPORT_SCOPE_TOO_LARGE"})
        defects = {"total": len(linked), "open": sum(item.get("status") in {"NEW", "CONFIRMED", "IN_PROGRESS", "READY_FOR_RETEST", "REOPENED"} for item in linked)}
    period_run_ids = {result.get("test_run_id") for result in period_results}
    environments = sorted({run.get("environment") for run in runs if run.get("_id") in period_run_ids and run.get("environment")})
    builds = sorted({run.get("build") for run in runs if run.get("_id") in period_run_ids and run.get("build")})
    return {**payload.model_dump(), "project_id": project_id, "project_name": project.get("name") or project_id,
            "plan_name": plan.get("name") or plan["_id"], "objective": snapshot.get("objective") or "",
            "scope_in": snapshot.get("scope_in") or [], "scope_out": snapshot.get("scope_out") or [],
            "exit_criteria": snapshot.get("exit_criteria") or [], "environments": environments, "builds": builds,
            "counts": counts, "total": len(scope), "defects": defects, "plan_snapshot_hash": plan_snapshot_hash, "excluded_run_count": excluded_run_count,
            "pass_rate": round(100 * counts["PASS"] / (counts["PASS"] + counts["FAIL"]), 2) if counts["PASS"] + counts["FAIL"] else None,
            "captured_at": now(), "created_by": user.id}

def report_hash(report):
    data = {key: value for key, value in report.items() if key not in {"_id", "captured_at", "preview_hash", "idempotency_key"}}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

@router.post("/du-an/{project_id}/bao-cao-kiem-thu/xem-truoc")
async def preview(project_id: str, payload: ReportInput, user: CurrentUser = Depends(get_current_user)):
    report = await build_report(project_id, payload, user)
    report["preview_hash"] = report_hash(report)
    return envelope(report)

@router.post("/du-an/{project_id}/bao-cao-kiem-thu", status_code=201)
async def create(project_id: str, payload: ReportInput, user: CurrentUser = Depends(get_current_user)):
    if not payload.preview_hash or not payload.idempotency_key:
        raise HTTPException(422, detail={"code": "REPORT_PREVIEW_REQUIRED", "message": "Xem trước báo cáo trước khi lưu."})
    report_id = "TREP-" + hashlib.sha256(f"{project_id}:{user.id}:{payload.idempotency_key}".encode()).hexdigest()
    existing = await database.value.simple_test_reports.find_one({"_id": report_id, "project_id": project_id})
    if existing:
        await report_permissions(project_id, user, existing["type"], True)
        if existing.get("preview_hash") != payload.preview_hash:
            raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        return envelope(existing)
    report = await build_report(project_id, payload, user)
    if report_hash(report) != payload.preview_hash:
        raise HTTPException(409, detail={"code": "REPORT_SOURCE_CHANGED", "message": "Dữ liệu đã thay đổi sau khi xem trước. Hãy xem trước lại trước khi lưu."})
    report["_id"] = report_id
    try:
        await database.value.simple_test_reports.insert_one(report)
    except Exception as exc:
        from pymongo.errors import DuplicateKeyError
        if not isinstance(exc, DuplicateKeyError): raise
        existing = await database.value.simple_test_reports.find_one({"_id": report_id, "project_id": project_id})
        if not existing or existing.get("preview_hash") != payload.preview_hash: raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        return envelope(existing)
    return envelope(report)

@router.get("/du-an/{project_id}/bao-cao-kiem-thu")
async def list_reports(project_id: str, user: CurrentUser = Depends(get_current_user)):
    permissions = await get_project_permissions(project_id, user.id)
    types = (["PROGRESS"] if "teststatusreport.read" in permissions else []) + (["COMPLETION"] if "testcompletion.read" in permissions else [])
    if not types:
        raise HTTPException(403, detail={"code": "PROJECT_PERMISSION_DENIED"})
    for report_type in types:
        await report_permissions(project_id, user, report_type)
    reports = await database.value.simple_test_reports.find({"project_id": project_id, "type": {"$in": types}}).sort("captured_at", -1).to_list(500)
    if "defect.read" not in permissions:
        for report in reports: report["defects"] = None
    return envelope(reports)

@router.get("/du-an/{project_id}/bao-cao-kiem-thu/{report_id}/xuat")
async def export(project_id: str, report_id: str, format: Literal["pdf", "docx"] = Query(...), user: CurrentUser = Depends(get_current_user)):
    report = await database.value.simple_test_reports.find_one({"_id": report_id, "project_id": project_id})
    if not report: raise HTTPException(404, detail={"code": "REPORT_NOT_FOUND"})
    await report_permissions(project_id, user, report["type"])
    await get_project(project_id, user, "report.export")
    permissions = await get_project_permissions(project_id, user.id)
    counts = report["counts"]
    rows = [("Dự án", report["project_name"]), ("Kế hoạch kiểm thử", report["plan_name"]),
            ("Kỳ báo cáo", f'{report["start_at"].isoformat()} – {report["end_at"].isoformat()}'),
            ("Thời điểm lưu", report["captured_at"].isoformat()), ("Mục tiêu", report["objective"] or "-"),
            ("Phạm vi kiểm thử", "\n".join(report["scope_in"]) or "-")]
    if report.get("excluded_run_count"):
        rows.append(("Lần chạy không thuộc phiên bản kế hoạch hiện tại", str(report["excluded_run_count"])))
    if report.get("scope_out"): rows.append(("Ngoài phạm vi", "\n".join(report["scope_out"])))
    if report.get("environments"): rows.append(("Môi trường", ", ".join(report["environments"])))
    if report.get("builds"): rows.append(("Bản dựng", ", ".join(report["builds"])))
    if report.get("exit_criteria") and report["type"] == "COMPLETION":
        rows.append(("Tiêu chí kết thúc", "\n".join(report["exit_criteria"])))
    rows.extend([("Kết quả", f'Tổng: {report["total"]}; Đạt: {counts["PASS"]}; Thất bại: {counts["FAIL"]}; Bị chặn: {counts["BLOCKED"]}; Bỏ qua: {counts["SKIPPED"]}; Không áp dụng: {counts["NOT_APPLICABLE"]}; Chưa ghi nhận trong kỳ: {counts["NOT_RUN"]}'),
            ("Tỷ lệ đạt (Đạt / (Đạt + Thất bại))", f'{report["pass_rate"]}%' if report.get("pass_rate") is not None else "Chưa đủ dữ liệu"),
            ("Cách tính", "Kết quả đã ghi nhận mới nhất của mỗi ca trong kỳ báo cáo; không cộng các lần chạy lại.")])
    if report.get("defects") is not None and "defect.read" in permissions:
        rows.append(("Lỗi liên kết", f'{report["defects"]["total"]} lỗi, {report["defects"]["open"]} lỗi đang mở tại thời điểm lập báo cáo'))
    for key, label in (("summary", "Nhận xét"), ("obstacles", "Trở ngại và xử lý"), ("next_steps", "Công việc tiếp theo"), ("evaluation", "Đánh giá"), ("remaining_risks", "Rủi ro còn lại"), ("lessons", "Bài học kinh nghiệm")):
        if report.get(key): rows.append((label, report[key]))
    document = legacy_report_document(report, rows, report["title"])
    content = await asyncio.to_thread(export_report_docx, document)
    if format == "pdf": content = await asyncio.to_thread(convert_report_pdf, content)
    media = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return StreamingResponse(io.BytesIO(content), media_type=media, headers={"Content-Disposition": f'attachment; filename="test-report-{report_id}.{format}"'})
