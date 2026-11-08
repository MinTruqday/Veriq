import hashlib
import json
from datetime import timedelta

from fastapi import HTTPException
from shared.completeness import COMPLETENESS_AREAS

from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.core.common import audit, get_project, now
from src.core.database import database
from src.modules.projects.services.project_complexity import (
    _claim_project_complexity_request,
    _fingerprint,
    _source_scope,
    get_project_complexity_scope,
)

RESULT_TYPE = "PROJECT_COMPLETENESS_REVIEW"
BATCH_SIZE = 60
MAXIMUM_CHUNKS = 1200
def _fail(code, status=409, **details):
    raise HTTPException(status_code=status, detail={"code": code, **details})


async def get_project_completeness_scope(project_id, user):
    return await get_project_complexity_scope(project_id, user)


async def _scope(project_id, user, selection):
    scope = await _source_scope(
        project_id,
        user,
        include_text=True,
        document_ids=selection["document_ids"],
        requirement_version_ids=selection["requirement_version_ids"],
        include_documents=bool(selection["document_ids"]),
    )
    scope["fingerprint"] = _fingerprint({
        "manifest": scope["manifest"],
        "evidence": [
            {
                "ref": item["artifact_version_id"],
                "hash": hashlib.sha256(item["text"].encode("utf-8")).hexdigest(),
            }
            for item in scope["evidence"]
        ],
    })
    return scope


def _validated_batch(result, evidence):
    if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
        _fail("AI_PROVIDER_UNAVAILABLE", 503, retryable=True)
    suggestions = result.get("suggestions") or []
    if len(suggestions) != 1:
        _fail("PROJECT_COMPLETENESS_OUTPUT_INVALID", 502)
    suggestion = suggestions[0]
    coverage = suggestion.get("coverage") or []
    if len(coverage) != len(COMPLETENESS_AREAS) or {
        item.get("area") for item in coverage
    } != set(COMPLETENESS_AREAS):
        _fail("PROJECT_COMPLETENESS_COVERAGE_INVALID", 502)
    sources = {item["artifact_version_id"]: item for item in evidence}
    citations = []
    for item in [*coverage, *(suggestion.get("findings") or [])]:
        quotes = item.get("evidence_quotes") or []
        if item in coverage:
            if item.get("status") != "NEEDS_CONFIRMATION" and not quotes:
                _fail("PROJECT_COMPLETENESS_GROUNDING_REQUIRED", 502)
        elif not quotes:
            _fail("PROJECT_COMPLETENESS_GROUNDING_REQUIRED", 502)
        if item.get("kind") == "POTENTIAL_CONFLICT" and len(quotes) < 2:
            _fail("PROJECT_COMPLETENESS_CONFLICT_UNGROUNDED", 502)
        for quote in quotes:
            source = sources.get(quote.get("evidence_ref"))
            text = str(quote.get("quote") or "").strip()
            if not source or not text or text not in source["text"]:
                _fail("PROJECT_COMPLETENESS_QUOTE_INVALID", 502)
            citations.append({
                "evidence_ref": quote["evidence_ref"],
                "artifact_type": source["artifact_type"],
                "artifact_id": source["artifact_id"],
                "source_version": source.get("source_version"),
                "quote": text,
            })
    return {"suggestion": suggestion, "citations": citations, "model": ai_contract_metadata(result)}


def _response(record, stale=False):
    if stale:
        return {
            "_id": record["_id"], "stale": True, "status": "SOURCES_CHANGED",
            "saved": True, "approved": False, "suggestions": [], "citations": [],
        }
    hidden = {
        "source_manifest", "claim_token", "lease_expires_at", "request_fingerprint",
        "idempotency_key", "batch_results", "last_error_code",
    }
    return {
        **{key: value for key, value in record.items() if key not in hidden},
        "stale": False, "saved": True, "approved": False,
    }


async def _renew(reservation):
    result = await database.value.ai_results.update_one(
        {"_id": reservation["_id"], "claim_token": reservation["claim_token"], "result_type": f"{RESULT_TYPE}_PENDING"},
        {"$set": {"lease_expires_at": now() + timedelta(minutes=35), "updated_at": now()}},
    )
    if result.matched_count != 1:
        _fail("PROJECT_COMPLETENESS_RESERVATION_EXPIRED", retryable=True)


async def review_project_completeness(project_id, user, payload):
    project = await get_project(project_id, user, "ai.ask_project")
    locale = payload.output_language or project.get("locale")
    if not locale:
        _fail("PROJECT_OUTPUT_LOCALE_REQUIRED")
    selection = {
        "document_ids": payload.document_ids,
        "requirement_version_ids": payload.requirement_version_ids,
    }
    scope = await _scope(project_id, user, selection)
    evidence = scope["evidence"]
    if len(evidence) > MAXIMUM_CHUNKS:
        _fail("PROJECT_COMPLETENESS_SCOPE_TOO_LARGE", 422, evidence_chunks=len(evidence), maximum=MAXIMUM_CHUNKS)
    context = {
        "stage": payload.stage,
        "in_scope": payload.scope_description,
        "out_of_scope": payload.out_of_scope,
        "user_instruction": payload.instruction,
        "selected_source_count": len(scope["manifest"]),
        "extraction_gaps": scope["extraction_gaps"],
    }
    reservation_payload = payload.model_copy(update={"idempotency_key": f"completeness:{payload.idempotency_key}"})
    reservation, replay = await _claim_project_complexity_request(
        project_id, user, reservation_payload, scope["fingerprint"], locale,
        result_type=RESULT_TYPE, request_context=context,
    )
    if replay:
        latest = await _scope(project_id, user, selection)
        return _response(replay, latest["fingerprint"] != scope["fingerprint"])
    batches = [evidence[index:index + BATCH_SIZE] for index in range(0, len(evidence), BATCH_SIZE)]
    completed = dict(reservation.get("batch_results") or {})
    try:
        for index, batch in enumerate(batches):
            batch_fingerprint = _fingerprint([item["artifact_version_id"] for item in batch])
            cached = completed.get(str(index))
            if cached and cached.get("input_fingerprint") == batch_fingerprint:
                continue
            await _renew(reservation)
            current = await _scope(project_id, user, selection)
            if current["fingerprint"] != scope["fingerprint"]:
                _fail("PROJECT_COMPLETENESS_SOURCES_CHANGED", retryable=True)
            instruction = json.dumps({
                **context,
                "batch": {"index": index + 1, "total": len(batches), "reviewed_chunks": len(batch), "selected_chunks": len(evidence)},
            }, ensure_ascii=False)
            if len(instruction) > 5000:
                _fail("PROJECT_COMPLETENESS_CONTEXT_TOO_LARGE", 422)
            result = await request_ai_automation(
                "project_completeness_review", project_id, instruction, batch,
                output_language=locale,
            )
            saved = {"input_fingerprint": batch_fingerprint, **_validated_batch(result, batch)}
            write = await database.value.ai_results.update_one(
                {"_id": reservation["_id"], "claim_token": reservation["claim_token"], "result_type": f"{RESULT_TYPE}_PENDING"},
                {"$set": {f"batch_results.{index}": saved, "updated_at": now(), "lease_expires_at": now() + timedelta(minutes=35)}},
            )
            if write.matched_count != 1:
                _fail("PROJECT_COMPLETENESS_RESERVATION_EXPIRED", retryable=True)
            completed[str(index)] = saved
        latest = await _scope(project_id, user, selection)
        if latest["fingerprint"] != scope["fingerprint"]:
            _fail("PROJECT_COMPLETENESS_SOURCES_CHANGED", retryable=True)
        suggestions = []
        citations = []
        for index in range(len(batches)):
            item = completed[str(index)]
            suggestions.append({"batch_index": index + 1, **item["suggestion"]})
            citations.extend(item["citations"])
        citations = list({(item["evidence_ref"], item["quote"]): item for item in citations}.values())
        limitations = []
        if len(batches) > 1:
            limitations.append("CROSS_BATCH_FINDINGS_REQUIRE_CONFIRMATION")
        if scope["extraction_gaps"]:
            limitations.append("SOURCE_READING_GAPS")
        record = {
            **reservation,
            "result_type": RESULT_TYPE,
            "status": "INSUFFICIENT_EVIDENCE" if not evidence else "SELECTED_SCOPE_REVIEWED",
            "candidate_only": True,
            "human_confirmation_required": True,
            "source_manifest": scope["manifest"],
            "source_selection": selection,
            "source_fingerprint": scope["fingerprint"],
            "review_context": context,
            "output_language": locale,
            "suggestions": suggestions,
            "citations": citations,
            "scope_summary": {
                "document_count": scope["document_count"],
                "requirement_count": scope["requirement_count"],
                "selected_chunk_count": len(evidence),
                "processed_chunk_count": sum(len(batch) for batch in batches),
                "batch_count": len(batches),
                "excluded_sources": scope["excluded"],
                "extraction_gaps": scope["extraction_gaps"],
                "entire_project_reviewed": False,
                "cross_batch_comparison_complete": len(batches) <= 1,
            },
            "limitations": limitations,
            "created_at": now(),
            "updated_at": now(),
        }
        for field in ("lease_expires_at", "last_error_code", "batch_results"):
            record.pop(field, None)
        persisted = await database.value.ai_results.replace_one(
            {"_id": reservation["_id"], "claim_token": reservation["claim_token"], "result_type": f"{RESULT_TYPE}_PENDING"},
            record,
        )
        if persisted.matched_count != 1:
            _fail("PROJECT_COMPLETENESS_RESERVATION_EXPIRED", retryable=True)
    except Exception as error:
        code = error.detail.get("code") if isinstance(error, HTTPException) and isinstance(error.detail, dict) else "PROJECT_COMPLETENESS_REVIEW_FAILED"
        await database.value.ai_results.update_one(
            {"_id": reservation["_id"], "claim_token": reservation["claim_token"], "result_type": f"{RESULT_TYPE}_PENDING"},
            {"$set": {"last_error_code": code, "lease_expires_at": now(), "updated_at": now()}},
        )
        raise
    await audit(user.id, "project_completeness_reviewed", "Project", project_id, project_id, {"result_id": record["_id"], "source_chunks": len(evidence), "batch_count": len(batches)})
    return _response(record)


async def get_latest_project_completeness(project_id, user):
    await get_project(project_id, user, "ai.ask_project")
    record = await database.value.ai_results.find_one(
        {"project_id": project_id, "created_by": user.id, "result_type": RESULT_TYPE},
        sort=[("created_at", -1)],
    )
    if not record:
        return None
    try:
        scope = await _scope(project_id, user, record["source_selection"])
    except HTTPException as error:
        if error.status_code not in {403, 409}:
            raise
        return _response(record, True)
    return _response(record, scope["fingerprint"] != record.get("source_fingerprint"))
