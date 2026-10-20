import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, new_id, now
from src.repositories.test_completion import find_ai_result, insert_ai_result
from src.core.ai_assistance import ai_contract_metadata, request_ai_assistance





async def completion_ai_result(report, payload, user, capability, result_type):
    
    if report["status"] != 'DRAFT':
        raise HTTPException(
            status_code=409, detail={"code": 'COMPLETION_REPORT_IMMUTABLE'}
        )
    existing = await find_ai_result(
        report["project_id"], payload.idempotency_key
    )
    if existing:
        if (
            existing.get("result_type") != result_type
            or existing.get("subject_id") != report["_id"]
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": 'IDEMPOTENCY_KEY_REUSED'},
            )
        return existing
    evidence = [
        {
            "artifact_type": 'test_completion_report',
            "artifact_id": report["_id"],
            "authority": 'PROJECT_RECORD',
            "text": json.dumps(
                {
                    key: report.get(key)
                    for key in (
                        "execution_summary",
                        "coverage_summary",
                        "defect_summary",
                        "unresolved_items",
                        "residual_risks",
                        "exit_criteria_evaluation",
                        "quality_gate_status",
                        "deviations",
                        "environment_closure",
                        "lessons_learned",
                        "improvement_actions",
                        "recommendation",
                    )
                },
                ensure_ascii=False,
                default=str,
            ),
        }
    ]
    instruction = json.dumps(
        {"user_instruction": payload.instruction}, ensure_ascii=False
    )
    ai = await request_ai_assistance(capability, report["project_id"], instruction, evidence)
    result = {
        "_id": new_id('AIR'),
        "project_id": report["project_id"],
        "result_type": result_type,
        "subject_id": report["_id"],
        "candidate_only": True,
        "human_confirmation_required": True,
        "suggestions": ai.get("suggestions", []),
        **ai_contract_metadata(ai),
        "idempotency_key": payload.idempotency_key,
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        await insert_ai_result(result)
    except DuplicateKeyError:
        return await find_ai_result(report["project_id"], payload.idempotency_key)
    await audit(
        user.id,
        f"{capability}_generated",
        'AIResult',
        result["_id"],
        report["project_id"],
        {"report_id": report["_id"], "candidate_count": len(result["suggestions"])},
    )
    return result
