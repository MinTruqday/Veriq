import json
from typing import Annotated
from urllib.parse import urlencode

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.prompts.test_generation import requirement_test_generation_instruction
from src.tools.grounded_publication import (
    publish_grounded_requirement,
    publish_grounded_test_case,
    verified_test_case_publication_readback,
)
from src.tools.registry import with_tool_access
from src.tools.test_case_deduplication import consolidate_duplicate_test_case_drafts
from src.tools.testing import (
    carry_forward_unchanged_requirement_tests,
    list_all_test_case_records,
    list_resumable_ai_test_case_drafts,
    normalized_text,
    resolve_answered_clarifications,
    response_items,
)
from src.tools.testing_api import ToolOperationError, require_operation


def finalized_generation_warnings(attempts, *, coverage_complete):
    selected_attempts = attempts[-1:] if coverage_complete and attempts else attempts
    return list(dict.fromkeys(str(warning) for attempt in selected_attempts for warning in attempt))


async def assess_changed_requirement_quality(project_id, version, config):
    version_id = str(version.get("_id") or "")
    revision = version.get("revision")
    if not version_id or not isinstance(revision, int) or isinstance(revision, bool):
        raise ToolOperationError("REQUIREMENT_QUALITY_SOURCE_REVISION_INVALID")
    idempotency_key = f"requirement-quality-event:{version_id}:{revision}"
    result = await require_operation(
        "POST",
        f"/phien-ban-yeu-cau/{version_id}/ai/kiem-tra",
        config,
        {
            "idempotency_key": idempotency_key,
            "instruction": "Assess the testability of this exact Requirement version. Record only evidence-backed issues and do not modify the source content.",
        },
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )
    if (
        not isinstance(result, dict)
        or not result.get("_id")
        or result.get("project_id") != project_id
        or result.get("artifact_id") != version_id
        or result.get("requirement_version_id") != version_id
        or result.get("result_type") != "REQUIREMENT_QUALITY_ANALYSIS"
        or result.get("idempotency_key") != idempotency_key
    ):
        raise ToolOperationError("REQUIREMENT_QUALITY_READBACK_INVALID")
    system_checks = result.get("findings")
    recommendations = result.get("recommendations")
    if not isinstance(system_checks, list) or any(
        not isinstance(item, dict)
        or item.get("severity") not in {"error", "warning", "info"}
        for item in system_checks
    ):
        raise ToolOperationError("REQUIREMENT_QUALITY_FINDINGS_INVALID")
    if not isinstance(recommendations, list) or any(
        not isinstance(item, dict) or "severity" in item
        for item in recommendations
    ):
        raise ToolOperationError("REQUIREMENT_QUALITY_RECOMMENDATIONS_INVALID")
    status = result.get("status")
    if status not in {"SUCCESS", "DEGRADED", "FAILED"}:
        raise ToolOperationError("REQUIREMENT_QUALITY_STATUS_INVALID")
    degraded_mode = result.get("degraded_mode")
    if not isinstance(result.get("valid"), bool) or not isinstance(degraded_mode, bool):
        raise ToolOperationError("REQUIREMENT_QUALITY_STATUS_INVALID")
    return {
        "analysis_id": str(result["_id"]),
        "status": status,
        "valid": result["valid"],
        "degraded_mode": degraded_mode,
        "system_check_count": len(system_checks),
        "blocking_system_check_count": sum(
            item.get("severity") == "error" for item in system_checks
        ),
        "recommendation_count": len(recommendations),
    }


def requirement_quality_allows_ai_publication(assessment):
    return (
        isinstance(assessment, dict)
        and assessment.get("status") == "SUCCESS"
        and assessment.get("valid") is True
        and assessment.get("degraded_mode") is not True
        and assessment.get("blocking_system_check_count") == 0
    )


async def list_all_impact_proposals(project_id, impact_analysis_id, config, page_size=500):
    records = []
    seen_ids = set()
    total = None
    total_pages = None
    scope_fingerprint = None
    page = 1
    while total_pages is None or page <= total_pages:
        query = urlencode(
            {
                "impact_analysis_id": impact_analysis_id,
                "page": page,
                "page_size": page_size,
                "sort": "created_at",
            }
        )
        response = await require_operation(
            "GET", f"/du-an/{project_id}/de-xuat-bao-tri?{query}", config
        )
        items = response_items(response)
        for item in items:
            identifier = str(item.get("_id") or "")
            if not identifier or identifier in seen_ids:
                raise ToolOperationError("MAINTENANCE_PROPOSAL_PAGINATION_DUPLICATE")
            if (
                item.get("project_id") != project_id
                or item.get("impact_analysis_id") != impact_analysis_id
            ):
                raise ToolOperationError("MAINTENANCE_PROPOSAL_SCOPE_INVALID")
            seen_ids.add(identifier)
            records.append(item)

        if not isinstance(response, dict):
            raise ToolOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INVALID")
        try:
            reported_total = int(response["total"])
            reported_pages = int(response["total_pages"])
            reported_page = int(response["page"])
            reported_page_size = int(response["page_size"])
        except (KeyError, TypeError, ValueError) as error:
            raise ToolOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INVALID") from error
        if reported_page != page or reported_page_size != page_size:
            raise ToolOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INVALID")
        reported_fingerprint = response.get("scope_fingerprint")
        if not isinstance(reported_fingerprint, str) or not reported_fingerprint:
            raise ToolOperationError("MAINTENANCE_PROPOSAL_SCOPE_FINGERPRINT_MISSING")
        if scope_fingerprint is not None and reported_fingerprint != scope_fingerprint:
            raise ToolOperationError("MAINTENANCE_PROPOSAL_SCOPE_CHANGED_DURING_READ")
        scope_fingerprint = reported_fingerprint
        if total is not None and reported_total != total:
            raise ToolOperationError("MAINTENANCE_PROPOSAL_SCOPE_CHANGED_DURING_READ")
        if total_pages is not None and reported_pages != total_pages:
            raise ToolOperationError("MAINTENANCE_PROPOSAL_SCOPE_CHANGED_DURING_READ")
        if reported_total < 0 or reported_pages < 0:
            raise ToolOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INVALID")
        total = reported_total
        total_pages = reported_pages
        page += 1

    if total is not None and len(records) != total:
        raise ToolOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INCOMPLETE")
    return records


async def apply_grounded_maintenance_proposal(
    project_id, requirement_version_id, impact_analysis, proposal, config
):
    if (
        proposal.get("project_id") != project_id
        or proposal.get("impact_analysis_id") != impact_analysis.get("_id")
        or impact_analysis.get("project_id") != project_id
        or impact_analysis.get("status") != "REVIEWED"
        or not proposal.get("evidence")
    ):
        raise ToolOperationError("MAINTENANCE_PROPOSAL_SOURCE_SCOPE_INVALID")

    proposal_type = proposal.get("proposal_type")
    patch = proposal.get("patch") or {}
    if proposal_type == "UPDATE_TEST_CASE":
        affected = (
            impact_analysis.get("reviewed_affected_test_cases")
            or impact_analysis.get("affected_test_cases")
            or []
        )
        exact_match = any(
            item.get("classification") == "NEEDS_UPDATE"
            and str(item.get("test_case_id") or "")
            == str(proposal.get("target_artifact_id") or "")
            and str(item.get("test_case_version_id") or "")
            == str(proposal.get("base_version_id") or "")
            and bool(item.get("ai_maintenance_patch"))
            for item in affected
        )
        if not exact_match:
            raise ToolOperationError("MAINTENANCE_PROPOSAL_TARGET_NOT_VERIFIED")
    elif proposal_type == "CREATE_TEST_CASE":
        if requirement_version_id not in set(patch.get("requirement_version_ids") or []):
            raise ToolOperationError("MAINTENANCE_PROPOSAL_REQUIREMENT_SCOPE_INVALID")
        if not patch.get("title") or not patch.get("steps"):
            raise ToolOperationError("MAINTENANCE_PROPOSAL_TEST_CASE_INCOMPLETE")
    else:
        raise ToolOperationError("MAINTENANCE_PROPOSAL_TYPE_NOT_AUTOMATABLE")

    if proposal.get("status") in {"PENDING", "APPLY_PARTIAL", "APPLYING"}:
        await require_operation(
            "POST",
            f"/de-xuat-bao-tri/{proposal['_id']}/chap-nhan",
            config,
            {
                "expected_revision": proposal["revision"],
                "review_note": 'Tự động áp dụng sau khi xác minh đúng dự án, phân tích tác động đã rà soát, phiên bản nguồn và kiểm tra chất lượng.',
            },
        )

    applied = await require_operation("GET", f"/de-xuat-bao-tri/{proposal['_id']}", config)
    if (
        applied.get("project_id") != project_id
        or applied.get("impact_analysis_id") != impact_analysis.get("_id")
        or applied.get("status") not in {"ACCEPTED", "EDITED_ACCEPTED"}
        or not applied.get("applied_artifact_id")
    ):
        raise ToolOperationError("MAINTENANCE_PROPOSAL_APPLY_READBACK_INVALID")

    artifact_id = str(applied["applied_artifact_id"])
    if proposal_type == "UPDATE_TEST_CASE":
        version = await require_operation("GET", f"/phien-ban-ca-kiem-thu/{artifact_id}", config)
        case = await require_operation(
            "GET", f"/ca-kiem-thu/{proposal['target_artifact_id']}", config
        )
        current_version_id = case.get("current_version_id") or (
            (case.get("current_version") or {}).get("_id")
        )
        if (
            version.get("_id") != artifact_id
            or version.get("project_id") != project_id
            or version.get("test_case_id") != proposal.get("target_artifact_id")
            or version.get("parent_version_id") != proposal.get("base_version_id")
            or version.get("status") != "ACTIVE"
            or current_version_id != artifact_id
            or requirement_version_id not in set(version.get("requirement_version_ids") or [])
        ):
            raise ToolOperationError("MAINTENANCE_TEST_CASE_VERSION_READBACK_INVALID")
        return {
            "proposal_id": proposal["_id"],
            "test_case_id": proposal["target_artifact_id"],
            "test_case_version_id": artifact_id,
            "proposal_type": proposal_type,
        }

    draft = await require_operation("GET", f"/ban-nhap-ca-kiem-thu/{artifact_id}", config)
    if (
        draft.get("_id") != artifact_id
        or draft.get("project_id") != project_id
        or draft.get("origin") != "maintenance"
        or requirement_version_id not in set(draft.get("requirement_version_ids") or [])
        or requirement_version_id not in set(draft.get("evidence_refs") or [])
    ):
        raise ToolOperationError("MAINTENANCE_TEST_CASE_DRAFT_READBACK_INVALID")
    lint = await require_operation(
        "POST", f"/ban-nhap-ca-kiem-thu/{artifact_id}/kiem-tra", config
    )
    if lint.get("valid") is not True:
        raise ToolOperationError("MAINTENANCE_TEST_CASE_QUALITY_FAILED")
    case, version, status = await publish_grounded_test_case(project_id, draft, config)
    if status != "SUCCESS" or version.get("status") != "ACTIVE":
        raise ToolOperationError("MAINTENANCE_TEST_CASE_PUBLICATION_FAILED")
    return {
        "proposal_id": proposal["_id"],
        "test_case_id": case["_id"],
        "test_case_version_id": version["_id"],
        "proposal_type": proposal_type,
    }


@with_tool_access(("requirement",), "MUTATE", "ai.generate_testcase")
async def process_changed_requirement_version(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    requirement_version_id: Annotated[
        str, Field(min_length=1, description="Changed Requirement version identifier")
    ],
    config: RunnableConfig = None,
) -> str:
    """Continue the Requirement lifecycle after a version change using only its linked evidence"""
    permissions = set((config or {}).get("configurable", {}).get("permissions", []))
    required_permissions = {
        "requirement.read",
        "requirement.review",
        "requirement.version.read",
        "ai.generate_testcase",
        "testcase.create",
        "testcase.read",
        "testcase.lint",
        "testcase.submit_review",
        "ai.run_lint",
        "changeset.create",
        "changeset.review",
        "impact.execute",
        "impact.review",
        "impact.close",
        "ai.run_impact",
        "ai.create_proposal",
        "proposal.read",
    }
    missing = sorted(required_permissions - permissions)
    if missing:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "REQUIRED_PERMISSION_MISSING",
                "missing_permissions": missing,
            }
        )

    version = await require_operation("GET", f"/phien-ban-yeu-cau/{requirement_version_id}", config)
    if version.get("project_id") != project_id or not version.get("requirement_id"):
        raise RuntimeError("REQUIREMENT_VERSION_SCOPE_INVALID")
    requirement = await require_operation("GET", f"/yeu-cau/{version['requirement_id']}", config)
    current_version = requirement.get("current_version") or version
    if current_version.get("_id") != requirement_version_id:
        raise RuntimeError("REQUIREMENT_VERSION_NOT_CURRENT")
    if current_version.get("status") == "DRAFT":
        await require_operation(
            "POST",
            f"/phien-ban-yeu-cau/{requirement_version_id}/phieu-lam-ro/tao-tu-ra-soat",
            config,
        )
    open_clarifications = await resolve_answered_clarifications(current_version, config)
    if open_clarifications:
        return json.dumps(
            {
                "status": "awaiting_input",
                "reason_code": "REQUIREMENT_CLARIFICATION_REQUIRED",
                "requirement_version_id": requirement_version_id,
                "clarification_ids": [
                    item.get("_id") for item in open_clarifications if item.get("_id")
                ],
                "verification": {
                    "status": "AWAITING_INPUT",
                    "project_id": project_id,
                    "artifact_ids": [
                        requirement_version_id,
                        *[str(item["_id"]) for item in open_clarifications if item.get("_id")],
                    ],
                    "checks": [
                        {
                            "artifact_id": requirement_version_id,
                            "artifact_type": "requirement_version",
                        },
                        *[
                            {
                                "artifact_id": str(item["_id"]),
                                "artifact_type": "requirement_clarification",
                            }
                            for item in open_clarifications
                            if item.get("_id")
                        ],
                    ],
                },
            },
            ensure_ascii=False,
        )
    try:
        requirement_quality = await assess_changed_requirement_quality(
            project_id, current_version, config
        )
    except ToolOperationError as error:
        return json.dumps(
            {
                "status": "partial_failure",
                "reason_code": error.reason_code,
                "requirement_version_id": requirement_version_id,
                "unresolved": [{"reason": error.reason_code}],
            },
            ensure_ascii=False,
        )
    if not requirement_quality_allows_ai_publication(requirement_quality):
        return json.dumps(
            {
                "status": "partial_failure",
                "reason_code": "REQUIREMENT_QUALITY_GATE_FAILED",
                "requirement_version_id": requirement_version_id,
                "requirement_quality": requirement_quality,
                "unresolved": [
                    {
                        "reason": "REQUIREMENT_QUALITY_GATE_FAILED",
                        "analysis_id": requirement_quality["analysis_id"],
                    }
                ],
                "verification": {
                    "status": "INCOMPLETE",
                    "project_id": project_id,
                    "artifact_ids": [requirement_version_id, requirement_quality["analysis_id"]],
                    "checks": [
                        {
                            "artifact_id": requirement_version_id,
                            "artifact_type": "requirement_version",
                        },
                        {
                            "artifact_id": requirement_quality["analysis_id"],
                            "artifact_type": "requirement_quality_analysis",
                        },
                    ],
                },
            },
            ensure_ascii=False,
        )
    requirement_versions = await require_operation(
        "GET", f"/yeu-cau/{version['requirement_id']}/phien-ban", config
    )
    previous_version = next(
        (
            item
            for item in response_items(requirement_versions)
            if item.get("_id") != requirement_version_id and item.get("status") == "BASELINED"
        ),
        None,
    )
    unresolved = []
    if version.get("status") != "BASELINED":
        try:
            version = await publish_grounded_requirement(
                project_id, requirement, version, config
            )
            current_version = version
        except ToolOperationError as error:
            return json.dumps(
                {
                    "status": "partial_failure",
                    "reason_code": error.reason_code,
                    "requirement_version_id": requirement_version_id,
                    "unresolved": [{"reason": error.reason_code}],
                    "verification": {"status": "FAILED", "project_id": project_id},
                },
                ensure_ascii=False,
            )

    maintenance_artifact_ids = []
    carried_forward_test_case_ids = []
    if previous_version:
        try:
            change_set = await require_operation(
                "POST",
                f"/yeu-cau/{version['requirement_id']}/bo-thay-doi",
                config,
                {
                    "from_version_id": previous_version["_id"],
                    "to_version_id": requirement_version_id,
                },
            )
            if change_set.get("status") == "READY" and change_set.get("changes"):
                change_set = await require_operation(
                    "POST",
                    f"/bo-thay-doi/{change_set['_id']}/ra-soat",
                    config,
                    {
                        "expected_revision": change_set["revision"],
                        "changes": change_set["changes"],
                        "review_note": 'AI tự động xác minh khác biệt giữa hai phiên bản Requirement có nguồn.',
                    },
                )
            if change_set.get("status") == "REVIEWED":
                analysis = await require_operation(
                    "POST",
                    f"/bo-thay-doi/{change_set['_id']}/phan-tich-anh-huong",
                    config,
                    timeout=settings.MODEL_TIMEOUT_SECONDS,
                )
                if analysis.get("status") == "REVIEW_READY":
                    analysis = await require_operation(
                        "POST",
                        f"/phan-tich-anh-huong/{analysis['_id']}/ra-soat",
                        config,
                        {
                            "expected_revision": analysis["revision"],
                            "overrides": [],
                            "review_note": 'AI tự động rà soát tác động dựa trên trace và bằng chứng của Requirement mới.',
                        },
                    )
                if analysis.get("status") == "REVIEWED":
                    (
                        carried_forward_test_case_ids,
                        carry_forward_unresolved,
                    ) = await carry_forward_unchanged_requirement_tests(
                        project_id,
                        version["requirement_id"],
                        version,
                        response_items(requirement_versions),
                        analysis,
                        config,
                    )
                    maintenance_artifact_ids.extend(carried_forward_test_case_ids)
                    unresolved.extend(carry_forward_unresolved)
                    proposals = await list_all_impact_proposals(
                        project_id, analysis["_id"], config
                    )
                    if not proposals:
                        created_proposals = await require_operation(
                            "POST",
                            f"/phan-tich-anh-huong/{analysis['_id']}/de-xuat-bao-tri",
                            config,
                            timeout=settings.MODEL_TIMEOUT_SECONDS,
                        )
                        proposals = await list_all_impact_proposals(
                            project_id, analysis["_id"], config
                        )
                        if response_items(created_proposals) and not proposals:
                            raise ToolOperationError(
                                "MAINTENANCE_PROPOSAL_PERSISTENCE_READBACK_EMPTY"
                            )
                    for proposal in response_items(proposals):
                        if proposal.get("status") not in {
                            "PENDING",
                            "APPLY_PARTIAL",
                            "APPLYING",
                            "ACCEPTED",
                            "EDITED_ACCEPTED",
                        }:
                            unresolved.append(
                                {
                                    "proposal_id": proposal.get("_id"),
                                    "reason": "MAINTENANCE_PROPOSAL_STATE_NOT_AUTOMATABLE",
                                }
                            )
                            continue
                        try:
                            applied_proposal = await apply_grounded_maintenance_proposal(
                                project_id,
                                requirement_version_id,
                                analysis,
                                proposal,
                                config,
                            )
                            maintenance_artifact_ids.append(
                                applied_proposal["test_case_version_id"]
                            )
                        except (ToolOperationError, KeyError, RuntimeError) as error:
                            unresolved.append(
                                {
                                    "proposal_id": proposal.get("_id"),
                                    "reason": str(error)
                                    or "MAINTENANCE_PROPOSAL_APPLY_FAILED",
                                }
                            )
                elif analysis.get("status") != "REVIEWED":
                    unresolved.append(
                        {
                            "impact_analysis_id": analysis.get("_id"),
                            "reason": "IMPACT_ANALYSIS_NOT_REVIEWED",
                        }
                    )
            elif change_set.get("status") not in {"REVIEWED", "ANALYZED"} and change_set.get(
                "changes"
            ):
                unresolved.append(
                    {
                        "change_set_id": change_set.get("_id"),
                        "reason": "REQUIREMENT_CHANGE_SET_NOT_REVIEWED",
                    }
                )
        except RuntimeError as error:
            unresolved.append(
                {"requirement_version_id": requirement_version_id, "reason": str(error)}
            )

    criteria_ids = list(dict.fromkeys(
        str(value)
        for value in (
            version.get("acceptance_criterion_ids")
            or [item.get("_id") for item in version.get("acceptance_criteria", []) if item.get("_id")]
        )
        if value
    ))
    if not criteria_ids:
        return json.dumps(
            {
                "status": "partial_failure",
                "reason_code": "NO_ACCEPTANCE_CRITERIA",
                "requirement_version_id": requirement_version_id,
            }
        )
    existing_cases = await list_all_test_case_records(
        project_id, version["requirement_id"], config
    )
    covered_by_active_cases = {
        str(criterion_id)
        for item in existing_cases
        if item.get("status") == "ACTIVE" and item.get("stale_status") != "STALE"
        for criterion_id in (item.get("current_version") or {}).get("acceptance_criterion_ids", [])
    }
    pending_drafts = await list_resumable_ai_test_case_drafts(
        project_id, requirement_version_id, config
    )
    covered_by_pending_drafts = {
        str(criterion_id)
        for item in pending_drafts
        for criterion_id in item.get("acceptance_criterion_ids", [])
    }
    already_covered = covered_by_active_cases | covered_by_pending_drafts
    missing_before_generation = set(criteria_ids) - already_covered
    request = {
        "categories": [],
        "max_cases": min(len(missing_before_generation), 50),
        "preview_only": True,
        "acceptance_criterion_ids": sorted(missing_before_generation),
        "instruction": requirement_test_generation_instruction(),
    }
    preview = {"items": [], "warnings": []}
    if missing_before_generation:
        preview = await require_operation(
            "POST",
            f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu",
            config,
            request,
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
    generation_warning_attempts = [list(preview.get("warnings") or [])]
    generated = preview.get("items") or []
    covered_ids = set()
    novel = []
    version_updates = []
    version_targets = set()
    skipped_duplicates = len(already_covered)
    warnings = []
    for item in generated:
        draft = item.get("draft") or {}
        matches = item.get("similar_cases") or []
        new_criteria = set(map(str, item.get("new_criterion_ids") or []))
        draft_criteria = set(map(str, draft.get("acceptance_criterion_ids") or []))
        if not draft or not draft_criteria <= set(criteria_ids):
            warnings.append("TEST_CASE_ACCEPTANCE_CRITERION_LINK_INVALID")
            skipped_duplicates += 1
        elif (
            matches
            and next((match for match in matches if match.get("target_version_id")), None)
            and new_criteria
            and next(match["target_version_id"] for match in matches if match.get("target_version_id")) not in version_targets
        ):
            target_version_id = next(
                match["target_version_id"] for match in matches if match.get("target_version_id")
            )
            version_targets.add(target_version_id)
            version_updates.append(
                {
                    **draft,
                    "target_version_id": target_version_id,
                    "version_reason": "Update the Test Case to cover the changed Requirement version.",
                }
            )
            covered_ids.update(draft_criteria)
        elif matches:
            skipped_duplicates += 1
        else:
            novel.append(draft)
            covered_ids.update(draft_criteria)

    required_ids = set(map(str, preview.get("criterion_coverage", {}).get("criterion_ids") or missing_before_generation))
    already_linked_ids = set(map(str, preview.get("criterion_coverage", {}).get("linked_criterion_ids") or []))
    missing_ids = required_ids - already_linked_ids - covered_by_pending_drafts - covered_ids
    if missing_ids:
        focused = await require_operation(
            "POST",
            f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu",
            config,
            {
                **request,
                "acceptance_criterion_ids": sorted(missing_ids),
                "max_cases": min(len(missing_ids), 50),
                "instruction": focused_requirement_test_generation_instruction(),
            },
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
        generation_warning_attempts.append(list(focused.get("warnings") or []))
        for item in focused.get("items") or []:
            draft = item.get("draft") or {}
            matches = item.get("similar_cases") or []
            draft_criteria = set(map(str, draft.get("acceptance_criterion_ids") or []))
            target = next((match for match in matches if match.get("target_version_id")), None)
            if target and draft and draft_criteria.intersection(missing_ids) and target["target_version_id"] not in version_targets:
                version_targets.add(target["target_version_id"])
                version_updates.append({
                    **draft,
                    "target_version_id": target["target_version_id"],
                    "version_reason": "Update the Test Case to cover the changed Requirement version.",
                })
                covered_ids.update(draft_criteria)
            elif matches:
                skipped_duplicates += 1
            elif draft and draft_criteria.intersection(missing_ids) and draft_criteria <= set(criteria_ids):
                if normalized_text(draft.get("title")) not in {
                    normalized_text(case.get("title")) for case in novel
                }:
                    novel.append(draft)
                    covered_ids.update(draft_criteria)
        missing_ids = required_ids - already_linked_ids - covered_by_pending_drafts - covered_ids
    if missing_ids:
        unresolved.append({
            "requirement_version_id": requirement_version_id,
            "reason": "ACCEPTANCE_CRITERIA_NOT_COVERED",
            "missing_acceptance_criterion_ids": sorted(missing_ids),
        })

    created_drafts = list(pending_drafts)
    approved_cases = []
    approved_case_versions = []
    drafts_to_save = [*novel, *version_updates]
    if len(drafts_to_save) > 1:
        comparison = await require_operation(
            "POST",
            f"/du-an/{project_id}/ca-kiem-thu/trung-lap/ban-nhap",
            config,
            {"items": drafts_to_save},
        )
        if comparison.get("candidate_count") != len(drafts_to_save):
            raise RuntimeError("TEST_CASE_BATCH_COMPARISON_READBACK_INVALID")
        drafts_to_save, consolidated_count, duplicate_conflicts = (
            consolidate_duplicate_test_case_drafts(
                drafts_to_save, comparison.get("duplicates") or []
            )
        )
        skipped_duplicates += consolidated_count
        unresolved.extend(duplicate_conflicts)
    if drafts_to_save:
        saved = await require_operation(
            "POST", f"/du-an/{project_id}/ban-nhap-ca-kiem-thu/lo", config, drafts_to_save
        )
        created_drafts = saved if isinstance(saved, list) else saved.get("items", [])
        if len(created_drafts) != len(drafts_to_save):
            raise RuntimeError("TEST_CASE_BATCH_READBACK_INVALID")
    for draft in created_drafts:
        lint = await require_operation("POST", f"/ca-kiem-thu/{draft['_id']}/kiem-tra", config)
        if not lint.get("valid"):
            unresolved.append(
                {"test_case_draft_id": draft["_id"], "reason": "TEST_CASE_QUALITY_FAILED"}
            )
            continue
        try:
            case, frozen_version, publication_status = await publish_grounded_test_case(
                project_id, draft, config
            )
            approved_cases.append(case)
            approved_case_versions.append(frozen_version)
            if publication_status != "SUCCESS":
                warnings.append(f"TEST_CASE_PUBLICATION_DEGRADED:{case['_id']}")
        except ToolOperationError as error:
            unresolved.append({"test_case_draft_id": draft["_id"], "reason": error.reason_code})
        except (KeyError, RuntimeError) as error:
            unresolved.append({
                "test_case_draft_id": draft["_id"],
                "reason": str(error) or "TEST_CASE_PUBLICATION_FAILED",
            })

    readback = await require_operation(
        "GET", f"/phien-ban-yeu-cau/{requirement_version_id}", config
    )
    if readback.get("_id") != requirement_version_id or readback.get("status") != "BASELINED":
        raise RuntimeError("REQUIREMENT_BASELINE_READBACK_INVALID")
    for case, frozen_version in zip(
        approved_cases, approved_case_versions, strict=True
    ):
        case_readback = await require_operation(
            "GET", f"/ca-kiem-thu/{case['_id']}", config
        )
        version_readback = await require_operation(
            "GET", f"/phien-ban-ca-kiem-thu/{frozen_version['_id']}", config
        )
        if not verified_test_case_publication_readback(
            project_id, case, frozen_version, case_readback, version_readback
        ):
            raise RuntimeError("TEST_CASE_VERSION_READBACK_INVALID")
    artifacts = [{"artifact_id": requirement_version_id, "artifact_type": "requirement_version"}]
    artifacts.append(
        {
            "artifact_id": requirement_quality["analysis_id"],
            "artifact_type": "requirement_quality_analysis",
        }
    )
    for case, frozen_version in zip(approved_cases, approved_case_versions, strict=True):
        artifacts.extend(
            [
                {"artifact_id": case["_id"], "artifact_type": "test_case"},
                {"artifact_id": frozen_version["_id"], "artifact_type": "test_case_version"},
            ]
        )
    artifacts = list(
        {
            (item["artifact_type"], str(item["artifact_id"])): item
            for item in artifacts
        }.values()
    )
    if unresolved:
        outcome = "partial_failure"
    else:
        outcome = "COMPLETED"
    return json.dumps(
        {
            "status": outcome,
            **({"reason_code": unresolved[0]["reason"]} if unresolved else {}),
            "requirement_version_id": requirement_version_id,
            "requirement_quality": requirement_quality,
            "approved_test_case_ids": [item["_id"] for item in approved_cases],
            "test_case_draft_ids": [item["_id"] for item in created_drafts],
            "maintenance_artifact_ids": list(dict.fromkeys(maintenance_artifact_ids)),
            "carried_forward_test_case_ids": list(dict.fromkeys(carried_forward_test_case_ids)),
            "skipped_duplicate_count": skipped_duplicates,
            "generation_warnings": list(
                dict.fromkeys(
                    [
                        *warnings,
                        *finalized_generation_warnings(
                            generation_warning_attempts,
                            coverage_complete=not missing_ids,
                        ),
                    ]
                )
            ),
            "unresolved": unresolved,
            "verification": {
                "status": "COMPLETED" if not unresolved else "INCOMPLETE",
                "project_id": project_id,
                "artifact_ids": [item["artifact_id"] for item in artifacts],
                "checks": artifacts,
            },
        },
        ensure_ascii=False,
        default=str,
    )
