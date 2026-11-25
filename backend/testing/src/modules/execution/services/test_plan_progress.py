from datetime import datetime, timezone

from fastapi import HTTPException

from src.core.common import get_project
from src.modules.execution.services.test_plan import verified_approved_plan_snapshot
from src.repositories.test_plan_progress import test_plan_progress_repository

OPEN_DEFECT_STATUSES = {
    "NEW",
    "CONFIRMED",
    "IN_PROGRESS",
    "READY_FOR_RETEST",
    "REOPENED",
}


def _timestamp(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _latest_results(plan, runs, results):
    snapshot = plan.get("approved_snapshot") or plan
    scope = set(snapshot.get("test_case_version_ids") or [])
    if not scope:
        scope = {
            case_id
            for run in runs
            for case_id in run.get("test_case_version_ids", [])
        }
    if not scope:
        scope = {
            result.get("test_case_version_id")
            for result in results
            if result.get("test_case_version_id")
        }
    latest = {}
    for result in results:
        case_id = result.get("test_case_version_id")
        if case_id not in scope:
            continue
        timestamp = _timestamp(
            result.get("completed_at") or result.get("updated_at") or result.get("created_at")
        )
        rank = (
            timestamp.timestamp() if timestamp else 0,
            str(result.get("_id") or ""),
        )
        if case_id not in latest or rank > latest[case_id][0]:
            latest[case_id] = (rank, result)
    return [latest[case_id][1] if case_id in latest else {"status": "NOT_RUN"} for case_id in scope]


async def get_live_plan_progress(project_id, plan_id, user):
    await get_project(project_id, user, "testrun.read")
    await get_project(project_id, user, "testplan.read")
    plan = await test_plan_progress_repository.find_plan(project_id, plan_id)
    if not plan or plan.get("status") != "APPROVED":
        raise HTTPException(status_code=404, detail={"code": "TEST_PLAN_NOT_APPROVED"})
    verified_approved_plan_snapshot(plan, project_id)
    runs = await test_plan_progress_repository.list_runs(project_id, plan_id, 10000)
    results = await test_plan_progress_repository.list_results(
        project_id, [item["_id"] for item in runs], 50000
    )
    latest = _latest_results(plan, runs, results)
    statuses = {
        status: sum(item.get("status") == status for item in latest)
        for status in (
            "NOT_RUN",
            "IN_PROGRESS",
            "PASS",
            "FAIL",
            "BLOCKED",
            "SKIPPED",
            "NOT_APPLICABLE",
        )
    }
    executed = sum(statuses[status] for status in ("PASS", "FAIL", "BLOCKED"))
    if len(runs) >= 10000 or len(results) >= 50000:
        raise HTTPException(status_code=409, detail={"code": "PLAN_PROGRESS_SCOPE_TOO_LARGE"})
    result_ids = {item["_id"] for item in results}
    defect_ids = {item for result in results for item in result.get("linked_defect_ids", [])}
    defects = await test_plan_progress_repository.list_defects(
        project_id, result_ids, defect_ids, 50000
    )
    if len(defects) >= 50000:
        raise HTTPException(status_code=409, detail={"code": "PLAN_PROGRESS_SCOPE_TOO_LARGE"})
    linked_open = [
        defect
        for defect in defects
        if defect.get("status") in OPEN_DEFECT_STATUSES
        and (
            defect.get("linked_test_result_id") in result_ids
            or defect.get("_id") in defect_ids
        )
    ]
    critical_high = sum(
        str(defect.get("severity") or "").strip().casefold()
        in {"critical", "high", "nghiêm trọng", "cao"}
        for defect in linked_open
    )
    decisive = sum(statuses[status] for status in ("PASS", "FAIL", "BLOCKED"))
    return {
        "total": len(latest),
        "executed": executed,
        "execution_percent": round(executed * 100 / len(latest), 2) if latest else None,
        "pass_rate": round(statuses["PASS"] * 100 / decisive, 2) if decisive else None,
        "statuses": statuses,
        "open_critical_high": critical_high,
    }
