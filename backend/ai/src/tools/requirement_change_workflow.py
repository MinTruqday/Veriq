import json
import re
from typing import Annotated
from urllib.parse import urlencode

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.prompts.test_generation import requirement_test_generation_instruction
from src.schemas.automation import AutomationFact
from src.services.testability_blueprint import (
    compile_testability_blueprint,
    obligations_supported_by_requirement_version,
    requirement_version_source_segments,
    requirement_version_source_text,
)
from src.tools.automation_publication import (
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
from src.tools.testing_api import AutomationOperationError, require_operation


def requirement_version_source_facts(version, event_facts=()):
    version_id = str(version.get("_id") or "")
    segments = requirement_version_source_segments(version)
    text = requirement_version_source_text(version)
    if not version_id or not text.strip():
        return [], {}

    facts = []
    cursor = 0
    for fact_kind, source_segment in segments:
        for sentence in re.split(r"(?<=[.!?。！？])\s+", source_segment):
            quote = sentence.strip()
            if not quote:
                continue
            start = text.find(quote, cursor)
            if start < 0:
                continue
            cursor = start + len(quote)
            facts.append(
                AutomationFact(
                    artifact_type="requirement_version",
                    artifact_id=version_id,
                    artifact_version_id=version_id,
                    source="requirement_version_readback",
                    authority="PROJECT_REQUIREMENT",
                    quote=quote,
                    fact_kind=fact_kind,
                    source_start=start,
                    source_end=start + len(quote),
                    source_offset_basis="CANONICAL_TEXT",
                )
            )
    for item in event_facts:
        if item.artifact_version_id != version_id or not item.quote:
            continue
        start, end = item.source_start, item.source_end
        if start is not None or end is not None:
            if (
                start is None
                or end is None
                or end - start != len(item.quote)
                or text[start:end] != item.quote
            ):
                continue
        else:
            start = text.find(item.quote)
            if start < 0 or text.find(item.quote, start + 1) >= 0:
                continue
            end = start + len(item.quote)
        facts.append(
            AutomationFact(
                artifact_type="requirement_version",
                artifact_id=version_id,
                artifact_version_id=version_id,
                source="requirement_version_readback",
                authority="PROJECT_REQUIREMENT",
                quote=item.quote,
                fact_kind=item.fact_kind,
                source_start=start,
                source_end=end,
                source_offset_basis="CANONICAL_TEXT",
            )
        )
    facts = list(
        {(item.source_start, item.source_end, item.quote): item for item in facts}.values()
    )
    evidence = {
        version_id: {
            "artifact_type": "requirement_version",
            "artifact_id": version_id,
            "artifact_version_id": version_id,
            "text": text,
            "source": "requirement_version_readback",
            "authority": "PROJECT_REQUIREMENT",
            "source_offset_basis": "CANONICAL_TEXT",
        }
    }
    return facts, evidence


def finalized_generation_warnings(attempts, *, coverage_complete):
    selected_attempts = attempts[-1:] if coverage_complete and attempts else attempts
    return list(dict.fromkeys(str(warning) for attempt in selected_attempts for warning in attempt))


async def assess_changed_requirement_quality(project_id, version, config):
    version_id = str(version.get("_id") or "")
    revision = version.get("revision")
    if not version_id or not isinstance(revision, int) or isinstance(revision, bool):
        raise AutomationOperationError("REQUIREMENT_QUALITY_SOURCE_REVISION_INVALID")
    idempotency_key = f"requirement-quality-event:{version_id}:{revision}"
    result = await require_operation(
        "POST",
        f"/phien-ban-yeu-cau/{version_id}/ai/kiem-tra",
        config,
        {
            "idempotency_key": idempotency_key,
            "instruction": "Đánh giá khả năng hiểu và kiểm thử của đúng phiên bản Requirement này; chỉ ghi nhận vấn đề có căn cứ, không tự sửa nội dung.",
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
        raise AutomationOperationError("REQUIREMENT_QUALITY_READBACK_INVALID")
    findings = result.get("findings")
    if not isinstance(findings, list) or any(
        not isinstance(item, dict)
        or item.get("severity") not in {"error", "warning", "info"}
        for item in findings
    ):
        raise AutomationOperationError("REQUIREMENT_QUALITY_FINDINGS_INVALID")
    status = result.get("status")
    if status not in {"SUCCESS", "DEGRADED", "FAILED"}:
        raise AutomationOperationError("REQUIREMENT_QUALITY_STATUS_INVALID")
    degraded_mode = result.get("degraded_mode")
    if not isinstance(result.get("valid"), bool) or not isinstance(degraded_mode, bool):
        raise AutomationOperationError("REQUIREMENT_QUALITY_STATUS_INVALID")
    return {
        "analysis_id": str(result["_id"]),
        "status": status,
        "valid": result["valid"],
        "degraded_mode": degraded_mode,
        "finding_count": len(findings),
        "blocking_finding_count": sum(
            item.get("severity") == "error" for item in findings
        ),
    }


def requirement_quality_allows_automatic_publication(assessment):
    return (
        isinstance(assessment, dict)
        and assessment.get("status") == "SUCCESS"
        and assessment.get("valid") is True
        and assessment.get("degraded_mode") is not True
        and assessment.get("blocking_finding_count") == 0
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
                raise AutomationOperationError("MAINTENANCE_PROPOSAL_PAGINATION_DUPLICATE")
            if (
                item.get("project_id") != project_id
                or item.get("impact_analysis_id") != impact_analysis_id
            ):
                raise AutomationOperationError("MAINTENANCE_PROPOSAL_SCOPE_INVALID")
            seen_ids.add(identifier)
            records.append(item)

        if not isinstance(response, dict):
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INVALID")
        try:
            reported_total = int(response["total"])
            reported_pages = int(response["total_pages"])
            reported_page = int(response["page"])
            reported_page_size = int(response["page_size"])
        except (KeyError, TypeError, ValueError) as error:
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INVALID") from error
        if reported_page != page or reported_page_size != page_size:
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INVALID")
        reported_fingerprint = response.get("scope_fingerprint")
        if not isinstance(reported_fingerprint, str) or not reported_fingerprint:
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_SCOPE_FINGERPRINT_MISSING")
        if scope_fingerprint is not None and reported_fingerprint != scope_fingerprint:
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_SCOPE_CHANGED_DURING_READ")
        scope_fingerprint = reported_fingerprint
        if total is not None and reported_total != total:
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_SCOPE_CHANGED_DURING_READ")
        if total_pages is not None and reported_pages != total_pages:
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_SCOPE_CHANGED_DURING_READ")
        if reported_total < 0 or reported_pages < 0:
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INVALID")
        total = reported_total
        total_pages = reported_pages
        page += 1

    if total is not None and len(records) != total:
        raise AutomationOperationError("MAINTENANCE_PROPOSAL_PAGINATION_INCOMPLETE")
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
        raise AutomationOperationError("MAINTENANCE_PROPOSAL_SOURCE_SCOPE_INVALID")

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
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_TARGET_NOT_VERIFIED")
    elif proposal_type == "CREATE_TEST_CASE":
        if requirement_version_id not in set(patch.get("requirement_version_ids") or []):
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_REQUIREMENT_SCOPE_INVALID")
        if not patch.get("title") or not patch.get("steps"):
            raise AutomationOperationError("MAINTENANCE_PROPOSAL_TEST_CASE_INCOMPLETE")
    else:
        raise AutomationOperationError("MAINTENANCE_PROPOSAL_TYPE_NOT_AUTOMATABLE")

    if proposal.get("status") in {"PENDING", "APPLY_PARTIAL", "APPLYING"}:
        await require_operation(
            "POST",
            f"/de-xuat-bao-tri/{proposal['_id']}/chap-nhan",
            config,
            {
                "expected_revision": proposal["revision"],
                "review_note": (
                    "Tự động áp dụng sau khi xác minh đúng dự án, phân tích tác động đã rà soát, "
                    "phiên bản nguồn và kiểm tra chất lượng."
                ),
            },
        )

    applied = await require_operation("GET", f"/de-xuat-bao-tri/{proposal['_id']}", config)
    if (
        applied.get("project_id") != project_id
        or applied.get("impact_analysis_id") != impact_analysis.get("_id")
        or applied.get("status") not in {"ACCEPTED", "EDITED_ACCEPTED"}
        or not applied.get("applied_artifact_id")
    ):
        raise AutomationOperationError("MAINTENANCE_PROPOSAL_APPLY_READBACK_INVALID")

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
            raise AutomationOperationError("MAINTENANCE_TEST_CASE_VERSION_READBACK_INVALID")
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
        raise AutomationOperationError("MAINTENANCE_TEST_CASE_DRAFT_READBACK_INVALID")
    lint = await require_operation(
        "POST", f"/ban-nhap-ca-kiem-thu/{artifact_id}/kiem-tra", config
    )
    if lint.get("valid") is not True:
        raise AutomationOperationError("MAINTENANCE_TEST_CASE_QUALITY_FAILED")
    case, version, status = await publish_grounded_test_case(project_id, draft, config)
    if status != "SUCCESS" or version.get("status") != "ACTIVE":
        raise AutomationOperationError("MAINTENANCE_TEST_CASE_PUBLICATION_FAILED")
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
    source_facts: Annotated[
        list[AutomationFact], Field(description="Verified facts from the changed Requirement event")
    ] = Field(default_factory=list),
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
                "status": "automation_blocked",
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
    blueprint_facts, evidence_by_ref = requirement_version_source_facts(
        current_version, source_facts
    )
    allowed_source_ids = {item.artifact_id for item in blueprint_facts}
    blueprint = await compile_testability_blueprint(
        project_id, blueprint_facts, evidence_by_ref, allowed_source_ids
    )
    if blueprint.get("status") != "SUCCESS":
        return json.dumps(
            {
                "status": "automation_partial_failure",
                "reason_code": "TESTABILITY_BLUEPRINT_COMPILATION_FAILED",
                "requirement_version_id": requirement_version_id,
                "blueprint_reason_codes": blueprint.get("reason_codes", []),
                "blueprint_warnings": blueprint.get("warnings", []),
                "unresolved": [{"reason": "TESTABILITY_BLUEPRINT_COMPILATION_FAILED"}],
            },
            ensure_ascii=False,
        )
    version_obligations, unlinked_obligations = obligations_supported_by_requirement_version(
        current_version, blueprint.get("obligations", []), evidence_by_ref
    )
    if unlinked_obligations:
        return json.dumps(
            {
                "status": "automation_partial_failure",
                "reason_code": "BLUEPRINT_OBLIGATIONS_NOT_SUPPORTED_BY_REQUIREMENT_VERSION",
                "requirement_version_id": requirement_version_id,
                "obligation_keys": [item.get("key") for item in unlinked_obligations],
                "testability_blueprint": blueprint,
            },
            ensure_ascii=False,
        )
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
                "status": "automation_waiting_for_input",
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
    except AutomationOperationError as error:
        return json.dumps(
            {
                "status": "automation_partial_failure",
                "reason_code": error.reason_code,
                "requirement_version_id": requirement_version_id,
                "unresolved": [{"reason": error.reason_code}],
            },
            ensure_ascii=False,
        )
    if not requirement_quality_allows_automatic_publication(requirement_quality):
        return json.dumps(
            {
                "status": "automation_partial_failure",
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
        except AutomationOperationError as error:
            return json.dumps(
                {
                    "status": "automation_partial_failure",
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
                        "review_note": "AI tự động xác minh khác biệt giữa hai phiên bản Requirement có nguồn",
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
                            "review_note": "AI tự động rà soát tác động dựa trên trace và bằng chứng của Requirement mới",
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
                            raise AutomationOperationError(
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
                        except (AutomationOperationError, KeyError, RuntimeError) as error:
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

    criteria_ids = version.get("acceptance_criterion_ids") or [
        item.get("_id") for item in version.get("acceptance_criteria", []) if item.get("_id")
    ]
    if not criteria_ids:
        return json.dumps(
            {
                "status": "automation_partial_failure",
                "reason_code": "NO_ACCEPTANCE_CRITERIA",
                "requirement_version_id": requirement_version_id,
            }
        )
    existing_cases = await list_all_test_case_records(
        project_id, version["requirement_id"], config
    )
    covered_by_active_cases = {
        criterion_id
        for item in existing_cases
        if item.get("status") == "ACTIVE" and item.get("stale_status") != "STALE"
        for criterion_id in (item.get("current_version") or {}).get("acceptance_criterion_ids", [])
    }
    covered_by_active_obligations = {
        str(key)
        for item in existing_cases
        if item.get("status") == "ACTIVE" and item.get("stale_status") != "STALE"
        for key in (item.get("current_version") or {}).get("coverage_obligations", [])
    }
    pending_drafts = await list_resumable_ai_test_case_drafts(
        project_id, requirement_version_id, config
    )
    covered_by_pending_drafts = {
        criterion_id
        for item in pending_drafts
        for criterion_id in item.get("acceptance_criterion_ids", [])
    }
    covered_by_pending_obligations = {
        str(key) for item in pending_drafts for key in item.get("coverage_obligations", [])
    }
    already_covered = covered_by_active_cases | covered_by_pending_drafts
    missing_before_generation = set(criteria_ids) - already_covered
    request = {
        "categories": [],
        "max_cases": len(missing_before_generation),
        "preview_only": True,
        "acceptance_criterion_ids": sorted(missing_before_generation),
        "instruction": requirement_test_generation_instruction(version_obligations),
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
    generated = preview.get("items") or []
    required_ids = missing_before_generation
    covered_ids = set()
    novel = []
    version_updates = []
    version_targets = set()
    skipped_duplicates = len(already_covered)
    warnings = []
    generation_warning_attempts = [list(preview.get("warnings") or [])]
    obligation_keys = {str(item.get("key")) for item in version_obligations if item.get("key")}
    covered_obligation_keys = (
        covered_by_active_obligations | covered_by_pending_obligations
    ) & obligation_keys
    blueprint_artifact_coverage = {
        key: {
            "obligation_key": key,
            "requirement_version_ids": [requirement_version_id],
            "test_case_ids": [],
            "test_case_version_ids": [],
        }
        for key in obligation_keys
    }
    for case in existing_cases:
        if case.get("status") != "ACTIVE" or case.get("stale_status") == "STALE":
            continue
        current_version = case.get("current_version") or {}
        for key in current_version.get("coverage_obligations") or []:
            entry = blueprint_artifact_coverage.get(str(key))
            if not entry:
                continue
            if case.get("_id"):
                entry["test_case_ids"].append(str(case["_id"]))
            if current_version.get("_id"):
                entry["test_case_version_ids"].append(str(current_version["_id"]))
    for item in generated:
        draft = item.get("draft") or {}
        matches = item.get("similar_cases") or []
        mapped_obligations = set(
            item.get("coverage_obligations") or draft.get("coverage_obligations") or []
        )
        if obligation_keys and (
            not mapped_obligations or not mapped_obligations <= obligation_keys
        ):
            warnings.append("BLUEPRINT_OBLIGATION_MAPPING_INVALID")
            skipped_duplicates += 1
            continue
        target = next((match for match in matches if match.get("target_version_id")), None)
        new_criteria = set(item.get("new_criterion_ids") or [])
        if target and draft and new_criteria and target["target_version_id"] not in version_targets:
            version_targets.add(target["target_version_id"])
            version_updates.append(
                {
                    **draft,
                    "target_version_id": target["target_version_id"],
                    "version_reason": "Tự động cập nhật liên kết và nội dung ca theo Requirement version mới sau khi đối chiếu trùng và bằng chứng nguồn",
                }
            )
            covered_ids.update(draft.get("acceptance_criterion_ids", []))
            covered_obligation_keys.update(mapped_obligations)
        elif matches:
            skipped_duplicates += 1
        elif draft:
            novel.append(draft)
            covered_ids.update(draft.get("acceptance_criterion_ids", []))
            covered_obligation_keys.update(mapped_obligations)
    missing_ids = required_ids - covered_ids
    if missing_ids:
        focused = await require_operation(
            "POST",
            f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu",
            config,
            {
                **request,
                "acceptance_criterion_ids": sorted(missing_ids),
                "max_cases": len(missing_ids),
            },
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
        generation_warning_attempts.append(list(focused.get("warnings") or []))
        for item in focused.get("items") or []:
            draft = item.get("draft") or {}
            matches = item.get("similar_cases") or []
            mapped_obligations = set(
                item.get("coverage_obligations") or draft.get("coverage_obligations") or []
            )
            if obligation_keys and (
                not mapped_obligations or not mapped_obligations <= obligation_keys
            ):
                warnings.append("BLUEPRINT_OBLIGATION_MAPPING_INVALID")
                skipped_duplicates += 1
                continue
            target = next((match for match in matches if match.get("target_version_id")), None)
            new_criteria = set(item.get("new_criterion_ids") or [])
            if (
                target
                and draft
                and new_criteria
                and target["target_version_id"] not in version_targets
            ):
                version_targets.add(target["target_version_id"])
                version_updates.append(
                    {
                        **draft,
                        "target_version_id": target["target_version_id"],
                        "version_reason": "Tự động cập nhật liên kết và nội dung ca theo Requirement version mới sau khi đối chiếu trùng và bằng chứng nguồn",
                    }
                )
                covered_ids.update(draft.get("acceptance_criterion_ids", []))
                covered_obligation_keys.update(mapped_obligations)
            elif matches:
                skipped_duplicates += 1
            elif draft and normalized_text(draft.get("title")) not in {
                normalized_text(case.get("title")) for case in novel
            }:
                novel.append(draft)
                covered_ids.update(draft.get("acceptance_criterion_ids", []))
                covered_obligation_keys.update(mapped_obligations)
        missing_ids = required_ids - covered_ids
    if missing_ids:
        unresolved.append(
            {
                "requirement_version_id": requirement_version_id,
                "reason": "ACCEPTANCE_CRITERIA_NOT_COVERED",
                "missing_acceptance_criterion_ids": sorted(missing_ids),
            }
        )

    missing_obligations = [
        item for item in version_obligations if str(item.get("key")) not in covered_obligation_keys
    ]
    if missing_obligations:
        obligation_preview = await require_operation(
            "POST",
            f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu",
            config,
            {
                **request,
                "acceptance_criterion_ids": criteria_ids,
                "max_cases": len(missing_obligations),
                "instruction": requirement_test_generation_instruction(missing_obligations),
            },
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
        generation_warning_attempts.append(list(obligation_preview.get("warnings") or []))
        for item in obligation_preview.get("items") or []:
            draft = item.get("draft") or {}
            mapped_obligations = set(
                item.get("coverage_obligations") or draft.get("coverage_obligations") or []
            )
            matches = item.get("similar_cases") or []
            if not draft or not mapped_obligations or not mapped_obligations <= obligation_keys:
                warnings.append("BLUEPRINT_OBLIGATION_MAPPING_INVALID")
                continue
            if matches or normalized_text(draft.get("title")) in {
                normalized_text(case.get("title")) for case in novel
            }:
                skipped_duplicates += 1
                continue
            novel.append(draft)
            covered_ids.update(draft.get("acceptance_criterion_ids", []))
            covered_obligation_keys.update(mapped_obligations)
        missing_obligations = [
            item
            for item in version_obligations
            if str(item.get("key")) not in covered_obligation_keys
        ]
    if missing_obligations:
        unresolved.append(
            {
                "requirement_version_id": requirement_version_id,
                "reason": "TESTABILITY_BLUEPRINT_OBLIGATIONS_NOT_COVERED",
                "obligation_keys": [item.get("key") for item in missing_obligations],
            }
        )

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
        covered_ids = (
            covered_by_active_cases
            | covered_by_pending_drafts
            | {
                str(criterion_id)
                for draft in drafts_to_save
                for criterion_id in draft.get("acceptance_criterion_ids", [])
            }
        )
        covered_obligation_keys = (
            covered_by_active_obligations
            | covered_by_pending_obligations
            | {
                str(key)
                for draft in drafts_to_save
                for key in draft.get("coverage_obligations", [])
            }
        ) & obligation_keys
        missing_ids = required_ids - covered_ids
        missing_obligations = [
            item
            for item in version_obligations
            if str(item.get("key")) not in covered_obligation_keys
        ]
        if missing_ids and not any(
            item.get("reason") == "ACCEPTANCE_CRITERIA_NOT_COVERED"
            for item in unresolved
        ):
            unresolved.append(
                {
                    "requirement_version_id": requirement_version_id,
                    "reason": "ACCEPTANCE_CRITERIA_NOT_COVERED",
                    "missing_acceptance_criterion_ids": sorted(missing_ids),
                }
            )
        if missing_obligations and not any(
            item.get("reason") == "TESTABILITY_BLUEPRINT_OBLIGATIONS_NOT_COVERED"
            for item in unresolved
        ):
            unresolved.append(
                {
                    "requirement_version_id": requirement_version_id,
                    "reason": "TESTABILITY_BLUEPRINT_OBLIGATIONS_NOT_COVERED",
                    "obligation_keys": [item.get("key") for item in missing_obligations],
                }
            )
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
            case_obligation_keys = list(
                draft.get("coverage_obligations")
                or frozen_version.get("coverage_obligations")
                or []
            )
            for key in case_obligation_keys:
                entry = blueprint_artifact_coverage.get(str(key))
                if entry:
                    entry["test_case_ids"].append(str(case["_id"]))
                    entry["test_case_version_ids"].append(str(frozen_version["_id"]))
            if publication_status != "SUCCESS":
                warnings.append(
                    f"TEST_CASE_PUBLICATION_DEGRADED:{case['_id']}"
                )
        except AutomationOperationError as error:
            unresolved.append({
                "test_case_draft_id": draft["_id"],
                "reason": error.reason_code,
            })
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
    for coverage in blueprint_artifact_coverage.values():
        for artifact_type, field in (
            ("test_case", "test_case_ids"),
            ("test_case_version", "test_case_version_ids"),
        ):
            artifacts.extend(
                {"artifact_id": artifact_id, "artifact_type": artifact_type}
                for artifact_id in coverage[field]
            )
        for field in (
            "requirement_version_ids",
            "test_case_ids",
            "test_case_version_ids",
        ):
            coverage[field] = list(dict.fromkeys(coverage[field]))
    artifacts = list(
        {
            (item["artifact_type"], str(item["artifact_id"])): item
            for item in artifacts
        }.values()
    )
    if unresolved:
        outcome = "automation_partial_failure"
    else:
        outcome = "COMPLETED"
    return json.dumps(
        {
            "status": outcome,
            **({"reason_code": unresolved[0]["reason"]} if unresolved else {}),
            "requirement_version_id": requirement_version_id,
            "requirement_quality": requirement_quality,
            "testability_blueprint": blueprint,
            "source_facts": [item.model_dump(mode="json") for item in blueprint_facts],
            "source_evidence": [evidence_by_ref[requirement_version_id]],
            "blueprint_obligation_keys": [item.get("key") for item in version_obligations],
            "covered_blueprint_obligation_keys": sorted(covered_obligation_keys),
            "blueprint_artifact_coverage": list(blueprint_artifact_coverage.values()),
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
                            coverage_complete=not missing_ids and not missing_obligations,
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
