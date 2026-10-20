from fastapi import HTTPException

from src.core.auth import roles_for_membership
from src.core.common import audit, get_project, new_id, now
from src.repositories.review import review_repository
from src.modules.quality.services.review_session_query import get_review, validate_members





async def add_finding(review_id, payload, user):
    
    review = await get_review(review_id, user, 'reviewsession.finding.manage')
    if review["status"] != 'IN_PROGRESS':
        raise HTTPException(status_code=409, detail={"code": 'COMPLETED_REVIEW_IMMUTABLE'})
    await validate_members(review["project_id"], [payload.owner_id])
    timestamp = now()
    value = {
        "_id": new_id('RVF'),
        "review_session_id": review_id,
        "project_id": review["project_id"],
        **payload.model_dump(),
        "status": 'OPEN',
        "resolution": "",
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await review_repository.insert_finding(value)
    await audit(
        user.id,
        'review_finding_created',
        'ReviewFinding',
        value["_id"],
        review["project_id"],
        {"review_session_id": review_id, "severity": value["severity"]},
    )
    return value


async def update_finding(finding_id, payload, user):
    
    finding = await review_repository.find_finding(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(finding["project_id"], user, 'reviewsession.finding.manage')
    review = await review_repository.find_review(finding["review_session_id"])
    if not review or review["status"] not in ['IN_PROGRESS', 'DECISION_PENDING']:
        raise HTTPException(status_code=409, detail={"code": 'COMPLETED_REVIEW_IMMUTABLE'})
    changes = {"status": payload.status, "resolution": payload.resolution, "updated_at": now()}
    value = await review_repository.update_finding(
        {"_id": finding_id, "revision": payload.expected_revision},
        changes,
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'formal_review_finding_updated',
        'ReviewFinding',
        finding_id,
        finding["project_id"],
        changes,
    )
    return value


async def get_finding_for_update(finding_id, user):
    
    finding = await review_repository.find_finding(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    await get_project(finding["project_id"], user, 'reviewsession.finding.manage')
    review = await review_repository.find_review(finding["review_session_id"])
    if not review or review["status"] != 'IN_PROGRESS':
        raise HTTPException(status_code=409, detail={"code": 'REVIEW_FINDING_STATE_INVALID'})
    return finding, review


async def assign_finding(finding_id, payload, user):
    
    finding, review = await get_finding_for_update(finding_id, user)
    await validate_members(review["project_id"], [payload.owner_id])
    timestamp = now()
    value = await review_repository.update_finding(
        {
            "_id": finding_id,
            "revision": payload.expected_revision,
            "status": {"$in": ['OPEN', 'IN_PROGRESS']},
        },
        {
            "owner_id": payload.owner_id,
            "status": 'IN_PROGRESS',
            "assigned_by": user.id,
            "assigned_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'formal_review_finding_assigned',
        'ReviewFinding',
        finding_id,
        finding["project_id"],
        {"owner_id": payload.owner_id},
    )
    return value


async def resolve_finding(finding_id, payload, user):
    
    finding, _ = await get_finding_for_update(finding_id, user)
    if finding.get("owner_id") != user.id:
        membership = await review_repository.find_active_member(
            finding["project_id"], user.id, 'ACTIVE'
        )
        if 'QA' not in roles_for_membership(membership):
            raise HTTPException(
                status_code=403,
                detail={"code": 'REVIEW_FINDING_OWNER_REQUIRED'},
            )
    timestamp = now()
    value = await review_repository.update_finding(
        {
            "_id": finding_id,
            "revision": payload.expected_revision,
            "status": {"$in": ['OPEN', 'IN_PROGRESS']},
        },
        {
            "status": 'RESOLVED',
            "resolution": payload.resolution,
            "resolved_by": user.id,
            "resolved_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'formal_review_finding_resolved',
        'ReviewFinding',
        finding_id,
        finding["project_id"],
        {"resolution": payload.resolution},
    )
    return value


async def verify_finding(finding_id, payload, user):
    
    finding, review = await get_finding_for_update(finding_id, user)
    reviewers = review.get("reviewer_ids", review.get("reviewers", []))
    if user.id not in reviewers and review.get("moderator_id") != user.id:
        raise HTTPException(status_code=403, detail={"code": 'REVIEW_VERIFIER_REQUIRED'})
    if finding.get("resolved_by") == user.id:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVIEW_INDEPENDENT_VERIFICATION_REQUIRED'},
        )
    timestamp = now()
    value = await review_repository.update_finding(
        {
            "_id": finding_id,
            "revision": payload.expected_revision,
            "status": 'RESOLVED',
        },
        {
            "status": 'VERIFIED',
            "verification_note": payload.note,
            "verified_by": user.id,
            "verified_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'review_finding_verified',
        'ReviewFinding',
        finding_id,
        finding["project_id"],
        {"note": payload.note},
    )
    return value
