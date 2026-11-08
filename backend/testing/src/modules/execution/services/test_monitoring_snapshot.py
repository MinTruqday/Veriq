from datetime import datetime, timezone

from src.modules.quality.services.defect_classification import (
    defect_is_blocking,
    defect_is_critical,
)
from src.repositories.test_monitoring import test_monitoring_repository

TERMINAL_RESULT_STATUSES = set(['PASS', 'FAIL', 'BLOCKED', 'SKIPPED', 'NOT_APPLICABLE'])
OPEN_DEFECT_STATUSES = set(['NEW', 'CONFIRMED', 'IN_PROGRESS', 'READY_FOR_RETEST', 'REOPENED'])


def percent(numerator, denominator):
    return round(numerator * 100 / denominator, 2) if denominator else 0.0


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


async def monitoring_sources(project_id, plan, release_id, payload):
    
    runs = await test_monitoring_repository.list_test_runs(
        project_id, plan["_id"], release_id, 10000
    )
    run_ids = [item["_id"] for item in runs]
    results = await test_monitoring_repository.list_test_results(
        project_id, run_ids, 50000
    )
    defects = await test_monitoring_repository.list_defects(
        project_id, release_id, 50000
    )
    requirements = await test_monitoring_repository.list_baselined_requirements(
        project_id,
        'BASELINED',
        20000,
    )
    requirement_version_ids = [
        item.get("current_version_id") for item in requirements if item.get("current_version_id")
    ]
    criteria = await test_monitoring_repository.list_acceptance_criteria(
        project_id, requirement_version_ids, 50000
    )
    conditions = await test_monitoring_repository.list_approved_conditions(
        project_id, 'APPROVED', 20000
    )
    version_ids = sorted(
        {version_id for run in runs for version_id in run.get("test_case_version_ids", [])}
    )
    versions = await test_monitoring_repository.list_test_case_versions(
        project_id, version_ids, 50000
    )
    api_operations = await test_monitoring_repository.list_api_operations(
        project_id, 20000
    )
    nfr_plans = await test_monitoring_repository.list_approved_non_functional_plans(
        project_id,
        'APPROVED',
        5000,
    )
    latest = await test_monitoring_repository.find_latest_snapshot(
        project_id, plan["_id"], release_id
    )
    since = (
        latest.get("snapshot_at") if latest else plan.get("approved_at") or plan.get("created_at")
    )
    changes = await test_monitoring_repository.count_requirement_changes(project_id, since)
    impact_pending = await test_monitoring_repository.count_pending_impact_analyses(
        project_id, ['CLOSED', 'COMPLETED']
    )
    proposal_pending = await test_monitoring_repository.count_pending_maintenance_proposals(
        project_id, ['PENDING_REVIEW', 'REVIEWED', 'APPROVED']
    )
    stale = await test_monitoring_repository.count_stale_test_cases(
        project_id, 'NEEDS_UPDATE'
    )
    incidents = await test_monitoring_repository.list_environment_incidents(
        project_id,
        ['OPEN', 'INVESTIGATING', 'MITIGATED'],
        bool(release_id),
        [item.get("build_id") for item in runs if item.get("build_id")],
        run_ids,
        10000,
    )
    return {
        "runs": runs,
        "results": results,
        "defects": defects,
        "requirements": requirements,
        "criteria": criteria,
        "conditions": conditions,
        "versions": versions,
        "api_operations": api_operations,
        "nfr_plans": nfr_plans,
        "changed_requirements": changes,
        "impact_pending": impact_pending,
        "proposal_pending": proposal_pending,
        "stale_testcases": stale,
        "environment_incidents": incidents,
        "since": since,
        "release_id": release_id,
        "actual_effort": payload.actual_effort,
        "expected_completion": payload.expected_completion,
    }


def build_metrics(plan, sources, snapshot_at):
    results = sources["results"]
    counts = {
        status: sum(item.get("status") == status for item in results)
        for status in ['NOT_RUN', 'IN_PROGRESS', 'PASS', 'FAIL', 'BLOCKED', 'SKIPPED', 'NOT_APPLICABLE']
    }
    planned_test_count = len(results)
    executed_test_count = sum(counts[status] for status in TERMINAL_RESULT_STATUSES)
    decisive = sum(counts[status] for status in ['PASS', 'FAIL', 'BLOCKED'])
    versions = sources["versions"]
    covered_requirements = {
        item for version in versions for item in version.get("requirement_version_ids", [])
    }
    covered_criteria = {
        item for version in versions for item in version.get("acceptance_criterion_ids", [])
    }
    covered_conditions = {
        item for version in versions for item in version.get("test_condition_ids", [])
    }
    covered_api_operations = {
        evidence.get("artifact_id") or evidence.get("artifact_version_id")
        for version in versions
        for evidence in version.get("source_evidence", [])
        if evidence.get("artifact_type") == 'api_operation'
    }
    api_operation_ids = {item["_id"] for item in sources["api_operations"]}
    executed_version_ids = {item["_id"] for item in versions}
    covered_nfr_plans = {
        item["_id"]
        for item in sources["nfr_plans"]
        if set(item.get("test_case_version_ids", [])) & executed_version_ids
        or set(item.get("test_condition_ids", [])) & covered_conditions
    }
    condition_ids = {item["_id"] for item in sources["conditions"]}
    assessed_risk_ids = {
        item["_id"]
        for item in sources["conditions"]
        if str(item.get("risk") or "").strip()
    }
    defects = sources["defects"]
    open_defects = [item for item in defects if item.get("status") in OPEN_DEFECT_STATUSES]
    since = sources["since"]
    new_defects = sum(
        1
        for item in defects
        if not since or bool(item.get("created_at") and item["created_at"] > since)
    )
    resolved = sum(
        1
        for item in defects
        if item.get("status") in ['RESOLVED', 'READY_FOR_RETEST', 'CLOSED']
        and (not since or bool(item.get("updated_at") and item["updated_at"] > since))
    )
    reopened = sum(
        1
        for item in defects
        if item.get("status") == 'REOPENED'
        and (not since or bool(item.get("updated_at") and item["updated_at"] > since))
    )
    ages = [
        (snapshot_at - item.get("created_at")).total_seconds() / 86400
        for item in open_defects
        if isinstance(item.get("created_at"), datetime)
    ]
    schedule = plan.get("schedule") or {}
    planned_start = parse_datetime(
        schedule.get("planned_start") or schedule.get("planned_start_at")
    )
    planned_end = parse_datetime(schedule.get("planned_end") or schedule.get("planned_end_at"))
    actual_starts = [
        item.get("started_at")
        for item in sources["runs"]
        if isinstance(item.get("started_at"), datetime)
    ]
    actual_start = min(actual_starts) if actual_starts else None
    expected_completion = sources["expected_completion"]
    schedule_variance = None
    if planned_end and expected_completion:
        schedule_variance = round((expected_completion - planned_end).total_seconds() / 86400, 2)
    planned_effort = (plan.get("estimation") or {}).get("planned_effort_hours")
    actual_effort = sources["actual_effort"]
    return {
        "planned_test_count": planned_test_count,
        "executed_test_count": executed_test_count,
        "execution_denominator": planned_test_count,
        "pass_rate_denominator": decisive,
        "requirement_coverage_denominator": len(sources["requirements"]),
        "acceptance_criteria_coverage_denominator": len(sources["criteria"]),
        "test_condition_coverage_denominator": len(condition_ids),
        "execution_percent": percent(executed_test_count, planned_test_count),
        "pass_rate": percent(counts['PASS'], decisive),
        "not_run": counts['NOT_RUN'],
        "in_progress": counts['IN_PROGRESS'],
        "pass": counts['PASS'],
        "fail": counts['FAIL'],
        "blocked": counts['BLOCKED'],
        "skipped": counts['SKIPPED'],
        "not_applicable": counts['NOT_APPLICABLE'],
        "requirement_coverage": percent(
            len(
                covered_requirements
                & set(item.get("current_version_id") for item in sources["requirements"])
            ),
            len(sources["requirements"]),
        ),
        "acceptance_criteria_coverage": percent(
            len(covered_criteria & set(item["_id"] for item in sources["criteria"])),
            len(sources["criteria"]),
        ),
        "test_condition_coverage": percent(
            len(covered_conditions & condition_ids), len(condition_ids)
        ),
        "risk_coverage": percent(
            len(covered_conditions & assessed_risk_ids), len(assessed_risk_ids)
        ),
        "api_coverage": percent(
            len(covered_api_operations & api_operation_ids), len(api_operation_ids)
        )
        if api_operation_ids
        else None,
        "nfr_coverage": percent(len(covered_nfr_plans), len(sources["nfr_plans"]))
        if sources["nfr_plans"]
        else None,
        "open_blocker": sum(defect_is_blocking(item) for item in open_defects),
        "open_critical": sum(defect_is_critical(item) for item in open_defects),
        "new_defects": new_defects,
        "resolved": resolved,
        "reopened": reopened,
        "defect_aging": round(sum(ages) / len(ages), 2) if ages else 0,
        "changed_requirements": sources["changed_requirements"],
        "stale_testcases": sources["stale_testcases"],
        "impact_pending": sources["impact_pending"],
        "proposal_pending": sources["proposal_pending"],
        "planned_start": planned_start,
        "planned_end": planned_end,
        "actual_start": actual_start,
        "expected_completion": expected_completion,
        "schedule_variance": schedule_variance,
        "planned_effort": planned_effort,
        "actual_effort": actual_effort,
        "effort_variance": round(actual_effort - planned_effort, 2)
        if actual_effort is not None and planned_effort is not None
        else None,
        "open_environment_incidents": len(sources["environment_incidents"]),
        "blocker_environment_incidents": sum(
            defect_is_blocking(item)
            for item in sources["environment_incidents"]
        ),
        "environment_downtime_seconds": sum(
            int(item.get("downtime") or max(0, (snapshot_at - item["observed_at"]).total_seconds()))
            for item in sources["environment_incidents"]
            if isinstance(item.get("observed_at"), datetime)
        ),
    }


def build_deviations(metrics):
    values = []
    if metrics["schedule_variance"] is not None and metrics["schedule_variance"] > 0:
        values.append(
            {
                "type": 'SCHEDULE',
                "planned": 0,
                "actual": metrics["schedule_variance"],
                "unit": "days",
            }
        )
    if metrics["effort_variance"] is not None and metrics["effort_variance"] > 0:
        values.append(
            {
                "type": 'EFFORT',
                "planned": metrics["planned_effort"],
                "actual": metrics["actual_effort"],
                "unit": "hours",
            }
        )
    if metrics["blocked"]:
        values.append(
            {
                "type": 'BLOCKED_TESTS',
                "planned": 0,
                "actual": metrics["blocked"],
                "unit": "tests",
            }
        )
    return values
