import hashlib
import json

from fastapi import HTTPException

from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.core.common import audit, get_project_entity, new_id, now, plain_text
from src.core.database import database
from src.core.source_evidence import split_source_evidence
from src.repositories.test_run import test_run_repository


def _result_source_text(result):
    lines = [f"Trạng thái đã lưu: {result.get('status') or 'Chưa ghi nhận'}"]
    actual = plain_text(result.get("actual_result_doc") or {})
    if actual:
        lines.append(f"Kết quả thực tế đã ghi: {actual}")
    note = str(result.get("note") or "").strip()
    if note:
        lines.append(f"Ghi chú đã lưu: {note}")
    for index, item in enumerate(result.get("step_results") or [], start=1):
        lines.append(f"Bước đã ghi nhận {index}, mã bước {item.get('step_id') or 'không có'}")
        lines.append(f"Trạng thái bước: {item.get('status') or 'Chưa ghi nhận'}")
        actual_step = plain_text(item.get("actual_doc") or {})
        if actual_step:
            lines.append(f"Kết quả bước đã ghi: {actual_step}")
        step_note = str(item.get("note") or "").strip()
        if step_note:
            lines.append(f"Ghi chú bước đã lưu: {step_note}")
    return "\n".join(lines)


def _case_source_text(version):
    lines = [
        f"Mã ca kiểm thử: {version.get('test_case_key') or 'Chưa có mã'}",
        f"Tên ca kiểm thử: {version.get('title') or 'Chưa có tên'}",
    ]
    objective = plain_text(version.get("objective_doc") or {})
    preconditions = plain_text(version.get("preconditions_doc") or {})
    if objective:
        lines.append(f"Mục tiêu: {objective}")
    if preconditions:
        lines.append(f"Điều kiện trước: {preconditions}")
    for index, item in enumerate(version.get("steps") or [], start=1):
        lines.append(f"Bước {index}, mã bước {item.get('id') or 'không có'}")
        lines.append(f"Thao tác: {plain_text(item.get('action_doc') or {})}")
        lines.append(f"Kết quả mong đợi: {plain_text(item.get('expected_doc') or {})}")
    return "\n".join(lines)


def _scope_fingerprint(run, result, version):
    scope = {
        "run_id": str(run["_id"]),
        "run_revision": run.get("revision"),
        "result_id": str(result["_id"]),
        "result_revision": result.get("revision"),
        "case_version_id": str(version["_id"]),
        "case_version_revision": version.get("revision"),
        "result": _result_source_text(result),
        "case": _case_source_text(version),
    }
    canonical = json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _execution_assistance_scope(project_id, run_id, result_id, user):
    result = await get_project_entity("test_results", result_id, user, "testrun.execute")
    if result.get("project_id") != project_id or result.get("test_run_id") != run_id:
        raise HTTPException(status_code=404, detail={"code": "TEST_RESULT_NOT_FOUND"})
    if result.get("status") in {"NOT_RUN", "IN_PROGRESS"}:
        raise HTTPException(status_code=409, detail={"code": "EXECUTION_RESULT_NOT_RECORDED"})
    run = await test_run_repository.find_run(run_id, project_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "TEST_RUN_NOT_FOUND"})
    versions = await test_run_repository.list_versions([result.get("test_case_version_id")], 1)
    if not versions:
        raise HTTPException(status_code=409, detail={"code": "TEST_CASE_VERSION_UNAVAILABLE"})
    version = versions[0]
    if version.get("project_id") != project_id:
        raise HTTPException(status_code=409, detail={"code": "TEST_CASE_PROJECT_MISMATCH"})
    evidence = []
    for artifact_type, artifact_id, text in (
        ("test_case_version", str(version["_id"]), _case_source_text(version)),
        ("test_result", str(result["_id"]), _result_source_text(result)),
        (
            "test_run_context",
            str(run["_id"]),
            json.dumps(
                {
                    "run_name": run.get("name"),
                    "environment": run.get("environment"),
                    "build": run.get("build"),
                    "release": run.get("release"),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        ),
    ):
        for chunk in split_source_evidence(artifact_type, artifact_id, text):
            evidence.append(
                {
                    "artifact_type": artifact_type,
                    "artifact_id": artifact_id,
                    "artifact_version_id": f"{artifact_id}:c{chunk['chunk_index']}",
                    "text": chunk["text"],
                }
            )
    if not evidence:
        raise HTTPException(status_code=422, detail={"code": "EXECUTION_ASSISTANCE_EVIDENCE_REQUIRED"})
    if len(evidence) > 100:
        raise HTTPException(status_code=422, detail={"code": "EXECUTION_ASSISTANCE_SCOPE_TOO_LARGE"})
    return run, result, version, evidence, _scope_fingerprint(run, result, version)


async def generate_execution_assistance(project_id, run_id, result_id, user):
    run, result, version, evidence, fingerprint = await _execution_assistance_scope(
        project_id, run_id, result_id, user
    )
    existing = await database.value.ai_results.find_one(
        {
            "project_id": project_id,
            "result_type": "EXECUTION_ASSISTANCE",
            "subject_id": result_id,
            "source_fingerprint": fingerprint,
        },
        sort=[("created_at", -1)],
    )
    if existing:
        return {**existing, "stale": False, "saved": True}
    context = {
        "saved_result_status": result.get("status"),
        "defect_draft_allowed": result.get("status") in {"FAIL", "BLOCKED"},
        "case_version_id": version["_id"],
        "result_revision": result.get("revision"),
    }
    ai_result = await request_ai_automation(
        "execution_assistance",
        project_id,
        json.dumps(context, ensure_ascii=False),
        evidence,
    )
    if ai_result.get("status") != "SUCCESS" or ai_result.get("degraded_mode"):
        raise HTTPException(
            status_code=503,
            detail={"code": "EXECUTION_ASSISTANCE_UNAVAILABLE", "retryable": True},
        )
    suggestions = ai_result.get("suggestions") or []
    if len(suggestions) != 1:
        raise HTTPException(status_code=502, detail={"code": "EXECUTION_ASSISTANCE_RESPONSE_INVALID"})
    suggestion = suggestions[0]
    defect_draft = suggestion.get("defect_draft")
    if defect_draft and result.get("status") not in {"FAIL", "BLOCKED"}:
        raise HTTPException(status_code=502, detail={"code": "EXECUTION_ASSISTANCE_DEFECT_STATUS_INVALID"})
    source_by_ref = {item["artifact_version_id"]: item for item in evidence}
    if set(ai_result.get("evidence_refs") or []) - set(source_by_ref):
        raise HTTPException(status_code=502, detail={"code": "EXECUTION_ASSISTANCE_REFERENCE_INVALID"})
    cited_refs = []
    valid_step_ids = {str(item.get("id")) for item in version.get("steps") or []}
    for observation in suggestion.get("observations") or []:
        if observation.get("step_id") and observation["step_id"] not in valid_step_ids:
            raise HTTPException(status_code=502, detail={"code": "EXECUTION_ASSISTANCE_STEP_INVALID"})
        for quote in observation.get("evidence_quotes") or []:
            source = source_by_ref.get(quote.get("evidence_ref"))
            if not source or quote.get("quote", "").strip() not in source["text"]:
                raise HTTPException(
                    status_code=502, detail={"code": "EXECUTION_ASSISTANCE_GROUNDING_INVALID"}
                )
            cited_refs.append(quote["evidence_ref"])
    if defect_draft:
        for quote in defect_draft.get("evidence_quotes") or []:
            source = source_by_ref.get(quote.get("evidence_ref"))
            if not source or quote.get("quote", "").strip() not in source["text"]:
                raise HTTPException(
                    status_code=502, detail={"code": "EXECUTION_ASSISTANCE_GROUNDING_INVALID"}
                )
            cited_refs.append(quote["evidence_ref"])
    if not cited_refs:
        raise HTTPException(status_code=502, detail={"code": "EXECUTION_ASSISTANCE_GROUNDING_REQUIRED"})
    if set(ai_result.get("evidence_refs") or []) - set(cited_refs):
        raise HTTPException(status_code=502, detail={"code": "EXECUTION_ASSISTANCE_REFERENCE_INVALID"})
    latest_scope = await _execution_assistance_scope(project_id, run_id, result_id, user)
    if latest_scope[4] != fingerprint:
        raise HTTPException(
            status_code=409,
            detail={"code": "EXECUTION_ASSISTANCE_SOURCE_CHANGED", "retryable": True},
        )
    record = {
        "_id": new_id("AIR"),
        "project_id": project_id,
        "result_type": "EXECUTION_ASSISTANCE",
        "subject_id": result_id,
        "source_run_id": run_id,
        "source_result_id": result_id,
        "source_case_version_id": str(version["_id"]),
        "source_fingerprint": fingerprint,
        "candidate_only": True,
        "human_confirmation_required": True,
        "suggestions": suggestions,
        "evidence_refs": list(dict.fromkeys(cited_refs)),
        "created_by": user.id,
        "created_at": now(),
        **ai_contract_metadata(ai_result),
    }
    await database.value.ai_results.insert_one(record)
    await audit(
        user.id,
        "execution_assistance_generated",
        "TestResult",
        result_id,
        project_id,
        {"ai_result_id": record["_id"], "source_revision": result.get("revision")},
    )
    return {**record, "stale": False, "saved": True}


async def latest_execution_assistance(project_id, run_id, result_id, user):
    scope = await _execution_assistance_scope(project_id, run_id, result_id, user)
    record = await database.value.ai_results.find_one(
        {
            "project_id": project_id,
            "result_type": "EXECUTION_ASSISTANCE",
            "subject_id": result_id,
        },
        sort=[("created_at", -1)],
    )
    if not record:
        return None
    stale = record.get("source_fingerprint") != scope[4]
    if stale:
        record["suggestions"] = []
        record["evidence_refs"] = []
    record["stale"] = stale
    return record
