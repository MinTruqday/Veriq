import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.core.common import audit, new_id, now
from src.repositories.test_completion import find_ai_result, insert_ai_result


async def completion_ai_result(report, payload, user, capability, result_type):
    run_id = str(getattr(user, "_ai_automation_run_id", "") or "")
    trigger = str(getattr(user, "_ai_automation_trigger", "") or "")
    source_event_id = str(getattr(user, "_ai_automation_source_event_id", "") or "")
    expected_event_id = (
        f"completion-report:{report['_id']}:{payload.source_event_revision}:"
        "TEST_COMPLETION_REPORT_CREATED"
    )
    if (
        not run_id
        or trigger != payload.source_event_trigger
        or trigger != "TEST_COMPLETION_REPORT_CREATED"
        or source_event_id != payload.source_event_id
        or source_event_id != expected_event_id
        or report.get("revision") != payload.source_event_revision
    ):
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_AI_EVENT_SOURCE_INVALID"})
    if report["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "COMPLETION_REPORT_IMMUTABLE"})
    existing = await find_ai_result(report["project_id"], payload.idempotency_key)
    if existing:
        if (
            existing.get("result_type") != result_type
            or existing.get("subject_id") != report["_id"]
            or existing.get("source_event_id") != source_event_id
            or existing.get("source_event_revision") != payload.source_event_revision
            or existing.get("source_event_trigger") != trigger
            or existing.get("source_automation_run_id") != run_id
        ):
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        return existing
    evidence = [
        {
            "artifact_type": "test_completion_report",
            "artifact_id": report["_id"],
            "authority": "PROJECT_RECORD",
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
    instruction = json.dumps({"user_instruction": payload.instruction}, ensure_ascii=False)
    ai = await request_ai_automation(capability, report["project_id"], instruction, evidence)
    result = {
        "_id": new_id("AIR"),
        "project_id": report["project_id"],
        "result_type": result_type,
        "subject_id": report["_id"],
        "candidate_only": True,
        "human_confirmation_required": False,
        "suggestions": ai.get("suggestions", []),
        **ai_contract_metadata(ai),
        "idempotency_key": payload.idempotency_key,
        "source_event_id": source_event_id,
        "source_event_revision": payload.source_event_revision,
        "source_event_trigger": trigger,
        "source_automation_run_id": run_id,
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        await insert_ai_result(result)
    except DuplicateKeyError:
        replay = await find_ai_result(report["project_id"], payload.idempotency_key)
        if (
            not replay
            or replay.get("result_type") != result_type
            or replay.get("subject_id") != report["_id"]
            or replay.get("source_event_id") != source_event_id
            or replay.get("source_event_revision") != payload.source_event_revision
            or replay.get("source_event_trigger") != trigger
            or replay.get("source_automation_run_id") != run_id
        ):
            raise HTTPException(
                status_code=409, detail={"code": "COMPLETION_AI_IDEMPOTENCY_CONFLICT"}
            )
        return replay
    await audit(
        user.id,
        f"{capability}_generated",
        "AIResult",
        result["_id"],
        report["project_id"],
        {"report_id": report["_id"], "candidate_count": len(result["suggestions"])},
    )
    return result
