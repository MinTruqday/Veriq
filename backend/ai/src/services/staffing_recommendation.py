from fastapi import HTTPException

from src.prompts.staffing_recommendation import build_staffing_recommendation_prompt
from src.schemas.inference_staffing import (
    StaffingRecommendationOutput,
    StaffingRecommendationRequest,
)
from src.services.inference import structured


async def recommend_staffing(request: StaffingRecommendationRequest) -> StaffingRecommendationOutput:
    result = await structured(
        build_staffing_recommendation_prompt(
            request.required_skills,
            [item.model_dump() for item in request.candidates],
            request.output_language,
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
        allowed_facts = {
            fact.fact_id for fact in candidate_by_id[item.candidate_id].evidence_facts
        }
        if not item.supporting_facts or not set(item.supporting_facts).issubset(allowed_facts):
            raise HTTPException(status_code=422, detail={"code": "STAFFING_EVIDENCE_REFERENCE_INVALID"})
    return result
