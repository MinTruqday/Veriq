import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.schemas.test_status_report import status_report_hash, status_report_snapshot
from src.repositories.test_status_report import (
    find_ai_result,
    find_build,
    find_monitoring_snapshot,
    find_plan,
    find_report,
    find_report_by_idempotency,
    insert_ai_result,
    insert_report,
    list_control_actions,
    list_reports,
    next_sequence,
    update_report,
)
from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.modules.execution.services.test_monitoring import effective_snapshot





def default_recommendation(snapshot):
    
    status = snapshot.get("effective_quality_gate_status") or snapshot.get("quality_gate_status")
    if snapshot.get("blockers"):
        return 'BLOCKED'
    if status == 'PASS':
        return 'ON_TRACK'
    if status == 'FAIL':
        return 'NOT_READY'
    return 'AT_RISK'


def text_document(value):
    return (
        {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": value}]}],
        }
        if value
        else {"type": "doc", "content": []}
    )


def normalized_forecast(value):
    if isinstance(value, str):
        return {
            "expected_completion_at": None,
            "confidence": None,
            "assumptions": [value] if value.strip() else [],
        }
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value or {"expected_completion_at": None, "confidence": None, "assumptions": []}


def generated_summaries(snapshot):
    metrics = snapshot.get("metrics") or {}
    progress = 'Đã thực thi {executed}/{planned} ca kiểm thử đạt {percent}%'.format(
        executed=metrics.get("executed_test_count", 0),
        planned=metrics.get("planned_test_count", 0),
        percent=metrics.get("execution_percent", 0),
    )
    coverage = (
        'Độ phủ yêu cầu {requirements}% điều kiện kiểm thử {conditions}% và rủi ro {risks}%'.format(
            requirements=metrics.get("requirement_coverage", 0),
            conditions=metrics.get("test_condition_coverage", 0),
            risks=metrics.get("risk_coverage", 0),
        )
    )
    defects = (
        'Lỗi đang mở gồm {blocker} blocker và {critical} critical với {reopened} lỗi mở lại'.format(
            blocker=metrics.get("open_blocker", 0),
            critical=metrics.get("open_critical", 0),
            reopened=metrics.get("reopened", 0),
        )
    )
    return progress, coverage, defects


async def get_report_for_user(report_id, user, permission=None):
    report = await find_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail={"code": 'STATUS_REPORT_NOT_FOUND'})
    await get_project(report["project_id"], user, permission or 'teststatusreport.read')
    return report


async def list_status_reports(project_id, test_plan_id, release_id, status, limit, user):
    await get_project(project_id, user, 'teststatusreport.read')
    return await list_reports(project_id, test_plan_id, release_id, status, limit)


async def generate_status_report(project_id, payload, user):
    
    await get_project(project_id, user, 'teststatusreport.create')
    if payload.idempotency_key:
        existing = await find_report_by_idempotency(
            project_id, payload.idempotency_key
        )
        if existing:
            if (
                existing.get("snapshot_id") != payload.snapshot_id
                or existing.get("build_id") != payload.build_id
            ):
                raise HTTPException(status_code=409, detail={"code": 'IDEMPOTENCY_CONFLICT'})
            return existing
    snapshot = await find_monitoring_snapshot(payload.snapshot_id, project_id)
    if not snapshot:
        raise HTTPException(status_code=422, detail={"code": 'INVALID_MONITORING_SNAPSHOT'})
    snapshot = await effective_snapshot(snapshot)
    plan = await find_plan(snapshot["test_plan_id"], project_id)
    if not plan:
        raise HTTPException(status_code=422, detail={"code": 'TEST_PLAN_NOT_FOUND'})
    build = await find_build(payload.build_id, project_id)
    if not build:
        raise HTTPException(status_code=422, detail={"code": 'INVALID_BUILD'})
    release_id = snapshot.get("release_id")
    if release_id and build.get("release_id") and build["release_id"] != release_id:
        raise HTTPException(status_code=422, detail={"code": 'BUILD_RELEASE_MISMATCH'})
    actions = await list_control_actions(
        project_id, snapshot["_id"], 5000
    )
    progress, coverage, defects = generated_summaries(snapshot)
    recommendation = default_recommendation(snapshot)
    if payload.recommendation and payload.recommendation != recommendation:
        raise HTTPException(
            status_code=422,
            detail={"code": 'STATUS_REPORT_RECOMMENDATION_MISMATCH', "expected": recommendation},
        )
    timestamp = now()
    report = {
        "_id": new_id('TSR'),
        "project_id": project_id,
        "idempotency_key": payload.idempotency_key,
        "test_plan_id": snapshot["test_plan_id"],
        "strategy_version_id": plan.get("strategy_version_id"),
        "release_id": release_id,
        "build_id": build["_id"],
        "reporting_period": payload.reporting_period.model_dump(),
        "reporting_period_start": payload.reporting_period.start_at,
        "reporting_period_end": payload.reporting_period.end_at,
        "snapshot_id": snapshot["_id"],
        "snapshot_source_fingerprint": snapshot["source_fingerprint"],
        "snapshot_basis": {
            "snapshot_at": snapshot["snapshot_at"],
            "metrics": snapshot.get("metrics", {}),
            "exit_criteria_evaluation": snapshot.get("effective_exit_criteria_evaluation", []),
            "quality_gate_status": snapshot.get(
                "effective_quality_gate_status", snapshot.get("quality_gate_status")
            ),
            "plan_revision": snapshot.get("plan_revision"),
            "plan_snapshot_hash": snapshot.get("plan_snapshot_hash"),
        },
        "executive_summary": payload.executive_summary,
        "executive_summary_doc": text_document(payload.executive_summary),
        "progress_summary": progress,
        "coverage_summary": coverage,
        "defect_summary": defects,
        "maintenance_summary": (snapshot.get("source_state") or {}).get("maintenance", {}),
        "deviations": snapshot.get("deviations", []),
        "blockers": snapshot.get("blockers", []),
        "risks": snapshot.get("risks", []),
        "control_actions": [
            {
                key: action.get(key)
                for key in (
                    "_id",
                    "type",
                    "title",
                    "description",
                    "owner_id",
                    "due_at",
                    "priority",
                    "status",
                    "decision_reason",
                    "evidence_refs",
                )
            }
            for action in actions
        ],
        "control_action_ids": [action["_id"] for action in actions],
        "risk_explanation": "",
        "forecast": normalized_forecast(payload.forecast),
        "recommendation": recommendation,
        "recommendation_narrative": "",
        "distribution": payload.distribution,
        "evidence_refs": payload.evidence_refs,
        "status": 'DRAFT',
        "sequence": await next_sequence(project_id, snapshot["test_plan_id"], release_id),
        "review_history": [],
        "approval_history": [],
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await insert_report(report)
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await find_report_by_idempotency(
                project_id, payload.idempotency_key
            )
            if (
                existing
                and existing.get("snapshot_id") == payload.snapshot_id
                and existing.get("build_id") == payload.build_id
            ):
                return existing
        raise
    await audit(
        user.id,
        'status_report_created',
        'TestStatusReport',
        report["_id"],
        project_id,
        {"snapshot_id": snapshot["_id"], "source_fingerprint": snapshot["source_fingerprint"]},
    )
    return report


async def update_status_report(report_id, payload, user):
    
    report = await get_report_for_user(report_id, user, 'teststatusreport.update')
    if report["status"] != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'STATUS_REPORT_IMMUTABLE'})
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    changes.pop("expected_revision", None)
    if "executive_summary" in changes:
        changes["executive_summary_doc"] = text_document(changes["executive_summary"])
    if "forecast" in changes:
        changes["forecast"] = normalized_forecast(changes["forecast"])
    changes["updated_at"] = now()
    updated = await update_report(
        report_id,
        report["project_id"],
        payload.expected_revision,
        {'DRAFT'},
        changes,
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'STATUS_REPORT_REVISION_CONFLICT'})
    await audit(
        user.id,
        'test_status_report_updated',
        'TestStatusReport',
        report_id,
        report["project_id"],
        {"fields": sorted(changes)},
    )
    return updated


async def generate_status_report_narrative(report_id, payload, user):
    
    report = await get_report_for_user(report_id, user, 'teststatusreport.update')
    if report["status"] != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'STATUS_REPORT_IMMUTABLE'})
    existing = await find_ai_result(
        report["project_id"], payload.idempotency_key
    )
    if existing:
        if (
            existing.get("result_type") != 'STATUS_REPORT_NARRATIVE'
            or existing.get("subject_id") != report_id
        ):
            raise HTTPException(status_code=409, detail={"code": 'IDEMPOTENCY_KEY_REUSED'})
        return existing
    narrative_basis = {
        key: report.get(key)
        for key in (
            "snapshot_basis",
            "executive_summary",
            "progress_summary",
            "coverage_summary",
            "defect_summary",
            "deviations",
            "blockers",
            "risks",
            "control_actions",
            "forecast",
            "recommendation",
        )
    }
    narrative_basis["snapshot_basis"] = {
        key: value
        for key, value in (report.get("snapshot_basis") or {}).items()
        if key not in {"plan_snapshot_hash", "source_fingerprint"}
    }
    evidence = [
        {
            "artifact_type": 'test_status_report',
            "artifact_id": report_id,
            "authority": 'PROJECT_RECORD',
            "text": json.dumps(narrative_basis, ensure_ascii=False, default=str),
        }
    ]
    instruction = json.dumps(
        {"user_instruction": payload.instruction},
        ensure_ascii=False,
    )
    ai = await request_ai_automation(
        'status_report_narrative', report["project_id"], instruction, evidence
    )
    result = {
        "_id": new_id('AIR'),
        "project_id": report["project_id"],
        "result_type": 'STATUS_REPORT_NARRATIVE',
        "subject_id": report_id,
        "candidate_only": True,
        "human_confirmation_required": True,
        "suggestions": ai.get("suggestions", []),
        **ai_contract_metadata(ai),
        "idempotency_key": payload.idempotency_key,
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        await insert_ai_result(result)
    except DuplicateKeyError:
        return await find_ai_result(
            report["project_id"], payload.idempotency_key
        )
    await audit(
        user.id,
        'test_status_report_ai_narrative_generated',
        'AIResult',
        result["_id"],
        report["project_id"],
        {"report_id": report_id},
    )
    return result


async def attach_status_report_evidence(report_id, payload, user):
    
    report = await get_report_for_user(report_id, user, 'teststatusreport.update')
    if report["status"] != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'STATUS_REPORT_IMMUTABLE'})
    evidence_refs = list(dict.fromkeys([*report.get("evidence_refs", []), *payload.evidence_refs]))
    updated = await update_report(
        report_id,
        report["project_id"],
        payload.expected_revision,
        {'DRAFT'},
        {"evidence_refs": evidence_refs, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'STATUS_REPORT_REVISION_CONFLICT'})
    await audit(
        user.id,
        'test_status_report_evidence_attached',
        'TestStatusReport',
        report_id,
        report["project_id"],
        {"evidence_refs": payload.evidence_refs},
    )
    return updated


async def transition_status_report(report_id, payload, user, transition_action):
    
    transition = {'submit': {'source': 'DRAFT',
            'target': 'IN_REVIEW',
            'permission': 'teststatusreport.submit_review',
            'event': 'test_status_report_submitted'},
 'request_changes': {'source': 'IN_REVIEW',
                     'target': 'DRAFT',
                     'permission': 'teststatusreport.review',
                     'event': 'test_status_report_changes_requested'},
 'approve': {'source': 'IN_REVIEW',
             'target': 'APPROVED',
             'permission': 'teststatusreport.approve',
             'event': 'status_report_approved'},
 'publish': {'source': 'APPROVED',
             'target': 'PUBLISHED',
             'permission': 'teststatusreport.publish',
             'event': 'status_report_published'},
 'archive': {'source': 'PUBLISHED',
             'target': 'ARCHIVED',
             'permission': 'teststatusreport.archive',
             'event': 'test_status_report_archived'}}[transition_action]
    source = transition["source"]
    target = transition["target"]
    report = await get_report_for_user(report_id, user, transition["permission"])
    timestamp = now()
    event = {"actor_id": user.id, "action": target, "note": payload.note, "at": timestamp}
    changes = {"status": target, "updated_at": timestamp}
    history_field = (
        "approval_history"
        if target in ['APPROVED', 'PUBLISHED']
        else "review_history"
    )
    changes[history_field] = [*report.get(history_field, []), event]
    if target == 'IN_REVIEW':
        changes.update({"submitted_by": user.id, "submitted_at": timestamp})
    elif target == 'DRAFT':
        changes.update(
            {"change_request": payload.note, "reviewed_by": user.id, "reviewed_at": timestamp}
        )
    elif target == 'APPROVED':
        approved_snapshot = status_report_snapshot(report)
        changes.update(
            {
                "approved_by": user.id,
                "approved_at": timestamp,
                "approved_snapshot": approved_snapshot,
                "approved_snapshot_hash": status_report_hash(report),
            }
        )
    elif target == 'PUBLISHED':
        changes.update({"published_by": user.id, "published_at": timestamp})
    updated = await update_report(
        report_id, report["project_id"], payload.expected_revision, {source}, changes
    )
    if not updated:
        raise HTTPException(
            status_code=409,
            detail={"code": 'STATUS_REPORT_TRANSITION_CONFLICT', "expected_status": source},
        )
    await audit(
        user.id,
        transition["event"],
        'TestStatusReport',
        report_id,
        report["project_id"],
        {"from": source, "to": target, "note": payload.note},
    )
    return updated


async def compare_status_reports(report_id, other_report_id, user):
    left = await get_report_for_user(report_id, user)
    right = await find_report(other_report_id, left["project_id"])
    if not right:
        raise HTTPException(
            status_code=404, detail={"code": 'STATUS_REPORT_COMPARE_TARGET_NOT_FOUND'}
        )
    fields = (
        "executive_summary",
        "progress_summary",
        "coverage_summary",
        "defect_summary",
        "deviations",
        "blockers",
        "risks",
        "control_actions",
        "forecast",
        "recommendation",
        "distribution",
        "status",
    )
    changes = [
        {"field": field, "from": left.get(field), "to": right.get(field)}
        for field in fields
        if left.get(field) != right.get(field)
    ]
    return {
        "from_report_id": report_id,
        "to_report_id": other_report_id,
        "from_sequence": left.get("sequence"),
        "to_sequence": right.get("sequence"),
        "changes": changes,
    }
