from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now, require_action_policy
from src.repositories.test_design import test_design_repository
from src.modules.design.services.linters import has_verifiable_steps, lint_test_case
from src.clients.project_knowledge import index_artifact
from src.modules.design.services.test_case_records import project_test_text




async def lint_test_case_draft_record(draft_id, user, project_id=None):
    draft = await get_project_entity('test_case_drafts', draft_id, user, 'testcase.lint')
    await get_project(draft["project_id"], user, 'ai.run_lint')
    if project_id is not None and draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    findings = lint_test_case(draft)
    result = {
        "test_case_draft_id": draft_id,
        "findings": findings,
        "valid": not any(
            item["severity"] == 'error'
            for item in findings
        ),
        "model": {
            "provider": 'deterministic',
            "model": 'test_case_quality',
            "prompt_version": 'ai_assistance',
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
            **result,
            "created_at": now(),
        }
    )
    return result


async def submit_test_case_review_record(project_id, draft_id, payload, user):
    draft = await get_project_entity('test_case_drafts', draft_id, user, 'testcase.submit_review')
    if draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if draft["status"] == 'IN_REVIEW':
        return draft
    if draft["status"] != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    if draft["revision"] != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_revision": draft["revision"]},
        )
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
    claimed = await claim_test_case_draft(draft, payload, user)
    if not claimed:
        current = await test_design_repository.find_case_draft(
            draft_id, draft["project_id"]
        )
        if (
            current
            and current.get("status") == 'APPROVED'
            and current.get("frozen_version_id")
        ):
            return await approved_test_case_result(current, user)
        raise HTTPException(status_code=409, detail={"code": 'TEST_CASE_APPROVAL_IN_PROGRESS'})
    test_case, version = await persist_test_case_version(claimed, payload, user)
    ready = await finalize_test_case_derivatives(claimed, version, user)
    return {
        "data": {"test_case": {**test_case, "current_version_id": version["_id"]}, "version": version},
        "status": 'SUCCESS' if ready else 'DEGRADED',
        "degraded_mode": None if ready else 'DEGRADED_DERIVED_DATA',
    }


async def claim_test_case_draft(draft, payload, user):
    timestamp = now()
    return await test_design_repository.claim_case_draft(
        draft["_id"],
        draft["project_id"],
        payload.expected_revision,
        'IN_REVIEW',
        'APPROVING',
        {
            "approval_started_by": user.id,
            "approval_started_at": timestamp,
            "updated_at": timestamp,
        },
    )


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
        field in version for field in ("trace_status", "approval_audit_status")
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
            await audit(
                user.id,
                'test_case_version_approved',
                'TestCaseVersion',
                version["_id"],
                version["project_id"],
                {"draft_id": draft["_id"]},
            )
            audit_ready = True
        except Exception:
            audit_ready = False
    derived_status = {
        "index_status": 'INDEXED' if indexed else 'FAILED',
        "index_error_code": None if indexed else 'KNOWLEDGE_INDEX_FAILED',
        "indexed_at": version.get("indexed_at") or (now() if indexed else None),
        "trace_status": 'READY' if trace_ready else 'FAILED',
        "trace_error_code": None if trace_ready else 'TRACE_LINK_CREATION_FAILED',
        "approval_audit_status": 'READY' if audit_ready else 'FAILED',
        "approval_audit_error_code": None if audit_ready else 'APPROVAL_AUDIT_FAILED',
    }
    try:
        await test_design_repository.set_case_version_approval_result(
            version["_id"],
            version["project_id"],
            derived_status["index_status"],
            derived_status["index_error_code"],
            derived_status["indexed_at"],
            derived_status["trace_status"],
            derived_status["trace_error_code"],
            derived_status["approval_audit_status"],
            derived_status["approval_audit_error_code"],
        )
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
            }
        )
    version.update(derived_status)
    try:
        from src.modules.design.services.test_adequacy import invalidate_adequacy_for_test_case_version
        await invalidate_adequacy_for_test_case_version(version)
    except Exception:
        pass
    return trace_ready and indexed and audit_ready


async def persist_test_case_version(draft, payload, user):
    timestamp = now()
    test_case = None
    version = None
    parent_version_id = None
    created_test_case = False
    try:
        existing = await test_design_repository.find_case_by_key(
            draft["project_id"], draft["test_case_key"]
        )
        if existing:
            latest = await test_design_repository.find_latest_case_version(existing["_id"])
            if not latest or latest["_id"] != existing.get("current_version_id"):
                raise HTTPException(status_code=409, detail={"code": 'TEST_CASE_VERSION_HISTORY_INVALID'})
            if draft.get("parent_version_id") != latest["_id"]:
                raise HTTPException(status_code=409, detail={"code": "TEST_CASE_BASE_VERSION_CHANGED"})
            test_case = existing
            version_number = int(latest["version"]) + 1
            parent_version_id = latest["_id"]
        else:
            if draft.get("parent_version_id"):
                raise HTTPException(status_code=409, detail={"code": "TEST_CASE_PARENT_VERSION_CHANGED"})
            test_case = {
                "_id": new_id('TC'),
                "project_id": draft["project_id"],
                "test_case_key": draft["test_case_key"],
                "current_version_id": None,
                "status": 'ACTIVE',
                "owner_id": draft.get("owner_id") or draft.get("created_by"),
                "tags": draft.get("tags", []),
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            await test_design_repository.insert_case(test_case)
            created_test_case = True
            version_number = 1
        version = build_test_case_version(
            draft, test_case["_id"], version_number, parent_version_id, payload, user, timestamp
        )
        await test_design_repository.insert_case_version(version)
        updated_case = await test_design_repository.activate_case_version(
            test_case["_id"],
            draft["project_id"],
            parent_version_id,
            version["_id"],
            'ACTIVE',
            timestamp,
        )
        if not updated_case:
            raise HTTPException(status_code=409, detail={"code": 'TEST_CASE_VERSION_CONFLICT'})
        updated_draft = await test_design_repository.approve_case_draft(
            draft["_id"],
            draft["project_id"],
            draft["revision"],
            'APPROVING',
            'APPROVED',
            version["_id"],
            timestamp,
        )
        if not updated_draft:
            raise HTTPException(status_code=409, detail={"code": 'TEST_CASE_APPROVAL_CONFLICT'})
        return test_case, version
    except Exception:
        await rollback_test_case_version(draft, test_case, version, parent_version_id, created_test_case)
        raise


def build_test_case_version(draft, test_case_id, version_number, parent_version_id, payload, user, timestamp):
    return {
        "_id": new_id('TCV'),
        "project_id": draft["project_id"],
        "test_case_id": test_case_id,
        "test_case_key": draft["test_case_key"],
        "version": version_number,
        "title": draft["title"],
        "type": draft["type"],
        "priority": draft["priority"],
        "risk": draft["risk"],
        "objective_doc": draft.get("objective_doc", {"type": "doc", "content": []}),
        "preconditions_doc": draft["preconditions_doc"],
        "steps": draft["steps"],
        "test_data": draft["test_data"],
        "expected_result_doc": draft["expected_result_doc"],
        "postconditions_doc": draft["postconditions_doc"],
        "tags": draft["tags"],
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
        "source_evidence": (
            draft.get("source_evidence", [])
            if draft.get("origin") != "ai_generated" or draft.get("evidence_refs")
            else []
        ),
        "coverage_obligations": draft.get("coverage_obligations", []),
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
        "approved_by": user.id,
        "created_at": timestamp,
    }


async def rollback_test_case_version(draft, test_case, version, parent_version_id, created_test_case):
    if version:
        await test_design_repository.delete_case_version(version["_id"], draft["project_id"])
    if test_case and created_test_case:
        await test_design_repository.delete_unactivated_case(
            test_case["_id"],
            draft["project_id"],
            [None, version["_id"] if version else None],
        )
    elif test_case and version:
        await test_design_repository.restore_case_version(
            test_case["_id"],
            draft["project_id"],
            version["_id"],
            parent_version_id,
            now(),
        )
    await test_design_repository.reset_case_draft(
        draft["_id"],
        draft["project_id"],
        'APPROVING',
        'IN_REVIEW',
        now(),
    )


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
