from fastapi import HTTPException

from src.core.common import get_project, get_project_entity, plain_text
from src.repositories.analysis import analysis_repository
from src.repositories.test_design import test_design_repository
from src.core.ai_assistance import ai_contract_metadata, request_ai_assistance
from src.modules.design.services.generation import generate_requirement_drafts
from src.modules.design.services.linters import duplicate_score
from src.modules.design.services.test_case_records import comparison_cases, project_test_text


async def generate_test_case_draft_records(version_id, payload, user):
    if not payload.preview_only:
        raise HTTPException(422, detail={"code": "TEST_CASE_PREVIEW_REQUIRED", "message": "Cần xem trước và chọn ca kiểm thử trước khi lưu"})
    version = await get_project_entity(
        "requirement_versions", version_id, user, "ai.generate_testcase"
    )
    await get_project(version["project_id"], user, "testcase.create")
    criteria = await analysis_repository.list_acceptance_criteria(version_id)
    drafts, result = await generate_requirement_drafts(version, criteria, payload, scenario=False)
    related, similarity_threshold = await comparison_cases(version["project_id"])
    items = []
    for index, (draft, generated) in enumerate(zip(drafts, result["suggestions"])):
        matches = sorted(
            (
                (score, item)
                for item in related
                if (score := duplicate_score(draft.model_dump(), item)[0]) >= similarity_threshold
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )[:3]
        items.append({
            "draft": draft.model_dump(),
            "coverage_obligations": generated.get("coverage_obligations", []),
            "evidence_refs": generated.get("evidence_refs", []),
            "similar_cases": [{"id": item["_id"], "title": item.get("title"), "score": score} for score, item in matches],
        })
        related.append({"_id": f"preview:{index}", **draft.model_dump()})
    return {
        "items": items,
        "evidence": criteria,
        **ai_contract_metadata(result),
        "generation_status": result["status"],
    }


async def recommend_test_design_techniques(version_id, payload, user):
    version = await get_project_entity(
        "requirement_versions", version_id, user, "ai.generate_testcase"
    )
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
            version["project_id"], version_id, remaining + 1
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
    for item in cases + drafts:
        evidence.append({
            "artifact_type": "existing_test_case",
            "artifact_version_id": item["_id"],
            "text": project_test_text(item),
        })
    result = await request_ai_assistance(
        "technique_recommendation", version["project_id"], payload.instruction, evidence
    )
    if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
        raise HTTPException(503, detail={"code": "AI_PROVIDER_UNAVAILABLE", "retryable": True})
    allowed_refs = {item["artifact_version_id"] for item in evidence}
    existing_refs = {
        item["artifact_version_id"] for item in evidence
        if item["artifact_type"] == "existing_test_case"
    }
    suggestions = result.get("suggestions") or []
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
    return {"items": suggestions, "evidence": evidence, **ai_contract_metadata(result)}


async def find_duplicate_test_case_records(project_id, user):
    await get_project(project_id, user, "testcase.duplicate_check")
    await get_project(project_id, user, "ai.run_duplicate_check")
    
    versions = await analysis_repository.list_active_test_case_versions(
        project_id, 'ACTIVE'
    )
    pairs = []
    for index, left in enumerate(versions):
        for right in versions[index + 1 :]:
            score, reasons = duplicate_score(left, right)
            if score >= 0.72:
                pairs.append(
                    {"left": left, "right": right, "similarity": score, "reasons": reasons}
                )
    return sorted(pairs, key=lambda item: item["similarity"], reverse=True)[
        : 100
    ]
