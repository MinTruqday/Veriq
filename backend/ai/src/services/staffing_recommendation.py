import unicodedata

from fastapi import HTTPException

from src.prompts.staffing_recommendation import build_staffing_recommendation_prompt
from src.schemas.inference_staffing import (
    StaffingRecommendationOutput,
    StaffingRecommendationRequest,
)
from src.services.inference import structured


def _skill_key(value):
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(normalized.split())


async def recommend_staffing(request: StaffingRecommendationRequest) -> StaffingRecommendationOutput:
    result = await structured(
        build_staffing_recommendation_prompt(
            request.required_skills,
            [item.model_dump() for item in request.candidates],
            request.output_language,
            request.task_context,
        ),
        StaffingRecommendationOutput,
        max_tokens=min(5000, 300 + len(request.candidates) * 180),
        timeout_seconds=120,
    )
    candidate_by_id = {item.candidate_id: item for item in request.candidates}
    ranked_ids = {item.candidate_id for item in result.recommendations}
    if ranked_ids != set(candidate_by_id):
        raise HTTPException(status_code=422, detail={"code": "STAFFING_CANDIDATE_SET_MISMATCH"})
    for item in result.recommendations:
        candidate = candidate_by_id[item.candidate_id]
        allowed_facts = {
            fact.fact_id for fact in candidate.evidence_facts
        }
        if not item.supporting_facts or not set(item.supporting_facts).issubset(allowed_facts):
            raise HTTPException(status_code=422, detail={"code": "STAFFING_EVIDENCE_REFERENCE_INVALID"})
        matched_skills = [match.required_skill for match in item.skill_matches]
        skill_labels = {_skill_key(label) for label in request.required_skills}
        normalized_matches = [_skill_key(label) for label in matched_skills]
        normalized_unmatched = [_skill_key(label) for label in item.unmatched_required_skills]
        if (
            len(normalized_matches) != len(set(normalized_matches))
            or not set(normalized_matches).issubset(skill_labels)
            or not set(normalized_unmatched).issubset(skill_labels)
            or len(normalized_unmatched) != len(set(normalized_unmatched))
            or set(normalized_matches) & set(normalized_unmatched)
            or set(normalized_matches) | set(normalized_unmatched) != set(skill_labels)
        ):
            raise HTTPException(status_code=422, detail={"code": "STAFFING_SKILL_COVERAGE_INVALID"})
        used_skill_facts = set()
        for match in item.skill_matches:
            if match.evidence_fact_id not in allowed_facts or not match.evidence_fact_id.startswith("skill-"):
                raise HTTPException(status_code=422, detail={"code": "STAFFING_SKILL_EVIDENCE_INVALID"})
            if match.evidence_fact_id in used_skill_facts:
                raise HTTPException(status_code=422, detail={"code": "STAFFING_SKILL_EVIDENCE_REUSED"})
            used_skill_facts.add(match.evidence_fact_id)
            fact_suffix = match.evidence_fact_id.removeprefix("skill-")
            if not fact_suffix.isdecimal():
                raise HTTPException(status_code=422, detail={"code": "STAFFING_SKILL_EVIDENCE_INVALID"})
            if match.match_type == "EXACT":
                index = int(fact_suffix) - 1
                required_key = _skill_key(match.required_skill)
                if (
                    index < 0
                    or index >= len(candidate.confirmed_skills)
                    or _skill_key(candidate.confirmed_skills[index]) != required_key
                ):
                    raise HTTPException(status_code=422, detail={"code": "STAFFING_EXACT_SKILL_MATCH_INVALID"})
            elif match.match_type == "EQUIVALENT":
                index = int(fact_suffix) - 1
                if (
                    index < 0
                    or index >= len(candidate.confirmed_skills)
                    or _skill_key(candidate.confirmed_skills[index]) == _skill_key(match.required_skill)
                ):
                    raise HTTPException(status_code=422, detail={"code": "STAFFING_EQUIVALENT_SKILL_MATCH_INVALID"})
    return result
