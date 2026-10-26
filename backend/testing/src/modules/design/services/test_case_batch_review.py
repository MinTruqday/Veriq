from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import get_project, new_id, now
from src.core.database import database
from src.core.human_decisions import require_automation_publication_authority
from src.clients.ai_automation import queue_test_case_approved
from src.modules.design.services.linters import duplicate_score, has_verifiable_steps, lint_test_case
from src.modules.design.services.test_case_custom_fields import validate_test_case_custom_values
from src.modules.design.services.test_case_lifecycle import build_test_case_version, finalize_test_case_derivatives
from src.modules.design.services.test_case_review import (
    assert_sources_current_in_session,
    fingerprint,
    review_context,
    validate_review_sources_before_approval,
    validate_test_case_publication_uniqueness,
)
from src.repositories.test_design import test_design_repository
from src.schemas.contracts.design import TestCaseFreezeInput


async def accept_test_case_group(project_id, payload, user):
    require_automation_publication_authority(user)
    await get_project(project_id, user, "testcase.approve")
    batch_id = "TCBATCH-" + fingerprint([project_id, payload.operation_id])
    body_hash = fingerprint(payload.model_dump())
    existing = await database.value.audit_events.find_one({"_id": batch_id})
    if existing:
        result = await _existing_batch_result(existing, user, body_hash, project_id)
        return await _retry_batch_derived_state(result, project_id, user)
    settings = await test_design_repository.find_project_settings(project_id)
    drafts = []
    duplicate_threshold = settings.get("testcase_duplicate_threshold", 0.72)
    for item in payload.items:
        context = await review_context(item.draft_id, user, "testcase.approve")
        draft = context["draft"]
        if draft["project_id"] != project_id:
            raise HTTPException(422, detail={"code": "PROJECT_MISMATCH"})
        if draft["revision"] != item.expected_revision:
            raise HTTPException(409, detail={"code": "REVISION_CONFLICT", "draft_id": item.draft_id})
        if context["comparison_token"] != item.comparison_token or context["stale_reasons"]:
            raise HTTPException(409, detail={"code": "TEST_CASE_COMPARISON_STALE", "draft_id": item.draft_id})
        if draft.get("status") != "IN_REVIEW":
            raise HTTPException(409, detail={"code": "INVALID_STATE_TRANSITION", "draft_id": item.draft_id})
        await validate_review_sources_before_approval(draft)
        await validate_test_case_custom_values(
            project_id, draft.get("custom_values", {}), enforce_required=True
        )
        if not has_verifiable_steps(draft):
            raise HTTPException(409, detail={"code": "TEST_CASE_STEPS_REQUIRED", "draft_id": item.draft_id})
        if draft.get("origin") == "ai_generated" and not draft.get("evidence_refs"):
            raise HTTPException(409, detail={"code": "TEST_CASE_SOURCE_REVIEW_REQUIRED", "draft_id": item.draft_id})
        matching_versions = {
            str(match.get("version_id"))
            for match in context.get("duplicates", [])
            if match.get("version_id")
        }
        if (
            matching_versions
            and not str(draft.get("duplicate_reason") or "").strip()
        ):
            raise HTTPException(
                409,
                detail={
                    "code": "TEST_CASE_DUPLICATE_REVIEW_REQUIRED",
                    "draft_id": item.draft_id,
                    "matches": context["duplicates"],
                    "message": "Ca này gần trùng với ca khác đang hiệu lực; QA cần ghi lý do xác nhận vẫn giữ riêng trước khi duyệt nhóm.",
                },
            )
        findings = lint_test_case(draft)
        if settings.get("testcase_lint_blocking", True) and any(item["severity"] == "error" for item in findings):
            raise HTTPException(409, detail={"code": "TEST_CASE_LINT_BLOCKED", "draft_id": item.draft_id, "findings": findings})
        drafts.append(draft)
    if len({draft["test_case_key"] for draft in drafts}) != len(drafts):
        raise HTTPException(409, detail={"code": "MULTIPLE_DRAFTS_FOR_SAME_TEST_CASE"})
    for index, draft in enumerate(drafts):
        duplicate_matches = [
            previous
            for previous in drafts[:index]
            if duplicate_score(draft, previous, duplicate_threshold)[0] >= duplicate_threshold
        ]
        if duplicate_matches and not str(draft.get("duplicate_reason") or "").strip():
            raise HTTPException(
                409,
                detail={
                    "code": "TEST_CASE_BATCH_DUPLICATE_REVIEW_REQUIRED",
                    "draft_id": draft["_id"],
                    "matches": [item["_id"] for item in duplicate_matches],
                    "message": "Các ca trong nhóm gần giống nhau; cần bỏ ca trùng hoặc ghi lý do QA xác nhận tạo riêng.",
                },
            )

    async def commit(session):
        replay = await database.value.audit_events.find_one({"_id": batch_id}, session=session)
        if replay:
            if (
                replay.get("project_id") != project_id
                or replay.get("actor_id") != user.id
                or replay.get("action") != "test_case_group_approved"
                or replay.get("entity_type") != "TestCaseApprovalGroup"
                or replay.get("entity_id") != batch_id
                or (replay.get("details") or {}).get("request_hash") != body_hash
            ):
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            replay_result = (replay.get("details") or {}).get("result")
            replay_count = replay_result.get("count") if isinstance(replay_result, dict) else None
            if (
                not isinstance(replay_result, dict)
                or replay_result.get("batch_id") != batch_id
                or not isinstance(replay_count, int)
                or isinstance(replay_count, bool)
                or replay_count < 1
                or not isinstance(replay_result.get("draft_ids"), list)
                or not isinstance(replay_result.get("version_ids"), list)
                or len(replay_result["draft_ids"]) != replay_count
                or len(replay_result["version_ids"]) != replay_count
            ):
                raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})
            await _verify_batch_publication_links(
                project_id,
                replay_result.get("draft_ids"),
                replay_result.get("version_ids"),
                session=session,
            )
            return {**replay_result, "idempotent": True}, []
        timestamp = now()
        published = []
        for draft in drafts:
            current = await database.value.test_case_drafts.find_one({"_id": draft["_id"], "project_id": project_id, "revision": draft["revision"], "status": "IN_REVIEW"}, session=session)
            if not current:
                raise HTTPException(409, detail={"code": "REVISION_CONFLICT", "draft_id": draft["_id"]})
            await assert_sources_current_in_session(current, session)
            await validate_test_case_custom_values(
                project_id,
                current.get("custom_values", {}),
                enforce_required=True,
                session=session,
            )
            await validate_test_case_publication_uniqueness(
                current, duplicate_threshold, session
            )
            case = await database.value.test_cases.find_one({"project_id": project_id, "test_case_key": draft["test_case_key"]}, session=session)
            if case:
                parent = await database.value.test_case_versions.find_one({"_id": case.get("current_version_id"), "project_id": project_id}, session=session)
                if not parent or draft.get("parent_version_id") != parent["_id"]:
                    raise HTTPException(409, detail={"code": "TEST_CASE_BASE_VERSION_CHANGED"})
                number, parent_id = parent["version"] + 1, parent["_id"]
            else:
                if draft.get("parent_version_id"):
                    raise HTTPException(409, detail={"code": "TEST_CASE_PARENT_VERSION_CHANGED"})
                case = {"_id": new_id("TC"), "project_id": project_id, "test_case_key": draft["test_case_key"], "current_version_id": None, "status": "ACTIVE", "owner_id": draft.get("owner_id") or draft.get("created_by"), "tags": draft.get("tags", []), "created_at": timestamp, "updated_at": timestamp}
                await database.value.test_cases.insert_one(case, session=session)
                number, parent_id = 1, None
            approval = TestCaseFreezeInput(expected_revision=draft["revision"], change_reason="QA chấp nhận nhóm ca đã chọn", review_note=payload.review_note)
            version = build_test_case_version(draft, case["_id"], number, parent_id, approval, user, timestamp)
            await database.value.test_case_versions.insert_one(version, session=session)
            changed = await database.value.test_cases.update_one({"_id": case["_id"], "project_id": project_id, "current_version_id": parent_id}, {"$set": {"current_version_id": version["_id"], "status": "ACTIVE", "updated_at": timestamp}}, session=session)
            if changed.matched_count != 1:
                raise HTTPException(409, detail={"code": "TEST_CASE_VERSION_CONFLICT"})
            transitioned = await database.value.test_case_drafts.update_one({"_id": draft["_id"], "project_id": project_id, "revision": draft["revision"], "status": "IN_REVIEW"}, {"$set": {"status": "APPROVED", "frozen_version_id": version["_id"], "approved_by": user.id, "approved_at": timestamp, "approval_batch_id": batch_id}, "$inc": {"revision": 1}}, session=session)
            if transitioned.matched_count != 1:
                raise HTTPException(409, detail={"code": "REVISION_CONFLICT", "draft_id": draft["_id"]})
            await queue_test_case_approved(version, user, session)
            published.append((draft, version))
        result = {"batch_id": batch_id, "count": len(published), "draft_ids": [draft["_id"] for draft, _ in published], "version_ids": [version["_id"] for _, version in published], "idempotent": False}
        await database.value.audit_events.insert_one({"_id": batch_id, "project_id": project_id, "actor_id": user.id, "action": "test_case_group_approved", "entity_type": "TestCaseApprovalGroup", "entity_id": batch_id, "created_at": timestamp, "details": {"request_hash": body_hash, "review_note": payload.review_note, "selected_items": [item.model_dump() for item in payload.items], "result": result}}, session=session)
        return result, published

    try:
        async with await database.client.start_session() as session:
            result, published = await session.with_transaction(commit)
    except DuplicateKeyError as error:
        existing = await database.value.audit_events.find_one(
            {"_id": batch_id, "project_id": project_id}
        )
        if existing:
            result = await _existing_batch_result(existing, user, body_hash, project_id)
            return await _retry_batch_derived_state(result, project_id, user)
        raise HTTPException(
            409,
            detail={"code": "TEST_CASE_VERSION_CONFLICT", "message": "Có phiên bản ca kiểm thử trùng khóa; không có ca nào trong nhóm được duyệt."},
        ) from error
    if not published:
        return await _retry_batch_derived_state(
            {**result, "idempotent": True}, project_id, user
        )
    pending = []
    for draft, version in published:
        try:
            if not await finalize_test_case_derivatives(draft, version, user):
                pending.append(version["_id"])
        except Exception:
            pending.append(version["_id"])
    return {**result, "derived_pending_version_ids": sorted(set(pending))}


async def _existing_batch_result(existing, user, body_hash, project_id):
    details = existing.get("details") or {}
    batch_id = existing.get("_id")
    if (
        existing.get("project_id") != project_id
        or existing.get("actor_id") != user.id
        or existing.get("action") != "test_case_group_approved"
        or existing.get("entity_type") != "TestCaseApprovalGroup"
        or existing.get("entity_id") != batch_id
        or details.get("request_hash") != body_hash
    ):
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
    result = details.get("result")
    draft_ids = result.get("draft_ids") if isinstance(result, dict) else None
    version_ids = result.get("version_ids") if isinstance(result, dict) else None
    count = result.get("count") if isinstance(result, dict) else None

    def valid_ids(values):
        return (
            isinstance(values, list)
            and all(isinstance(value, str) and value for value in values)
            and len(values) == len(set(values))
        )

    if (
        not isinstance(result, dict)
        or not existing.get("_id")
        or result.get("batch_id") != batch_id
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 1
        or not valid_ids(draft_ids)
        or not valid_ids(version_ids)
        or len(draft_ids) != count
        or len(version_ids) != count
    ):
        raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})
    await _verify_batch_publication_links(project_id, draft_ids, version_ids)
    return {**await _result_with_derived_state(result), "idempotent": True}


async def _retry_batch_derived_state(result, project_id, user):
    draft_ids = result.get("draft_ids") or []
    version_ids = result.get("version_ids") or []
    if len(draft_ids) != len(version_ids):
        raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})
    await _verify_batch_publication_links(project_id, draft_ids, version_ids)
    pending = []
    for draft_id, version_id in zip(draft_ids, version_ids, strict=True):
        draft = await database.value.test_case_drafts.find_one(
            {"_id": draft_id, "project_id": project_id, "status": "APPROVED", "frozen_version_id": version_id}
        )
        version = await database.value.test_case_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )
        if not draft or not version:
            raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})
        try:
            ready = await finalize_test_case_derivatives(draft, version, user)
        except Exception:
            ready = False
        if not ready:
            pending.append(version_id)
    return {
        **result,
        "derived_pending_version_ids": sorted(set(pending)),
    }


async def _verify_batch_publication_links(project_id, draft_ids, version_ids, session=None):
    if (
        not isinstance(draft_ids, list)
        or not isinstance(version_ids, list)
        or not draft_ids
        or len(draft_ids) != len(version_ids)
        or any(not isinstance(value, str) or not value for value in draft_ids + version_ids)
        or len(draft_ids) != len(set(draft_ids))
        or len(version_ids) != len(set(version_ids))
    ):
        raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})
    db = database.value
    drafts = await db.test_case_drafts.find(
        {"_id": {"$in": draft_ids}, "project_id": project_id},
        {"_id": 1, "status": 1, "frozen_version_id": 1, "test_case_key": 1},
        **({"session": session} if session is not None else {}),
    ).to_list(len(draft_ids))
    versions = await db.test_case_versions.find(
        {"_id": {"$in": version_ids}, "project_id": project_id},
        {"_id": 1, "test_case_id": 1},
        **({"session": session} if session is not None else {}),
    ).to_list(len(version_ids))
    drafts_by_id = {str(item.get("_id")): item for item in drafts}
    versions_by_id = {str(item.get("_id")): item for item in versions}
    if len(drafts_by_id) != len(draft_ids) or len(versions_by_id) != len(version_ids):
        raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})
    for draft_id, version_id in zip(draft_ids, version_ids, strict=True):
        approved_draft = drafts_by_id.get(draft_id)
        published_version = versions_by_id.get(version_id)
        if (
            not approved_draft
            or approved_draft.get("status") != "APPROVED"
            or approved_draft.get("frozen_version_id") != version_id
            or not published_version
            or not published_version.get("test_case_id")
        ):
            raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})
    case_ids = list({item["test_case_id"] for item in versions_by_id.values()})
    cases = await db.test_cases.find(
        {"_id": {"$in": case_ids}, "project_id": project_id},
        {"_id": 1, "test_case_key": 1},
        **({"session": session} if session is not None else {}),
    ).to_list(len(case_ids))
    cases_by_id = {str(item.get("_id")): item for item in cases}
    if set(cases_by_id) != set(case_ids):
        raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})
    for draft_id, version_id in zip(draft_ids, version_ids, strict=True):
        approved_draft = drafts_by_id[draft_id]
        published_version = versions_by_id[version_id]
        published_case = cases_by_id[str(published_version["test_case_id"])]
        if (
            not approved_draft.get("test_case_key")
            or approved_draft.get("test_case_key") != published_case.get("test_case_key")
        ):
            raise HTTPException(409, detail={"code": "TEST_CASE_APPROVAL_INCOMPLETE"})


async def _result_with_derived_state(result):
    version_ids = list(
        dict.fromkeys(
            str(version_id)
            for version_id in result.get("version_ids", [])
            if isinstance(version_id, str) and version_id
        )
    )
    versions = await database.value.test_case_versions.find(
        {"_id": {"$in": version_ids}},
        {
            "_id": 1,
            "index_status": 1,
            "trace_status": 1,
            "approval_audit_status": 1,
            "adequacy_invalidation_status": 1,
        },
    ).to_list(100)
    ready = {
        "index_status": "INDEXED",
        "trace_status": "READY",
        "approval_audit_status": "READY",
        "adequacy_invalidation_status": "READY",
    }
    found_ids = {str(version.get("_id") or "") for version in versions}
    pending = set(version_ids) - found_ids
    pending.update(
        str(version["_id"])
        for version in versions
        if any(version.get(key) != value for key, value in ready.items())
    )
    return {**result, "derived_pending_version_ids": sorted(pending)}
