from fastapi import HTTPException

from src.repositories.test_completion import find_project_settings, list_monitoring_overrides
from src.modules.execution.services.exit_criteria import evaluate_exit_criteria





def default_completion_recommendation(gate, unresolved_items, residual_risks):
    
    if gate == 'FAIL' or any(
        item.get("severity") in set(['blocker', 'critical', 'BLOCKER', 'CRITICAL'])
        for item in unresolved_items
        if isinstance(item, dict)
    ):
        return 'NOT_READY'
    if gate != 'PASS':
        return 'CONTINUE_TESTING'
    if residual_risks:
        return 'READY_WITH_RISK'
    return 'READY_FOR_RELEASE'


async def reevaluate_completion_exit_criteria(plan, snapshot, completed_run_ids):
    evaluations = evaluate_exit_criteria(
        plan.get("quality_targets", []), snapshot.get("metrics") or {}, completed_run_ids
    )
    criterion_ids = {item["criterion_id"] for item in evaluations}
    evaluations.extend(
        dict(item)
        for item in snapshot.get("exit_criteria_evaluation", [])
        if item.get("criterion_id") not in criterion_ids
    )
    overrides = await list_monitoring_overrides(snapshot["_id"])
    latest = {item["criterion_id"]: item for item in overrides}
    for item in evaluations:
        override = latest.get(item["criterion_id"])
        if override:
            item.update({"status": override["status"], "overridden": True, "override": override})
    return evaluations


async def validate_completion_readiness(report):
    
    
    
    
    project = await find_project_settings(report["project_id"]) or {}
    settings = project.get("settings") or {}
    mandatory_incomplete = [
        item.get("run_id")
        for item in (report.get("scope_snapshot") or {}).get("runs", [])
        if item.get("mandatory", True) and item.get("status") != 'COMPLETED'
    ]
    if mandatory_incomplete:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'COMPLETION_REPORT_NOT_READY',
                "reason_code": 'COMPLETION_MANDATORY_RUNS_INCOMPLETE',
                "run_ids": mandatory_incomplete,
            },
        )
    blocker_threshold = int(
        settings.get(
            'completion_open_blocker_threshold',
            0,
        )
        or 0
    )
    open_blockers = int((report.get("defect_summary") or {}).get("open_blocker", 0) or 0)
    if open_blockers > blocker_threshold:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'COMPLETION_REPORT_NOT_READY',
                "reason_code": 'COMPLETION_OPEN_BLOCKER_THRESHOLD_EXCEEDED',
                "open_blockers": open_blockers,
                "threshold": blocker_threshold,
            },
        )
    ownerless_critical = [
        item.get("risk_id")
        for item in report.get("residual_risks", [])
        if item.get("severity") == 'CRITICAL'
        and not item.get("owner_id")
    ]
    if ownerless_critical:
        raise HTTPException(
            status_code=409,
            detail={"code": 'RESIDUAL_RISK_OWNER_REQUIRED', "risk_ids": ownerless_critical},
        )
    failed_criteria = [
        item.get("criterion_id")
        for item in report.get(
            "exit_criteria_evaluations", report.get("exit_criteria_evaluation", [])
        )
        if item.get("status") == 'FAIL'
    ]
    if failed_criteria:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'COMPLETION_REPORT_NOT_READY',
                "reason_code": 'COMPLETION_EXIT_CRITERIA_FAILED',
                "criterion_ids": failed_criteria,
            },
        )
    reasonless_scope = [
        item.get("item_id")
        for item in report.get("unexecuted_scope", [])
        if not str(item.get("reason") or "").strip()
    ]
    if reasonless_scope:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'COMPLETION_REPORT_NOT_READY',
                "reason_code": 'COMPLETION_UNEXECUTED_SCOPE_REASON_REQUIRED',
                "item_ids": reasonless_scope,
            },
        )
