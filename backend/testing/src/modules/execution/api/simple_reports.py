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
from src.modules.execution.services.test_plan import verified_approved_plan_snapshot

router = APIRouter(prefix="/kiem-thu", tags=["Báo cáo kiểm thử"])

class ReportInput(BaseModel):
    preview_hash: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    type: Literal["PROGRESS", "COMPLETION"]
    title: str = Field(min_length=2, max_length=300)
    test_plan_id: str = Field(min_length=1, max_length=200)
    test_period_id: str | None = Field(default=None, max_length=200)
    test_run_id: str | None = Field(default=None, max_length=200)
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


def parse_datetime(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

async def report_permissions(project_id, user, report_type, write=False):
    prefix = "teststatusreport" if report_type == "PROGRESS" else "testcompletion"
    return await get_project(project_id, user, f"{prefix}.{'create' if write else 'read'}")

async def build_report(project_id, payload, user, write=True):
    project = await report_permissions(project_id, user, payload.type, write)
    await get_project(project_id, user, "testplan.read")
    await get_project(project_id, user, "testrun.read")
    plan = await database.value.test_plans.find_one({"_id": payload.test_plan_id, "project_id": project_id})
    if not plan or plan.get("status") != "APPROVED":
        raise HTTPException(422, detail={"code": "INVALID_TEST_PLAN", "message": "Chọn kế hoạch kiểm thử đã duyệt."})
    snapshot, plan_snapshot_hash = verified_approved_plan_snapshot(plan, project_id)
    plan_period_id = snapshot.get("test_period_id") or plan.get("test_period_id")
    if payload.test_period_id and payload.test_period_id != plan_period_id:
        raise HTTPException(422, detail={"code": "REPORT_PERIOD_PLAN_MISMATCH"})
    period = None
    if plan_period_id:
        period = await database.value.test_periods.find_one(
            {"_id": plan_period_id, "project_id": project_id}, {"name": 1, "sequence": 1}
        )
        if not period:
            raise HTTPException(409, detail={"code": "REPORT_TEST_PERIOD_MISSING"})
    requirement_version_ids = list(dict.fromkeys(snapshot.get("requirement_version_ids") or []))
    requirement_versions = await database.value.requirement_versions.find(
        {"project_id": project_id, "_id": {"$in": requirement_version_ids}}
    ).to_list(len(requirement_version_ids)) if requirement_version_ids else []
    requirement_records = await database.value.requirements.find(
        {
            "project_id": project_id,
            "_id": {"$in": [item.get("requirement_id") for item in requirement_versions if item.get("requirement_id")]},
        }
    ).to_list(len(requirement_versions)) if requirement_versions else []
    requirements_by_id = {item["_id"]: item for item in requirement_records}
    requirement_scope = []
    for version in requirement_versions:
        requirement = requirements_by_id.get(version.get("requirement_id"), {})
        key = requirement.get("requirement_key") or version.get("requirement_id") or version.get("_id")
        title = version.get("title") or requirement.get("title") or ""
        version_number = version.get("version")
        version_label = f" v{version_number}" if version_number is not None else ""
        requirement_scope.append(" ".join(part for part in [f"{key}{version_label}", title] if part).strip())
    if len(requirement_versions) != len(requirement_version_ids):
        raise HTTPException(409, detail={"code": "REPORT_REQUIREMENT_SCOPE_CHANGED"})
    plan_scope = list(dict.fromkeys(snapshot.get("test_case_version_ids") or []))
    runs = await database.value.test_runs.find({"project_id": project_id, "test_plan_id": plan["_id"]}).to_list(10001)
    if len(runs) > 10000:
        raise HTTPException(422, detail={"code": "REPORT_SCOPE_TOO_LARGE"})
    excluded_run_count = sum(run.get("test_plan_snapshot_hash") != plan_snapshot_hash for run in runs)
    runs = [run for run in runs if run.get("test_plan_snapshot_hash") == plan_snapshot_hash]
    selected_run = None
    if payload.test_run_id:
        selected_run = next((run for run in runs if run.get("_id") == payload.test_run_id), None)
        if not selected_run:
            raise HTTPException(422, detail={"code": "REPORT_RUN_PLAN_MISMATCH"})
        if selected_run.get("test_period_id") != plan_period_id:
            raise HTTPException(409, detail={"code": "REPORT_RUN_PERIOD_MISMATCH"})
        scope = list(dict.fromkeys(selected_run.get("test_case_version_ids") or []))
        if not set(scope).issubset(set(plan_scope)):
            raise HTTPException(409, detail={"code": "REPORT_RUN_SCOPE_CHANGED"})
        runs = [selected_run]
        excluded_run_count = 0
    else:
        scope = plan_scope
    if len(scope) > 5000:
        raise HTTPException(422, detail={"code": "REPORT_SCOPE_TOO_LARGE"})
    scope_ids = set(scope)
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
    case_versions = await database.value.test_case_versions.find(
        {"project_id": project_id, "_id": {"$in": scope}},
        {"test_case_id": 1, "test_case_key": 1, "title": 1, "version": 1},
    ).to_list(len(scope)) if scope else []
    if len(case_versions) != len(scope):
        raise HTTPException(409, detail={"code": "REPORT_CASE_SCOPE_CHANGED"})
    versions_by_id = {item["_id"]: item for item in case_versions}
    runs_by_id = {item["_id"]: item for item in runs}
    case_results = []
    for case_id in scope:
        result = latest[case_id][1] if case_id in latest else None
        run = runs_by_id.get(result.get("test_run_id")) if result else None
        version = versions_by_id[case_id]
        case_results.append({
            "test_case_version_id": case_id,
            "test_case_id": version.get("test_case_id"),
            "test_case_key": version.get("test_case_key") or version.get("test_case_id") or case_id,
            "title": version.get("title") or "Ca kiểm thử",
            "version": version.get("version"),
            "status": result.get("status") if result else "NOT_RUN",
            "test_run_id": run.get("_id") if run else None,
            "test_run_name": run.get("name") if run else "",
            "test_result_id": result.get("_id") if result else None,
            "executed_at": (result.get("completed_at") or result.get("executed_at")) if result else None,
        })
    permissions = await get_project_permissions(project_id, user.id)
    defects = None
    if "defect.read" in permissions:
        result_ids = [item["_id"] for item in period_results]
        defect_ids = [defect_id for item in period_results for defect_id in item.get("linked_defect_ids", [])]
        linked = await database.value.defects.find(
            {"project_id": project_id, "$or": [{"linked_test_result_id": {"$in": result_ids}}, {"_id": {"$in": defect_ids}}]},
            {"defect_key": 1, "title": 1, "status": 1, "severity": 1, "linked_test_result_id": 1},
        ).to_list(5001)
        if len(linked) > 5000:
            raise HTTPException(422, detail={"code": "REPORT_SCOPE_TOO_LARGE"})
        result_by_id = {item["_id"]: item for item in period_results}
        run_by_id = {item["_id"]: item for item in runs}
        source_by_defect = {}
        for result in period_results:
            for defect_id in result.get("linked_defect_ids", []):
                source_by_defect.setdefault(defect_id, result)
        open_statuses = {"NEW", "CONFIRMED", "IN_PROGRESS", "READY_FOR_RETEST", "REOPENED"}
        defect_items = []
        for item in linked:
            source_result = result_by_id.get(item.get("linked_test_result_id")) or source_by_defect.get(item["_id"])
            source_run = run_by_id.get(source_result.get("test_run_id")) if source_result else None
            defect_items.append({
                "defect_id": item["_id"],
                "defect_key": item.get("defect_key") or item["_id"],
                "title": item.get("title") or "Lỗi chưa có tiêu đề",
                "status": item.get("status"),
                "severity": item.get("severity"),
                "linked_test_result_id": item.get("linked_test_result_id"),
                "source_test_result_id": source_result.get("_id") if source_result else None,
                "source_test_case_version_id": source_result.get("test_case_version_id") if source_result else None,
                "source_test_run_id": source_result.get("test_run_id") if source_result else None,
                "source_test_run_name": source_run.get("name", "") if source_run else "",
            })
        defects = {
            "total": len(linked),
            "open": sum(item.get("status") in open_statuses for item in linked),
            "items": defect_items,
        }
    period_run_ids = {result.get("test_run_id") for result in period_results}
    if selected_run:
        period_run_ids.add(selected_run["_id"])
    environments = sorted({run.get("environment") for run in runs if run.get("_id") in period_run_ids and run.get("environment")})
    builds = sorted({run.get("build") for run in runs if run.get("_id") in period_run_ids and run.get("build")})
    return {**payload.model_dump(), "test_period_id": plan_period_id,
            "test_run_id": selected_run.get("_id") if selected_run else None,
            "project_id": project_id, "project_name": project.get("name") or project_id,
            "plan_name": plan.get("name") or plan["_id"], "objective": snapshot.get("objective") or "",
            "period_name": period.get("name") if period else "",
            "run_name": selected_run.get("name") if selected_run else "",
            "scope_in": requirement_scope or snapshot.get("scope_in") or [], "scope_out": snapshot.get("scope_out") or [],
            "exit_criteria": snapshot.get("exit_criteria") or [], "environments": environments, "builds": builds,
            "counts": counts, "case_results": case_results, "total": len(scope), "defects": defects, "plan_snapshot_hash": plan_snapshot_hash, "excluded_run_count": excluded_run_count,
            "pass_rate": round(100 * counts["PASS"] / (counts["PASS"] + counts["FAIL"]), 2) if counts["PASS"] + counts["FAIL"] else None,
            "captured_at": now(), "created_by": user.id}


async def build_live_report(project_id, report_type, plan_id, user):
    await report_permissions(project_id, user, report_type)
    plan = await database.value.test_plans.find_one(
        {"_id": plan_id, "project_id": project_id},
        {"name": 1, "status": 1, "created_at": 1, "approved_at": 1, "test_period_id": 1},
    )
    if not plan or plan.get("status") != "APPROVED":
        raise HTTPException(422, detail={"code": "INVALID_TEST_PLAN", "message": "Chọn kế hoạch kiểm thử đã duyệt."})
    end_at = datetime.now(timezone.utc)
    start_at = parse_datetime(plan.get("approved_at") or plan.get("created_at")) or end_at
    payload = ReportInput(
        type=report_type,
        title=f'{"Tiến độ kiểm thử" if report_type == "PROGRESS" else "Hoàn tất kiểm thử"} · {plan.get("name") or plan_id}',
        test_plan_id=plan_id,
        test_period_id=plan.get("test_period_id"),
        start_at=start_at,
        end_at=end_at,
    )
    report = await build_report(project_id, payload, user, write=False)
    report["preview_hash"] = report_hash(report)
    return report

def report_hash(report):
    data = {key: value for key, value in report.items() if key not in {"_id", "captured_at", "preview_hash", "idempotency_key"}}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

@router.post("/du-an/{project_id}/bao-cao-kiem-thu/xem-truoc")
async def preview(project_id: str, payload: ReportInput, user: CurrentUser = Depends(get_current_user)):
    report = await build_report(project_id, payload, user)
    report["preview_hash"] = report_hash(report)
    return envelope(report)


@router.get("/du-an/{project_id}/bao-cao-kiem-thu/tu-dong")
async def live_report(
    project_id: str,
    type: Literal["PROGRESS", "COMPLETION"] = Query(...),
    test_plan_id: str = Query(..., min_length=1, max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await build_live_report(project_id, type, test_plan_id, user))


@router.get("/du-an/{project_id}/bao-cao-kiem-thu/tu-dong/xuat")
async def export_live_report(
    project_id: str,
    type: Literal["PROGRESS", "COMPLETION"] = Query(...),
    test_plan_id: str = Query(..., min_length=1, max_length=200),
    format: Literal["pdf", "docx"] = Query(...),
    user: CurrentUser = Depends(get_current_user),
):
    report = await build_live_report(project_id, type, test_plan_id, user)
    await get_project(project_id, user, "report.export")
    permissions = await get_project_permissions(project_id, user.id)
    counts = report["counts"]
    rows = [
        ("Dự án", report["project_name"]),
        ("Kế hoạch kiểm thử", report["plan_name"]),
        ("Kỳ báo cáo", f'{report["start_at"].isoformat()} – {report["end_at"].isoformat()}'),
        ("Thời điểm tạo", report["captured_at"].isoformat()),
        ("Mục tiêu", report["objective"] or "-"),
        ("Phạm vi kiểm thử", "\n".join(report["scope_in"]) or "-"),
        ("Kết quả", f'Tổng: {report["total"]}; Đạt: {counts["PASS"]}; Thất bại: {counts["FAIL"]}; Bị chặn: {counts["BLOCKED"]}; Bỏ qua: {counts["SKIPPED"]}; Không áp dụng: {counts["NOT_APPLICABLE"]}; Chưa ghi nhận: {counts["NOT_RUN"]}'),
        ("Tỷ lệ đạt", f'{report["pass_rate"]}%' if report.get("pass_rate") is not None else "Chưa đủ dữ liệu"),
        ("Cách tính", "Kết quả mới nhất của mỗi ca kể từ khi kế hoạch được duyệt; không cộng các lần chạy lại."),
    ]
    if report.get("period_name"):
        rows.insert(2, ("Đợt kiểm thử", report["period_name"]))
    if report.get("environments"):
        rows.append(("Môi trường", ", ".join(report["environments"])))
    if report.get("builds"):
        rows.append(("Bản dựng", ", ".join(report["builds"])))
    if report.get("exit_criteria") and report["type"] == "COMPLETION":
        rows.append(("Tiêu chí kết thúc", "\n".join(report["exit_criteria"])))
    if report.get("defects") is not None and "defect.read" in permissions:
        rows.append(("Lỗi liên kết", f'{report["defects"]["total"]} lỗi, {report["defects"]["open"]} lỗi đang mở'))
    document = legacy_report_document(report, rows, report["title"])
    content = await asyncio.to_thread(export_report_docx, document)
    if format == "pdf":
        content = await asyncio.to_thread(convert_report_pdf, content)
    media = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="test-report-live-{project_id}.{format}"'},
    )

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
    reports = await database.value.simple_test_reports.find(
        {"project_id": project_id, "type": {"$in": types}},
        {"case_results": 0, "defects.items": 0},
    ).sort("captured_at", -1).to_list(500)
    if "defect.read" not in permissions:
        for report in reports: report["defects"] = None
    return envelope(reports)


@router.get("/du-an/{project_id}/bao-cao-kiem-thu/{report_id}")
async def get_report(project_id: str, report_id: str, user: CurrentUser = Depends(get_current_user)):
    report = await database.value.simple_test_reports.find_one(
        {"_id": report_id, "project_id": project_id}
    )
    if not report:
        raise HTTPException(404, detail={"code": "REPORT_NOT_FOUND"})
    await report_permissions(project_id, user, report["type"])
    permissions = await get_project_permissions(project_id, user.id)
    if "defect.read" not in permissions:
        report["defects"] = None
    return envelope(report)

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
    if report.get("period_name"):
        rows.insert(2, ("Đợt kiểm thử", report["period_name"]))
    if report.get("run_name"):
        rows.insert(3, ("Lần chạy", report["run_name"]))
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
