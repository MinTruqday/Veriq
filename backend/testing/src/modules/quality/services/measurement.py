import hashlib
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.auth import access_policy
from src.core.common import audit, get_project, new_id, now
from src.core.database import database
from src.modules.quality.services.measurement_engine import (
    compute_custom_metric,
    compute_metric,
    validate_formula_source,
)
from src.modules.quality.services.measurement_export import export_metric_csv
from src.repositories.measurement import measurement_repository
from src.schemas.measurement import validate_threshold_order


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


def _version_request_hash(payload, source_definition_id):
    request = payload.model_dump(mode="json", exclude={"idempotency_key"})
    request["source_definition_id"] = source_definition_id
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_version_replay(existing, payload, source_definition_id, user):
    if not existing.get("created_by"):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if existing["created_by"] != user.id:
        raise HTTPException(status_code=403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _version_request_hash(payload, source_definition_id):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})


async def list_definitions(project_id, user):
    
    await get_project(project_id, user, 'measurement.read')
    items = await measurement_repository.list_definitions(
        project_id, 1000
    )
    return {"items": items, "total": len(items)}


async def create_definition(project_id, payload, user):
    
    await get_project(project_id, user, 'measurement.manage')
    if payload.owner_role not in access_policy().get("role_permissions", {}):
        raise HTTPException(status_code=422, detail={"code": "PROJECT_ROLE_UNAVAILABLE"})
    if payload.idempotency_key:
        existing = await measurement_repository.find_definition_idempotency(
            project_id, payload.idempotency_key
        )
        if existing:
            _verify_create_replay(existing, payload, user)
            return existing
    validation = validate_formula_source(
        payload.formula_type, payload.formula, payload.data_sources
    )
    if not validation["valid"]:
        raise HTTPException(
            status_code=422,
            detail={"code": 'MEASUREMENT_DEFINITION_INVALID', "errors": validation["errors"]},
        )
    latest = await measurement_repository.find_latest_definition(project_id, payload.key)
    timestamp = now()
    value = {
        "_id": new_id('METDEF'),
        "project_id": project_id,
        **payload.model_dump(),
        "idempotency_request_hash": (
            _create_request_hash(payload) if payload.idempotency_key else None
        ),
        "version": int(latest.get("version", 0)) + 1 if latest else 1,
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await measurement_repository.insert_definition(value, session=session)
                await audit(
                    user.id,
                    'measurement_definition_created',
                    'MeasurementDefinition',
                    value["_id"],
                    project_id,
                    {"key": value["key"], "version": value["version"]},
                    session=session,
                )
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await measurement_repository.find_definition_idempotency(
                project_id, payload.idempotency_key
            )
            if existing:
                _verify_create_replay(existing, payload, user)
                return existing
        raise
    return value


async def update_definition(definition_id, payload, user):
    
    value = await measurement_repository.find_definition(definition_id)
    if not value:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(value["project_id"], user, 'measurement.manage')
    if value["status"] != 'DRAFT':
        raise HTTPException(
            status_code=409, detail={"code": 'ACTIVE_MEASUREMENT_DEFINITION_IMMUTABLE'}
        )
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if changes.get("owner_role") not in {None, *access_policy().get("role_permissions", {})}:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_ROLE_UNAVAILABLE"})
    try:
        validate_threshold_order(
            value["key"],
            changes.get("target", value.get("target")),
            changes.get("warning_threshold", value.get("warning_threshold")),
            changes.get("critical_threshold", value.get("critical_threshold")),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": 'INVALID_MEASUREMENT_THRESHOLDS', "message": str(error)},
        ) from error
    validation = validate_formula_source(
        changes.get("formula_type", value.get("formula_type", 'BUILT_IN')),
        changes.get("formula", value["formula"]),
        changes.get("data_sources", value["data_sources"]),
    )
    if not validation["valid"]:
        raise HTTPException(
            status_code=422,
            detail={"code": 'MEASUREMENT_DEFINITION_INVALID', "errors": validation["errors"]},
        )
    changes["updated_at"] = now()
    updated = await measurement_repository.update_definition(
        definition_id, payload.expected_revision, 'DRAFT', changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'measurement_definition_updated',
        'MeasurementDefinition',
        definition_id,
        value["project_id"],
        {"fields": sorted(changes)},
    )
    return updated


async def transition_definition(definition_id, payload, user):
    
    value = await measurement_repository.find_definition(definition_id)
    if not value:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(value["project_id"], user, 'measurement.manage')
    allowed = {tuple(item) for item in [['DRAFT', 'ACTIVE'], ['ACTIVE', 'ARCHIVED'], ['DRAFT', 'ARCHIVED']]}
    if (value["status"], payload.status) not in allowed:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_MEASUREMENT_TRANSITION'})
    timestamp = now()
    if payload.status == 'ACTIVE':
        await measurement_repository.archive_other_active_definitions(
            value["project_id"],
            value["key"],
            definition_id,
            'ACTIVE',
            'ARCHIVED',
            timestamp,
        )
    try:
        updated = await measurement_repository.update_definition(
            definition_id,
            payload.expected_revision,
            value["status"],
            {
                "status": payload.status,
                "transition_note": payload.note,
                "updated_at": timestamp,
            },
        )
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=409, detail={"code": 'ACTIVE_MEASUREMENT_DEFINITION_EXISTS'}
        ) from error
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    event = (
        'measurement_definition_activated'
        if payload.status == 'ACTIVE'
        else 'measurement_definition_status_changed'
    )
    await audit(
        user.id,
        event,
        'MeasurementDefinition',
        definition_id,
        value["project_id"],
        {"from": value["status"], "to": payload.status},
    )
    return updated


async def create_snapshot(project_id, payload, user):
    
    await get_project(project_id, user, 'measurement.snapshot.create')
    definition = await measurement_repository.find_definition(
        payload.definition_id,
        {"project_id": project_id, "status": 'ACTIVE'},
    )
    if not definition:
        raise HTTPException(
            status_code=422, detail={"code": 'ACTIVE_MEASUREMENT_DEFINITION_REQUIRED'}
        )
    if payload.release_id and not await measurement_repository.find_release(
        payload.release_id, project_id
    ):
        raise HTTPException(status_code=422, detail={"code": 'RELEASE_NOT_IN_PROJECT'})
    if payload.idempotency_key:
        existing = await measurement_repository.find_snapshot_idempotency(
            project_id, payload.idempotency_key
        )
        if existing:
            _verify_create_replay(existing, payload, user)
            return existing
    if definition.get("formula_type") == 'CUSTOM_SAFE_EXPRESSION':
        value, source = await compute_custom_metric(project_id, payload.release_id, definition)
    else:
        value, source = await compute_metric(project_id, payload.release_id, definition["key"])
    if value is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": 'METRIC_SOURCE_UNAVAILABLE',
                "metric": definition["key"],
                "source": source,
            },
        )
    fingerprint = hashlib.sha256(
        json.dumps(source, sort_keys=True, default=str).encode()
    ).hexdigest()
    timestamp = now()
    snapshot = {
        "_id": new_id('METSNP'),
        "project_id": project_id,
        "release_id": payload.release_id,
        "measurement_definition_id": definition["_id"],
        "measurement_definition_version": definition["version"],
        "measurement_key": definition["key"],
        "value": value,
        "unit": definition["unit"],
        "dimensions": payload.dimensions,
        "source": source,
        "source_fingerprint": fingerprint,
        "measured_at": timestamp,
        "idempotency_key": payload.idempotency_key,
        "idempotency_request_hash": (
            _create_request_hash(payload) if payload.idempotency_key else None
        ),
        "created_by": user.id,
        "created_at": timestamp,
    }
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await measurement_repository.insert_snapshot(snapshot, session=session)
                await audit(
                    user.id,
                    'measurement_snapshot_created',
                    'MeasurementSnapshot',
                    snapshot["_id"],
                    project_id,
                    {"key": definition["key"], "value": value, "source_fingerprint": fingerprint},
                    session=session,
                )
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await measurement_repository.find_snapshot_idempotency(
                project_id, payload.idempotency_key
            )
            if existing:
                _verify_create_replay(existing, payload, user)
                return existing
        raise
    return snapshot


async def list_snapshots(project_id, user, definition_id, release_id):
    
    await get_project(project_id, user, 'measurement.read')
    query = {"project_id": project_id}
    if definition_id:
        query["measurement_definition_id"] = definition_id
    if release_id:
        query["release_id"] = release_id
    items = await measurement_repository.list_snapshots(
        query, -1, 2000
    )
    return {"items": items, "total": len(items)}


async def version_definition(definition_id, payload, user):
    
    source = await measurement_repository.find_definition(definition_id)
    if not source:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(source["project_id"], user, 'measurement.manage')
    existing = await measurement_repository.find_definition_idempotency(
        source["project_id"], payload.idempotency_key
    )
    if existing:
        _verify_version_replay(existing, payload, definition_id, user)
        return existing
    if source["revision"] != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    latest = await measurement_repository.find_latest_definition(
        source["project_id"], source["key"]
    )
    excluded = {
        "_id",
        "status",
        "revision",
        "created_by",
        "created_at",
        "updated_at",
        "transition_note",
        "idempotency_key",
    }
    timestamp = now()
    value = {key: item for key, item in source.items() if key not in excluded}
    value.update(
        {
            "_id": new_id('METDEF'),
            "version": int((latest or {}).get("version", 0)) + 1,
            "status": 'DRAFT',
            "revision": 1,
            "idempotency_key": payload.idempotency_key,
            "idempotency_request_hash": _version_request_hash(payload, definition_id),
            "supersedes_definition_id": definition_id,
            "version_note": payload.note,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await measurement_repository.insert_definition(value, session=session)
                await audit(
                    user.id,
                    'measurement_definition_versioned',
                    'MeasurementDefinition',
                    value["_id"],
                    source["project_id"],
                    {"supersedes_definition_id": definition_id, "version": value["version"]},
                    session=session,
                )
    except DuplicateKeyError:
        duplicate = await measurement_repository.find_definition_idempotency(
            source["project_id"], payload.idempotency_key
        )
        if duplicate:
            _verify_version_replay(duplicate, payload, definition_id, user)
            return duplicate
        raise
    return value


async def validate_definition(definition_id, user):
    
    value = await measurement_repository.find_definition(definition_id)
    if not value:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(value["project_id"], user, 'measurement.read')
    result = validate_formula_source(
        value.get("formula_type", 'BUILT_IN'),
        value["formula"],
        value["data_sources"],
    )
    return {
        **result,
        "definition_id": definition_id,
        "key": value["key"],
        "version": value["version"],
    }


async def measurement_trend(definition_id, release_id, user):
    
    definition = await measurement_repository.find_definition(definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(definition["project_id"], user, 'measurement.read')
    query = {"project_id": definition["project_id"], "measurement_key": definition["key"]}
    if release_id:
        query["release_id"] = release_id
    items = await measurement_repository.list_snapshots(
        query, 1, 5000
    )
    return {
        "definition_id": definition_id,
        "measurement_key": definition["key"],
        "items": items,
        "total": len(items),
    }


async def compare_measurement_releases(project_id, release_a, release_b, user):
    
    await get_project(project_id, user, 'measurement.read')
    releases = await measurement_repository.count_releases(
        project_id, [release_a, release_b]
    )
    if releases != len({release_a, release_b}):
        raise HTTPException(status_code=422, detail={"code": 'RELEASE_NOT_IN_PROJECT'})
    rows = await measurement_repository.list_snapshots(
        {"project_id": project_id, "release_id": {"$in": [release_a, release_b]}},
        -1,
        10000,
    )
    latest = {}
    for item in rows:
        latest.setdefault((item["release_id"], item["measurement_key"]), item)
    keys = sorted({key for _, key in latest})
    items = [
        {
            "measurement_key": key,
            "release_a": latest.get((release_a, key)),
            "release_b": latest.get((release_b, key)),
            "delta": round(
                float(latest[(release_b, key)]["value"]) - float(latest[(release_a, key)]["value"]),
                4,
            )
            if (release_a, key) in latest and (release_b, key) in latest
            else None,
        }
        for key in keys
    ]
    return {"release_a": release_a, "release_b": release_b, "items": items}


def threshold_level(definition, value):
    
    key = definition["key"]
    critical = definition.get("critical_threshold")
    warning = definition.get("warning_threshold")
    if value is None:
        return 'NO_DATA'
    if key in ['BLOCKED_RATE',
 'DEFECT_REOPEN_RATE',
 'CRITICAL_DEFECT_AGING',
 'MEAN_TIME_TO_RETEST',
 'STALE_TEST_RATIO',
 'REQUIREMENT_VOLATILITY',
 'ESCAPED_DEFECT_RATE']:
        if critical is not None and value >= critical:
            return 'CRITICAL'
        if warning is not None and value >= warning:
            return 'WARNING'
    else:
        if critical is not None and value <= critical:
            return 'CRITICAL'
        if warning is not None and value <= warning:
            return 'WARNING'
    return 'NORMAL'


async def measurement_alerts(project_id, user):
    
    await get_project(project_id, user, 'measurement.read')
    definitions = await measurement_repository.list_active_definitions(
        project_id, 'ACTIVE', 1000
    )
    items = []
    for definition in definitions:
        snapshot = await measurement_repository.find_latest_snapshot(
            project_id, definition["_id"]
        )
        level = threshold_level(definition, snapshot.get("value") if snapshot else None)
        if level in ['WARNING', 'CRITICAL', 'NO_DATA']:
            items.append(
                {
                    "definition_id": definition["_id"],
                    "measurement_key": definition["key"],
                    "level": level,
                    "value": snapshot.get("value") if snapshot else None,
                    "snapshot_id": snapshot.get("_id") if snapshot else None,
                }
            )
    return {"items": items, "total": len(items)}


async def pin_metric(definition_id, payload, user):
    
    definition = await measurement_repository.find_definition(definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(definition["project_id"], user, 'measurement.read')
    key = {
        "project_id": definition["project_id"],
        "user_id": user.id,
        "measurement_key": definition["key"],
    }
    if payload.pinned:
        await measurement_repository.set_dashboard_pin(key, definition_id, now())
    else:
        await measurement_repository.delete_dashboard_pin(key)
    await audit(
        user.id,
        'measurement_dashboard_pin_changed',
        'MeasurementDefinition',
        definition_id,
        definition["project_id"],
        {"pinned": payload.pinned},
    )
    return {**key, "definition_id": definition_id, "pinned": payload.pinned}


class MeasurementService:
    @staticmethod
    async def list_definitions(project_id, user):
        return await list_definitions(project_id, user)

    @staticmethod
    async def create_definition(project_id, payload, user):
        return await create_definition(project_id, payload, user)

    @staticmethod
    async def update_definition(definition_id, payload, user):
        return await update_definition(definition_id, payload, user)

    @staticmethod
    async def version_definition(definition_id, payload, user):
        return await version_definition(definition_id, payload, user)

    @staticmethod
    async def transition_definition(definition_id, payload, user):
        return await transition_definition(definition_id, payload, user)

    @staticmethod
    async def list_snapshots(project_id, user, definition_id, release_id):
        return await list_snapshots(project_id, user, definition_id, release_id)

    @staticmethod
    async def create_snapshot(project_id, payload, user):
        return await create_snapshot(project_id, payload, user)

    @staticmethod
    async def get_snapshot(snapshot_id, user):
        
        value = await measurement_repository.find_snapshot(snapshot_id)
        if not value:
            raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
        await get_project(value["project_id"], user, 'measurement.read')
        return value

    @staticmethod
    async def trend(definition_id, release_id, user):
        return await measurement_trend(definition_id, release_id, user)

    @staticmethod
    async def compare_releases(project_id, release_a, release_b, user):
        return await compare_measurement_releases(project_id, release_a, release_b, user)

    @staticmethod
    async def alerts(project_id, user):
        return await measurement_alerts(project_id, user)

    @staticmethod
    async def validate(definition_id, user):
        return await validate_definition(definition_id, user)

    @staticmethod
    async def pin(definition_id, payload, user):
        return await pin_metric(definition_id, payload, user)

    @staticmethod
    async def export(definition_id, user):
        
        definition = await measurement_repository.find_definition(definition_id)
        if not definition:
            raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
        await get_project(definition["project_id"], user, 'report.export')
        snapshots = await measurement_repository.list_snapshots(
            {
                "project_id": definition["project_id"],
                "measurement_key": definition["key"],
            },
            1,
            10000,
        )
        return definition, export_metric_csv(definition, snapshots)
