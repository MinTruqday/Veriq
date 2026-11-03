import hashlib
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, new_id, now
from src.core.database import database
from src.repositories.causal_analysis import causal_analysis_repository
from src.modules.quality.services.causal_analysis_query import get_analysis
from src.core.ai_automation import (
    ai_contract_metadata,
    request_ai_automation,
    require_ai_automation_event,
)


def _hypothesis_request_hash(payload, analysis, automation):
    request = payload.model_dump(mode="json", exclude={"idempotency_key"})
    request.update(
        {
            "analysis_id": analysis["_id"],
            "analysis_revision": analysis.get("revision"),
            "problem_statement": analysis.get("problem_statement"),
            "source_event_id": analysis["source_event_id"],
            "source_event_revision": analysis["source_event_revision"],
            "automation_run_id": automation["run_id"],
        }
    )
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_hypothesis_replay(existing, payload, analysis, automation, user):
    if not existing.get("created_by"):
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if existing["created_by"] != user.id:
        raise HTTPException(403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _hypothesis_request_hash(payload, analysis, automation):
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})


async def generate_hypotheses(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.update")
    automation = require_ai_automation_event(
        user, {"DEFECT_RECORDED", "DEFECT_CHANGED"}
    )
    if (
        not value.get("source_event_id")
        or value.get("source_event_id") != automation["source_event_id"]
        or value.get("source_event_trigger") != automation["trigger"]
        or value.get("source_automation_run_id") != automation["run_id"]
        or len(value.get("defect_ids") or []) != 1
    ):
        raise HTTPException(
            status_code=403,
            detail={"code": "VERIFIED_DEFECT_EVENT_REQUIRED"},
        )
    expected_event_id = (
        f"defect:{value['defect_ids'][0]}:{value.get('source_event_revision')}"
    )
    if value["source_event_id"] != expected_event_id:
        raise HTTPException(
            status_code=409,
            detail={"code": "DEFECT_EVENT_IDENTITY_MISMATCH"},
        )
    current_defects = await causal_analysis_repository.list_defects(
        {
            "_id": value["defect_ids"][0],
            "project_id": value["project_id"],
        },
        1,
    )
    if (
        not current_defects
        or current_defects[0].get("revision") != value.get("source_event_revision")
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "DEFECT_EVENT_SUPERSEDED"},
        )
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
        _verify_hypothesis_replay(existing, payload, value, automation, user)
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
    ai = await request_ai_automation(
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
        "idempotency_request_hash": _hypothesis_request_hash(payload, value, automation),
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await causal_analysis_repository.insert_ai_result(result, session=session)
                await audit(
                    user.id,
                    "causal_analysis_ai_hypotheses_generated",
                    "AIResult",
                    result["_id"],
                    value["project_id"],
                    {"analysis_id": analysis_id, "candidate_count": len(result["suggestions"])},
                    session=session,
                )
    except DuplicateKeyError:
        existing = await causal_analysis_repository.find_ai_result_by_idempotency(
            value["project_id"], payload.idempotency_key
        )
        if not existing:
            raise
        if (
            existing.get("result_type") != 'CAUSAL_ANALYSIS_HYPOTHESES'
            or existing.get("subject_id") != analysis_id
        ):
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        _verify_hypothesis_replay(existing, payload, value, automation, user)
        return existing
    return result
