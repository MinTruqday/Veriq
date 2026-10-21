import json
from typing import Annotated
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.tools.registry import with_tool_access
from src.tools.testing_api import AutomationOperationError, INTERNAL_API_URL, call, headers, parse, require_operation

def compilable_document_ids(documents, event_document_id):
    """Return the authorized, AI-enabled source set for one compilation event."""
    identifiers = sorted(
        {
            str(item.get("_id"))
            for item in documents
            if item.get("_id")
            and item.get("ai_enabled") is True
            and item.get("status") == "READY"
            and item.get("normalized_content")
        }
    )
    return identifiers if str(event_document_id) in identifiers else []

def normalized_text(value):
    return " ".join(str(value or "").casefold().split())

def response_items(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        items = value.get("items")
        return items if isinstance(items, list) else []
    return []

async def carry_forward_unchanged_requirement_tests(
    project_id, requirement_id, target_version, requirement_versions, impact_analysis, config
):
    ai_result = impact_analysis.get("ai_result") or {}
    applied_versions = set(impact_analysis.get("ai_applied_version_ids") or [])
    unchanged_versions = {
        item.get("test_case_version_id") or item.get("artifact_version_id")
        for item in ai_result.get("suggestions", [])
        if item.get("classification") == "STILL_VALID"
    } & applied_versions
    if not unchanged_versions:
        return [], []

    prior_versions = {}
    for item in requirement_versions:
        if item.get("_id") == target_version.get("_id") or item.get("status") != "BASELINED":
            continue
        previous = await require_operation(
            "GET", f"/phien-ban-yeu-cau/{item['_id']}", config
        )
        if previous.get("requirement_id") == requirement_id:
            prior_versions[previous["_id"]] = previous

    target_criteria = target_version.get("acceptance_criteria") or []
    target_by_key = {
        item.get("key"): item
        for item in target_criteria
        if item.get("key") and item.get("_id")
    }
    prior_criteria_by_id = {
        criterion["_id"]: criterion
        for item in prior_versions.values()
        for criterion in item.get("acceptance_criteria", [])
        if criterion.get("_id")
    }
    prior_criterion_ids = set(prior_criteria_by_id)
    cases = await require_operation(
        "GET",
        f"/du-an/{project_id}/ca-kiem-thu?requirement_id={requirement_id}&page_size=500",
        config,
    )
    carried = []
    unresolved = []
    for case in response_items(cases):
        current = case.get("current_version") or {}
        current_version_id = case.get("current_version_id") or current.get("_id")
        old_requirement_ids = set(current.get("requirement_version_ids", [])) & set(prior_versions)
        if (
            case.get("status") != "ACTIVE"
            or current_version_id not in unchanged_versions
            or not old_requirement_ids
        ):
            continue
        old_criterion_links = set(current.get("acceptance_criterion_ids", [])) & prior_criterion_ids
        mapped_criterion_ids = {
            target_by_key[prior_criteria_by_id[item].get("key")]["_id"]
            for item in old_criterion_links
            if prior_criteria_by_id[item].get("key") in target_by_key
        }
        if old_criterion_links and not mapped_criterion_ids:
            unresolved.append({
                "test_case_id": case.get("_id"),
                "reason": "UNCHANGED_TEST_CASE_CRITERION_MAPPING_NOT_FOUND",
            })
            continue
        requirement_ids = sorted((set(current.get("requirement_version_ids", [])) - old_requirement_ids) | {target_version["_id"]})
        criterion_ids = sorted((set(current.get("acceptance_criterion_ids", [])) - prior_criterion_ids) | mapped_criterion_ids)
        if (
            target_version["_id"] in current.get("requirement_version_ids", [])
            and set(current.get("acceptance_criterion_ids", [])) == set(criterion_ids)
        ):
            continue
        try:
            draft = await require_operation(
                "POST",
                f"/ca-kiem-thu/{case['_id']}/phien-ban/ban-nhap",
                config,
                {
                    "expected_current_version_id": current_version_id,
                    "change_reason": "Giữ nguyên ca đã được AI phân loại còn hiệu lực và cập nhật trace sang Requirement version mới",
                },
            )
            draft = await require_operation(
                "PATCH",
                f"/ban-nhap-ca-kiem-thu/{draft['_id']}",
                config,
                {
                    "expected_revision": draft["revision"],
                    "requirement_version_ids": requirement_ids,
                    "acceptance_criterion_ids": criterion_ids,
                },
            )
            lint = await require_operation(
                "POST", f"/ca-kiem-thu/{draft['_id']}/kiem-tra", config
            )
            if not lint.get("valid"):
                unresolved.append({"test_case_id": case["_id"], "reason": "CARRIED_TEST_CASE_QUALITY_FAILED"})
                continue
            reviewed = await require_operation(
                "POST",
                f"/du-an/{project_id}/ca-kiem-thu/{draft['_id']}/gui-ra-soat",
                config,
                {
                    "expected_revision": draft["revision"],
                    "review_note": "Tự động kiểm tra chất lượng và nguồn trước khi chốt phiên bản đã được impact analysis xác nhận còn hiệu lực",
                },
            )
            approved = await require_operation(
                "POST",
                f"/du-an/{project_id}/ca-kiem-thu/{draft['_id']}/phe-duyet",
                config,
                {
                    "expected_revision": reviewed["revision"],
                    "change_reason": "Tự động cập nhật trace của ca còn hiệu lực sang Requirement version mới",
                    "review_note": "Impact analysis xác nhận ca còn hiệu lực; kiểm tra chất lượng phiên bản mới đã đạt",
                },
            )
            readback = approved.get("test_case") or (approved.get("data") or {}).get("test_case")
            if not readback or readback.get("_id") != case.get("_id"):
                raise RuntimeError("UNCHANGED_TEST_CASE_VERSION_READBACK_INVALID")
            carried.append(case["_id"])
        except (KeyError, RuntimeError) as error:
            unresolved.append({"test_case_id": case.get("_id"), "reason": str(error)})
    return carried, unresolved

def requirement_source_text(version):
    values = [version.get("plain_text_projection"), version.get("business_rules")]
    for field in ("content_doc", "acceptance_criteria"):
        values.append(version.get(field))

    def collect(value):
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [text for item in value for text in collect(item)]
        if isinstance(value, dict):
            if isinstance(value.get("text"), str):
                return [value["text"]]
            return [text for item in value.values() for text in collect(item)]
        return []

    return " ".join(collect(values)).casefold()

async def resolve_answered_clarifications(version, config):
    clarifications = await require_operation(
        "GET", f"/phien-ban-yeu-cau/{version['_id']}/phieu-lam-ro", config
    )
    source_text = requirement_source_text(version)
    unresolved = []
    for item in response_items(clarifications):
        if item.get("status") != "ANSWERED":
            continue
        answer = str(item.get("answer") or "").strip()
        if not answer or answer.casefold() not in source_text:
            unresolved.append(item)
            continue
        try:
            await require_operation(
                "POST",
                f"/phieu-lam-ro/{item['_id']}/xac-nhan-giai-quyet",
                config,
                {
                    "expected_revision": item["revision"],
                    "requirement_version_id": version["_id"],
                    "evidence_quote": answer,
                },
            )
        except (KeyError, RuntimeError):
            unresolved.append(item)

    refreshed = await require_operation(
        "GET", f"/phien-ban-yeu-cau/{version['_id']}/phieu-lam-ro", config
    )
    unresolved.extend(
        item for item in response_items(refreshed)
        if item.get("status") in {"OPEN", "ANSWERED"}
        and item not in unresolved
    )
    return unresolved

async def plan_clarification_priority(version, clarifications, config):
    """Rank open questions only by obligations linked through exact source identity."""
    if not clarifications:
        return []
    assessment = await require_operation(
        "GET",
        f"/phien-ban-yeu-cau/{version['_id']}/do-day-du-kiem-thu",
        config,
    )
    unresolved_items = [
        item
        for item in assessment.get("coverage_items", [])
        if item.get("status") in {"UNASSESSED", "MISSING_INFORMATION"}
    ]
    ranked = []
    for clarification in clarifications:
        source_ref = str(clarification.get("source_ref") or "").strip().casefold()
        source_quote = str(clarification.get("source_quote") or "").strip().casefold()
        linked = []
        for item in unresolved_items:
            if clarification.get("coverage_item_id") == item.get("coverage_item_id"):
                linked.append(item)
                continue
            if source_ref and source_ref == str(item.get("source_ref") or "").strip().casefold():
                linked.append(item)
                continue
            quote = str(item.get("source_quote") or "").strip().casefold()
            if source_quote and quote and (source_quote == quote or source_quote in quote or quote in source_quote):
                linked.append(item)
        ranked.append(
            {
                "clarification_id": clarification.get("_id"),
                "requirement_version_id": version["_id"],
                "question": clarification.get("question"),
                "reason": clarification.get("reason"),
                "status": clarification.get("status"),
                "unlocks_coverage_item_ids": list(
                    dict.fromkeys(item.get("coverage_item_id") for item in linked if item.get("coverage_item_id"))
                ),
                "unlock_count": len({item.get("coverage_item_id") for item in linked if item.get("coverage_item_id")}),
            }
        )
    ranked.sort(key=lambda item: (-item["unlock_count"], str(item.get("clarification_id") or "")))
    for priority, item in enumerate(ranked, start=1):
        item["priority"] = priority
        if not item["unlock_count"]:
            item["priority_basis"] = "Không có liên kết nguồn chính xác với Nghĩa vụ còn mở; không khẳng định số mục được mở khóa"
        else:
            item["priority_basis"] = "Số Nghĩa vụ còn mở được liên kết qua mã nguồn hoặc trích dẫn chính xác"
    return ranked

from src.tools.knowledge_tools import (
    get_project_context,
    search_project_knowledge,
    retrieve_project_evidence,
)

from src.tools.requirement_tools import (
    get_requirement_version,
    compare_requirement_versions,
    get_acceptance_criteria,
    get_trace_links,
    synthesize_requirement_template,
    create_requirement_draft,
    create_trace_link_suggestion,
    confirm_trace_link,
    baseline_requirement_version,
    get_requirement,
    get_change_facts,
    lint_requirement,
    get_traceability_links,
)

from src.tools.test_design_tools import (
    search_test_cases,
    get_test_case_version,
    get_test_case_draft,
    get_test_case_version_by_id,
    find_near_duplicates,
    create_test_case_draft,
    approve_test_case_version,
    mark_test_case_obsolete,
    apply_test_case_revision,
    apply_maintenance_proposal,
    search_related_testcases,
    generate_test_scenarios,
    generate_testcases,
    lint_testcase,
    find_duplicate_testcases,
    calculate_coverage,
    propose_testcase_revision,
    propose_new_testcase,
    propose_obsolete_testcase,
)

from src.tools.execution_tools import (
    get_test_results,
    get_test_result,
    get_test_plan,
    get_release,
    get_work_item,
    get_work_item_impact_context,
    get_historical_defects,
    create_impact_analysis,
    create_maintenance_proposal,
    create_regression_recommendation,
    analyze_change_impact,
    suggest_regression_scope,
    get_execution_history,
    get_bug_history,
    link_bug_candidates,
)

from src.tools.requirement_workflows import (
    process_changed_requirement_version,
    process_ingested_requirement_document,
)
from src.tools.execution_workflows import (
    process_approved_test_plan,
    process_changed_test_plan,
    process_recorded_defect,
)

