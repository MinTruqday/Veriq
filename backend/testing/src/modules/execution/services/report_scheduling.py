from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.auth import CurrentUser
from src.core.common import audit, get_project, new_id, now
from src.core.database import database
from src.modules.execution.services.report_schedule import latest_due, occurrence
from src.modules.execution.services.reporting import create_report, fail, fingerprint, get_settings, participants
from src.repositories.reporting import reporting_repository as repository
from src.schemas.reporting import ReportCreate


async def create_schedule(project_id, payload, user):
    await get_project(project_id, user, "workreport.manage")
    if not (await get_settings(project_id, user))["enabled"]:
        fail("PROJECT_REPORTING_DISABLED", 403)
    await participants(project_id, payload.report, user.id)
    request_hash = fingerprint(payload.model_dump())
    query = {"project_id": project_id, "idempotency_key": payload.idempotency_key}
    existing = await repository.find("report_schedules", query)
    if existing:
        if existing.get("request_hash") != request_hash:
            fail("REPORT_IDEMPOTENCY_CONFLICT")
        return existing
    record = {"_id": new_id("RSCH"), "project_id": project_id, **payload.model_dump(), "request_hash": request_hash, "enabled": True, "next_run_at": payload.first_run_at, "next_index": 0, "revision": 1, "created_by": user.id, "created_by_email": user.email, "created_at": now(), "updated_at": now()}
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            await repository.insert("report_schedules", record, session=session)
            await audit(user.id, "report_schedule_created", "ReportSchedule", record["_id"], project_id, session=session)
    return record


async def process_due_schedule(schedule):
    timestamp = now()
    token = str(uuid4())
    claimed = await repository.change("report_schedules", {"_id": schedule["_id"], "revision": schedule["revision"], "enabled": True, "next_run_at": {"$lte": timestamp}, "$or": [{"lease_until": {"$lt": timestamp}}, {"lease_until": {"$exists": False}}]}, {"$set": {"lease_token": token, "lease_until": timestamp + timedelta(minutes=5)}})
    if not claimed:
        return
    due = latest_due(schedule, timestamp)
    if due is None:
        return
    index, scheduled_at, next_at = due
    user = CurrentUser(_id=schedule["created_by"], email=schedule.get("created_by_email", ""))
    run = {"_id": new_id("RSRUN"), "schedule_id": schedule["_id"], "project_id": schedule["project_id"], "occurrence_index": index, "scheduled_at": scheduled_at, "skipped_count": index - schedule["next_index"], "status": "CREATED", "created_at": timestamp, "updated_at": timestamp}
    try:
        await get_project(schedule["project_id"], user, "workreport.manage")
        settings = await get_settings(schedule["project_id"], user)
        if not settings["enabled"]:
            fail("PROJECT_REPORTING_DISABLED", 403)
        value = dict(schedule["report"])
        period = dict(value["period"])
        if schedule.get("period_mode", "PREVIOUS_INTERVAL") == "PREVIOUS_INTERVAL" and schedule["cadence"] != "ONCE":
            period["end_at"] = scheduled_at
            period["start_at"] = occurrence(schedule["first_run_at"], schedule["cadence"], schedule["interval"], index - 1, period["timezone"])
        else:
            for key in ("start_at", "end_at"):
                period[key] = occurrence(period[key], schedule["cadence"], schedule["interval"], index, period["timezone"])
        value.update({"period": period, "due_at": scheduled_at + timedelta(hours=schedule["due_hours_after"]), "idempotency_key": f"schedule:{schedule['_id']}:{index}"})
        request = ReportCreate.model_validate(value)
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                existing_run = await repository.find("report_schedule_runs", {"schedule_id": schedule["_id"], "occurrence_index": index}, session=session)
                if not existing_run or existing_run["status"] == "BLOCKED":
                    report = await create_report(schedule["project_id"], request, user, session=session)
                    run.update({"report_id": report["_id"], "status": "DRAFT_CREATED"})
                    from src.modules.execution.services.report_jobs import build_export_record
                    persisted_report = await repository.find("work_reports", {"_id": report["_id"]}, session=session)
                    for format in dict.fromkeys(schedule.get("formats", ["docx", "pdf"])):
                        await repository.insert("report_exports", build_export_record(persisted_report, format, user), session=session)
                    if existing_run:
                        await repository.change("report_schedule_runs", {"_id": existing_run["_id"], "status": "BLOCKED"}, {"$set": {key: value for key, value in run.items() if key not in {"_id", "created_at"}}, "$unset": {"error_code": ""}}, session=session)
                    else:
                        await repository.insert("report_schedule_runs", run, session=session)
                await repository.change("report_schedules", {"_id": schedule["_id"], "lease_token": token}, {"$set": {"next_index": index + 1, "next_run_at": next_at, "enabled": next_at is not None, "last_run_at": timestamp, "updated_at": timestamp}, "$unset": {"lease_token": "", "lease_until": "", "last_error": ""}}, session=session)
    except Exception as error:
        code = (error.detail or {}).get("code") if isinstance(error, HTTPException) and isinstance(error.detail, dict) else type(error).__name__
        run.update({"status": "BLOCKED", "error_code": code})
        try:
            await repository.insert("report_schedule_runs", run)
        except DuplicateKeyError:
            pass
        await repository.change("report_schedules", {"_id": schedule["_id"], "lease_token": token}, {"$set": {"enabled": False, "last_error": code, "updated_at": now()}, "$unset": {"lease_token": "", "lease_until": ""}})
