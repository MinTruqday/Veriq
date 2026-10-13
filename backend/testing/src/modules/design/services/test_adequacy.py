from hashlib import sha256

from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, get_project_role, new_id, now
from src.repositories.requirement import requirement_repository
from src.repositories.test_adequacy import test_adequacy_repository
from src.repositories.test_design import test_design_repository


def _item_id(requirement_version_id, source_type, source_id, quote):
    value = f"{requirement_version_id}|{source_type}|{source_id}|{quote}".encode()
    return f"COV-{sha256(value).hexdigest()[:20]}"


async def _require_qa(project_id, user):
    if await get_project_role(project_id, user.id) != "QA":
        raise HTTPException(status_code=403, detail={"code": "QA_DECISION_REQUIRED"})


async def _sources(version):
    items = []
    criteria = await requirement_repository.list_acceptance_criteria(version["_id"], 500)
    for criterion in criteria:
        quote = criterion.get("plain_text") or ""
        if quote.strip():
            items.append({
                "source_type": "acceptance_criterion",
                "source_id": criterion["_id"],
                "source_ref": criterion.get("key") or criterion["_id"],
                "source_quote": quote,
            })
    for index, rule in enumerate(version.get("business_rules") or []):
        if str(rule).strip():
            items.append({
                "source_type": "business_rule",
                "source_id": str(index),
                "source_ref": f"business_rule:{index + 1}",
                "source_quote": str(rule).strip(),
            })
    if not items:
        quote = version.get("plain_text_projection") or version.get("title") or ""
        if quote.strip():
            items.append({
                "source_type": "requirement_version",
                "source_id": version["_id"],
                "source_ref": version["_id"],
                "source_quote": quote,
            })
    for item in items:
        item["coverage_item_id"] = _item_id(
            version["_id"], item["source_type"], item["source_id"], item["source_quote"]
        )
    return items


def _case_mapping(item, version):
    if item["source_type"] == "acceptance_criterion":
        return item["source_id"] in version.get("acceptance_criterion_ids", [])
    if item["source_type"] == "requirement_version":
        return item["source_id"] in version.get("requirement_version_ids", [])
    return item["coverage_item_id"] in version.get("coverage_item_ids", [])


async def _snapshot(requirement_version):
    cases = await test_design_repository.list_case_versions(
        {"project_id": requirement_version["project_id"], "requirement_version_ids": requirement_version["_id"], "status": "ACTIVE"},
        5000,
    )
    result = []
    for source in await _sources(requirement_version):
        mapped = [case for case in cases if _case_mapping(source, case)]
        result.append({
            **source,
            "test_case_versions": [
                {
                    "id": case["_id"],
                    "key": case.get("test_case_key"),
                    "title": case.get("title"),
                    "techniques": case.get("techniques", []),
                    "evidence_refs": case.get("evidence_refs", []),
                    "evidence_quotes": case.get("evidence_quotes", []),
                    "challenge_hypotheses": case.get("challenge_hypotheses", []),
                }
                for case in mapped
            ],
            "status": "COVERED_PENDING_REVIEW" if mapped else "UNASSESSED",
        })
    return result


def _merge_decisions(items, existing):
    previous = {item["coverage_item_id"]: item for item in (existing or {}).get("coverage_items", [])}
    for item in items:
        prior = previous.get(item["coverage_item_id"])
        if prior and prior.get("status") in {"MISSING_INFORMATION", "NOT_APPLICABLE", "WAIVED"}:
            item["status"] = prior["status"]
            item["decision"] = prior.get("decision")
            item["execution_feedback"] = prior.get("execution_feedback", [])
        elif prior:
            item["execution_feedback"] = prior.get("execution_feedback", [])
    return items


def _ratio(items):
    applicable = [item for item in items if item["status"] not in {"NOT_APPLICABLE", "WAIVED"}]
    verified = [item for item in applicable if item["status"] == "VERIFIED_COVERED"]
    return {"verified_covered": len(verified), "applicable": len(applicable)}


async def get_adequacy_assessment(requirement_version_id, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "testcase.read")
    assessment = await test_adequacy_repository.find(version["project_id"], requirement_version_id)
    if assessment:
        return assessment
    return await refresh_adequacy_assessment(requirement_version_id, user, None)


async def refresh_adequacy_assessment(requirement_version_id, user, expected_revision):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "testcase.read")
    await get_project(version["project_id"], user, "testcase.read")
    existing = await test_adequacy_repository.find(version["project_id"], requirement_version_id)
    if existing and expected_revision is not None and existing["revision"] != expected_revision:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "current_revision": existing["revision"]})
    items = _merge_decisions(await _snapshot(version), existing)
    timestamp = now()
    lifecycle = "DRAFT" if not existing or existing.get("status") != "APPROVED" else "DRAFT"
    value = {
        "requirement_id": version["requirement_id"],
        "requirement_version_id": version["_id"],
        "requirement_revision": version["revision"],
        "requirement_snapshot": {"title": version["title"], "status": version["status"], "revision": version["revision"]},
        "coverage_items": items,
        "coverage_ratio": _ratio(items),
        "status": lifecycle,
        "updated_at": timestamp,
    }
    if not existing:
        assessment = {
            "_id": new_id("ADA"), "project_id": version["project_id"], "revision": 1,
            "created_by": user.id, "created_at": timestamp, **value,
        }
        await test_adequacy_repository.insert(assessment)
    else:
        assessment = await test_adequacy_repository.replace(existing["_id"], version["project_id"], existing["revision"], value)
        if not assessment:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "test_adequacy_assessment_refreshed", "TestAdequacyAssessment", assessment["_id"], version["project_id"], {"requirement_version_id": version["_id"]})
    return assessment


async def supersede_requirement_assessments(project_id, requirement_id, requirement_version_id, user_id):
    timestamp = now()
    await test_adequacy_repository.supersede_for_requirement(
        project_id, requirement_id, requirement_version_id, timestamp
    )


async def invalidate_adequacy_for_test_case_version(version):
    await test_adequacy_repository.invalidate_for_requirement_versions(
        version["project_id"], version.get("requirement_version_ids", []), now()
    )
    await audit(
        user_id, "test_adequacy_assessment_superseded", "Requirement", requirement_id,
        project_id, {"current_requirement_version_id": requirement_version_id},
    )


async def submit_adequacy_assessment(assessment_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.submit_review")
    if assessment["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    value = {"status": "IN_REVIEW", "review_note": payload.note, "review_submitted_by": user.id, "review_submitted_at": now(), "updated_at": now()}
    updated = await test_adequacy_repository.replace(assessment_id, assessment["project_id"], payload.expected_revision, value)
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "test_adequacy_review_submitted", "TestAdequacyAssessment", assessment_id, assessment["project_id"])
    return updated


async def approve_adequacy_assessment(assessment_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.review")
    await _require_qa(assessment["project_id"], user)
    if assessment["status"] != "IN_REVIEW":
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    unresolved = [item["coverage_item_id"] for item in assessment["coverage_items"] if item["status"] not in {"COVERED_PENDING_REVIEW", "NOT_APPLICABLE", "WAIVED"}]
    if unresolved:
        raise HTTPException(status_code=409, detail={"code": "ADEQUACY_UNRESOLVED_ITEMS", "coverage_item_ids": unresolved})
    items = []
    for item in assessment["coverage_items"]:
        item = dict(item)
        if item["status"] == "COVERED_PENDING_REVIEW":
            item["status"] = "VERIFIED_COVERED"
        items.append(item)
    value = {"coverage_items": items, "coverage_ratio": _ratio(items), "status": "APPROVED", "approved_by": user.id, "approved_at": now(), "review_note": payload.note, "updated_at": now()}
    updated = await test_adequacy_repository.replace(assessment_id, assessment["project_id"], payload.expected_revision, value)
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "test_adequacy_assessment_approved", "TestAdequacyAssessment", assessment_id, assessment["project_id"])
    return updated


async def request_adequacy_changes(assessment_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.review")
    await _require_qa(assessment["project_id"], user)
    if assessment["status"] != "IN_REVIEW":
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    value = {"status": "DRAFT", "review_note": payload.note, "changes_requested_by": user.id, "changes_requested_at": now(), "updated_at": now()}
    updated = await test_adequacy_repository.replace(assessment_id, assessment["project_id"], payload.expected_revision, value)
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "test_adequacy_changes_requested", "TestAdequacyAssessment", assessment_id, assessment["project_id"])
    return updated


async def decide_coverage_item(assessment_id, coverage_item_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.read")
    if payload.status in {"NOT_APPLICABLE", "WAIVED"}:
        await _require_qa(assessment["project_id"], user)
    items = []
    found = False
    for item in assessment["coverage_items"]:
        item = dict(item)
        if item["coverage_item_id"] == coverage_item_id:
            found = True
            item["status"] = payload.status
            item["decision"] = {"reason": payload.reason, "decided_by": user.id, "decided_at": now()}
        items.append(item)
    if not found:
        raise HTTPException(status_code=404, detail={"code": "COVERAGE_ITEM_NOT_FOUND"})
    value = {"coverage_items": items, "coverage_ratio": _ratio(items), "status": "DRAFT", "updated_at": now()}
    updated = await test_adequacy_repository.replace(assessment_id, assessment["project_id"], payload.expected_revision, value)
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "test_adequacy_coverage_decided", "CoverageItem", coverage_item_id, assessment["project_id"], {"status": payload.status})
    return updated


async def add_execution_feedback(assessment_id, coverage_item_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.read")
    await _require_qa(assessment["project_id"], user)
    case = await test_design_repository.find_case_version(payload.test_case_version_id, assessment["project_id"])
    if not case:
        raise HTTPException(status_code=422, detail={"code": "TEST_CASE_VERSION_NOT_FOUND"})
    if payload.test_result_id:
        results = await test_design_repository.list_case_results(assessment["project_id"], [case["_id"]])
        if payload.test_result_id not in {item["_id"] for item in results}:
            raise HTTPException(status_code=422, detail={"code": "TEST_RESULT_NOT_LINKED"})
    if payload.defect_id and not await test_design_repository.find_defect(assessment["project_id"], payload.defect_id):
        raise HTTPException(status_code=422, detail={"code": "DEFECT_NOT_FOUND"})
    items = []
    found = False
    for item in assessment["coverage_items"]:
        item = dict(item)
        if item["coverage_item_id"] == coverage_item_id:
            found = True
            if case["_id"] not in {entry["id"] for entry in item.get("test_case_versions", [])}:
                raise HTTPException(status_code=422, detail={"code": "TEST_CASE_NOT_MAPPED_TO_COVERAGE_ITEM"})
            feedback = list(item.get("execution_feedback", []))
            feedback.append({"test_case_version_id": case["_id"], "outcome": payload.outcome, "test_result_id": payload.test_result_id, "defect_id": payload.defect_id, "note": payload.note, "recorded_by": user.id, "recorded_at": now()})
            item["execution_feedback"] = feedback
        items.append(item)
    if not found:
        raise HTTPException(status_code=404, detail={"code": "COVERAGE_ITEM_NOT_FOUND"})
    value = {"coverage_items": items, "status": "DRAFT", "updated_at": now()}
    updated = await test_adequacy_repository.replace(assessment_id, assessment["project_id"], payload.expected_revision, value)
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "test_adequacy_execution_feedback_recorded", "CoverageItem", coverage_item_id, assessment["project_id"], {"outcome": payload.outcome})
    return updated


async def adequacy_change_impact(requirement_id, user):
    requirement = await get_project_entity("requirements", requirement_id, user, "testcase.read")
    assessments = await test_adequacy_repository.list_for_requirement(requirement["project_id"], requirement_id)
    version_ids = [item["requirement_version_id"] for item in assessments]
    versions = await test_design_repository.list_case_versions(
        {"project_id": requirement["project_id"], "requirement_version_ids": {"$in": version_ids}, "status": "ACTIVE"}, 5000
    )
    current_version_id = requirement.get("current_version_id")
    return {
        "requirement_id": requirement_id,
        "current_requirement_version_id": current_version_id,
        "superseded_assessment_ids": [item["_id"] for item in assessments if item.get("status") == "SUPERSEDED"],
        "affected_test_case_versions": [
            {"id": version["_id"], "key": version.get("test_case_key"), "title": version.get("title"), "review_required": current_version_id not in version.get("requirement_version_ids", [])}
            for version in versions
        ],
    }
