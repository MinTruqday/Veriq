import hashlib

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from src.core.human_decisions import require_automation_publication_authority

from src.core.common import audit, get_project, get_project_entity, new_id, now, require_action_policy
from src.core.database import database
from src.repositories.test_design import test_design_repository
from src.modules.design.services.linters import has_verifiable_steps, lint_test_case
from src.clients.project_knowledge import index_artifact
from src.modules.design.services.test_case_records import project_test_text
from src.modules.design.services.test_case_custom_fields import validate_test_case_custom_values




async def lint_test_case_draft_record(draft_id, user, project_id=None):
    draft = await get_project_entity('test_case_drafts', draft_id, user, 'testcase.lint')
    await get_project(draft["project_id"], user, 'ai.run_lint')
    if project_id is not None and draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    findings = lint_test_case(draft)
    result = {
        "test_case_draft_id": draft_id,
        "artifact_revision": draft.get("revision"),
        "source_hash": hashlib.sha256(project_test_text(draft).encode("utf-8")).hexdigest(),
        "findings": findings,
        "valid": not any(
            item["severity"] == 'error'
            for item in findings
        ),
        "model": {
            "provider": 'deterministic',
            "model": 'test_case_quality',
            "prompt_version": 'ai_automation',
            "tool_schema_version": '1',
            "retrieval_version": 'project_evidence',
        },
    }
    await test_design_repository.insert_ai_finding(
        {
            "_id": new_id('AIF'),
            "project_id": draft["project_id"],
            "artifact_type": 'test_case_draft',
            "artifact_id": draft_id,
            "result_type": "TEST_CASE_DRAFT_LINT",
            **result,
            "created_at": now(),
        }
    )
    return result


async def get_latest_test_case_draft_lint(draft_id, user):
    draft = await get_project_entity(
        "test_case_drafts", draft_id, user, "testcase.read"
    )
    result = await test_design_repository.find_latest_test_draft_lint(
        draft["project_id"], draft_id
    )
    if not result:
        return None
    return {
        **result,
        "is_stale": result.get("artifact_revision") != draft.get("revision"),
    }


async def submit_test_case_review_record(project_id, draft_id, payload, user):
    draft = await get_project_entity('test_case_drafts', draft_id, user, 'testcase.submit_review')
    if draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if draft["status"] == 'IN_REVIEW':
        return draft
    if draft["status"] != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    await validate_test_case_custom_values(
        project_id, draft.get("custom_values", {}), enforce_required=True
    )
    if draft["revision"] != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_revision": draft["revision"]},
        )
    from src.modules.design.services.test_case_review import validate_review_sources_before_approval

    await validate_review_sources_before_approval(draft)
    if draft.get("origin") == "ai_generated" and not draft.get("evidence_refs"):
        raise HTTPException(409, detail={"code": "TEST_CASE_SOURCE_REVIEW_REQUIRED", "message": "Ca đã được sửa; cần đối chiếu lại nguồn trước khi duyệt."})
    if not has_verifiable_steps(draft):
        raise HTTPException(status_code=409, detail={"code": "TEST_CASE_STEPS_REQUIRED", "message": "Cần bổ sung hành động và kết quả mong đợi cho từng bước trước khi gửi duyệt"})
    findings = lint_test_case(draft)
    project_settings = await test_design_repository.find_project_settings(project_id)
    lint_blocking = project_settings.get(
        'testcase_lint_blocking', True
    )
    if lint_blocking and any(
        item["severity"] == 'error' for item in findings
    ):
        raise HTTPException(
            status_code=409, detail={"code": 'TEST_CASE_LINT_BLOCKED', "findings": findings}
        )
    timestamp = now()
    transitioned = await test_design_repository.transition_case_draft(
        draft_id,
        project_id,
        payload.expected_revision,
        'DRAFT',
        'IN_REVIEW',
        {
            "review_note": payload.review_note,
            "review_submitted_by": user.id,
            "review_submitted_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not transitioned:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    draft = await test_design_repository.find_case_draft(draft_id, project_id)
    await audit(
        user.id,
        'test_case_review_submitted',
        'TestCaseDraft',
        draft_id,
        project_id,
        {"review_note": payload.review_note},
    )
    return draft


async def request_test_case_changes_record(project_id, draft_id, payload, user):
    draft = await get_project_entity('test_case_drafts', draft_id, user, 'testcase.review')
    await require_action_policy(draft["project_id"], user, 'testcase.request_changes', set(['QA']))
    if draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if draft["status"] != 'IN_REVIEW':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    if draft["revision"] != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_revision": draft["revision"]},
        )
    timestamp = now()
    transitioned = await test_design_repository.transition_case_draft(
        draft_id,
        project_id,
        payload.expected_revision,
        'IN_REVIEW',
        'DRAFT',
        {
            "review_note": payload.review_note,
            "changes_requested_by": user.id,
            "changes_requested_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not transitioned:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    draft = await test_design_repository.find_case_draft(draft_id, project_id)
    await audit(
        user.id,
        'test_case_changes_requested',
        'TestCaseDraft',
        draft_id,
        project_id,
        {"review_note": payload.review_note},
    )
    return draft


async def approve_test_case_draft_record(draft_id, payload, user):
    require_automation_publication_authority(user, "testcase.approve")
    draft = await get_project_entity('test_case_drafts', draft_id, user, 'testcase.approve')
    if draft["status"] == 'APPROVED' and draft.get(
        "frozen_version_id"
    ):
        return await approved_test_case_result(draft, user)
    if draft["status"] != 'IN_REVIEW':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    if draft["revision"] != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_revision": draft["revision"]},
        )
    if not has_verifiable_steps(draft):
        raise HTTPException(status_code=409, detail={"code": "TEST_CASE_STEPS_REQUIRED", "message": "Cần bổ sung hành động và kết quả mong đợi cho từng bước trước khi phê duyệt"})
    await validate_test_case_custom_values(
        draft["project_id"], draft.get("custom_values", {}), enforce_required=True
    )
    findings = lint_test_case(draft)
    project_settings = await test_design_repository.find_project_settings(draft["project_id"])
    lint_blocking = project_settings.get(
        'testcase_lint_blocking', True
    )
    if lint_blocking and any(
        item["severity"] == 'error' for item in findings
    ):
        raise HTTPException(
            status_code=409, detail={"code": 'TEST_CASE_LINT_BLOCKED', "findings": findings}
        )
    from src.modules.design.services.test_case_review import validate_review_sources_before_approval

    await validate_review_sources_before_approval(draft)
    from src.modules.design.services.test_case_review import review_context

    comparison = await review_context(draft_id, user, "testcase.approve")
    if comparison["duplicates"] and not str(draft.get("duplicate_reason") or "").strip():
        raise HTTPException(
            409,
            detail={
                "code": "TEST_CASE_DUPLICATE_REVIEW_REQUIRED",
                "matches": comparison["duplicates"],
                "message": "Ca này gần trùng với ca đang hiệu lực; QA cần ghi lý do xác nhận vẫn giữ riêng trước khi duyệt.",
            },
        )
    if draft.get("origin") == "ai_generated" and not draft.get("evidence_refs"):
        raise HTTPException(409, detail={"code": "TEST_CASE_SOURCE_REVIEW_REQUIRED", "message": "Ca đã được sửa; cần đối chiếu lại nguồn trước khi duyệt."})
    from src.clients.ai_automation import queue_test_case_approved
    from src.modules.design.services.test_case_review import (
        assert_sources_current_in_session,
        validate_test_case_publication_uniqueness,
    )

    async def publish(session):
        current_draft = await database.value.test_case_drafts.find_one(
            {
                "_id": draft_id,
                "project_id": draft["project_id"],
                "revision": payload.expected_revision,
                "status": "IN_REVIEW",
            },
            session=session,
        )
        if not current_draft:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        await assert_sources_current_in_session(current_draft, session)
        await validate_test_case_custom_values(
            current_draft["project_id"],
            current_draft.get("custom_values", {}),
            enforce_required=True,
            session=session,
        )
        await validate_test_case_publication_uniqueness(
            current_draft,
            project_settings.get("testcase_duplicate_threshold", 0.72),
            session,
        )
        existing = await database.value.test_cases.find_one(
            {
                "project_id": current_draft["project_id"],
                "test_case_key": current_draft["test_case_key"],
            },
            session=session,
        )
        timestamp = now()
        parent_version_id = None
        if existing:
            latest = await database.value.test_case_versions.find_one(
                {"test_case_id": existing["_id"]},
                sort=[("version", -1)],
                session=session,
            )
            if not latest or latest["_id"] != existing.get("current_version_id"):
                raise HTTPException(status_code=409, detail={"code": "TEST_CASE_VERSION_HISTORY_INVALID"})
            if current_draft.get("parent_version_id") != latest["_id"]:
                raise HTTPException(status_code=409, detail={"code": "TEST_CASE_BASE_VERSION_CHANGED"})
            test_case = existing
            version_number = int(latest["version"]) + 1
            parent_version_id = latest["_id"]
        else:
            if current_draft.get("parent_version_id"):
                raise HTTPException(status_code=409, detail={"code": "TEST_CASE_PARENT_VERSION_CHANGED"})
            test_case = {
                "_id": new_id("TC"),
                "project_id": current_draft["project_id"],
                "test_case_key": current_draft["test_case_key"],
                "current_version_id": None,
                "status": "ACTIVE",
                "owner_id": current_draft.get("owner_id") or current_draft.get("created_by"),
                "tags": current_draft.get("tags", []),
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            await database.value.test_cases.insert_one(test_case, session=session)
            version_number = 1

        version = build_test_case_version(
            current_draft,
            test_case["_id"],
            version_number,
            parent_version_id,
            payload,
            user,
            timestamp,
        )
        version["approval_audit_status"] = "READY"
        await database.value.test_case_versions.insert_one(version, session=session)
        activated = await database.value.test_cases.update_one(
            {
                "_id": test_case["_id"],
                "project_id": current_draft["project_id"],
                "current_version_id": parent_version_id,
            },
            {"$set": {"current_version_id": version["_id"], "status": "ACTIVE", "updated_at": timestamp}},
            session=session,
        )
        if activated.matched_count != 1:
            raise HTTPException(status_code=409, detail={"code": "TEST_CASE_VERSION_CONFLICT"})
        transitioned = await database.value.test_case_drafts.update_one(
            {
                "_id": draft_id,
                "project_id": current_draft["project_id"],
                "revision": payload.expected_revision,
                "status": "IN_REVIEW",
            },
            {
                "$set": {
                    "status": "APPROVED",
                    "frozen_version_id": version["_id"],
                    "approved_by": user.id,
                    "approved_at": timestamp,
                    "updated_at": timestamp,
                },
                "$inc": {"revision": 1},
            },
            session=session,
        )
        if transitioned.matched_count != 1:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        await audit(
            user.id,
            "test_case_version_approved",
            "TestCaseVersion",
            version["_id"],
            version["project_id"],
            {"draft_id": draft_id},
            session=session,
        )
        await queue_test_case_approved(version, user, session)
        return test_case, version

    try:
        async with await database.client.start_session() as session:
            test_case, version = await session.with_transaction(publish)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail={"code": "TEST_CASE_VERSION_CONFLICT"}) from error

    ready = await finalize_test_case_derivatives(draft, version, user)
    return {
        "data": {"test_case": {**test_case, "current_version_id": version["_id"]}, "version": version},
        "status": 'SUCCESS' if ready else 'DEGRADED',
        "degraded_mode": None if ready else 'DEGRADED_DERIVED_DATA',
    }


async def approved_test_case_result(draft, user):
    version = await test_design_repository.find_case_version(
        draft["frozen_version_id"], draft["project_id"]
    )
    if not version:
        raise HTTPException(status_code=409, detail={"code": 'TEST_CASE_APPROVAL_INCOMPLETE'})
    test_case = await test_design_repository.find_case(
        version["test_case_id"], draft["project_id"]
    )
    if not test_case:
        raise HTTPException(status_code=409, detail={"code": 'TEST_CASE_APPROVAL_INCOMPLETE'})
    tracks_approval_derivatives = any(
        field in version
        for field in (
            "trace_status",
            "approval_audit_status",
            "adequacy_invalidation_status",
        )
    )
    ready = (
        await finalize_test_case_derivatives(draft, version, user)
        if tracks_approval_derivatives
        else version.get("index_status") == 'INDEXED'
    )
    return {
        "data": {"test_case": test_case, "version": version},
        "status": 'SUCCESS' if ready else 'DEGRADED',
        "degraded_mode": None if ready else 'DEGRADED_DERIVED_DATA',
    }


async def finalize_test_case_derivatives(draft, version, user):
    trace_ready = version.get("trace_status") == 'READY'
    if not trace_ready:
        try:
            await create_suggested_trace_records(draft, version, user)
            trace_ready = True
        except Exception:
            trace_ready = False
    indexed = version.get("index_status") == 'INDEXED'
    if not indexed:
        try:
            indexed = await index_artifact(
                version["project_id"],
                'test_case_version',
                version["test_case_id"],
                version["_id"],
                version["title"],
                version["plain_text_projection"],
                version["status"],
                'APPROVED_SOURCE',
                version["version"],
                requirement_version_ids=version.get("requirement_version_ids", []),
                acceptance_criterion_ids=version.get("acceptance_criterion_ids", []),
            )
        except Exception:
            indexed = False
    audit_ready = version.get("approval_audit_status") == 'READY'
    if not audit_ready:
        try:
            event_id = f"AUD-TC-APPROVAL-{version['_id']}"
            try:
                await audit(
                    user.id,
                    'test_case_version_approved',
                    'TestCaseVersion',
                    version["_id"],
                    version["project_id"],
                    {"draft_id": draft["_id"]},
                    event_id=event_id,
                )
            except DuplicateKeyError:
                existing_event = await database.value.audit_events.find_one(
                    {"_id": event_id}
                )
                if (
                    not existing_event
                    or existing_event.get("actor_id") != user.id
                    or existing_event.get("project_id") != version["project_id"]
                    or existing_event.get("action") != 'test_case_version_approved'
                    or existing_event.get("entity_type") != 'TestCaseVersion'
                    or existing_event.get("entity_id") != version["_id"]
                    or (existing_event.get("details") or {}).get("draft_id") != draft["_id"]
                ):
                    raise
            audit_ready = True
        except Exception:
            audit_ready = False
    adequacy_ready = version.get("adequacy_invalidation_status") == 'READY'
    if not adequacy_ready:
        try:
            from src.modules.design.services.test_adequacy import invalidate_adequacy_for_test_case_version

            await invalidate_adequacy_for_test_case_version(version)
            adequacy_ready = True
        except Exception:
            adequacy_ready = False
    derived_status = {
        "index_status": 'INDEXED' if indexed else 'FAILED',
        "index_error_code": None if indexed else 'KNOWLEDGE_INDEX_FAILED',
        "indexed_at": version.get("indexed_at") or (now() if indexed else None),
        "trace_status": 'READY' if trace_ready else 'FAILED',
        "trace_error_code": None if trace_ready else 'TRACE_LINK_CREATION_FAILED',
        "approval_audit_status": 'READY' if audit_ready else 'FAILED',
        "approval_audit_error_code": None if audit_ready else 'APPROVAL_AUDIT_FAILED',
        "adequacy_invalidation_status": 'READY' if adequacy_ready else 'FAILED',
        "adequacy_invalidation_error_code": None if adequacy_ready else 'ADEQUACY_INVALIDATION_FAILED',
    }
    try:
        persisted = await test_design_repository.set_case_version_approval_result(
            version["_id"],
            version["project_id"],
            derived_status["index_status"],
            derived_status["index_error_code"],
            derived_status["indexed_at"],
            derived_status["trace_status"],
            derived_status["trace_error_code"],
            derived_status["approval_audit_status"],
            derived_status["approval_audit_error_code"],
            derived_status["adequacy_invalidation_status"],
            derived_status["adequacy_invalidation_error_code"],
        )
        if getattr(persisted, "matched_count", 0) != 1:
            raise RuntimeError("APPROVAL_STATUS_PERSIST_FAILED")
    except Exception:
        indexed = False
        trace_ready = False
        audit_ready = False
        derived_status.update(
            {
                "index_status": 'FAILED',
                "index_error_code": 'APPROVAL_STATUS_PERSIST_FAILED',
                "indexed_at": None,
                "trace_status": 'FAILED',
                "trace_error_code": 'APPROVAL_STATUS_PERSIST_FAILED',
                "approval_audit_status": 'FAILED',
                "approval_audit_error_code": 'APPROVAL_STATUS_PERSIST_FAILED',
                "adequacy_invalidation_status": 'FAILED',
                "adequacy_invalidation_error_code": 'APPROVAL_STATUS_PERSIST_FAILED',
            }
        )
    version.update(derived_status)
    return trace_ready and indexed and audit_ready and adequacy_ready


def build_test_case_version(draft, test_case_id, version_number, parent_version_id, payload, user, timestamp):
    return {
        "_id": new_id('TCV'),
        "project_id": draft["project_id"],
        "test_case_id": test_case_id,
        "test_case_key": draft["test_case_key"],
        "version": version_number,
        "title": draft["title"],
        "type": draft["type"],
        "test_level": draft.get("test_level"),
        "test_kind": draft.get("test_kind"),
        "expected_impact": draft.get("expected_impact", "unassessed"),
        "assessment_reason": draft.get("assessment_reason", ""),
        "priority": draft["priority"],
        "risk": draft["risk"],
        "objective_doc": draft.get("objective_doc", {"type": "doc", "content": []}),
        "preconditions_doc": draft["preconditions_doc"],
        "steps": draft["steps"],
        "test_data": draft["test_data"],
        "expected_result_doc": draft["expected_result_doc"],
        "postconditions_doc": draft["postconditions_doc"],
        "tags": draft["tags"],
        "required_skills": draft.get("required_skills", []),
        "custom_values": draft.get("custom_values", {}),
        "owner_id": draft.get("owner_id") or draft.get("created_by"),
        "techniques": draft.get("techniques", []),
        "automation_status": draft["automation_status"],
        "attachments": draft.get("attachments", []),
        "data_set_version_ids": draft.get("data_set_version_ids", []),
        "requirement_version_ids": draft["requirement_version_ids"],
        "acceptance_criterion_ids": draft["acceptance_criterion_ids"],
        "coverage_item_ids": draft.get("coverage_item_ids", []),
        "test_condition_ids": draft.get("test_condition_ids", []),
        "scenario_id": draft.get("scenario_id"),
        "repository_node_id": draft.get("repository_node_id"),
        "bdd": draft.get("bdd"),
        "ai_proposal_snapshot": draft.get("ai_proposal_snapshot"),
        "review_acceptance_criteria_snapshot_ids": draft.get("review_acceptance_criteria_snapshot_ids"),
        "merge_decision_ids": draft.get("merge_decision_ids", []),
        "source_evidence": (
            draft.get("source_evidence", [])
            if draft.get("origin") != "ai_generated" or draft.get("evidence_refs")
            else []
        ),
        "coverage_obligations": draft.get("coverage_obligations", []),
        "obligation_evidence": draft.get("obligation_evidence", []),
        "evidence_refs": draft.get("evidence_refs", []),
        "evidence_quotes": draft.get("evidence_quotes", []),
        "challenge_hypotheses": draft.get("challenge_hypotheses", []),
        "plain_text_projection": project_test_text(draft),
        "parent_version_id": parent_version_id,
        "change_reason": draft.get("change_reason") or payload.change_reason,
        "review_note": payload.review_note,
        "status": 'ACTIVE',
        "index_status": 'PENDING',
        "index_error_code": None,
        "indexed_at": None,
        "trace_status": 'PENDING',
        "trace_error_code": None,
        "approval_audit_status": 'PENDING',
        "approval_audit_error_code": None,
        "adequacy_invalidation_status": 'PENDING',
        "adequacy_invalidation_error_code": None,
        "approved_by": user.id,
        "created_at": timestamp,
    }


async def create_suggested_trace_records(draft, version, user):
    sources = [
        ('requirement_version', source_id)
        for source_id in draft.get("requirement_version_ids", [])
    ] + [
        ('acceptance_criterion', source_id)
        for source_id in draft.get("acceptance_criterion_ids", [])
    ]
    for source_type, source_id in sources:
        exists = await test_design_repository.find_trace_link(
            {
                "project_id": draft["project_id"],
                "source_type": source_type,
                "source_id": source_id,
                "target_type": 'test_case_version',
                "target_id": version["_id"],
            }
        )
        if exists:
            continue
        ai_generated = draft.get("origin") == 'ai_generated'
        await test_design_repository.insert_trace_link(
            {
                "_id": new_id('TL'),
                "project_id": draft["project_id"],
                "source_type": source_type,
                "source_id": source_id,
                "target_type": 'test_case_version',
                "target_id": version["_id"],
                "link_type": 'verifies',
                "confidence": 0.9
                if ai_generated
                else 1.0,
                "origin": 'ai_suggested'
                if ai_generated
                else 'manual',
                "status": 'SUGGESTED'
                if ai_generated
                else 'CONFIRMED',
                "revision": 1,
                "evidence": (
                    draft.get("source_evidence", [])
                    if draft.get("origin") != "ai_generated" or draft.get("evidence_refs")
                    else []
                ),
                "created_by": user.id,
                "created_at": now(),
            }
        )
