import hashlib
import json

from fastapi import HTTPException

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    next_key,
    now,
    optimistic_patch,
    plain_text,
)
from src.core.database import database
from src.repositories.test_design import test_design_repository
from src.repositories.analysis import (
    ActiveTestCaseVersionIntegrityError,
    analysis_repository,
)
from src.repositories.common import common_repository
from src.modules.design.services.linters import duplicate_score
from src.modules.design.services.test_evidence import requirement_test_evidence_text
from src.modules.design.services.test_case_custom_fields import (
    inherit_custom_values,
    validate_test_case_custom_values,
)


def project_test_text(value):
    steps = " ".join(
        f"{plain_text(step.get('action_doc', {}))} {plain_text(step.get('expected_doc', {}))}"
        for step in value.get("steps", [])
    )
    return " ".join(
        [
            value.get("title", ""),
            plain_text(value.get("objective_doc", {})),
            plain_text(value.get("preconditions_doc", {})),
            steps,
            plain_text(value.get("expected_result_doc", {})),
            plain_text(value.get("postconditions_doc", {})),
            " ".join(str(item) for item in (value.get("custom_values") or {}).values()),
        ]
    ).strip()


def active_suite_signature(cases, requirement_version_ids):
    requirement_ids = set(requirement_version_ids)
    snapshot = [
        {
            "id": item["_id"],
            "revision": item.get("revision"),
            "updated_at": item.get("updated_at"),
            "acceptance_criterion_ids": sorted(item.get("acceptance_criterion_ids", [])),
            "techniques": sorted(item.get("techniques", [])),
            "test_data": item.get("test_data", {}),
            "step_test_data": [step.get("test_data", {}) for step in item.get("steps", [])],
            "text": project_test_text(item),
        }
        for item in cases
        if item.get("status") == "ACTIVE"
        and requirement_ids.intersection(item.get("requirement_version_ids", []))
    ]
    snapshot.sort(key=lambda item: item["id"])
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def acceptance_criteria_snapshot_matches(snapshot_ids, current_ids):
    """Check the complete criterion set observed by generation, not cited subset."""
    if snapshot_ids is None:
        return None
    snapshot_ids = list(snapshot_ids)
    if len(snapshot_ids) != len(set(snapshot_ids)):
        return False
    return set(snapshot_ids) == set(current_ids)


async def require_current_baselined_version(version):
    requirement = await test_design_repository.find_current_requirement(
        version["project_id"], version["requirement_id"]
    )
    current_version = bool(
        requirement and requirement.get("current_version_id") == version["_id"]
    )
    baselined = bool(
        current_version
        and requirement.get("status") == "BASELINED"
        and version.get("status") == "BASELINED"
    )
    if not baselined:
        raise HTTPException(409, detail={"code": "TEST_DESIGN_REQUIREMENT_CHANGED", "message": "Phiên bản yêu cầu đã thay đổi hoặc chưa được duyệt  Hãy tải lại trước khi thiết kế ca kiểm thử"})


async def comparison_cases(project_id):
    versions = []
    try:
        async for page in analysis_repository.iter_active_test_case_version_pages(
            project_id, "ACTIVE"
        ):
            versions.extend(page)
    except ActiveTestCaseVersionIntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "TEST_CASE_CURRENT_VERSION_MISSING"},
        ) from error
    drafts = []
    async for page in test_design_repository.iter_case_draft_pages(
        project_id, ["DRAFT", "IN_REVIEW", "APPROVING"]
    ):
        drafts.extend(page)
    settings = await test_design_repository.find_project_settings(project_id)
    return versions + drafts, settings.get("testcase_duplicate_threshold", 0.72)


async def validate_design_sources(
    project_id,
    requirement_version_ids,
    acceptance_criterion_ids,
    scenario_id=None,
    test_condition_ids=None,
):
    
    requirement_ids = list(dict.fromkeys(requirement_version_ids or []))
    criterion_ids = list(dict.fromkeys(acceptance_criterion_ids or []))
    if requirement_ids:
        count = await test_design_repository.count_requirement_versions(
            project_id, requirement_ids
        )
        if count != len(requirement_ids):
            raise HTTPException(
                status_code=422, detail={"code": 'CROSS_PROJECT_OR_MISSING_REQUIREMENT_VERSION'}
            )
    if criterion_ids:
        query = {"project_id": project_id, "_id": {"$in": criterion_ids}}
        if requirement_ids:
            query["requirement_version_id"] = {"$in": requirement_ids}
        count = await test_design_repository.count_acceptance_criteria(query)
        if count != len(criterion_ids):
            raise HTTPException(
                status_code=422, detail={"code": 'CROSS_PROJECT_OR_MISSING_ACCEPTANCE_CRITERION'}
            )
    if scenario_id:
        scenario = await test_design_repository.find_scenario(
            scenario_id, project_id
        )
        if not scenario:
            raise HTTPException(
                status_code=422, detail={"code": 'CROSS_PROJECT_OR_MISSING_TEST_SCENARIO'}
            )
    condition_ids = list(dict.fromkeys(test_condition_ids or []))
    if condition_ids:
        settings = await test_design_repository.find_project_settings(project_id)
        query = {
            "project_id": project_id,
            "_id": {"$in": condition_ids},
            "status": {"$ne": 'ARCHIVED'},
        }
        conditions = await test_design_repository.list_conditions(query, len(condition_ids))
        found_ids = {item["_id"] for item in conditions}
        missing_ids = [
            condition_id for condition_id in condition_ids if condition_id not in found_ids
        ]
        if missing_ids:
            raise HTTPException(
                status_code=422,
                detail={"code": 'TEST_CONDITION_NOT_FOUND', "condition_ids": missing_ids},
            )
        strict = settings.get(
            'require_condition_approval_before_testcase',
            settings.get('require_approved_test_conditions', False),
        )
        unapproved_ids = [
            item["_id"]
            for item in conditions
            if item.get("status") != 'APPROVED'
        ]
        if strict and unapproved_ids:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": 'TEST_CONDITION_NOT_APPROVED',
                    "condition_ids": unapproved_ids,
                },
            )


async def validate_data_set_versions(project_id, data_set_version_ids):
    
    version_ids = list(dict.fromkeys(data_set_version_ids or []))
    if not version_ids:
        return
    count = await test_design_repository.count_data_set_versions(
        project_id, version_ids
    )
    if count != len(version_ids):
        raise HTTPException(
            status_code=422, detail={"code": 'CROSS_PROJECT_OR_MISSING_DATA_SET_VERSION'}
        )


async def validate_test_design_structure(project_id, repository_node_id, bdd):
    if repository_node_id and not await test_design_repository.find_repository_node(
        project_id, repository_node_id
    ):
        raise HTTPException(status_code=422, detail={"code": "TEST_REPOSITORY_NODE_NOT_FOUND"})
    for item in (bdd.steps if bdd else []):
        if item.reusable_step_version_id and not await test_design_repository.find_reusable_step_version(
            project_id, item.reusable_step_version_id
        ):
            raise HTTPException(status_code=422, detail={"code": "REUSABLE_TEST_STEP_NOT_FOUND"})


async def validate_test_case_owner(project_id, owner_id):
    owner = str(owner_id or "").strip()
    if not owner:
        return None
    membership = await common_repository.find_membership(
        project_id, owner, status="ACTIVE", projection={"_id": 1, "user_id": 1}
    )
    if (
        not membership
        or membership.get("status", "ACTIVE") != "ACTIVE"
        or membership.get("user_id", owner) != owner
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TEST_CASE_OWNER_NOT_ACTIVE_PROJECT_MEMBER",
                "message": "Người phụ trách phải là thành viên đang hoạt động của dự án.",
            },
        )
    return owner


async def validate_coverage_items(project_id, requirement_version_ids, coverage_item_ids):
    if not coverage_item_ids:
        return
    from src.modules.design.services.test_adequacy import _sources

    versions = await analysis_repository.list_requirement_versions(
        project_id, list(dict.fromkeys(requirement_version_ids)), len(set(requirement_version_ids))
    )
    available = {
        item["coverage_item_id"]
        for version in versions
        for item in await _sources(version)
    }
    missing = sorted(set(coverage_item_ids) - available)
    if missing:
        raise HTTPException(status_code=422, detail={"code": "COVERAGE_ITEM_SOURCE_INVALID", "coverage_item_ids": missing})


async def create_test_case_draft_record(
    project_id, payload, user, parent_version_id=None, change_reason=None, session=None,
    draft_id=None,
):
    
    await get_project(project_id, user, "testcase.create")
    if payload.owner_id:
        await get_project(project_id, user, "project.members.read")
    owner_id = await validate_test_case_owner(project_id, payload.owner_id)
    if owner_id != payload.owner_id:
        payload = payload.model_copy(update={"owner_id": owner_id})
    if payload.custom_values:
        await validate_test_case_custom_values(project_id, payload.custom_values)
    if payload.target_version_id:
        if payload.origin != "ai_generated" or parent_version_id or len((payload.version_reason or "").strip()) < 2:
            raise HTTPException(status_code=422, detail={"code": "TEST_CASE_VERSION_RESOLUTION_INVALID"})
        await get_project(project_id, user, "testcase.version.create")
        target = await test_design_repository.find_case_version(payload.target_version_id, project_id)
        target_case = await test_design_repository.find_case(target["test_case_id"], project_id) if target else None
        if (
            not target_case
            or target_case.get("status") != "ACTIVE"
            or target_case.get("current_version_id") != payload.target_version_id
            or (payload.test_case_key and payload.test_case_key != target_case.get("test_case_key"))
        ):
            raise HTTPException(status_code=409, detail={"code": "TEST_CASE_VERSION_TARGET_CHANGED", "message": "Phiên bản ca kiểm thử đích đã thay đổi  Hãy tạo lại bản xem trước"})
        parent_version_id = payload.target_version_id
        change_reason = payload.version_reason.strip()
        payload = payload.model_copy(
            update={
                "test_case_key": target_case["test_case_key"],
                "custom_values": inherit_custom_values(payload.custom_values, target),
            }
        )
    elif payload.version_reason:
        raise HTTPException(status_code=422, detail={"code": "TEST_CASE_VERSION_RESOLUTION_INVALID"})
    if payload.test_case_key:
        existing = await test_design_repository.find_case_by_key(
            project_id, payload.test_case_key
        )
        if existing and parent_version_id != existing.get("current_version_id"):
            raise HTTPException(status_code=409, detail={"code": "TEST_CASE_EXISTING_KEY_REQUIRES_VERSION_DRAFT"})
        if not existing and parent_version_id:
            raise HTTPException(status_code=409, detail={"code": "TEST_CASE_PARENT_VERSION_CHANGED"})
    await validate_design_sources(
        project_id,
        payload.requirement_version_ids,
        payload.acceptance_criterion_ids,
        payload.scenario_id,
        payload.test_condition_ids,
    )
    await validate_data_set_versions(project_id, payload.data_set_version_ids)
    await validate_test_design_structure(project_id, payload.repository_node_id, payload.bdd)
    await validate_coverage_items(
        project_id, payload.requirement_version_ids, payload.coverage_item_ids
    )
    if payload.origin == "ai_generated":
        if not payload.requirement_version_ids or not payload.source_evidence or not payload.evidence_refs or not payload.suite_signature:
            raise HTTPException(422, detail={"code": "TEST_CASE_EVIDENCE_REQUIRED", "message": "Ca kiểm thử do AI tạo cần liên kết yêu cầu và bằng chứng nguồn"})
        versions = await analysis_repository.list_requirement_versions(
            project_id, payload.requirement_version_ids, len(payload.requirement_version_ids)
        )
        if len(versions) != len(set(payload.requirement_version_ids)):
            raise HTTPException(409, detail={"code": "TEST_DESIGN_REQUIREMENT_CHANGED", "message": "Phiên bản yêu cầu đã thay đổi  Hãy tải lại trước khi lưu ca kiểm thử"})
        for version in versions:
            await require_current_baselined_version(version)
        existing, threshold = await comparison_cases(project_id)
        if payload.suite_signature != active_suite_signature(existing, payload.requirement_version_ids):
            raise HTTPException(409, detail={"code": "TEST_DESIGN_PREVIEW_STALE", "message": "Bộ ca đang hiệu lực đã thay đổi  Hãy tạo lại bản xem trước trước khi lưu"})
        active_refs = {
            item["_id"]
            for item in existing
            if item.get("status") == "ACTIVE"
            and set(item.get("requirement_version_ids", [])) & set(payload.requirement_version_ids)
        }
        source_text_by_ref = {
            item.get("artifact_version_id"): item.get("text", "")
            for item in payload.source_evidence
        }
        if any(
            challenge.technique not in payload.techniques
            or challenge.source_ref not in payload.evidence_refs
            or challenge.source_quote.strip() not in source_text_by_ref.get(challenge.source_ref, "")
            or not set(challenge.existing_case_refs) <= active_refs
            for challenge in payload.challenge_hypotheses
        ):
            raise HTTPException(409, detail={"code": "TEST_DESIGN_CHALLENGE_SOURCE_CHANGED", "message": "Giả thuyết thiết kế không còn khớp với nguồn hoặc ca đang hiệu lực  Hãy tạo lại bản xem trước"})
        matches = sorted(
            (
                (score, item)
                for item in existing
                if (score := duplicate_score(payload.model_dump(), item, threshold)[0]) >= threshold
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )[:3]
        if payload.target_version_id and payload.target_version_id not in {item["_id"] for _, item in matches}:
            raise HTTPException(status_code=409, detail={"code": "TEST_CASE_VERSION_TARGET_CHANGED", "message": "Ca đích không còn khớp bản xem trước  Hãy tạo lại bản xem trước"})
        if matches and not ((payload.duplicate_reason or "").strip() or change_reason):
            raise HTTPException(status_code=409, detail={"code": "TEST_CASE_DUPLICATE_REVIEW_REQUIRED", "message": "Cần bỏ qua ca gần giống hoặc ghi lý do tạo ca riêng", "matches": [{"id": item["_id"], "title": item.get("title"), "score": score} for score, item in matches]})
    source_evidence = payload.source_evidence
    if payload.evidence_refs or payload.coverage_obligations:
        version_ids = list(dict.fromkeys(payload.requirement_version_ids))
        versions = await analysis_repository.list_requirement_versions(
            project_id, version_ids, len(version_ids)
        ) if version_ids else []
        criterion_ids = list(dict.fromkeys(
            item.get("artifact_version_id") for item in source_evidence
            if item.get("artifact_type") == "acceptance_criterion" and item.get("artifact_version_id")
        ))
        if payload.origin == "ai_generated":
            source_version_ids = {
                item.get("artifact_version_id")
                for item in source_evidence
                if item.get("artifact_type") == "requirement_version"
            }
            snapshot_matches = None
            if payload.acceptance_criteria_snapshot_ids is not None:
                current_criteria = [
                    criterion
                    for version_id in version_ids
                    for criterion in await analysis_repository.list_acceptance_criteria(version_id)
                ]
                snapshot_matches = acceptance_criteria_snapshot_matches(
                    payload.acceptance_criteria_snapshot_ids,
                    [item["_id"] for item in current_criteria],
                )
            else:
                current_criterion_count = await test_design_repository.count_acceptance_criteria({
                    "project_id": project_id,
                    "requirement_version_id": {"$in": version_ids},
                })
                snapshot_matches = current_criterion_count == len(criterion_ids)
            if source_version_ids != set(version_ids) or not snapshot_matches:
                raise HTTPException(status_code=409, detail={"code": "TEST_CASE_EVIDENCE_CHANGED", "message": "Nguồn yêu cầu hoặc tiêu chí chấp nhận đã thay đổi  Hãy tạo lại bản xem trước"})
        criteria = await test_design_repository.list_acceptance_criteria_by_ids(
            project_id, version_ids, criterion_ids
        ) if criterion_ids else []
        expected = {
            ("requirement_version", item["_id"]): requirement_test_evidence_text(item)
            for item in versions
        }
        expected.update({
            ("acceptance_criterion", item["_id"]): item.get("plain_text") or plain_text(item.get("content_doc", {}))
            for item in criteria
        })
        seen = set()
        canonical = []
        for item in source_evidence:
            identity = (item.get("artifact_type"), item.get("artifact_version_id"))
            if identity in seen or not expected.get(identity) or item.get("text") != expected[identity]:
                raise HTTPException(status_code=422, detail={"code": "TEST_CASE_EVIDENCE_CHANGED"})
            seen.add(identity)
            canonical.append({
                "artifact_type": identity[0],
                "artifact_version_id": identity[1],
                "text": expected[identity],
            })
        if not payload.evidence_refs or not set(payload.evidence_refs) <= {item[1] for item in seen}:
            raise HTTPException(status_code=422, detail={"code": "TEST_CASE_EVIDENCE_CHANGED"})
        source_evidence = canonical
    draft = {
        "_id": draft_id or new_id('TCD'),
        "project_id": project_id,
        **payload.model_dump(exclude={
            "suite_signature",
            "target_version_id",
            "version_reason",
            "acceptance_criteria_snapshot_ids",
        }),
        "source_evidence": source_evidence,
        "test_case_key": payload.test_case_key
        or await next_key(project_id, 'test_case', 'TC'),
        **({"parent_version_id": parent_version_id, "change_reason": change_reason} if parent_version_id else {}),
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": now(),
        "updated_at": now(),
    }
    if payload.origin in {"ai_generated", "maintenance"}:
        from src.modules.design.services.test_case_review import proposal_snapshot

        draft["ai_proposal_snapshot"] = proposal_snapshot(draft)
        draft["review_acceptance_criteria_snapshot_ids"] = payload.acceptance_criteria_snapshot_ids
    from src.clients.ai_automation import emit_test_case_changed

    async def persist(active_session):
        await test_design_repository.insert_case_draft(draft, session=active_session)
        await audit(
            user.id,
            "test_case_draft_created",
            "TestCaseDraft",
            draft["_id"],
            project_id,
            session=active_session,
        )
        await emit_test_case_changed(draft, user, session=active_session)

    if session is not None:
        await persist(session)
    else:
        async with await database.client.start_session() as active_session:
            async with active_session.start_transaction():
                await persist(active_session)
    return draft


async def create_generated_test_case_draft_batch(project_id, payloads, user):
    await get_project(project_id, user, "testcase.create")
    if not payloads or len(payloads) > 100:
        raise HTTPException(422, detail={"code": "TEST_CASE_BATCH_SIZE_INVALID"})
    first = payloads[0]
    if (
        first.origin != "ai_generated"
        or not first.suite_signature
        or any(
            item.origin != "ai_generated"
            or item.requirement_version_ids != first.requirement_version_ids
            or item.suite_signature != first.suite_signature
            for item in payloads
        )
    ):
        raise HTTPException(422, detail={"code": "TEST_CASE_BATCH_SOURCE_MISMATCH"})
    targets = [item.target_version_id for item in payloads if item.target_version_id]
    if len(targets) != len(set(targets)):
        raise HTTPException(422, detail={"code": "TEST_CASE_BATCH_TARGET_CONFLICT", "message": "Không thể tạo nhiều bản nháp phiên bản cho cùng một ca trong một lượt"})
    settings = await test_design_repository.find_project_settings(project_id)
    threshold = settings.get("testcase_duplicate_threshold", 0.72)
    for index, item in enumerate(payloads):
        if any(
            duplicate_score(item.model_dump(), previous.model_dump(), threshold)[0] >= threshold
            for previous in payloads[:index]
        ) and (item.target_version_id or not (item.duplicate_reason or "").strip()):
            raise HTTPException(
                409,
                detail={
                    "code": "TEST_CASE_BATCH_DUPLICATE_REVIEW_REQUIRED",
                    "index": index,
                    "message": "Các ca trong cùng lượt tạo gần giống nhau  Hãy bỏ ca trùng hoặc ghi lý do tạo riêng",
                },
            )
    created = []
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            for index, item in enumerate(payloads):
                try:
                    created.append(
                        await create_test_case_draft_record(
                            project_id, item, user, session=session
                        )
                    )
                except HTTPException as error:
                    detail = error.detail
                    if isinstance(detail, dict):
                        detail = {**detail, "index": index}
                    raise HTTPException(error.status_code, detail=detail) from error
    return created


async def update_test_case_draft_record(draft_id, payload, user, project_id=None):
    
    draft = await get_project_entity("test_case_drafts", draft_id, user, "testcase.update")
    if project_id is not None and draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if draft["status"] != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'IMMUTABLE_TEST_CASE_DRAFT'})
    if payload.attachments is not None:
        await get_project(draft["project_id"], user, "attachment.manage")
    if payload.owner_id is not None and payload.owner_id != draft.get("owner_id"):
        await get_project(draft["project_id"], user, "project.members.read")
        owner_id = await validate_test_case_owner(draft["project_id"], payload.owner_id)
        payload = payload.model_copy(update={"owner_id": owner_id})
    await validate_design_sources(
        draft["project_id"],
        payload.requirement_version_ids
        if payload.requirement_version_ids is not None
        else draft.get("requirement_version_ids", []),
        payload.acceptance_criterion_ids
        if payload.acceptance_criterion_ids is not None
        else draft.get("acceptance_criterion_ids", []),
        payload.scenario_id if payload.scenario_id is not None else draft.get("scenario_id"),
        payload.test_condition_ids
        if payload.test_condition_ids is not None
        else draft.get("test_condition_ids", []),
    )
    await validate_data_set_versions(
        draft["project_id"],
        payload.data_set_version_ids
        if payload.data_set_version_ids is not None
        else draft.get("data_set_version_ids", []),
    )
    await validate_test_design_structure(
        draft["project_id"],
        payload.repository_node_id
        if payload.repository_node_id is not None
        else draft.get("repository_node_id"),
        payload.bdd if payload.bdd is not None else draft.get("bdd"),
    )
    changes = payload.model_dump()
    effective_custom_values = (
        payload.custom_values if payload.custom_values is not None else draft.get("custom_values", {})
    )
    if effective_custom_values:
        await validate_test_case_custom_values(draft["project_id"], effective_custom_values)
    if (draft.get("evidence_refs") or draft.get("coverage_obligations") or draft.get("obligation_evidence") or draft.get("challenge_hypotheses")) and any(
        changes.get(field) is not None and changes[field] != draft.get(field)
        for field in (
            "title", "type", "objective_doc", "preconditions_doc", "steps", "test_data",
            "expected_result_doc", "postconditions_doc", "techniques",
            "requirement_version_ids", "acceptance_criterion_ids",
            "data_set_version_ids", "test_condition_ids", "scenario_id",
        )
    ):
        changes["coverage_obligations"] = []
        changes["obligation_evidence"] = []
        changes["evidence_refs"] = []
        changes["challenge_hypotheses"] = []
    from src.clients.ai_automation import emit_test_case_changed

    async with await database.client.start_session() as session:
        async with session.start_transaction():
            updated = await optimistic_patch(
                "test_case_drafts",
                draft_id,
                draft["project_id"],
                payload.expected_revision,
                changes,
                session=session,
            )
            await audit(
                user.id,
                "test_case_draft_updated",
                "TestCaseDraft",
                draft_id,
                draft["project_id"],
                session=session,
            )
            await emit_test_case_changed(
                updated, user, previous_case=draft, session=session
            )
    return updated
