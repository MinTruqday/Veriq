from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.ai_automation import emit_performance_configuration_approved
from src.core.common import audit, get_project, new_id, now
from src.core.database import database
from src.repositories.non_functional_test import non_functional_test_repository





def normalize_plan(value):
    if value is None:
        return value
    normalized = dict(value)
    for target, source in {'test_conditions': 'test_condition_ids',
 'test_cases': 'test_case_version_ids',
 'requirement_refs': 'requirement_version_ids',
 'tool_refs': 'tools'}.items():
        normalized[target] = normalized.get(target, normalized.get(source, []))
    return normalized


async def validate_refs(project_id, values):
    
    for field, collection_name in {'test_conditions': 'test_conditions',
 'test_cases': 'test_case_versions',
 'requirement_refs': 'requirement_versions',
 'source_ai_result_ids': 'ai_results'}.items():
        ids = list(dict.fromkeys(values.get(field) or []))
        if ids and await non_functional_test_repository.count_project_entities(
            collection_name, project_id, ids
        ) != len(ids):
            raise HTTPException(
                status_code=422,
                detail={"code": 'NFR_TRACE_NOT_IN_PROJECT', "field": field},
            )


async def get_plan(plan_id, user, permission="nfrtest.read"):
    value = await non_functional_test_repository.find_plan(plan_id)
    if not value:
        raise HTTPException(
            status_code=404,
            detail={"code": 'ENTITY_NOT_FOUND'},
        )
    await get_project(value["project_id"], user, permission)
    return normalize_plan(value)


async def list_plans(project_id, plan_type, user):
    await get_project(project_id, user, "nfrtest.read")
    query = {"project_id": project_id}
    if plan_type:
        query["plan_type"] = plan_type
    items = [
        normalize_plan(item)
        for item in await non_functional_test_repository.list_plans(
            query, 1000
        )
    ]
    return {"items": items, "total": len(items)}


async def create_plan(project_id, payload, user):
    
    await get_project(project_id, user, "nfrtest.manage")
    await validate_refs(project_id, payload.model_dump())
    if payload.idempotency_key:
        existing = await non_functional_test_repository.find_plan_by_idempotency_key(
            project_id, payload.idempotency_key
        )
        if existing:
            if (
                existing.get("plan_type") != payload.plan_type
                or existing.get("name") != payload.name
            ):
                raise HTTPException(
                    status_code=409, detail={"code": 'IDEMPOTENCY_KEY_REUSED'}
                )
            return existing
    timestamp = now()
    value = {
        "_id": new_id('NFR'),
        "project_id": project_id,
        **payload.model_dump(),
        "external_evidence_ids": [],
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await non_functional_test_repository.insert_plan(value)
    except DuplicateKeyError:
        if payload.idempotency_key:
            return await non_functional_test_repository.find_plan_by_idempotency_key(
                project_id, payload.idempotency_key
            )
        raise
    await audit(
        user.id,
        "nfr_test_plan_created",
        "NonFunctionalTestPlan",
        value["_id"],
        project_id,
        {"plan_type": value["plan_type"]},
    )
    return value


async def update_plan(plan_id, payload, user):
    
    value = await get_plan(plan_id, user, "nfrtest.manage")
    if value["status"] not in ['DRAFT', 'IN_REVIEW']:
        raise HTTPException(status_code=409, detail={"code": 'APPROVED_NFR_PLAN_IMMUTABLE'})
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    await validate_refs(value["project_id"], changes)
    merged = normalize_plan({**value, **changes})
    if not merged.get("test_conditions") and not merged.get("test_cases"):
        raise HTTPException(status_code=422, detail={"code": 'NFR_TRACE_REQUIRED'})
    changes["updated_at"] = now()
    updated = await non_functional_test_repository.update_plan(
        plan_id, payload.expected_revision, ['DRAFT', 'IN_REVIEW'], changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        "nfr_test_plan_updated",
        "NonFunctionalTestPlan",
        plan_id,
        value["project_id"],
        {"fields": sorted(changes)},
    )
    return updated


async def transition_plan(plan_id, payload, user, approve=False):
    
    permission = "nfrtest.approve" if approve else "nfrtest.review"
    value = await get_plan(plan_id, user, permission)
    transition = {'submit': {'source': 'DRAFT', 'target': 'IN_REVIEW'},
 'approve': {'source': 'IN_REVIEW', 'target': 'APPROVED'}}["approve" if approve else "submit"]
    source, target = transition["source"], transition["target"]
    if value["status"] != source:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_NFR_PLAN_TRANSITION'})
    timestamp = now()
    changes = {"status": target, "updated_at": timestamp, "transition_note": payload.note}
    if approve:
        changes.update({"approved_by": user.id, "approved_at": timestamp})
    else:
        changes.update({"submitted_by": user.id, "submitted_at": timestamp})
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await non_functional_test_repository.transition_plan(
                plan_id, payload.expected_revision, source, changes, session=session
            )
            if not updated:
                raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
            await audit(
                user.id,
                "nfr_test_plan_approved" if approve else "nfr_test_plan_submitted",
                "NonFunctionalTestPlan",
                plan_id,
                value["project_id"],
                {"note": payload.note},
                session=session,
            )
            if approve and updated.get("plan_type") == "PERFORMANCE_TEST_PLAN":
                await emit_performance_configuration_approved(updated, user, session=session)
    return updated


async def import_evidence(plan_id, payload, user):
    
    value = await get_plan(plan_id, user, "nfrtest.evidence.import")
    existing = await non_functional_test_repository.find_evidence_by_idempotency_key(
        value["project_id"], payload.idempotency_key
    )
    if existing:
        if existing["plan_id"] != plan_id or existing["raw_result_hash"] != payload.raw_result_hash:
            raise HTTPException(
                status_code=409, detail={"code": 'IDEMPOTENCY_KEY_REUSED'}
            )
        return existing
    timestamp = now()
    evidence = {
        "_id": new_id('NFREVD'),
        "project_id": value["project_id"],
        "plan_id": plan_id,
        **payload.model_dump(),
        "imported_by": user.id,
        "created_at": timestamp,
    }
    try:
        await non_functional_test_repository.insert_evidence(evidence)
    except DuplicateKeyError:
        return await non_functional_test_repository.find_evidence_by_idempotency_key(
            value["project_id"], payload.idempotency_key
        )
    await non_functional_test_repository.attach_evidence(
        plan_id, evidence["_id"], payload.result_summary, timestamp
    )
    await audit(
        user.id,
        "nfr_external_evidence_imported",
        "NonFunctionalTestEvidence",
        evidence["_id"],
        value["project_id"],
        {
            "plan_id": plan_id,
            "provider": payload.provider,
            "raw_result_hash": payload.raw_result_hash,
        },
    )
    return evidence


class NonFunctionalTestService:
    @staticmethod
    async def list(project_id, plan_type, user):
        return await list_plans(project_id, plan_type, user)

    @staticmethod
    async def create(project_id, payload, user):
        return await create_plan(project_id, payload, user)

    @staticmethod
    async def get(plan_id, user):
        value = await get_plan(plan_id, user)
        value["external_evidence"] = await non_functional_test_repository.list_evidence(
            plan_id, 1000
        )
        return value

    @staticmethod
    async def update(plan_id, payload, user):
        return await update_plan(plan_id, payload, user)

    @staticmethod
    async def transition(plan_id, payload, user, approve=False):
        return await transition_plan(plan_id, payload, user, approve)

    @staticmethod
    async def import_evidence(plan_id, payload, user):
        return await import_evidence(plan_id, payload, user)
