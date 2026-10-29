import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from loguru import logger

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.observability import trace_span
from src.core.security.guardrails import guardrails_engine
from src.prompts.test_case_grounding import build_generated_cases_grounding_prompt
from src.prompts.testability_blueprint_review import build_testability_blueprint_grounding_prompt
from src.prompts.testing import (
    build_testing_prompt,
    prompt_contract_fingerprint,
    prompt_messages_fingerprint,
)
from src.runtime.output import normalize_narrative_payload
from src.schemas.inference import output_schema
from src.schemas.inference_requests import (
    TestingAutomationDegradedMode,
    TestingAutomationRequest,
    TestingAutomationResult,
    TestingAutomationStatus,
)
from src.schemas.inference_requirements import TestabilityBlueprintGroundingReview
from src.schemas.inference_test_design import GeneratedCasesGroundingReview
from src.services.automation_provenance import source_quote_spans
from src.services.inference import model_metadata, structured


def evidence_text(evidence, compact=False):
    values = []
    for item in evidence:
        reference = item.get("artifact_version_id") or item.get("artifact_id")
        if compact:
            values.append(f"[{reference}] {str(item.get('text', ''))[:4000]}")
            continue
        metadata = {
            key: item.get(key)
            for key in (
                "artifact_type",
                "artifact_id",
                "artifact_version_id",
                "source_version",
                "relationship_paths",
                "authority",
            )
            if item.get(key) is not None
        }
        if item.get("verified_facts"):
            metadata["verified_facts"] = item["verified_facts"]
        values.extend(
            (json.dumps(metadata, ensure_ascii=False, default=str), str(item.get("text", ""))[:4000])
        )
    return "\n".join(values)


def evidence_payload(evidence):
    return [
        {
            "artifact_type": item.artifact_type,
            "artifact_id": item.artifact_id,
            "artifact_version_id": item.artifact_version_id,
            "source_version": item.source_version,
            "relationship_paths": item.relationship_paths,
            "authority": item.authority,
            "verified_facts": [
                fact.model_dump(mode="json") for fact in item.verified_facts
            ],
            "text": item.text,
        }
        for item in evidence
    ]


def evidence_reference_ids(evidence):
    return [
        str(item.get("artifact_version_id") or item.get("artifact_id"))
        for item in evidence
        if item.get("artifact_version_id") or item.get("artifact_id")
    ]


def nested_values(value, key_name):
    values = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == key_name and isinstance(item, list):
                values.extend(str(entry) for entry in item)
            else:
                values.extend(nested_values(item, key_name))
    elif isinstance(value, list):
        for item in value:
            values.extend(nested_values(item, key_name))
    return values


def performance_targets_have_evidence(suggestions, evidence):
    source_text = {
        str(item.get("artifact_version_id") or item.get("artifact_id")): str(
            item.get("text") or ""
        )
        for item in evidence
        if item.get("artifact_version_id") or item.get("artifact_id")
    }
    for suggestion in suggestions:
        quotes = suggestion.get("evidence_quotes") or []
        valid_quotes = [
            quote
            for quote in quotes
            if quote.get("evidence_ref") in source_text
            and quote.get("quote", "").strip()
            and source_quote_spans(
                source_text[quote["evidence_ref"]], quote["quote"].strip()
            )
        ]
        if not valid_quotes:
            return False
        for field in ("virtual_users", "requests_per_second", "duration_minutes"):
            value = suggestion.get(field)
            if value is None:
                continue
            try:
                expected = Decimal(format(float(value), ".15g"))
            except (InvalidOperation, TypeError, ValueError):
                return False
            supported = False
            for quote in valid_quotes:
                tokens = re.findall(
                    r"(?<![\w])[+-]?\d+(?:[.,]\d+)*(?![\w])", quote["quote"]
                )
                for token in tokens:
                    try:
                        token_value = Decimal(token.replace(",", "."))
                    except InvalidOperation:
                        continue
                    if token_value == expected:
                        supported = True
                        break
                if supported:
                    break
            if not supported:
                return False
    return True


def generated_cases_have_grounded_citations(cases, evidence):
    source_text = {
        str(item.get("artifact_version_id") or item.get("artifact_id")): str(
            item.get("text") or ""
        )
        for item in evidence
        if item.get("artifact_version_id") or item.get("artifact_id")
    }
    for case in cases:
        evidence_refs = set(case.get("evidence_refs") or [])
        quotes = case.get("evidence_quotes") or []
        if not quotes:
            return False
        valid_quotes = []
        for item in quotes:
            reference = item.get("evidence_ref")
            quote = str(item.get("quote") or "").strip()
            if (
                reference not in evidence_refs
                or reference not in source_text
                or not quote
                or not source_quote_spans(source_text[reference], quote)
            ):
                return False
            valid_quotes.append(quote.casefold())
        quoted_text = " ".join(valid_quotes)
        if any(
            not source_quote_spans(quoted_text, str(skill).strip().casefold())
            for skill in case.get("required_skills") or []
        ):
            return False
    return True


async def generate_ai_automation(req: TestingAutomationRequest):
    with trace_span(
        "ai.testing_automation",
        {
            "project.id": req.project_id,
            "ai.capability": req.capability,
            "ai.evidence_count": len(req.evidence),
        },
    ) as span:
        result = await _generate_ai_automation(req)
        if span is not None:
            span.set_attribute("ai.result.status", str(result.status))
        return result


async def _generate_ai_automation(req: TestingAutomationRequest):
    evidence = evidence_payload(req.evidence)
    source_text = evidence_text(
        evidence,
        compact=req.capability in {"project_question", "requirement_quality_analysis"},
    )
    inspected = await guardrails_engine.async_inspect_input(
        "\n".join(str(item.get("text", ""))[:4000] for item in evidence)
    )
    if not inspected.get("is_safe", False):
        raise HTTPException(status_code=422, detail={"code": "qa_evidence_unsafe"})
    allowed_evidence_refs = evidence_reference_ids(evidence)
    schema = output_schema(req.capability)
    prompt = build_testing_prompt(
        req.capability,
        req.project_id,
        req.instruction,
        source_text,
        allowed_evidence_refs,
        schema,
        req.output_language,
    )
    model = {
        **model_metadata(),
        "prompt_version": prompt_contract_fingerprint(req.capability, schema),
        "prompt_execution_fingerprints": [],
        "prompt_execution_attempts": [],
        "tool_schema_version": "ai_automation",
        "retrieval_version": "project_evidence",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    def observe_prompt_attempt(stage):
        def record(messages, attempt):
            fingerprint = prompt_messages_fingerprint(messages)
            model["prompt_execution_fingerprints"].append(fingerprint)
            model["prompt_execution_attempts"].append(
                {"stage": stage, "attempt": attempt, "fingerprint": fingerprint}
            )

        return record

    unsupported_details = []
    try:
        with trace_span(
            "ai.model_generation",
            {"ai.capability": req.capability},
        ):
            generated = await structured(
                prompt,
                schema,
                max_tokens=4096,
                timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
                provider_schema=False,
                prompt_attempt_observer=observe_prompt_attempt("generation"),
            )
        generated_data = normalize_narrative_payload(generated.model_dump())
        generated_data["capability"] = req.capability
        generated_data.setdefault("confidence", 0)
        generated_data.setdefault("warnings", [])
        unknown_refs = sorted(
            set(nested_values(generated_data, "evidence_refs")) - set(allowed_evidence_refs)
        )
        if unknown_refs:
            raise ValueError("AI_EVIDENCE_REF_UNKNOWN")
        if req.capability == "performance_plan_generation" and not (
            performance_targets_have_evidence(generated_data.get("suggestions", []), evidence)
        ):
            raise ValueError("AI_PERFORMANCE_TARGET_EVIDENCE_INVALID")
        if req.capability == "test_generation" and generated_data.get("suggestions"):
            cases = generated_data["suggestions"]
            if not generated_cases_have_grounded_citations(cases, evidence):
                raise ValueError("AI_TEST_CASE_CITATION_INVALID")
            grounding_prompt = build_generated_cases_grounding_prompt(evidence, cases)
            with trace_span(
                "ai.grounding_review",
                {"ai.review_type": "test_case", "ai.candidate_count": len(cases)},
            ):
                review = await structured(
                    grounding_prompt,
                    GeneratedCasesGroundingReview,
                    max_tokens=4096,
                    timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
                    provider_schema=False,
                    prompt_attempt_observer=observe_prompt_attempt("grounding"),
                )
            if [item.index for item in review.cases] != list(range(len(cases))):
                raise ValueError("AI_GROUNDING_REVIEW_INVALID")
            unsupported = [item for item in review.cases if item.unsupported_claims]
            if unsupported:
                unsupported_details = [
                    {
                        "case_index": item.index,
                        "unsupported_claims": item.unsupported_claims[:10],
                    }
                    for item in unsupported
                ]
                logger.warning(
                    "AI generated cases rejected as ungrounded count={} indices={}",
                    len(unsupported),
                    [item.index for item in unsupported],
                )
                rejected = {item.index for item in unsupported}
                generated_data["suggestions"] = [
                    case for index, case in enumerate(cases) if index not in rejected
                ]
                if not generated_data["suggestions"]:
                    raise ValueError("AI_UNGROUNDED_OUTPUT")
                generated_data["findings"] = unsupported_details
                generated_data["warnings"] = [
                    *generated_data.get("warnings", []),
                    "AI_UNGROUNDED_CANDIDATES_REJECTED",
                ]
        if req.capability == "testability_blueprint_compilation" and (
            generated_data.get("obligations") or generated_data.get("clarifications")
        ):
            review_prompt = build_testability_blueprint_grounding_prompt(
                evidence,
                generated_data.get("obligations", []),
                generated_data.get("clarifications", []),
            )
            with trace_span(
                "ai.grounding_review",
                {
                    "ai.review_type": "testability_blueprint",
                    "ai.obligation_count": len(generated_data.get("obligations", [])),
                    "ai.clarification_count": len(generated_data.get("clarifications", [])),
                },
            ):
                review = await structured(
                    review_prompt,
                    TestabilityBlueprintGroundingReview,
                    max_tokens=4096,
                    timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
                    provider_schema=False,
                    prompt_attempt_observer=observe_prompt_attempt("blueprint_grounding"),
                )
            expected_obligation_indexes = list(range(len(generated_data.get("obligations", []))))
            expected_clarification_indexes = list(range(len(generated_data.get("clarifications", []))))
            if (
                [item.index for item in review.obligations] != expected_obligation_indexes
                or [item.index for item in review.clarifications] != expected_clarification_indexes
            ):
                raise ValueError("AI_BLUEPRINT_GROUNDING_REVIEW_INVALID")
            rejected_obligation_indexes = {
                item.index for item in review.obligations if item.unsupported_claims
            }
            rejected_clarification_indexes = {
                item.index for item in review.clarifications if item.unsupported_claims
            }
            rejected_obligation_keys = {
                generated_data["obligations"][index]["key"]
                for index in rejected_obligation_indexes
            }
            rejected_claims = [
                {
                    "claim_type": claim_type,
                    "index": item.index,
                    "unsupported_claims": item.unsupported_claims[:10],
                }
                for claim_type, items in (
                    ("OBLIGATION", review.obligations),
                    ("CLARIFICATION", review.clarifications),
                )
                for item in items
                if item.unsupported_claims
            ]
            retained_obligations = [
                item
                for index, item in enumerate(generated_data.get("obligations", []))
                if index not in rejected_obligation_indexes
            ]
            retained_clarifications = [
                item
                for index, item in enumerate(generated_data.get("clarifications", []))
                if index not in rejected_clarification_indexes
                and not set(item.get("unlocks_obligation_keys", []))
                & rejected_obligation_keys
            ]
            if rejected_claims and (retained_obligations or retained_clarifications):
                generated_data["obligations"] = retained_obligations
                generated_data["clarifications"] = retained_clarifications
                generated_data["findings"] = [
                    *generated_data.get("findings", []),
                    *rejected_claims[:100],
                ]
                generated_data["warnings"] = list(
                    dict.fromkeys(
                        [
                            *generated_data.get("warnings", []),
                            "AI_UNGROUNDED_CANDIDATES_REJECTED",
                        ]
                    )
                )
                retained_refs = {
                    str(item.get("source_ref") or "")
                    for item in retained_obligations
                }
                retained_refs.update(
                    str(reference)
                    for item in retained_clarifications
                    for reference in item.get("evidence_refs", [])
                )
                generated_data["evidence_refs"] = [
                    reference
                    for reference in generated_data.get("evidence_refs", [])
                    if reference in retained_refs
                ]
            elif rejected_claims:
                unsupported_details = rejected_claims[:100]
                raise ValueError("AI_BLUEPRINT_UNGROUNDED_OUTPUT")
        if req.capability == "test_condition_generation":
            generated_data["suggestions"] = generated_data.pop("condition_candidates")
        generated_data.update(
            {
                "status": TestingAutomationStatus.SUCCESS,
                "degraded_mode": None,
                "provider": model["provider"],
                "model": model,
                "prompt_version": model["prompt_version"],
                "tool_schema_version": model["tool_schema_version"],
                "retrieval_version": model["retrieval_version"],
                "created_at": model["created_at"],
            }
        )
        result = TestingAutomationResult(**generated_data)
    except Exception as error:
        error_message = str(error)
        output_invalid = type(error).__name__ in {
            "StructuredOutputError",
            "ValidationError",
            "ValueError",
        }
        failure_code = (
            "AI_UNGROUNDED_OUTPUT"
            if error_message in {"AI_UNGROUNDED_OUTPUT", "AI_BLUEPRINT_UNGROUNDED_OUTPUT"}
            else "AI_TEST_CASE_CITATION_INVALID"
            if error_message == "AI_TEST_CASE_CITATION_INVALID"
            else "AI_GROUNDING_REVIEW_INVALID"
            if error_message == "AI_BLUEPRINT_GROUNDING_REVIEW_INVALID"
            else "AI_OUTPUT_INVALID" if output_invalid else "AI_PROVIDER_UNAVAILABLE"
        )
        logger.warning(
            "AI automation result rejected capability={} error_type={} error_code={}",
            req.capability,
            type(error).__name__,
            failure_code,
        )
        degraded_mode = (
            TestingAutomationDegradedMode.OUTPUT
            if output_invalid
            else TestingAutomationDegradedMode.PROVIDER
        )
        provider = model["provider"] if output_invalid else "unavailable"
        answer = (
            "Đầu ra của mô hình không đáp ứng hợp đồng dữ liệu yêu cầu"
            if output_invalid
            else "Chưa thể tạo kết quả có căn cứ vì dịch vụ AI hiện không khả dụng"
        )
        result = TestingAutomationResult(
            capability=req.capability,
            suggestions=[],
            findings=unsupported_details
            if failure_code
            in {
                "AI_UNGROUNDED_OUTPUT",
                "AI_BLUEPRINT_UNGROUNDED_OUTPUT",
                "AI_GROUNDING_REVIEW_INVALID",
            }
            else [],
            evidence_refs=evidence_reference_ids(evidence),
            confidence=0,
            warnings=[failure_code, "MANUAL_REVIEW_REQUIRED"],
            status=TestingAutomationStatus.DEGRADED,
            degraded_mode=degraded_mode,
            provider=provider,
            model={**model, "provider": provider},
            prompt_version=model["prompt_version"],
            tool_schema_version=model["tool_schema_version"],
            retrieval_version=model["retrieval_version"],
            created_at=model["created_at"],
            reason_codes=[failure_code, "MANUAL_REVIEW_REQUIRED"],
            answer=answer,
        )
    if result.capability != req.capability:
        raise HTTPException(status_code=502, detail={"code": "qa_capability_mismatch"})
    if not result.reason_codes:
        result.reason_codes = (
            nested_values(result.model_dump(), "reason_codes")[:100]
            or [
                str(item.get("reason_code") or item.get("action") or "EVIDENCE_REVIEW")
                for item in result.suggestions
            ][:100]
        )
    result.workflow = {
        "request_id": f"qa-{datetime.now(timezone.utc).timestamp()}",
        "project_id": req.project_id,
        "intent": req.capability,
        "phases": [
            "OBSERVE_EVIDENCE",
            "REASON_AND_PLAN",
            "ACT_VALIDATE_PROPOSAL",
            "OBSERVE_VALIDATION",
        ],
        "evidence_count": len(evidence),
        "candidate_count": len(result.suggestions) + len(result.new_test_candidates),
        "confidence": result.confidence,
        "degraded_flags": (
            result.warnings if result.status == TestingAutomationStatus.DEGRADED else []
        ),
        "hidden_reasoning_stored": False,
    }
    return result
