import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.auth import permissions_for_membership
from src.core.common import audit, get_project, new_id, now
from src.core.database import database
from src.core.human_decisions import (
    content_authorship_changes,
    require_automation_publication_authority,
    require_independent_review,
)
from src.modules.execution.services.report_document import validate_report_document
from src.repositories.common import common_repository
from src.repositories.reporting import reporting_repository as repository
from src.schemas.reporting import ReportCreate


COLLECTION = "work_reports"


def fail(code, status=409):
    raise HTTPException(status_code=status, detail={"code": code})


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode()).hexdigest()


async def membership(project_id, user_id):
    value = await database.value.project_members.find_one({"project_id": project_id, "user_id": user_id, "status": "ACTIVE"})
    if not value:
        fail("REPORT_MEMBER_NOT_ACTIVE", 422)
    return value


async def member_permissions(project_id, user_id):
    member = await membership(project_id, user_id)
    project = await common_repository.find_project(project_id, {"settings": 1}) or {}
    return permissions_for_membership(member, project.get("settings"))


async def list_eligible_participants(project_id, user):
    await get_project(project_id, user, "workreport.read")
    project = await common_repository.find_project(project_id, {"settings": 1}) or {}
    members = await database.value.project_members.find(
        {"project_id": project_id, "status": "ACTIVE"},
        {"user_id": 1, "project_role": 1, "project_roles": 1, "status": 1},
    ).to_list(5000)
    writers = []
    reviewers = []
    for member in members:
        permissions = permissions_for_membership(member, project.get("settings"))
        user_id = member.get("user_id")
        if not user_id:
            continue
        if "workreport.write" in permissions:
            writers.append(user_id)
        if "workreport.review" in permissions:
            reviewers.append(user_id)
    return {"writer_ids": sorted(writers), "reviewer_ids": sorted(reviewers)}


async def participants(project_id, value, creator_id=None):
    if value.reviewer_id in {value.owner_id, *value.editor_ids, creator_id}:
        fail("REPORT_REVIEWER_MUST_BE_INDEPENDENT", 422)
    for user_id in set([value.owner_id, *value.editor_ids]):
        if "workreport.write" not in await member_permissions(project_id, user_id):
            fail("REPORT_EDITOR_PERMISSION_INVALID", 422)
    if "workreport.review" not in await member_permissions(project_id, value.reviewer_id):
        fail("REPORT_REVIEW_PERMISSION_INVALID", 422)
    for recipient in value.recipients:
        await membership(project_id, recipient.user_id)


async def report_for_user(report_id, user, action="read"):
    report = await repository.find(COLLECTION, {"_id": report_id})
    if not report:
        fail("REPORT_NOT_FOUND", 404)
    permission = (
        f"workreport.{action}"
        if action in {"write", "review", "publish"}
        else "workreport.read"
    )
    await get_project(report["project_id"], user, permission)
    permissions = await member_permissions(report["project_id"], user.id)
    is_author = "workreport.write" in permissions and user.id in {
        report["owner_id"], *report.get("editor_ids", [])
    }
    is_reviewer = bool(permissions & {"workreport.review", "workreport.publish"}) and (
        report["reviewer_id"] == user.id
    )
    delivery = await repository.find("report_deliveries", {"report_id": report_id, "user_id": user.id, "revoked_at": {"$exists": False}})
    if action == "write" and not is_author:
        fail("REPORT_EDIT_FORBIDDEN", 403)
    if action in {"review", "publish"} and not is_reviewer:
        fail("REPORT_REVIEWER_REQUIRED", 403)
    if action == "read" and not (is_author or is_reviewer or (delivery and delivery["status"] in {"RECEIVED", "VIEWED", "ACKNOWLEDGED"} and report["status"] in {"PUBLISHED", "ARCHIVED"})):
        fail("REPORT_ACCESS_DENIED", 403)
    missing_identity_ids = [
        report.get(id_field)
        for name_field, id_field in (
            ("owner_name", "owner_id"),
            ("reviewer_name", "reviewer_id"),
            ("created_by_name", "created_by"),
        )
        if not report.get(name_field) and report.get(id_field)
    ]
    if missing_identity_ids:
        from src.core.common import load_user_identities

        identities = await load_user_identities(missing_identity_ids)
        report = dict(report)
        for name_field, id_field in (
            ("owner_name", "owner_id"),
            ("reviewer_name", "reviewer_id"),
            ("created_by_name", "created_by"),
        ):
            if not report.get(name_field) and report.get(id_field):
                identity = identities.get(report[id_field]) or {}
                report[name_field] = identity.get("label") or identity.get("full_name") or identity.get("email")
    return report


async def get_settings(project_id, user):
    project = await get_project(project_id, user, "workreport.read")
    return await repository.find("report_settings", {"project_id": project_id}) or {
        "project_id": project_id,
        "revision": 0,
        "enabled": False,
        "timezone": project.get("timezone"),
        "allowed_kinds": ["PERSONAL", "TEAM", "PROJECT"],
        "reminder_hours_before": 24,
    }


async def update_settings(project_id, payload, user):
    await get_project(project_id, user, "workreport.manage")
    current = await get_settings(project_id, user)
    if current["revision"] != payload.expected_revision:
        fail("REPORT_REVISION_CONFLICT")
    changes = payload.model_dump(exclude={"expected_revision"})
    timestamp = now()
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            if current["revision"] == 0:
                try:
                    value = await repository.insert("report_settings", {"_id": new_id("RCFG"), "project_id": project_id, **changes, "revision": 1, "created_at": timestamp, "updated_at": timestamp}, session=session)
                except DuplicateKeyError:
                    fail("REPORT_REVISION_CONFLICT")
            else:
                value = await repository.change("report_settings", {"project_id": project_id, "revision": payload.expected_revision}, {"$set": {**changes, "updated_at": timestamp}, "$inc": {"revision": 1}}, session=session)
                if not value:
                    fail("REPORT_REVISION_CONFLICT")
            if not payload.enabled:
                await database.value.report_schedules.update_many({"project_id": project_id, "enabled": True}, {"$set": {"enabled": False, "paused_by_project": True, "updated_at": timestamp}, "$inc": {"revision": 1}}, session=session)
            elif not current["enabled"]:
                from src.modules.execution.services.report_schedule import latest_due
                paused = await database.value.report_schedules.find({"project_id": project_id, "paused_by_project": True}, session=session).to_list(None)
                for schedule in paused:
                    due = latest_due(schedule, timestamp)
                    changes = {"enabled": True, "updated_at": timestamp}
                    if due:
                        index, _, following = due
                        changes.update({"next_index": index + 1, "next_run_at": following, "enabled": following is not None})
                    await repository.change("report_schedules", {"_id": schedule["_id"], "revision": schedule["revision"]}, {"$set": changes, "$unset": {"paused_by_project": ""}, "$inc": {"revision": 1}}, session=session)
            if payload.enabled:
                await seed_report_templates(project_id, user.id, session)
            await audit(user.id, "report_settings_updated", "ReportSettings", value["_id"], project_id, changes, session=session)
    return value


async def source_snapshot(project_id, payload):
    period = payload.period
    subjects = set(payload.subject_ids or ([payload.owner_id] if payload.kind == "PERSONAL" else []))
    for user_id in subjects:
        await membership(project_id, user_id)
    query = {"project_id": project_id, "item_type": {"$in": ["TASK", "SUBTASK"]}}
    if subjects:
        query["assignee_id"] = {"$in": sorted(subjects)}
    fields = {"_id": 1, "title": 1, "status": 1, "assignee_id": 1, "updated_at": 1, "created_at": 1, "completed_at": 1, "estimate": 1, "revision": 1, "due_at": 1, "priority": 1}
    tasks = await database.value.work_items.find(query, fields).limit(5001).to_list(5001)
    if len(tasks) > 5000:
        fail("REPORT_SCOPE_TOO_LARGE", 422)
    workflow = await database.value.planning_workflows.find_one({"project_id": project_id}) or {}
    terminal = {str(item["key"]) for item in workflow.get("statuses", []) if item.get("counts_as_completed")}
    if not terminal:
        terminal = {"DONE"}
    cancelled = {"CANCELLED", "CANCELED"}
    valid = [item for item in tasks if str(item.get("status", "")).upper() not in cancelled]
    def in_period(value):
        return isinstance(value, datetime) and period.start_at <= value.replace(tzinfo=value.tzinfo or timezone.utc) < period.end_at
    changed = [item for item in tasks if in_period(item.get("updated_at"))]
    completed = [item for item in valid if str(item.get("status", "")).upper() in terminal]
    from src.modules.projects.services.project_progress import task_summary
    summary = task_summary([{"status": "COMPLETED" if item.get("status") in terminal else item.get("status"), "weight": item.get("estimate") or 1} for item in tasks])
    data = {
        "task_summary": summary,
        "captured_at": now(), "period": period.model_dump(), "subject_ids": sorted(subjects),
        "metrics": {"work_items_total": len(valid), "work_items_completed_at_capture": len(completed), "work_items_changed_in_period": len(changed)},
        "work_items": tasks,
        "limitations": ["ACTUAL_WORK_HOURS_NOT_INFERRED", "SNAPSHOT_IS_CURRENT_STATE_NOT_HISTORICAL_RECONSTRUCTION"],
    }
    data["hash"] = fingerprint(data)
    return data


async def queue_report_notification(project_id, report_id, user_id, kind, event_key, session=None):
    await database.value.report_notifications.update_one(
        {"user_id": user_id, "event_key": event_key},
        {"$setOnInsert": {"_id": new_id("RNTF"), "user_id": user_id, "project_id": project_id, "report_id": report_id, "kind": kind, "event_key": event_key, "status": "PENDING", "attempts": 0, "next_attempt_at": now(), "created_at": now(), "updated_at": now()}},
        upsert=True, session=session,
    )


async def create_report(project_id, payload, user, session=None):
    project = await get_project(project_id, user, "workreport.write")
    config = await get_settings(project_id, user)
    if not config["enabled"] or payload.kind not in config["allowed_kinds"]:
        fail("PROJECT_REPORTING_DISABLED", 403)
    permissions = await member_permissions(project_id, user.id)
    if "workreport.manage" not in permissions and (
        payload.owner_id != user.id
        or payload.kind != "PERSONAL"
        or set(payload.subject_ids) - {user.id}
    ):
        fail("REPORT_ASSIGNMENT_MANAGEMENT_REQUIRED", 403)
    request_hash = fingerprint(payload.model_dump(mode="json"))
    existing = await repository.find(COLLECTION, {"project_id": project_id, "created_by": user.id, "idempotency_key": payload.idempotency_key}, session=session)
    if existing:
        if existing.get("request_hash") != request_hash:
            fail("REPORT_IDEMPOTENCY_CONFLICT")
        return existing
    await participants(project_id, payload, user.id)
    template = await repository.find("report_templates", {"_id": payload.template_version_id, "project_id": project_id}, session=session)
    if not template or template["kind"] != payload.kind:
        fail("REPORT_TEMPLATE_NOT_FOUND", 422)
    content = validate_report_document(template["content_doc"])
    from src.core.common import load_user_identities
    identities = await load_user_identities([payload.owner_id, payload.reviewer_id, user.id])
    owner = identities.get(payload.owner_id) or {}
    reviewer = identities.get(payload.reviewer_id) or {}
    creator = identities.get(user.id) or {}
    report_id = new_id("RPT")
    from src.modules.execution.services.report_assets import normalize_image_urls
    content = normalize_image_urls(content, project_id, report_id)
    timestamp = now()
    record = {"_id": report_id, "series_id": report_id, "version": 1, "project_id": project_id, "project_key": project.get("key", ""), "project_name": project.get("name", ""), "owner_name": owner.get("label", ""), "reviewer_name": reviewer.get("label", ""), "created_by_name": creator.get("label", ""), **payload.model_dump(), "content_doc": content, "template_snapshot": template, "snapshot": await source_snapshot(project_id, payload), "status": "DRAFT", "revision": 1, "created_by": user.id, "content_author_ids": [user.id], "content_authorship_status": "VERIFIED", "request_hash": request_hash, "created_at": timestamp, "updated_at": timestamp}
    try:
        if session:
            await repository.insert(COLLECTION, record, session=session)
            await queue_report_notification(project_id, report_id, payload.owner_id, "REPORT_ASSIGNED", f"report-assigned:{report_id}", session=session)
            await audit(user.id, "report_created", "Report", report_id, project_id, session=session)
        else:
            async with await database.client.start_session() as transaction:
                async with transaction.start_transaction():
                    await repository.insert(COLLECTION, record, session=transaction)
                    await queue_report_notification(project_id, report_id, payload.owner_id, "REPORT_ASSIGNED", f"report-assigned:{report_id}", session=transaction)
                    await audit(user.id, "report_created", "Report", report_id, project_id, session=transaction)
    except DuplicateKeyError:
        existing = await repository.find(COLLECTION, {"project_id": project_id, "created_by": user.id, "idempotency_key": payload.idempotency_key})
        if existing and existing.get("request_hash") == request_hash:
            return existing
        fail("REPORT_IDEMPOTENCY_CONFLICT")
    return record


async def list_reports(project_id, user, inbox=False, limit=50, offset=0, search="", status=None):
    await get_project(project_id, user, "workreport.read")
    permissions = await member_permissions(project_id, user.id)
    received = await repository.collection("report_deliveries").distinct("report_id", {"project_id": project_id, "user_id": user.id, "status": {"$in": ["RECEIVED", "VIEWED", "ACKNOWLEDGED"]}, "revoked_at": {"$exists": False}})
    query = {"project_id": project_id}
    if inbox:
        query["$and"] = [
            {"_id": {"$in": received}},
            {"status": {"$in": ["PUBLISHED", "ARCHIVED"]}},
        ]
    else:
        visible = [{"_id": {"$in": received}, "status": {"$in": ["PUBLISHED", "ARCHIVED"]}}]
        if "workreport.write" in permissions:
            visible.extend([{"owner_id": user.id}, {"editor_ids": user.id}])
        if "workreport.review" in permissions:
            visible.append({"reviewer_id": user.id})
        query["$or"] = visible
    if search.strip():
        import re
        query["title"] = {"$regex": re.escape(search.strip()), "$options": "i"}
    if status:
        query["status"] = status
    projection = {"content_doc": 0, "template_snapshot": 0, "snapshot": 0, "published_snapshot": 0, "ai_application_history": 0}
    values = await repository.collection(COLLECTION).find(query, projection).sort([("updated_at", -1), ("_id", -1)]).skip(offset).limit(limit).to_list(limit)
    from src.core.common import load_user_identities
    people = await load_user_identities(item["owner_id"] for item in values)
    return [{**item, "owner_label": (people.get(item["owner_id"]) or {}).get("label") or ""} for item in values]


async def patch_report(report_id, payload, user):
    report = await report_for_user(report_id, user, "write")
    if report["status"] not in {"DRAFT", "APPROVED"}:
        fail("REPORT_NOT_EDITABLE")
    changes = {"updated_at": now()}
    if payload.title is not None:
        changes["title"] = payload.title
    if payload.content_doc is not None:
        try:
            changes["content_doc"] = validate_report_document(payload.content_doc)
            from src.modules.execution.services.report_assets import image_ids, normalize_image_urls, validate_asset_access
            await validate_asset_access(report["project_id"], changes["content_doc"], user, image_ids(report["content_doc"]))
            changes["content_doc"] = normalize_image_urls(changes["content_doc"], report["project_id"], report_id)
        except ValueError as error:
            fail(str(error), 422)
    if payload.participants:
        await get_project(report["project_id"], user, "workreport.manage")
        await participants(report["project_id"], payload.participants, report.get("created_by"))
        changes.update(payload.participants.model_dump())
    if payload.refresh_snapshot:
        if report["status"] != "DRAFT":
            fail("REPORT_SNAPSHOT_REFRESH_REQUIRES_DRAFT")
        changes["snapshot"] = await source_snapshot(report["project_id"], ReportCreate.model_validate({key: report[key] for key in ReportCreate.model_fields}))
    if report["status"] == "APPROVED":
        if not payload.reason.strip():
            fail("REPORT_CHANGE_REASON_REQUIRED", 422)
        changes["status"] = "DRAFT"
    changes = content_authorship_changes(report, user, changes)
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await repository.change(COLLECTION, {"_id": report_id, "revision": payload.expected_revision, "status": report["status"]}, {"$set": changes, "$unset": {"approved_at": "", "approved_by": "", "approved_hash": ""}, "$inc": {"revision": 1}}, session=session)
            if not updated:
                fail("REPORT_REVISION_CONFLICT")
            await audit(user.id, "report_updated", "Report", report_id, report["project_id"], {"reason": payload.reason, "previous_revision": report["revision"]}, session=session)
    return updated


REPORT_ASSIGNMENT_FIELDS = {
    "_id", "project_id", "title", "kind", "period", "owner_id", "editor_ids",
    "reviewer_id", "recipients", "status", "revision", "due_at", "updated_at",
}


async def list_report_assignments(project_id, user, limit=50, offset=0):
    await get_project(project_id, user, "workreport.manage")
    return await repository.collection(COLLECTION).find(
        {"project_id": project_id}, {key: 1 for key in REPORT_ASSIGNMENT_FIELDS}
    ).sort([("updated_at", -1), ("_id", -1)]).skip(offset).limit(limit).to_list(limit)


async def patch_report_assignments(report_id, payload, user):
    report = await repository.find(COLLECTION, {"_id": report_id})
    if not report:
        fail("REPORT_NOT_FOUND", 404)
    await get_project(report["project_id"], user, "workreport.manage")
    if report["status"] not in {"DRAFT", "IN_REVIEW", "APPROVED"}:
        fail("REPORT_ASSIGNMENTS_IMMUTABLE")
    if not payload.reason.strip():
        fail("REPORT_CHANGE_REASON_REQUIRED", 422)
    await participants(report["project_id"], payload.participants, report.get("created_by"))
    if payload.participants.reviewer_id in set(report.get("content_author_ids") or []):
        fail("REPORT_REVIEWER_MUST_BE_INDEPENDENT", 422)
    from src.core.common import load_user_identities

    identities = await load_user_identities([payload.participants.owner_id, payload.participants.reviewer_id])
    changes = {
        **payload.participants.model_dump(), "status": "DRAFT", "updated_at": now(),
        "owner_name": (identities.get(payload.participants.owner_id) or {}).get("label", ""),
        "reviewer_name": (identities.get(payload.participants.reviewer_id) or {}).get("label", ""),
    }
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await repository.change(
                COLLECTION,
                {"_id": report_id, "project_id": report["project_id"], "revision": payload.expected_revision, "status": report["status"]},
                {"$set": changes, "$unset": {"approved_at": "", "approved_by": "", "approved_hash": ""}, "$inc": {"revision": 1}},
                session=session,
            )
            if not updated:
                fail("REPORT_REVISION_CONFLICT")
            await audit(user.id, "report_assignments_updated", "Report", report_id, report["project_id"], {"reason": payload.reason, "previous_revision": report["revision"]}, session=session)
            if report["owner_id"] != payload.participants.owner_id:
                await queue_report_notification(report["project_id"], report_id, payload.participants.owner_id, "REPORT_ASSIGNED", f"report-assigned:{report_id}:{updated['revision']}", session=session)
    return {key: updated[key] for key in REPORT_ASSIGNMENT_FIELDS if key in updated}


async def transition_report(report_id, payload, user):
    action = payload.action
    if action in {"SUBMIT", "REQUEST_CHANGES", "APPROVE", "PUBLISH"}:
        require_automation_publication_authority(user, f"workreport.{action.lower()}")
    permission = "review" if action in {"APPROVE", "REQUEST_CHANGES"} else "publish" if action == "PUBLISH" else "write"
    report = await report_for_user(report_id, user, permission)
    existing = await repository.find("report_actions", {"report_id": report_id, "actor_id": user.id, "idempotency_key": payload.idempotency_key})
    request_hash = fingerprint(payload.model_dump())
    if existing:
        if existing["request_hash"] != request_hash:
            fail("REPORT_IDEMPOTENCY_CONFLICT")
        return existing["result"]
    states = {"SUBMIT": ("DRAFT", "IN_REVIEW"), "REQUEST_CHANGES": ("IN_REVIEW", "DRAFT"), "APPROVE": ("IN_REVIEW", "APPROVED"), "PUBLISH": ("APPROVED", "PUBLISHED"), "ARCHIVE": ("PUBLISHED", "ARCHIVED")}
    if action == "NEW_VERSION":
        return await new_report_version(report_id, payload, user)
    source, target = states[action]
    if report["status"] != source:
        fail("REPORT_TRANSITION_INVALID")
    if action == "REQUEST_CHANGES" and not payload.note.strip():
        fail("REPORT_CHANGE_REASON_REQUIRED", 422)
    if action == "SUBMIT" and report["reviewer_id"] == user.id:
        fail("REPORT_SELF_REVIEW_FORBIDDEN", 403)
    if action in {"REQUEST_CHANGES", "APPROVE"}:
        await require_independent_review(report, user, "REPORT_SELF_REVIEW_FORBIDDEN")
    if action in {"SUBMIT", "REQUEST_CHANGES", "APPROVE", "PUBLISH"}:
        from src.schemas.reporting import ReportParticipants
        await participants(
            report["project_id"],
            ReportParticipants.model_validate({key: report[key] for key in ReportParticipants.model_fields}),
            report.get("created_by"),
        )
    changes = {"status": target, "updated_at": now(), f"{action.lower()}_by": user.id, f"{action.lower()}_at": now()}
    if action == "APPROVE":
        changes["approved_hash"] = fingerprint({"content_doc": report["content_doc"], "snapshot": report["snapshot"], "participants": {key: report[key] for key in ("owner_id", "editor_ids", "reviewer_id", "recipients")}})
    if action == "PUBLISH":
        from src.modules.execution.services.report_document import REPORT_RENDERER_VERSION
        exports = await repository.list("report_exports", {"report_id": report_id, "revision": report["revision"], "renderer_version": REPORT_RENDERER_VERSION, "status": "READY"}, 10)
        if not exports:
            fail("REPORT_EXPORT_REQUIRED")
        changes.update({"published_export_ids": [item["_id"] for item in exports], "published_source_revision": report["revision"], "published_snapshot": {key: report[key] for key in ("title", "content_doc", "snapshot", "template_version_id", "version")}})
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await repository.change(COLLECTION, {"_id": report_id, "revision": payload.expected_revision, "status": source}, {"$set": changes, "$inc": {"revision": 1}}, session=session)
            if not updated:
                fail("REPORT_REVISION_CONFLICT")
            if action in {"SUBMIT", "REQUEST_CHANGES", "APPROVE"}:
                target_user = report["reviewer_id"] if action == "SUBMIT" else report["owner_id"]
                await queue_report_notification(report["project_id"], report_id, target_user, f"REPORT_{action}", f"report-stage:{report_id}:{updated['revision']}", session=session)
            if action == "PUBLISH":
                for recipient in report["recipients"]:
                    await repository.insert("report_deliveries", {"_id": new_id("RDEL"), "report_id": report_id, "project_id": report["project_id"], **recipient, "status": "PENDING", "revision": 1, "created_at": now(), "updated_at": now(), "sender_id": user.id, "version": report["version"]}, session=session)
            await repository.insert("report_actions", {"_id": new_id("RACT"), "report_id": report_id, "actor_id": user.id, "idempotency_key": payload.idempotency_key, "request_hash": request_hash, "result": updated, "created_at": now()}, session=session)
            await audit(user.id, f"report_{action.lower()}", "Report", report_id, report["project_id"], {"note": payload.note, "revision": updated["revision"]}, session=session)
    return updated


async def create_template(project_id, payload, user):
    await get_project(project_id, user, "workreport.manage")
    try:
        validate_report_document(payload.content_doc)
    except ValueError as error:
        fail(str(error), 422)
    from src.modules.execution.services.report_assets import validate_asset_access
    previous = None
    if payload.template_id:
        rows = await repository.list("report_templates", {"project_id": project_id, "template_id": payload.template_id}, 500)
        previous = max(rows, key=lambda item: item["version"]) if rows else None
        if not previous or previous["revision"] != payload.expected_revision:
            fail("REPORT_TEMPLATE_REVISION_CONFLICT")
    preview = None
    if payload.import_preview_id:
        preview = await repository.find("report_template_previews", {"_id": payload.import_preview_id, "project_id": project_id, "created_by": user.id, "expires_at": {"$gt": now()}})
        if not preview:
            fail("REPORT_TEMPLATE_PREVIEW_EXPIRED", 422)
        if set(preview["warnings"]) - set(payload.accepted_warnings):
            fail("REPORT_TEMPLATE_WARNINGS_UNCONFIRMED", 422)
    from src.modules.execution.services.report_assets import image_ids
    await validate_asset_access(project_id, payload.content_doc, user, image_ids(previous["content_doc"]) if previous else ())
    record = {"_id": new_id("RTV"), "template_id": new_id("RTPL"), "project_id": project_id, "name": payload.name, "kind": payload.kind, "content_doc": payload.content_doc, "version": 1, "revision": 1, "created_by": user.id, "created_at": now(), "updated_at": now()}
    if previous:
        record.update({"template_id": previous["template_id"], "version": previous["version"] + 1, "revision": previous["revision"] + 1, "previous_version_id": previous["_id"]})
        for field in ("original_file", "original_artifact_id", "import_warnings"):
            if field in previous:
                record[field] = previous[field]
    if preview:
        record.update({"original_file": preview["original_file"], "original_artifact_id": preview["_id"], "import_warnings": preview["warnings"]})
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            await repository.insert("report_templates", record, session=session)
            await audit(user.id, "report_template_created", "ReportTemplate", record["_id"], project_id, session=session)
    return record


async def add_comment(report_id, payload, user):
    report = await report_for_user(report_id, user)
    delivery = await repository.find("report_deliveries", {"report_id": report_id, "user_id": user.id, "revoked_at": {"$exists": False}})
    permissions = await member_permissions(report["project_id"], user.id)
    privileged = bool(permissions & {"workreport.write", "workreport.review"}) and user.id in {
        report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])
    }
    if not privileged and not (delivery and delivery["access"] == "COMMENT"):
        fail("REPORT_COMMENT_FORBIDDEN", 403)
    if payload.parent_id and not await repository.find("report_comments", {"_id": payload.parent_id, "report_id": report_id}):
        fail("REPORT_COMMENT_PARENT_NOT_FOUND", 422)
    for user_id in payload.mentioned_user_ids:
        if user_id not in {report["owner_id"], report["reviewer_id"], *report.get("editor_ids", []), *(item["user_id"] for item in report["recipients"])}:
            fail("REPORT_MENTION_ACCESS_DENIED", 422)
        await membership(report["project_id"], user_id)
    query = {"report_id": report_id, "created_by": user.id, "idempotency_key": payload.idempotency_key}
    existing = await repository.find("report_comments", query)
    if existing:
        if existing.get("request_hash") != fingerprint(payload.model_dump()):
            fail("REPORT_IDEMPOTENCY_CONFLICT")
        return existing
    value = {"_id": new_id("RCMT"), "project_id": report["project_id"], **query, **payload.model_dump(), "resolved": False, "revision": 1, "report_version": report["version"], "request_hash": fingerprint(payload.model_dump()), "created_at": now(), "updated_at": now()}
    await repository.insert("report_comments", value)
    return value


async def receipt(report_id, user, acknowledge=False):
    await report_for_user(report_id, user)
    query = {"report_id": report_id, "user_id": user.id, "revoked_at": {"$exists": False}}
    delivery = await repository.find("report_deliveries", query)
    if not delivery or delivery["status"] not in {"RECEIVED", "VIEWED", "ACKNOWLEDGED"}:
        fail("REPORT_RECEIPT_NOT_AVAILABLE")
    changes = {"status": "ACKNOWLEDGED" if acknowledge else delivery["status"] if delivery["status"] == "ACKNOWLEDGED" else "VIEWED", "last_viewed_at": now(), "updated_at": now()}
    if not delivery.get("first_viewed_at"):
        changes["first_viewed_at"] = now()
    if acknowledge:
        changes["acknowledged_at"] = now()
    return await repository.change("report_deliveries", query, {"$set": changes})


async def new_report_version(report_id, payload, user):
    report = await report_for_user(report_id, user, "write")
    if report["status"] not in {"PUBLISHED", "ARCHIVED"}:
        fail("REPORT_NEW_VERSION_REQUIRES_PUBLISHED")
    if not payload.note.strip():
        fail("REPORT_CHANGE_REASON_REQUIRED", 422)
    key = {"report_id": report_id, "actor_id": user.id, "idempotency_key": payload.idempotency_key}
    request_hash = fingerprint(payload.model_dump())
    replay = await repository.find("report_actions", key)
    if replay:
        if replay["request_hash"] != request_hash:
            fail("REPORT_IDEMPOTENCY_CONFLICT")
        return replay["result"]
    if report["revision"] != payload.expected_revision:
        fail("REPORT_REVISION_CONFLICT")
    values = {key: report[key] for key in ReportCreate.model_fields}
    values["idempotency_key"] = payload.idempotency_key
    draft_id = new_id("RPT")
    draft = {"_id": draft_id, "series_id": report["series_id"], "version": report["version"] + 1, "previous_version_id": report_id, "project_id": report["project_id"], **values, "content_doc": __import__("copy").deepcopy(report["content_doc"]), "project_name": report.get("project_name", ""), "owner_name": report.get("owner_name", ""), "snapshot": report["snapshot"], "template_snapshot": report["template_snapshot"], "change_reason": payload.note, "status": "DRAFT", "revision": 1, "created_by": user.id, "content_author_ids": [user.id], "content_authorship_status": "VERIFIED", "created_at": now(), "updated_at": now()}
    from src.modules.execution.services.report_assets import normalize_image_urls
    draft["content_doc"] = normalize_image_urls(draft["content_doc"], draft["project_id"], draft_id)
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await repository.insert(COLLECTION, draft, session=session)
                await repository.insert("report_actions", {"_id": new_id("RACT"), **key, "request_hash": request_hash, "result": draft, "created_at": now()}, session=session)
                await audit(user.id, "report_new_version_created", "Report", draft_id, report["project_id"], {"previous_version_id": report_id, "reason": payload.note}, session=session)
    except DuplicateKeyError:
        fail("REPORT_NEW_VERSION_ALREADY_EXISTS")
    return draft


async def change_delivery(report_id, payload, user):
    report = await report_for_user(report_id, user)
    await get_project(report["project_id"], user, "workreport.write" if user.id == report["owner_id"] else "workreport.manage")
    if report["status"] not in {"PUBLISHED", "ARCHIVED"}:
        fail("REPORT_NOT_PUBLISHED")
    if not payload.revoked:
        await membership(report["project_id"], payload.user_id)
    query = {"report_id": report_id, "user_id": payload.user_id}
    changes = {"access": payload.access, "can_download": payload.can_download, "acknowledgment_required": payload.acknowledgment_required, "updated_at": now()}
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            current = await repository.find("report_deliveries", query, session=session)
            if not current:
                if payload.expected_revision != 0 or payload.revoked:
                    fail("REPORT_REVISION_CONFLICT")
                value = {"_id": new_id("RDEL"), **query, "project_id": report["project_id"], **changes, "status": "PENDING", "revision": 1, "version": report["version"], "created_at": now(), "sender_id": user.id}
                await repository.insert("report_deliveries", value, session=session)
            else:
                if payload.revoked:
                    changes.update({"revoked_at": now(), "status": "REVOKED"})
                elif current.get("revoked_at"):
                    changes["status"] = "PENDING"
                value = await repository.change("report_deliveries", {**query, "revision": payload.expected_revision}, {"$set": changes, "$inc": {"revision": 1}, **({"$unset": {"revoked_at": "", "first_viewed_at": "", "last_viewed_at": "", "acknowledged_at": ""}} if not payload.revoked and current.get("revoked_at") else {})}, session=session)
                if not value:
                    fail("REPORT_REVISION_CONFLICT")
            await audit(user.id, "report_delivery_access_changed", "Report", report_id, report["project_id"], {"user_id": payload.user_id, "access": payload.access, "revoked": payload.revoked, "can_download": payload.can_download}, session=session)
    return value


async def resolve_comment(report_id, comment_id, payload, user):
    report = await report_for_user(report_id, user)
    comment = await repository.find("report_comments", {"_id": comment_id, "report_id": report_id})
    if not comment:
        fail("REPORT_COMMENT_NOT_FOUND", 404)
    delivery = await repository.find(
        "report_deliveries",
        {"report_id": report_id, "user_id": user.id, "revoked_at": {"$exists": False}},
    )
    permissions = await member_permissions(report["project_id"], user.id)
    privileged = bool(permissions & {"workreport.write", "workreport.review"}) and user.id in {
        report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])
    }
    can_comment = privileged or bool(delivery and delivery["access"] == "COMMENT")
    if not can_comment:
        fail("REPORT_COMMENT_RESOLVE_FORBIDDEN", 403)
    if user.id not in {comment["created_by"], report["owner_id"], report["reviewer_id"]}:
        fail("REPORT_COMMENT_RESOLVE_FORBIDDEN", 403)
    value = await repository.change("report_comments", {"_id": comment_id, "report_id": report_id, "revision": payload.expected_revision}, {"$set": {"resolved": payload.resolved, "resolved_by": user.id, "updated_at": now()}, "$inc": {"revision": 1}})
    if not value:
        fail("REPORT_REVISION_CONFLICT")
    return value


async def seed_report_templates(project_id, actor_id, session):
    from src.modules.execution.services.report_document import paragraph
    sections = {
        "vi": ["TÓM TẮT TÌNH HÌNH", "KẾT QUẢ TRONG KỲ", "KẾ HOẠCH TIẾP THEO", "RỦI RO VÀ VƯỚNG MẮC", "QUYẾT ĐỊNH VÀ HỖ TRỢ CẦN THIẾT", "GHI CHÚ VỀ SỐ LIỆU"],
        "en": ["EXECUTIVE SUMMARY", "RESULTS DURING THE PERIOD", "NEXT STEPS", "RISKS AND BLOCKERS", "DECISIONS AND SUPPORT REQUIRED", "DATA NOTES"],
    }
    names = {"vi": {"PERSONAL": "Báo cáo cá nhân", "TEAM": "Báo cáo nhóm", "PROJECT": "Báo cáo dự án"}, "en": {"PERSONAL": "Personal report", "TEAM": "Team report", "PROJECT": "Project report"}}
    for locale, headings in sections.items():
        for kind in ("PERSONAL", "TEAM", "PROJECT"):
            template_id = f"standard-{kind}-{locale}"
            summary = "Tại thời điểm {{snapshot.captured_at}}, phạm vi báo cáo có {{metrics.work_items_total}} công việc; {{metrics.work_items_completed_at_capture}} đã hoàn tất và {{metrics.work_items_changed_in_period}} có thay đổi trong kỳ. Số hoàn tất là trạng thái tại thời điểm chốt, không phải lịch sử hoàn tất trong kỳ." if locale == "vi" else "At {{snapshot.captured_at}}, the report scope contains {{metrics.work_items_total}} work items; {{metrics.work_items_completed_at_capture}} are complete and {{metrics.work_items_changed_in_period}} changed during the period. Completion is the captured state, not a historical reconstruction of when work was completed."
            content = [paragraph(summary)]
            content.append(paragraph("SỐ LIỆU CÔNG VIỆC" if locale == "vi" else "WORK ITEM METRICS", 2))
            metric_labels = ["Tổng công việc", "Hoàn tất tại thời điểm chốt", "Có thay đổi trong kỳ"] if locale == "vi" else ["Total work items", "Complete at capture", "Changed during period"]
            content.append({"type": "table", "content": [
                {"type": "tableRow", "content": [{"type": "tableHeader", "content": [paragraph(label)]} for label in metric_labels]},
                {"type": "tableRow", "content": [{"type": "tableCell", "content": [paragraph("{{metrics." + name + "}}")]} for name in ("work_items_total", "work_items_completed_at_capture", "work_items_changed_in_period")]},
            ]})
            for heading in headings:
                content.extend([paragraph(heading, 2), paragraph()])
            template_content = {"type": "doc", "content": content}
            await database.value.report_templates.update_one(
                {"project_id": project_id, "template_id": template_id, "version": 1},
                {"$set": {"kind": kind, "name": names[locale][kind], "language": locale, "content_doc": template_content, "updated_at": now()}, "$setOnInsert": {"_id": new_id("RTV"), "project_id": project_id, "template_id": template_id, "version": 1, "revision": 1, "created_by": actor_id, "created_at": now()}}, upsert=True, session=session,
            )
