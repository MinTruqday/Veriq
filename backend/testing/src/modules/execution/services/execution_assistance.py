import hashlib
import json
import logging
import unicodedata
from datetime import timedelta

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.core.common import audit, get_project_entity, new_id, now, plain_text
from src.core.database import database
from src.core.sensitive_data import redact_sensitive_text
from src.core.source_evidence import split_source_evidence
from src.modules.execution.services.execution_state import assigned_execution_versions
from src.repositories.test_run import test_run_repository

logger = logging.getLogger(__name__)


def _invalid_execution_assistance_response(project_id, result_id, request_id, code):
    logger.warning(
        "Execution assistance response rejected project_id=%s result_id=%s request_id=%s code=%s",
        project_id,
        result_id,
        request_id,
        code,
    )
    return HTTPException(status_code=502, detail={"code": code})


def _quote_is_exact_source_excerpt(source_text, quote):
    normalized_source = unicodedata.normalize("NFC", str(source_text or ""))
    normalized_quote = unicodedata.normalize("NFC", str(quote or "").strip())
    return bool(normalized_quote) and normalized_quote in normalized_source


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


def _normalize_source_phrase(value):
    normalized = unicodedata.normalize("NFC", str(value or "")).casefold()
    return " ".join(normalized.split()).rstrip(" .,!?:;")


def _defect_values_are_grounded(defect_draft, result, version):
    expected_values = [
        redact_sensitive_text(plain_text(item.get("expected_doc") or {}))
        for item in version.get("steps") or []
    ]
    actual_values = [
        redact_sensitive_text(plain_text(result.get("actual_result_doc") or {})),
        *[
            redact_sensitive_text(plain_text(item.get("actual_doc") or {}))
            for item in result.get("step_results") or []
        ],
    ]
    expected_values = [value for value in expected_values if value]
    actual_values = [value for value in actual_values if value]
    if not expected_values or not actual_values:
        return False
    expected_sources = [*expected_values, "\n".join(expected_values)]
    actual_sources = [*actual_values, "\n".join(actual_values)]

    def matches_source(value, sources):
        phrase = _normalize_source_phrase(value)
        return bool(phrase) and any(
            phrase == _normalize_source_phrase(source) for source in sources
        )

    return matches_source(
        defect_draft.get("expected_result"), expected_sources
    ) and matches_source(defect_draft.get("actual_result"), actual_sources)


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
    version_id = str(version.get("_id") or "")
    if version_id not in {str(item) for item in run.get("test_case_version_ids") or []}:
        raise HTTPException(status_code=409, detail={"code": "TEST_CASE_OUTSIDE_RUN_SCOPE"})
    assigned_version_ids = await assigned_execution_versions(run, user)
    if version_id not in {str(item) for item in assigned_version_ids}:
        raise HTTPException(status_code=403, detail={"code": "TEST_CASE_ASSIGNMENT_REQUIRED"})
    evidence = []
    redactions_applied = False
    for artifact_type, artifact_id, text in (
        ("test_case_version", str(version["_id"]), _case_source_text(version)),
        ("test_result", str(result["_id"]), _result_source_text(result)),
    ):
        safe_text = redact_sensitive_text(text)
        redactions_applied = redactions_applied or safe_text != text
        for chunk in split_source_evidence(artifact_type, artifact_id, safe_text):
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
    fingerprint = _scope_fingerprint(run, result, version)
    return run, result, version, evidence, fingerprint, redactions_applied


async def _claim_execution_assistance(project_id, result_id, fingerprint, user_id):
    collection = database.value.ai_results
    timestamp = now()
    claim_token = new_id("AIC")
    idempotency_key = f"execution-assistance:{fingerprint}"
    reservation = {
        "_id": new_id("AIR"),
        "project_id": project_id,
        "result_type": "EXECUTION_ASSISTANCE_PENDING",
        "subject_id": result_id,
        "source_fingerprint": fingerprint,
        "idempotency_key": idempotency_key,
        "claim_token": claim_token,
        "lease_expires_at": timestamp + timedelta(minutes=35),
        "created_by": user_id,
        "created_at": timestamp,
    }
    try:
        await collection.insert_one(reservation)
        return reservation
    except DuplicateKeyError:
        existing = await collection.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )
        if not existing or existing.get("source_fingerprint") != fingerprint:
            raise HTTPException(
                status_code=409,
                detail={"code": "EXECUTION_ASSISTANCE_IDEMPOTENCY_CONFLICT"},
            )
        if existing.get("result_type") == "EXECUTION_ASSISTANCE":
            return existing
        if existing.get("result_type") != "EXECUTION_ASSISTANCE_PENDING":
            raise HTTPException(
                status_code=409,
                detail={"code": "EXECUTION_ASSISTANCE_RESERVATION_INVALID"},
            )
        reclaimed = await collection.find_one_and_update(
            {
                "_id": existing["_id"],
                "result_type": "EXECUTION_ASSISTANCE_PENDING",
                "lease_expires_at": {"$lte": timestamp},
            },
            {
                "$set": {
                    "claim_token": claim_token,
                    "lease_expires_at": timestamp + timedelta(minutes=35),
                    "updated_at": timestamp,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not reclaimed:
            raise HTTPException(
                status_code=409,
                detail={"code": "EXECUTION_ASSISTANCE_ALREADY_RUNNING", "retryable": True},
            )
        return reclaimed


async def _build_execution_assistance_record(
    project_id, run_id, result_id, user, scope, reservation
):
    run, result, version, evidence, fingerprint, redactions_applied = scope
    context = {
        "saved_result_status": result.get("status"),
        "defect_draft_allowed": result.get("status") in {"FAIL", "BLOCKED"},
        "case_version_id": version["_id"],
        "result_revision": result.get("revision"),
        "sensitive_values_redacted": redactions_applied,
    }
    request_id = new_id("TRC")
    ai_result = await request_ai_automation(
        "execution_assistance",
        project_id,
        json.dumps(context, ensure_ascii=False),
        evidence,
        request_id=request_id,
    )
    if ai_result.get("status") != "SUCCESS" or ai_result.get("degraded_mode"):
        raise HTTPException(
            status_code=503,
            detail={"code": "EXECUTION_ASSISTANCE_UNAVAILABLE", "retryable": True},
        )
    suggestions = ai_result.get("suggestions") or []
    if len(suggestions) != 1:
        raise _invalid_execution_assistance_response(
            project_id, result_id, request_id, "EXECUTION_ASSISTANCE_RESPONSE_INVALID"
        )
    suggestion = suggestions[0]
    defect_draft = suggestion.get("defect_draft")
    if defect_draft and result.get("status") not in {"FAIL", "BLOCKED"}:
        raise _invalid_execution_assistance_response(
            project_id, result_id, request_id, "EXECUTION_ASSISTANCE_DEFECT_STATUS_INVALID"
        )
    if defect_draft and not _defect_values_are_grounded(defect_draft, result, version):
        raise _invalid_execution_assistance_response(
            project_id, result_id, request_id, "EXECUTION_ASSISTANCE_DEFECT_VALUE_UNGROUNDED"
        )
    source_by_ref = {item["artifact_version_id"]: item for item in evidence}
    if set(ai_result.get("evidence_refs") or []) - set(source_by_ref):
        raise _invalid_execution_assistance_response(
            project_id, result_id, request_id, "EXECUTION_ASSISTANCE_REFERENCE_INVALID"
        )
    cited_refs = []
    valid_step_ids = {str(item.get("id")) for item in version.get("steps") or []}
    for observation in suggestion.get("observations") or []:
        if observation.get("step_id") and observation["step_id"] not in valid_step_ids:
            raise _invalid_execution_assistance_response(
                project_id, result_id, request_id, "EXECUTION_ASSISTANCE_STEP_INVALID"
            )
        for quote in observation.get("evidence_quotes") or []:
            source = source_by_ref.get(quote.get("evidence_ref"))
            if not source or not _quote_is_exact_source_excerpt(
                source["text"], quote.get("quote")
            ):
                raise _invalid_execution_assistance_response(
                    project_id, result_id, request_id, "EXECUTION_ASSISTANCE_GROUNDING_INVALID"
                )
            cited_refs.append(quote["evidence_ref"])
    if defect_draft:
        for quote in defect_draft.get("evidence_quotes") or []:
            source = source_by_ref.get(quote.get("evidence_ref"))
            if not source or not _quote_is_exact_source_excerpt(
                source["text"], quote.get("quote")
            ):
                raise _invalid_execution_assistance_response(
                    project_id, result_id, request_id, "EXECUTION_ASSISTANCE_GROUNDING_INVALID"
                )
            cited_refs.append(quote["evidence_ref"])
    if not cited_refs:
        raise _invalid_execution_assistance_response(
            project_id, result_id, request_id, "EXECUTION_ASSISTANCE_GROUNDING_REQUIRED"
        )
    latest_scope = await _execution_assistance_scope(project_id, run_id, result_id, user)
    if latest_scope[4] != fingerprint:
        raise HTTPException(
            status_code=409,
            detail={"code": "EXECUTION_ASSISTANCE_SOURCE_CHANGED", "retryable": True},
        )
    contract_metadata = ai_contract_metadata(ai_result)
    contract_metadata.pop("evidence_refs", None)
    record = {
        **reservation,
        "result_type": "EXECUTION_ASSISTANCE",
        "source_run_id": run_id,
        "source_result_id": result_id,
        "source_case_version_id": str(version["_id"]),
        "candidate_only": True,
        "human_confirmation_required": True,
        "sensitive_values_redacted": redactions_applied,
        "suggestions": suggestions,
        "evidence_refs": list(dict.fromkeys(cited_refs)),
        **contract_metadata,
    }
    record.pop("claim_token", None)
    record.pop("lease_expires_at", None)
    return record


async def generate_execution_assistance(project_id, run_id, result_id, user):
    scope = await _execution_assistance_scope(project_id, run_id, result_id, user)
    fingerprint = scope[4]
    result = scope[1]
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
    reservation = await _claim_execution_assistance(
        project_id, result_id, fingerprint, user.id
    )
    if reservation.get("result_type") == "EXECUTION_ASSISTANCE":
        return {**reservation, "stale": False, "saved": True}
    try:
        record = await _build_execution_assistance_record(
            project_id, run_id, result_id, user, scope, reservation
        )
        record["created_at"] = now()
        persisted = await database.value.ai_results.replace_one(
            {"_id": reservation["_id"], "claim_token": reservation["claim_token"]},
            record,
        )
        if persisted.matched_count != 1:
            raise HTTPException(
                status_code=409,
                detail={"code": "EXECUTION_ASSISTANCE_RESERVATION_EXPIRED", "retryable": True},
            )
    except Exception:
        await database.value.ai_results.delete_one(
            {"_id": reservation["_id"], "claim_token": reservation["claim_token"]}
        )
        raise
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
