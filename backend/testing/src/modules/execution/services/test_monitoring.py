from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.auth import permissions_for_membership
from src.core.common import audit, get_project, new_id, now
from src.schemas.test_monitoring import (
    ControlActionCreate,
    ControlActionPatch,
    ExitCriterionOverride,
    MonitoringSnapshotCreate,
    source_fingerprint,
)
from src.repositories.test_monitoring import test_monitoring_repository
from src.modules.execution.services.exit_criteria import evaluate_exit_criteria, quality_gate_status
from src.modules.quality.services.quality_gate import (
    create_quality_decision,
    export_quality_gate,
    get_quality_gate,
    list_quality_decisions,
)
from src.modules.execution.services.test_monitoring_snapshot import (
    OPEN_DEFECT_STATUSES,
    build_deviations,
    build_metrics,
    monitoring_sources,
)



__all__ = [
    "create_quality_decision",
    "export_quality_gate",
    "get_quality_gate",
    "list_quality_decisions",
]


async def create_monitoring_snapshot(project_id, payload: MonitoringSnapshotCreate, user):
    await get_project(project_id, user, 'testmonitor.snapshot.create')
    plan = await test_monitoring_repository.find_test_plan(payload.test_plan_id, project_id)
    if not plan:
        raise HTTPException(
            status_code=422,
            detail={"code": 'MONITORING_SOURCE_INCOMPLETE', "reason_code": 'INVALID_TEST_PLAN'},
        )
    if plan.get("status") != 'APPROVED' or not plan.get(
        "approved_snapshot_hash"
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'MONITORING_SOURCE_INCOMPLETE',
                "reason_code": 'TEST_PLAN_NOT_APPROVED',
            },
        )
    release_id = payload.release_id or plan.get("release_id")
    if release_id and not await test_monitoring_repository.release_exists(release_id, project_id):
        raise HTTPException(status_code=422, detail={"code": 'INVALID_RELEASE'})
    if payload.idempotency_key:
        existing = await test_monitoring_repository.find_snapshot_by_idempotency(
            project_id, payload.idempotency_key
        )
        if existing:
            if (
                existing.get("test_plan_id") != payload.test_plan_id
                or existing.get("release_id") != release_id
            ):
                raise HTTPException(status_code=409, detail={"code": 'IDEMPOTENCY_CONFLICT'})
            return existing
    timestamp = now()
    sources = await monitoring_sources(project_id, plan, release_id, payload)
    metrics = build_metrics(plan, sources, timestamp)
    evaluations = evaluate_exit_criteria(
        plan.get("quality_targets", []),
        metrics,
        [
            item["_id"]
            for item in sources["runs"]
            if item.get("status") == 'COMPLETED'
        ],
    )
    blocker_incidents = [
        item
        for item in sources["environment_incidents"]
        if item.get("severity") in ['BLOCKER', 'CRITICAL']
    ]
    if blocker_incidents:
        evaluations.append(
            {
                **{'criterion_id': 'ENVIRONMENT-INCIDENT-GATE',
 'criterion': 'Không có incident môi trường blocker hoặc critical',
 'type': 'ENVIRONMENT_INCIDENT_MAX',
 'threshold': 0},
                "actual": len(blocker_incidents),
                "status": 'FAIL',
                "overridden": False,
                "evidence_refs": [item["_id"] for item in blocker_incidents],
            }
        )
    source_state = {
        "plan": {
            "id": plan["_id"],
            "revision": plan["revision"],
            "hash": plan["approved_snapshot_hash"],
        },
        "runs": sorted(
            [
                {
                    "id": item["_id"],
                    "revision": item.get("revision"),
                    "scope_hash": item.get("frozen_scope_hash"),
                    "status": item.get("status"),
                    "test_case_version_ids": sorted(item.get("test_case_version_ids", [])),
                    "release_id": item.get("release_id"),
                    "build_id": item.get("build_id"),
                    "environment_id": item.get("environment_id"),
                }
                for item in sources["runs"]
            ],
            key=lambda item: item["id"],
        ),
        "results": sorted(
            [
                {"id": item["_id"], "revision": item.get("revision"), "status": item.get("status")}
                for item in sources["results"]
            ],
            key=lambda item: item["id"],
        ),
        "defects": sorted(
            [
                {
                    "id": item["_id"],
                    "revision": item.get("revision"),
                    "status": item.get("status"),
                    "severity": item.get("severity"),
                }
                for item in sources["defects"]
            ],
            key=lambda item: item["id"],
        ),
        "conditions": sorted(
            [
                {
                    "id": item["_id"],
                    "revision": item.get("revision"),
                    "hash": item.get("snapshot_hash"),
                }
                for item in sources["conditions"]
            ],
            key=lambda item: item["id"],
        ),
        "requirements": sorted(
            item.get("current_version_id")
            for item in sources["requirements"]
            if item.get("current_version_id")
        ),
        "acceptance_criteria": sorted(item["_id"] for item in sources["criteria"]),
        "test_case_versions": sorted(
            [
                {
                    "id": item["_id"],
                    "requirements": sorted(item.get("requirement_version_ids", [])),
                    "criteria": sorted(item.get("acceptance_criterion_ids", [])),
                    "conditions": sorted(item.get("test_condition_ids", [])),
                }
                for item in sources["versions"]
            ],
            key=lambda item: item["id"],
        ),
        "api_operations": sorted(item["_id"] for item in sources["api_operations"]),
        "nfr_plans": sorted(
            (
                {"id": item["_id"], "revision": item.get("revision")}
                for item in sources["nfr_plans"]
            ),
            key=lambda item: item["id"],
        ),
        "maintenance": {
            "changed_requirements": sources["changed_requirements"],
            "impact_pending": sources["impact_pending"],
            "proposal_pending": sources["proposal_pending"],
            "stale_testcases": sources["stale_testcases"],
        },
        "environment_incidents": sorted(
            [
                {
                    "id": item["_id"],
                    "revision": item.get("revision"),
                    "status": item.get("status"),
                    "severity": item.get("severity"),
                    "environment_id": item.get("environment_id"),
                    "build_id": item.get("build_id"),
                }
                for item in sources["environment_incidents"]
            ],
            key=lambda item: item["id"],
        ),
    }
    snapshot = {
        "_id": new_id('MONS'),
        "project_id": project_id,
        "idempotency_key": payload.idempotency_key,
        "test_plan_id": plan["_id"],
        "release_id": release_id,
        "build_id": plan.get("build_id"),
        "snapshot_at": timestamp,
        "plan_revision": plan["revision"],
        "plan_snapshot_hash": plan["approved_snapshot_hash"],
        "planned": {
            "schedule": plan.get("schedule", {}),
            "estimation": plan.get("estimation", {}),
            "quality_targets": plan.get("quality_targets", []),
            "scope_in": plan.get("scope_in", []),
            "scope_out": plan.get("scope_out", []),
        },
        "actual": {
            "run_ids": [item["_id"] for item in sources["runs"]],
            "result_ids": [item["_id"] for item in sources["results"]],
            "defect_ids": [item["_id"] for item in sources["defects"]],
        },
        "metrics": metrics,
        "exit_criteria_evaluation": evaluations,
        "deviations": build_deviations(metrics),
        "risks": [*plan.get("risk_register", []), *payload.risks],
        "blockers": [
            *payload.blockers,
            *[
                {
                    "defect_id": item["_id"],
                    "severity": item.get("severity"),
                    "title": item.get("title"),
                }
                for item in sources["defects"]
                if item.get("status") in OPEN_DEFECT_STATUSES
                and str(item.get("severity", "")).upper()
                == 'BLOCKER'
            ],
            *[
                {
                    "environment_incident_id": item["_id"],
                    "severity": item.get("severity"),
                    "description": item.get("description"),
                }
                for item in blocker_incidents
            ],
        ],
        "quality_gate_status": quality_gate_status(evaluations),
        "source_fingerprint": source_fingerprint(source_state),
        "source_state": source_state,
        "created_by": user.id,
        "created_at": timestamp,
        "revision": 1,
    }
    gate_evaluation = {
        "_id": new_id('QGTE'),
        "project_id": project_id,
        "test_plan_id": plan["_id"],
        "release_id": release_id,
        "snapshot_id": snapshot["_id"],
        "rules": evaluations,
        "overall_status": snapshot["quality_gate_status"],
        "blocking_reasons": [
            item
            for item in evaluations
            if item.get("status") == 'FAIL'
        ],
        "warning_reasons": [
            item
            for item in evaluations
            if item.get("status") in ['WARN', 'INSUFFICIENT_DATA', 'MANUAL_REQUIRED']
        ],
        "evaluated_at": timestamp,
        "engine_version": 'exit_criteria',
    }
    snapshot["gate_evaluation_id"] = gate_evaluation["_id"]
    try:
        await test_monitoring_repository.insert_snapshot(snapshot)
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await test_monitoring_repository.find_snapshot_by_idempotency(
                project_id, payload.idempotency_key
            )
            if (
                existing
                and existing.get("test_plan_id") == payload.test_plan_id
                and existing.get("release_id") == release_id
            ):
                return existing
        raise
    await test_monitoring_repository.insert_gate_evaluation(gate_evaluation)
    await audit(
        user.id,
        'monitoring_snapshot_created',
        'TestMonitoringSnapshot',
        snapshot["_id"],
        project_id,
        {
            "source_fingerprint": snapshot["source_fingerprint"],
            "quality_gate_status": snapshot["quality_gate_status"],
        },
    )
    await audit(
        user.id,
        'exit_criteria_evaluated',
        'TestMonitoringSnapshot',
        snapshot["_id"],
        project_id,
        {
            "criterion_count": len(evaluations),
            "quality_gate_status": snapshot["quality_gate_status"],
        },
    )
    await audit(
        user.id,
        'quality_gate_evaluated',
        'QualityGateEvaluation',
        gate_evaluation["_id"],
        project_id,
        {"snapshot_id": snapshot["_id"], "overall_status": gate_evaluation["overall_status"]},
    )
    return snapshot


async def effective_snapshot(snapshot):
    overrides = await test_monitoring_repository.list_overrides(
        snapshot["_id"], 1000
    )
    effective = [dict(item) for item in snapshot.get("exit_criteria_evaluation", [])]
    latest = {item["criterion_id"]: item for item in overrides}
    for item in effective:
        override = latest.get(item["criterion_id"])
        if override:
            item.update({"status": override["status"], "overridden": True, "override": override})
    return {
        **snapshot,
        "effective_exit_criteria_evaluation": effective,
        "effective_quality_gate_status": quality_gate_status(effective),
        "overrides": overrides,
    }


async def get_snapshot_for_user(snapshot_id, user):
    snapshot = await test_monitoring_repository.find_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail={"code": 'MONITORING_SNAPSHOT_NOT_FOUND'})
    await get_project(snapshot["project_id"], user, 'testmonitor.read')
    return await effective_snapshot(snapshot)


async def list_monitoring_snapshots(project_id, test_plan_id, release_id, limit, user):
    await get_project(project_id, user, 'testmonitor.read')
    return [
        await effective_snapshot(item)
        for item in await test_monitoring_repository.list_snapshots(
            project_id, test_plan_id, release_id, limit
        )
    ]


async def override_exit_criterion(snapshot_id, payload: ExitCriterionOverride, user):
    snapshot = await test_monitoring_repository.find_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail={"code": 'MONITORING_SNAPSHOT_NOT_FOUND'})
    await get_project(snapshot["project_id"], user, 'testmonitor.exit_criteria.override')
    if payload.expected_revision != snapshot.get("revision", 1):
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    if payload.criterion_id not in {
        item["criterion_id"] for item in snapshot.get("exit_criteria_evaluation", [])
    }:
        raise HTTPException(status_code=404, detail={"code": 'EXIT_CRITERION_NOT_FOUND'})
    value = {
        "_id": new_id('MONO'),
        "project_id": snapshot["project_id"],
        "snapshot_id": snapshot_id,
        **payload.model_dump(exclude={"expected_revision"}),
        "created_by": user.id,
        "created_at": now(),
    }
    await test_monitoring_repository.insert_override(value)
    await audit(
        user.id,
        'test_monitoring_exit_criterion_overridden',
        'TestMonitoringSnapshot',
        snapshot_id,
        snapshot["project_id"],
        {
            "criterion_id": payload.criterion_id,
            "status": payload.status,
            "reason": payload.reason,
            "override_id": value["_id"],
        },
    )
    return await effective_snapshot(snapshot)


async def create_control_action(project_id, payload: ControlActionCreate, user):
    project = await get_project(project_id, user, 'testmonitor.control.create')
    snapshot = await test_monitoring_repository.find_snapshot(payload.snapshot_id, project_id)
    if not snapshot:
        raise HTTPException(status_code=422, detail={"code": 'INVALID_MONITORING_SNAPSHOT'})
    membership = await test_monitoring_repository.find_active_membership(
        project_id, user.id, 'ACTIVE'
    )
    permissions = (
        permissions_for_membership(membership, project.get("settings"))
        if membership
        else set()
    )
    if payload.owner_id != user.id and 'testmonitor.control.assign' not in permissions:
        raise HTTPException(status_code=403, detail={"code": 'CONTROL_ACTION_ASSIGN_DENIED'})
    if not await test_monitoring_repository.find_active_membership(
        project_id,
        payload.owner_id,
        'ACTIVE',
        {"_id": 1},
    ):
        raise HTTPException(status_code=422, detail={"code": 'INVALID_CONTROL_ACTION_OWNER'})
    timestamp = now()
    value = {
        "_id": new_id('MONA'),
        "project_id": project_id,
        "plan_id": snapshot["test_plan_id"],
        **payload.model_dump(),
        "status": 'OPEN',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await test_monitoring_repository.insert_control_action(value)
    await audit(
        user.id,
        'control_action_created',
        'TestControlAction',
        value["_id"],
        project_id,
        {"type": value["type"], "owner_id": value["owner_id"]},
    )
    return value


async def update_control_action(action_id, payload: ControlActionPatch, user):
    action = await test_monitoring_repository.find_control_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail={"code": 'CONTROL_ACTION_NOT_FOUND'})
    project = await get_project(
        action["project_id"],
        user,
        'testmonitor.control.update',
        assigned_role='TESTER',
        assigned_user_id=action.get("owner_id"),
    )
    actor_membership = await test_monitoring_repository.find_active_membership(
        action["project_id"], user.id, 'ACTIVE'
    )
    actor_permissions = (
        permissions_for_membership(actor_membership, project.get("settings"))
        if actor_membership
        else set()
    )
    if action.get("owner_id") != user.id and 'testmonitor.control.assign' not in actor_permissions:
        raise HTTPException(status_code=403, detail={"code": 'CONTROL_ACTION_UPDATE_DENIED'})
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "owner_id" in changes and changes["owner_id"] != action.get("owner_id"):
        if 'testmonitor.control.assign' not in actor_permissions:
            raise HTTPException(status_code=403, detail={"code": 'CONTROL_ACTION_ASSIGN_DENIED'})
        if not await test_monitoring_repository.find_active_membership(
            action["project_id"],
            changes["owner_id"],
            'ACTIVE',
            {"_id": 1},
        ):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_CONTROL_ACTION_OWNER'})
    
    if (
        "status" in changes
        and changes["status"] != action["status"]
        and changes["status"] not in {'OPEN': ['IN_PROGRESS', 'CANCELLED'],
 'IN_PROGRESS': ['DONE', 'CANCELLED'],
 'DONE': [],
 'CANCELLED': []}[action["status"]]
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'INVALID_STATE_TRANSITION',
                "from": action["status"],
                "to": changes["status"],
            },
        )
    updated = await test_monitoring_repository.update_control_action(
        action_id,
        action["project_id"],
        payload.expected_revision,
        changes,
        now(),
    )
    if not updated:
        current = await test_monitoring_repository.find_control_action(action_id)
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_revision": current.get("revision") if current else None,
            },
        )
    await audit(
        user.id,
        'control_action_updated',
        'TestControlAction',
        action_id,
        action["project_id"],
        {"changed_fields": sorted(changes)},
    )
    return updated


async def list_actions_for_user(project_id, snapshot_id, status, user):
    await get_project(project_id, user, 'testmonitor.read')
    return await test_monitoring_repository.list_control_actions(
        project_id, snapshot_id, status, 500
    )
