import re

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now, page_payload
from src.core.human_decisions import require_independent_review
from src.schemas.test_strategy import (
    TestStrategyFields,
    compare_strategy_snapshots,
    strategy_completeness,
    strategy_hash,
    strategy_snapshot,
)
from src.repositories.test_strategy import test_strategy_repository





async def get_strategy_for_user(strategy_id, user, permission=None):
    
    strategy = await test_strategy_repository.get(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=404, detail={"code": 'TEST_STRATEGY_NOT_FOUND'}
        )
    await get_project(
        strategy["project_id"], user, permission or 'teststrategy.read'
    )
    return strategy


async def list_strategies(project_id, user, query_text, status, version, page, page_size):
    await get_project(project_id, user, 'teststrategy.read')
    query = {"project_id": project_id}
    if query_text:
        query["$or"] = [
            {"key": {"$regex": re.escape(query_text), "$options": "i"}},
            {"name": {"$regex": re.escape(query_text), "$options": "i"}},
        ]
    if status:
        query["status"] = status
    if version is not None:
        query["version"] = version
    items, total = await test_strategy_repository.list(query, (page - 1) * page_size, page_size)
    return page_payload(items, page, page_size, total)


async def create_strategy(project_id, payload, user):
    
    await get_project(project_id, user, 'teststrategy.create')
    timestamp = now()
    strategy_id = new_id('TSTR')
    value = {
        "_id": strategy_id,
        "lineage_id": strategy_id,
        "project_id": project_id,
        **payload.model_dump(),
        "version": 1,
        "status": 'DRAFT',
        "active_approved": False,
        "reviewed_by": [],
        "approval_history": [],
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await test_strategy_repository.create(value)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=409, detail={"code": 'STRATEGY_KEY_VERSION_EXISTS'}
        ) from error
    await audit(
        user.id,
        'test_strategy_created',
        'TestStrategy',
        strategy_id,
        project_id,
        {"key": value["key"], "version": 1},
    )
    return value


async def update_strategy(strategy_id, payload, user):
    
    
    
    strategy = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.update'
    )
    if strategy["status"] == 'ARCHIVED':
        raise HTTPException(
            status_code=409,
            detail={"code": 'ARTIFACT_ARCHIVED', "artifact_type": 'TEST_STRATEGY'},
        )
    if strategy["status"] not in set(['DRAFT', 'IN_REVIEW']):
        raise HTTPException(
            status_code=409,
            detail={"code": 'TEST_STRATEGY_NOT_DRAFT', "status": strategy["status"]},
        )
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    merged = {**strategy, **changes}
    TestStrategyFields.model_validate(merged)
    changes["updated_at"] = now()
    updated = await test_strategy_repository.update(
        strategy_id,
        strategy["project_id"],
        payload.expected_revision,
        set(['DRAFT', 'IN_REVIEW']),
        changes,
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'test_strategy_updated',
        'TestStrategy',
        strategy_id,
        strategy["project_id"],
        {"fields": sorted(field for field in changes if field != "updated_at")},
    )
    return updated


async def submit_strategy(strategy_id, payload, user):
    
    
    
    strategy = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.submit_review'
    )
    completeness = strategy_completeness(strategy)
    if not completeness["ready_for_review"]:
        raise HTTPException(
            status_code=409, detail={"code": 'TEST_STRATEGY_INCOMPLETE', **completeness}
        )
    if not strategy.get("reviewer_ids"):
        raise HTTPException(status_code=422, detail={"code": 'STRATEGY_REVIEWERS_REQUIRED'})
    if not any(reviewer_id != user.id for reviewer_id in strategy.get("reviewer_ids", [])):
        raise HTTPException(
            status_code=422, detail={"code": 'INDEPENDENT_STRATEGY_REVIEWER_REQUIRED'}
        )
    updated = await test_strategy_repository.update(
        strategy_id,
        strategy["project_id"],
        payload.expected_revision,
        {'DRAFT'},
        {
            "status": 'IN_REVIEW',
            "submitted_by": user.id,
            "submitted_at": now(),
            "review_note": payload.note,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'STRATEGY_TRANSITION_CONFLICT'})
    await audit(
        user.id,
        'test_strategy_submitted',
        'TestStrategy',
        strategy_id,
        strategy["project_id"],
        {"note": payload.note},
    )
    return updated


async def request_strategy_changes(strategy_id, payload, user):
    
    
    
    strategy = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.review'
    )
    require_independent_review(strategy, user, 'TEST_STRATEGY_SELF_REVIEW_FORBIDDEN')
    if user.id not in strategy.get("reviewer_ids", []):
        raise HTTPException(
            status_code=403, detail={"code": 'STRATEGY_REVIEW_ASSIGNMENT_REQUIRED'}
        )
    if user.id == strategy.get("created_by"):
        raise HTTPException(
            status_code=403, detail={"code": 'STRATEGY_SELF_REVIEW_NOT_ALLOWED'}
        )
    updated = await test_strategy_repository.update(
        strategy_id,
        strategy["project_id"],
        payload.expected_revision,
        {'IN_REVIEW'},
        {
            "status": 'DRAFT',
            "reviewed_by": list(dict.fromkeys([*strategy.get("reviewed_by", []), user.id])),
            "change_request": payload.note,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'STRATEGY_TRANSITION_CONFLICT'})
    await audit(
        user.id,
        'test_strategy_changes_requested',
        'TestStrategy',
        strategy_id,
        strategy["project_id"],
        {"note": payload.note},
    )
    return updated


async def approve_strategy(strategy_id, payload, user):
    
    
    
    strategy = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.approve'
    )
    require_independent_review(strategy, user, 'TEST_STRATEGY_SELF_REVIEW_FORBIDDEN')
    if user.id not in strategy.get("reviewer_ids", []):
        raise HTTPException(status_code=403, detail={"code": 'STRATEGY_REVIEW_ASSIGNMENT_REQUIRED'})
    if strategy["status"] != 'IN_REVIEW':
        raise HTTPException(status_code=409, detail={"code": 'STRATEGY_NOT_IN_REVIEW'})
    if payload.expected_revision != strategy["revision"]:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    completeness = strategy_completeness(strategy)
    if not completeness["ready_for_review"]:
        raise HTTPException(
            status_code=409, detail={"code": 'TEST_STRATEGY_INCOMPLETE', **completeness}
        )
    if not strategy.get("reviewed_by"):
        raise HTTPException(status_code=409, detail={"code": 'STRATEGY_REVIEW_REQUIRED'})
    timestamp = now()
    existing = await test_strategy_repository.active_approved(
        strategy["project_id"], 'APPROVED', strategy_id
    )
    if existing:
        await test_strategy_repository.update(
            existing["_id"],
            strategy["project_id"],
            existing["revision"],
            {'APPROVED'},
            {
                "status": 'SUPERSEDED',
                "active_approved": False,
                "superseded_by": strategy_id,
                "superseded_at": timestamp,
                "updated_at": timestamp,
            },
        )
    snapshot = strategy_snapshot(strategy)
    approval = {
        "actor_id": user.id,
        "action": 'APPROVED',
        "note": payload.note,
        "at": timestamp,
    }
    try:
        updated = await test_strategy_repository.update(
            strategy_id,
            strategy["project_id"],
            payload.expected_revision,
            {'IN_REVIEW'},
            {
                "status": 'APPROVED',
                "active_approved": True,
                "approved_by": user.id,
                "approved_at": timestamp,
                "approved_snapshot": snapshot,
                "snapshot_hash": strategy_hash(strategy),
                "approval_history": [*strategy.get("approval_history", []), approval],
                "updated_at": timestamp,
            },
        )
    except DuplicateKeyError as error:
        if existing:
            await test_strategy_repository.update(
                existing["_id"],
                strategy["project_id"],
                existing["revision"] + 1,
                {'SUPERSEDED'},
                {"status": 'APPROVED', "active_approved": True, "updated_at": now()},
            )
        raise HTTPException(
            status_code=409, detail={"code": 'TEST_STRATEGY_ACTIVE_CONFLICT'}
        ) from error
    if not updated:
        if existing:
            await test_strategy_repository.update(
                existing["_id"],
                strategy["project_id"],
                existing["revision"] + 1,
                {'SUPERSEDED'},
                {"status": 'APPROVED', "active_approved": True, "updated_at": now()},
            )
        raise HTTPException(status_code=409, detail={"code": 'STRATEGY_TRANSITION_CONFLICT'})
    await audit(
        user.id,
        'test_strategy_approved',
        'TestStrategy',
        strategy_id,
        strategy["project_id"],
        {
            "snapshot_hash": updated["snapshot_hash"],
            "superseded_strategy_id": existing.get("_id") if existing else None,
        },
    )
    return updated


async def create_strategy_version(strategy_id, payload, user):
    
    
    
    strategy = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.version.create'
    )
    if strategy["status"] not in set(['APPROVED', 'SUPERSEDED']):
        raise HTTPException(
            status_code=409, detail={"code": 'STRATEGY_VERSION_SOURCE_NOT_APPROVED'}
        )
    if payload.expected_revision != strategy["revision"]:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    version = await test_strategy_repository.next_version(strategy["lineage_id"])
    timestamp = now()
    fields = {field: strategy.get(field) for field in TestStrategyFields.model_fields}
    value = {
        "_id": new_id('TSTR'),
        "lineage_id": strategy["lineage_id"],
        "project_id": strategy["project_id"],
        "key": strategy["key"],
        **fields,
        "version": version,
        "status": 'DRAFT',
        "active_approved": False,
        "reviewed_by": [],
        "approval_history": [],
        "version_reason": payload.change_reason,
        "derived_from_strategy_id": strategy_id,
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await test_strategy_repository.create(value)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=409, detail={"code": 'STRATEGY_VERSION_CONFLICT'}
        ) from error
    await audit(
        user.id,
        'test_strategy_version_created',
        'TestStrategy',
        value["_id"],
        strategy["project_id"],
        {"source_strategy_id": strategy_id, "version": version, "reason": payload.change_reason},
    )
    return value


async def validate_strategy(strategy_id, user):
    strategy = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.review'
    )
    return strategy_completeness(strategy)


async def review_strategy(strategy_id, payload, user):
    
    
    
    strategy = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.review'
    )
    if strategy["status"] != 'IN_REVIEW':
        raise HTTPException(status_code=409, detail={"code": 'TEST_STRATEGY_NOT_IN_REVIEW'})
    if user.id not in strategy.get("reviewer_ids", []):
        raise HTTPException(
            status_code=403, detail={"code": 'STRATEGY_REVIEW_ASSIGNMENT_REQUIRED'}
        )
    if user.id == strategy.get("created_by"):
        raise HTTPException(
            status_code=403, detail={"code": 'STRATEGY_SELF_REVIEW_NOT_ALLOWED'}
        )
    entry = {"reviewer_id": user.id, "note": payload.note, "at": now()}
    updated = await test_strategy_repository.update(
        strategy_id,
        strategy["project_id"],
        payload.expected_revision,
        {'IN_REVIEW'},
        {
            "reviewed_by": list(dict.fromkeys([*strategy.get("reviewed_by", []), user.id])),
            "review_history": [*strategy.get("review_history", []), entry],
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'test_strategy_reviewed',
        'TestStrategy',
        strategy_id,
        strategy["project_id"],
        {"note": payload.note},
    )
    return updated


async def compare_strategies(strategy_id, other_strategy_id, user):
    
    left = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.version.read'
    )
    right = await get_strategy_for_user(
        other_strategy_id, user, 'teststrategy.version.read'
    )
    if left["project_id"] != right["project_id"]:
        raise HTTPException(
            status_code=422,
            detail={"code": 'CROSS_PROJECT_REFERENCE'},
        )
    return compare_strategy_snapshots(left, right)


async def clone_strategy(project_id, payload, user):
    
    await get_project(project_id, user, 'teststrategy.create')
    source = await get_strategy_for_user(
        payload.source_strategy_id, user, 'teststrategy.read'
    )
    timestamp = now()
    strategy_id = new_id('TSTR')
    fields = {field: source.get(field) for field in TestStrategyFields.model_fields}
    fields["name"] = payload.name
    fields["tailoring_rationale"] = payload.tailoring_rationale
    value = {
        "_id": strategy_id,
        "lineage_id": strategy_id,
        "project_id": project_id,
        "key": payload.key,
        **fields,
        "version": 1,
        "status": 'DRAFT',
        "active_approved": False,
        "reviewed_by": [],
        "approval_history": [],
        "cloned_from_strategy_id": source["_id"],
        "cloned_from_project_id": source["project_id"],
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await test_strategy_repository.create(value)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": 'STRATEGY_KEY_VERSION_EXISTS'},
        ) from error
    await audit(
        user.id,
        'test_strategy_cloned',
        'TestStrategy',
        strategy_id,
        project_id,
        {"source_strategy_id": source["_id"]},
    )
    return value


async def archive_strategy(strategy_id, payload, user):
    
    strategy = await get_strategy_for_user(
        strategy_id, user, 'teststrategy.archive'
    )
    updated = await test_strategy_repository.update(
        strategy_id,
        strategy["project_id"],
        payload.expected_revision,
        set(['DRAFT', 'SUPERSEDED']),
        {
            "status": 'ARCHIVED',
            "active_approved": False,
            "archived_by": user.id,
            "archived_at": now(),
            "archive_reason": payload.note,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(
            status_code=409,
            detail={"code": 'STRATEGY_ARCHIVE_CONFLICT'},
        )
    await audit(
        user.id,
        'test_strategy_archived',
        'TestStrategy',
        strategy_id,
        strategy["project_id"],
        {"reason": payload.note},
    )
    return updated
