import json
from typing import Annotated
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.schemas.automation import AutomationFact
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
    source_facts: Annotated[list[AutomationFact], Field(description="Source facts extracted and quote-verified by the automation graph")] = Field(default_factory=list),
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

    evidence_by_ref = {
        str(item.get("artifact_version_id") or item.get("artifact_id")): item
        for item in configurable.get("evidence", [])
        if isinstance(item, dict) and item.get("artifact_id")
    }
    verified_facts = []
    for fact in source_facts:
        source = evidence_by_ref.get(fact.artifact_version_id or fact.artifact_id)
        if (
            source
            and str(source.get("artifact_id")) == fact.artifact_id
            and fact.quote in str(source.get("text") or "")
            and fact.artifact_id in source_document_ids
        ):
            verified_facts.append(fact)

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
                "instruction": "Tổng hợp thành blueprint kiểm thử phù hợp riêng với dự án từ toàn bộ nguồn được chọn. Giữ nguyên nguồn và trích dẫn cho từng đề xuất. Phân biệt dữ kiện, thông tin còn thiếu, mơ hồ và mâu thuẫn giữa các nguồn. Không tự chọn cách giải quyết mâu thuẫn; thể hiện rõ các quyết định cần BA hoặc QA làm rõ. Không suy đoán actor, quy tắc, tiêu chí chấp nhận, dữ liệu, mã phản hồi hoặc giới hạn không có trong nguồn. Dùng các facts đã trích xuất và kiểm chứng dưới đây làm đầu vào cấu trúc; mỗi fact chỉ được áp dụng nếu trích dẫn và nguồn vẫn khớp tài liệu hiện hành. Không bỏ qua hoặc mở rộng ý nghĩa trích dẫn.\n\nFACTS ĐÃ KIỂM CHỨNG:\n" + "\n".join(
                    f"[{fact.artifact_type}:{fact.artifact_id}:{fact.artifact_version_id or ''} | {fact.fact_kind}] {fact.quote}"
                    for fact in verified_facts
                ),
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

