from fastapi import APIRouter, Depends, Query, File, UploadFile, Request, HTTPException
from fastapi.routing import APIRoute
from pymongo.errors import DuplicateKeyError, OperationFailure

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, get_project
from src.repositories.reporting import reporting_repository as repository
from src.schemas.reporting import ReportAIApply, ReportDeliveryPatch, ReportCommentPatch, ReportExportRetry, ReportAIDraft, ReportScheduleCreate, ReportSchedulePatch, ReportExportRequest, ReportAction, ReportComment, ReportCreate, ReportPatch, ReportTemplateCreate, ReportingSettings
from src.modules.execution.services import reporting
from src.schemas.reporting import ReportAssignmentPatch

class ReportingRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def guarded(request):
            import asyncio
            for attempt in range(3):
                try:
                    return await handler(request)
                except DuplicateKeyError as error:
                    if attempt == 2:
                        raise HTTPException(status_code=409, detail={"code": "REPORT_REVISION_CONFLICT"}) from error
                except OperationFailure as error:
                    if error.code not in {112, 244} and not error.has_error_label("TransientTransactionError"):
                        raise
                    if attempt == 2:
                        raise HTTPException(status_code=409, detail={"code": "REPORT_REVISION_CONFLICT"}) from error
                await asyncio.sleep(0.025 * (attempt + 1))

        return guarded


router = APIRouter(prefix="/kiem-thu", tags=["Báo cáo công việc"], route_class=ReportingRoute)


@router.get("/du-an/{project_id}/bao-cao-cong-viec/cau-hinh")
async def get_settings(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.get_settings(project_id, user))


@router.get("/du-an/{project_id}/bao-cao-cong-viec/nguoi-tham-gia")
async def eligible_participants(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.list_eligible_participants(project_id, user))


@router.put("/du-an/{project_id}/bao-cao-cong-viec/cau-hinh")
async def update_settings(project_id: str, payload: ReportingSettings, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.update_settings(project_id, payload, user))


@router.get("/du-an/{project_id}/bao-cao-cong-viec/mau")
async def list_templates(project_id: str, user: CurrentUser = Depends(get_current_user)):
    await get_project(project_id, user, "workreport.read")
    return envelope(await repository.list("report_templates", {"project_id": project_id}, 500))


@router.post("/du-an/{project_id}/bao-cao-cong-viec/mau", status_code=201)
async def create_template(project_id: str, payload: ReportTemplateCreate, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.create_template(project_id, payload, user))


@router.get("/du-an/{project_id}/bao-cao-cong-viec")
async def list_reports(project_id: str, inbox: bool = Query(default=False), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), search: str = Query(default="", max_length=200), status: str | None = Query(default=None, pattern="^(DRAFT|IN_REVIEW|APPROVED|PUBLISHED|ARCHIVED)$"), user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.list_reports(project_id, user, inbox, limit, offset, search, status))


@router.post("/du-an/{project_id}/bao-cao-cong-viec", status_code=201)
async def create_report(project_id: str, payload: ReportCreate, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.create_report(project_id, payload, user))


@router.get("/du-an/{project_id}/bao-cao-cong-viec/phan-cong")
async def list_report_assignments(project_id: str, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.list_report_assignments(project_id, user, limit, offset))


@router.patch("/bao-cao-cong-viec/{report_id}/phan-cong")
async def update_report_assignments(report_id: str, payload: ReportAssignmentPatch, user: CurrentUser = Depends(get_current_user)):
    value = await reporting.patch_report_assignments(report_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/bao-cao-cong-viec/{report_id}")
async def get_report(report_id: str, user: CurrentUser = Depends(get_current_user)):
    report = await reporting.report_for_user(report_id, user)
    delivery = await repository.find("report_deliveries", {"report_id": report_id, "user_id": user.id, "revoked_at": {"$exists": False}})
    permissions = await reporting.member_permissions(report["project_id"], user.id)
    participating = bool(permissions & {"workreport.write", "workreport.review"}) and user.id in {
        report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])
    }
    return envelope(
        {
            **report,
            "current_access": {
                "can_comment": participating or bool(delivery and delivery["access"] == "COMMENT"),
                "can_download": participating or bool(delivery and delivery["can_download"]),
            },
        }
    )


@router.get("/bao-cao-cong-viec/{report_id}/xem-truoc")
async def preview_report_content(report_id: str, user: CurrentUser = Depends(get_current_user)):
    from src.modules.execution.services.report_document import resolve_report_fields
    report = await reporting.report_for_user(report_id, user)
    return envelope({"revision": report["revision"], "content_doc": resolve_report_fields(report)})


@router.patch("/bao-cao-cong-viec/{report_id}")
async def update_report(report_id: str, payload: ReportPatch, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.patch_report(report_id, payload, user))


@router.post("/bao-cao-cong-viec/{report_id}/chuyen-trang-thai")
async def transition_report(report_id: str, payload: ReportAction, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.transition_report(report_id, payload, user))


@router.get("/bao-cao-cong-viec/{report_id}/binh-luan")
async def list_comments(report_id: str, user: CurrentUser = Depends(get_current_user)):
    await reporting.report_for_user(report_id, user)
    rows = await repository.list("report_comments", {"report_id": report_id}, 500, "created_at")
    from src.core.common import load_user_identities
    people = await load_user_identities(item["created_by"] for item in rows)
    return envelope([{**item, "author_label": (people.get(item["created_by"]) or {}).get("label") or ""} for item in rows])


@router.post("/bao-cao-cong-viec/{report_id}/binh-luan", status_code=201)
async def add_comment(report_id: str, payload: ReportComment, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.add_comment(report_id, payload, user))


@router.get("/bao-cao-cong-viec/{report_id}/nguoi-nhan")
async def recipients(report_id: str, user: CurrentUser = Depends(get_current_user)):
    report = await reporting.report_for_user(report_id, user)
    if user.id not in {report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])}:
        await get_project(report["project_id"], user, "workreport.manage")
    rows = await repository.list("report_deliveries", {"report_id": report_id}, 500)
    from src.core.common import load_user_identities
    people = await load_user_identities(item["user_id"] for item in rows)
    return envelope([{**item, "user_label": (people.get(item["user_id"]) or {}).get("label") or ""} for item in rows])


@router.post("/bao-cao-cong-viec/{report_id}/da-xem")
async def viewed(report_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.receipt(report_id, user))


@router.post("/bao-cao-cong-viec/{report_id}/xac-nhan")
async def acknowledge(report_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.receipt(report_id, user, True))


@router.get("/du-an/{project_id}/bao-cao-cong-viec/lich")
async def list_schedules(project_id: str, user: CurrentUser = Depends(get_current_user)):
    await get_project(project_id, user, "workreport.manage")
    return envelope(await repository.list("report_schedules", {"project_id": project_id}, 500))


@router.post("/du-an/{project_id}/bao-cao-cong-viec/lich", status_code=201)
async def create_schedule_endpoint(project_id: str, payload: ReportScheduleCreate, user: CurrentUser = Depends(get_current_user)):
    from src.modules.execution.services.report_scheduling import create_schedule
    return envelope(await create_schedule(project_id, payload, user))


@router.patch("/lich-bao-cao/{schedule_id}")
async def change_schedule(schedule_id: str, payload: ReportSchedulePatch, user: CurrentUser = Depends(get_current_user)):
    schedule = await repository.find("report_schedules", {"_id": schedule_id})
    if not schedule:
        reporting.fail("REPORT_SCHEDULE_NOT_FOUND", 404)
    await get_project(schedule["project_id"], user, "workreport.manage")
    value = await repository.change("report_schedules", {"_id": schedule_id, "revision": payload.expected_revision}, {"$set": {"enabled": payload.enabled, "updated_at": reporting.now()}, "$inc": {"revision": 1}})
    if not value:
        reporting.fail("REPORT_REVISION_CONFLICT")
    return envelope(value)


@router.get("/lich-bao-cao/{schedule_id}/luot-chay")
async def schedule_runs(schedule_id: str, user: CurrentUser = Depends(get_current_user)):
    schedule = await repository.find("report_schedules", {"_id": schedule_id})
    if not schedule:
        reporting.fail("REPORT_SCHEDULE_NOT_FOUND", 404)
    await get_project(schedule["project_id"], user, "workreport.manage")
    return envelope(await repository.list("report_schedule_runs", {"schedule_id": schedule_id}, 500, "created_at"))


@router.post("/bao-cao-cong-viec/{report_id}/xuat", status_code=202)
async def request_export_endpoint(report_id: str, payload: ReportExportRequest, user: CurrentUser = Depends(get_current_user)):
    from src.modules.execution.services.report_jobs import request_export
    return envelope(await request_export(report_id, payload, user))


@router.get("/bao-cao-cong-viec/{report_id}/ban-xuat")
async def list_exports(report_id: str, user: CurrentUser = Depends(get_current_user)):
    report = await reporting.report_for_user(report_id, user)
    values = await repository.list("report_exports", {"report_id": report_id}, 100)
    if user.id not in {report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])}:
        values = [value for value in values if value["_id"] in report.get("published_export_ids", [])]
    return envelope([{key: value for key, value in item.items() if key not in {"file", "requester_email"}} for item in values])


@router.get("/ban-xuat-bao-cao/{export_id}/tai-xuong")
async def download_export_endpoint(export_id: str, user: CurrentUser = Depends(get_current_user)):
    from fastapi.responses import Response
    from src.modules.execution.services.report_jobs import download_export, MIME
    job, data = await download_export(export_id, user)
    return Response(content=data, media_type=MIME[job["format"]], headers={"Content-Disposition": f'attachment; filename="report.{job["format"]}"', "Cache-Control": "no-store"})


@router.post("/bao-cao-cong-viec/{report_id}/ai/de-xuat")
async def draft_report_endpoint(report_id: str, payload: ReportAIDraft, user: CurrentUser = Depends(get_current_user)):
    from src.modules.execution.services.report_ai import draft_report
    return envelope(await draft_report(report_id, payload, user))


@router.post("/du-an/{project_id}/bao-cao-cong-viec/mau/xem-truoc", status_code=201)
async def preview_template_endpoint(project_id: str, file: UploadFile = File(), user: CurrentUser = Depends(get_current_user)):
    from src.modules.execution.services.report_templates import preview_template
    data = await file.read(25 * 1024 * 1024 + 1)
    return envelope(await preview_template(project_id, file.filename or "", data, user))


@router.patch("/bao-cao-cong-viec/{report_id}/nguoi-nhan")
async def change_delivery_endpoint(report_id: str, payload: ReportDeliveryPatch, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.change_delivery(report_id, payload, user))


@router.patch("/bao-cao-cong-viec/{report_id}/binh-luan/{comment_id}")
async def resolve_comment_endpoint(report_id: str, comment_id: str, payload: ReportCommentPatch, user: CurrentUser = Depends(get_current_user)):
    return envelope(await reporting.resolve_comment(report_id, comment_id, payload, user))


@router.post("/ban-xuat-bao-cao/{export_id}/thu-lai", status_code=202)
async def retry_export_endpoint(export_id: str, payload: ReportExportRetry, user: CurrentUser = Depends(get_current_user)):
    from src.modules.execution.services.report_jobs import retry_export
    return envelope(await retry_export(export_id, payload, user))


@router.post("/bao-cao-cong-viec/{report_id}/ai/ap-dung")
async def apply_report_proposal_endpoint(report_id: str, payload: ReportAIApply, user: CurrentUser = Depends(get_current_user)):
    from src.modules.execution.services.report_ai import apply_report_proposal
    return envelope(await apply_report_proposal(report_id, payload, user))


async def report_image_user(request: Request):
    authorization = request.headers.get("authorization", "")
    token = authorization.partition(" ")[2] if authorization.lower().startswith("bearer ") else request.cookies.get("token")
    return await get_current_user(request, token, None, None)


@router.post("/du-an/{project_id}/bao-cao-cong-viec/anh", status_code=201)
async def upload_report_image(project_id: str, file: UploadFile = File(), user: CurrentUser = Depends(get_current_user)):
    from src.modules.execution.services.report_assets import upload_image
    data = await file.read(5 * 1024 * 1024 + 1)
    asset = await upload_image(project_id, data, user)
    return envelope({key: asset[key] for key in ("_id", "width", "height")})


@router.get("/du-an/{project_id}/bao-cao-cong-viec/anh/{asset_id}")
async def preview_report_image(project_id: str, asset_id: str, user: CurrentUser = Depends(report_image_user)):
    from fastapi.responses import Response
    from src.clients.storage import storage_client
    await get_project(project_id, user, "workreport.write")
    asset = await repository.find("report_assets", {"_id": asset_id, "project_id": project_id, "created_by": user.id})
    if not asset:
        reporting.fail("REPORT_IMAGE_NOT_FOUND", 404)
    data = await storage_client.read_report_asset(project_id, asset_id, asset["file"]["object_key"])
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/bao-cao-cong-viec/{report_id}/anh/{asset_id}")
async def read_report_image(report_id: str, asset_id: str, user: CurrentUser = Depends(report_image_user)):
    from fastapi.responses import Response
    from src.clients.storage import storage_client
    from src.modules.execution.services.report_assets import image_ids
    report = await reporting.report_for_user(report_id, user)
    if asset_id not in image_ids(report["content_doc"]):
        reporting.fail("REPORT_IMAGE_NOT_FOUND", 404)
    asset = await repository.find("report_assets", {"_id": asset_id, "project_id": report["project_id"]})
    if not asset:
        reporting.fail("REPORT_IMAGE_NOT_FOUND", 404)
    data = await storage_client.read_report_asset(report["project_id"], asset_id, asset["file"]["object_key"])
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/bao-cao-cong-viec/{report_id}/ai/de-xuat/{proposal_id}")
async def get_report_proposal(report_id: str, proposal_id: str, user: CurrentUser = Depends(get_current_user)):
    report = await reporting.report_for_user(report_id, user)
    await get_project(report["project_id"], user, "workreport.ai")
    if user.id not in {report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])}:
        reporting.fail("REPORT_AI_ACCESS_DENIED", 403)
    proposal = await repository.find("report_ai_drafts", {"_id": proposal_id, "report_id": report_id})
    if not proposal:
        reporting.fail("REPORT_AI_PROPOSAL_NOT_FOUND", 404)
    return envelope(proposal)
