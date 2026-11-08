
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.core.common import idempotency_request_hash as _create_request_hash
from src.core.common import verify_idempotency_replay as _verify_create_replay
from src.core.database import database
from src.modules.quality.services.defect_classification import (
    defect_is_blocking,
    resolve_severity_classification,
)
from src.repositories.environment_incident import environment_incident_repository


async def validate_sources(project_id, payload):
    environment = await environment_incident_repository.find_environment(
        payload.environment_id,
        project_id,
        'ARCHIVED',
    )
    if not environment:
        raise HTTPException(status_code=422, detail={"code": 'ENVIRONMENT_NOT_IN_PROJECT'})
    if payload.build_id and not await environment_incident_repository.find_build(
        payload.build_id, project_id
    ):
        raise HTTPException(status_code=422, detail={"code": 'BUILD_NOT_IN_PROJECT'})
    run_ids = list(dict.fromkeys(payload.affected_run_ids))
    count = await environment_incident_repository.count_environment_runs(
        run_ids, project_id, payload.environment_id
    )
    if count != len(run_ids):
        raise HTTPException(status_code=422, detail={"code": 'AFFECTED_RUN_NOT_IN_ENVIRONMENT'})
    if not await environment_incident_repository.find_active_member(
        project_id, payload.owner_id, 'ACTIVE'
    ):
        raise HTTPException(status_code=422, detail={"code": 'INCIDENT_OWNER_NOT_PROJECT_MEMBER'})
    return environment, run_ids


async def get_incident(incident_id, user, permission=None):
    value = await environment_incident_repository.find_incident(incident_id)
    if not value:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(value["project_id"], user, permission or 'environmentincident.read')
    return value


async def list_incidents(project_id, environment_id, status, user):
    await get_project(project_id, user, 'environmentincident.read')
    query = {"project_id": project_id}
    if environment_id:
        query["environment_id"] = environment_id
    if status:
        query["status"] = status
    items = await environment_incident_repository.list_incidents(
        query, 1000
    )
    return {"items": items, "total": len(items)}


async def create_incident(project_id, payload, user):
    await get_project(project_id, user, 'environmentincident.create')
    
    environment, run_ids = await validate_sources(project_id, payload)
    classification = await resolve_severity_classification(project_id, payload.severity)
    if payload.idempotency_key:
        existing = await environment_incident_repository.find_by_idempotency_key(
            project_id, payload.idempotency_key
        )
        if existing:
            _verify_create_replay(existing, payload, user)
            return existing
    timestamp = now()
    sequence = await environment_incident_repository.next_sequence(
        f"{project_id}:{'environment-incident'}"
    )
    previous_availability = environment.get("availability", 'AVAILABLE')
    if previous_availability == 'UNAVAILABLE' and environment.get("active_incident_id"):
        active_incident = await environment_incident_repository.find_incident(
            environment["active_incident_id"], project_id
        )
        if active_incident:
            previous_availability = active_incident.get(
                "previous_environment_availability", previous_availability
            )
    value = {
        "_id": new_id('ENVINC'),
        "incident_key": f"{'ENVINC'}-{int(sequence['value']):0{4}d}",
        "project_id": project_id,
        **payload.model_dump(),
        **classification,
        "idempotency_request_hash": (
            _create_request_hash(payload) if payload.idempotency_key else None
        ),
        "affected_run_ids": run_ids,
        "previous_environment_availability": previous_availability,
        "status": 'OPEN',
        "resolution": "",
        "downtime_start": payload.observed_at,
        "downtime_end": None,
        "downtime": None,
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await environment_incident_repository.insert_incident(value, session=session)
                if value["severity_blocks_release"]:
                    environment_update = await environment_incident_repository.mark_environment_unavailable(
                        environment["_id"],
                        environment.get("revision"),
                        value["_id"],
                        'UNAVAILABLE',
                        timestamp,
                        session=session,
                    )
                    if environment_update.matched_count != 1:
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "ENVIRONMENT_CHANGED_RETRY_INCIDENT"},
                        )
                    if run_ids:
                        await environment_incident_repository.pause_runs(
                            run_ids,
                            project_id,
                            value["_id"],
                            'IN_PROGRESS',
                            timestamp,
                            session=session,
                        )
                await audit(
                    user.id,
                    'environment_incident_created',
                    'EnvironmentIncident',
                    value["_id"],
                    project_id,
                    {
                        "environment_id": payload.environment_id,
                        "severity": payload.severity,
                        "affected_run_ids": run_ids,
                    },
                    session=session,
                )
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await environment_incident_repository.find_by_idempotency_key(
                project_id, payload.idempotency_key
            )
            if existing:
                _verify_create_replay(existing, payload, user)
                return existing
        raise
    return value


async def update_incident(incident_id, payload, user):
    
    value = await get_incident(incident_id, user, 'environmentincident.update')
    if value["status"] in ['RESOLVED', 'CLOSED']:
        raise HTTPException(status_code=409, detail={"code": 'RESOLVED_INCIDENT_IMMUTABLE'})
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "severity" in changes:
        changes.update(
            await resolve_severity_classification(value["project_id"], changes["severity"])
        )
    if "owner_id" in changes and not await environment_incident_repository.find_active_member(
        value["project_id"], changes["owner_id"], 'ACTIVE'
    ):
        raise HTTPException(status_code=422, detail={"code": 'INCIDENT_OWNER_NOT_PROJECT_MEMBER'})
    if "affected_run_ids" in changes:
        run_ids = list(dict.fromkeys(changes["affected_run_ids"]))
        count = await environment_incident_repository.count_environment_runs(
            run_ids, value["project_id"], value["environment_id"]
        )
        if count != len(run_ids):
            raise HTTPException(status_code=422, detail={"code": 'AFFECTED_RUN_NOT_IN_ENVIRONMENT'})
        changes["affected_run_ids"] = run_ids
    changes["updated_at"] = now()
    updated = await environment_incident_repository.update_incident(
        incident_id, payload.expected_revision, ['OPEN', 'INVESTIGATING', 'MITIGATED'], changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    was_blocking = defect_is_blocking(value)
    is_blocking = defect_is_blocking(updated)
    if was_blocking != is_blocking and value["status"] in {"OPEN", "INVESTIGATING", "MITIGATED"}:
        if is_blocking:
            environment = await environment_incident_repository.find_environment(
                value["environment_id"], value["project_id"], "ARCHIVED"
            )
            if environment:
                environment_update = await environment_incident_repository.mark_environment_unavailable(
                    environment["_id"],
                    environment.get("revision"),
                    incident_id,
                    "UNAVAILABLE",
                    changes["updated_at"],
                )
                if environment_update.matched_count != 1:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "ENVIRONMENT_CHANGED_RETRY_INCIDENT"},
                    )
            await environment_incident_repository.pause_runs(
                updated.get("affected_run_ids", []),
                value["project_id"],
                incident_id,
                "IN_PROGRESS",
                changes["updated_at"],
            )
        else:
            remaining = await environment_incident_repository.count_other_active_blocking(
                value["project_id"],
                value["environment_id"],
                incident_id,
                ["OPEN", "INVESTIGATING", "MITIGATED"],
            )
            if not remaining:
                await environment_incident_repository.restore_environment(
                    value["environment_id"],
                    value.get("previous_environment_availability", "AVAILABLE"),
                    "ARCHIVED",
                    changes["updated_at"],
                )
                await environment_incident_repository.resume_runs(
                    value["project_id"], incident_id, changes["updated_at"]
                )
    await audit(
        user.id,
        'environment_incident_updated',
        'EnvironmentIncident',
        incident_id,
        value["project_id"],
        {"fields": sorted(changes)},
    )
    return updated


async def transition_incident(incident_id, payload, user):
    
    permission = (
        'environmentincident.close'
        if payload.status == 'CLOSED'
        else 'environmentincident.update'
    )
    value = await get_incident(incident_id, user, permission)
    if payload.status not in {'OPEN': ['INVESTIGATING'],
 'INVESTIGATING': ['MITIGATED'],
 'MITIGATED': ['RESOLVED'],
 'RESOLVED': ['CLOSED']}.get(value["status"], []):
        raise HTTPException(
            status_code=409, detail={"code": 'INVALID_ENVIRONMENT_INCIDENT_TRANSITION'}
        )
    timestamp = now()
    changes = {"status": payload.status, "resolution": payload.resolution, "updated_at": timestamp}
    if payload.status == 'RESOLVED':
        changes.update(
            {
                "resolved_at": timestamp,
                "downtime_end": timestamp,
                "downtime": max(0, int((timestamp - value["observed_at"]).total_seconds())),
            }
        )
    if payload.status == 'CLOSED':
        changes.update({"closed_at": timestamp, "closed_by": user.id})
    updated = await environment_incident_repository.update_incident(
        incident_id, payload.expected_revision, value["status"], changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    if payload.status == 'RESOLVED' and defect_is_blocking(value):
        remaining = await environment_incident_repository.count_other_active_blocking(
            value["project_id"],
            value["environment_id"],
            incident_id,
            ['OPEN', 'INVESTIGATING', 'MITIGATED'],
        )
        if not remaining:
            await environment_incident_repository.restore_environment(
                value["environment_id"],
                value.get("previous_environment_availability", 'AVAILABLE'),
                'ARCHIVED',
                timestamp,
            )
            await environment_incident_repository.resume_runs(
                value["project_id"], incident_id, timestamp
            )
    event = (
        'environment_incident_closed'
        if payload.status == 'CLOSED'
        else 'environment_incident_status_changed'
    )
    await audit(
        user.id,
        event,
        'EnvironmentIncident',
        incident_id,
        value["project_id"],
        {"from": value["status"], "to": payload.status, "downtime": changes.get("downtime")},
    )
    return updated


class EnvironmentIncidentService:
    @staticmethod
    async def list(project_id, environment_id, status, user):
        return await list_incidents(project_id, environment_id, status, user)

    @staticmethod
    async def create(project_id, payload, user):
        return await create_incident(project_id, payload, user)

    @staticmethod
    async def get(incident_id, user):
        return await get_incident(incident_id, user)

    @staticmethod
    async def update(incident_id, payload, user):
        return await update_incident(incident_id, payload, user)

    @staticmethod
    async def investigate(incident_id, payload, user):
        if payload.status == 'CLOSED':
            raise HTTPException(
                status_code=422,
                detail={"code": 'USE_INCIDENT_CLOSE_ENDPOINT'},
            )
        return await transition_incident(incident_id, payload, user)

    @staticmethod
    async def close(incident_id, payload, user):
        if payload.status != 'CLOSED':
            raise HTTPException(
                status_code=422,
                detail={"code": 'INCIDENT_CLOSE_STATUS_REQUIRED'},
            )
        return await transition_incident(incident_id, payload, user)

    @staticmethod
    async def transition(incident_id, payload, user):
        return await transition_incident(incident_id, payload, user)
