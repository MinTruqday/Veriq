import hashlib
import json
import math

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.core.database import database
from src.repositories.statistical_quality import statistical_quality_repository


def _create_request_hash(payload):
    request = payload.model_dump(mode="json", exclude={"idempotency_key"})
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_create_replay(existing, payload, user):
    created_by = existing.get("created_by")
    if not created_by:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if created_by != user.id:
        raise HTTPException(status_code=403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _create_request_hash(payload):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})


def round_measurement(value):
    return round(value, 6)

def control_statistics(values):
    
    if len(values) < 5:
        raise ValueError('STATISTICAL_BASELINE_INSUFFICIENT')
    center = sum(values) / len(values)
    variance = sum((value - center) ** 2 for value in values) / len(values)
    deviation = math.sqrt(variance)
    return (
        round_measurement(center),
        round_measurement(
            max(0, center - 3 * deviation)
        ),
        round_measurement(center + 3 * deviation),
    )


async def get_statistical_analysis(analysis_id, user, permission=None):
    
    value = await statistical_quality_repository.find_analysis(analysis_id)
    if not value:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(value["project_id"], user, permission or 'statisticalquality.read')
    return value


async def list_statistical_analyses(project_id, user):
    
    await get_project(project_id, user, 'statisticalquality.read')
    items = await statistical_quality_repository.list_analyses(
        {"project_id": project_id}, 1000
    )
    return {"items": items, "total": len(items)}


async def create_statistical_baseline(project_id, payload, user):
    
    await get_project(project_id, user, 'statisticalquality.manage')
    if payload.idempotency_key:
        existing = await statistical_quality_repository.find_by_idempotency(
            project_id, payload.idempotency_key
        )
        if existing:
            _verify_create_replay(existing, payload, user)
            return existing
    definition = await statistical_quality_repository.find_definition(
        payload.measurement_definition_id, project_id
    )
    snapshots = await statistical_quality_repository.list_snapshots(
        project_id,
        payload.measurement_definition_id,
        payload.measurement_snapshot_refs,
        1000,
    )
    if not definition or len(snapshots) != len(payload.measurement_snapshot_refs):
        raise HTTPException(
            status_code=422, detail={"code": 'STATISTICAL_SOURCE_NOT_IN_PROJECT'}
        )
    if any(
        not isinstance(item.get("value"), (int, float)) or isinstance(item.get("value"), bool)
        for item in snapshots
    ):
        raise HTTPException(
            status_code=422, detail={"code": 'STATISTICAL_VALUE_NOT_NUMERIC'}
        )
    values = [float(item["value"]) for item in snapshots]
    center, lower, upper = control_statistics(values)
    points = [
        {
            "snapshot_id": item["_id"],
            "value": float(item["value"]),
            "measured_at": item.get("measured_at"),
            "outlier": float(item["value"]) < lower or float(item["value"]) > upper,
        }
        for item in snapshots
    ]
    outliers = [item["snapshot_id"] for item in points if item["outlier"]]
    timestamp = now()
    result = {
        "_id": new_id('SQC'),
        "project_id": project_id,
        **payload.model_dump(),
        "idempotency_request_hash": (
            _create_request_hash(payload) if payload.idempotency_key else None
        ),
        "measurement_key": definition.get("key"),
        "unit": definition.get("unit"),
        "points": points,
        "center_line": center,
        "lower_control_limit": lower,
        "upper_control_limit": upper,
        "outlier_snapshot_refs": outliers,
        "process_status": 'UNSTABLE' if outliers else 'STABLE',
        "alerts": [
            {"code": 'PROCESS_INSTABILITY_DETECTED', "snapshot_id": reference}
            for reference in outliers
        ],
        "calculation": 'DETERMINISTIC',
        "special_causes": [],
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await statistical_quality_repository.insert_analysis(result, session=session)
                await audit(
                    user.id,
                    'statistical_baseline_calculated',
                    'StatisticalQualityAnalysis',
                    result["_id"],
                    project_id,
                    {
                        "center_line": center,
                        "lower_control_limit": lower,
                        "upper_control_limit": upper,
                        "outlier_count": len(outliers),
                    },
                    session=session,
                )
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await statistical_quality_repository.find_by_idempotency(
                project_id, payload.idempotency_key
            )
            if existing:
                _verify_create_replay(existing, payload, user)
                return existing
        raise
    return result


async def annotate_special_cause(analysis_id, payload, user):
    
    value = await get_statistical_analysis(analysis_id, user, 'statisticalquality.annotate')
    if payload.measurement_snapshot_id not in {item["snapshot_id"] for item in value["points"]}:
        raise HTTPException(
            status_code=422, detail={"code": 'STATISTICAL_POINT_NOT_IN_WINDOW'}
        )
    timestamp = now()
    cause = {
        "annotation_id": new_id('SQCANN'),
        "measurement_snapshot_id": payload.measurement_snapshot_id,
        "cause": payload.cause,
        "evidence_refs": payload.evidence_refs,
        "created_by": user.id,
        "created_at": timestamp,
    }
    updated = await statistical_quality_repository.annotate(
        analysis_id, payload.expected_revision, cause, timestamp
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'statistical_special_cause_annotated',
        'StatisticalQualityAnalysis',
        analysis_id,
        value["project_id"],
        {"snapshot_id": payload.measurement_snapshot_id, "evidence_refs": payload.evidence_refs},
    )
    return updated


async def compare_statistical_analyses(project_id, payload, user):
    
    await get_project(project_id, user, 'statisticalquality.read')
    rows = await statistical_quality_repository.list_analyses_by_ids(
        project_id,
        [payload.before_analysis_id, payload.after_analysis_id],
        2,
    )
    by_id = {item["_id"]: item for item in rows}
    if len(by_id) != 2:
        raise HTTPException(
            status_code=422, detail={"code": 'STATISTICAL_COMPARISON_SOURCE_NOT_IN_PROJECT'}
        )
    before = by_id[payload.before_analysis_id]
    after = by_id[payload.after_analysis_id]
    if before.get("measurement_definition_id") != after.get("measurement_definition_id"):
        raise HTTPException(
            status_code=422, detail={"code": 'STATISTICAL_DEFINITION_MISMATCH'}
        )
    proposal = None
    if payload.process_improvement_id:
        proposal = await statistical_quality_repository.find_improvement(
            payload.process_improvement_id, project_id
        )
        if not proposal:
            raise HTTPException(
                status_code=422, detail={"code": 'IMPROVEMENT_NOT_IN_PROJECT'}
            )
    return {
        "project_id": project_id,
        "before_analysis_id": before["_id"],
        "after_analysis_id": after["_id"],
        "process_improvement_id": proposal.get("_id") if proposal else None,
        "center_line_delta": round_measurement(
            after["center_line"] - before["center_line"]
        ),
        "control_width_before": round_measurement(
            before["upper_control_limit"] - before["lower_control_limit"]
        ),
        "control_width_after": round_measurement(
            after["upper_control_limit"] - after["lower_control_limit"]
        ),
        "outlier_count_before": len(before.get("outlier_snapshot_refs", [])),
        "outlier_count_after": len(after.get("outlier_snapshot_refs", [])),
        "calculation": 'DETERMINISTIC',
    }
