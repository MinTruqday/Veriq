import hashlib
import json

from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now, page_payload, sort_spec
from src.core.metrics import PROPOSAL_ACCEPTANCE_RATE
from src.repositories.maintenance_proposal import maintenance_proposal_repository


async def create_maintenance_proposal_records(analysis_id, user):
    
    analysis = await get_project_entity("impact_analyses", analysis_id, user, "ai.create_proposal")
    if analysis.get("status") != 'REVIEWED':
        raise HTTPException(status_code=409, detail={"code": 'IMPACT_REVIEW_REQUIRED'})
    existing = await maintenance_proposal_repository.list_by_impact_and_status(
        analysis_id, 'PENDING', 10000
    )
    if existing:
        return existing
    proposals = []
    change_set = await maintenance_proposal_repository.find_change_set(
        analysis["change_set_id"]
    )
    for item in analysis.get("reviewed_affected_test_cases", analysis["affected_test_cases"]):
        if item["classification"] != 'NEEDS_UPDATE':
            continue
        patch = item.get("ai_maintenance_patch", {})
        if not patch:
            continue
        proposals.append(
            {
                "_id": new_id('MP'),
                "project_id": analysis["project_id"],
                "impact_analysis_id": analysis_id,
                "proposal_type": 'UPDATE_TEST_CASE',
                "test_case_key": item.get("test_case_key"),
                "target_artifact_id": item["test_case_id"],
                "base_version_id": item["test_case_version_id"],
                "patch": patch,
                "confidence": item.get("confidence", 0),
                "reason": " · ".join(item["reasons"]),
                "evidence": item["evidence"] + change_set["changes"],
                "status": 'PENDING',
                "revision": 1,
                "model_version": 'maintenance_analysis',
                "created_by": user.id,
                "created_at": now(),
                "updated_at": now(),
            }
        )
    for item in analysis.get("new_test_requirements", []):
        patch = item.get("patch", {})
        if not patch:
            continue
        proposals.append(
            {
                "_id": new_id('MP'),
                "project_id": analysis["project_id"],
                "impact_analysis_id": analysis_id,
                "proposal_type": 'CREATE_TEST_CASE',
                "target_artifact_id": None,
                "base_version_id": None,
                "patch": patch,
                "reason": item["reason"],
                "confidence": item.get("confidence", 0),
                "evidence": item["evidence"],
                "status": 'PENDING',
                "revision": 1,
                "model_version": 'maintenance_analysis',
                "created_by": user.id,
                "created_at": now(),
                "updated_at": now(),
            }
        )
    if proposals:
        await maintenance_proposal_repository.insert_many(proposals)
    await audit(
        user.id,
        "maintenance_proposals_created",
        "ImpactAnalysis",
        analysis_id,
        analysis["project_id"],
        {"count": len(proposals)},
    )
    return proposals


async def list_maintenance_proposal_records(
    project_id,
    user,
    status="",
    proposal_type="",
    target_artifact_id="",
    impact_analysis_id="",
    sort="-created_at",
    limit=100,
    page=0,
    page_size=100,
):
    
    await get_project(project_id, user, "proposal.read")
    query = {"project_id": project_id}
    for field, value in {
        "status": status,
        "proposal_type": proposal_type,
        "target_artifact_id": target_artifact_id,
        "impact_analysis_id": impact_analysis_id,
    }.items():
        if value:
            query[field] = value
    sort_field, direction = sort_spec(
        sort, set(['status', 'proposal_type', 'confidence', 'created_at', 'updated_at']), "-created_at"
    )
    if page:
        limit = page_size
        scope_snapshot = await maintenance_proposal_repository.proposal_scope_snapshot(
            query, sort_field, direction
        )
        total = len(scope_snapshot)
        skip = (page - 1) * page_size
    else:
        scope_snapshot = None
        total = None
        skip = 0
    proposals = await maintenance_proposal_repository.list_proposals(
        query, sort_field, direction, limit, skip
    )
    if page:
        expected_page = scope_snapshot[skip : skip + page_size]
        scope_fields = (
            "_id",
            "project_id",
            "impact_analysis_id",
            "proposal_type",
            "target_artifact_id",
            "base_version_id",
            "status",
            "revision",
        )
        if len(proposals) != len(expected_page) or any(
            any(proposal.get(field) != expected.get(field) for field in scope_fields)
            for proposal, expected in zip(proposals, expected_page)
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "MAINTENANCE_PROPOSAL_SCOPE_CHANGED_DURING_READ"},
            )
    base_ids = [item.get("base_version_id") for item in proposals if item.get("base_version_id")]
    bases = await maintenance_proposal_repository.list_test_case_versions(
        project_id, base_ids, limit
    )
    by_id = {item["_id"]: item for item in bases}
    analysis_ids = [
        item.get("impact_analysis_id") for item in proposals if item.get("impact_analysis_id")
    ]
    analyses = await maintenance_proposal_repository.list_impact_analyses(
        project_id, analysis_ids, limit
    )
    analyses_by_id = {item["_id"]: item for item in analyses}
    records = [
        {
            **item,
            "base_version": by_id.get(item.get("base_version_id")),
            "impact_analysis": analyses_by_id.get(item.get("impact_analysis_id")),
        }
        for item in proposals
    ]
    if page:
        payload = page_payload(records, page, page_size, total)
        payload["scope_fingerprint"] = hashlib.sha256(
            json.dumps(
                scope_snapshot,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return payload
    return records


async def get_maintenance_proposal_record(proposal_id, user, permission="proposal.read"):
    return await get_project_entity("maintenance_proposals", proposal_id, user, permission)


async def review_maintenance_proposal_record(project_id, proposal_id, payload, user):
    
    proposal = await get_maintenance_proposal_record(proposal_id, user, "proposal.review")
    if proposal["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if proposal.get("status") != 'PENDING':
        raise HTTPException(status_code=409, detail={"code": 'PROPOSAL_NOT_REVIEWABLE'})
    if proposal.get("revision") != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    changes = {
        "review_note": payload.review_note,
        "updated_at": now(),
        "last_reviewed_by": user.id,
        "last_reviewed_at": now(),
    }
    if payload.patch is not None:
        changes["patch"] = payload.patch
    updated = await maintenance_proposal_repository.update(
        {
            "_id": proposal_id,
            "project_id": project_id,
            "status": 'PENDING',
            "revision": payload.expected_revision,
        },
        changes,
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id, "maintenance_proposal_reviewed", "MaintenanceProposal", proposal_id, project_id
    )
    return updated


def require_pending_revision(proposal, payload, allow_partial=False):
    
    allowed = (
        {'PENDING', 'APPLY_PARTIAL'}
        if allow_partial
        else {'PENDING'}
    )
    if proposal["status"] not in allowed:
        raise HTTPException(status_code=409, detail={"code": 'PROPOSAL_ALREADY_REVIEWED'})
    if proposal["revision"] != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_revision": proposal["revision"]},
        )


async def update_proposal_acceptance_rate(project_id):
    
    total = await maintenance_proposal_repository.count_by_statuses(
        project_id, ['ACCEPTED', 'EDITED_ACCEPTED', 'REJECTED']
    )
    accepted = await maintenance_proposal_repository.count_by_statuses(
        project_id, ['ACCEPTED', 'EDITED_ACCEPTED']
    )
    PROPOSAL_ACCEPTANCE_RATE.set(accepted / total if total else 0)


async def reject_maintenance_proposal_record(proposal_id, payload, user):
    
    proposal = await get_maintenance_proposal_record(proposal_id, user, "proposal.reject")
    if proposal.get("status") == 'REJECTED':
        return proposal
    require_pending_revision(proposal, payload)
    timestamp = now()
    proposal = await maintenance_proposal_repository.update(
        {
            "_id": proposal_id,
            "project_id": proposal["project_id"],
            "status": 'PENDING',
            "revision": payload.expected_revision,
        },
        {
            "status": 'REJECTED',
            "review_note": payload.review_note,
            "reviewed_by": user.id,
            "reviewed_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not proposal:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await update_proposal_acceptance_rate(proposal["project_id"])
    await audit(
        user.id,
        "maintenance_proposal_rejected",
        "MaintenanceProposal",
        proposal_id,
        proposal["project_id"],
    )
    return proposal


async def regenerate_maintenance_proposal_record(proposal_id, payload, user):
    
    proposal = await get_maintenance_proposal_record(proposal_id, user, "ai.create_proposal")
    if proposal.get("status") != 'PENDING':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    if proposal.get("revision") != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    replacement = {
        **{
            key: value
            for key, value in proposal.items()
            if key
            not in {
                "_id",
                "status",
                "revision",
                "created_at",
                "updated_at",
                "reviewed_at",
                "reviewed_by",
            }
        },
        "_id": new_id('MP'),
        "parent_proposal_id": proposal_id,
        "regeneration_instruction": payload.instruction,
        "status": 'PENDING',
        "revision": 1,
        "model_version": 'maintenance_analysis',
        "created_by": user.id,
        "created_at": now(),
        "updated_at": now(),
    }
    updated = await maintenance_proposal_repository.update(
        {
            "_id": proposal_id,
            "project_id": proposal["project_id"],
            "status": 'PENDING',
            "revision": payload.expected_revision,
        },
        {
            "status": 'SUPERSEDED',
            "superseded_by": replacement["_id"],
            "regeneration_instruction": payload.instruction,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    try:
        await maintenance_proposal_repository.insert(replacement)
    except Exception:
        await maintenance_proposal_repository.rollback_supersede(
            proposal_id,
            proposal["project_id"],
            replacement["_id"],
            'PENDING',
            now(),
        )
        raise
    await audit(
        user.id,
        "maintenance_proposal_regenerated",
        "MaintenanceProposal",
        replacement["_id"],
        proposal["project_id"],
        {"parent_proposal_id": proposal_id},
    )
    return replacement
