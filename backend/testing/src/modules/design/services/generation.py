import json
from collections import Counter
from difflib import SequenceMatcher

from fastapi import HTTPException
from pydantic import ValidationError

from src.core.ai_automation import request_ai_automation
from src.core.common import plain_text
from src.core.rich_text import text_document
from src.modules.design.services.linters import duplicate_score
from src.modules.design.services.test_case_records import active_suite_signature, comparison_cases
from src.modules.projects.services.project_setting_defaults import resolve_testcase_duplicate_threshold
from src.repositories.test_design import test_design_repository
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


def grounded_retry_instruction(instruction, result):
    try:
        value = json.loads(instruction)
    except (TypeError, ValueError):
        value = {"user_instruction": str(instruction or "")}
    if not isinstance(value, dict):
        value = {"user_instruction": value}
    claims = [
        claim
        for finding in result.get("findings", [])
        if isinstance(finding, dict)
        for claim in finding.get("unsupported_claims", [])
        if isinstance(claim, str) and claim.strip()
    ]
    value["grounding_retry"] = {
        "instruction": "Regenerate once using only claims directly supported by the supplied source evidence. Omit cases that cannot be supported; do not invent replacement behavior.",
        "rejected_claims": list(dict.fromkeys(claims))[:20],
    }
    return json.dumps(value, ensure_ascii=False)


async def request_grounded_test_generation(project_id, instruction, evidence):
    result = await request_ai_automation(
        "test_generation", project_id, instruction, evidence
    )
    if (
        result.get("status") == "SUCCESS"
        and not result.get("degraded_mode")
    ) or "AI_UNGROUNDED_OUTPUT" not in (result.get("reason_codes") or []):
        return result
    return await request_ai_automation(
        "test_generation",
        project_id,
        grounded_retry_instruction(instruction, result),
        evidence,
    )


def merge_duplicate_generated_cases(drafts, suggestions, threshold):
    kept_drafts = []
    kept_suggestions = []
    merged_count = 0
    for draft, suggestion in zip(drafts, suggestions):
        duplicate_index = next((
            index
            for index, (kept_draft, kept_suggestion) in enumerate(
                zip(kept_drafts, kept_suggestions)
            )
            if (
            draft.type == kept_draft.type
            and set(suggestion.challenge_techniques) == set(kept_suggestion.challenge_techniques)
            and generated_cases_have_equivalent_actions(draft, kept_draft)
            and duplicate_score(draft.model_dump(), kept_draft.model_dump(), threshold)[0]
            >= threshold
            )
        ), None)
        if duplicate_index is not None:
            kept_draft = kept_drafts[duplicate_index]
            kept_suggestion = kept_suggestions[duplicate_index]
            criterion_ids = list(dict.fromkeys([
                *kept_draft.acceptance_criterion_ids,
                *draft.acceptance_criterion_ids,
            ]))
            evidence_refs = list(dict.fromkeys([
                *kept_suggestion.evidence_refs,
                *suggestion.evidence_refs,
            ]))
            evidence_quotes = list({
                (quote.evidence_ref, quote.quote): quote
                for quote in [*kept_suggestion.evidence_quotes, *suggestion.evidence_quotes]
            }.values())
            obligations = list(dict.fromkeys([
                *kept_suggestion.coverage_obligations,
                *suggestion.coverage_obligations,
            ]))
            techniques = list(dict.fromkeys([
                *kept_suggestion.techniques,
                *suggestion.techniques,
            ]))
            obligation_evidence_by_key = {}
            for item in [*kept_suggestion.obligation_evidence, *suggestion.obligation_evidence]:
                evidence = obligation_evidence_by_key.setdefault(item.obligation_key, {})
                evidence.update({
                    (quote.evidence_ref, quote.quote): quote
                    for quote in item.evidence_quotes
                })
            obligation_evidence = [
                {
                    "obligation_key": key,
                    "evidence_quotes": list(quotes.values()),
                }
                for key, quotes in obligation_evidence_by_key.items()
            ]
            if (
                len(evidence_quotes) > 20
                or len(obligations) > 100
                or len(techniques) > 50
                or len(obligation_evidence) > 100
                or len(criterion_ids) > 500
                or len(evidence_refs) > 200
            ):
                kept_drafts.append(draft)
                kept_suggestions.append(suggestion)
                continue
            try:
                merged_suggestion = GeneratedCase.model_validate({
                    **kept_suggestion.model_dump(),
                    "acceptance_criterion_ids": criterion_ids,
                    "techniques": techniques,
                    "evidence_refs": evidence_refs,
                    "evidence_quotes": [item.model_dump() for item in evidence_quotes],
                    "coverage_obligations": obligations,
                    "obligation_evidence": obligation_evidence,
                    "required_skills": list(dict.fromkeys([
                        *kept_suggestion.required_skills,
                        *suggestion.required_skills,
                    ])),
                })
                merged_draft = type(kept_draft).model_validate({
                    **kept_draft.model_dump(),
                    "acceptance_criterion_ids": criterion_ids,
                    "techniques": techniques,
                    "evidence_refs": evidence_refs,
                    "evidence_quotes": [item.model_dump() for item in evidence_quotes],
                    "coverage_obligations": obligations,
                    "obligation_evidence": obligation_evidence,
                    "required_skills": merged_suggestion.required_skills,
                })
            except ValidationError:
                kept_drafts.append(draft)
                kept_suggestions.append(suggestion)
                continue
            kept_drafts[duplicate_index] = merged_draft
            kept_suggestions[duplicate_index] = merged_suggestion
            merged_count += 1
            continue
        kept_drafts.append(draft)
        kept_suggestions.append(suggestion)
    return kept_drafts, kept_suggestions, merged_count


def generated_cases_have_equivalent_actions(left, right):
    if left.test_data != right.test_data:
        return False
    left_preconditions = " ".join(plain_text(left.preconditions_doc).casefold().split())
    right_preconditions = " ".join(plain_text(right.preconditions_doc).casefold().split())
    if SequenceMatcher(None, left_preconditions, right_preconditions).ratio() < 0.9:
        return False
    if len(left.steps) != len(right.steps):
        return False
    for left_step, right_step in zip(left.steps, right.steps):
        if left_step.test_data != right_step.test_data:
            return False
        left_action = " ".join(plain_text(left_step.action_doc).casefold().split())
        right_action = " ".join(plain_text(right_step.action_doc).casefold().split())
        if SequenceMatcher(None, left_action, right_action).ratio() < 0.9:
            return False
    return True


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
    categories = [str(item).strip() for item in payload.categories]
    if any(not item for item in categories) or len(
        {item.casefold() for item in categories}
    ) != len(categories):
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
    result = (
        await request_ai_automation(
            "scenario_generation", version["project_id"], instruction, evidence
        )
        if scenario
        else await request_grounded_test_generation(
            version["project_id"], instruction, evidence
        )
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
            if any(not item.category.strip() for item in generated):
                raise ValueError("empty test category")
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
                not item.category.strip() for item in generated
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
            not item.category.strip() for item in generated
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
                        priority=version.get("priority") or "unassessed",
                        risk=version.get("risk") or "unassessed",
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
                        required_skills=item.required_skills,
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
    if not scenario:
        duplicate_threshold = resolve_testcase_duplicate_threshold(
            await test_design_repository.find_project_settings(version["project_id"])
        )
        drafts, generated, merged_duplicates = merge_duplicate_generated_cases(
            drafts, generated, duplicate_threshold
        )
        result["suggestions"] = [item.model_dump() for item in generated]
        if merged_duplicates:
            result["warnings"] = list(dict.fromkeys([
                *(result.get("warnings") or []),
                f"Đã gộp {merged_duplicates} ca trùng vào ca kiểm thử tương ứng và giữ đủ liên kết tiêu chí.",
            ]))
    requested_categories = Counter({category: payload.count_per_category for category in categories})
    generated_categories = Counter(item.category for item in generated)
    result["unapplied_categories"] = [category for category, requested_count in requested_categories.items() if generated_categories[category] < requested_count]
    return drafts, result
