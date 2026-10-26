import json
import re
import hashlib

from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, next_key, now, page_payload
from src.schemas.test_analysis import TestConditionCreate, condition_hash, condition_snapshot
from src.repositories.test_condition import test_condition_repository
from src.repositories.test_analysis import test_analysis_repository
from src.repositories.requirement_analysis import requirement_analysis_repository
from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.modules.design.services.test_analysis_basis import (
    deterministic_testability_findings,
    list_test_basis,
    resolve_basis,
)



__all__ = ["list_test_basis"]


async def list_ai_analysis_results(project_id, user, limit=100, idempotency_key=None):
    if idempotency_key:
        await get_project(project_id, user, "testanalysis.run_ai")
        if (
            not getattr(user, "_ai_automation_run_id", "")
            or getattr(user, "_ai_automation_trigger", "") != "REQUIREMENT_CHANGED"
        ):
            raise HTTPException(403, detail={"code": "VERIFIED_REQUIREMENT_EVENT_REQUIRED"})
        result = await test_analysis_repository.find_ai_result(project_id, idempotency_key)
        if result and (
            result.get("created_by") != user.id
            or not result.get("source_event_id")
            or result.get("source_event_revision") is None
        ):
            raise HTTPException(404, detail={"code": "ENTITY_NOT_FOUND"})
        if result:
            result.pop("basis_snapshots", None)
            result.pop("created_by", None)
        return result
    await get_project(project_id, user, "testanalysis.read")
    return await test_analysis_repository.list_ai_results(project_id, limit)


async def get_condition_for_user(condition_id, user, permission=None):
    
    condition = await test_condition_repository.get(condition_id)
    if not condition:
        raise HTTPException(
            status_code=404,
            detail={"code": 'TEST_CONDITION_NOT_FOUND'},
        )
    await get_project(
        condition["project_id"],
        user,
        permission or 'testcondition.read',
    )
    return condition


async def list_conditions(project_id, user, q, status, risk, testability_status, page, page_size):
    await get_project(
        project_id, user, 'testcondition.read'
    )
    query = {"project_id": project_id}
    if q:
        query["$or"] = [
            {"condition_key": {"$regex": re.escape(q), "$options": "i"}},
            {"title": {"$regex": re.escape(q), "$options": "i"}},
            {"coverage_item": {"$regex": re.escape(q), "$options": "i"}},
        ]
    for field, value in {
        "status": status,
        "risk": risk,
        "testability_status": testability_status,
    }.items():
        if value:
            query[field] = value
    items, total = await test_condition_repository.list(query, (page - 1) * page_size, page_size)
    return page_payload(items, page, page_size, total)


async def create_condition(project_id, payload, user):
    
    await get_project(project_id, user, 'testcondition.create')
    basis_snapshots = await resolve_basis(project_id, payload.basis_refs, user)
    timestamp = now()
    value = {
        "_id": new_id('TCON'),
        "project_id": project_id,
        **payload.model_dump(),
        "condition_key": payload.condition_key
        or await next_key(
            project_id, 'test_condition', 'TCON'
        ),
        "basis_snapshots": basis_snapshots,
        "status": 'DRAFT',
        "reviewed_by": [],
        "approval_history": [],
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await test_condition_repository.create(value)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": 'TEST_CONDITION_KEY_EXISTS'},
        ) from error
    await audit(
        user.id,
        'test_condition_created',
        'TestCondition',
        value["_id"],
        project_id,
        {"basis_count": len(basis_snapshots), "origin": value["origin"]},
    )
    return value


async def update_condition(condition_id, payload, user):
    
    condition = await get_condition_for_user(
        condition_id, user, 'testcondition.update'
    )
    if condition["status"] != 'DRAFT':
        raise HTTPException(
            status_code=409,
            detail={"code": 'TEST_CONDITION_IMMUTABLE'},
        )
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if payload.basis_refs is not None:
        changes["basis_snapshots"] = await resolve_basis(
            condition["project_id"], payload.basis_refs, user
        )
    TestConditionCreate.model_validate({**condition, **changes})
    changes["updated_at"] = now()
    updated = await test_condition_repository.update(
        condition_id,
        condition["project_id"],
        payload.expected_revision,
        {'DRAFT'},
        changes,
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    await audit(
        user.id,
        'test_condition_updated',
        'TestCondition',
        condition_id,
        condition["project_id"],
        {"fields": sorted(field for field in changes if field != "updated_at")},
    )
    return updated


async def transition_condition(condition_id, payload, user, action):
    
    transition = {'submit': {'sources': ['DRAFT'],
            'target': 'IN_REVIEW',
            'permission': 'testcondition.review',
            'event': 'test_condition_submitted'},
 'approve': {'sources': ['IN_REVIEW'],
             'target': 'APPROVED',
             'permission': 'testcondition.approve',
             'event': 'test_condition_approved'},
 'archive': {'sources': ['DRAFT', 'APPROVED'],
             'target': 'ARCHIVED',
             'permission': 'testcondition.archive',
             'event': 'test_condition_archived'}}[action]
    condition = await get_condition_for_user(
        condition_id, user, transition["permission"]
    )
    sources = set(transition["sources"])
    target = transition["target"]
    if action in {"submit", "approve"}:
        try:
            TestConditionCreate.model_validate(condition)
        except ValidationError as error:
            raise HTTPException(
                status_code=409,
                detail={"code": 'TEST_CONDITION_INCOMPLETE'},
            ) from error
    changes = {"status": target, "updated_at": now()}
    if action == "submit":
        changes.update(
            {"submitted_by": user.id, "submitted_at": now(), "review_note": payload.note}
        )
    elif action == "approve":
        open_blockers = [
            finding
            for finding in condition.get("analysis_findings", [])
            if finding.get("status") == 'OPEN'
            and finding.get("severity") in set(['CRITICAL', 'HIGH'])
        ]
        if open_blockers:
            raise HTTPException(
                status_code=409, detail={"code": 'OPEN_TESTABILITY_FINDINGS'}
            )
        changes.update(
            {
                "approved_by": user.id,
                "approved_at": now(),
                "approved_snapshot": condition_snapshot(condition),
                "approved_snapshot_hash": condition_hash(condition),
                "approval_history": [
                    *condition.get("approval_history", []),
                    {
                        "actor_id": user.id,
                        "action": 'APPROVED',
                        "note": payload.note,
                        "at": now(),
                    },
                ],
            }
        )
    else:
        changes.update(
            {"archived_by": user.id, "archived_at": now(), "archive_reason": payload.note}
        )
    updated = await test_condition_repository.update(
        condition_id, condition["project_id"], payload.expected_revision, sources, changes
    )
    if not updated:
        raise HTTPException(
            status_code=409,
            detail={"code": 'TEST_CONDITION_TRANSITION_CONFLICT'},
        )
    await audit(
        user.id,
        transition["event"],
        'TestCondition',
        condition_id,
        condition["project_id"],
        {"from": condition["status"], "to": target, "note": payload.note},
    )
    return updated


async def resolve_finding(condition_id, finding_id, payload, user):
    
    condition = await get_condition_for_user(
        condition_id, user, 'testanalysis.resolve_finding'
    )
    if condition["status"] == 'ARCHIVED':
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'ARTIFACT_ARCHIVED',
                "artifact_type": 'TEST_CONDITION',
            },
        )
    found = False
    findings = []
    for finding in condition.get("analysis_findings", []):
        if finding.get("finding_id") != finding_id:
            findings.append(finding)
            continue
        found = True
        if finding.get("status") != 'OPEN':
            raise HTTPException(
                status_code=409,
                detail={"code": 'ANALYSIS_FINDING_ALREADY_RESOLVED'},
            )
        findings.append(
            {
                **finding,
                "status": payload.status,
                "resolved_by": user.id,
                "resolved_at": now(),
                "resolution_ref": payload.resolution_ref,
                "resolution_note": payload.note,
            }
        )
    if not found:
        raise HTTPException(
            status_code=404, detail={"code": 'FINDING_NOT_FOUND'}
        )
    updated = await test_condition_repository.update(
        condition_id,
        condition["project_id"],
        payload.expected_revision,
        set(['DRAFT', 'IN_REVIEW', 'APPROVED']),
        {"analysis_findings": findings, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    await audit(
        user.id,
        'test_analysis_finding_resolved',
        'TestCondition',
        condition_id,
        condition["project_id"],
        {
            "finding_id": finding_id,
            "status": payload.status,
            "resolution_ref": payload.resolution_ref,
        },
    )
    return updated


async def run_ai_analysis(project_id, payload, user):
    
    await get_project(project_id, user, 'testanalysis.run_ai')
    event_scoped = bool(payload.source_event_id or payload.source_event_revision)
    automation_trigger = str(getattr(user, "_ai_automation_trigger", "") or "")
    source_version_id = None
    if (
        not event_scoped
        or not payload.source_event_id
        or payload.source_event_revision is None
        or not getattr(user, "_ai_automation_run_id", "")
        or automation_trigger != "REQUIREMENT_CHANGED"
        or len(payload.basis_refs) != 1
        or payload.basis_refs[0].artifact_type != "REQUIREMENT_VERSION"
    ):
        raise HTTPException(403, detail={"code": "VERIFIED_REQUIREMENT_EVENT_REQUIRED"})
    if event_scoped:
        source_version_id = str(
            payload.basis_refs[0].artifact_version_id or payload.basis_refs[0].artifact_id
        )
        expected_event_id = (
            f"requirement-version:{source_version_id}:"
            f"{payload.source_event_revision}:BASELINED"
        )
        if payload.source_event_id != expected_event_id:
            raise HTTPException(409, detail={"code": "REQUIREMENT_EVENT_SOURCE_CHANGED"})
        expected_key = "test-condition-baseline:" + hashlib.sha256(
            f"{payload.source_event_id}:{source_version_id}".encode("utf-8")
        ).hexdigest()
        if payload.idempotency_key != expected_key:
            raise HTTPException(422, detail={"code": "TEST_CONDITION_EVENT_KEY_INVALID"})
    existing = await test_analysis_repository.find_ai_result(
        project_id, payload.idempotency_key
    )
    if existing:
        if existing.get("result_type") != 'TEST_CONDITION_CANDIDATES':
            raise HTTPException(
                status_code=409,
                detail={"code": 'IDEMPOTENCY_KEY_REUSED'},
            )
        if event_scoped and (
            existing.get("source_event_id") != payload.source_event_id
            or existing.get("source_event_revision") != payload.source_event_revision
            or existing.get("requirement_version_id") != source_version_id
        ):
            raise HTTPException(409, detail={"code": "TEST_CONDITION_EVENT_KEY_CONFLICT"})
        return existing
    basis_snapshots = await resolve_basis(project_id, payload.basis_refs, user)
    if event_scoped:
        version = await requirement_analysis_repository.find_version(
            source_version_id, project_id
        )
        requirement = (
            await requirement_analysis_repository.find_requirement(
                str(version.get("requirement_id") or ""), project_id
            )
            if version
            else None
        )
        if (
            not version
            or version.get("status") != "BASELINED"
            or version.get("revision") != payload.source_event_revision
            or not requirement
            or requirement.get("current_version_id") != source_version_id
        ):
            raise HTTPException(409, detail={"code": "REQUIREMENT_EVENT_SOURCE_CHANGED"})
        initial_source_hash = basis_snapshots[0].get("source_hash")
    evidence = [
        {
            "artifact_type": item["artifact_type"],
            "artifact_id": item["artifact_id"],
            "artifact_version_id": item.get("artifact_version_id") or item["resolved_id"],
            "authority": 'PROJECT_BASELINE',
            "text": item["text"],
        }
        for item in basis_snapshots
    ]
    instruction = json.dumps(
        {"user_instruction": payload.instruction},
        ensure_ascii=False,
    )
    ai_result = await request_ai_automation(
        "test_condition_generation", project_id, instruction, evidence
    )
    if ai_result.get("status") != "SUCCESS" or ai_result.get("degraded_mode"):
        raise HTTPException(
            503,
            detail={"code": "AI_PROVIDER_UNAVAILABLE", "retryable": True},
        )
    if event_scoped:
        current_version = await requirement_analysis_repository.find_version(
            source_version_id, project_id
        )
        current_requirement = (
            await requirement_analysis_repository.find_requirement(
                str(current_version.get("requirement_id") or ""), project_id
            )
            if current_version
            else None
        )
        current_basis = await resolve_basis(project_id, payload.basis_refs, user)
        if (
            not current_version
            or current_version.get("status") != "BASELINED"
            or current_version.get("revision") != payload.source_event_revision
            or not current_requirement
            or current_requirement.get("current_version_id") != source_version_id
            or current_basis[0].get("source_hash") != initial_source_hash
        ):
            raise HTTPException(409, detail={"code": "REQUIREMENT_EVENT_SOURCE_CHANGED"})
        basis_snapshots = current_basis
    suggestions = ai_result.get("suggestions", [])
    if not isinstance(suggestions, list) or any(not isinstance(item, dict) for item in suggestions):
        raise HTTPException(502, detail={"code": "AI_GENERATION_INVALID"})
    raw_candidates = [
        item
        for item in suggestions
        if isinstance(item, dict) and str(item.get("title") or "").strip()
    ]
    if len(raw_candidates) != len(suggestions) or len(raw_candidates) > 100:
        raise HTTPException(502, detail={"code": "AI_GENERATION_INVALID"})
    basis_by_ref = {}
    for snapshot in basis_snapshots:
        for reference in (
            str(snapshot.get("artifact_id") or ""),
            str(snapshot.get("artifact_version_id") or snapshot.get("resolved_id") or ""),
        ):
            if reference:
                basis_by_ref[reference] = snapshot
    for candidate in raw_candidates:
        citations = candidate.get("evidence_quotes")
        if not isinstance(citations, list) or not citations:
            raise HTTPException(502, detail={"code": "AI_GENERATION_INVALID"})
        for citation in citations:
            if not isinstance(citation, dict):
                raise HTTPException(502, detail={"code": "AI_GENERATION_INVALID"})
            source_ref = str(citation.get("evidence_ref") or "")
            quote = str(citation.get("quote") or "").strip()
            source_snapshot = basis_by_ref.get(source_ref)
            if not source_snapshot or len(quote) < 2 or quote not in str(source_snapshot.get("text") or ""):
                raise HTTPException(502, detail={"code": "AI_GENERATION_INVALID"})
    candidates = [
        {
            **item,
            "candidate_id": f"{'TCON-CAND-'}{index}",
            "status": 'CANDIDATE',
            "candidate_only": True,
            "basis_refs": [
                ref.model_dump()
                for ref in payload.basis_refs
                if any(
                    str(citation.get("evidence_ref") or "")
                    in {
                        str(ref.artifact_id),
                        str(ref.artifact_version_id or ""),
                    }
                    for citation in item.get("evidence_quotes", [])
                    if isinstance(citation, dict)
                )
            ],
        }
        for index, item in enumerate(raw_candidates, 1)
    ]
    value = {
        "_id": new_id('AIR'),
        "project_id": project_id,
        "result_type": 'TEST_CONDITION_CANDIDATES',
        "candidates": candidates,
        "basis_snapshots": basis_snapshots,
        "requirement_version_id": source_version_id if event_scoped else None,
        "source_event_id": payload.source_event_id,
        "source_event_revision": payload.source_event_revision,
        "generation_status": ai_result.get("status", "DEGRADED"),
        "candidate_only": True,
        "human_confirmation_required": True,
        **ai_contract_metadata(ai_result),
        "idempotency_key": payload.idempotency_key,
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        await test_analysis_repository.insert_ai_result(value)
    except DuplicateKeyError:
        return await test_analysis_repository.find_ai_result(
            project_id, payload.idempotency_key
        )
    await audit(
        user.id,
        'test_analysis_ai_candidates_generated',
        'AIResult',
        value["_id"],
        project_id,
        {"candidate_count": len(candidates), "status": value["status"]},
    )
    return value


async def condition_coverage(project_id, user):
    
    await get_project(project_id, user, 'testcondition.read')
    conditions = await test_analysis_repository.list_conditions(
        project_id, 'ARCHIVED', 5000
    )
    condition_ids = [item["_id"] for item in conditions]
    scenarios = await test_analysis_repository.list_scenarios(
        project_id, condition_ids, 5000
    )
    case_versions = await test_analysis_repository.list_case_versions(
        project_id,
        condition_ids,
        [item["_id"] for item in scenarios],
        10000,
    )
    rows = []
    for condition in conditions:
        linked_scenarios = [
            item["_id"]
            for item in scenarios
            if condition["_id"] in item.get("test_condition_ids", [])
        ]
        linked_cases = [
            item["_id"]
            for item in case_versions
            if condition["_id"] in item.get("test_condition_ids", [])
            or item.get("scenario_id") in linked_scenarios
        ]
        rows.append(
            {
                "condition_id": condition["_id"],
                "condition_key": condition["condition_key"],
                "title": condition["title"],
                "basis_refs": condition["basis_refs"],
                "scenario_ids": linked_scenarios,
                "test_case_version_ids": linked_cases,
                "uncovered": not linked_cases,
            }
        )
    return {
        "items": rows,
        "condition_count": len(rows),
        "uncovered_count": sum(item["uncovered"] for item in rows),
    }


async def run_deterministic_analysis(project_id, payload, user):
    
    await get_project(project_id, user, 'testanalysis.execute')
    snapshots = await resolve_basis(project_id, payload.basis_refs, user)
    findings = deterministic_testability_findings(snapshots)
    await audit(
        user.id,
        'test_analysis_executed',
        'Project',
        project_id,
        project_id,
        {
            "basis_count": len(snapshots),
            "finding_count": len(findings),
            "engine": 'deterministic_rules',
        },
    )
    return {
        "status": 'SUCCESS',
        "engine": 'deterministic_rules',
        "findings": findings,
        "basis_snapshots": snapshots,
    }


async def list_analysis_findings(project_id, user, status="", limit=500):
    await get_project(
        project_id, user, 'testanalysis.read'
    )
    query = {"project_id": project_id}
    if status:
        query["status"] = status
    items = await test_analysis_repository.list_findings(query, limit)
    return {"items": items, "total": len(items)}


async def create_analysis_finding(project_id, payload, user):
    
    await get_project(project_id, user, 'testanalysis.finding.create')
    ref_type = payload.artifact_type.upper()
    collection_name = "requirement_versions" if ref_type == "REQUIREMENT_VERSION" else "acceptance_criteria" if ref_type == "ACCEPTANCE_CRITERION" else "api_operations" if ref_type == "API_OPERATION" else "requirement_documents" if ref_type in {"KNOWLEDGE_SOURCE", "REGULATION"} else "business_rules" if ref_type == "BUSINESS_RULE" else "risk_rankings" if ref_type == "RISK_RANKING" else "defects" if ref_type == "DEFECT" else None
    if not collection_name:
        raise HTTPException(
            status_code=422, detail={"code": 'TEST_BASIS_TYPE_INVALID'}
        )
    identifier = payload.artifact_version_id or payload.artifact_id
    if collection_name == "requirement_documents":
        from src.modules.requirements.services.requirement_documents import get_requirement_document_record

        await get_requirement_document_record(identifier, user, "requirement_document.read")
    elif not await test_analysis_repository.find_basis(
        collection_name, identifier, project_id
    ):
        raise HTTPException(
            status_code=422,
            detail={"code": 'CROSS_PROJECT_REFERENCE'},
        )
    timestamp = now()
    value = {
        "_id": new_id('AFND'),
        "project_id": project_id,
        **payload.model_dump(),
        "status": 'OPEN',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await test_analysis_repository.insert_finding(value)
    await audit(
        user.id,
        'analysis_finding_created',
        'AnalysisFinding',
        value["_id"],
        project_id,
        {"category": value["category"], "severity": value["severity"]},
    )
    return value


async def assign_analysis_finding(finding_id, payload, user):
    
    finding = await test_analysis_repository.find_finding(finding_id)
    if not finding:
        raise HTTPException(
            status_code=404,
            detail={"code": 'ANALYSIS_FINDING_NOT_FOUND'},
        )
    await get_project(finding["project_id"], user, 'testanalysis.finding.assign')
    member = await test_analysis_repository.find_active_member(
        finding["project_id"], payload.owner_id, 'ACTIVE'
    )
    if not member:
        raise HTTPException(
            status_code=422,
            detail={"code": 'PROJECT_MEMBER_NOT_FOUND'},
        )
    updated = await test_analysis_repository.update_finding(
        {
            "_id": finding_id,
            "revision": payload.expected_revision,
            "status": {"$in": ['OPEN', 'IN_PROGRESS']},
        },
        {
            "owner_id": payload.owner_id,
            "status": 'IN_PROGRESS',
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'STALE_REVISION'}
        )
    await audit(
        user.id,
        'analysis_finding_assigned',
        'AnalysisFinding',
        finding_id,
        finding["project_id"],
        {"owner_id": payload.owner_id},
    )
    return updated


async def transition_analysis_finding(finding_id, payload, user, verify=False):
    
    finding = await test_analysis_repository.find_finding(finding_id)
    if not finding:
        raise HTTPException(
            status_code=404,
            detail={"code": 'ANALYSIS_FINDING_NOT_FOUND'},
        )
    permission = (
        'testanalysis.verify_finding'
        if verify
        else 'testanalysis.resolve_finding'
    )
    await get_project(finding["project_id"], user, permission)
    if (verify and finding.get("status") != 'RESOLVED') or (
        not verify and finding.get("status") not in ['OPEN', 'IN_PROGRESS']
    ):
        if finding.get("status") in ['RESOLVED', 'VERIFIED', 'ACCEPTED_RISK']:
            raise HTTPException(
                status_code=409,
                detail={"code": 'ANALYSIS_FINDING_ALREADY_RESOLVED'},
            )
        raise HTTPException(
            status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'}
        )
    source = (
        'RESOLVED'
        if verify
        else {"$in": ['OPEN', 'IN_PROGRESS']}
    )
    target = 'VERIFIED' if verify else 'RESOLVED'
    changes = {
        "status": target,
        "updated_at": now(),
        "resolution": payload.resolution,
        "resolution_ref": payload.resolution_ref,
    }
    changes["verified_by" if verify else "resolved_by"] = user.id
    changes["verified_at" if verify else "resolved_at"] = now()
    updated = await test_analysis_repository.update_finding(
        {"_id": finding_id, "revision": payload.expected_revision, "status": source},
        changes,
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'}
        )
    await audit(
        user.id,
        'analysis_finding_verified'
        if verify
        else 'analysis_finding_resolved',
        'AnalysisFinding',
        finding_id,
        finding["project_id"],
        {},
    )
    return updated


async def review_condition(condition_id, payload, user):
    
    condition = await get_condition_for_user(
        condition_id, user, 'testcondition.review'
    )
    updated = await test_condition_repository.update(
        condition_id,
        condition["project_id"],
        payload.expected_revision,
        {'IN_REVIEW'},
        {
            "reviewed_by": list(dict.fromkeys([*condition.get("reviewed_by", []), user.id])),
            "review_note": payload.note,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'STALE_REVISION'}
        )
    await audit(
        user.id,
        'test_condition_reviewed',
        'TestCondition',
        condition_id,
        condition["project_id"],
        {"note": payload.note},
    )
    return updated


async def bulk_prioritize_conditions(project_id, payload, user):
    
    await get_project(project_id, user, 'testcondition.bulk.update')
    results = []
    for item in payload.items:
        condition = await test_condition_repository.get(item["condition_id"], project_id)
        if not condition:
            raise HTTPException(
                status_code=404,
                detail={"code": 'TEST_CONDITION_NOT_FOUND'},
            )
        updated = await test_condition_repository.update(
            item["condition_id"],
            project_id,
            int(item["expected_revision"]),
            {'DRAFT'},
            {"priority": item["priority"], "updated_at": now()},
        )
        if not updated:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": 'STALE_REVISION',
                    "condition_id": item["condition_id"],
                },
            )
        results.append(updated)
        await audit(
            user.id,
            'test_condition_updated',
            'TestCondition',
            item["condition_id"],
            project_id,
            {"fields": ["priority"]},
        )
    return {"items": results, "total": len(results)}
