from pymongo import ReturnDocument

from src.core.database import database


async def find_report(report_id, project_id=None):
    query = {"_id": report_id}
    if project_id:
        query["project_id"] = project_id
    return await database.value.test_status_reports.find_one(query)


async def list_reports(project_id, test_plan_id=None, release_id=None, status=None, limit=500):
    query = {"project_id": project_id}
    if test_plan_id:
        query["test_plan_id"] = test_plan_id
    if release_id:
        query["release_id"] = release_id
    if status:
        query["status"] = status
    return (
        await database.value.test_status_reports.find(query)
        .sort([("created_at", -1), ("sequence", -1)])
        .limit(limit)
        .to_list(limit)
    )


async def update_report(report_id, project_id, expected_revision, allowed_statuses, changes):
    return await database.value.test_status_reports.find_one_and_update(
        {
            "_id": report_id,
            "project_id": project_id,
            "revision": expected_revision,
            "status": {"$in": sorted(allowed_statuses)},
        },
        {"$set": changes, "$inc": {"revision": 1}},
        return_document=ReturnDocument.AFTER,
    )


async def next_sequence(project_id, test_plan_id, release_id):
    counter = await database.value.counters.find_one_and_update(
        {"_id": f"{project_id}:test-status-report:{test_plan_id}:{release_id or 'none'}"},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(counter["value"])


async def find_report_by_idempotency(project_id, idempotency_key):
    return await database.value.test_status_reports.find_one(
        {"project_id": project_id, "idempotency_key": idempotency_key}
    )


async def find_monitoring_snapshot(snapshot_id, project_id):
    return await database.value.test_monitoring_snapshots.find_one(
        {"_id": snapshot_id, "project_id": project_id}
    )


async def find_plan(plan_id, project_id):
    return await database.value.test_plans.find_one({"_id": plan_id, "project_id": project_id})


async def find_build(build_id, project_id):
    return await database.value.builds.find_one({"_id": build_id, "project_id": project_id})


async def list_control_actions(project_id, snapshot_id, limit):
    return (
        await database.value.test_control_actions.find(
            {"project_id": project_id, "snapshot_id": snapshot_id}
        )
        .sort("created_at", 1)
        .to_list(limit)
    )


async def insert_report(value, session=None):
    await database.value.test_status_reports.insert_one(value, session=session)
    return value


async def find_ai_result(project_id, idempotency_key):
    return await database.value.ai_results.find_one(
        {"project_id": project_id, "idempotency_key": idempotency_key}
    )


async def find_latest_status_report_narrative(project_id, report_id):
    return await database.value.ai_results.find_one(
        {
            "project_id": project_id,
            "subject_id": report_id,
            "result_type": "STATUS_REPORT_NARRATIVE",
        },
        sort=[("created_at", -1), ("_id", -1)],
    )


async def insert_ai_result(value):
    await database.value.ai_results.insert_one(value)
    return value
