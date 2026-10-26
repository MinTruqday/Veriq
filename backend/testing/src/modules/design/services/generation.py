import json
from collections import Counter

from fastapi import HTTPException
from pydantic import ValidationError

from src.core.ai_automation import request_ai_automation
from src.core.common import plain_text
from src.core.rich_text import text_document
from src.modules.design.services.linters import duplicate_score
from src.modules.design.services.test_case_records import active_suite_signature, comparison_cases
from src.modules.design.services.test_evidence import requirement_test_evidence_text
from src.schemas.contracts.design import ScenarioCreate, TestCaseDraftCreate
from src.schemas.test_analysis import GeneratedCase


def select_generation_criteria(criteria, criterion_ids):
    if not criterion_ids:
        return criteria
    if len(criterion_ids) != len(set(criterion_ids)):
        raise HTTPException(422, detail={"code": "DUPLICATE_ACCEPTANCE_CRITERIA"})
    by_id = {item["_id"]: item for item in criteria}
    if not set(criterion_ids) <= set(by_id):
        raise HTTPException(422, detail={"code": "ACCEPTANCE_CRITERIA_NOT_IN_REQUIREMENT"})
    return [by_id[identifier] for identifier in criterion_ids]


def validated_suggestions(result, schema, *, allow_empty=False):
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
            or not (0 if allow_empty else 1) <= len(items) <= 100
        ):
            raise ValueError("invalid suggestion count")
        return [schema.model_validate(item).model_dump() for item in items]
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(
            502,
            detail={"code": 'AI_GENERATION_INVALID', "message": "AI chưa tạo được bản nháp hợp lệ", "retryable": True},
        ) from error


async def generate_requirement_drafts(
    version, criteria, payload, scenario=False, acceptance_criteria_snapshot_ids=None
):
    if len(criteria) > 99:
        raise HTTPException(
            422,
            detail={
                "code": "GENERATION_EVIDENCE_LIMIT_EXCEEDED",
                "message": "Yêu cầu có quá nhiều tiêu chí chấp nhận để xét đầy đủ trong một lượt  Chưa tạo ca kiểm thử để tránh bỏ sót nguồn",
            },
        )
    technique_mode = bool(payload.techniques) and not scenario
    categories = payload.categories
    allowed = (ScenarioCreate.model_fields["category"] if scenario else TestCaseDraftCreate.model_fields["type"]).annotation.__args__
    if len(set(categories)) != len(categories) or any(item not in allowed for item in categories):
        raise HTTPException(422, detail={"code": 'INVALID_GENERATION_CATEGORIES'})
    if len(payload.techniques) != len(set(payload.techniques)):
        raise HTTPException(422, detail={"code": "DUPLICATE_DESIGN_TECHNIQUE"})
    requested_limit = (
        len(categories) * payload.count_per_category
        if categories
        else payload.max_cases or len(criteria)
    )
    if requested_limit > 100:
        raise HTTPException(422, detail={"code": 'GENERATION_LIMIT_EXCEEDED'})
    evidence = [
        {
            "artifact_type": 'requirement_version',
            "artifact_version_id": version["_id"],
            "text": requirement_test_evidence_text(version),
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
    source_text_by_ref = {item["artifact_version_id"]: item["text"] for item in evidence}
    challenge_cases = {}
    challenge_similarity_threshold = None
    if bool(payload.challenge_hypotheses) != bool(payload.challenge_suite_signature):
        raise HTTPException(422, detail={"code": "TEST_DESIGN_CHALLENGE_SOURCE_CHANGED", "message": "Cần nhận lại gợi ý kỹ thuật trước khi tạo ca theo giả thuyết lỗi"})
    if payload.challenge_hypotheses:
        related, challenge_similarity_threshold = await comparison_cases(version["project_id"])
        challenge_cases = {item["_id"]: item for item in related if item.get("status") == "ACTIVE"}
        current_refs = {
            item["_id"]
            for item in related
            if item.get("status") == "ACTIVE"
            and version["_id"] in item.get("requirement_version_ids", [])
        }
        if (
            payload.challenge_suite_signature != active_suite_signature(related, [version["_id"]])
            or any(not set(item.existing_case_refs) <= current_refs for item in payload.challenge_hypotheses)
        ):
            raise HTTPException(409, detail={"code": "TEST_DESIGN_PREVIEW_STALE", "message": "Bộ ca đang hiệu lực đã thay đổi  Hãy nhận gợi ý mới trước khi tạo ca"})
    if (
        scenario and payload.challenge_hypotheses
        or len({item.technique for item in payload.challenge_hypotheses})
        != len(payload.challenge_hypotheses)
        or any(
            item.technique not in payload.techniques
            or item.source_ref not in source_text_by_ref
            or item.source_quote.strip() not in source_text_by_ref[item.source_ref]
            for item in payload.challenge_hypotheses
        )
    ):
        raise HTTPException(422, detail={"code": "TEST_DESIGN_CHALLENGE_SOURCE_CHANGED", "message": "Giả thuyết lỗi không còn khớp với nguồn hoặc kỹ thuật đã chọn  Hãy nhận gợi ý mới trước khi tạo ca"})
    instruction = json.dumps(
        {
            "categories": categories,
            "count_per_category": payload.count_per_category,
            "maximum_cases": payload.max_cases or (len(payload.techniques) if technique_mode else (len(criteria) if not categories else None)),
            "selected_design_techniques": payload.techniques if not scenario else [],
            "allowed_acceptance_criterion_ids": [item["_id"] for item in criteria],
            "challenge_hypotheses": [item.model_dump() for item in payload.challenge_hypotheses],
            "user_instruction": payload.instruction,
        },
        ensure_ascii=False,
    )
    if len(instruction) > 5000:
        raise HTTPException(
            422, detail={"code": 'GENERATION_INSTRUCTION_TOO_LONG'}
        )
    result = await request_ai_automation(
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
                    "unsupported_claims": [
                        claim
                        for finding in result.get("findings", [])
                        for claim in finding.get("unsupported_claims", [])
                        if isinstance(claim, str)
                    ][:10],
                },
            )
        raise HTTPException(
            503,
            detail={"code": 'AI_PROVIDER_UNAVAILABLE', "retryable": True},
        )
    try:
        generated = [GeneratedCase.model_validate(item) for item in result.get("suggestions", [])]
        if not generated:
            raise HTTPException(
                422,
                detail={
                    "code": "TECHNIQUE_EVIDENCE_INSUFFICIENT" if technique_mode else "GENERATION_EVIDENCE_INSUFFICIENT",
                    "message": "Nguồn yêu cầu chưa đủ để tạo ca kiểm thử theo lựa chọn hiện tại",
                    "unapplied_techniques": payload.techniques if technique_mode else [],
                    "warnings": result.get("warnings", [])[:10],
                },
            )
        if technique_mode:
            if not 1 <= len(generated) <= (payload.max_cases or len(payload.techniques)):
                raise ValueError("case count outside selected limit")
            if any(item.category not in allowed for item in generated):
                raise ValueError("unknown test category")
        elif scenario and categories:
            requested_counts = Counter(
                {category: payload.count_per_category for category in categories}
            )
            generated_counts = Counter(item.category for item in generated)
            if (
                not generated_counts
                or generated_counts - requested_counts
                or requested_counts - generated_counts and not result.get("warnings")
            ):
                raise ValueError("scenario category count mismatch")
        elif scenario:
            if len(generated) > (payload.max_cases or len(criteria)) or any(
                item.category not in allowed for item in generated
            ):
                raise ValueError("automatic scenario count or category is invalid")
        elif categories:
            requested_counts = Counter(
                {category: payload.count_per_category for category in categories}
            )
            generated_counts = Counter(item.category for item in generated)
            if (
                not generated_counts
                or generated_counts - requested_counts
                or requested_counts - generated_counts and not result.get("warnings")
            ):
                raise ValueError("test case category count mismatch")
        elif len(generated) > (payload.max_cases or len(criteria)) or any(
            item.category not in allowed for item in generated
        ):
            raise ValueError("automatic test case count or category is invalid")
        criterion_ids = {item["_id"] for item in criteria}
        evidence_ids = {item["artifact_version_id"] for item in evidence}
        selected_techniques = set(payload.techniques) if not scenario else set()
        if selected_techniques:
            used = {technique for item in generated for technique in item.techniques}
            if used != selected_techniques:
                raise HTTPException(
                    422,
                    detail={
                        "code": "TECHNIQUE_GENERATION_INCOMPLETE",
                        "message": "AI chưa tạo được ca cho mọi kỹ thuật đã chọn trong số ca tối đa hiện tại  Chưa lưu bản nháp thiếu kỹ thuật  Hãy tăng số ca tối đa hoặc điều chỉnh lựa chọn theo bằng chứng",
                        "unapplied_techniques": sorted(selected_techniques - used),
                        "warnings": result.get("warnings", [])[:10],
                        "unsupported_claims": [
                            claim
                            for finding in result.get("findings", [])
                            for claim in finding.get("unsupported_claims", [])
                            if isinstance(claim, str)
                        ][:10],
                    },
                )
        selected_challenges = {item.technique for item in payload.challenge_hypotheses}
        if any(
            len(item.challenge_techniques) != len(set(item.challenge_techniques))
            or not set(item.challenge_techniques) <= set(item.techniques)
            or not set(item.challenge_techniques) <= selected_challenges
            for item in generated
        ):
            raise ValueError("invalid challenge association")
        addressed_challenges = {
            technique for item in generated for technique in item.challenge_techniques
        }
        if addressed_challenges != selected_challenges:
            raise HTTPException(
                422,
                detail={
                    "code": "TEST_DESIGN_CHALLENGE_NOT_ADDRESSED",
                    "message": "AI chưa tạo được ca kiểm thử cho mọi giả thuyết đã chọn  Hãy xem lại bằng chứng hoặc chọn ít giả thuyết hơn",
                    "unaddressed_challenges": sorted(selected_challenges - addressed_challenges),
                    "warnings": result.get("warnings", [])[:10],
                },
            )
        drafts = []
        for item in generated:
            if not set(item.acceptance_criterion_ids) <= criterion_ids:
                raise ValueError("unknown evidence")
            if not set(item.evidence_refs) <= evidence_ids:
                raise ValueError("unknown evidence reference")
            if not all(
                quote.evidence_ref in item.evidence_refs
                and quote.quote.strip() in source_text_by_ref.get(quote.evidence_ref, "")
                for quote in item.evidence_quotes
            ):
                raise ValueError("invalid evidence quote")
            if selected_techniques and (not item.techniques or not set(item.techniques) <= selected_techniques):
                raise ValueError("unselected design technique")
            if selected_techniques and (not item.coverage_obligations or not item.evidence_refs):
                raise ValueError("missing technique coverage evidence")
            if any(
                challenge.source_ref not in item.evidence_refs
                for challenge in payload.challenge_hypotheses
                if challenge.technique in item.challenge_techniques
            ):
                raise ValueError("challenge source not cited by generated case")
            common = {
                "title": item.title,
                "requirement_version_ids": [version["_id"]],
                "acceptance_criterion_ids": item.acceptance_criterion_ids,
                "origin": 'ai_generated',
            }
            if scenario:
                drafts.append(
                    ScenarioCreate(
                        **common,
                        priority=version.get("priority") or "medium",
                        risk=version.get("risk") or "medium",
                        category=item.category,
                        objective=item.objective,
                    )
                )
            else:
                steps = [
                    {
                        "id": f"{'step-'}{index}",
                        "order": index,
                        "action_doc": text_document(step.action),
                        "expected_doc": text_document(step.expected),
                        "test_data": step.test_data,
                    }
                    for index, step in enumerate(item.steps, 1)
                ]
                drafts.append(
                    TestCaseDraftCreate(
                        **common,
                        priority="unassessed",
                        risk="unassessed",
                        type=item.category,
                        objective_doc=text_document(item.objective),
                        preconditions_doc=text_document(item.preconditions),
                        steps=steps,
                        expected_result_doc=text_document(item.expected),
                        source_evidence=evidence,
                        acceptance_criteria_snapshot_ids=(
                            list(dict.fromkeys(acceptance_criteria_snapshot_ids))
                            if acceptance_criteria_snapshot_ids is not None
                            else None
                        ),
                        techniques=item.techniques,
                        coverage_obligations=item.coverage_obligations,
                        obligation_evidence=[
                            evidence.model_dump()
                            for evidence in item.obligation_evidence
                        ],
                        evidence_refs=item.evidence_refs,
                        evidence_quotes=[quote.model_dump() for quote in item.evidence_quotes],
                        challenge_hypotheses=[
                            challenge
                            for challenge in payload.challenge_hypotheses
                            if challenge.technique in item.challenge_techniques
                        ],
                    )
                )
                draft = drafts[-1]
                if any(
                    duplicate_score(
                        draft.model_dump(),
                        challenge_cases[existing_ref],
                        challenge_similarity_threshold,
                    )[0] >= challenge_similarity_threshold
                    for challenge in payload.challenge_hypotheses
                    if challenge.technique in item.challenge_techniques
                    for existing_ref in challenge.existing_case_refs
                ):
                    raise HTTPException(
                        422,
                        detail={
                            "code": "TEST_DESIGN_CHALLENGE_NOT_DISTINGUISHING",
                            "message": "Ca được tạo vẫn trùng phạm vi của ca đang hiệu lực nên chưa thể kiểm chứng giả thuyết  Hãy nhận gợi ý kỹ thuật mới",
                        },
                    )
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(
            502,
            detail={"code": 'AI_GENERATION_INVALID', "message": "AI chưa tạo được bản nháp hợp lệ", "retryable": True},
        ) from error
    requested_categories = Counter({category: payload.count_per_category for category in categories})
    generated_categories = Counter(item.category for item in generated)
    result["unapplied_categories"] = [category for category, requested_count in requested_categories.items() if generated_categories[category] < requested_count]
    return drafts, result
