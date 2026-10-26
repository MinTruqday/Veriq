from pymongo import ReturnDocument

from src.core.database import database


async def find_completion(report_id, project_id=None):
    query = {"_id": report_id}
    if project_id:
        query["project_id"] = project_id
    return await database.value.test_completion_reports.find_one(query)


async def list_completions(project_id, release_id=None, status=None, limit=200):
    query = {"project_id": project_id}
    if release_id:
        query["release_id"] = release_id
    if status:
        query["status"] = status
    return (
        await database.value.test_completion_reports.find(query)
        .sort([("created_at", -1), ("sequence", -1)])
        .limit(limit)
        .to_list(limit)
    )


async def update_completion(report_id, project_id, expected_revision, allowed_statuses, changes):
    return await database.value.test_completion_reports.find_one_and_update(
        {
            "_id": report_id,
            "project_id": project_id,
            "revision": expected_revision,
            "status": {"$in": sorted(allowed_statuses)},
        },
        {"$set": changes, "$inc": {"revision": 1}},
        return_document=ReturnDocument.AFTER,
    )


async def next_completion_sequence(project_id, release_id):
    counter = await database.value.counters.find_one_and_update(
        {"_id": f"{project_id}:test-completion:{release_id}"},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(counter["value"])


async def count_active_members(project_id, user_ids, active_status):
    return await database.value.project_members.count_documents(
        {"project_id": project_id, "user_id": {"$in": sorted(user_ids)}, "status": active_status}
    )


async def list_monitoring_overrides(snapshot_id, limit=1000):
    return (
        await database.value.test_monitoring_overrides.find({"snapshot_id": snapshot_id})
        .sort("created_at", 1)
        .to_list(limit)
    )


async def find_project_settings(project_id):
    return await database.value.projects.find_one({"_id": project_id}, {"settings": 1})


async def find_ai_result(project_id, idempotency_key):
    return await database.value.ai_results.find_one(
        {"project_id": project_id, "idempotency_key": idempotency_key}
    )


async def insert_ai_result(value):
    await database.value.ai_results.insert_one(value)
    return value


async def find_latest_completion_ai_result(project_id, report_id, result_type):
    return await database.value.ai_results.find_one(
        {
            "project_id": project_id,
            "subject_id": report_id,
            "result_type": result_type,
            "source_event_trigger": "TEST_COMPLETION_REPORT_CREATED",
        },
        sort=[("created_at", -1), ("_id", -1)],
    )


async def find_release(project_id, release_id):
    return await database.value.releases.find_one({"_id": release_id, "project_id": project_id})


async def find_build(project_id, build_id):
    return await database.value.builds.find_one({"_id": build_id, "project_id": project_id})


async def find_strategy(project_id, strategy_id):
    return await database.value.test_strategies.find_one(
        {"_id": strategy_id, "project_id": project_id}
    )


async def list_runs(project_id, identifiers, limit=10000):
    if not identifiers:
        return []
    return await database.value.test_runs.find(
        {"_id": {"$in": identifiers}, "project_id": project_id}
    ).to_list(limit)


async def list_results(project_id, identifiers, limit=50000):
    if not identifiers:
        return []
    return await database.value.test_results.find(
        {"_id": {"$in": identifiers}, "project_id": project_id}
    ).to_list(limit)


async def list_defects(project_id, identifiers, limit=10000):
    if not identifiers:
        return []
    return await database.value.defects.find(
        {"_id": {"$in": identifiers}, "project_id": project_id}
    ).to_list(limit)


async def list_environments(project_id, identifiers, limit=1000):
    if not identifiers:
        return []
    return await database.value.test_environments.find(
        {"_id": {"$in": identifiers}, "project_id": project_id}
    ).to_list(limit)


async def list_active_data_sets(project_id, excluded_status, limit=5000):
    return await database.value.data_sets.find(
        {"project_id": project_id, "status": {"$ne": excluded_status}},
        {"_id": 1, "name": 1, "revision": 1, "status": 1},
    ).to_list(limit)


async def list_approved_automation(project_id, approved_statuses, limit=5000):
    return await database.value.automation_script_drafts.find(
        {"project_id": project_id, "status": {"$in": approved_statuses}},
        {"_id": 1, "status": 1, "revision": 1, "framework": 1, "language": 1},
    ).to_list(limit)


async def list_approved_status_reports(project_id, release_id, approved_statuses, limit=5000):
    return await database.value.test_status_reports.find(
        {"project_id": project_id, "release_id": release_id, "status": {"$in": approved_statuses}},
        {"_id": 1, "status": 1, "approved_snapshot_hash": 1},
    ).to_list(limit)


async def list_archived_test_cases(project_id, archived_statuses, limit=5000):
    return await database.value.test_cases.find(
        {"project_id": project_id, "status": {"$in": archived_statuses}},
        {"_id": 1, "status": 1, "current_version_id": 1},
    ).to_list(limit)


async def list_archived_requirement_documents(project_id, archived_status, limit=5000):
    return await database.value.requirement_documents.find(
        {"project_id": project_id, "status": archived_status}, {"_id": 1, "content_hash": 1}
    ).to_list(limit)


async def find_completion_by_idempotency_key(project_id, idempotency_key):
    return await database.value.test_completion_reports.find_one(
        {"project_id": project_id, "idempotency_key": idempotency_key}
    )


async def find_monitoring_snapshot(project_id, snapshot_id):
    return await database.value.test_monitoring_snapshots.find_one(
        {"_id": snapshot_id, "project_id": project_id}
    )


async def find_test_plan(project_id, plan_id):
    return await database.value.test_plans.find_one({"_id": plan_id, "project_id": project_id})


async def maintenance_summary(project_id, pending_status, applied_statuses):
    impact_analysis_count = await database.value.impact_analyses.count_documents(
        {"project_id": project_id}
    )
    pending_proposal_count = await database.value.maintenance_proposals.count_documents(
        {"project_id": project_id, "status": pending_status}
    )
    applied_proposal_count = await database.value.maintenance_proposals.count_documents(
        {"project_id": project_id, "status": {"$in": applied_statuses}}
    )
    return {
        "impact_analysis_count": impact_analysis_count,
        "pending_proposal_count": pending_proposal_count,
        "applied_proposal_count": applied_proposal_count,
    }


async def insert_completion(value, session=None):
    await database.value.test_completion_reports.insert_one(value, session=session)
    return value


async def find_active_member(project_id, user_id, active_status):
    return await database.value.project_members.find_one(
        {"project_id": project_id, "user_id": user_id, "status": active_status}
    )
