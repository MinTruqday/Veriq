import json
from typing import Annotated
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.tools.registry import with_tool_access
from src.tools.testing import (
    AutomationOperationError,
    call,
    carry_forward_unchanged_requirement_tests,
    compilable_document_ids,
    normalized_text,
    parse,
    plan_clarification_priority,
    require_operation,
    requirement_source_text,
    resolve_answered_clarifications,
    response_items,
)

@with_tool_access(
    ("requirement",),
    "MUTATE",
    "requirement.approve",
)

async def process_changed_requirement_version(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    requirement_version_id: Annotated[str, Field(min_length=1, description="Changed Requirement version identifier")],
    config: RunnableConfig = None,
) -> str:
    """Continue the Requirement lifecycle after a version change using only its linked evidence"""
    permissions = set((config or {}).get("configurable", {}).get("permissions", []))
    required_permissions = {
        "requirement.read", "requirement.review", "requirement.version.read",
        "requirement.submit_review", "requirement.approve",
        "ai.generate_testcase", "testcase.create", "testcase.read", "testcase.lint",
        "testcase.submit_review", "testcase.approve", "ai.run_lint",
        "changeset.create", "changeset.review", "impact.execute", "impact.review",
        "impact.close", "ai.run_impact", "ai.create_proposal", "proposal.read",
        "proposal.approve",
    }
    missing = sorted(required_permissions - permissions)
    if missing:
        return json.dumps({"status": "automation_blocked", "reason_code": "REQUIRED_PERMISSION_MISSING", "missing_permissions": missing})

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
                "status": "automation_partial_failure",
                "reason_code": "REQUIREMENT_CLARIFICATION_REQUIRED",
                "requirement_version_id": requirement_version_id,
                "clarification_ids": [item.get("_id") for item in open_clarifications if item.get("_id")],
            },
            ensure_ascii=False,
        )
    requirement_versions = await require_operation(
        "GET", f"/yeu-cau/{version['requirement_id']}/phien-ban", config
    )
    previous_version = next(
        (
            item for item in response_items(requirement_versions)
            if item.get("_id") != requirement_version_id and item.get("status") == "BASELINED"
        ),
        None,
    )
    unresolved = []
    if version.get("status") == "DRAFT":
        try:
            version = await require_operation(
                "POST", f"/du-an/{project_id}/yeu-cau/{version['requirement_id']}/gui-ra-soat", config,
                {"expected_revision": version["revision"], "review_note": "AI tự động rà nguồn và chất lượng phiên bản Requirement"},
            )
        except RuntimeError as error:
            unresolved.append({"requirement_version_id": requirement_version_id, "reason": str(error)})
    if version.get("status") == "IN_REVIEW":
        try:
            version = await require_operation(
                "POST", f"/phien-ban-yeu-cau/{requirement_version_id}/chot-chuan", config,
                {"expected_revision": version["revision"], "review_note": "AI tự động chốt chuẩn sau khi cổng chất lượng đạt"},
            )
        except RuntimeError as error:
            unresolved.append({"requirement_version_id": requirement_version_id, "reason": str(error)})
    if version.get("status") != "BASELINED":
        return json.dumps({"status": "automation_partial_failure", "reason_code": "REQUIREMENT_NOT_BASELINED", "requirement_version_id": requirement_version_id, "unresolved": unresolved})

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
                    "POST", f"/bo-thay-doi/{change_set['_id']}/ra-soat", config,
                    {
                        "expected_revision": change_set["revision"],
                        "changes": change_set["changes"],
                        "review_note": "AI tự động xác minh khác biệt giữa hai phiên bản Requirement có nguồn",
                    },
                )
            if change_set.get("status") == "REVIEWED":
                analysis = await require_operation(
                    "POST", f"/bo-thay-doi/{change_set['_id']}/phan-tich-anh-huong", config,
                    timeout=settings.MODEL_TIMEOUT_SECONDS,
                )
                if analysis.get("status") == "REVIEW_READY":
                    analysis = await require_operation(
                        "POST", f"/phan-tich-anh-huong/{analysis['_id']}/ra-soat", config,
                        {
                            "expected_revision": analysis["revision"],
                            "overrides": [],
                            "review_note": "AI tự động rà soát tác động dựa trên trace và bằng chứng của Requirement mới",
                        },
                    )
                if analysis.get("status") == "REVIEWED":
                    carried_forward_test_case_ids, carry_forward_unresolved = await carry_forward_unchanged_requirement_tests(
                        project_id,
                        version["requirement_id"],
                        version,
                        response_items(requirement_versions),
                        analysis,
                        config,
                    )
                    maintenance_artifact_ids.extend(carried_forward_test_case_ids)
                    unresolved.extend(carry_forward_unresolved)
                    existing_proposals = await require_operation(
                        "GET", f"/du-an/{project_id}/de-xuat-bao-tri?limit=500", config
                    )
                    proposals = [
                        item for item in response_items(existing_proposals)
                        if item.get("impact_analysis_id") == analysis["_id"]
                    ]
                    if not proposals:
                        proposals = await require_operation(
                            "POST", f"/phan-tich-anh-huong/{analysis['_id']}/de-xuat-bao-tri", config,
                            timeout=settings.MODEL_TIMEOUT_SECONDS,
                        )
                    for proposal in response_items(proposals):
                        if proposal.get("status") not in {"PENDING", "APPLY_PARTIAL"}:
                            if proposal.get("applied_artifact_id"):
                                maintenance_artifact_ids.append(proposal["applied_artifact_id"])
                            continue
                        applied = await require_operation(
                            "POST",
                            f"/du-an/{project_id}/de-xuat-ai/{proposal['_id']}/phe-duyet",
                            config,
                            {
                                "expected_revision": proposal["revision"],
                                "review_note": "AI tự động áp dụng đề xuất bảo trì đã qua kiểm tra bằng chứng và revision",
                            },
                        )
                        artifact = applied.get("result") or {}
                        if artifact.get("_id"):
                            maintenance_artifact_ids.append(artifact["_id"])
                        if proposal.get("proposal_type") == "CREATE_TEST_CASE" and artifact.get("status") == "DRAFT":
                            lint = await require_operation(
                                "POST", f"/ca-kiem-thu/{artifact['_id']}/kiem-tra", config
                            )
                            if not lint.get("valid"):
                                unresolved.append({"test_case_draft_id": artifact["_id"], "reason": "MAINTENANCE_TEST_CASE_QUALITY_FAILED"})
                                continue
                            reviewed = await require_operation(
                                "POST", f"/du-an/{project_id}/ca-kiem-thu/{artifact['_id']}/gui-ra-soat", config,
                                {"expected_revision": artifact["revision"], "review_note": "AI tự động rà nguồn và chất lượng ca bảo trì"},
                            )
                            approved = await require_operation(
                                "POST", f"/du-an/{project_id}/ca-kiem-thu/{artifact['_id']}/phe-duyet", config,
                                {"expected_revision": reviewed["revision"], "change_reason": "Ca bảo trì đạt cổng nguồn và chất lượng tự động", "review_note": "AI tự động đóng băng ca bảo trì đã xác minh"},
                            )
                            case = approved.get("test_case") or (approved.get("data") or {}).get("test_case")
                            if not case or case.get("project_id") != project_id:
                                raise RuntimeError("MAINTENANCE_TEST_CASE_APPROVAL_READBACK_INVALID")
                            maintenance_artifact_ids[-1] = case["_id"]
                elif analysis.get("status") != "REVIEWED":
                    unresolved.append({"impact_analysis_id": analysis.get("_id"), "reason": "IMPACT_ANALYSIS_NOT_REVIEWED"})
            elif change_set.get("status") not in {"REVIEWED", "ANALYZED"} and change_set.get("changes"):
                unresolved.append({"change_set_id": change_set.get("_id"), "reason": "REQUIREMENT_CHANGE_SET_NOT_REVIEWED"})
        except RuntimeError as error:
            unresolved.append({"requirement_version_id": requirement_version_id, "reason": str(error)})

    criteria_ids = version.get("acceptance_criterion_ids") or [
        item.get("_id") for item in version.get("acceptance_criteria", []) if item.get("_id")
    ]
    if not criteria_ids:
        return json.dumps({"status": "automation_partial_failure", "reason_code": "NO_ACCEPTANCE_CRITERIA", "requirement_version_id": requirement_version_id})
    existing_cases = await require_operation(
        "GET",
        f"/du-an/{project_id}/ca-kiem-thu?requirement_id={version['requirement_id']}&page_size=500",
        config,
    )
    covered_by_active_cases = {
        criterion_id
        for item in response_items(existing_cases)
        if item.get("status") == "ACTIVE"
        and item.get("stale_status") != "STALE"
        for criterion_id in (item.get("current_version") or {}).get("acceptance_criterion_ids", [])
    }
    existing_drafts = await require_operation(
        "GET", f"/du-an/{project_id}/ban-nhap-ca-kiem-thu?limit=500", config
    )
    pending_drafts = [
        item
        for item in response_items(existing_drafts)
        if item.get("status") == "DRAFT"
        and requirement_version_id in item.get("requirement_version_ids", [])
    ]
    covered_by_pending_drafts = {
        criterion_id
        for item in pending_drafts
        for criterion_id in item.get("acceptance_criterion_ids", [])
    }
    already_covered = covered_by_active_cases | covered_by_pending_drafts
    missing_before_generation = set(criteria_ids) - already_covered
    request = {
        "categories": [], "max_cases": len(missing_before_generation), "preview_only": True,
        "acceptance_criterion_ids": sorted(missing_before_generation),
        "instruction": "Tạo ca kiểm thử mới chỉ cho nghĩa vụ chưa được ca hiện có bao phủ. Loại ca trùng, giữ liên kết phiên bản Requirement mới và chỉ dùng bằng chứng đã trích dẫn.",
    }
    preview = {"items": [], "warnings": []}
    if missing_before_generation:
        preview = await require_operation(
            "POST", f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu", config, request,
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
    generated = preview.get("items") or []
    required_ids = missing_before_generation
    covered_ids = set()
    novel = []
    version_updates = []
    version_targets = set()
    skipped_duplicates = len(already_covered)
    warnings = list(preview.get("warnings") or [])
    for item in generated:
        draft = item.get("draft") or {}
        matches = item.get("similar_cases") or []
        target = next(
            (match for match in matches if match.get("target_version_id")),
            None,
        )
        new_criteria = set(item.get("new_criterion_ids") or [])
        if target and draft and new_criteria and target["target_version_id"] not in version_targets:
            version_targets.add(target["target_version_id"])
            version_updates.append({
                **draft,
                "target_version_id": target["target_version_id"],
                "version_reason": "Tự động cập nhật liên kết và nội dung ca theo Requirement version mới sau khi đối chiếu trùng và bằng chứng nguồn",
            })
            covered_ids.update(draft.get("acceptance_criterion_ids", []))
        elif matches:
            skipped_duplicates += 1
        elif draft:
            novel.append(draft)
            covered_ids.update(draft.get("acceptance_criterion_ids", []))
    missing_ids = required_ids - covered_ids
    if missing_ids:
        focused = await require_operation(
            "POST", f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu", config,
            {**request, "acceptance_criterion_ids": sorted(missing_ids), "max_cases": len(missing_ids)},
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
        warnings.extend(focused.get("warnings") or [])
        for item in focused.get("items") or []:
            draft = item.get("draft") or {}
            matches = item.get("similar_cases") or []
            target = next(
                (match for match in matches if match.get("target_version_id")),
                None,
            )
            new_criteria = set(item.get("new_criterion_ids") or [])
            if target and draft and new_criteria and target["target_version_id"] not in version_targets:
                version_targets.add(target["target_version_id"])
                version_updates.append({
                    **draft,
                    "target_version_id": target["target_version_id"],
                    "version_reason": "Tự động cập nhật liên kết và nội dung ca theo Requirement version mới sau khi đối chiếu trùng và bằng chứng nguồn",
                })
                covered_ids.update(draft.get("acceptance_criterion_ids", []))
            elif matches:
                skipped_duplicates += 1
            elif draft and normalized_text(draft.get("title")) not in {normalized_text(case.get("title")) for case in novel}:
                novel.append(draft)
                covered_ids.update(draft.get("acceptance_criterion_ids", []))
        missing_ids = required_ids - covered_ids
    if missing_ids:
        unresolved.append({"requirement_version_id": requirement_version_id, "reason": "ACCEPTANCE_CRITERIA_NOT_COVERED", "missing_acceptance_criterion_ids": sorted(missing_ids)})

    created_drafts = list(pending_drafts)
    approved_cases = []
    drafts_to_save = [*novel, *version_updates]
    if drafts_to_save:
        saved = await require_operation("POST", f"/du-an/{project_id}/ban-nhap-ca-kiem-thu/lo", config, drafts_to_save)
        created_drafts = saved if isinstance(saved, list) else saved.get("items", [])
        if len(created_drafts) != len(drafts_to_save):
            raise RuntimeError("TEST_CASE_BATCH_READBACK_INVALID")
    for draft in created_drafts:
        lint = await require_operation("POST", f"/ca-kiem-thu/{draft['_id']}/kiem-tra", config)
        if not lint.get("valid"):
            unresolved.append({"test_case_draft_id": draft["_id"], "reason": "TEST_CASE_QUALITY_FAILED"})
            continue
        reviewed = await require_operation(
            "POST", f"/du-an/{project_id}/ca-kiem-thu/{draft['_id']}/gui-ra-soat", config,
            {"expected_revision": draft["revision"], "review_note": "AI tự động rà nguồn, trùng lặp và chất lượng"},
        )
        approved = await require_operation(
            "POST", f"/du-an/{project_id}/ca-kiem-thu/{draft['_id']}/phe-duyet", config,
            {"expected_revision": reviewed["revision"], "change_reason": "Ca kiểm thử đạt cổng nguồn và chất lượng tự động", "review_note": "AI tự động đóng băng phiên bản đã xác minh"},
        )
        case = approved.get("test_case") or (approved.get("data") or {}).get("test_case")
        if not case or case.get("project_id") != project_id:
            raise RuntimeError("TEST_CASE_APPROVAL_READBACK_INVALID")
        case_readback = await require_operation("GET", f"/ca-kiem-thu/{case['_id']}", config)
        if case_readback.get("_id") != case["_id"]:
            raise RuntimeError("TEST_CASE_READBACK_INVALID")
        approved_cases.append(case)

    readback = await require_operation("GET", f"/phien-ban-yeu-cau/{requirement_version_id}", config)
    if readback.get("_id") != requirement_version_id or readback.get("status") != "BASELINED":
        raise RuntimeError("REQUIREMENT_BASELINE_READBACK_INVALID")
    artifacts = [{"artifact_id": requirement_version_id, "artifact_type": "requirement_version"}]
    artifacts.extend({"artifact_id": item["_id"], "artifact_type": "test_case"} for item in approved_cases)
    if unresolved:
        outcome = "automation_partial_failure"
    else:
        outcome = "COMPLETED"
    return json.dumps({
        "status": outcome,
        "requirement_version_id": requirement_version_id,
        "approved_test_case_ids": [item["_id"] for item in approved_cases],
        "maintenance_artifact_ids": list(dict.fromkeys(maintenance_artifact_ids)),
        "carried_forward_test_case_ids": list(dict.fromkeys(carried_forward_test_case_ids)),
        "skipped_duplicate_count": skipped_duplicates,
        "generation_warnings": list(dict.fromkeys(warnings)),
        "unresolved": unresolved,
        "verification": {"status": "COMPLETED" if not unresolved else "INCOMPLETE", "project_id": project_id, "artifact_ids": [item["artifact_id"] for item in artifacts], "checks": artifacts},
    }, ensure_ascii=False, default=str)

