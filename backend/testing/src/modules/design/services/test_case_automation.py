from fastapi import HTTPException

from src.core.common import get_project, get_project_entity, plain_text
from src.core.rich_text import text_document
from src.repositories.analysis import analysis_repository
from src.repositories.test_design import test_design_repository
from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.modules.design.services.generation import generate_requirement_drafts, select_generation_criteria
from src.modules.design.services.linters import duplicate_score
from src.modules.design.services.test_case_records import active_suite_signature, comparison_cases, project_test_text, require_current_baselined_version


async def generate_test_case_draft_records(version_id, payload, user):
    if not payload.preview_only:
        raise HTTPException(422, detail={"code": "TEST_CASE_PREVIEW_REQUIRED", "message": "Cần xem trước và chọn ca kiểm thử trước khi lưu"})
    version = await get_project_entity(
        "requirement_versions", version_id, user, "ai.generate_testcase"
    )
    await require_current_baselined_version(
        version, allow_automation_draft=bool(user._ai_automation_run_id)
    )
    await get_project(version["project_id"], user, "testcase.create")
    criteria = await analysis_repository.list_acceptance_criteria(version_id)
    criteria = select_generation_criteria(criteria, payload.acceptance_criterion_ids)
    drafts, result = await generate_requirement_drafts(version, criteria, payload, scenario=False)
    current_versions = await analysis_repository.list_requirement_versions(
        version["project_id"], [version_id], 1
    )
    if not current_versions:
        raise HTTPException(409, detail={"code": "TEST_DESIGN_REQUIREMENT_CHANGED", "message": "Yêu cầu đã thay đổi trong lúc AI tạo ca  Hãy tạo lại bản xem trước"})
    await require_current_baselined_version(
        current_versions[0], allow_automation_draft=bool(user._ai_automation_run_id)
    )
    current_criteria = await analysis_repository.list_acceptance_criteria(version_id)
    current_criteria = select_generation_criteria(
        current_criteria, payload.acceptance_criterion_ids
    )
    if (
        (current_versions[0].get("plain_text_projection") or plain_text(current_versions[0].get("content_doc", {})))
        != (version.get("plain_text_projection") or plain_text(version.get("content_doc", {})))
        or sorted(
            (item["_id"], item.get("plain_text") or plain_text(item.get("content_doc", {})))
            for item in current_criteria
        ) != sorted(
            (item["_id"], item.get("plain_text") or plain_text(item.get("content_doc", {})))
            for item in criteria
        )
    ):
        raise HTTPException(409, detail={"code": "TEST_DESIGN_PREVIEW_STALE", "message": "Nguồn yêu cầu đã thay đổi trong lúc AI tạo ca  Hãy tạo lại bản xem trước"})
    related, similarity_threshold = await comparison_cases(version["project_id"])
    suite_signature = active_suite_signature(related, [version_id])
    if payload.challenge_hypotheses and suite_signature != payload.challenge_suite_signature:
        raise HTTPException(409, detail={"code": "TEST_DESIGN_PREVIEW_STALE", "message": "Bộ ca đang hiệu lực đã thay đổi trong lúc AI tạo ca  Hãy nhận gợi ý mới"})
    await require_current_baselined_version(
        version, allow_automation_draft=bool(user._ai_automation_run_id)
    )
    criterion_ids = {item["_id"] for item in criteria}
    from src.modules.design.services.test_adequacy import _sources
    coverage_by_criterion = {
        item["source_id"]: item["coverage_item_id"]
        for item in await _sources(version)
        if item["source_type"] == "acceptance_criterion"
    }
    linked_criterion_ids = criterion_ids.intersection(
        criterion_id
        for case in related
        if case.get("status") == "ACTIVE"
        if version_id in case.get("requirement_version_ids", [])
        for criterion_id in case.get("acceptance_criterion_ids", [])
    )
    items = []
    for index, (draft, generated) in enumerate(zip(drafts, result["suggestions"])):
        draft = draft.model_copy(update={
            "coverage_item_ids": [
                coverage_by_criterion[criterion_id]
                for criterion_id in draft.acceptance_criterion_ids
                if criterion_id in coverage_by_criterion
            ]
        })
        ranked = sorted(
            (
                (score, item)
                for item in related
                if (score := duplicate_score(draft.model_dump(), item, similarity_threshold)[0]) >= similarity_threshold
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        matches = ranked[:3]
        preview_match = next(
            (match for match in ranked if str(match[1]["_id"]).startswith("preview:")),
            None,
        )
        if preview_match and preview_match not in matches:
            matches[-1] = preview_match
        items.append({
            "draft": {**draft.model_dump(), "suite_signature": suite_signature},
            "coverage_obligations": generated.get("coverage_obligations", []),
            "evidence_refs": generated.get("evidence_refs", []),
            "evidence_quotes": generated.get("evidence_quotes", []),
            "challenge_techniques": generated.get("challenge_techniques", []),
            "new_criterion_ids": sorted(set(draft.acceptance_criterion_ids) - linked_criterion_ids),
            "similar_cases": [{
                "id": item["_id"],
                "title": item.get("title"),
                "score": score,
                "target_version_id": item["_id"] if item.get("test_case_id") and item.get("status") == "ACTIVE" else None,
            } for score, item in matches],
        })
        related.append({"_id": f"preview:{index}", **draft.model_dump()})
    return {
        "items": items,
        "evidence": criteria,
        "challenge_hypotheses": [item.model_dump() for item in payload.challenge_hypotheses],
        "suite_signature": suite_signature,
        "criterion_coverage": {
            "criterion_ids": sorted(criterion_ids),
            "linked_criterion_ids": sorted(linked_criterion_ids),
        },
        **ai_contract_metadata(result),
        "grounding_findings": result.get("findings", []),
        "generation_status": result["status"],
        "unapplied_categories": result.get("unapplied_categories", []),
    }


async def recommend_test_design_techniques(version_id, payload, user):
    version = await get_project_entity(
        "requirement_versions", version_id, user, "ai.generate_testcase"
    )
    await require_current_baselined_version(version)
    criteria = await analysis_repository.list_acceptance_criteria(version_id)
    evidence = [{
        "artifact_type": "requirement_version",
        "artifact_version_id": version_id,
        "text": version.get("plain_text_projection") or plain_text(version.get("content_doc", {})),
    }]
    evidence.extend({
        "artifact_type": "acceptance_criterion",
        "artifact_version_id": item["_id"],
        "text": item.get("plain_text") or plain_text(item.get("content_doc", {})),
    } for item in criteria)
    if len(evidence) > 100:
        raise HTTPException(
            422,
            detail={
                "code": "TECHNIQUE_EVIDENCE_LIMIT_EXCEEDED",
                "message": "Yêu cầu có quá nhiều tiêu chí chấp nhận để đánh giá đầy đủ trong một lượt  Chưa đưa ra gợi ý một phần",
            },
        )
    cases = await analysis_repository.list_related_active_test_case_versions(
        version["project_id"], version_id, 101 - len(evidence)
    )
    remaining = 100 - len(evidence) - len(cases)
    drafts = (
        await test_design_repository.list_related_case_drafts(
            version["project_id"], version_id, remaining + 1,
            ["DRAFT", "IN_REVIEW", "APPROVING"],
        )
        if remaining >= 0 else []
    )
    if len(evidence) + len(cases) + len(drafts) > 100:
        raise HTTPException(
            422,
            detail={
                "code": "TECHNIQUE_EVIDENCE_LIMIT_EXCEEDED",
                "message": "Có quá nhiều ca kiểm thử liên quan để đánh giá đầy đủ trong một lượt  Chưa đưa ra gợi ý một phần",
            },
        )
    for item in cases:
        evidence.append({
            "artifact_type": "existing_test_case",
            "artifact_version_id": item["_id"],
            "text": project_test_text(item),
        })
    for item in drafts:
        evidence.append({
            "artifact_type": "test_case_draft",
            "artifact_version_id": item["_id"],
            "text": project_test_text(item),
        })
    result = await request_ai_automation(
        "technique_recommendation", version["project_id"], payload.instruction, evidence
    )
    if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
        raise HTTPException(503, detail={"code": "AI_PROVIDER_UNAVAILABLE", "retryable": True})
    current_versions = await analysis_repository.list_requirement_versions(
        version["project_id"], [version_id], 1
    )
    if not current_versions:
        raise HTTPException(409, detail={"code": "TEST_DESIGN_REQUIREMENT_CHANGED", "message": "Yêu cầu đã thay đổi trong lúc AI xử lý  Hãy nhận gợi ý mới"})
    await require_current_baselined_version(current_versions[0])
    current_criteria = await analysis_repository.list_acceptance_criteria(version_id)
    current_cases = await analysis_repository.list_related_active_test_case_versions(
        version["project_id"], version_id, len(evidence) + 1
    )
    current_drafts = await test_design_repository.list_related_case_drafts(
        version["project_id"], version_id, len(evidence) + 1,
        ["DRAFT", "IN_REVIEW", "APPROVING"],
    )
    if (
        (current_versions[0].get("plain_text_projection") or plain_text(current_versions[0].get("content_doc", {})))
        != evidence[0]["text"]
        or sorted(
            (item["_id"], item.get("plain_text") or plain_text(item.get("content_doc", {})))
            for item in current_criteria
        ) != sorted(
            (item["artifact_version_id"], item["text"])
            for item in evidence if item["artifact_type"] == "acceptance_criterion"
        )
        or active_suite_signature(current_cases, [version_id]) != active_suite_signature(cases, [version_id])
        or sorted((item["_id"], project_test_text(item)) for item in current_drafts)
        != sorted((item["_id"], project_test_text(item)) for item in drafts)
    ):
        raise HTTPException(409, detail={"code": "TEST_DESIGN_PREVIEW_STALE", "message": "Nguồn yêu cầu hoặc bộ ca đã thay đổi trong lúc AI xử lý  Hãy nhận gợi ý mới"})
    allowed_refs = {item["artifact_version_id"] for item in evidence}
    existing_refs = {
        item["artifact_version_id"] for item in evidence
        if item["artifact_type"] == "existing_test_case"
    }
    source_text_by_ref = {
        item["artifact_version_id"]: item["text"]
        for item in evidence
        if item["artifact_type"] in {"requirement_version", "acceptance_criterion"}
    }
    case_by_ref = {item["_id"]: item for item in cases}
    similarity_threshold = (
        await test_design_repository.find_project_settings(version["project_id"])
    ).get("testcase_duplicate_threshold", 0.72)
    suggestions = result.get("suggestions") or []
    challenge_warnings = []
    if not suggestions or len({item.get("technique") for item in suggestions}) != len(suggestions):
        raise HTTPException(502, detail={"code": "AI_RECOMMENDATION_INVALID"})
    for item in suggestions:
        if not set(item.get("evidence_refs") or []) <= allowed_refs:
            raise HTTPException(502, detail={"code": "AI_RECOMMENDATION_INVALID"})
        if not set(item.get("existing_coverage_refs") or []) <= existing_refs:
            raise HTTPException(502, detail={"code": "AI_RECOMMENDATION_INVALID"})
        if item.get("suitability") in {"recommended", "possible"} and (
            not item.get("evidence_refs") or not item.get("expected_coverage")
        ):
            raise HTTPException(502, detail={"code": "AI_RECOMMENDATION_INVALID"})
        challenge = item.get("challenge")
        if challenge:
            if challenge.get("source_quote", "").strip() not in source_text_by_ref.get(challenge.get("source_ref"), ""):
                item["challenge"] = None
                challenge_warnings.append("AI trích dẫn không đúng nguyên văn yêu cầu nên giả thuyết lỗi chưa được dùng  Hãy nhận gợi ý lại")
            elif (
                item.get("suitability") not in {"recommended", "possible"}
                or not challenge.get("existing_case_refs")
                or challenge.get("source_ref") not in item.get("evidence_refs", [])
                or not set(challenge.get("existing_case_refs") or []) <= existing_refs
            ):
                item["challenge"] = None
                challenge_warnings.append("Giả thuyết lỗi không được hiển thị vì không đối chiếu được với ca đang hiệu lực hoặc nguồn dẫn")
            else:
                challenge_candidate = {
                    "title": challenge["distinguishing_input"],
                    "objective_doc": text_document(challenge["distinguishing_input"]),
                    "preconditions_doc": text_document(""),
                    "steps": [{
                        "action_doc": text_document(challenge["distinguishing_input"]),
                        "expected_doc": text_document(challenge["expected_result"]),
                        "test_data": {},
                    }],
                    "expected_result_doc": text_document(challenge["expected_result"]),
                    "requirement_version_ids": [version_id],
                    "acceptance_criterion_ids": [challenge["source_ref"]]
                    if challenge["source_ref"] in {criterion["_id"] for criterion in criteria}
                    else [],
                }
                if any(
                    duplicate_score(
                        challenge_candidate,
                        case_by_ref[existing_ref],
                        similarity_threshold,
                    )[0] >= similarity_threshold
                    for existing_ref in challenge["existing_case_refs"]
                ):
                    item["challenge"] = None
                    challenge_warnings.append("Giả thuyết lỗi không tạo thêm phạm vi kiểm thử so với ca đang hiệu lực nên chưa được dùng")
    return {
        "items": suggestions,
        "evidence": evidence,
        "suite_signature": active_suite_signature(cases, [version_id]),
        **ai_contract_metadata(result),
        "warnings": list(dict.fromkeys(result.get("warnings", []) + challenge_warnings)),
    }


async def find_duplicate_test_case_records(project_id, user):
    await get_project(project_id, user, "testcase.duplicate_check")
    await get_project(project_id, user, "ai.run_duplicate_check")
    
    versions = await analysis_repository.list_active_test_case_versions(
        project_id, 'ACTIVE'
    )
    settings = await test_design_repository.find_project_settings(project_id)
    pairs = []
    for index, left in enumerate(versions):
        for right in versions[index + 1 :]:
            threshold = settings.get("testcase_duplicate_threshold", 0.72)
            score, reasons = duplicate_score(left, right, threshold)
            if score >= threshold:
                pairs.append(
                    {"left": left, "right": right, "similarity": score, "reasons": reasons}
                )
    return sorted(pairs, key=lambda item: item["similarity"], reverse=True)[
        : 100
    ]
