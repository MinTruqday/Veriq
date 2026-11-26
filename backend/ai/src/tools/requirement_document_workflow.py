import asyncio
import hashlib
import json
import math
import re
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.prompts.requirement_templates import requirement_document_synthesis_instruction
from src.prompts.test_generation import (
    focused_requirement_test_generation_instruction,
    requirement_test_generation_instruction,
    retry_grounded_requirement_test_generation_instruction,
)
from src.repositories.ai_runs import ai_run_repository
from src.schemas.ai_runs import AIRunStatus
from src.services.source_provenance import source_quote_spans
from src.tools.registry import with_tool_access
from src.tools.requirement_change_workflow import process_changed_requirement_version
from src.tools.test_case_deduplication import consolidate_duplicate_test_case_drafts
from src.tools.testing import (
    compilable_document_ids,
    list_resumable_ai_test_case_drafts,
    normalized_text,
    response_items,
)
from src.tools.testing_api import ToolOperationError, parse, require_operation

REQUIREMENT_IMPORT_APPLY_TIMEOUT_SECONDS = 180


async def apply_requirement_import_safely(import_job, config, before_write=None):
    job_id = str(import_job.get("_id") or "")
    if not job_id:
        raise RuntimeError("REQUIREMENT_IMPORT_JOB_ID_MISSING")
    if before_write is not None:
        await before_write()
    try:
        result = await require_operation(
            "POST",
            f"/nhap-yeu-cau/{job_id}/tu-dong-ap-dung",
            config,
            {
                "selected_indexes": list(range(len(import_job.get("preview") or []))),
                "expected_revision": import_job["revision"],
            },
            timeout=REQUIREMENT_IMPORT_APPLY_TIMEOUT_SECONDS,
        )
        latest = await require_operation("GET", f"/nhap-yeu-cau/{job_id}", config)
    except (ToolOperationError, httpx.TimeoutException, httpx.NetworkError) as error:
        latest = None
        for _ in range(30):
            try:
                latest = await require_operation("GET", f"/nhap-yeu-cau/{job_id}", config)
            except (ToolOperationError, httpx.TimeoutException, httpx.NetworkError):
                await asyncio.sleep(2)
                continue
            if latest.get("status") == "CONFIRMED":
                return {"requirements": []}, latest
            if latest.get("status") != "CONFIRMING":
                raise error
            await asyncio.sleep(2)
        raise ToolOperationError(
            "REQUIREMENT_IMPORT_CONFIRMATION_OUTCOME_UNRESOLVED"
        ) from error

    if latest.get("status") != "CONFIRMED":
        raise RuntimeError("REQUIREMENT_IMPORT_CONFIRMATION_READBACK_INVALID")
    return result, latest


async def generate_grounded_test_case_preview(
    requirement_version_id,
    config,
    payload,
    before_request=None,
):
    path = f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu"
    try:
        if before_request is not None:
            await before_request()
        return await require_operation("POST", path, config, payload, timeout=settings.MODEL_TIMEOUT_SECONDS)
    except ToolOperationError as error:
        if error.reason_code != "AI_UNGROUNDED_OUTPUT":
            raise
    retry_payload = {
        **payload,
        "instruction": retry_grounded_requirement_test_generation_instruction(),
    }
    if before_request is not None:
        await before_request()
    return await require_operation(
        "POST", path, config, retry_payload, timeout=settings.MODEL_TIMEOUT_SECONDS
    )


def resumable_draft_matches_requirement_scope(draft, requirement_version_id, criterion_ids):
    if (
        draft.get("origin") != "ai_generated"
        or not draft.get("_id")
        or requirement_version_id not in set(draft.get("requirement_version_ids") or [])
    ):
        return False
    draft_criterion_ids = [
        str(item) for item in (draft.get("acceptance_criterion_ids") or [])
    ]
    if (
        len(draft_criterion_ids) != len(set(draft_criterion_ids))
        or not set(draft_criterion_ids) <= set(map(str, criterion_ids))
    ):
        return False
    return bool(draft.get("evidence_refs")) and bool(draft.get("evidence_quotes"))

def verified_requirement_source_citations(
    template_requirements, source_documents, allowed_document_ids
):
    allowed_document_ids = {str(value) for value in allowed_document_ids}
    facts = {}
    evidence = {}
    for requirement in template_requirements:
        for reference in requirement.get("source_refs", []):
            document_id = str(reference.get("requirement_document_id") or "")
            document = source_documents.get(document_id) or {}
            if (
                not document_id
                or document_id not in allowed_document_ids
                or document.get("ai_enabled") is not True
                or document.get("status") != "READY"
            ):
                continue
            normalized_content = document.get("normalized_content")
            if isinstance(normalized_content, str):
                source_text = normalized_content
            elif isinstance(normalized_content, (dict, list)):
                source_text = json.dumps(
                    normalized_content,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            else:
                continue

            source_version = str(document.get("source_version") or "")
            expected_version = str(reference.get("source_version") or "")
            current_hash = str(document.get("content_hash") or "")
            expected_hash = str(reference.get("content_hash") or "")
            if (
                expected_version
                and (not source_version or source_version != expected_version)
            ) or (expected_hash and (not current_hash or current_hash != expected_hash)):
                continue

            start = reference.get("source_start")
            end = reference.get("source_end")
            stored_quote = str(reference.get("source_quote") or "").strip()
            valid_offsets = (
                isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
                and 0 <= start < end <= len(source_text)
            )
            span_quote = source_text[start:end] if valid_offsets else ""
            quote = stored_quote or span_quote
            quote_spans = source_quote_spans(source_text, quote)
            if not quote or not quote_spans or (
                valid_offsets and (span_quote != quote or (start, end) not in quote_spans)
            ):
                continue
            if not valid_offsets:
                if len(quote_spans) != 1:
                    continue
                start, end = quote_spans[0]
            expected_quote_hash = str(reference.get("source_text_hash") or "")
            quote_hash = hashlib.sha256(quote.encode("utf-8")).hexdigest()
            if expected_quote_hash and expected_quote_hash != quote_hash:
                continue

            version_id = document_id
            relationship_path = authorized_document_version_path(
                document_id, source_documents, allowed_document_ids
            )
            fact_key = (document_id, version_id, start, end, quote)
            facts[fact_key] = {
                "artifact_type": "requirement_document",
                "artifact_id": document_id,
                "artifact_version_id": version_id,
                "relationship_path": relationship_path,
                "source_start": start,
                "source_end": end,
                "source": "document",
                "authority": str(document.get("authority") or "PROJECT_REFERENCE"),
                "quote": quote,
            }
            evidence[(document_id, version_id, start, end, quote)] = {
                "artifact_type": "requirement_document",
                "artifact_id": document_id,
                "artifact_version_id": version_id,
                "relationship_path": relationship_path,
                "source": "document",
                "authority": str(document.get("authority") or "PROJECT_REFERENCE"),
                "text": quote,
                "source_start": start,
                "source_end": end,
                "source_verification": "VERIFIED_REQUIREMENT_SOURCE_CITATION",
            }
    return list(facts.values()), list(evidence.values())


def document_content_fingerprint(document):
    content = document.get("normalized_content")
    if isinstance(content, str):
        source_text = content
    elif isinstance(content, (dict, list)):
        source_text = json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    else:
        return None
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def requirement_document_synthesis_snapshot(source_documents):
    fields = (
        "revision",
        "status",
        "ai_enabled",
        "source_version",
        "source_version_sequence",
        "source_series_id",
        "previous_source_version_id",
        "content_hash",
        "authority",
        "source_type",
        "format",
        "index_status",
    )
    snapshots = {}
    for document in source_documents:
        if not document.get("_id"):
            continue
        snapshot = {field: document.get(field) for field in fields}
        normalized_content = document.get("normalized_content")
        snapshot["normalized_content_sha256"] = (
            hashlib.sha256(str(normalized_content).encode("utf-8")).hexdigest()
            if isinstance(normalized_content, str)
            else None
        )
        snapshots[str(document["_id"])] = snapshot
    return snapshots


def requirement_template_source_snapshot_matches(
    template, source_document_ids, source_documents
):
    snapshot = (template.get("synthesis") or {}).get("source_snapshot")
    if not isinstance(snapshot, dict):
        return False
    expected_ids = sorted(set(map(str, source_document_ids)))
    if snapshot.get("source_document_ids") != expected_ids:
        return False
    expected_documents = requirement_document_synthesis_snapshot(
        [source_documents.get(document_id) or {} for document_id in expected_ids]
    )
    if set(expected_documents) != set(expected_ids):
        return False
    stored_documents = snapshot.get("documents")
    if not isinstance(stored_documents, dict) or set(stored_documents) != set(expected_ids):
        return False
    if any(
        not isinstance(stored_documents.get(document_id), dict)
        or {
            key: value
            for key, value in stored_documents[document_id].items()
            if key != "revision"
        }
        != {
            key: value
            for key, value in expected_documents[document_id].items()
            if key != "revision"
        }
        for document_id in expected_ids
    ):
        return False
    if snapshot.get("templates") != {}:
        return False
    return True


def source_extraction_gaps(document_ids, documents):
    gaps = []
    for document_id in document_ids:
        document = documents.get(str(document_id)) or {}
        report = document.get("parse_report")
        report = report if isinstance(report, dict) else {}
        index_status = document.get("index_status")
        extraction_reported = report.get("unprocessed_blocks_reported") is True
        unprocessed_count = report.get("unprocessed_block_count")
        if not isinstance(unprocessed_count, int) or isinstance(unprocessed_count, bool):
            unprocessed_count = None
        if index_status != "INDEXED" or not extraction_reported or unprocessed_count != 0:
            gaps.append(
                {
                    "document_id": str(document_id),
                    "reason": "SOURCE_EXTRACTION_INCOMPLETE",
                    "index_status": index_status or "UNKNOWN",
                    "parser": report.get("parser"),
                    "page_count": report.get("page_count"),
                    "unprocessed_blocks_reported": extraction_reported,
                    "unprocessed_block_count": unprocessed_count,
                    "unprocessed_blocks": report.get("unprocessed_blocks") or [],
                    "unprocessed_blocks_truncated": bool(
                        report.get("unprocessed_blocks_truncated")
                    ),
                }
            )
    return gaps


def source_extraction_warnings(document_ids, documents):
    warnings = []
    truncated = False
    for document_id in document_ids:
        document = documents.get(str(document_id)) or {}
        report = document.get("parse_report")
        report = report if isinstance(report, dict) else {}
        items = report.get("extraction_warnings")
        if not isinstance(items, list) or not items:
            continue
        if len(warnings) >= 500:
            truncated = True
            break
        warning_limit = min(100, 500 - len(warnings))
        for item in items[:warning_limit]:
            if not isinstance(item, dict):
                continue
            warning = {"document_id": str(document_id)}
            for key in ("page_no", "block_id", "type", "reason_code"):
                value = item.get(key)
                if isinstance(value, (str, int)) and not isinstance(value, bool):
                    warning[key] = value[:160] if isinstance(value, str) else value
            confidence = item.get("ocr_page_confidence")
            if (
                isinstance(confidence, (int, float))
                and not isinstance(confidence, bool)
                and 0 <= confidence <= 1
            ):
                warning["ocr_page_confidence"] = float(confidence)
            warnings.append(warning)
        if len(items) > warning_limit:
            truncated = True
    return warnings, truncated


def require_project_scoped_sources(project_id, documents):
    items = response_items(documents)
    if any(item.get("project_id") != project_id for item in items):
        raise ToolOperationError("AI_SOURCE_PROJECT_SCOPE_INVALID")
    return items


async def list_all_ai_readable_requirement_documents(project_id, project_path, config):
    documents = []
    seen_ids = set()
    seen_cursors = set()
    cursor = ""
    while True:
        query = {"limit": 200}
        if cursor:
            query["cursor"] = cursor
        response = await require_operation(
            "GET",
            f"{project_path}/tai-lieu-yeu-cau/nguon-ai?{urlencode(query)}",
            config,
        )
        if not isinstance(response, dict) or not isinstance(response.get("items"), list):
            raise ToolOperationError("AI_SOURCE_PAGE_INVALID")
        page = require_project_scoped_sources(project_id, response["items"])
        for document in page:
            document_id = str(document.get("_id") or "")
            if not document_id or document_id in seen_ids:
                raise ToolOperationError("AI_SOURCE_PAGINATION_DUPLICATE")
            seen_ids.add(document_id)
            documents.append(document)
        next_cursor = response.get("next_cursor")
        if next_cursor is None:
            break
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
            raise ToolOperationError("AI_SOURCE_PAGINATION_CURSOR_INVALID")
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    return documents


async def revalidate_compilation_sources(
    project_id, project_path, source_document_ids, source_documents, config
):
    visible_latest = await list_all_ai_readable_requirement_documents(
        project_id, project_path, config
    )
    latest_documents = {
        str(item["_id"]): item
        for item in visible_latest
        if item.get("_id")
    }
    latest_compilable_ids = compilable_document_ids(
        list(latest_documents.values()), source_document_ids[0] if source_document_ids else ""
    )
    expected_source_ids = set(map(str, source_document_ids))
    if not expected_source_ids or not expected_source_ids.issubset(latest_compilable_ids):
        raise ToolOperationError("AI_SOURCE_SCOPE_CHANGED_DURING_COMPILATION")

    for document_id in source_document_ids:
        previous = source_documents.get(str(document_id)) or {}
        current = latest_documents.get(str(document_id)) or {}
        if (
            previous.get("project_id") != project_id
            or current.get("project_id") != project_id
            or current.get("status") != "READY"
            or current.get("ai_enabled") is not True
            or current.get("source_version") != previous.get("source_version")
            or current.get("source_version_sequence")
            != previous.get("source_version_sequence")
            or current.get("source_series_id") != previous.get("source_series_id")
            or current.get("previous_source_version_id")
            != previous.get("previous_source_version_id")
            or current.get("authority") != previous.get("authority")
            or current.get("filename") != previous.get("filename")
            or current.get("title") != previous.get("title")
            or current.get("source_type") != previous.get("source_type")
            or current.get("content_hash") != previous.get("content_hash")
            or current.get("index_status") != previous.get("index_status")
            or current.get("parse_report") != previous.get("parse_report")
            or document_content_fingerprint(current)
            != document_content_fingerprint(previous)
        ):
            raise ToolOperationError("AI_SOURCE_SNAPSHOT_CHANGED_DURING_COMPILATION")


def authorized_document_version_path(
    document_id, source_documents, allowed_document_ids=None
):
    path = []
    visited = set()
    current_id = str(document_id)
    allowed_ids = (
        {str(value) for value in allowed_document_ids}
        if allowed_document_ids is not None
        else None
    )
    if allowed_ids is not None and current_id not in allowed_ids:
        return path
    while current_id and current_id not in visited and len(path) < 50:
        current = source_documents.get(current_id)
        if not isinstance(current, dict) or str(current.get("_id") or "") != current_id:
            break
        visited.add(current_id)
        path.append(current_id)
        previous_id = str(current.get("previous_source_version_id") or "")
        if not previous_id or previous_id in visited:
            break
        if allowed_ids is not None and previous_id not in allowed_ids:
            break
        previous = source_documents.get(previous_id)
        if (
            not isinstance(previous, dict)
            or str(previous.get("_id") or "") != previous_id
        ):
            break
        current_series = current.get("source_series_id")
        previous_series = previous.get("source_series_id")
        if (
            not current_series
            or not previous_series
            or str(current_series) != str(previous_series)
        ):
            break
        current_project = str(current.get("project_id") or "")
        previous_project = str(previous.get("project_id") or "")
        if not current_project or current_project != previous_project:
            break
        current_sequence = current.get("source_version_sequence")
        previous_sequence = previous.get("source_version_sequence")
        if current_sequence is not None or previous_sequence is not None:
            if (
                not isinstance(current_sequence, int)
                or isinstance(current_sequence, bool)
                or not isinstance(previous_sequence, int)
                or isinstance(previous_sequence, bool)
                or current_sequence != previous_sequence + 1
            ):
                break
        current_id = previous_id
    path.reverse()
    return path


def classify_requirement_ingestion_outcome(unresolved):
    if not unresolved:
        return "COMPLETED", "COMPLETED", None
    input_reasons = {
        "REQUIREMENT_MATCH_NEEDS_RECONCILIATION",
        "HUMAN_REQUIREMENT_REVIEW_REQUIRED",
        "HUMAN_TEST_CASE_REVIEW_REQUIRED",
    }
    if all(item.get("reason") in input_reasons for item in unresolved):
        reason_code = (
            "REQUIREMENT_MATCH_NEEDS_RECONCILIATION"
            if any(
                item.get("reason") == "REQUIREMENT_MATCH_NEEDS_RECONCILIATION"
                for item in unresolved
            )
            else next(item["reason"] for item in unresolved)
        )
        return (
            "awaiting_input",
            "AWAITING_INPUT",
            reason_code,
        )
    return "partial_failure", "INCOMPLETE", None


def focused_requirement_generation_request(generation_request, missing_criteria):
    return {
        **generation_request,
        "acceptance_criterion_ids": sorted(missing_criteria),
        "max_cases": max(len(missing_criteria), 1),
        "instruction": focused_requirement_test_generation_instruction(),
    }


def qa_test_design_handoff_versions(requirements, permissions):
    if "ai.generate_testcase" in set(permissions):
        return []
    handoffs = []
    for item in requirements:
        version = item.get("version") or {}
        version_id = str(version.get("_id") or "")
        if (
            not version_id
            or version.get("status") != "BASELINED"
        ):
            continue
        criteria = version.get("acceptance_criterion_ids") or [
            criterion.get("_id")
            for criterion in version.get("acceptance_criteria", [])
            if criterion.get("_id")
        ]
        if criteria:
            handoffs.append(version_id)
    return list(dict.fromkeys(handoffs))


def safe_requirement_import_resolution(candidate_match):
    raw_matches = candidate_match.get("matches")
    if raw_matches == []:
        return ("create_requirement", None)
    if not isinstance(raw_matches, list):
        return None
    matches = [
        item
        for item in raw_matches
        if item.get("requirement_id") and item.get("version_id")
        and item.get("requirement_status") not in {"OBSOLETE", "ARCHIVED"}
    ]
    exact_matches = [item for item in matches if item.get("match_type") == "EXACT"]
    if exact_matches:
        return ("link_source", exact_matches[0]) if len(exact_matches) == 1 else None
    stable_identity_matches = [
        item for item in matches if item.get("match_type") == "SAME_KEY"
    ]
    if len(stable_identity_matches) == 1:
        return "create_version", stable_identity_matches[0]
    return None


def requirement_versions_requiring_maintenance(import_job):
    resolutions = (import_job or {}).get("resolutions")
    if not isinstance(resolutions, list):
        return set()
    return {
        str(item["to_version_id"])
        for item in resolutions
        if isinstance(item, dict)
        and item.get("action") == "create_version"
        and isinstance(item.get("to_version_id"), str)
        and item["to_version_id"].strip()
    }


def safe_in_import_duplicate_resolution(candidate_match, earlier_matches, resolutions):
    internal_matches = [
        item
        for item in earlier_matches
        if item.get("match_type") in {"IN_IMPORT", "SAME_KEY_IN_IMPORT"}
    ]
    if not internal_matches or any(
        item.get("match_type") != "IN_IMPORT" for item in internal_matches
    ):
        return None
    target_candidate_ids = {
        str(item.get("candidate_id") or "") for item in internal_matches
    }
    if "" in target_candidate_ids:
        return None
    resolution_by_candidate = {
        str(item.get("candidate_id") or ""): item
        for item in resolutions
        if item.get("candidate_id")
    }
    if not target_candidate_ids.issubset(resolution_by_candidate):
        return None
    target_requirement_ids = {
        str(resolution_by_candidate[candidate_id].get("requirement_id") or "")
        for candidate_id in target_candidate_ids
        if candidate_id in resolution_by_candidate
    }
    if len(target_requirement_ids) != 1 or "" in target_requirement_ids:
        return None
    current_matches = candidate_match.get("matches")
    if not isinstance(current_matches, list) or len(current_matches) != 1:
        return None
    match = current_matches[0]
    if (
        match.get("match_type") != "EXACT"
        or str(match.get("requirement_id") or "") not in target_requirement_ids
        or not match.get("version_id")
    ):
        return None
    return "link_source", match


async def process_ingested_requirement_document(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    document_id: Annotated[str, Field(min_length=1, description="Verified uploaded requirement document identifier")],
    source_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", description="Content hash captured when the user started this document run")],
    resume_import_job_id: Annotated[str | None, Field(description="Previously confirmed import job for resuming the same document workflow")] = None,
    resume_requirement_ids: Annotated[list[str], Field(description="Requirements created by the prior confirmed import in this workflow")] = Field(default_factory=list),
    config: RunnableConfig = None,
) -> str:
    """Run the authorized document-ingestion workflow through a grounded template, Requirements, duplicate-safe Test Cases, and lifecycle checks"""
    configurable = (config or {}).get("configurable", {})
    permissions = set(configurable.get("permissions", []))
    required_permissions = {
        "project.read",
        "requirement.create",
        "requirement_document.review_extraction",
        "requirement.version.create",
        "requirement.read",
        "ai.run_lint",
    }
    missing_permissions = sorted(required_permissions - permissions)
    if missing_permissions:
        return json.dumps(
            {"status": "blocked", "reason_code": "REQUIRED_PERMISSION_MISSING", "missing_permissions": missing_permissions},
            ensure_ascii=False,
        )

    project_path = f"/du-an/{project_id}"
    project = await require_operation("GET", project_path, config)
    if project.get("_id") != project_id or not project.get("project_type"):
        return json.dumps(
            {"status": "blocked", "reason_code": "PROJECT_TYPE_REQUIRED"},
            ensure_ascii=False,
        )
    visible_document_items = await list_all_ai_readable_requirement_documents(
        project_id, project_path, config
    )
    source_documents = {
        str(item["_id"]): item
        for item in visible_document_items
        if item.get("_id")
    }
    available_document_ids = compilable_document_ids(visible_document_items, document_id)
    source_document_ids = [document_id] if document_id in available_document_ids else []
    if not source_document_ids:
        raise ToolOperationError("AI_ENABLED_SOURCE_NOT_ACCESSIBLE")
    source_document = source_documents[document_id]
    if str(source_document.get("content_hash") or "") != source_hash:
        raise ToolOperationError("DOCUMENT_EVENT_SOURCE_CHANGED")

    extraction_gaps = source_extraction_gaps(source_document_ids, source_documents)
    extraction_warnings, extraction_warnings_truncated = source_extraction_warnings(
        source_document_ids, source_documents
    )
    if extraction_gaps:
        return json.dumps(
            {
                "status": "partial_failure",
                "reason_code": "SOURCE_EXTRACTION_INCOMPLETE",
                "safe_no_mutation": True,
                "source_extraction_gaps": extraction_gaps,
                "source_extraction_warnings": extraction_warnings,
                "source_extraction_warnings_truncated": extraction_warnings_truncated,
                "verification": {
                    "status": "INCOMPLETE",
                    "project_id": project_id,
                    "artifact_ids": [],
                    "checks": [],
                },
            },
            ensure_ascii=False,
        )

    await revalidate_compilation_sources(
        project_id, project_path, source_document_ids, source_documents, config
    )

    async def validate_source_access():
        configurable = (config or {}).get("configurable", {})
        ai_run_id = configurable.get("ai_run_id")
        if ai_run_id:
            active_run = await ai_run_repository.get_run(str(ai_run_id))
            if not active_run:
                raise ToolOperationError("AI_RUN_NOT_FOUND")
            if active_run.status == AIRunStatus.CANCELLED:
                raise ToolOperationError(
                    active_run.error_code or "AI_READ_PERMISSION_REVOKED"
                )
        await revalidate_compilation_sources(
            project_id, project_path, source_document_ids, source_documents, config
        )

    async def authorized_source_operation(method, path, payload=None, timeout=None):
        if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            await validate_source_access()
        if timeout is None:
            return await require_operation(method, path, config, payload)
        return await require_operation(method, path, config, payload, timeout=timeout)

    templates = await require_operation("GET", f"{project_path}/mau-yeu-cau", config)
    reusable_templates = [
        item
        for item in response_items(templates)
        if item.get("project_id") == project_id
        and sorted(set(map(str, item.get("source_document_ids", []))))
        == source_document_ids
        and item.get("status") == "DRAFT"
        and requirement_template_source_snapshot_matches(
            item, source_document_ids, source_documents
        )
    ]
    template = max(
        reusable_templates,
        key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
        default=None,
    )
    if not template:
        template = await authorized_source_operation(
            "POST",
            f"{project_path}/mau-yeu-cau/tong-hop",
            {
                "name": str(source_documents[document_id].get("title") or source_documents[document_id].get("filename") or document_id),
                "product_types": [project["project_type"]],
                "source_document_ids": source_document_ids,
                "source_template_ids": [],
                "instruction": requirement_document_synthesis_instruction(),
                "output_language": str(
                    ((config or {}).get("configurable") or {}).get("output_language")
                    or "auto"
                ),
            },
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
    if not template.get("_id") or template.get("project_id") != project_id:
        raise RuntimeError("TEMPLATE_READBACK_INVALID")
    template_conflicts = (template.get("synthesis") or {}).get("conflicts") or []
    if template_conflicts:
        conflict_template = await require_operation(
            "GET", f"{project_path}/mau-yeu-cau/{template['_id']}", config
        )
        conflicts = (conflict_template.get("synthesis") or {}).get("conflicts") or []
        if (
            conflict_template.get("_id") != template["_id"]
            or conflict_template.get("project_id") != project_id
            or not conflicts
        ):
            raise RuntimeError("SOURCE_CONFLICT_READBACK_INVALID")
        template = conflict_template
        return json.dumps(
            {
                "status": "awaiting_decision",
                "reason_code": "SOURCE_CONFLICT",
                "template_id": template["_id"],
                "conflicts": conflicts,
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [template["_id"]],
                    "checks": [
                        {
                            "artifact_id": template["_id"],
                            "artifact_type": "requirement_template",
                            "conflict_count": len(conflicts),
                        }
                    ],
                },
            },
            ensure_ascii=False,
        )
    template_requirements = template.get("requirements") or []
    if not template_requirements:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "NO_GROUNDED_REQUIREMENTS",
                "template_id": template["_id"],
            },
            ensure_ascii=False,
        )

    resumed_requirement_ids = set()
    if resume_import_job_id:
        import_job = await require_operation(
            "GET", f"/nhap-yeu-cau/{resume_import_job_id}", config
        )
        if (
            import_job.get("_id") != resume_import_job_id
            or import_job.get("project_id") != project_id
            or import_job.get("template_id") != template.get("_id")
            or import_job.get("status") != "CONFIRMED"
        ):
            raise ToolOperationError("RESUME_IMPORT_SCOPE_MISMATCH")
        resumed_requirement_ids = {
            str(value)
            for value in [
                *(resume_requirement_ids or []),
                *(import_job.get("created_requirement_ids") or []),
            ]
            if value
        }
        if not resumed_requirement_ids:
            raise ToolOperationError("RESUME_IMPORT_REQUIREMENTS_MISSING")
    else:
        import_job = await authorized_source_operation(
            "POST", f"{project_path}/mau-yeu-cau/{template['_id']}/xem-truoc"
        )
    if import_job.get("project_id") != project_id or not import_job.get("_id"):
        raise RuntimeError("REQUIREMENT_IMPORT_PREVIEW_INVALID")

    linked_requirement_ids = set(resumed_requirement_ids) | {
        item.get("requirement_id")
        for item in import_job.get("resolutions", [])
        if item.get("requirement_id")
    }
    unresolved = []
    updated_requirement_versions = requirement_versions_requiring_maintenance(import_job)
    if import_job.get("status") == "PREVIEW_READY":
        comparison = await require_operation(
            "GET", f"/nhap-yeu-cau/{import_job['_id']}/doi-chieu", config
        )
        candidate_matches = comparison.get("comparisons", [])
        in_import_matches = {
            str(item.get("candidate_id")): item.get("matches", [])
            for item in candidate_matches
            if item.get("candidate_id")
        }
        for queued_candidate_match in candidate_matches:
            candidate_id = queued_candidate_match.get("candidate_id")
            if not candidate_id:
                continue
            comparison = await require_operation(
                "GET", f"/nhap-yeu-cau/{import_job['_id']}/doi-chieu", config
            )
            candidate_match = next(
                (
                    item
                    for item in comparison.get("comparisons", [])
                    if item.get("candidate_id") == candidate_id
                ),
                None,
            )
            if not candidate_match:
                continue
            current_job = await require_operation(
                "GET", f"/nhap-yeu-cau/{import_job['_id']}", config
            )
            original_internal_matches = [
                item
                for item in in_import_matches.get(str(candidate_id), [])
                if item.get("match_type") in {"IN_IMPORT", "SAME_KEY_IN_IMPORT"}
            ]
            if original_internal_matches:
                resolution = safe_in_import_duplicate_resolution(
                    candidate_match,
                    original_internal_matches,
                    current_job.get("resolutions", []),
                )
            else:
                resolution = safe_requirement_import_resolution(candidate_match)
            if resolution and resolution[0] == "link_source":
                _, match = resolution
                current_job = await require_operation("GET", f"/nhap-yeu-cau/{import_job['_id']}", config)
                await authorized_source_operation(
                    "POST",
                    f"/nhap-yeu-cau/{import_job['_id']}/ung-vien/{candidate_id}/doi-chieu",
                    {
                        "expected_revision": current_job["revision"],
                        "target_requirement_id": match["requirement_id"],
                        "expected_target_version_id": match["version_id"],
                        "action": "link_source",
                        "reason": 'Tài liệu {document_id} xác nhận cùng nội dung Requirement; chỉ bổ sung dấu vết nguồn.'.format(document_id=document_id),
                    },
                )
                linked_requirement_ids.add(match["requirement_id"])
                continue

            if resolution and resolution[0] == "create_version":
                _, match = resolution
                current_job = await require_operation(
                    "GET", f"/nhap-yeu-cau/{import_job['_id']}", config
                )
                resolution = await authorized_source_operation(
                    "POST",
                    f"/nhap-yeu-cau/{import_job['_id']}/ung-vien/{candidate_id}/doi-chieu",
                    {
                        "expected_revision": current_job["revision"],
                        "target_requirement_id": match["requirement_id"],
                        "expected_target_version_id": match["version_id"],
                        "action": "create_version",
                        "reason": 'Tài liệu {document_id} được đối chiếu với một Requirement hiện có theo mã định danh ổn định; tạo phiên bản mới từ nội dung có nguồn và giữ nguyên lịch sử phiên bản.'.format(document_id=document_id),
                    },
                )
                updated_requirement_versions.update(
                    item.get("to_version_id")
                    for item in resolution.get("resolutions", [])
                    if item.get("candidate_id") == candidate_id
                    and item.get("to_version_id")
                )
                linked_requirement_ids.add(match["requirement_id"])
                continue

            if resolution and resolution[0] == "create_requirement":
                current_job = await require_operation(
                    "GET", f"/nhap-yeu-cau/{import_job['_id']}", config
                )
                resolved_job = await authorized_source_operation(
                    "POST",
                    f"/nhap-yeu-cau/{import_job['_id']}/ung-vien/{candidate_id}/doi-chieu",
                    {
                        "expected_revision": current_job["revision"],
                        "action": "create_requirement",
                        "reason": 'Tài liệu {document_id} tạo Requirement nháp riêng vì ứng viên không trùng với Requirement hiện có; ứng viên mơ hồ khác vẫn chờ làm rõ.'.format(document_id=document_id),
                    },
                )
                linked_requirement_ids.update(
                    item.get("requirement_id")
                    for item in resolved_job.get("resolutions", [])
                    if item.get("requirement_id")
                )

        import_job = await require_operation("GET", f"/nhap-yeu-cau/{import_job['_id']}", config)
        linked_requirement_ids.update(
            item.get("requirement_id")
            for item in import_job.get("resolutions", [])
            if item.get("requirement_id")
        )
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
                created_result, import_job = await apply_requirement_import_safely(
                    import_job, config, before_write=validate_source_access
                )
                linked_requirement_ids.update(
                    item.get("_id") for item in created_result.get("requirements", []) if item.get("_id")
                )

    if import_job.get("status") == "CONFIRMED":
        linked_requirement_ids.update(import_job.get("created_requirement_ids", []))

    requirements = []
    for requirement_id in sorted(linked_requirement_ids):
        requirement = await require_operation("GET", f"/yeu-cau/{requirement_id}", config)
        if requirement.get("project_id") != project_id or not requirement.get("current_version_id"):
            raise RuntimeError("REQUIREMENT_READBACK_INVALID")
        current = requirement.get("current_version") or await require_operation(
            "GET", f"/phien-ban-yeu-cau/{requirement['current_version_id']}", config
        )
        if current.get("status") != "BASELINED":
            unresolved.append({
                "requirement_id": requirement["_id"],
                "requirement_version_id": current["_id"],
                "reason": "HUMAN_REQUIREMENT_REVIEW_REQUIRED",
            })
        requirements.append({"requirement": requirement, "version": current})

    document_run_id = str(configurable.get("ai_run_id") or "")
    workflow_stages = {
        "test_plan": {"status": "NOT_STARTED"},
        "test_scenarios": {"status": "NOT_STARTED", "draft_ids": []},
        "test_cases": {"status": "NOT_STARTED", "draft_ids": []},
        "test_run": {"status": "REQUIRES_REAL_EXECUTION"},
        "test_report": {"status": "REQUIRES_EXECUTION_RESULTS"},
        "release": {"status": "REQUIRES_HUMAN_REVIEW_AND_APPROVAL"},
    }
    design_requirements = [
        item
        for item in requirements
        if item.get("version", {}).get("_id")
    ]
    review_required_version_ids = [
        str(item["version"]["_id"])
        for item in design_requirements
        if item["version"].get("status") != "BASELINED"
    ]
    design_version_ids = [
        str(item["version"]["_id"])
        for item in design_requirements
        if item["version"].get("status") == "BASELINED"
    ]
    if design_version_ids and {"testplan.read", "ai.ask_project"} <= permissions:
        try:
            await validate_source_access()
            plan_suggestion = await require_operation(
                "POST",
                f"/du-an/{project_id}/ke-hoach-kiem-thu/ai/de-xuat",
                config,
                {
                    "requirement_version_ids": design_version_ids,
                    "instruction": (
                        "Return a traceable Test Plan proposal for review only from the exact imported Requirement "
                        "versions and their acceptance criteria. Do not create or save a Test Plan. Do not invent "
                        "schedules, team assignments, environments, release data, or unsupported scope. Keep "
                        "conflicting source values unresolved."
                    ),
                },
                timeout=settings.MODEL_TIMEOUT_SECONDS,
            )
            proposal = plan_suggestion.get("suggestion") or {}
            workflow_stages["test_plan"] = {
                "status": "PROPOSED",
                "suggestion": proposal,
                "source_warnings": (plan_suggestion.get("warnings") or proposal.get("warnings") or [])[:20],
                "unresolved_questions": plan_suggestion.get("unresolved_questions", [])[:30],
                "evidence_refs": plan_suggestion.get("evidence_refs", [])[:100],
                "field_evidence": plan_suggestion.get("field_evidence", [])[:100],
            }
        except (ToolOperationError, RuntimeError, httpx.TimeoutException, httpx.NetworkError) as error:
            workflow_stages["test_plan"] = {
                "status": "BLOCKED",
                "reason_code": getattr(error, "reason_code", str(error) or "TEST_PLAN_SUGGESTION_FAILED"),
            }
            unresolved.append({
                "reason": "DOCUMENT_WORKFLOW_TEST_PLAN_SUGGESTION_FAILED",
                "details": workflow_stages["test_plan"],
            })
    elif design_version_ids:
        workflow_stages["test_plan"] = {
            "status": "BLOCKED",
            "reason_code": "TEST_PLAN_SUGGESTION_PERMISSION_MISSING",
        }
    elif review_required_version_ids:
        workflow_stages["test_plan"] = {
            "status": "AWAITING_REQUIREMENT_REVIEW",
            "requirement_version_ids": review_required_version_ids,
        }

    if design_version_ids and "ai.generate_scenario" in permissions and "testscenario.create" in permissions:
        scenario_ids = []
        scenario_blockers = []
        for requirement in design_requirements:
            version_id = str(requirement["version"]["_id"])
            if requirement["version"].get("status") != "BASELINED":
                continue
            try:
                await validate_source_access()
                preview = await require_operation(
                    "POST",
                    f"/phien-ban-yeu-cau/{version_id}/ai/sinh-kich-ban",
                    config,
                    {
                        "preview_only": True,
                        "max_cases": 50,
                        "instruction": "Generate only source-grounded draft Test Scenarios. Preserve unresolved conflicts as warnings and do not invent expected behavior.",
                    },
                    timeout=settings.MODEL_TIMEOUT_SECONDS,
                )
                scenario_payloads = [
                    item.get("draft")
                    for item in preview.get("items", [])
                    if isinstance(item, dict) and isinstance(item.get("draft"), dict)
                ]
                if scenario_payloads:
                    allowed_fields = {
                        "scenario_key", "title", "objective", "risk", "priority",
                        "requirement_version_ids", "acceptance_criterion_ids",
                        "test_condition_ids", "status", "origin", "category", "description",
                        "actors", "preconditions", "business_flow", "expected_outcome",
                        "test_data_notes", "test_level", "test_kind", "owner_id", "tags",
                    }
                    scenario_payloads = [
                        {key: value for key, value in item.items() if key in allowed_fields}
                        for item in scenario_payloads
                    ]
                    created_scenarios = await authorized_source_operation(
                        "POST",
                        f"/du-an/{project_id}/kich-ban-kiem-thu/ban-nhap/lo",
                        scenario_payloads,
                    )
                    if not isinstance(created_scenarios, list) or len(created_scenarios) != len(scenario_payloads):
                        raise RuntimeError("TEST_SCENARIO_DRAFT_READBACK_INVALID")
                    readback_ids = [
                        str(item["_id"])
                        for item in created_scenarios
                        if item.get("project_id") == project_id and item.get("_id") and item.get("status") == "draft"
                    ]
                    if len(readback_ids) != len(created_scenarios):
                        raise RuntimeError("TEST_SCENARIO_DRAFT_READBACK_INVALID")
                    scenario_ids.extend(readback_ids)
                scenario_blockers.extend(preview.get("warnings", []))
            except (ToolOperationError, RuntimeError, httpx.TimeoutException, httpx.NetworkError) as error:
                scenario_blockers.append(getattr(error, "reason_code", str(error) or "SCENARIO_GENERATION_FAILED"))
        workflow_stages["test_scenarios"] = {
            "status": "DRAFT_CREATED" if scenario_ids else "PARTIAL_OR_BLOCKED",
            "draft_ids": scenario_ids,
            "warnings": list(dict.fromkeys(map(str, scenario_blockers)))[:50],
            "evaluation": {
                "assessment_type": "NOT_AVAILABLE",
                "reason": "Chưa có bộ tham chiếu độc lập theo Scenario cho nguồn này.",
            },
        }
        if not scenario_ids:
            unresolved.append({
                "reason": "DOCUMENT_WORKFLOW_SCENARIO_DRAFTS_UNAVAILABLE",
                "details": workflow_stages["test_scenarios"],
            })
    elif design_version_ids:
        workflow_stages["test_scenarios"] = {
            "status": "BLOCKED",
            "reason_code": "SCENARIO_GENERATION_PERMISSION_MISSING",
            "draft_ids": [],
        }
    elif review_required_version_ids:
        workflow_stages["test_scenarios"] = {
            "status": "AWAITING_REQUIREMENT_REVIEW",
            "requirement_version_ids": review_required_version_ids,
            "draft_ids": [],
        }

    if design_version_ids and "ai.generate_testcase" in permissions and "testcase.create" in permissions:
        workflow_stages["test_cases"] = {"status": "IN_PROGRESS", "draft_ids": []}
    elif design_version_ids:
        workflow_stages["test_cases"] = {
            "status": "BLOCKED",
            "reason_code": "TEST_CASE_GENERATION_PERMISSION_MISSING",
            "draft_ids": [],
        }
    elif review_required_version_ids:
        workflow_stages["test_cases"] = {
            "status": "AWAITING_REQUIREMENT_REVIEW",
            "requirement_version_ids": review_required_version_ids,
            "draft_ids": [],
        }

    changed_versions = [
        item["version"]
        for item in requirements
        if configurable.get("allow_test_case_generation") is True
        and item["version"].get("_id") in updated_requirement_versions
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
        if parsed_change_result and parsed_change_result.get("status") == "awaiting_input":
            unresolved.append({
                "requirement_version_id": version["_id"],
                "reason": parsed_change_result.get("reason_code") or "REQUIREMENT_CHANGE_INPUT_REQUIRED",
                "details": parsed_change_result,
            })
        elif not parsed_change_result or parsed_change_result.get("status") != "COMPLETED":
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
    skipped_duplicates = 0
    generation_warnings = []
    unapplied_categories = []
    qa_test_design_handoff_version_ids = (
        qa_test_design_handoff_versions(requirements, permissions)
        if configurable.get("allow_test_design_handoff") is True else []
    )
    versions_by_id = {
        str(item["version"].get("_id")): item["version"]
        for item in requirements
        if item.get("version", {}).get("_id")
    }
    qa_test_design_handoff_evidence = []
    for version_id in qa_test_design_handoff_version_ids:
        version = versions_by_id.get(version_id)
        source_text = str((version or {}).get("plain_text_projection") or "").strip()
        if source_text:
            qa_test_design_handoff_evidence.append(
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": version_id,
                    "artifact_version_id": version_id,
                    "source": "database",
                    "authority": "PROJECT_REQUIREMENT",
                    "text": source_text,
                }
            )
    available_handoff_versions = {
        item["artifact_version_id"] for item in qa_test_design_handoff_evidence
    }
    qa_test_design_handoff_version_ids = [
        version_id
        for version_id in qa_test_design_handoff_version_ids
        if version_id in available_handoff_versions
    ]

    for item in requirements:
        version = item["version"]
        version_id = str(version.get("_id") or "")
        if (
            configurable.get("allow_test_case_generation") is not True
            or version.get("status") != "BASELINED"
            or "ai.generate_testcase" not in permissions
            or "testcase.create" not in permissions
        ):
            continue
        criterion_ids = list(dict.fromkeys(
            str(value)
            for value in (
                version.get("acceptance_criterion_ids")
                or [
                    criterion.get("_id")
                    for criterion in version.get("acceptance_criteria", [])
                    if criterion.get("_id")
                ]
            )
            if value
        ))
        if not criterion_ids:
            unresolved.append(
                {
                    "requirement_version_id": version_id,
                    "reason": "NO_ACCEPTANCE_CRITERIA",
                }
            )
            continue
        generation_request = {
            "categories": [],
            "max_cases": min(len(criterion_ids), 50),
            "preview_only": True,
            "acceptance_criterion_ids": criterion_ids,
            "instruction": requirement_test_generation_instruction(),
        }
        pending = await list_resumable_ai_test_case_drafts(
            project_id, version_id, config
        )
        compatible_pending = [
            draft
            for draft in pending
            if resumable_draft_matches_requirement_scope(
                draft, version_id, criterion_ids
            )
        ]
        created_drafts.extend(compatible_pending)
        for draft in pending:
            if draft not in compatible_pending:
                unresolved.append(
                    {
                        "requirement_version_id": version_id,
                        "test_case_draft_id": draft.get("_id"),
                        "reason": "RESUMABLE_TEST_CASE_DRAFT_SCOPE_MISMATCH",
                    }
                )
        try:
            preview = await generate_grounded_test_case_preview(
                version_id,
                config,
                generation_request,
                before_request=validate_source_access,
            )
        except ToolOperationError as error:
            if error.reason_code not in {
                "GENERATION_EVIDENCE_INSUFFICIENT",
                "AI_UNGROUNDED_OUTPUT",
            }:
                raise
            unresolved.append(
                {
                    "requirement_version_id": version_id,
                    "reason": "TEST_CASE_GENERATION_NOT_GROUNDED",
                    "generation_reason_code": error.reason_code,
                    "acceptance_criterion_ids": criterion_ids,
                }
            )
            generation_warnings.append(
                f"TEST_CASE_GENERATION_NOT_GROUNDED:{version_id}"
            )
            continue

        generation_warnings.extend(preview.get("warnings") or [])
        unapplied_categories.extend(preview.get("unapplied_categories") or [])
        coverage = preview.get("criterion_coverage") or {}
        required_criteria = set(map(str, coverage.get("criterion_ids") or criterion_ids))
        already_covered = set(map(str, coverage.get("linked_criterion_ids") or []))
        pending_criteria = {
            str(criterion_id)
            for draft in compatible_pending
            for criterion_id in draft.get("acceptance_criterion_ids") or []
        }
        novel = []
        for generated in preview.get("items") or []:
            draft = generated.get("draft") or {}
            draft_criteria = set(map(str, draft.get("acceptance_criterion_ids") or []))
            if not draft or not draft_criteria or not draft_criteria <= set(criterion_ids):
                generation_warnings.append("TEST_CASE_ACCEPTANCE_CRITERION_LINK_INVALID")
                skipped_duplicates += 1
                continue
            if generated.get("similar_cases"):
                skipped_duplicates += 1
                continue
            novel.append(draft)

        covered_criteria = already_covered | pending_criteria | {
            str(criterion_id)
            for draft in novel
            for criterion_id in draft.get("acceptance_criterion_ids") or []
        }
        missing_criteria = required_criteria - covered_criteria
        if missing_criteria:
            focused_preview = await generate_grounded_test_case_preview(
                version_id,
                config,
                focused_requirement_generation_request(
                    generation_request, missing_criteria
                ),
                before_request=validate_source_access,
            )
            generation_warnings.extend(focused_preview.get("warnings") or [])
            unapplied_categories.extend(focused_preview.get("unapplied_categories") or [])
            for generated in focused_preview.get("items") or []:
                draft = generated.get("draft") or {}
                draft_criteria = set(map(str, draft.get("acceptance_criterion_ids") or []))
                if (
                    not draft
                    or not draft_criteria.intersection(missing_criteria)
                    or not draft_criteria <= set(criterion_ids)
                    or generated.get("similar_cases")
                ):
                    skipped_duplicates += 1
                    continue
                signature = normalized_text(draft.get("title"))
                if signature and signature not in {
                    normalized_text(existing.get("title")) for existing in novel
                }:
                    novel.append(draft)
                    covered_criteria.update(draft_criteria)
            missing_criteria = required_criteria - covered_criteria

        if missing_criteria:
            unresolved.append(
                {
                    "requirement_version_id": version_id,
                    "reason": "ACCEPTANCE_CRITERIA_NOT_COVERED",
                    "missing_acceptance_criterion_ids": sorted(missing_criteria),
                }
            )
        if not novel:
            continue
        if len(novel) > 1:
            comparison = await authorized_source_operation(
                "POST",
                f"/du-an/{project_id}/ca-kiem-thu/trung-lap/ban-nhap",
                {"items": novel},
            )
            if comparison.get("candidate_count") != len(novel):
                raise RuntimeError("TEST_CASE_BATCH_COMPARISON_READBACK_INVALID")
            novel, consolidated_count, duplicate_conflicts = (
                consolidate_duplicate_test_case_drafts(
                    novel, comparison.get("duplicates") or []
                )
            )
            skipped_duplicates += consolidated_count
            unresolved.extend(duplicate_conflicts)
        if novel:
            created = await authorized_source_operation(
                "POST", f"{project_path}/ban-nhap-ca-kiem-thu/lo", novel
            )
            created_items = created if isinstance(created, list) else created.get("items", [])
            if len(created_items) != len(novel):
                raise RuntimeError("TEST_CASE_BATCH_READBACK_INVALID")
            created_drafts.extend(created_items)

    workflow_stages["test_cases"] = {
        "status": "DRAFT_CREATED" if created_drafts else "PARTIAL_OR_BLOCKED",
        "draft_ids": [str(item.get("_id")) for item in created_drafts if item.get("_id")],
    }
    for draft in created_drafts:
        if draft.get("project_id") != project_id or not draft.get("_id"):
            raise RuntimeError("TEST_CASE_READBACK_INVALID")
        lint = await authorized_source_operation(
            "POST", f"/ca-kiem-thu/{draft['_id']}/kiem-tra"
        )
        if not lint.get("valid"):
            unresolved.append({"test_case_draft_id": draft["_id"], "reason": "TEST_CASE_QUALITY_FAILED"})
            continue
        unresolved.append({"test_case_draft_id": draft["_id"], "reason": "HUMAN_TEST_CASE_REVIEW_REQUIRED"})

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
        requirement_version_id = item["version"]["_id"]
        requirement_version = await require_operation(
            "GET", f"/phien-ban-yeu-cau/{requirement_version_id}", config
        )
        if (
            requirement_version.get("_id") != requirement_version_id
            or requirement_version.get("project_id") != project_id
            or requirement_version.get("requirement_id") != requirement["_id"]
        ):
            raise RuntimeError("REQUIREMENT_VERSION_READBACK_INVALID")
        checks.append(
            {"artifact_id": requirement_version_id, "artifact_type": "requirement_version"}
        )
    verified_source_facts, verified_source_evidence = verified_requirement_source_citations(
        template_requirements, source_documents, source_document_ids
    )
    workflow_status, verification_status, reason_code = (
        classify_requirement_ingestion_outcome(unresolved)
    )
    result = {
        "status": workflow_status,
        **({"reason_code": reason_code} if reason_code else {}),
        "source_document_id": document_id,
        "source_document_title": str(
            source_document.get("title") or source_document.get("filename") or ""
        ),
        "template_id": template["_id"],
        "requirement_import_job_id": import_job["_id"],
        "requirement_ids": [item["requirement"]["_id"] for item in requirements],
        "requirement_version_ids": [item["version"]["_id"] for item in requirements],
        "qa_test_design_handoff_version_ids": qa_test_design_handoff_version_ids,
        "qa_test_design_handoff_evidence": qa_test_design_handoff_evidence,
        "test_case_draft_ids": [item["_id"] for item in created_drafts],
        "workflow_stages": workflow_stages,
        "updated_requirement_version_ids": sorted(updated_requirement_versions),
        "maintenance_results": maintenance_results,
        "skipped_duplicate_count": skipped_duplicates,
        "generation_warnings": list(dict.fromkeys(generation_warnings)),
        "unapplied_categories": sorted(set(unapplied_categories)),
        "unresolved": unresolved,
        "source_extraction_gaps": extraction_gaps,
        "source_extraction_warnings": extraction_warnings,
        "source_extraction_warnings_truncated": extraction_warnings_truncated,
        "source_facts": verified_source_facts,
        "source_evidence": verified_source_evidence,
        "verification": {
            "status": verification_status,
            "project_id": project_id,
            "artifact_ids": [item["artifact_id"] for item in checks],
            "checks": checks,
        },
    }
    return json.dumps(result, ensure_ascii=False, default=str)
