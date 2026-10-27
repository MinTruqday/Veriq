import math
import re
import unicodedata
from urllib.parse import urlencode

from src.tools.automation_publication import publish_grounded_test_case
from src.tools.testing_api import AutomationOperationError, require_operation


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
    normalized = unicodedata.normalize("NFC", str(value or ""))
    return " ".join(normalized.casefold().split())


def source_contains_exact_phrase(source_text, quote):
    normalized_source = normalized_text(source_text)
    normalized_quote = normalized_text(quote)
    if not normalized_source or not normalized_quote:
        return False
    return re.search(
        rf"(?<!\w){re.escape(normalized_quote)}(?!\w)",
        normalized_source,
        flags=re.UNICODE,
    ) is not None

def response_items(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        items = value.get("items")
        return items if isinstance(items, list) else []
    return []


async def list_resumable_ai_test_case_drafts(project_id, requirement_version_id, config):
    drafts_by_id = {}
    for status in ("DRAFT", "IN_REVIEW"):
        query = urlencode(
            {"requirement_version_id": requirement_version_id, "status": status}
        )
        response = await require_operation(
            "GET",
            f"/du-an/{project_id}/ban-nhap-ca-kiem-thu?{query}",
            config,
        )
        if not isinstance(response, (list, dict)):
            raise AutomationOperationError("AI_TEST_CASE_DRAFT_READBACK_INVALID")
        items = response_items(response)
        if isinstance(response, dict) and not isinstance(response.get("items"), list):
            raise AutomationOperationError("AI_TEST_CASE_DRAFT_READBACK_INVALID")
        for draft in items:
            if not isinstance(draft, dict) or not draft.get("_id"):
                raise AutomationOperationError("AI_TEST_CASE_DRAFT_READBACK_INVALID")
            if (
                draft.get("project_id") != project_id
                or requirement_version_id
                not in (draft.get("requirement_version_ids") or [])
                or draft.get("status") != status
            ):
                raise AutomationOperationError("AI_TEST_CASE_DRAFT_SCOPE_INVALID")
            if draft.get("origin") != "ai_generated":
                continue
            previous = drafts_by_id.get(str(draft["_id"]))
            if previous and (
                previous.get("status") != draft.get("status")
                or previous.get("revision") != draft.get("revision")
            ):
                raise AutomationOperationError(
                    "AI_TEST_CASE_DRAFT_STATE_CHANGED_DURING_READ"
                )
            drafts_by_id[str(draft["_id"])] = draft
    return sorted(
        drafts_by_id.values(),
        key=lambda draft: (str(draft.get("created_at") or ""), str(draft["_id"])),
    )


async def list_all_test_case_records(project_id, requirement_id, config, page_size=500):
    if not isinstance(page_size, int) or isinstance(page_size, bool) or page_size < 1:
        raise AutomationOperationError("REQUIREMENT_TEST_CASE_PAGINATION_INVALID")
    page = 1
    total = None
    total_pages = None
    records = []
    seen_ids = set()
    scope_fingerprint = None
    while total_pages is None or page <= total_pages:
        response = await require_operation(
            "GET",
            f"/du-an/{project_id}/ca-kiem-thu?requirement_id={requirement_id}"
            f"&page={page}&page_size={page_size}&sort=test_case_key",
            config,
        )
        items = response_items(response)
        for item in items:
            identifier = str(item.get("_id") or "")
            if not identifier:
                raise AutomationOperationError("REQUIREMENT_TEST_CASE_PAGINATION_INVALID")
            if item.get("project_id") != project_id:
                raise AutomationOperationError("REQUIREMENT_TEST_CASE_SCOPE_INVALID")
            if identifier in seen_ids:
                raise AutomationOperationError("REQUIREMENT_TEST_CASE_PAGINATION_DUPLICATE")
            seen_ids.add(identifier)
            records.append(item)

        if not isinstance(response, dict):
            raise AutomationOperationError("REQUIREMENT_TEST_CASE_PAGINATION_INVALID")

        try:
            reported_total = int(response["total"])
            reported_pages = int(response["total_pages"])
            reported_page = int(response["page"])
            reported_page_size = int(response["page_size"])
        except (KeyError, TypeError, ValueError) as error:
            raise AutomationOperationError(
                "REQUIREMENT_TEST_CASE_PAGINATION_INVALID"
            ) from error
        if (
            reported_total < 0
            or reported_pages != math.ceil(reported_total / page_size)
            or reported_page != page
            or reported_page_size != page_size
        ):
            raise AutomationOperationError("REQUIREMENT_TEST_CASE_PAGINATION_INVALID")
        if total is not None and reported_total != total:
            raise AutomationOperationError(
                "REQUIREMENT_TEST_CASE_SCOPE_CHANGED_DURING_READ"
            )
        if total_pages is not None and reported_pages != total_pages:
            raise AutomationOperationError(
                "REQUIREMENT_TEST_CASE_SCOPE_CHANGED_DURING_READ"
            )
        total = reported_total
        total_pages = reported_pages
        reported_fingerprint = response.get("scope_fingerprint")
        if not isinstance(reported_fingerprint, str) or not reported_fingerprint:
            raise AutomationOperationError("REQUIREMENT_TEST_CASE_SCOPE_FINGERPRINT_MISSING")
        if scope_fingerprint is not None and reported_fingerprint != scope_fingerprint:
            raise AutomationOperationError("REQUIREMENT_TEST_CASE_SCOPE_CHANGED_DURING_READ")
        scope_fingerprint = reported_fingerprint
        expected_items = min(page_size, max(0, reported_total - (page - 1) * page_size))
        if len(items) != expected_items:
            raise AutomationOperationError("REQUIREMENT_TEST_CASE_PAGINATION_INCOMPLETE")
        if reported_pages == 0:
            break
        page += 1

    if total is not None and len(records) != total:
        raise AutomationOperationError("REQUIREMENT_TEST_CASE_PAGINATION_INCOMPLETE")
    return records

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
    cases = await list_all_test_case_records(project_id, requirement_id, config)
    carried = []
    unresolved = []
    for case in cases:
        current = case.get("current_version") or {}
        current_version_id = case.get("current_version_id") or current.get("_id")
        old_requirement_ids = set(current.get("requirement_version_ids", [])) & set(prior_versions)
        if (
            case.get("status") != "ACTIVE"
            or current_version_id not in unchanged_versions
            or not old_requirement_ids
        ):
            continue
        if case.get("stale_status") == "STALE" or current.get("status") != "ACTIVE":
            unresolved.append(
                {
                    "test_case_id": case.get("_id"),
                    "reason": "UNCHANGED_TEST_CASE_SOURCE_VERSION_NOT_CURRENT",
                }
            )
            continue
        old_criterion_links = set(current.get("acceptance_criterion_ids", [])) & prior_criterion_ids
        unmapped_criterion_ids = [
            criterion_id
            for criterion_id in old_criterion_links
            if prior_criteria_by_id[criterion_id].get("key") not in target_by_key
        ]
        if unmapped_criterion_ids:
            unresolved.append(
                {
                    "test_case_id": case.get("_id"),
                    "reason": "UNCHANGED_TEST_CASE_CRITERION_MAPPING_INCOMPLETE",
                    "acceptance_criterion_ids": sorted(unmapped_criterion_ids),
                }
            )
            continue
        mapped_criterion_ids = {
            target_by_key[prior_criteria_by_id[item].get("key")]["_id"]
            for item in old_criterion_links
            if prior_criteria_by_id[item].get("key") in target_by_key
        }
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
            published_case, published_version, _ = await publish_grounded_test_case(
                project_id, draft, config
            )
            carried.append(
                {
                    "test_case_id": published_case["_id"],
                    "test_case_version_id": published_version["_id"],
                }
            )
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
    items = response_items(clarifications)
    permissions = set((config or {}).get("configurable", {}).get("permissions", []))
    if "requirement.approve" not in permissions:
        return [item for item in items if item.get("status") in {"OPEN", "ANSWERED"}]

    source_parts = [str(version.get("plain_text_projection") or "")]

    def collect_text(value):
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [part for item in value for part in collect_text(item)]
        if isinstance(value, dict):
            if isinstance(value.get("text"), str):
                return [value["text"]]
            return [part for item in value.values() for part in collect_text(item)]
        return []

    source_parts.extend(collect_text(version.get("content_doc") or {}))
    source_parts.extend(collect_text(version.get("business_rules") or []))
    source_parts.extend(
        collect_text(version.get("acceptance_criteria") or [])
    )
    pending = []
    for item in items:
        if item.get("status") == "OPEN":
            pending.append(item)
            continue
        if item.get("status") != "ANSWERED":
            continue
        answer = str(item.get("answer") or "").strip()
        if not any(source_contains_exact_phrase(part, answer) for part in source_parts):
            pending.append(item)
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
        except AutomationOperationError:
            latest = response_items(
                await require_operation(
                    "GET", f"/phien-ban-yeu-cau/{version['_id']}/phieu-lam-ro", config
                )
            )
            already_resolved = any(
                current.get("_id") == item.get("_id")
                and current.get("status") == "RESOLVED"
                and current.get("resolved_requirement_version_id") == version["_id"]
                and current.get("resolution_evidence_quote") == answer
                for current in latest
            )
            if not already_resolved:
                raise
    return pending

async def plan_clarification_priority(version, clarifications, config):
    """Rank open questions by persisted, exact links to unresolved test obligations."""
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
        explicit_item_ids = set(clarification.get("unlocks_coverage_item_ids") or [])
        obligation_quotes = {
            " ".join(str(value or "").split())
            for value in clarification.get("unlocks_source_quotes", [])
            if str(value or "").strip()
        }
        if explicit_item_ids:
            linked = [
                item for item in unresolved_items
                if item.get("coverage_item_id") in explicit_item_ids
            ]
        elif obligation_quotes:
            linked = [
                item for item in unresolved_items
                if " ".join(str(item.get("source_quote") or "").split()) in obligation_quotes
            ]
        else:
            source_ref = str(clarification.get("source_ref") or "").strip()
            source_quote = " ".join(str(clarification.get("source_quote") or "").split())
            linked = [
                item for item in unresolved_items
                if (
                    clarification.get("coverage_item_id") == item.get("coverage_item_id")
                    or (source_ref and source_ref == str(item.get("source_ref") or "").strip())
                    or (
                        source_quote
                        and source_quote == " ".join(str(item.get("source_quote") or "").split())
                    )
                )
            ]
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

