import json
from datetime import datetime, timezone

from fastapi import HTTPException
from loguru import logger

from src.core.infrastructure.configuration import settings
from src.core.security.guardrails import guardrails_engine
from src.prompts.testing import build_generated_cases_grounding_prompt, build_testing_prompt
from src.runtime.output import normalize_narrative_payload
from src.schemas.inference import (
    TestingAssistanceRequest,
    GeneratedCasesGroundingReview,
    TestingAssistanceDegradedMode,
    TestingAssistanceResult,
    TestingAssistanceStatus,
    output_schema,
)
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
            for key in ("artifact_type", "artifact_id", "artifact_version_id", "authority")
            if item.get(key) is not None
        }
        values.extend(
            (json.dumps(metadata, ensure_ascii=False, default=str), str(item.get("text", ""))[:4000])
        )
    return "\n".join(values)


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


async def generate_ai_assistance(req: TestingAssistanceRequest):
    evidence = [
        {
            "artifact_type": item.artifact_type,
            "artifact_id": item.artifact_id,
            "artifact_version_id": item.artifact_version_id,
            "authority": item.authority,
            "text": item.text,
        }
        for item in req.evidence
    ]
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
    )
    model = {
        **model_metadata(),
        "prompt_version": "ai_assistance_v3_multilingual_few_shot",
        "tool_schema_version": "ai_assistance",
        "retrieval_version": "project_evidence",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        generated = await structured(
            prompt,
            schema,
            max_tokens=4096,
            timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
            provider_schema=False,
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
        if req.capability == "test_generation" and generated_data.get("suggestions"):
            cases = generated_data["suggestions"]
            review = await structured(
                build_generated_cases_grounding_prompt(evidence, cases),
                GeneratedCasesGroundingReview,
                max_tokens=4096,
                timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
                provider_schema=False,
            )
            if [item.index for item in review.cases] != list(range(len(cases))):
                raise ValueError("AI_GROUNDING_REVIEW_INVALID")
            unsupported = [item for item in review.cases if item.unsupported_claims]
            if unsupported:
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
        if req.capability == "test_condition_generation":
            generated_data["suggestions"] = generated_data.pop("condition_candidates")
        generated_data.update(
            {
                "status": TestingAssistanceStatus.SUCCESS,
                "degraded_mode": None,
                "provider": model["provider"],
                "model": model,
                "prompt_version": model["prompt_version"],
                "tool_schema_version": model["tool_schema_version"],
                "retrieval_version": model["retrieval_version"],
                "created_at": model["created_at"],
            }
        )
        result = TestingAssistanceResult(**generated_data)
    except Exception as error:
        logger.warning(
            "AI assistance result rejected capability={} error_type={} error={}",
            req.capability,
            type(error).__name__,
            str(error),
        )
        output_invalid = type(error).__name__ in {
            "StructuredOutputError",
            "ValidationError",
            "ValueError",
        }
        failure_code = (
            "AI_UNGROUNDED_OUTPUT"
            if str(error) == "AI_UNGROUNDED_OUTPUT"
            else "AI_OUTPUT_INVALID" if output_invalid else "AI_PROVIDER_UNAVAILABLE"
        )
        degraded_mode = (
            TestingAssistanceDegradedMode.OUTPUT
            if output_invalid
            else TestingAssistanceDegradedMode.PROVIDER
        )
        provider = model["provider"] if output_invalid else "unavailable"
        answer = (
            "The model output did not satisfy the required response contract"
            if output_invalid
            else "An evidence grounded answer cannot be produced while the AI provider is unavailable"
        )
        result = TestingAssistanceResult(
            capability=req.capability,
            suggestions=[],
            evidence_refs=evidence_reference_ids(evidence),
            confidence=0,
            warnings=[failure_code, "MANUAL_REVIEW_REQUIRED"],
            status=TestingAssistanceStatus.DEGRADED,
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
            result.warnings if result.status == TestingAssistanceStatus.DEGRADED else []
        ),
        "approval_required": bool(result.suggestions or result.new_test_candidates),
        "hidden_reasoning_stored": False,
    }
    return result
