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
from src.repositories.test_design import test_design_repository
from src.repositories.analysis import analysis_repository
from src.modules.design.services.linters import duplicate_score


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
        ]
    ).strip()


async def comparison_cases(project_id):
    versions = await analysis_repository.list_active_test_case_versions(project_id, "ACTIVE", 2001)
    drafts = await test_design_repository.list_case_drafts(project_id, 2001)
    if len(versions) > 2000 or len(drafts) > 2000:
        raise HTTPException(status_code=422, detail={"code": "TEST_CASE_COMPARISON_LIMIT_EXCEEDED", "message": "Có quá nhiều ca kiểm thử để đối chiếu đầy đủ, chưa cho tạo ca mới có thể trùng"})
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


async def create_test_case_draft_record(project_id, payload, user):
    
    await get_project(project_id, user, "testcase.create")
    await validate_design_sources(
        project_id,
        payload.requirement_version_ids,
        payload.acceptance_criterion_ids,
        payload.scenario_id,
        payload.test_condition_ids,
    )
    await validate_data_set_versions(project_id, payload.data_set_version_ids)
    if payload.origin == "ai_generated":
        existing, threshold = await comparison_cases(project_id)
        matches = sorted(
            (
                (score, item)
                for item in existing
                if (score := duplicate_score(payload.model_dump(), item)[0]) >= threshold
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )[:3]
        if matches and not (payload.duplicate_reason or "").strip():
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
        criteria = await test_design_repository.list_acceptance_criteria_by_ids(
            project_id, version_ids, criterion_ids
        ) if criterion_ids else []
        expected = {
            ("requirement_version", item["_id"]): item.get("plain_text_projection") or plain_text(item.get("content_doc", {}))
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
        "_id": new_id('TCD'),
        "project_id": project_id,
        **payload.model_dump(),
        "source_evidence": source_evidence,
        "test_case_key": payload.test_case_key
        or await next_key(project_id, 'test_case', 'TC'),
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": now(),
        "updated_at": now(),
    }
    await test_design_repository.insert_case_draft(draft)
    await audit(user.id, "test_case_draft_created", "TestCaseDraft", draft["_id"], project_id)
    return draft


async def update_test_case_draft_record(draft_id, payload, user, project_id=None):
    
    draft = await get_project_entity("test_case_drafts", draft_id, user, "testcase.update")
    if project_id is not None and draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    if draft["status"] != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'IMMUTABLE_TEST_CASE_DRAFT'})
    if payload.attachments is not None:
        await get_project(draft["project_id"], user, "attachment.manage")
    await validate_design_sources(
        draft["project_id"],
        payload.requirement_version_ids
        if payload.requirement_version_ids is not None
        else draft.get("requirement_version_ids", []),
        payload.acceptance_criterion_ids
        if payload.acceptance_criterion_ids is not None
        else draft.get("acceptance_criterion_ids", []),
        payload.scenario_id if payload.scenario_id is not None else draft.get("scenario_id"),
    )
    await validate_data_set_versions(
        draft["project_id"],
        payload.data_set_version_ids
        if payload.data_set_version_ids is not None
        else draft.get("data_set_version_ids", []),
    )
    changes = payload.model_dump()
    if (draft.get("evidence_refs") or draft.get("coverage_obligations")) and any(
        changes.get(field) is not None and changes[field] != draft.get(field)
        for field in (
            "title", "type", "objective_doc", "preconditions_doc", "steps", "test_data",
            "expected_result_doc", "postconditions_doc", "techniques",
            "requirement_version_ids", "acceptance_criterion_ids",
        )
    ):
        changes["coverage_obligations"] = []
        changes["evidence_refs"] = []
    updated = await optimistic_patch(
        "test_case_drafts",
        draft_id,
        draft["project_id"],
        payload.expected_revision,
        changes,
    )
    await audit(user.id, "test_case_draft_updated", "TestCaseDraft", draft_id, draft["project_id"])
    return updated
