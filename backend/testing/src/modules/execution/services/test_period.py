from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo import ReturnDocument

from src.core.common import audit, get_project, get_project_entity, new_id, now, optimistic_patch
from src.core.database import database
from src.modules.execution.services.result_metrics import result_timestamp


async def list_test_period_records(project_id, user):
    await get_project(project_id, user, "testplan.read")
    return await database.value.test_periods.find(
        {"project_id": project_id}
    ).sort([("sequence", -1)]).to_list(500)


async def create_test_period_record(payload, user):
    await get_project(payload.project_id, user, "testplan.create")
    source_period = None
    if payload.source_period_id:
        source_period = await database.value.test_periods.find_one(
            {"_id": payload.source_period_id, "project_id": payload.project_id}
        )
        if not source_period or source_period.get("status") != "CLOSED":
            raise HTTPException(status_code=422, detail={"code": "TEST_PERIOD_SOURCE_NOT_CLOSED"})
    timestamp = now()
    counter = await database.value.test_period_counters.find_one_and_update(
        {"_id": payload.project_id},
        {"$inc": {"sequence": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    period = {
        "_id": new_id("CYCLE"),
        **payload.model_dump(mode="json"),
        "sequence": counter["sequence"],
        "status": "PLANNED",
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    if source_period:
        period["source_period_id"] = source_period["_id"]
        period["carry_over_items"] = [dict(item) for item in source_period.get("carry_over_items", [])]
    await database.value.test_periods.insert_one(period)
    await audit(user.id, "test_period_created", "TestPeriod", period["_id"], payload.project_id)
    return period


async def get_test_period_record(period_id, user, permission="testplan.read"):
    return await get_project_entity("test_periods", period_id, user, permission)


async def touch_open_test_period(project_id, period_id, session, activate=False):
    if not period_id:
        return None
    timestamp = now()
    changes = {"updated_at": timestamp}
    if activate:
        changes["status"] = "ACTIVE"
    updated = await database.value.test_periods.find_one_and_update(
        {
            "_id": period_id,
            "project_id": project_id,
            "status": {"$in": ["PLANNED", "ACTIVE"]},
        },
        {"$set": changes, "$inc": {"revision": 1}},
        return_document=ReturnDocument.AFTER,
        session=session,
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "TEST_PERIOD_UNAVAILABLE"})
    return updated


async def register_period_activity(project_id, period_id, session):
    if not period_id:
        return None
    period = await database.value.test_periods.find_one(
        {"_id": period_id, "project_id": project_id}, session=session
    )
    if not period:
        raise HTTPException(status_code=409, detail={"code": "TEST_PERIOD_NOT_FOUND"})
    if period.get("status") == "CLOSED":
        return period
    return await touch_open_test_period(project_id, period_id, session)


async def register_test_result_period_activity(project_id, result_id, session):
    if not result_id:
        return None
    result = await database.value.test_results.find_one(
        {"_id": result_id, "project_id": project_id},
        {"test_run_id": 1},
        session=session,
    )
    if not result:
        return None
    run = await database.value.test_runs.find_one(
        {"_id": result.get("test_run_id"), "project_id": project_id},
        {"test_period_id": 1},
        session=session,
    )
    if run and run.get("test_period_id"):
        return await register_period_activity(project_id, run["test_period_id"], session)
    return None


async def update_test_period_record(period_id, payload, user):
    period = await get_test_period_record(period_id, user, "testplan.update")
    if period.get("status") == "CLOSED":
        raise HTTPException(status_code=409, detail={"code": "TEST_PERIOD_CLOSED"})
    changes = payload.model_dump(exclude_unset=True, mode="json")
    changes.pop("expected_revision", None)
    start = changes.get("planned_start_date", period.get("planned_start_date"))
    end = changes.get("planned_end_date", period.get("planned_end_date"))
    if start and end and start > end:
        raise HTTPException(status_code=422, detail={"code": "TEST_PERIOD_END_BEFORE_START"})
    updated = await optimistic_patch(
        "test_periods", period_id, period["project_id"], payload.expected_revision, changes
    )
    await audit(user.id, "test_period_updated", "TestPeriod", period_id, period["project_id"])
    return updated


async def get_test_period_summary(period_id, user):
    period = await get_test_period_record(period_id, user, "testplan.read")
    close_summary = period.get("close_summary")
    if period.get("status") == "CLOSED" and close_summary:
        carry_over_cases = [
            {
                "test_case_version_id": item["test_case_version_id"],
                "test_case_id": item.get("test_case_id"),
                "title": item.get("title") or "Ca kiểm thử",
                "version": item.get("version"),
                "status": item.get("source_status") or "NOT_RUN",
                "source_test_run_id": item.get("source_test_run_id"),
                "source_test_run_name": item.get("source_test_run_name", ""),
                "source_test_plan_id": item.get("source_test_plan_id"),
                "source_test_plan_name": item.get("source_test_plan_name", ""),
                "carry_over_eligible": True,
            }
            for item in period.get("carry_over_items", [])
        ]
        return {
            "period": period,
            **close_summary,
            "cases": carry_over_cases,
        }
    runs = await database.value.test_runs.find(
        {"project_id": period["project_id"], "test_period_id": period_id}
    ).sort([("created_at", 1)]).to_list(5000)
    run_by_id = {run["_id"]: run for run in runs}
    source_run_by_version = {}
    for run in reversed(runs):
        for version_id in run.get("test_case_version_ids", []):
            source_run_by_version.setdefault(version_id, run)
    plans = await database.value.test_plans.find(
        {"project_id": period["project_id"], "test_period_id": period_id, "status": "APPROVED"}
    ).sort([("updated_at", -1), ("created_at", -1)]).to_list(5000)
    source_plan_by_version = {}
    planned_version_ids = []
    for plan in plans:
        snapshot = plan.get("approved_snapshot") or plan
        for version_id in snapshot.get("test_case_version_ids", []):
            if version_id not in source_plan_by_version:
                source_plan_by_version[version_id] = plan
                planned_version_ids.append(version_id)
    results = await database.value.test_results.find(
        {"project_id": period["project_id"], "test_run_id": {"$in": list(run_by_id)}}
    ).to_list(50000) if runs else []
    results.sort(
        key=lambda item: (
            result_timestamp(item) or datetime.min.replace(tzinfo=timezone.utc),
            str(item.get("_id") or ""),
        ),
        reverse=True,
    )
    latest = {}
    for result in results:
        latest.setdefault(result["test_case_version_id"], result)
    version_ids = list(dict.fromkeys([*planned_version_ids, *latest]))
    versions = await database.value.test_case_versions.find(
        {"project_id": period["project_id"], "_id": {"$in": version_ids}},
        {"title": 1, "test_case_id": 1, "version": 1},
    ).to_list(50000) if version_ids else []
    version_by_id = {item["_id"]: item for item in versions}
    items = []
    counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "SKIPPED": 0, "NOT_RUN": 0, "IN_PROGRESS": 0}
    for version_id in version_ids:
        result = latest.get(version_id)
        status = (result or {}).get("status", "NOT_RUN")
        counts[status] = counts.get(status, 0) + 1
        run = (
            run_by_id.get(result.get("test_run_id"), {})
            if result else source_run_by_version.get(version_id, {})
        )
        source_plan = source_plan_by_version.get(version_id)
        version = version_by_id.get(version_id, {})
        items.append({
            "test_case_version_id": version_id,
            "test_case_id": version.get("test_case_id"),
            "title": version.get("title") or "Ca kiểm thử",
            "version": version.get("version"),
            "status": status,
            "source_test_run_id": run.get("_id"),
            "source_test_run_name": run.get("name", ""),
            "source_test_plan_id": source_plan.get("_id") if source_plan else None,
            "source_test_plan_name": source_plan.get("name", "") if source_plan else "",
            "updated_at": result.get("updated_at") if result else None,
            "carry_over_eligible": status in {"NOT_RUN", "IN_PROGRESS", "FAIL", "BLOCKED", "SKIPPED"},
        })
    result_ids = [result["_id"] for result in results]
    defect_ids = list(dict.fromkeys(
        defect_id for result in results for defect_id in result.get("linked_defect_ids", [])
    ))
    defects = await database.value.defects.find(
        {
            "project_id": period["project_id"],
            "$or": [
                {"linked_test_result_id": {"$in": result_ids}},
                {"_id": {"$in": defect_ids}},
            ],
        },
        {"status": 1, "severity": 1},
    ).to_list(50000) if result_ids or defect_ids else []
    return {
        "period": period,
        "run_count": len(runs),
        "open_run_count": sum(run.get("status") not in {"COMPLETED", "ABORTED"} for run in runs),
        "case_count": len(items),
        "latest_case_statuses": counts,
        "open_defect_count": sum(item.get("status") not in {"CLOSED", "RESOLVED"} for item in defects),
        "cases": items,
    }


async def close_test_period_record(period_id, payload, user):
    period = await get_test_period_record(period_id, user, "testplan.update")
    if period.get("status") == "CLOSED":
        raise HTTPException(status_code=409, detail={"code": "TEST_PERIOD_CLOSED"})
    summary = await get_test_period_summary(period_id, user)
    eligible = {
        (item.get("source_test_run_id") or item.get("source_test_plan_id"), item["test_case_version_id"]): item
        for item in summary["cases"] if item["carry_over_eligible"]
    }
    selected = []
    seen = set()
    for value in payload.carry_over_items:
        source_id = value.source_test_run_id or value.source_test_plan_id
        key = (source_id, value.test_case_version_id)
        if key in seen or key not in eligible:
            raise HTTPException(status_code=422, detail={"code": "TEST_PERIOD_CARRY_OVER_INVALID"})
        seen.add(key)
        item = value.model_dump()
        item["source_test_run_id"] = item.get("source_test_run_id") or None
        item["source_test_plan_id"] = item.get("source_test_plan_id") or None
        item["source_period_id"] = period_id
        item["source_period_name"] = period["name"]
        item["source_status"] = eligible[key]["status"]
        item["test_case_id"] = eligible[key].get("test_case_id")
        item["title"] = eligible[key].get("title")
        item["version"] = eligible[key].get("version")
        item["source_test_run_name"] = eligible[key].get("source_test_run_name", "")
        item["source_test_plan_name"] = eligible[key].get("source_test_plan_name", "")
        selected.append(item)
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            open_run_count = await database.value.test_runs.count_documents(
                {
                    "project_id": period["project_id"],
                    "test_period_id": period_id,
                    "status": {"$nin": ["COMPLETED", "ABORTED"]},
                },
                session=session,
            )
            if open_run_count:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "TEST_PERIOD_HAS_OPEN_RUNS", "count": open_run_count},
                )
            updated = await database.value.test_periods.find_one_and_update(
                {
                    "_id": period_id,
                    "project_id": period["project_id"],
                    "revision": payload.expected_revision,
                    "status": {"$in": ["PLANNED", "ACTIVE"]},
                },
                {
                    "$set": {
                        "status": "CLOSED",
                        "closed_at": now(),
                        "closed_by": user.id,
                        "close_note": payload.note.strip(),
                        "carry_over_items": selected,
                        "close_summary": {
                            "run_count": summary["run_count"],
                            "open_run_count": 0,
                            "case_count": summary["case_count"],
                            "latest_case_statuses": summary["latest_case_statuses"],
                            "open_defect_count": summary["open_defect_count"],
                            "captured_at": now(),
                        },
                        "updated_at": now(),
                    },
                    "$inc": {"revision": 1},
                },
                return_document=ReturnDocument.AFTER,
                session=session,
            )
            if not updated:
                raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
            await audit(
                user.id,
                "test_period_closed",
                "TestPeriod",
                period_id,
                period["project_id"],
                {"carry_over_count": len(selected), "note": payload.note.strip()},
                session=session,
            )
    return updated


