from datetime import datetime, timezone
from hashlib import sha256
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.auth import ai_automation_context
from src.core.common import audit, get_project, get_project_entity, get_project_roles, new_id, now, plain_text, resolve_user_reference
from src.core.database import database
from src.repositories.project import project_repository
from src.repositories.requirement import requirement_repository
from src.repositories.requirement_clarification import requirement_clarification_repository
from src.repositories.test_adequacy import test_adequacy_repository
from src.repositories.test_design import test_design_repository


def _item_id(requirement_version_id, source_type, source_id, quote):
    value = f"{requirement_version_id}|{source_type}|{source_id}|{quote}".encode()
    return f"COV-{sha256(value).hexdigest()[:20]}"


async def _require_qa(project_id, user, *, allow_execution_feedback_automation=False):
    if "QA" not in await get_project_roles(project_id, user.id):
        automation = ai_automation_context.get()
        if (
            allow_execution_feedback_automation
            and isinstance(automation, dict)
            and automation.get("principal_id") == user.id
            and automation.get("publication_project_id") == project_id
            and "testadequacy.execution_feedback.record"
            in set(automation.get("publication_permissions") or [])
        ):
            return
        raise HTTPException(status_code=403, detail={"code": "QA_DECISION_REQUIRED"})


async def _replace_assessment_with_audit(
    assessment_id,
    project_id,
    expected_revision,
    value,
    user,
    action,
    entity_type="TestAdequacyAssessment",
    entity_id=None,
    details=None,
    expected_status=None,
    before_replace=None,
):
    async def commit(session):
        if before_replace is not None:
            await before_replace(session)
        updated = await test_adequacy_repository.replace(
            assessment_id,
            project_id,
            expected_revision,
            value,
            session=session,
            expected_status=expected_status,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        await audit(
            user.id,
            action,
            entity_type,
            entity_id or assessment_id,
            project_id,
            details,
            session=session,
        )
        return updated

    async with await database.client.start_session() as session:
        return await session.with_transaction(commit)


async def _sources(version):
    items = []
    criteria = await requirement_repository.list_acceptance_criteria(version["_id"], None)
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
    for operation in (version.get("details") or {}).get("api_operations", []):
        if not isinstance(operation, dict):
            continue
        method = str(operation.get("method") or "").strip().upper()
        path = str(operation.get("path") or operation.get("url_template") or "").strip()
        if not method or not path:
            continue
        identity = json.dumps(operation, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        items.append({
            "source_type": "api_operation",
            "source_id": sha256(identity.encode()).hexdigest(),
            "source_ref": f"{method} {path}",
            "source_quote": f"{method} {path}",
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
        item["requirement_version_id"] = version["_id"]
        item["coverage_item_id"] = _item_id(
            version["_id"], item["source_type"], item["source_id"], item["source_quote"]
        )
    return items


def _case_mapping(item, version):
    if item["source_type"] == "acceptance_criterion":
        return item["source_id"] in version.get("acceptance_criterion_ids", [])
    if item["source_type"] == "requirement_version":
        return item["source_id"] in version.get("requirement_version_ids", [])
    if item["coverage_item_id"] in version.get("coverage_item_ids", []):
        return True
    return _case_proves_coverage_item(
        {
            **version,
            "assurance_evidence_complete": _case_has_assurance_evidence(version),
        },
        item,
    )


def _case_has_assurance_evidence(version):
    has_data = bool(version.get("test_data")) or any(
        bool(step.get("test_data")) for step in version.get("steps", [])
    )
    return bool(
        version.get("techniques")
        and version.get("evidence_refs")
        and version.get("evidence_quotes")
        and has_data
        and plain_text(version.get("expected_result_doc", {})).strip()
    )


async def _snapshot(requirement_version):
    cases = await test_design_repository.list_case_versions(
        {"project_id": requirement_version["project_id"], "requirement_version_ids": requirement_version["_id"], "status": "ACTIVE"},
        None,
    )
    result = []
    for source in await _sources(requirement_version):
        mapped = [case for case in cases if _case_mapping(source, case)]
        eligible = [case for case in mapped if _case_has_assurance_evidence(case)]
        result.append({
            **source,
            "test_case_versions": [
                {
                    "id": case["_id"],
                    "key": case.get("test_case_key"),
                    "title": case.get("title"),
                    "requirement_version_ids": case.get("requirement_version_ids", []),
                    "acceptance_criterion_ids": case.get("acceptance_criterion_ids", []),
                    "techniques": case.get("techniques", []),
                    "evidence_refs": case.get("evidence_refs", []),
                    "evidence_quotes": case.get("evidence_quotes", []),
                    "challenge_hypotheses": case.get("challenge_hypotheses", []),
                    "assurance_evidence_complete": _case_has_assurance_evidence(case),
                }
                for case in mapped
            ],
            "status": "COVERED_PENDING_REVIEW" if eligible else "UNASSESSED",
            "owner_id": (eligible[0].get("owner_id") if eligible else requirement_version.get("owner_id")),
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
            item["owner_id"] = prior.get("owner_id") or item.get("owner_id")
        elif prior:
            item["execution_feedback"] = prior.get("execution_feedback", [])
    return items


def _as_datetime(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _waiver_active(item, timestamp):
    if item.get("status") != "WAIVED":
        return False
    decision = item.get("decision") or {}
    expires_at = _as_datetime(decision.get("waiver_expires_at"))
    review_at = _as_datetime(decision.get("waiver_review_at"))
    decided_at = _as_datetime(decision.get("decided_at"))
    owner_id = decision.get("waiver_owner_id")
    return bool(
        expires_at
        and expires_at > timestamp
        and review_at
        and review_at <= expires_at
        and decided_at
        and decision.get("decided_by")
        and str(decision.get("reason") or "").strip()
        and owner_id
        and owner_id == item.get("owner_id")
    )


def coverage_item_ready_for_assurance(item, timestamp):
    """Require source-backed evidence or an auditable QA decision for every item."""
    if not all(
        str(item.get(field) or "").strip()
        for field in (
            "coverage_item_id",
            "requirement_version_id",
            "source_type",
            "source_id",
            "source_ref",
            "source_quote",
        )
    ):
        return False
    status = item.get("status")
    if status == "WAIVED":
        return _waiver_active(item, timestamp)
    if status == "NOT_APPLICABLE":
        decision = item.get("decision") or {}
        return bool(
            str(decision.get("reason") or "").strip()
            and decision.get("decided_by")
            and _as_datetime(decision.get("decided_at"))
        )
    if status in {"COVERED_PENDING_REVIEW", "VERIFIED_COVERED"}:
        return any(
            _case_proves_coverage_item(case, item)
            for case in item.get("test_case_versions", [])
            if isinstance(case, dict)
        )
    return False


def _case_proves_coverage_item(case, item):
    requirement_version_id = item.get("requirement_version_id")
    source_type = item.get("source_type")
    source_id = str(item.get("source_id") or "")
    source_quote = " ".join(str(item.get("source_quote") or "").split())
    requirement_ids = set(case.get("requirement_version_ids") or [])
    criterion_ids = set(case.get("acceptance_criterion_ids") or [])
    references = set(case.get("evidence_refs") or [])
    if (
        case.get("assurance_evidence_complete") is not True
        or not requirement_version_id
        or requirement_version_id not in requirement_ids
        or not case.get("techniques")
        or not references
    ):
        return False
    if source_type == "acceptance_criterion" and source_id not in criterion_ids:
        return False
    if source_type != "acceptance_criterion" and requirement_version_id not in references:
        return False
    for evidence in case.get("evidence_quotes") or []:
        if not isinstance(evidence, dict):
            continue
        evidence_ref = str(evidence.get("evidence_ref") or "")
        quote = " ".join(str(evidence.get("quote") or "").split())
        if (
            evidence_ref in references
            and (evidence_ref == requirement_version_id or evidence_ref == source_id)
            and quote
            and (source_quote in quote or quote in source_quote)
        ):
            return True
    return False


def _summary(items, timestamp):
    verified = sum(item.get("status") == "VERIFIED_COVERED" for item in items)
    not_applicable = sum(item.get("status") == "NOT_APPLICABLE" for item in items)
    conditional = sum(_waiver_active(item, timestamp) for item in items)
    expired = sum(item.get("status") == "WAIVED" and not _waiver_active(item, timestamp) for item in items)
    outstanding = len(items) - verified - not_applicable - conditional
    return {
        "total": len(items),
        "verified": verified,
        "not_applicable": not_applicable,
        "conditional": conditional,
        "expired_waivers": expired,
        "outstanding": outstanding,
    }


def assessment_status_for_list(assessment):
    if not assessment:
        return "NEEDS_TEST_COVERAGE"
    if assessment.get("status") == "SUPERSEDED":
        return "SUPERSEDED"
    if any(
        item.get("status") == "WAIVED" and not _waiver_active(item, now())
        for item in assessment.get("coverage_items", [])
    ):
        return "NEEDS_TEST_COVERAGE"
    return assessment.get("status") or "NEEDS_TEST_COVERAGE"


async def _reconcile_expired_waivers(assessment):
    timestamp = now()
    expired_ids = [
        item["coverage_item_id"]
        for item in assessment.get("coverage_items", [])
        if item.get("status") == "WAIVED" and not _waiver_active(item, timestamp)
    ]
    if not expired_ids:
        return assessment
    items = []
    for item in assessment["coverage_items"]:
        value = dict(item)
        if value["coverage_item_id"] in expired_ids:
            value["decision"] = {**value.get("decision", {}), "waiver_expired_at": timestamp}
        items.append(value)
    updated = await test_adequacy_repository.replace(
        assessment["_id"],
        assessment["project_id"],
        assessment["revision"],
        {
            "coverage_items": items,
            "coverage_summary": _summary(items, timestamp),
            "status": "DRAFT",
            "updated_at": timestamp,
        },
    )
    return updated or await test_adequacy_repository.find(
        assessment["project_id"], assessment["requirement_version_id"]
    )


async def get_adequacy_assessment(requirement_version_id, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "testcase.read")
    assessment = await test_adequacy_repository.find(version["project_id"], requirement_version_id)
    if assessment:
        return await _reconcile_expired_waivers(assessment)
    return await refresh_adequacy_assessment(requirement_version_id, user, None)


async def refresh_adequacy_assessment(requirement_version_id, user, expected_revision):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "testcase.read")
    await get_project(version["project_id"], user, "testcase.read")
    existing = await test_adequacy_repository.find(version["project_id"], requirement_version_id)
    if existing and expected_revision is not None and existing["revision"] != expected_revision:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "current_revision": existing["revision"]})
    items = _merge_decisions(await _snapshot(version), existing)
    timestamp = now()
    value = {
        "requirement_id": version["requirement_id"],
        "requirement_version_id": version["_id"],
        "requirement_revision": version["revision"],
        "requirement_snapshot": {"title": version["title"], "status": version["status"], "revision": version["revision"]},
        "coverage_items": items,
        "coverage_summary": _summary(items, timestamp),
        "status": "DRAFT",
        "updated_at": timestamp,
    }
    if not existing:
        assessment = {
            "_id": new_id("ADA"), "project_id": version["project_id"], "revision": 1,
            "created_by": user.id, "created_at": timestamp, **value,
        }
        async def create(session):
            await test_adequacy_repository.insert(assessment, session=session)
            await audit(
                user.id,
                "test_adequacy_assessment_refreshed",
                "TestAdequacyAssessment",
                assessment["_id"],
                version["project_id"],
                {"requirement_version_id": version["_id"]},
                session=session,
            )
            return assessment

        try:
            async with await database.client.start_session() as session:
                assessment = await session.with_transaction(create)
        except DuplicateKeyError as error:
            raise HTTPException(
                status_code=409,
                detail={"code": "ADEQUACY_ASSESSMENT_CREATED_CONCURRENTLY"},
            ) from error
    else:
        assessment = await _replace_assessment_with_audit(
            existing["_id"],
            version["project_id"],
            existing["revision"],
            value,
            user,
            "test_adequacy_assessment_refreshed",
            details={"requirement_version_id": version["_id"]},
            expected_status=existing.get("status"),
        )
    return assessment


async def supersede_requirement_assessments(
    project_id, requirement_id, requirement_version_id, user_id, session=None
):
    timestamp = now()
    await test_adequacy_repository.supersede_for_requirement(
        project_id, requirement_id, requirement_version_id, timestamp, session=session
    )


async def invalidate_adequacy_for_test_case_version(version):
    await test_adequacy_repository.invalidate_for_requirement_versions(
        version["project_id"],
        version.get("requirement_version_ids", []),
        now(),
        version["_id"],
    )


async def submit_adequacy_assessment(assessment_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.submit_review")
    if assessment["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    value = {"status": "IN_REVIEW", "review_note": payload.note, "review_submitted_by": user.id, "review_submitted_at": now(), "updated_at": now()}
    return await _replace_assessment_with_audit(
        assessment_id, assessment["project_id"], payload.expected_revision, value,
        user, "test_adequacy_review_submitted",
        expected_status="DRAFT",
    )


async def approve_adequacy_assessment(assessment_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.review")
    assessment = await _reconcile_expired_waivers(assessment)
    await _require_qa(assessment["project_id"], user)
    if assessment["status"] != "IN_REVIEW":
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    timestamp = now()
    if not assessment.get("coverage_items"):
        raise HTTPException(status_code=409, detail={"code": "ADEQUACY_NO_COVERAGE_ITEMS"})
    unresolved = [
        item.get("coverage_item_id") or "UNKNOWN_COVERAGE_ITEM"
        for item in assessment["coverage_items"]
        if not coverage_item_ready_for_assurance(item, timestamp)
    ]
    if unresolved:
        raise HTTPException(status_code=409, detail={"code": "ADEQUACY_UNRESOLVED_ITEMS", "coverage_item_ids": unresolved})
    items = []
    for item in assessment["coverage_items"]:
        item = dict(item)
        if item["status"] == "COVERED_PENDING_REVIEW":
            item["status"] = "VERIFIED_COVERED"
        items.append(item)
    summary = _summary(items, timestamp)
    value = {
        "coverage_items": items,
        "coverage_summary": summary,
        "status": "CONDITIONAL" if summary["conditional"] else "ASSURED",
        "approved_by": user.id,
        "approved_at": timestamp,
        "review_note": payload.note,
        "updated_at": timestamp,
    }

    async def validate_clarifications_in_transaction(session):
        if not await requirement_repository.bump_clarification_gate_revision(
            assessment["requirement_version_id"],
            assessment["project_id"],
            session=session,
        ):
            raise HTTPException(status_code=409, detail={"code": "REQUIREMENT_VERSION_CHANGED"})
        open_items = await requirement_clarification_repository.list_open_for_version(
            assessment["project_id"],
            assessment["requirement_version_id"],
            session=session,
        )
        if open_items:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ADEQUACY_OPEN_CLARIFICATIONS",
                    "clarification_ids": [item["_id"] for item in open_items],
                },
            )

    return await _replace_assessment_with_audit(
        assessment_id, assessment["project_id"], payload.expected_revision, value,
        user, "test_adequacy_assessment_approved",
        expected_status="IN_REVIEW",
        before_replace=validate_clarifications_in_transaction,
    )


async def request_adequacy_changes(assessment_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.review")
    await _require_qa(assessment["project_id"], user)
    if assessment["status"] != "IN_REVIEW":
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    value = {"status": "DRAFT", "review_note": payload.note, "changes_requested_by": user.id, "changes_requested_at": now(), "updated_at": now()}
    return await _replace_assessment_with_audit(
        assessment_id, assessment["project_id"], payload.expected_revision, value,
        user, "test_adequacy_changes_requested",
        expected_status="IN_REVIEW",
    )


async def decide_coverage_item(assessment_id, coverage_item_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.read")
    await _require_qa(assessment["project_id"], user)
    waiver_owner_id = None
    if payload.status == "MISSING_INFORMATION":
        clarification = await requirement_clarification_repository.find(
            payload.clarification_id, assessment["project_id"]
        )
        if (
            not clarification
            or clarification.get("requirement_version_id") != assessment["requirement_version_id"]
            or clarification.get("coverage_item_id") != coverage_item_id
            or clarification.get("status") not in {"OPEN", "ANSWERED"}
        ):
            raise HTTPException(status_code=422, detail={"code": "CLARIFICATION_NOT_ACTIVE_FOR_COVERAGE_ITEM"})
    if payload.status == "WAIVED":
        timestamp = now()
        if payload.waiver_review_at < timestamp or payload.waiver_expires_at <= timestamp:
            raise HTTPException(status_code=422, detail={"code": "WAIVER_SCHEDULE_INVALID"})
        waiver_owner_id = await resolve_user_reference(payload.waiver_owner_id)
        membership = await project_repository.find_member(
            assessment["project_id"], waiver_owner_id, status="ACTIVE"
        )
        if not membership:
            raise HTTPException(status_code=422, detail={"code": "WAIVER_OWNER_NOT_PROJECT_MEMBER"})
    items = []
    found = False
    for item in assessment["coverage_items"]:
        item = dict(item)
        if item["coverage_item_id"] == coverage_item_id:
            found = True
            item["status"] = payload.status
            item["owner_id"] = waiver_owner_id or item.get("owner_id")
            item["decision"] = {
                "reason": payload.reason,
                "decided_by": user.id,
                "decided_at": now(),
                **(
                    {"clarification_id": payload.clarification_id}
                    if payload.status == "MISSING_INFORMATION"
                    else {}
                ),
                **(
                    {
                        "waiver_owner_id": waiver_owner_id,
                        "waiver_expires_at": payload.waiver_expires_at,
                        "waiver_review_at": payload.waiver_review_at,
                    }
                    if payload.status == "WAIVED"
                    else {}
                ),
            }
        items.append(item)
    if not found:
        raise HTTPException(status_code=404, detail={"code": "COVERAGE_ITEM_NOT_FOUND"})
    timestamp = now()
    value = {"coverage_items": items, "coverage_summary": _summary(items, timestamp), "status": "DRAFT", "updated_at": timestamp}
    return await _replace_assessment_with_audit(
        assessment_id, assessment["project_id"], payload.expected_revision, value,
        user, "test_adequacy_coverage_decided", "CoverageItem", coverage_item_id,
        {"status": payload.status},
        expected_status=assessment.get("status"),
    )


async def add_execution_feedback(assessment_id, coverage_item_id, payload, user):
    assessment = await get_project_entity("test_adequacy_assessments", assessment_id, user, "testcase.read")
    await _require_qa(
        assessment["project_id"],
        user,
        allow_execution_feedback_automation=True,
    )
    case = await test_design_repository.find_case_version(payload.test_case_version_id, assessment["project_id"])
    if not case:
        raise HTTPException(status_code=422, detail={"code": "TEST_CASE_VERSION_NOT_FOUND"})
    if payload.test_result_id:
        results = await test_design_repository.list_case_results(assessment["project_id"], [case["_id"]])
        if payload.test_result_id not in {item["_id"] for item in results}:
            raise HTTPException(status_code=422, detail={"code": "TEST_RESULT_NOT_LINKED"})
        if payload.test_result_revision is not None and not any(
            item["_id"] == payload.test_result_id
            and item.get("revision") == payload.test_result_revision
            for item in results
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "TEST_RESULT_EVENT_SUPERSEDED"},
            )
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
            feedback.append({"test_case_version_id": case["_id"], "outcome": payload.outcome, "test_result_id": payload.test_result_id, "test_result_revision": payload.test_result_revision, "defect_id": payload.defect_id, "note": payload.note, "recorded_by": user.id, "recorded_at": now()})
            item["execution_feedback"] = feedback
        items.append(item)
    if not found:
        raise HTTPException(status_code=404, detail={"code": "COVERAGE_ITEM_NOT_FOUND"})
    value = {"coverage_items": items, "status": "DRAFT", "updated_at": now()}
    return await _replace_assessment_with_audit(
        assessment_id, assessment["project_id"], payload.expected_revision, value,
        user, "test_adequacy_execution_feedback_recorded", "CoverageItem",
        coverage_item_id, {"outcome": payload.outcome},
        expected_status=assessment.get("status"),
    )


async def adequacy_change_impact(requirement_id, user):
    requirement = await get_project_entity("requirements", requirement_id, user, "testcase.read")
    assessments = await test_adequacy_repository.list_for_requirement(requirement["project_id"], requirement_id)
    version_ids = [item["requirement_version_id"] for item in assessments]
    versions = await test_design_repository.list_case_versions(
        {"project_id": requirement["project_id"], "requirement_version_ids": {"$in": version_ids}, "status": "ACTIVE"}, None
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
