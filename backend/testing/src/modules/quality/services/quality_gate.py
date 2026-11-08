
from functools import partial

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now, verify_idempotency_replay
from src.core.common import idempotency_request_hash as _create_request_hash
from src.core.database import database
from src.repositories.quality import quality_repository
from src.repositories.test_monitoring import test_monitoring_repository
from src.schemas.test_monitoring import QualityDecisionCreate

_verify_decision_replay = partial(verify_idempotency_replay, actor_field="decided_by")










async def get_quality_gate(snapshot_id, user):
    snapshot = await test_monitoring_repository.find_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail={"code": 'MONITORING_SNAPSHOT_NOT_FOUND'})
    await get_project(snapshot["project_id"], user, 'qualitygate.read')
    gate = await quality_repository.find_gate(snapshot_id)
    if not gate:
        gate = {
            "_id": snapshot.get("gate_evaluation_id") or f"{'QGTE'}-{snapshot_id}",
            "project_id": snapshot["project_id"],
            "test_plan_id": snapshot["test_plan_id"],
            "release_id": snapshot.get("release_id"),
            "snapshot_id": snapshot_id,
            "rules": snapshot.get("exit_criteria_evaluation", []),
            "overall_status": snapshot.get("quality_gate_status", 'INSUFFICIENT_DATA'),
            "blocking_reasons": [
                item
                for item in snapshot.get("exit_criteria_evaluation", [])
                if item.get("status") in ['FAIL']
            ],
            "warning_reasons": [
                item
                for item in snapshot.get("exit_criteria_evaluation", [])
                if item.get("status") in ['WARN', 'INSUFFICIENT_DATA', 'MANUAL_REQUIRED']
            ],
            "evaluated_at": snapshot.get("snapshot_at"),
            "engine_version": 'exit_criteria',
        }
    return gate


async def list_quality_decisions(project_id, release_id, user):
    await get_project(project_id, user, 'qualitygate.read')
    query = {"project_id": project_id}
    if release_id:
        query["release_id"] = release_id
    return await quality_repository.list_decisions(query)


async def create_quality_decision(snapshot_id, payload: QualityDecisionCreate, user):
    snapshot = await test_monitoring_repository.find_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail={"code": 'MONITORING_SNAPSHOT_NOT_FOUND'})
    permission = (
        'qualitygate.accept_risk'
        if payload.decision == 'ACCEPT_RISK'
        else 'qualitygate.decide'
    )
    project = await get_project(snapshot["project_id"], user, permission)
    existing = await quality_repository.find_decision_by_idempotency_key(
        snapshot["project_id"], payload.idempotency_key
    )
    if existing:
        _verify_decision_replay(existing, payload, user)
        if existing.get("snapshot_id") != snapshot_id:
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        return existing
    gate = await get_quality_gate(snapshot_id, user)
    if payload.decision == 'APPROVE_RELEASE' and gate.get(
        "overall_status"
    ) == 'INSUFFICIENT_DATA':
        raise HTTPException(status_code=409, detail={"code": 'QUALITY_GATE_INSUFFICIENT_DATA'})
    failed = gate.get("overall_status") in ['FAIL', 'MANUAL_REQUIRED']
    if payload.decision == 'APPROVE_RELEASE' and failed:
        if not project.get("settings", {}).get(
            'allow_quality_gate_override',
            False,
        ):
            code = (
                'QUALITY_GATE_OVERRIDE_NOT_ALLOWED'
                if payload.override_reason
                else 'QUALITY_GATE_BLOCKED'
            )
            raise HTTPException(status_code=409, detail={"code": code})
        if not payload.override_reason:
            raise HTTPException(
                status_code=422, detail={"code": 'QUALITY_GATE_OVERRIDE_REASON_REQUIRED'}
            )
    if payload.supersedes_decision_id:
        prior = await quality_repository.find_decision(
            payload.supersedes_decision_id, snapshot["project_id"]
        )
        if not prior:
            raise HTTPException(status_code=422, detail={"code": 'QUALITY_DECISION_NOT_FOUND'})
    timestamp = now()
    value = {
        "_id": new_id('QDEC'),
        "project_id": snapshot["project_id"],
        "release_id": snapshot.get("release_id"),
        "build_id": snapshot.get("build_id"),
        "snapshot_id": snapshot_id,
        "gate_evaluation_id": gate["_id"],
        **payload.model_dump(),
        "idempotency_request_hash": _create_request_hash(payload),
        "decided_by": user.id,
        "decided_at": timestamp,
        "created_at": timestamp,
    }
    event = (
        'quality_risk_accepted'
        if payload.decision == 'ACCEPT_RISK'
        else 'quality_gate_overridden'
        if payload.override_reason
        else 'quality_decision_recorded'
    )
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await quality_repository.insert_decision(value, session=session)
                await audit(
                    user.id,
                    event,
                    'QualityDecision',
                    value["_id"],
                    snapshot["project_id"],
                    {
                        "decision": payload.decision,
                        "snapshot_id": snapshot_id,
                        "supersedes_decision_id": payload.supersedes_decision_id,
                    },
                    session=session,
                )
    except DuplicateKeyError:
        replay = await quality_repository.find_decision_by_idempotency_key(
            snapshot["project_id"], payload.idempotency_key
        )
        if replay:
            _verify_decision_replay(replay, payload, user)
            if replay.get("snapshot_id") != snapshot_id:
                raise HTTPException(
                    status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"}
                )
            return replay
        raise
    return value


async def export_quality_gate(snapshot_id, user):
    gate = await get_quality_gate(snapshot_id, user)
    decisions = await list_quality_decisions(gate["project_id"], gate.get("release_id"), user)
    return {
        "gate_evaluation": gate,
        "decision_history": [item for item in decisions if item.get("snapshot_id") == snapshot_id],
        "exported_at": now(),
    }
