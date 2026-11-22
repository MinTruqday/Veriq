from datetime import date, timedelta

from fastapi import HTTPException

from src.core.common import now
from src.core.database import database
from src.repositories.test_run import test_run_repository


async def _project_capacity_limits(
    user_ids,
    period_start=None,
    period_end=None,
    *,
    session=None,
    fence_periods=False,
):
    if not user_ids:
        return "CAPACITY_NOT_DECLARED", {}
    start = str(period_start or now().date().isoformat())[:10]
    end = str(period_end or start)[:10]
    periods = await database.value.resource_capacity_periods.find(
        {"period_start": {"$lte": end}, "period_end": {"$gte": start}},
        session=session,
    ).to_list(100)
    if fence_periods and session is not None:
        for period in sorted(periods, key=lambda item: item["_id"]):
            fenced = await database.value.resource_capacity_periods.update_one(
                {"_id": period["_id"], "revision": period.get("revision", 1)},
                {"$inc": {"assignment_fence_revision": 1}},
                session=session,
            )
            if fenced.matched_count != 1:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "RESOURCE_CAPACITY_CHANGED_RETRY_ASSIGNMENT"},
                )
    if not periods:
        if await database.value.resource_capacity_periods.count_documents(
            {}, session=session
        ):
            return "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE", {}
        return "CAPACITY_NOT_DECLARED", {}
    periods.sort(key=lambda item: (item.get("period_start", ""), item.get("period_end", "")))
    requested_start = date.fromisoformat(start)
    requested_end = date.fromisoformat(end)
    first_start = date.fromisoformat(periods[0]["period_start"])
    covered_until = date.fromisoformat(periods[0]["period_end"])
    if first_start > requested_start or covered_until < requested_start:
        return "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE", {}
    for period in periods[1:]:
        period_start = date.fromisoformat(period["period_start"])
        period_end = date.fromisoformat(period["period_end"])
        if period_start <= covered_until:
            return "AMBIGUOUS_CAPACITY_PERIOD", {}
        if period_start > covered_until + timedelta(days=1):
            return "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE", {}
        covered_until = max(covered_until, period_end)
    if covered_until < requested_end:
        return "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE", {}
    limits_by_period = [
        {
            item.get("user_id"): item["max_concurrent_projects"]
            for item in period.get("entries") or []
            if item.get("user_id") and item.get("max_concurrent_projects") is not None
        }
        for period in periods
    ]
    user_ids_with_limits = set().union(*(set(item) for item in limits_by_period))
    limits = {
        user_id: min(period_limits[user_id] for period_limits in limits_by_period)
        for user_id in user_ids_with_limits
        if all(user_id in period_limits for period_limits in limits_by_period)
    }
    return "PROJECT_LIMITS_PARTIALLY_DECLARED" if limits else "PROJECT_LIMIT_NOT_DECLARED", limits


async def _check_test_run_assignment_capacity(
    project_id,
    run,
    user_ids,
    *,
    session,
    existing_run_user_ids=(),
):
    user_ids = set(user_ids)
    if not user_ids:
        return
    schedule = run.get("test_plan_schedule_snapshot") or {}
    capacity_status, limits = await _project_capacity_limits(
        sorted(user_ids),
        schedule.get("planned_start_at"),
        schedule.get("planned_end_at"),
        session=session,
        fence_periods=True,
    )
    if not limits:
        return
    project_workload = await _member_project_workload(
        user_ids,
        schedule,
        session=session,
        exclude_run_id=run.get("_id"),
    )
    for user_id in set(existing_run_user_ids).intersection(user_ids):
        project_workload[user_id].add(project_id)
    exceeded = {
        user_id: {
            "active_project_count": len(projects),
            "max_concurrent_projects": limits[user_id],
        }
        for user_id, projects in project_workload.items()
        if user_id in limits
        and project_id not in projects
        and len(projects) >= limits[user_id]
    }
    if exceeded:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MAX_CONCURRENT_PROJECTS_REACHED",
                "users": exceeded,
                "capacity_status": capacity_status,
            },
        )


async def _member_project_workload(
    user_ids,
    schedule,
    *,
    session=None,
    exclude_run_id=None,
    exclude_plan_id=None,
):
    user_ids = set(user_ids)
    workload = {user_id: set() for user_id in user_ids}
    start_value = str(schedule.get("planned_start_at") or now().date().isoformat())[:10]
    end_value = str(schedule.get("planned_end_at") or start_value)[:10]
    async for active_run in test_run_repository.iter_active_runs_for_members(
        sorted(user_ids),
        session=session,
        exclude_run_id=exclude_run_id,
        include_drafts=True,
    ):
        run_schedule = active_run.get("test_plan_schedule_snapshot") or {}
        run_start = str(run_schedule.get("planned_start_at") or "")[:10]
        run_end = str(run_schedule.get("planned_end_at") or "")[:10]
        if (
            run_start
            and run_end
            and (run_start > end_value or run_end < start_value)
        ):
            continue
        assigned = set((active_run.get("test_case_assignments") or {}).values())
        if active_run.get("assignee_id"):
            assigned.add(active_run["assignee_id"])
        project_id = active_run.get("project_id")
        if project_id:
            for user_id in assigned.intersection(user_ids):
                workload[user_id].add(project_id)

    plan_query = {
        "status": {"$in": ["IN_REVIEW", "APPROVED"]},
        "schedule.planned_start_at": {"$lte": f"{end_value}T23:59:59.999999"},
        "schedule.planned_end_at": {"$gte": start_value},
    }
    if exclude_plan_id:
        plan_query["_id"] = {"$ne": exclude_plan_id}
    plans = database.value.test_plans.find(
        plan_query,
        {
            "project_id": 1,
            "schedule.planned_start_at": 1,
            "schedule.planned_end_at": 1,
            "estimation.effort_allocations": 1,
        },
        session=session,
    )
    async for plan in plans:
        other_schedule = plan.get("schedule") or {}
        other_start = str(other_schedule.get("planned_start_at") or "")[:10]
        other_end = str(other_schedule.get("planned_end_at") or "")[:10]
        if not other_start or not other_end or other_start > end_value or other_end < start_value:
            continue
        project_id = plan.get("project_id")
        if not project_id:
            continue
        for allocation in (plan.get("estimation") or {}).get("effort_allocations") or []:
            user_id = allocation.get("user_id")
            if user_id in user_ids:
                workload[user_id].add(project_id)
    return workload


async def _check_test_plan_assignment_capacity(
    project_id,
    schedule,
    user_ids,
    *,
    session,
    exclude_plan_id=None,
):
    user_ids = set(user_ids)
    if not user_ids:
        return
    start = (schedule or {}).get("planned_start_at")
    end = (schedule or {}).get("planned_end_at")
    if not start or not end:
        return
    capacity_status, limits = await _project_capacity_limits(
        sorted(user_ids), start, end, session=session, fence_periods=True
    )
    if not limits:
        return
    workload = await _member_project_workload(
        user_ids,
        schedule,
        session=session,
        exclude_plan_id=exclude_plan_id,
    )
    exceeded = {
        user_id: {
            "active_project_count": len(projects),
            "max_concurrent_projects": limits[user_id],
        }
        for user_id, projects in workload.items()
        if user_id in limits
        and project_id not in projects
        and len(projects) >= limits[user_id]
    }
    if exceeded:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MAX_CONCURRENT_PROJECTS_REACHED",
                "users": exceeded,
                "capacity_status": capacity_status,
            },
        )
