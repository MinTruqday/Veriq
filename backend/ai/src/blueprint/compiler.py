import hashlib

from src.core.infrastructure.configuration import settings
from src.schemas.inference_requests import (
    TESTING_AUTOMATION_MAX_EVIDENCE_ITEMS,
    TestingAutomationRequest,
)
from src.schemas.inference_requirements import (
    TESTABILITY_BLUEPRINT_MAX_CLARIFICATIONS,
    TESTABILITY_BLUEPRINT_MAX_EVIDENCE_REFS,
    TESTABILITY_BLUEPRINT_MAX_OBLIGATIONS,
    TESTABILITY_BLUEPRINT_MAX_WARNINGS,
)
from src.services.automation_provenance import source_quote_spans
from src.services.ai_automation import generate_ai_automation
from src.blueprint.source_evidence import verified_fact_evidence


async def compile_testability_blueprint(
    project_id, source_facts, evidence_by_ref, allowed_document_ids, instruction=""
):
    try:
        evidence = verified_fact_evidence(source_facts, evidence_by_ref, allowed_document_ids)
    except ValueError as error:
        return {
            "status": "DEGRADED",
            "reason_codes": [str(error)],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": [],
            "warnings": [],
        }
    if not evidence:
        return {
            "status": "DEGRADED",
            "reason_codes": ["NO_VERIFIED_BLUEPRINT_EVIDENCE"],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": [],
            "warnings": [],
        }
    batch_size = min(
        settings.AI_AGENT_MAX_EVIDENCE_ITEMS,
        TESTING_AUTOMATION_MAX_EVIDENCE_ITEMS,
    )
    if len(evidence) <= batch_size:
        return await _compile_blueprint_evidence(project_id, evidence, instruction)

    batch_results = []
    for start in range(0, len(evidence), batch_size):
        batch_index = start // batch_size
        result = await _compile_blueprint_evidence(
            project_id, evidence[start : start + batch_size], instruction
        )
        if (
            result.get("status") != "SUCCESS"
            and result.get("reason_codes") == ["BLUEPRINT_HAS_NO_TESTABILITY_OUTCOMES"]
        ):
            batch_results.append(
                {
                    **result,
                    "status": "SUCCESS",
                    "obligations": [],
                    "clarifications": [],
                    "batch_index": batch_index,
                    "warnings": list(
                        dict.fromkeys(
                            [
                                *(result.get("warnings") or []),
                                f"BATCH_{batch_index + 1}:NO_TESTABILITY_OUTCOMES",
                            ]
                        )
                    ),
                }
            )
            continue
        if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
            attempted_refs = list(
                dict.fromkeys(
                    str(item.artifact_version_id or item.artifact_id)
                    for item in evidence
                )
            )
            return {
                "status": "DEGRADED",
                "reason_codes": ["BLUEPRINT_BATCH_COMPILATION_FAILED"],
                "obligations": [],
                "clarifications": [],
                "evidence_refs": attempted_refs[:TESTABILITY_BLUEPRINT_MAX_EVIDENCE_REFS],
                "warnings": _bounded_blueprint_warnings(
                    [
                        f"BATCH_{batch_index + 1}:{code}"
                        for code in result.get("reason_codes", [])
                    ]
                ),
            }
        batch_results.append({**result, "batch_index": batch_index})

    obligations = []
    clarifications = []
    evidence_refs = []
    warnings = ["BLUEPRINT_COMPILED_IN_EVIDENCE_BATCHES"]
    obligation_keys_by_identity = {}
    for batch in batch_results:
        batch_index = batch["batch_index"]
        prefix = f"B{batch_index + 1:03d}-"
        batch_key_map = {}
        for item in batch.get("obligations", []):
            identity = (
                str(item.get("source_ref") or ""),
                str(item.get("source_quote") or ""),
                " ".join(str(item.get("obligation") or "").split()).casefold(),
            )
            existing_key = obligation_keys_by_identity.get(identity)
            source_key = str(item.get("key") or "")
            if existing_key:
                batch_key_map[source_key] = existing_key
                continue
            namespaced_key = _namespaced_blueprint_key(prefix, source_key)
            batch_key_map[source_key] = namespaced_key
            obligation_keys_by_identity[identity] = namespaced_key
            obligations.append({**item, "key": namespaced_key})

        for item in batch.get("clarifications", []):
            source_code = str(item.get("code") or "")
            namespaced_code = _namespaced_blueprint_key(prefix, source_code)
            unlocks = [
                batch_key_map.get(str(key), _namespaced_blueprint_key(prefix, str(key)))
                for key in item.get("unlocks_obligation_keys", [])
            ]
            clarifications.append(
                {
                    **item,
                    "code": namespaced_code,
                    "unlocks_obligation_keys": list(dict.fromkeys(unlocks)),
                }
            )
        evidence_refs.extend(map(str, batch.get("evidence_refs", [])))
        warnings.extend(batch.get("warnings", []))

    if not obligations and not clarifications:
        evidence_refs = list(dict.fromkeys(evidence_refs))
        return {
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_HAS_NO_TESTABILITY_OUTCOMES"],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": evidence_refs[:TESTABILITY_BLUEPRINT_MAX_EVIDENCE_REFS],
            "warnings": _bounded_blueprint_warnings(warnings),
        }

    evidence_refs = list(dict.fromkeys(evidence_refs))
    if (
        len(obligations) > TESTABILITY_BLUEPRINT_MAX_OBLIGATIONS
        or len(clarifications) > TESTABILITY_BLUEPRINT_MAX_CLARIFICATIONS
        or len(evidence_refs) > TESTABILITY_BLUEPRINT_MAX_EVIDENCE_REFS
    ):
        return {
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_AGGREGATED_OUTPUT_LIMIT_EXCEEDED"],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": evidence_refs[:TESTABILITY_BLUEPRINT_MAX_EVIDENCE_REFS],
            "warnings": _bounded_blueprint_warnings(warnings),
        }

    return {
        "status": "SUCCESS",
        "degraded_mode": None,
        "obligations": obligations,
        "clarifications": clarifications,
        "evidence_refs": evidence_refs,
        "confidence": min(
            (float(batch.get("confidence", 0)) for batch in batch_results),
            default=0.0,
        ),
        "warnings": _bounded_blueprint_warnings(warnings),
    }


def _bounded_blueprint_warnings(warnings):
    unique = list(dict.fromkeys(str(item) for item in warnings if item))
    if len(unique) <= TESTABILITY_BLUEPRINT_MAX_WARNINGS:
        return unique
    retained = unique[: TESTABILITY_BLUEPRINT_MAX_WARNINGS - 1]
    retained.append(f"{len(unique) - len(retained)} cảnh báo bổ sung đã được gộp")
    return retained


def _namespaced_blueprint_key(prefix, value):
    value = str(value or "")
    if len(prefix) + len(value) <= 160:
        return f"{prefix}{value}"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    available = max(1, 160 - len(prefix) - len(digest) - 1)
    return f"{prefix}{value[:available]}-{digest}"


async def _compile_blueprint_evidence(project_id, evidence, instruction=""):
    if not evidence:
        return {
            "status": "DEGRADED",
            "reason_codes": ["NO_VERIFIED_BLUEPRINT_EVIDENCE"],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": [],
            "warnings": [],
        }

    request = TestingAutomationRequest(
        capability="testability_blueprint_compilation",
        project_id=project_id,
        instruction=instruction,
        evidence=evidence,
    )
    try:
        result = await generate_ai_automation(request)
    except Exception as error:
        return {
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_MODEL_CALL_FAILED"],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": [
                str(item.artifact_version_id or item.artifact_id) for item in evidence
            ],
            "warnings": [type(error).__name__],
        }
    output = result.model_dump(mode="json")
    if output.get("status") != "SUCCESS" or output.get("degraded_mode"):
        return output

    if not output.get("obligations") and not output.get("clarifications"):
        return {
            **output,
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_HAS_NO_TESTABILITY_OUTCOMES"],
            "warnings": list(
                dict.fromkeys(
                    [
                        *(output.get("warnings") or []),
                        "Không tạo nghĩa vụ kiểm thử hoặc câu hỏi làm rõ từ nguồn đã xác minh",
                    ]
                )
            ),
        }

    source_text_by_ref = {
        str(item.artifact_version_id or item.artifact_id): "\n".join(
            value.text
            for value in evidence
            if str(value.artifact_version_id or value.artifact_id)
            == str(item.artifact_version_id or item.artifact_id)
        )
        for item in evidence
    }
    allowed_refs = set(source_text_by_ref)
    verified_fact_quotes_by_ref = {
        reference: [
            fact.quote
            for item in evidence
            if str(item.artifact_version_id or item.artifact_id) == reference
            for fact in item.verified_facts
        ]
        for reference in source_text_by_ref
    }
    if not set(output.get("evidence_refs", [])) <= allowed_refs:
        return {
            **output,
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_EVIDENCE_REFERENCE_INVALID"],
            "obligations": [],
            "clarifications": [],
        }

    declared_refs = set(output.get("evidence_refs", []))
    used_refs = {
        str(item.get("source_ref") or "")
        for item in output.get("obligations", [])
    }
    used_refs.update(
        str(reference)
        for item in output.get("clarifications", [])
        for reference in item.get("evidence_refs", [])
    )
    if not used_refs <= declared_refs:
        return {
            **output,
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_EVIDENCE_REFERENCE_INCOMPLETE"],
            "obligations": [],
            "clarifications": [],
        }

    for obligation in output.get("obligations", []):
        reference = str(obligation.get("source_ref") or "")
        quote = str(obligation.get("source_quote") or "").strip()
        if (
            reference not in allowed_refs
            or not quote
            or not source_quote_spans(source_text_by_ref[reference], quote)
            or not any(
                source_quote_spans(fact_quote, quote)
                for fact_quote in verified_fact_quotes_by_ref.get(reference, [])
            )
        ):
            return {
                **output,
                "status": "DEGRADED",
                "reason_codes": ["BLUEPRINT_OBLIGATION_GROUNDING_INVALID"],
                "obligations": [],
                "clarifications": [],
            }

    for clarification in output.get("clarifications", []):
        references = set(clarification.get("evidence_refs", []))
        quote = str(clarification.get("source_quote") or "").strip()
        reason = str(clarification.get("reason") or "").strip()
        if len(reason) < 2:
            return {
                **output,
                "status": "DEGRADED",
                "reason_codes": ["BLUEPRINT_CLARIFICATION_REASON_MISSING"],
                "obligations": [],
                "clarifications": [],
            }
        if (
            not references
            or not references <= allowed_refs
            or not quote
            or not any(
                source_quote_spans(source_text_by_ref[reference], quote)
                for reference in references
            )
            or not any(
                source_quote_spans(fact_quote, quote)
                for reference in references
                for fact_quote in verified_fact_quotes_by_ref.get(reference, [])
            )
        ):
            return {
                **output,
                "status": "DEGRADED",
                "reason_codes": ["BLUEPRINT_CLARIFICATION_GROUNDING_INVALID"],
                "obligations": [],
                "clarifications": [],
            }

    return output
