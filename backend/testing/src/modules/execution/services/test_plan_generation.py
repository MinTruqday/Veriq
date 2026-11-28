import logging

from fastapi import HTTPException

from src.core.ai_capabilities import ai_contract_metadata, request_ai_capability
from src.core.common import get_project, get_project_entity, plain_text
from src.modules.design.services.test_case_records import require_current_baselined_version
from src.repositories.analysis import analysis_repository

logger = logging.getLogger(__name__)


def _field_evidence_values(field, value, expected_field_values):
    """Expand a grouped citation value only when every part is a proposed value."""
    if (field, value) in expected_field_values:
        return {(field, value)}
    if field not in {"scope_out", "entry_criteria", "exit_criteria", "test_types"}:
        return set()
    parts = [part.strip() for part in str(value or "").split(",")]
    expanded = {(field, part) for part in parts if part}
    if (
        len(parts) > 1
        and len(expanded) == len(parts)
        and expanded <= expected_field_values
    ):
        return expanded
    return set()


def _append_evidence(evidence, artifact_type, artifact_id, text):
    normalized = str(text or "").strip()
    if not normalized:
        return
    for offset in range(0, len(normalized), 3800):
        chunk = normalized[offset : offset + 3800]
        evidence.append({
            "artifact_type": artifact_type,
            "artifact_id": f"{artifact_id}:{offset}",
            "text": chunk,
        })
        if len(evidence) > 100:
            raise HTTPException(413, detail={"code": "TEST_PLAN_EVIDENCE_LIMIT_EXCEEDED"})


async def generate_test_plan_suggestion(project_id, payload, user):
    await get_project(project_id, user, "testplan.read")
    await get_project(project_id, user, "ai.ask_project")
    evidence = []
    for version_id in payload.requirement_version_ids:
        version = await get_project_entity(
            "requirement_versions", version_id, user, "requirement.read"
        )
        if version.get("project_id") != project_id:
            raise HTTPException(422, detail={"code": "PROJECT_MISMATCH"})
        if version.get("status") not in {"READY", "BASELINED"}:
            raise HTTPException(409, detail={"code": "TEST_PLAN_REQUIREMENT_NOT_APPROVED"})
        await require_current_baselined_version(version)
        version_text = version.get("plain_text_projection") or plain_text(
            version.get("content_doc") or {}
        )
        _append_evidence(evidence, "requirement_version", version_id, version_text)
        criteria = await analysis_repository.list_acceptance_criteria(version_id)
        for criterion in criteria:
            _append_evidence(
                evidence,
                "acceptance_criterion",
                criterion["_id"],
                criterion.get("plain_text") or plain_text(criterion.get("content_doc") or {}),
            )

    if not evidence:
        raise HTTPException(422, detail={"code": "TEST_PLAN_REQUIREMENT_EVIDENCE_EMPTY"})

    result = await request_ai_capability(
        "test_plan_generation",
        project_id,
        payload.instruction,
        evidence,
    )
    if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
        raise HTTPException(
            503,
            detail={"code": "AI_PROVIDER_UNAVAILABLE", "retryable": True},
        )

    allowed_refs = {item["artifact_id"] for item in evidence}
    suggestion = result.get("suggestion") or {}
    if not set(result.get("evidence_refs") or []) <= allowed_refs:
        logger.warning("Test Plan AI suggestion rejected reason=AI_EVIDENCE_REF_UNKNOWN")
        raise HTTPException(502, detail={"code": "AI_EVIDENCE_REF_UNKNOWN"})
    if not set(suggestion.get("evidence_refs") or []) <= allowed_refs:
        logger.warning("Test Plan AI suggestion rejected reason=AI_EVIDENCE_REF_UNKNOWN")
        raise HTTPException(502, detail={"code": "AI_EVIDENCE_REF_UNKNOWN"})
    source_text_by_ref = {item["artifact_id"]: item["text"] for item in evidence}
    expected_field_values = set()
    if suggestion.get("objective"):
        expected_field_values.add(("objective", suggestion["objective"]))
    for field in ("scope_out", "entry_criteria", "exit_criteria", "test_types"):
        expected_field_values.update(
            (field, str(value)) for value in suggestion.get(field, []) if value
        )
    if suggestion.get("test_level"):
        expected_field_values.add(("test_level", suggestion["test_level"]))
    cited_field_values = set()
    for item in suggestion.get("field_evidence") or []:
        field_values = _field_evidence_values(
            item.get("field"), item.get("value"), expected_field_values
        )
        if not field_values:
            logger.warning(
                "Test Plan AI suggestion rejected reason=AI_PLAN_EVIDENCE_FIELD_INVALID field=%s",
                item.get("field"),
            )
            raise HTTPException(502, detail={"code": "AI_PLAN_EVIDENCE_FIELD_INVALID"})
        cited_field_values.update(field_values)
        for quote in item.get("evidence_quotes") or []:
            if (
                quote.get("evidence_ref") not in allowed_refs
                or quote.get("quote") not in source_text_by_ref.get(quote.get("evidence_ref"), "")
            ):
                logger.warning("Test Plan AI suggestion rejected reason=AI_EVIDENCE_QUOTE_INVALID")
                raise HTTPException(502, detail={"code": "AI_EVIDENCE_QUOTE_INVALID"})
    if not expected_field_values <= cited_field_values:
        logger.warning("Test Plan AI suggestion rejected reason=AI_PLAN_FIELD_EVIDENCE_MISSING")
        raise HTTPException(502, detail={"code": "AI_PLAN_FIELD_EVIDENCE_MISSING"})
    for risk in suggestion.get("risks") or []:
        if not set(risk.get("evidence_refs") or []) <= allowed_refs:
            logger.warning("Test Plan AI suggestion rejected reason=AI_EVIDENCE_REF_UNKNOWN")
            raise HTTPException(502, detail={"code": "AI_EVIDENCE_REF_UNKNOWN"})
        for quote in risk.get("evidence_quotes") or []:
            if quote.get("quote") not in source_text_by_ref.get(quote.get("evidence_ref"), ""):
                logger.warning("Test Plan AI suggestion rejected reason=AI_EVIDENCE_QUOTE_INVALID")
                raise HTTPException(502, detail={"code": "AI_EVIDENCE_QUOTE_INVALID"})

    return {
        "suggestion": suggestion,
        "evidence_refs": result.get("evidence_refs") or [],
        "unresolved_questions": suggestion.get("unresolved_questions") or [],
        "field_evidence": suggestion.get("field_evidence") or [],
        **ai_contract_metadata(result),
    }
