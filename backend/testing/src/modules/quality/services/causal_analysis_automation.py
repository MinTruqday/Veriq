import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, new_id, now
from src.repositories.causal_analysis import causal_analysis_repository
from src.modules.quality.services.causal_analysis_query import get_analysis
from src.core.ai_assistance import ai_contract_metadata, request_ai_assistance


async def generate_hypotheses(analysis_id, payload, user):
    
    value = await get_analysis(analysis_id, user, "causalanalysis.update")
    existing = await causal_analysis_repository.find_ai_result_by_idempotency(
        value["project_id"], payload.idempotency_key
    )
    if existing:
        if (
            existing.get("result_type") != 'CAUSAL_ANALYSIS_HYPOTHESES'
            or existing.get("subject_id") != analysis_id
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": 'IDEMPOTENCY_KEY_REUSED'},
            )
        return existing
    defects = await causal_analysis_repository.list_defects(
        {"_id": {"$in": value["defect_ids"]}, "project_id": value["project_id"]},
        500,
    )
    historical = await causal_analysis_repository.list_defects(
        {
            "project_id": value["project_id"],
            "_id": {"$nin": value["defect_ids"]},
            "root_cause_category": {"$ne": 'UNKNOWN'},
        },
        100,
        {"_id": 1, "title": 1, "root_cause_category": 1, "root_cause_detail": 1},
    )
    evidence = [
        {
            "artifact_type": "defect",
            "artifact_id": item["_id"],
            "authority": 'PROJECT_RECORD',
            "text": json.dumps(
                {
                    key: item.get(key)
                    for key in [
                        "title",
                        "severity",
                        "status",
                        "root_cause_category",
                        "root_cause_detail",
                        "injected_phase",
                        "detected_phase",
                        "escape_reason",
                    ]
                },
                ensure_ascii=False,
                default=str,
            ),
        }
        for item in [*defects, *historical]
    ]
    instruction = json.dumps(
        {
            "problem_statement": value["problem_statement"],
            "user_instruction": payload.instruction,
        },
        ensure_ascii=False,
    )
    ai = await request_ai_assistance(
        "causal_analysis", value["project_id"], instruction, evidence
    )
    result = {
        "_id": new_id('AIR'),
        "project_id": value["project_id"],
        "result_type": 'CAUSAL_ANALYSIS_HYPOTHESES',
        "subject_id": analysis_id,
        "candidate_only": True,
        "human_confirmation_required": True,
        "suggestions": ai.get("suggestions", []),
        **ai_contract_metadata(ai),
        "idempotency_key": payload.idempotency_key,
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        await causal_analysis_repository.insert_ai_result(result)
    except DuplicateKeyError:
        return await causal_analysis_repository.find_ai_result_by_idempotency(
            value["project_id"], payload.idempotency_key
        )
    await audit(
        user.id,
        "causal_analysis_ai_hypotheses_generated",
        "AIResult",
        result["_id"],
        value["project_id"],
        {"analysis_id": analysis_id, "candidate_count": len(result["suggestions"])},
    )
    return result
