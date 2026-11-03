import hashlib
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.core.database import database
from src.schemas.review_session import ReviewSessionCreate
from src.repositories.review import review_repository
from src.modules.quality.services.review_finding import (
    add_finding,
    assign_finding,
    resolve_finding,
    verify_finding,
)
from src.modules.quality.services.review_session_export import export_review_csv
from src.modules.quality.services.review_session_query import get_review, list_reviews, validate_members


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





async def create_review(project_id, payload, user):
    
    await get_project(project_id, user, 'reviewsession.create')
    collection_name = {'REQUIREMENT': 'requirements',
 'TEST_STRATEGY': 'test_strategies',
 'TEST_PLAN': 'test_plans',
 'TEST_CONDITION': 'test_conditions',
 'TEST_CASE': 'test_cases',
 'IMPACT_ANALYSIS': 'impact_analyses',
 'TEST_COMPLETION': 'test_completion_reports',
 'COMPLETION_REPORT': 'test_completion_reports',
 'STATUS_REPORT': 'test_status_reports'}.get(payload.artifact_type.upper())
    if not collection_name:
        raise HTTPException(
            status_code=422,
            detail={"code": 'UNSUPPORTED_REVIEW_ARTIFACT'},
        )
    artifact = await review_repository.find_artifact(
        collection_name, payload.artifact_id, project_id
    )
    if not artifact:
        raise HTTPException(
            status_code=422,
            detail={"code": 'REVIEW_ARTIFACT_NOT_IN_PROJECT'},
        )
    version_mapping = {'REQUIREMENT': ['requirement_versions', 'requirement_id'],
 'TEST_CASE': ['test_case_versions', 'test_case_id']}.get(
        payload.artifact_type.upper()
    )
    if version_mapping:
        version_collection, parent_field = version_mapping
        version = await review_repository.find_artifact(
            version_collection,
            payload.artifact_version_id,
            project_id,
            {parent_field: payload.artifact_id},
        )
        if not version:
            raise HTTPException(
                status_code=422,
                detail={"code": 'REVIEW_ARTIFACT_VERSION_NOT_IN_PROJECT'},
            )
    elif payload.artifact_version_id != payload.artifact_id:
        raise HTTPException(
            status_code=422,
            detail={"code": 'REVIEW_ARTIFACT_VERSION_MISMATCH'},
        )
    await validate_members(
        project_id,
        [payload.moderator_id, payload.author_id, *payload.reviewers, payload.scribe_id],
    )
    if payload.idempotency_key:
        existing = await review_repository.find_review_by_idempotency(
            project_id, payload.idempotency_key
        )
        if existing:
            _verify_create_replay(existing, payload, user)
            return existing
    timestamp = now()
    sequence = await review_repository.next_sequence(
        f"{project_id}:{'formal-review'}"
    )
    value = {
        "_id": new_id('RVS'),
        "project_id": project_id,
        **payload.model_dump(),
        "idempotency_request_hash": (
            _create_request_hash(payload) if payload.idempotency_key else None
        ),
        "review_key": f"{'RVS'}-{int(sequence['value']):04d}",
        "checklist_version_id": payload.checklist_version,
        "reviewer_ids": payload.reviewers,
        "status": 'PLANNED',
        "decision": None,
        "started_at": None,
        "decision_at": None,
        "completed_at": None,
        "metrics": {},
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await review_repository.insert_review(value, session=session)
                await audit(
                    user.id,
                    'formal_review_created',
                    'ReviewSession',
                    value["_id"],
                    project_id,
                    {"artifact_id": payload.artifact_id, "artifact_version_id": payload.artifact_version_id},
                    session=session,
                )
    except DuplicateKeyError:
        if payload.idempotency_key:
            existing = await review_repository.find_review_by_idempotency(
                project_id, payload.idempotency_key
            )
            if existing:
                _verify_create_replay(existing, payload, user)
                return existing
        raise
    return value


async def update_review(review_id, payload, user):
    
    review = await get_review(review_id, user, 'reviewsession.update')
    if review["status"] not in ['PLANNED', 'IN_PROGRESS']:
        raise HTTPException(
            status_code=409,
            detail={"code": 'COMPLETED_REVIEW_IMMUTABLE'},
        )
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "reviewers" in changes:
        changes["reviewers"] = list(dict.fromkeys(changes["reviewers"]))
        changes["reviewer_ids"] = changes["reviewers"]
    participants = [
        changes.get("moderator_id", review["moderator_id"]),
        review["author_id"],
        *(changes.get("reviewers") or review["reviewers"]),
        changes.get("scribe_id", review.get("scribe_id")),
    ]
    if review["author_id"] in participants[2:-1] or participants[0] in participants[2:-1]:
        raise HTTPException(
            status_code=422,
            detail={"code": 'REVIEW_PARTICIPANT_ROLE_CONFLICT'},
        )
    await validate_members(review["project_id"], participants)
    changes["updated_at"] = now()
    value = await review_repository.update_review(
        {
            "_id": review_id,
            "revision": payload.expected_revision,
            "status": {"$in": ['PLANNED', 'IN_PROGRESS']},
        },
        changes,
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'formal_review_updated',
        'ReviewSession',
        review_id,
        review["project_id"],
        {"fields": sorted(changes)},
    )
    return value


async def assign_reviewers(review_id, payload, user):
    
    review = await get_review(review_id, user, 'reviewsession.update')
    if review["status"] != 'PLANNED':
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVIEW_ASSIGNMENT_STATE_INVALID'},
        )
    if (
        review["author_id"] in payload.reviewer_ids
        or payload.moderator_id in payload.reviewer_ids
    ):
        raise HTTPException(
            status_code=422,
            detail={"code": 'REVIEW_PARTICIPANT_ROLE_CONFLICT'},
        )
    await validate_members(
        review["project_id"], [payload.moderator_id, *payload.reviewer_ids, payload.scribe_id]
    )
    changes = {
        "moderator_id": payload.moderator_id,
        "reviewers": list(dict.fromkeys(payload.reviewer_ids)),
        "reviewer_ids": list(dict.fromkeys(payload.reviewer_ids)),
        "scribe_id": payload.scribe_id,
        "updated_at": now(),
    }
    value = await review_repository.update_review(
        {
            "_id": review_id,
            "revision": payload.expected_revision,
            "status": 'PLANNED',
        },
        changes,
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'formal_review_reviewers_assigned',
        'ReviewSession',
        review_id,
        review["project_id"],
        {"reviewer_ids": changes["reviewer_ids"], "moderator_id": payload.moderator_id},
    )
    return value


async def review_metrics(review):
    
    findings = await review_repository.list_findings(
        review["_id"], 1000
    )
    timestamp = now()
    return {
        "finding_count": len(findings),
        "major_count": sum(
            1 for item in findings if item["severity"] == 'MAJOR'
        ),
        "open_count": sum(
            1
            for item in findings
            if item["status"]
            not in {'RESOLVED', 'VERIFIED'}
        ),
        "verified_count": sum(
            1 for item in findings if item["status"] == 'VERIFIED'
        ),
        "duration_seconds": max(
            0,
            int(((review.get("completed_at") or timestamp) - review["started_at"]).total_seconds()),
        )
        if review.get("started_at")
        else 0,
    }


async def record_review_decision(review_id, payload, user):
    
    review = await get_review(review_id, user, 'reviewsession.complete')
    if review.get("moderator_id") != user.id:
        raise HTTPException(status_code=403, detail={"code": 'REVIEW_MODERATOR_REQUIRED'})
    if review["status"] != 'IN_PROGRESS':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_REVIEW_TRANSITION'})
    metrics = await review_metrics(review)
    if (
        payload.decision in ['ACCEPTED', 'ACCEPTED_WITH_ACTIONS']
        and metrics["major_count"]
        and metrics["open_count"]
    ):
        open_major = await review_repository.count_findings(
            {
                "review_session_id": review_id,
                "severity": 'MAJOR',
                "status": {
                    "$nin": [
                        'RESOLVED',
                        'VERIFIED',
                    ]
                },
            }
        )
        if open_major:
            raise HTTPException(
                status_code=409,
                detail={"code": 'OPEN_MAJOR_REVIEW_FINDINGS'},
            )
    timestamp = now()
    value = await review_repository.update_review(
        {
            "_id": review_id,
            "revision": payload.expected_revision,
            "status": 'IN_PROGRESS',
        },
        {
            "status": 'DECISION_PENDING',
            "decision": payload.decision,
            "decision_note": payload.note,
            "decision_by": user.id,
            "decision_at": timestamp,
            "metrics": metrics,
            "updated_at": timestamp,
        },
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'formal_review_decision_recorded',
        'ReviewSession',
        review_id,
        review["project_id"],
        {"decision": payload.decision, "metrics": metrics},
    )
    return value


async def transition_review(review_id, payload, user, complete=False):
    
    review = await get_review(
        review_id,
        user,
        'reviewsession.complete' if complete else 'reviewsession.update',
    )
    if review["moderator_id"] != user.id:
        raise HTTPException(status_code=403, detail={"code": 'REVIEW_MODERATOR_REQUIRED'})
    source, target = (
        ('DECISION_PENDING', 'COMPLETED')
        if complete
        else ('PLANNED', 'IN_PROGRESS')
    )
    if review["status"] != source:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_REVIEW_TRANSITION'})
    timestamp = now()
    changes = {"status": target, "updated_at": timestamp, "transition_note": payload.note}
    if complete:
        changes.update(
            {
                "completed_at": timestamp,
                "metrics": await review_metrics({**review, "completed_at": timestamp}),
            }
        )
    else:
        changes["started_at"] = timestamp
    value = await review_repository.update_review(
        {"_id": review_id, "revision": payload.expected_revision, "status": source},
        changes,
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'formal_review_completed' if complete else 'formal_review_started',
        'ReviewSession',
        review_id,
        review["project_id"],
        {"decision": review.get("decision"), "metrics": changes.get("metrics")},
    )
    return value


async def transition_review_terminal(review_id, payload, user):
    
    review = await get_review(review_id, user, 'reviewsession.complete')
    if review.get("moderator_id") != user.id:
        raise HTTPException(status_code=403, detail={"code": 'REVIEW_MODERATOR_REQUIRED'})
    expected_source = (
        'PLANNED'
        if payload.target_status == 'CANCELLED'
        else 'COMPLETED'
    )
    if review["status"] != expected_source:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_REVIEW_TRANSITION'})
    timestamp = now()
    value = await review_repository.update_review(
        {"_id": review_id, "revision": payload.expected_revision, "status": expected_source},
        {
            "status": payload.target_status,
            "transition_note": payload.note,
            "updated_at": timestamp,
            "archived_at"
            if payload.target_status == 'ARCHIVED'
            else "cancelled_at": timestamp,
        },
    )
    if not value:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'formal_review_archived'
        if payload.target_status == 'ARCHIVED'
        else 'formal_review_cancelled',
        'ReviewSession',
        review_id,
        review["project_id"],
        {"note": payload.note},
    )
    return value


async def create_follow_up_review(review_id, payload, user):
    
    review = await get_review(review_id, user, 'reviewsession.create')
    if review["status"] != 'COMPLETED':
        raise HTTPException(
            status_code=409,
            detail={"code": 'FOLLOW_UP_REQUIRES_COMPLETED_REVIEW'},
        )
    if review["revision"] != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    create_payload = ReviewSessionCreate(
        idempotency_key=payload.idempotency_key,
        review_type=review["review_type"],
        artifact_type=review["artifact_type"],
        artifact_id=review["artifact_id"],
        artifact_version_id=review["artifact_version_id"],
        objective=payload.objective,
        checklist_version=review.get(
            "checklist_version_id",
            review.get("checklist_version", '1'),
        ),
        moderator_id=payload.moderator_id,
        author_id=review["author_id"],
        reviewers=payload.reviewer_ids,
        scribe_id=payload.scribe_id,
        planned_at=payload.planned_at,
        checklist=review.get("checklist", []),
    )
    value = await create_review(review["project_id"], create_payload, user)
    updated = await review_repository.set_review_fields(
        value["_id"],
        {
            "parent_review_session_id": review_id,
            "follow_up_number": int(review.get("follow_up_number", 0)) + 1,
        },
    )
    await audit(
        user.id,
        'formal_review_follow_up_created',
        'ReviewSession',
        updated["_id"],
        review["project_id"],
        {"parent_review_session_id": review_id},
    )
    return updated


class ReviewSessionService:
    @staticmethod
    async def list(project_id, user, status, artifact_type):
        return await list_reviews(project_id, user, status, artifact_type)

    @staticmethod
    async def create(project_id, payload, user):
        return await create_review(project_id, payload, user)

    @staticmethod
    async def get(review_id, user):
        
        value = await get_review(review_id, user)
        value["findings"] = await review_repository.list_findings(
            review_id, 1000
        )
        return value

    @staticmethod
    async def update(review_id, payload, user):
        return await update_review(review_id, payload, user)

    @staticmethod
    async def assign_reviewers(review_id, payload, user):
        return await assign_reviewers(review_id, payload, user)

    @staticmethod
    async def transition(review_id, payload, user, complete=False):
        return await transition_review(review_id, payload, user, complete)

    @staticmethod
    async def add_finding(review_id, payload, user):
        return await add_finding(review_id, payload, user)

    @staticmethod
    async def assign_finding(finding_id, payload, user):
        return await assign_finding(finding_id, payload, user)

    @staticmethod
    async def resolve_finding(finding_id, payload, user):
        return await resolve_finding(finding_id, payload, user)

    @staticmethod
    async def verify_finding(finding_id, payload, user):
        return await verify_finding(finding_id, payload, user)

    @staticmethod
    async def record_decision(review_id, payload, user):
        return await record_review_decision(review_id, payload, user)

    @staticmethod
    async def transition_terminal(review_id, payload, user):
        return await transition_review_terminal(review_id, payload, user)

    @staticmethod
    async def metrics(review_id, user):
        value = await get_review(review_id, user)
        return await review_metrics(value)

    @staticmethod
    async def create_follow_up(review_id, payload, user):
        return await create_follow_up_review(review_id, payload, user)

    @staticmethod
    async def export(review_id, user):
        value = await ReviewSessionService.get(review_id, user)
        return export_review_csv(value)
