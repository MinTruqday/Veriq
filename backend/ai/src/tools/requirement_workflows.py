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
    "requirement.create",
)
async def process_ingested_requirement_document(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    document_id: Annotated[str, Field(min_length=1, description="Verified uploaded requirement document identifier")],
    config: RunnableConfig = None,
) -> str:
    """Run the authorized document-ingestion workflow through a grounded template, Requirements, duplicate-safe Test Cases, and lifecycle checks"""
    configurable = (config or {}).get("configurable", {})
    permissions = set(configurable.get("permissions", []))
    required_permissions = {
        "project.read",
        "requirement.create",
        "requirement_document.review_extraction",
        "requirement_document.confirm_extraction",
        "requirement.version.create",
        "requirement.read",
        "requirement.review",
        "requirement.submit_review",
        "requirement.approve",
        "ai.generate_testcase",
        "testcase.create",
        "testcase.read",
        "testcase.lint",
        "testcase.submit_review",
        "testcase.approve",
        "ai.run_lint",
    }
    missing_permissions = sorted(required_permissions - permissions)
    if missing_permissions:
        return json.dumps(
            {"status": "automation_blocked", "reason_code": "REQUIRED_PERMISSION_MISSING", "missing_permissions": missing_permissions},
            ensure_ascii=False,
        )

    project_path = f"/du-an/{project_id}"
    project = await require_operation("GET", project_path, config)
    if project.get("_id") != project_id or not project.get("project_type"):
        return json.dumps(
            {"status": "automation_blocked", "reason_code": "PROJECT_TYPE_REQUIRED"},
            ensure_ascii=False,
        )
    # Compile the new source together with every other source that this
    # executor can currently read and that has explicitly enabled AI access.
    # The project API applies the document ACL before returning this list; do
    # not widen access by querying storage directly from the AI service.
    visible_documents = await require_operation(
        "GET", f"{project_path}/tai-lieu-yeu-cau?status=READY&limit=1000", config
    )
    visible_document_items = response_items(visible_documents)
    source_documents = {
        str(item["_id"]): item
        for item in visible_document_items
        if item.get("_id")
    }
    source_document_ids = compilable_document_ids(
        visible_document_items, document_id
    )
    if not source_document_ids:
        raise AutomationOperationError("AI_ENABLED_SOURCE_NOT_ACCESSIBLE")

    templates = await require_operation("GET", f"{project_path}/mau-yeu-cau", config)
    template = next(
        (
            item for item in response_items(templates)
            if item.get("project_id") == project_id
            and sorted(set(item.get("source_document_ids", []))) == source_document_ids
            and item.get("status") == "DRAFT"
        ),
        None,
    )
    if not template:
        template = await require_operation(
            "POST",
            f"{project_path}/mau-yeu-cau/tong-hop",
            config,
            {
                "name": "Blueprint kiểm thử dự án",
                "product_types": [project["project_type"]],
                "source_document_ids": source_document_ids,
                "source_template_ids": [],
                "instruction": "Tổng hợp thành blueprint kiểm thử phù hợp riêng với dự án từ toàn bộ nguồn được chọn. Giữ nguyên nguồn và trích dẫn cho từng đề xuất. Phân biệt dữ kiện, thông tin còn thiếu, mơ hồ và mâu thuẫn giữa các nguồn. Không tự chọn cách giải quyết mâu thuẫn; thể hiện rõ các quyết định cần BA hoặc QA làm rõ. Không suy đoán actor, quy tắc, tiêu chí chấp nhận, dữ liệu, mã phản hồi hoặc giới hạn không có trong nguồn.",
            },
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
    if not template.get("_id") or template.get("project_id") != project_id:
        raise RuntimeError("TEMPLATE_READBACK_INVALID")
    if (template.get("synthesis") or {}).get("conflicts"):
        return json.dumps(
            {"status": "automation_blocked", "reason_code": "SOURCE_CONFLICT", "template_id": template["_id"], "conflict_count": len(template["synthesis"]["conflicts"])},
            ensure_ascii=False,
        )
    template_requirements = template.get("requirements") or []
    if not template_requirements:
        return json.dumps(
            {"status": "automation_blocked", "reason_code": "NO_GROUNDED_REQUIREMENTS", "template_id": template["_id"]},
            ensure_ascii=False,
        )

    import_job = await require_operation(
        "POST", f"{project_path}/mau-yeu-cau/{template['_id']}/xem-truoc", config
    )
    if import_job.get("project_id") != project_id or not import_job.get("_id"):
        raise RuntimeError("REQUIREMENT_IMPORT_PREVIEW_INVALID")

    linked_requirement_ids = {
        item.get("requirement_id")
        for item in import_job.get("resolutions", [])
        if item.get("requirement_id")
    }
    unresolved = []
    updated_requirement_versions = set()
    if import_job.get("status") == "PREVIEW_READY":
        comparison = await require_operation(
            "GET", f"/nhap-yeu-cau/{import_job['_id']}/doi-chieu", config
        )
        for candidate_match in comparison.get("comparisons", []):
            exact_matches = [
                match for match in candidate_match.get("matches", [])
                if match.get("requirement_id") and match.get("match_type") == "EXACT"
            ]
            if len(exact_matches) == 1:
                candidate_id = candidate_match.get("candidate_id")
                current_job = await require_operation("GET", f"/nhap-yeu-cau/{import_job['_id']}", config)
                try:
                    await require_operation(
                        "POST",
                        f"/nhap-yeu-cau/{import_job['_id']}/ung-vien/{candidate_id}/doi-chieu",
                        config,
                        {
                            "expected_revision": current_job["revision"],
                            "target_requirement_id": exact_matches[0]["requirement_id"],
                            "expected_target_version_id": exact_matches[0]["version_id"],
                            "action": "link_source",
                            "reason": f"Tài liệu {document_id} xác nhận cùng nội dung Requirement; chỉ bổ sung dấu vết nguồn",
                        },
                    )
                except RuntimeError as error:
                    if str(error) != "SOURCE_ALREADY_LINKED":
                        raise
                linked_requirement_ids.add(exact_matches[0]["requirement_id"])
                continue

            stable_identity_matches = [
                match
                for match in candidate_match.get("matches", [])
                if match.get("requirement_id")
                and match.get("match_type") == "SAME_KEY"
            ]
            semantic_matches = [
                match
                for match in candidate_match.get("matches", [])
                if match.get("requirement_id")
                and match.get("match_type") == "POSSIBLE"
            ]
            unique_semantic_match = (
                semantic_matches[0]
                if len(candidate_match.get("matches", [])) == 1
                and len(semantic_matches) == 1
                else None
            )
            if len(stable_identity_matches) == 1 or unique_semantic_match:
                match = stable_identity_matches[0] if stable_identity_matches else unique_semantic_match
                candidate_id = candidate_match.get("candidate_id")
                current_job = await require_operation(
                    "GET", f"/nhap-yeu-cau/{import_job['_id']}", config
                )
                resolution = await require_operation(
                    "POST",
                    f"/nhap-yeu-cau/{import_job['_id']}/ung-vien/{candidate_id}/doi-chieu",
                    config,
                    {
                        "expected_revision": current_job["revision"],
                        "target_requirement_id": match["requirement_id"],
                        "expected_target_version_id": match["version_id"],
                        "action": "create_version",
                        "reason": (
                            f"Tài liệu {document_id} được đối chiếu với một Requirement hiện có "
                            "theo mã ổn định hoặc một kết quả trùng ngữ nghĩa duy nhất; tạo phiên bản "
                            "mới từ nội dung có nguồn và giữ nguyên lịch sử phiên bản"
                        ),
                    },
                )
                updated_requirement_versions.update(
                    item.get("to_version_id")
                    for item in resolution.get("resolutions", [])
                    if item.get("candidate_id") == candidate_id
                    and item.get("to_version_id")
                )
                linked_requirement_ids.add(match["requirement_id"])

        import_job = await require_operation("GET", f"/nhap-yeu-cau/{import_job['_id']}", config)
        if import_job.get("status") == "PREVIEW_READY" and import_job.get("preview"):
            comparison = await require_operation(
                "GET", f"/nhap-yeu-cau/{import_job['_id']}/doi-chieu", config
            )
            unresolved_matches = [
                item for item in comparison.get("comparisons", [])
                if item.get("matches")
            ]
            if unresolved_matches:
                unresolved.extend(
                    {
                        "candidate_id": item.get("candidate_id"),
                        "reason": "REQUIREMENT_MATCH_NEEDS_RECONCILIATION",
                        "candidate_matches": item.get("matches", []),
                    }
                    for item in unresolved_matches
                )
            else:
                created_result = await require_operation(
                    "POST",
                    f"/nhap-yeu-cau/{import_job['_id']}/xac-nhan",
                    config,
                    {
                        "selected_indexes": list(range(len(import_job["preview"]))),
                        "expected_revision": import_job["revision"],
                    },
                )
                linked_requirement_ids.update(
                    item.get("_id") for item in created_result.get("requirements", []) if item.get("_id")
                )
                import_job = await require_operation(
                    "GET", f"/nhap-yeu-cau/{import_job['_id']}", config
                )
                if import_job.get("status") != "CONFIRMED":
                    raise RuntimeError("REQUIREMENT_IMPORT_CONFIRMATION_READBACK_INVALID")

    if import_job.get("status") == "CONFIRMED":
        linked_requirement_ids.update(import_job.get("created_requirement_ids", []))

    requirements = []
    clarification_blocked_version_ids = set()
    clarification_ids = set()
    clarification_plans = []
    for requirement_id in sorted(linked_requirement_ids):
        requirement = await require_operation("GET", f"/yeu-cau/{requirement_id}", config)
        if requirement.get("project_id") != project_id or not requirement.get("current_version_id"):
            raise RuntimeError("REQUIREMENT_READBACK_INVALID")
        current = requirement.get("current_version") or await require_operation(
            "GET", f"/phien-ban-yeu-cau/{requirement['current_version_id']}", config
        )
        if current.get("status") == "DRAFT":
            await require_operation(
                "POST",
                f"/phien-ban-yeu-cau/{current['_id']}/phieu-lam-ro/tao-tu-ra-soat",
                config,
            )
        open_clarifications = await resolve_answered_clarifications(current, config)
        if open_clarifications:
            clarification_plans.extend(
                await plan_clarification_priority(current, open_clarifications, config)
            )
            clarification_blocked_version_ids.add(current["_id"])
            clarification_ids.update(
                item["_id"] for item in open_clarifications if item.get("_id")
            )
            unresolved.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_version_id": current["_id"],
                    "reason": "REQUIREMENT_CLARIFICATION_REQUIRED",
                    "clarification_ids": [
                        item["_id"] for item in open_clarifications if item.get("_id")
                    ],
                }
            )
            requirements.append({"requirement": requirement, "version": current})
            continue
        if current.get("status") == "DRAFT":
            try:
                current = await require_operation(
                    "POST", f"{project_path}/yeu-cau/{requirement['_id']}/gui-ra-soat", config,
                    {"expected_revision": current["revision"], "review_note": "AI tự động kiểm tra nguồn và chất lượng trước khi chốt chuẩn"},
                )
            except RuntimeError as error:
                unresolved.append({"requirement_id": requirement["_id"], "requirement_version_id": current["_id"], "reason": str(error)})
        if current.get("status") == "IN_REVIEW":
            try:
                current = await require_operation(
                    "POST", f"/phien-ban-yeu-cau/{current['_id']}/chot-chuan", config,
                    {"expected_revision": current["revision"], "review_note": "AI tự động chốt Requirement sau khi kiểm tra chất lượng"},
                )
            except RuntimeError as error:
                unresolved.append({"requirement_id": requirement["_id"], "requirement_version_id": current["_id"], "reason": str(error)})
        requirements.append({"requirement": requirement, "version": current})

    changed_versions = [
        item["version"]
        for item in requirements
        if item["version"].get("_id") in updated_requirement_versions
        and item["version"].get("status") == "BASELINED"
    ]
    maintenance_results = []
    for version in changed_versions:
        change_result = await process_changed_requirement_version.ainvoke(
            {
                "project_id": project_id,
                "requirement_version_id": version["_id"],
            },
            config=config,
        )
        parsed_change_result = parse(change_result)
        if not parsed_change_result or parsed_change_result.get("status") != "COMPLETED":
            unresolved.append(
                {
                    "requirement_version_id": version["_id"],
                    "reason": (parsed_change_result or {}).get("reason_code")
                    or "RELATED_TEST_MAINTENANCE_INCOMPLETE",
                    "details": parsed_change_result,
                }
            )
        else:
            maintenance_results.append(parsed_change_result)

    created_drafts = []
    approved_cases = []
    skipped_duplicates = 0
    generation_warnings = []
    unapplied_categories = []
    baselined_version_ids = {
        item["version"]["_id"]
        for item in requirements
        if item["version"].get("status") == "BASELINED"
    }
    for item in requirements:
        version = item["version"]
        if version.get("_id") in clarification_blocked_version_ids:
            continue
        if version.get("status") not in {"BASELINED", "DRAFT"}:
            unresolved.append({"requirement_version_id": version.get("_id"), "reason": "REQUIREMENT_NOT_READY"})
            continue
        criterion_ids = version.get("acceptance_criterion_ids") or [
            criterion.get("_id") for criterion in version.get("acceptance_criteria", [])
            if criterion.get("_id")
        ]
        if not criterion_ids:
            unresolved.append({"requirement_version_id": version.get("_id"), "reason": "NO_ACCEPTANCE_CRITERIA"})
            continue
        generation_request = {
            "categories": [],
            "max_cases": len(criterion_ids),
            "preview_only": True,
            "instruction": "Tạo ca kiểm thử cụ thể từ tiêu chí và nguồn của Requirement. Không tạo hành vi hoặc giới hạn không có căn cứ.",
        }
        preview = await require_operation(
            "POST",
            f"/phien-ban-yeu-cau/{version['_id']}/ai/sinh-ca-kiem-thu",
            config,
            generation_request,
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
        items = preview.get("items") or []
        generation_warnings.extend(preview.get("warnings") or [])
        unapplied_categories.extend(preview.get("unapplied_categories") or [])
        novel = []
        for generated in items:
            draft = generated.get("draft") or {}
            similar = generated.get("similar_cases") or []
            newly_covered = set(generated.get("new_criterion_ids") or [])
            draft_criteria = set(draft.get("acceptance_criterion_ids") or [])
            if similar or not newly_covered or not (newly_covered & draft_criteria):
                skipped_duplicates += 1
            elif draft:
                novel.append(draft)
        coverage = preview.get("criterion_coverage") or {}
        required_criteria = set(coverage.get("criterion_ids") or [])
        already_covered = set(coverage.get("linked_criterion_ids") or [])
        newly_covered = {
            criterion_id
            for candidate in novel
            for criterion_id in candidate.get("acceptance_criterion_ids", [])
        }
        missing_criteria = required_criteria - already_covered - newly_covered
        if missing_criteria:
            focused_request = {
                **generation_request,
                "acceptance_criterion_ids": sorted(missing_criteria),
                "max_cases": len(missing_criteria),
                "instruction": (
                    "Tập trung tạo ca kiểm thử cho đúng các acceptance criterion được chọn trong yêu cầu này. "
                    "Không lặp lại nội dung đã được ca kiểm thử hiện có bao phủ. Chỉ dùng hành vi có dẫn chứng; "
                    "nếu thiếu bằng chứng thì để trống thay vì tự suy diễn."
                ),
            }
            focused_preview = await require_operation(
                "POST",
                f"/phien-ban-yeu-cau/{version['_id']}/ai/sinh-ca-kiem-thu",
                config,
                focused_request,
                timeout=settings.MODEL_TIMEOUT_SECONDS,
            )
            generation_warnings.extend(focused_preview.get("warnings") or [])
            unapplied_categories.extend(focused_preview.get("unapplied_categories") or [])
            for generated in focused_preview.get("items") or []:
                draft = generated.get("draft") or {}
                similar = generated.get("similar_cases") or []
                newly_covered = set(generated.get("new_criterion_ids") or [])
                draft_criteria = set(draft.get("acceptance_criterion_ids") or [])
                if similar or not newly_covered or not (newly_covered & draft_criteria):
                    skipped_duplicates += 1
                    continue
                signature = normalized_text(draft.get("title"))
                if not draft or not signature or signature in {normalized_text(item.get("title")) for item in novel}:
                    continue
                novel.append(draft)
                newly_covered.update(draft.get("acceptance_criterion_ids", []))
            missing_criteria = required_criteria - already_covered - newly_covered
        if missing_criteria:
            unresolved.append(
                {
                    "requirement_version_id": version["_id"],
                    "reason": "ACCEPTANCE_CRITERIA_NOT_COVERED",
                    "missing_acceptance_criterion_ids": sorted(missing_criteria),
                }
            )
        if not novel:
            continue
        created = await require_operation(
            "POST", f"{project_path}/ban-nhap-ca-kiem-thu/lo", config, novel
        )
        created_items = created if isinstance(created, list) else created.get("items", [])
        if len(created_items) != len(novel):
            raise RuntimeError("TEST_CASE_BATCH_READBACK_INVALID")
        created_drafts.extend(created_items)

    for draft in created_drafts:
        if draft.get("project_id") != project_id or not draft.get("_id"):
            raise RuntimeError("TEST_CASE_READBACK_INVALID")
        lint = await require_operation(
            "POST", f"/ca-kiem-thu/{draft['_id']}/kiem-tra", config
        )
        if not lint.get("valid"):
            unresolved.append({"test_case_draft_id": draft["_id"], "reason": "TEST_CASE_QUALITY_FAILED"})
            continue
        if not set(draft.get("requirement_version_ids", [])) <= baselined_version_ids:
            unresolved.append({"test_case_draft_id": draft["_id"], "reason": "REQUIREMENT_NOT_BASELINED"})
            continue
        reviewed = await require_operation(
            "POST",
            f"{project_path}/ca-kiem-thu/{draft['_id']}/gui-ra-soat",
            config,
            {"expected_revision": draft["revision"], "review_note": "AI tự động rà soát ca kiểm thử dựa trên nguồn và kết quả kiểm tra chất lượng"},
        )
        approved = await require_operation(
            "POST",
            f"{project_path}/ca-kiem-thu/{draft['_id']}/phe-duyet",
            config,
            {"expected_revision": reviewed["revision"], "change_reason": "AI tự động hoàn tất ca kiểm thử có đủ bằng chứng và đạt kiểm tra chất lượng", "review_note": "Đã kiểm tra nguồn, trùng lặp và chất lượng"},
        )
        case = approved.get("test_case") or (approved.get("data") or {}).get("test_case")
        if not case or case.get("project_id") != project_id:
            raise RuntimeError("TEST_CASE_APPROVAL_READBACK_INVALID")
        await require_operation("GET", f"/ca-kiem-thu/{case['_id']}", config)
        approved_cases.append(case)

    checks = []
    template_readback = await require_operation(
        "GET", f"{project_path}/mau-yeu-cau/{template['_id']}", config
    )
    if (
        template_readback.get("_id") != template["_id"]
        or template_readback.get("project_id") != project_id
    ):
        raise RuntimeError("TEMPLATE_READBACK_INVALID")
    checks.append({"artifact_id": template["_id"], "artifact_type": "requirement_template"})
    for item in requirements:
        requirement = await require_operation(
            "GET", f"/yeu-cau/{item['requirement']['_id']}", config
        )
        if requirement.get("_id") != item["requirement"]["_id"] or requirement.get("project_id") != project_id:
            raise RuntimeError("REQUIREMENT_READBACK_INVALID")
        checks.append({"artifact_id": requirement["_id"], "artifact_type": "requirement"})
    for case in approved_cases:
        case_readback = await require_operation("GET", f"/ca-kiem-thu/{case['_id']}", config)
        if case_readback.get("_id") != case["_id"] or case_readback.get("project_id") != project_id:
            raise RuntimeError("TEST_CASE_READBACK_INVALID")
        checks.append({"artifact_id": case["_id"], "artifact_type": "test_case"})

    result = {
        "status": "automation_partial_failure" if unresolved else "COMPLETED",
        "template_id": template["_id"],
        "requirement_import_job_id": import_job["_id"],
        "requirement_ids": [item["requirement"]["_id"] for item in requirements],
        "requirement_version_ids": [item["version"]["_id"] for item in requirements],
        "test_case_draft_ids": [item["_id"] for item in created_drafts],
        "approved_test_case_ids": [item["_id"] for item in approved_cases],
        "updated_requirement_version_ids": sorted(updated_requirement_versions),
        "clarification_ids": sorted(clarification_ids),
        "clarification_plan": clarification_plans,
        "maintenance_results": maintenance_results,
        "skipped_duplicate_count": skipped_duplicates,
        "generation_warnings": list(dict.fromkeys(generation_warnings)),
        "unapplied_categories": sorted(set(unapplied_categories)),
        "unresolved": unresolved,
        "source_facts": list(
            {
                (
                    str(reference.get("requirement_document_id")),
                    str(reference.get("source_version") or ""),
                    str(reference.get("source_quote") or ""),
                ): {
                    "artifact_type": "requirement_document",
                    "artifact_id": str(reference.get("requirement_document_id")),
                    "artifact_version_id": str(
                        reference.get("source_version")
                        or source_documents.get(str(reference.get("requirement_document_id")), {}).get("source_version")
                        or ""
                    ) or None,
                    "source_start": reference.get("source_start"),
                    "source_end": reference.get("source_end"),
                    "source": "document",
                    "authority": str(
                        source_documents.get(str(reference.get("requirement_document_id")), {}).get("authority")
                        or "PROJECT_REFERENCE"
                    ),
                    "quote": str(reference.get("source_quote") or ""),
                }
                for requirement in template_requirements
                for reference in requirement.get("source_refs", [])
                if reference.get("requirement_document_id")
                and str(reference.get("source_quote") or "").strip()
            }.values()
        ),
        "verification": {
            "status": "COMPLETED" if not unresolved else "INCOMPLETE",
            "project_id": project_id,
            "artifact_ids": [item["artifact_id"] for item in checks],
            "checks": checks,
        },
    }
    return json.dumps(result, ensure_ascii=False, default=str)


@with_tool_access(("requirement",), "MUTATE", "requirement.approve")
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
