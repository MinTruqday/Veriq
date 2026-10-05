import json
from collections import Counter
from fastapi import HTTPException
from pydantic import ValidationError

from src.core.common import plain_text
from src.schemas.contracts.design import (
    ScenarioCreate,
    TestCaseDraftCreate,
)
from src.schemas.test_analysis import (
    GeneratedCase,
    GeneratedStep,
    PerformanceScenario,
    SecurityCandidate,
)
from src.core.ai_assistance import request_ai_assistance


def validated_suggestions(result, schema):
    if result.get("status") != 'SUCCESS' or result.get(
        "degraded_mode"
    ):
        raise HTTPException(
            503,
            detail={"code": 'AI_PROVIDER_UNAVAILABLE', "retryable": True},
        )
    try:
        items = result.get("suggestions")
        if (
            not isinstance(items, list)
            or not 1 <= len(items) <= 100
        ):
            raise ValueError("invalid suggestion count")
        return [schema.model_validate(item).model_dump() for item in items]
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(
            502,
            detail={"code": 'AI_GENERATION_INVALID', "message": "AI chưa tạo được bản nháp hợp lệ", "retryable": True},
        ) from error


def document(text):
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


async def generate_requirement_drafts(version, criteria, payload, scenario=False):
    if len(criteria) > 99:
        raise HTTPException(
            422,
            detail={
                "code": "GENERATION_EVIDENCE_LIMIT_EXCEEDED",
                "message": "Yêu cầu có quá nhiều tiêu chí chấp nhận để xét đầy đủ trong một lượt  Chưa tạo ca kiểm thử để tránh bỏ sót nguồn",
            },
        )
    technique_mode = bool(payload.techniques) and not scenario
    categories = payload.categories or ([] if technique_mode else ['happy_path', 'negative', 'boundary', 'validation'])
    allowed = (ScenarioCreate.model_fields["category"] if scenario else TestCaseDraftCreate.model_fields["type"]).annotation.__args__
    if len(set(categories)) != len(categories) or any(item not in allowed for item in categories):
        raise HTTPException(422, detail={"code": 'INVALID_GENERATION_CATEGORIES'})
    if len(payload.techniques) != len(set(payload.techniques)):
        raise HTTPException(422, detail={"code": "DUPLICATE_DESIGN_TECHNIQUE"})
    if (len(categories) * payload.count_per_category if categories else payload.max_cases or len(payload.techniques)) > 100:
        raise HTTPException(422, detail={"code": 'GENERATION_LIMIT_EXCEEDED'})
    evidence = [
        {
            "artifact_type": 'requirement_version',
            "artifact_version_id": version["_id"],
            "text": version["plain_text_projection"],
        }
    ]
    evidence.extend(
        {
            "artifact_type": 'acceptance_criterion',
            "artifact_version_id": item["_id"],
            "text": item.get("plain_text") or plain_text(item.get("content_doc", {})),
        }
        for item in criteria
    )
    instruction = json.dumps(
        {
            "categories": categories,
            "count_per_category": payload.count_per_category,
            "maximum_cases": payload.max_cases or len(payload.techniques) if technique_mode else None,
            "selected_design_techniques": payload.techniques if not scenario else [],
            "user_instruction": payload.instruction,
        },
        ensure_ascii=False,
    )
    if len(instruction) > 5000:
        raise HTTPException(
            422, detail={"code": 'GENERATION_INSTRUCTION_TOO_LONG'}
        )
    result = await request_ai_assistance(
        'scenario_generation'
        if scenario
        else 'test_generation',
        version["project_id"],
        instruction,
        evidence,
    )
    if result.get("status") != 'SUCCESS' or result.get(
        "degraded_mode"
    ):
        if "AI_UNGROUNDED_OUTPUT" in result.get("reason_codes", []):
            raise HTTPException(
                422,
                detail={
                    "code": "AI_UNGROUNDED_OUTPUT",
                    "message": "AI đưa ra hành vi chưa được tài liệu xác nhận  Cần bổ sung bằng chứng hoặc thử lại với kỹ thuật phù hợp",
                },
            )
        raise HTTPException(
            503,
            detail={"code": 'AI_PROVIDER_UNAVAILABLE', "retryable": True},
        )
    try:
        generated = [GeneratedCase.model_validate(item) for item in result.get("suggestions", [])]
        if technique_mode:
            if not 1 <= len(generated) <= (payload.max_cases or len(payload.techniques)):
                raise ValueError("case count outside selected limit")
            if any(item.category not in allowed for item in generated):
                raise ValueError("unknown test category")
        elif Counter(item.category for item in generated) != Counter(
            {category: payload.count_per_category for category in categories}
        ):
            raise ValueError("category count mismatch")
        criterion_ids = {item["_id"] for item in criteria}
        evidence_ids = {item["artifact_version_id"] for item in evidence}
        selected_techniques = set(payload.techniques) if not scenario else set()
        if selected_techniques:
            used = {technique for item in generated for technique in item.techniques}
            if used != selected_techniques:
                raise HTTPException(
                    422,
                    detail={"code": "TECHNIQUE_EVIDENCE_INSUFFICIENT", "message": "Nguồn yêu cầu chưa đủ để áp dụng tất cả kỹ thuật đã chọn", "unapplied_techniques": sorted(selected_techniques - used)},
                )
        drafts = []
        for item in generated:
            if not set(item.acceptance_criterion_ids) <= criterion_ids:
                raise ValueError("unknown evidence")
            if not set(item.evidence_refs) <= evidence_ids:
                raise ValueError("unknown evidence reference")
            if selected_techniques and (not item.techniques or not set(item.techniques) <= selected_techniques):
                raise ValueError("unselected design technique")
            if selected_techniques and (not item.coverage_obligations or not item.evidence_refs):
                raise ValueError("missing technique coverage evidence")
            common = {
                "title": item.title,
                "priority": version.get("priority", 'medium'),
                "risk": version.get("risk", 'medium'),
                "requirement_version_ids": [version["_id"]],
                "acceptance_criterion_ids": item.acceptance_criterion_ids,
                "origin": 'ai_generated',
            }
            if scenario:
                drafts.append(
                    ScenarioCreate(**common, category=item.category, objective=item.objective)
                )
            else:
                steps = [
                    {
                        "id": f"{'step-'}{index}",
                        "order": index,
                        "action_doc": document(step.action),
                        "expected_doc": document(step.expected),
                        "test_data": step.test_data,
                    }
                    for index, step in enumerate(item.steps, 1)
                ]
                drafts.append(
                    TestCaseDraftCreate(
                        **common,
                        type=item.category,
                        objective_doc=document(item.objective),
                        preconditions_doc=document(item.preconditions),
                        steps=steps,
                        expected_result_doc=document(item.expected),
                        source_evidence=evidence,
                        techniques=item.techniques,
                        coverage_obligations=item.coverage_obligations,
                        evidence_refs=item.evidence_refs,
                    )
                )
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(
            502,
            detail={"code": 'AI_GENERATION_INVALID', "message": "AI chưa tạo được bản nháp hợp lệ", "retryable": True},
        ) from error
    return drafts, result
