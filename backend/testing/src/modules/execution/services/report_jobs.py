import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.storage import storage_client
from src.clients.worker import WorkerClientError, worker_client
from src.core.auth import CurrentUser
from src.core.common import get_project, new_id, now
from src.core.database import database
from src.modules.execution.services.report_document import REPORT_RENDERER_VERSION, convert_report_pdf, export_report_docx
from src.modules.execution.services.reporting import fail, fingerprint, report_for_user
from src.repositories.reporting import reporting_repository as repository

logger = logging.getLogger(__name__)
_background = None
_conversion_slots = asyncio.Semaphore(2)
MIME = {"docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "pdf": "application/pdf"}


async def enqueue_export(job):
    payload = {"event": "report.export.requested", "project_id": job["project_id"], "artifact_version_id": job["_id"], "model_version": f"report-export-v1-g{job.get('dispatch_generation', 0)}", "requester_id": job["requested_by"], "requester_email": job["requester_email"], "payload": {"export_id": job["_id"], "dispatch_generation": job.get("dispatch_generation", 0)}}
    worker = await worker_client.enqueue(payload)
    worker_id = worker.get("job_id") or worker.get("_id")
    if not worker_id:
        raise WorkerClientError()
    await repository.change("report_exports", {"_id": job["_id"], "status": "QUEUED", "dispatch_generation": job.get("dispatch_generation", 0)}, {"$set": {"worker_job_id": worker_id, "updated_at": now()}})


def build_export_record(report, format, user):
    return {"_id": new_id("REXP"), "report_id": report["_id"], "revision": report["revision"], "format": format, "renderer_version": REPORT_RENDERER_VERSION, "project_id": report["project_id"], "report_hash": report_source_hash(report), "requested_by": user.id, "requester_email": user.email, "status": "QUEUED", "dispatch_generation": 0, "created_at": now(), "updated_at": now()}


def report_source_hash(report):
    def normalize(value):
        if isinstance(value, datetime):
            instant = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
            return instant.isoformat(timespec="microseconds")
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    return fingerprint(normalize({"content": report["content_doc"], "title": report["title"], "snapshot": report["snapshot"]}))


async def request_export(report_id, payload, user):
    report = await report_for_user(report_id, user)
    await get_project(report["project_id"], user, "workreport.write")
    if user.id not in {report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])}:
        fail("REPORT_EXPORT_FORBIDDEN", 403)
    if report["revision"] != payload.expected_revision:
        fail("REPORT_REVISION_CONFLICT")
    revision = report.get("published_source_revision", report["revision"]) if report["status"] in {"PUBLISHED", "ARCHIVED"} else report["revision"]
    if report["status"] in {"PUBLISHED", "ARCHIVED"}:
        published = await repository.list("report_exports", {"_id": {"$in": report.get("published_export_ids", [])}, "format": payload.format}, 10)
        if published:
            return published[0]
        fail("REPORT_PUBLISHED_EXPORT_IMMUTABLE")
    query = {"report_id": report_id, "revision": revision, "format": payload.format, "renderer_version": REPORT_RENDERER_VERSION}
    existing = await repository.find("report_exports", query)
    if existing:
        return existing
    record = build_export_record(report, payload.format, user)
    try:
        await repository.insert("report_exports", record)
    except DuplicateKeyError:
        return await repository.find("report_exports", query)
    try:
        await enqueue_export(record)
    except WorkerClientError:
        logger.warning("Report export dispatch deferred export=%s", record["_id"])
    return await repository.find("report_exports", {"_id": record["_id"]})


async def process_export(body, user):
    export_id = (body.get("payload") or {}).get("export_id")
    job = await repository.find("report_exports", {"_id": export_id, "project_id": body["project_id"], "requested_by": user.id})
    if not job:
        fail("REPORT_EXPORT_NOT_FOUND", 404)
    generation = int((body.get("payload") or {}).get("dispatch_generation", 0))
    if generation != int(job.get("dispatch_generation", 0)):
        return {"status": "COMPLETED", "export_status": "SUPERSEDED"}
    report = await report_for_user(job["report_id"], user)
    await get_project(report["project_id"], user, "workreport.write")
    if job["status"] == "READY":
        return {"status": "COMPLETED", "export_id": export_id}
    expected = report_source_hash(report)
    if expected != job["report_hash"]:
        await repository.change("report_exports", {"_id": export_id, "dispatch_generation": generation}, {"$set": {"status": "SUPERSEDED", "error_code": "REPORT_SOURCE_CHANGED", "updated_at": now()}})
        return {"status": "COMPLETED", "export_status": "SUPERSEDED"}
    claimed = await repository.change("report_exports", {"_id": export_id, "dispatch_generation": generation, "status": {"$in": ["QUEUED", "FAILED", "RUNNING"]}}, {"$set": {"status": "RUNNING", "updated_at": now()}})
    if not claimed:
        return {"status": "COMPLETED", "export_status": "SUPERSEDED"}
    try:
        template = report.get("template_snapshot") or {}
        base_docx = None
        if template.get("original_file"):
            base_docx = await storage_client.read_report_asset(job["project_id"], template["original_artifact_id"], template["original_file"]["object_key"])
        from src.modules.execution.services.report_assets import export_assets
        assets = await export_assets(report)
        if not report.get("owner_name") or not report.get("reviewer_name"):
            raise RuntimeError("REPORT_SIGNATORY_NAME_UNAVAILABLE")
        async with _conversion_slots:
            render_report = {**report, "exported_at": now()}
            data = await asyncio.to_thread(export_report_docx, render_report, assets, base_docx)
            if job["format"] == "pdf":
                data = await asyncio.to_thread(convert_report_pdf, data)
        current = await report_for_user(job["report_id"], user)
        await get_project(current["project_id"], user, "workreport.write")
        if report_source_hash(current) != expected:
            raise RuntimeError("REPORT_SOURCE_CHANGED")
        stored = await storage_client.store_report_asset(job["project_id"], export_id, f"report-v{report['version']}.{job['format']}", MIME[job["format"]], data)
        await repository.change("report_exports", {"_id": export_id, "report_hash": expected, "dispatch_generation": generation}, {"$set": {"status": "READY", "file": stored, "completed_at": now(), "updated_at": now()}, "$unset": {"error_code": ""}})
        return {"status": "COMPLETED", "export_id": export_id}
    except Exception as error:
        code = str(error) if isinstance(error, (RuntimeError, ValueError)) and str(error).startswith("REPORT_") else "REPORT_EXPORT_FAILED"
        await repository.change("report_exports", {"_id": export_id, "dispatch_generation": generation}, {"$set": {"status": "FAILED", "error_code": code[:160], "updated_at": now()}})
        logger.exception("Report export failed export=%s", export_id)
        return {"status": "COMPLETED", "export_status": "FAILED", "error_code": code}


async def download_export(export_id, user):
    job = await repository.find("report_exports", {"_id": export_id})
    if not job or job["status"] != "READY":
        fail("REPORT_EXPORT_NOT_READY", 404)
    report = await report_for_user(job["report_id"], user)
    from src.core.common import get_project_roles
    roles = await get_project_roles(report["project_id"], user.id)
    if not roles & {"BA", "QA", "TESTER", "DEVELOPER"} or user.id not in {report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])}:
        delivery = await repository.find("report_deliveries", {"report_id": report["_id"], "user_id": user.id, "can_download": True, "revoked_at": {"$exists": False}})
        if not delivery or export_id not in report.get("published_export_ids", []):
            fail("REPORT_DOWNLOAD_FORBIDDEN", 403)
    data = await storage_client.read_report_asset(job["project_id"], export_id, job["file"]["object_key"])
    return job, data


async def dispatch_delivery(delivery):
    try:
        await get_project(delivery["project_id"], CurrentUser(_id=delivery["user_id"]), "workreport.read")
        timestamp = now()
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                updated = await repository.change("report_deliveries", {"_id": delivery["_id"], "status": "PENDING", "revoked_at": {"$exists": False}}, {"$set": {"status": "RECEIVED", "sent_at": timestamp, "received_at": timestamp, "updated_at": timestamp}}, session=session)
                if updated:
                    await database.value.report_notifications.update_one({"user_id": delivery["user_id"], "event_key": f"report-received:{delivery['_id']}"}, {"$setOnInsert": {"_id": new_id("RNTF"), "user_id": delivery["user_id"], "project_id": delivery["project_id"], "event_key": f"report-received:{delivery['_id']}", "report_id": delivery["report_id"], "kind": "REPORT_RECEIVED", "status": "PENDING", "attempts": 0, "next_attempt_at": timestamp, "created_at": timestamp, "updated_at": timestamp}}, upsert=True, session=session)
    except HTTPException as error:
        if error.status_code not in {401, 403, 404}:
            raise
        await repository.change("report_deliveries", {"_id": delivery["_id"], "status": "PENDING"}, {"$set": {"status": "FAILED", "error_code": "REPORT_RECIPIENT_ACCESS_REVOKED", "updated_at": now()}})


async def run_reporting_background():
    from src.modules.execution.services.report_scheduling import process_due_schedule

    while True:
        try:
            notifications = await repository.list("report_notifications", {"status": "PENDING", "next_attempt_at": {"$lte": now()}}, 20)
            for notification in notifications:
                await dispatch_notification(notification)
            await queue_due_reminders()
            await reconcile_exports()
            await repository.collection("report_ai_drafts").update_many({"status": "RUNNING", "updated_at": {"$lt": now() - timedelta(minutes=30)}}, {"$set": {"status": "FAILED", "error_code": "REPORT_AI_INTERRUPTED", "updated_at": now()}})
            deliveries = await repository.list("report_deliveries", {"status": "PENDING", "revoked_at": {"$exists": False}}, 50)
            for delivery in deliveries:
                await dispatch_delivery(delivery)
            exports = await repository.list("report_exports", {"status": "QUEUED", "worker_job_id": {"$exists": False}}, 10)
            for job in exports:
                try:
                    await enqueue_export(job)
                except WorkerClientError:
                    break
            schedules = await repository.list("report_schedules", {"enabled": True, "next_run_at": {"$lte": now()}, "$or": [{"lease_until": {"$lt": now()}}, {"lease_until": {"$exists": False}}]}, 10)
            for schedule in schedules:
                await process_due_schedule(schedule)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Reporting background processing failed")
        await asyncio.sleep(5)


async def start_reporting_background():
    global _background
    if not _background or _background.done():
        _background = asyncio.create_task(run_reporting_background())


async def stop_reporting_background():
    global _background
    if _background:
        _background.cancel()
        try:
            await _background
        except asyncio.CancelledError:
            pass
        _background = None


async def dispatch_notification(notification):
    import httpx
    from src.core.configuration import settings
    from src.modules.execution.services.reporting import report_for_user

    try:
        await report_for_user(notification["report_id"], CurrentUser(_id=notification["user_id"]))
    except HTTPException:
        await repository.change("report_notifications", {"_id": notification["_id"]}, {"$set": {"status": "CANCELLED", "updated_at": now()}})
        return
    titles = {
        "REPORT_ASSIGNED": "Bạn được giao viết báo cáo", "REPORT_SUBMIT": "Có báo cáo cần rà soát",
        "REPORT_REQUEST_CHANGES": "Báo cáo cần chỉnh sửa", "REPORT_APPROVE": "Báo cáo đã được duyệt",
        "REPORT_RECEIVED": "Bạn đã nhận báo cáo", "REPORT_DUE": "Báo cáo sắp đến hạn", "REPORT_OVERDUE": "Báo cáo đã quá hạn",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{settings.NOTIFICATION_URL.rstrip('/')}/thong-bao/gui-di", headers={"X-Internal-Token": settings.SECRET_KEY}, json={"target_user_id": notification["user_id"], "title": titles.get(notification["kind"], "Cập nhật báo cáo"), "body": f"Mở mục Báo cáo trong dự án để xem nội dung. /du-an/{notification['project_id']}/bao-cao", "type": "system", "idempotency_key": f"report:{notification['user_id']}:{notification['event_key']}"})
            response.raise_for_status()
        await repository.change("report_notifications", {"_id": notification["_id"]}, {"$set": {"status": "SENT", "sent_at": now(), "updated_at": now()}})
    except httpx.HTTPError:
        attempts = notification.get("attempts", 0) + 1
        await repository.change("report_notifications", {"_id": notification["_id"], "status": "PENDING"}, {"$set": {"attempts": attempts, "next_attempt_at": now() + timedelta(seconds=min(300, 5 * 2 ** min(attempts, 6))), "updated_at": now()}})


async def queue_due_reminders():
    from src.modules.execution.services.reporting import queue_report_notification
    timestamp = now()
    reports = await repository.list("work_reports", {"status": {"$in": ["DRAFT", "IN_REVIEW"]}, "due_at": {"$lte": timestamp + timedelta(days=30), "$type": "date"}}, 100)
    for report in reports:
        config = await repository.find("report_settings", {"project_id": report["project_id"], "enabled": True})
        if not config:
            continue
        deadline = report["due_at"]
        if deadline > timestamp + timedelta(hours=config.get("reminder_hours_before", 24)):
            continue
        kind = "REPORT_OVERDUE" if deadline < timestamp else "REPORT_DUE"
        target = report["reviewer_id"] if report["status"] == "IN_REVIEW" else report["owner_id"]
        await queue_report_notification(report["project_id"], report["_id"], target, kind, f"{kind}:{report['_id']}:{deadline.isoformat()}")


async def retry_export(export_id, payload, user):
    job = await repository.find("report_exports", {"_id": export_id})
    if not job:
        fail("REPORT_EXPORT_NOT_FOUND", 404)
    report = await report_for_user(job["report_id"], user)
    await get_project(report["project_id"], user, "workreport.write")
    if user.id not in {report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])}:
        fail("REPORT_EXPORT_FORBIDDEN", 403)
    value = await repository.change("report_exports", {"_id": export_id, "status": "FAILED", "dispatch_generation": payload.expected_generation}, {"$set": {"status": "QUEUED", "updated_at": now()}, "$inc": {"dispatch_generation": 1}, "$unset": {"worker_job_id": "", "error_code": ""}})
    if not value:
        fail("REPORT_EXPORT_NOT_RETRYABLE")
    return value


async def reconcile_exports():
    jobs = await repository.list("report_exports", {"status": {"$in": ["QUEUED", "RUNNING"]}, "worker_job_id": {"$exists": True}, "updated_at": {"$lt": now() - timedelta(seconds=60)}}, 10)
    for job in jobs:
        try:
            worker = await worker_client.get(job["worker_job_id"])
        except WorkerClientError:
            continue
        if worker.get("status") in {"failed", "canceled", "reconciliation_required", "completed"}:
            await repository.change("report_exports", {"_id": job["_id"], "dispatch_generation": job.get("dispatch_generation", 0), "status": {"$in": ["QUEUED", "RUNNING"]}}, {"$set": {"status": "FAILED", "error_code": "REPORT_EXPORT_INTERRUPTED", "updated_at": now()}})
