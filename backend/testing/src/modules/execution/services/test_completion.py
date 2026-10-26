from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.ai_automation import emit_test_completion_report_created
from src.core.auth import roles_for_membership
from src.core.common import audit, get_project, new_id, now
from src.core.database import database
from src.modules.execution.services.exit_criteria import quality_gate_status
from src.modules.execution.services.test_completion_automation import completion_ai_result
from src.modules.execution.services.test_completion_query import (
    get_completion_for_user,
    list_completion_reports,
    validate_people,
)
from src.modules.execution.services.test_completion_readiness import (
    default_completion_recommendation,
    reevaluate_completion_exit_criteria,
    validate_completion_readiness,
)
from src.modules.execution.services.test_completion_sources import (
    completion_sources,
    handover_records,
)
from src.modules.execution.services.test_completion_updates import (
    add_completion_lesson,
    add_completion_residual_risk,
    manage_completion_handover,
)
from src.repositories.test_completion import (
    find_active_member,
    find_completion_by_idempotency_key,
    find_latest_completion_ai_result,
    find_monitoring_snapshot,
    find_test_plan,
    insert_completion,
    maintenance_summary,
    next_completion_sequence,
    update_completion,
)
from src.schemas.test_completion import completion_hash, completion_snapshot

OPEN_DEFECT_STATUSES = set(["NEW", "CONFIRMED", "IN_PROGRESS", "READY_FOR_RETEST", "REOPENED"])

__all__ = [
    "add_completion_lesson",
    "add_completion_residual_risk",
    "list_completion_reports",
    "manage_completion_handover",
]


async def create_completion_report(project_id, payload, user):
    await get_project(project_id, user, "testcompletion.create")
    if payload.idempotency_key:
        existing = await find_completion_by_idempotency_key(project_id, payload.idempotency_key)
        if existing:
            if (
                existing.get("monitoring_snapshot_id") != payload.snapshot_id
                or existing.get("build_id") != payload.build_id
            ):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            await emit_test_completion_report_created(existing, user)
            return existing
    snapshot = await find_monitoring_snapshot(project_id, payload.snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=422, detail={"code": "INVALID_MONITORING_SNAPSHOT"})
    plan = await find_test_plan(project_id, snapshot["test_plan_id"])
    if (
        not plan
        or plan.get("status") != "APPROVED"
        or plan.get("approved_snapshot_hash") != snapshot.get("plan_snapshot_hash")
    ):
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_PLAN_SNAPSHOT_INVALID"})
    sources = await completion_sources(project_id, snapshot, plan, payload.build_id)
    (
        release,
        build,
        strategy,
        runs,
        results,
        defects,
        environments,
        data_sets,
        automation,
        status_reports,
        archived_testcases,
        archived_documents,
    ) = sources
    residual_risks = [item.model_dump() for item in payload.residual_risks]
    improvement_actions = [item.model_dump() for item in payload.improvement_actions]
    lessons_learned = [
        {**item.model_dump(), "lesson_id": item.lesson_id or new_id("LESSON")}
        for item in payload.lessons_learned
    ]
    supplied_handover = [item.model_dump() for item in payload.testware_handover]
    supplied_unexecuted = [item.model_dump() for item in payload.unexecuted_scope]
    await validate_people(
        project_id,
        [
            *[item["owner_id"] for item in residual_risks],
            *[item.get("accepted_by") for item in residual_risks],
            *[item["owner_id"] for item in improvement_actions],
            *[item.get("owner_id") for item in lessons_learned],
        ],
    )
    if any(item.get("treatment") != "PENDING" for item in residual_risks):
        raise HTTPException(
            status_code=422, detail={"code": "RESIDUAL_RISK_DECISION_ENDPOINT_REQUIRED"}
        )
    completed_run_ids = sorted(item["_id"] for item in runs if item.get("status") == "COMPLETED")
    metrics = snapshot.get("metrics") or {}
    exit_evaluation = await reevaluate_completion_exit_criteria(plan, snapshot, completed_run_ids)
    gate = quality_gate_status(exit_evaluation)
    open_defects = [item for item in defects if item.get("status") in OPEN_DEFECT_STATUSES]
    generated_unresolved = [
        {
            "type": "DEFECT",
            "defect_id": item["_id"],
            "title": item.get("title"),
            "severity": item.get("severity"),
            "status": item.get("status"),
            "owner_id": item.get("assignee"),
        }
        for item in open_defects
    ]
    omitted = [
        {
            "item_id": result["_id"],
            "item_type": "TEST_RESULT",
            "reason": result.get("reason") or result.get("notes") or "",
            "source_refs": [
                value
                for value in (result.get("test_run_id"), result.get("test_case_version_id"))
                if value
            ],
        }
        for result in results
        if result.get("status") in set(["NOT_RUN", "IN_PROGRESS", "SKIPPED"])
    ]
    unexecuted_scope = [*omitted, *supplied_unexecuted]
    unresolved_items = [*generated_unresolved, *payload.unresolved_items]
    scope_runs = [
        {
            "run_id": item["_id"],
            "revision": item.get("revision"),
            "status": item.get("status"),
            "mandatory": item.get("mandatory", item.get("is_mandatory", True)),
            "frozen_scope_hash": item.get("frozen_scope_hash"),
            "test_case_version_ids": item.get("test_case_version_ids", []),
            "release_id": item.get("release_id"),
            "build_id": item.get("build_id"),
            "environment_id": item.get("environment_id"),
        }
        for item in runs
    ]
    testware = [
        *handover_records(
            "TEST_CASE_VERSION",
            (snapshot.get("source_state") or {}).get("test_case_versions", []),
            "test-case-versions",
        ),
        *handover_records("DATA_SET", data_sets, "data-sets"),
        *handover_records("AUTOMATION_SCRIPT", automation, "automation-scripts"),
        *handover_records("STATUS_REPORT", status_reports, "status-reports"),
        *supplied_handover,
    ]
    archived = [
        {"type": "TEST_CASE", "items": archived_testcases},
        {"type": "REQUIREMENT_DOCUMENT", "items": archived_documents},
        *payload.archived_artifacts,
    ]
    environment_closure = [
        {
            "environment_id": item["_id"],
            "name": item.get("name"),
            "availability": item.get("availability"),
            "status": item.get("status"),
            "revision": item.get("revision"),
        }
        for item in environments
    ] + payload.environment_closure
    recommendation = default_completion_recommendation(gate, unresolved_items, residual_risks)
    if payload.recommendation and payload.recommendation != recommendation:
        raise HTTPException(
            status_code=422,
            detail={"code": "COMPLETION_RECOMMENDATION_MISMATCH", "expected": recommendation},
        )

    maintenance = await maintenance_summary(project_id, "PENDING", ["APPLIED", "EDITED_ACCEPTED"])
    timestamp = now()
    sequence = await next_completion_sequence(project_id, release["_id"])
    report = {
        "_id": new_id("TCP"),
        "project_id": project_id,
        "completion_key": f"{'TCP-'}{sequence:04d}",
        "idempotency_key": payload.idempotency_key,
        "test_plan_id": plan["_id"],
        "release_id": release["_id"],
        "build_id": build["_id"],
        "build_ids": [build["_id"]],
        "strategy_version_id": strategy["_id"],
        "strategy_snapshot_hash": strategy["snapshot_hash"],
        "monitoring_snapshot_id": snapshot["_id"],
        "final_snapshot_id": snapshot["_id"],
        "scope_snapshot": {
            "plan_revision": snapshot.get("plan_revision"),
            "plan_snapshot_hash": snapshot.get("plan_snapshot_hash"),
            "scope_in": (plan.get("approved_snapshot") or {}).get("scope_in", []),
            "scope_out": (plan.get("approved_snapshot") or {}).get("scope_out", []),
            "runs": scope_runs,
            "source_fingerprint": snapshot.get("source_fingerprint"),
        },
        "completed_run_ids": completed_run_ids,
        "execution_summary": {
            key: metrics.get(key)
            for key in (
                "planned_test_count",
                "executed_test_count",
                "execution_percent",
                "pass",
                "fail",
                "blocked",
                "skipped",
                "not_applicable",
                "pass_rate",
            )
        },
        "coverage_summary": {
            key: metrics.get(key)
            for key in (
                "requirement_coverage",
                "acceptance_criteria_coverage",
                "test_condition_coverage",
                "risk_coverage",
                "api_coverage",
                "nfr_coverage",
            )
        },
        "defect_summary": {
            "total": len(defects),
            "open": len(open_defects),
            "open_blocker": metrics.get("open_blocker", 0),
            "open_critical": metrics.get("open_critical", 0),
            "resolved": metrics.get("resolved", 0),
            "reopened": metrics.get("reopened", 0),
        },
        "maintenance_summary": maintenance,
        "unexecuted_scope": unexecuted_scope,
        "unresolved_items": unresolved_items,
        "residual_risks": residual_risks,
        "exit_criteria_evaluation": exit_evaluation,
        "exit_criteria_evaluations": exit_evaluation,
        "quality_gate_status": gate,
        "deviations": [*snapshot.get("deviations", []), *payload.deviations],
        "testware_handover": testware,
        "archived_artifacts": archived,
        "environment_closure": environment_closure,
        "lessons_learned": lessons_learned,
        "improvement_actions": improvement_actions,
        "recommendation": recommendation,
        "executive_summary": "",
        "closure_summary": "",
        "residual_risk_summary": "",
        "recommendation_rationale": "",
        "sign_offs": [],
        "status": "DRAFT",
        "sequence": sequence,
        "revision": 1,
        "review_history": [],
        "approval_history": [],
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    automation_run_id = getattr(user, "_ai_automation_run_id", None)
    if automation_run_id:
        report["automation_run_id"] = str(automation_run_id)
        report["automation_gate_snapshot"] = completion_snapshot(report)
        report["automation_gate_hash"] = completion_hash(report)
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await insert_completion(report, session=session)
                await audit(
                    user.id,
                    "completion_report_created",
                    "TestCompletionReport",
                    report["_id"],
                    project_id,
                    {
                        "release_id": release["_id"],
                        "snapshot_id": snapshot["_id"],
                        "quality_gate_status": gate,
                    },
                    session=session,
                )
                await emit_test_completion_report_created(report, user, session=session)
    except DuplicateKeyError:
        existing = (
            await find_completion_by_idempotency_key(project_id, payload.idempotency_key)
            if payload.idempotency_key
            else None
        )
        if not existing:
            raise
        if (
            existing.get("monitoring_snapshot_id") != payload.snapshot_id
            or existing.get("build_id") != payload.build_id
        ):
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        await emit_test_completion_report_created(existing, user)
        return existing
    return report


async def latest_completion_ai_result(report_id, result_type, user):
    report = await get_completion_for_user(report_id, user, "testcompletion.read")
    result = await find_latest_completion_ai_result(report["project_id"], report_id, result_type)
    if not result:
        return None
    result["stale"] = result.get("source_event_revision") != report.get("revision")
    return result


async def update_completion_report(report_id, payload, user):
    report = await get_completion_for_user(report_id, user, "testcompletion.update")
    if report["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_REPORT_IMMUTABLE"})
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    changes.pop("expected_revision", None)
    if "unresolved_items" in changes:
        generated = [
            item
            for item in report.get("unresolved_items", [])
            if isinstance(item, dict) and item.get("type") == "DEFECT"
        ]
        identities = {
            (item.get("defect_id"), item.get("type"))
            for item in changes["unresolved_items"]
            if isinstance(item, dict)
        }
        if any((item.get("defect_id"), item.get("type")) not in identities for item in generated):
            raise HTTPException(
                status_code=422, detail={"code": "GENERATED_COMPLETION_FACT_IMMUTABLE"}
            )
    if "unexecuted_scope" in changes:
        existing = {
            item.get("item_id")
            for item in report.get("unexecuted_scope", [])
            if item.get("item_type") == "TEST_RESULT"
        }
        incoming = {
            item.get("item_id")
            for item in changes["unexecuted_scope"]
            if item.get("item_type") == "TEST_RESULT"
        }
        if not existing <= incoming:
            raise HTTPException(
                status_code=422, detail={"code": "GENERATED_COMPLETION_FACT_IMMUTABLE"}
            )
    if (
        "residual_risks" in changes
        or "improvement_actions" in changes
        or "lessons_learned" in changes
    ):
        await validate_people(
            report["project_id"],
            [
                *[item["owner_id"] for item in changes.get("residual_risks", [])],
                *[item.get("accepted_by") for item in changes.get("residual_risks", [])],
                *[item["owner_id"] for item in changes.get("improvement_actions", [])],
                *[item.get("owner_id") for item in changes.get("lessons_learned", [])],
            ],
        )
    if "residual_risks" in changes:
        existing_risks = {item.get("risk_id"): item for item in report.get("residual_risks", [])}
        incoming_risk_ids = {item.get("risk_id") for item in changes["residual_risks"]}
        if (
            not incoming_risk_ids <= set(existing_risks)
            or not set(existing_risks) <= incoming_risk_ids
        ):
            await get_project(report["project_id"], user, "testcompletion.risk.manage")
        for item in changes["residual_risks"]:
            previous = existing_risks.get(item.get("risk_id")) or {}
            decision = (
                item.get("treatment"),
                item.get("acceptance_reason"),
                item.get("accepted_by"),
            )
            previous_decision = (
                previous.get("treatment", previous.get("acceptance")),
                previous.get("acceptance_reason"),
                previous.get("accepted_by"),
            )
            if item.get("treatment") != "PENDING" and decision != previous_decision:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "RESIDUAL_RISK_DECISION_ENDPOINT_REQUIRED",
                        "risk_id": item.get("risk_id"),
                    },
                )
    if "lessons_learned" in changes and len(changes["lessons_learned"]) > len(
        report.get("lessons_learned", [])
    ):
        await get_project(report["project_id"], user, "testcompletion.lesson.create")
    if "testware_handover" in changes:
        await get_project(report["project_id"], user, "testcompletion.handover.manage")
    changes["updated_at"] = now()
    updated = await update_completion(
        report_id, report["project_id"], payload.expected_revision, {"DRAFT"}, changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_REPORT_REVISION_CONFLICT"})
    await audit(
        user.id,
        "test_completion_report_updated",
        "TestCompletionReport",
        report_id,
        report["project_id"],
        {"fields": sorted(changes)},
    )
    return updated


async def generate_completion_narrative(report_id, payload, user):
    report = await get_completion_for_user(report_id, user, "testcompletion.update")
    return await completion_ai_result(
        report, payload, user, "completion_report_narrative", "COMPLETION_REPORT_NARRATIVE"
    )


async def cluster_completion_lessons(report_id, payload, user):
    report = await get_completion_for_user(report_id, user, "testcompletion.update")
    if not report.get("lessons_learned"):
        raise HTTPException(status_code=422, detail={"code": "LESSONS_LEARNED_REQUIRED"})
    return await completion_ai_result(
        report, payload, user, "lessons_learned_clustering", "LESSONS_LEARNED_CLUSTERS"
    )


async def decide_residual_risk(report_id, risk_id, payload, user):
    report = await get_completion_for_user(report_id, user, "testcompletion.review")
    mutable_statuses = {"DRAFT", "IN_REVIEW"}
    if report["status"] not in mutable_statuses:
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_REPORT_IMMUTABLE"})
    membership = await find_active_member(report["project_id"], user.id, "ACTIVE")
    risks = [dict(item) for item in report.get("residual_risks", [])]
    risk = next((item for item in risks if item.get("risk_id") == risk_id), None)
    if not risk:
        raise HTTPException(status_code=404, detail={"code": "RESIDUAL_RISK_NOT_FOUND"})
    if risk.get("owner_id") != user.id and not roles_for_membership(membership).intersection(
        {"QA", "BA"}
    ):
        raise HTTPException(status_code=403, detail={"code": "RESIDUAL_RISK_DECISION_DENIED"})
    risk.update(
        {
            "treatment": payload.acceptance,
            "acceptance": payload.acceptance,
            "acceptance_reason": payload.reason,
            "accepted_by": user.id,
            "accepted_at": now(),
            "status": "CLOSED"
            if payload.acceptance in set(["ACCEPTED", "AVOID"])
            else "MONITORING",
        }
    )
    updated = await update_completion(
        report_id,
        report["project_id"],
        payload.expected_revision,
        mutable_statuses,
        {"residual_risks": risks, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_REPORT_REVISION_CONFLICT"})
    event = (
        "residual_risk_accepted"
        if payload.acceptance == "ACCEPTED"
        else "test_completion_residual_risk_decided"
    )
    await audit(
        user.id,
        event,
        "TestCompletionReport",
        report_id,
        report["project_id"],
        {"risk_id": risk_id, "acceptance": payload.acceptance, "reason": payload.reason},
    )
    return updated


async def sign_off_completion(report_id, payload, user):
    report = await get_completion_for_user(report_id, user, "testcompletion.review")
    if report["status"] != "IN_REVIEW":
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_SIGN_OFF_STATE_INVALID"})
    membership = await find_active_member(report["project_id"], user.id, "ACTIVE")
    if not membership:
        raise HTTPException(status_code=403, detail={"code": "PROJECT_MEMBERSHIP_REQUIRED"})
    sign_offs = [item for item in report.get("sign_offs", []) if item.get("user_id") != user.id]
    sign_offs.append(
        {
            "user_id": user.id,
            "role": membership.get("project_role"),
            "decision": payload.decision,
            "note": payload.note,
            "at": now(),
        }
    )
    updated = await update_completion(
        report_id,
        report["project_id"],
        payload.expected_revision,
        {"IN_REVIEW"},
        {"sign_offs": sign_offs, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_REPORT_REVISION_CONFLICT"})
    await audit(
        user.id,
        "test_completion_signed_off",
        "TestCompletionReport",
        report_id,
        report["project_id"],
        {"decision": payload.decision, "role": membership.get("project_role")},
    )
    return updated


async def transition_completion(report_id, payload, user, transition_action):
    transition = {
        "submit_review": {
            "source": "DRAFT",
            "target": "IN_REVIEW",
            "permission": "testcompletion.submit_review",
            "event": "test_completion_submitted",
        },
        "request_changes": {
            "source": "IN_REVIEW",
            "target": "DRAFT",
            "permission": "testcompletion.review",
            "event": "test_completion_changes_requested",
        },
        "approve": {
            "source": "IN_REVIEW",
            "target": "APPROVED",
            "permission": "testcompletion.approve",
            "event": "completion_report_approved",
        },
        "close": {
            "source": "APPROVED",
            "target": "CLOSED",
            "permission": "testcompletion.close",
            "event": "completion_report_closed",
        },
    }[transition_action]
    source = transition["source"]
    target = transition["target"]
    report = await get_completion_for_user(report_id, user, transition["permission"])
    if target == "APPROVED":
        await validate_completion_readiness(report)
        qa_approved = any(
            item.get("role") == "QA" and item.get("decision") == "APPROVE"
            for item in report.get("sign_offs", [])
        )
        if not qa_approved:
            raise HTTPException(status_code=409, detail={"code": "QA_SIGN_OFF_REQUIRED"})
        if any(
            item.get("treatment", item.get("acceptance")) == "PENDING"
            for item in report.get("residual_risks", [])
        ):
            raise HTTPException(
                status_code=409, detail={"code": "RESIDUAL_RISK_ACCEPTANCE_REQUIRED"}
            )
        if any(item.get("decision") == "REJECT" for item in report.get("sign_offs", [])):
            raise HTTPException(status_code=409, detail={"code": "COMPLETION_REJECTION_UNRESOLVED"})
    timestamp = now()
    event = {"actor_id": user.id, "action": target, "note": payload.note, "at": timestamp}
    history_field = (
        "approval_history" if target in set(["APPROVED", "CLOSED"]) else "review_history"
    )
    changes = {
        "status": target,
        "updated_at": timestamp,
        history_field: [*report.get(history_field, []), event],
    }
    if target == "IN_REVIEW":
        changes.update({"submitted_by": user.id, "submitted_at": timestamp})
    elif target == "DRAFT":
        changes.update(
            {
                "reviewed_by": user.id,
                "reviewed_at": timestamp,
                "change_request": payload.note,
                "sign_offs": [],
            }
        )
    elif target == "APPROVED":
        changes.update(
            {
                "approved_by": user.id,
                "approved_at": timestamp,
                "approved_snapshot": completion_snapshot(report),
                "approved_snapshot_hash": completion_hash(report),
            }
        )
    elif target == "CLOSED":
        changes.update({"closed_by": user.id, "closed_at": timestamp})
    updated = await update_completion(
        report_id, report["project_id"], payload.expected_revision, {source}, changes
    )
    if not updated:
        raise HTTPException(
            status_code=409,
            detail={"code": "COMPLETION_TRANSITION_CONFLICT", "expected_status": source},
        )
    await audit(
        user.id,
        transition["event"],
        "TestCompletionReport",
        report_id,
        report["project_id"],
        {"from": source, "to": target, "note": payload.note},
    )
    return updated
