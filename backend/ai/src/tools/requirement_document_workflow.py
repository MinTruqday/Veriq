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
from src.repositories.automation import automation_repository
from src.schemas.automation import AutomationFact, AutomationStatus
from src.services.testability_blueprint import (
    compile_testability_blueprint,
    facts_bound_to_authorized_evidence,
    map_blueprint_obligations_to_requirements,
    requirement_version_source_text,
)
from src.services.automation_provenance import source_quote_spans
from src.tools.automation_publication import (
    publish_grounded_requirement,
    publish_grounded_test_case,
    verified_test_case_publication_readback,
)
from src.tools.registry import with_tool_access
from src.tools.requirement_change_workflow import process_changed_requirement_version
from src.tools.test_case_deduplication import consolidate_duplicate_test_case_drafts
from src.tools.testing import (
    compilable_document_ids,
    list_resumable_ai_test_case_drafts,
    normalized_text,
    plan_clarification_priority,
    resolve_answered_clarifications,
    response_items,
)
from src.tools.testing_api import AutomationOperationError, parse, require_operation

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
    except (AutomationOperationError, httpx.TimeoutException, httpx.NetworkError) as error:
        latest = None
        for _ in range(30):
            try:
                latest = await require_operation("GET", f"/nhap-yeu-cau/{job_id}", config)
            except (AutomationOperationError, httpx.TimeoutException, httpx.NetworkError):
                await asyncio.sleep(2)
                continue
            if latest.get("status") == "CONFIRMED":
                return {"requirements": []}, latest
            if latest.get("status") != "CONFIRMING":
                raise error
            await asyncio.sleep(2)
        raise AutomationOperationError(
            "REQUIREMENT_IMPORT_CONFIRMATION_OUTCOME_UNRESOLVED"
        ) from error

    if latest.get("status") != "CONFIRMED":
        raise RuntimeError("REQUIREMENT_IMPORT_CONFIRMATION_READBACK_INVALID")
    return result, latest


async def generate_grounded_test_case_preview(
    requirement_version_id,
    config,
    payload,
    testability_obligations=None,
    before_request=None,
):
    path = f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu"
    try:
        if before_request is not None:
            await before_request()
        return await require_operation("POST", path, config, payload, timeout=settings.MODEL_TIMEOUT_SECONDS)
    except AutomationOperationError as error:
        if error.reason_code != "AI_UNGROUNDED_OUTPUT":
            raise
    retry_payload = {
        **payload,
        "instruction": retry_grounded_requirement_test_generation_instruction(
            testability_obligations
        ),
    }
    if before_request is not None:
        await before_request()
    return await require_operation(
        "POST", path, config, retry_payload, timeout=settings.MODEL_TIMEOUT_SECONDS
    )


def existing_test_case_supports_obligation(
    requirement_version_id, obligation, test_case, test_case_version
):
    version_id = str(test_case_version.get("_id") or "")
    if (
        not version_id
        or test_case_version.get("test_case_id") != test_case.get("_id")
        or test_case.get("status") != "ACTIVE"
        or test_case.get("stale_status") == "STALE"
        or test_case.get("current_version_id") != version_id
        or requirement_version_id
        not in set(test_case_version.get("requirement_version_ids") or [])
        or test_case_version.get("status") != "ACTIVE"
    ):
        return False

    quote = str(obligation.get("source_quote") or "").strip()
    key = str(obligation.get("key") or "")
    if not quote or not key or not test_case_version.get("coverage_obligations"):
        return False

    evidence_refs = {
        str(reference)
        for reference in test_case_version.get("evidence_refs", [])
        if str(reference).strip()
    }
    source_by_ref = {
        str(item.get("artifact_version_id") or item.get("artifact_id") or ""): str(
            item.get("text") or ""
        )
        for item in test_case_version.get("source_evidence", [])
        if isinstance(item, dict)
    }
    for citation in test_case_version.get("evidence_quotes", []):
        if not isinstance(citation, dict):
            continue
        citation_quote = str(citation.get("quote") or "").strip()
        citation_ref = str(citation.get("evidence_ref") or "")
        if (
            citation_quote == quote
            and citation_ref in evidence_refs
            and source_quote_spans(source_by_ref.get(citation_ref, ""), quote)
        ):
            return True
    return False


def resumable_draft_matches_blueprint_scope(
    draft, requirement_version_id, criterion_ids, obligations
):
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

    obligation_by_key = {
        str(item.get("key")): item
        for item in obligations
        if item.get("key")
    }
    draft_keys = [str(item) for item in (draft.get("coverage_obligations") or [])]
    if len(draft_keys) != len(set(draft_keys)):
        return False
    if obligations and not draft_keys:
        return False
    if not set(draft_keys) <= set(obligation_by_key):
        return False

    allowed_evidence_refs = {str(requirement_version_id), *map(str, criterion_ids)}
    evidence_refs = {
        str(item) for item in (draft.get("evidence_refs") or []) if str(item).strip()
    }
    if not evidence_refs or not evidence_refs <= allowed_evidence_refs:
        return False

    source_evidence = {
        str(item.get("artifact_version_id") or item.get("artifact_id") or ""): str(
            item.get("text") or ""
        )
        for item in (draft.get("source_evidence") or [])
        if isinstance(item, dict)
    }
    if any(not source_evidence.get(reference) for reference in evidence_refs):
        return False

    citations_by_ref = {}
    for citation in (draft.get("evidence_quotes") or []):
        if not isinstance(citation, dict):
            return False
        reference = str(citation.get("evidence_ref") or "")
        quote = str(citation.get("quote") or "").strip()
        if (
            reference not in evidence_refs
            or not quote
            or not source_quote_spans(source_evidence.get(reference, ""), quote)
        ):
            return False
        citations_by_ref.setdefault(reference, []).append(quote)

    for key in draft_keys:
        source_quote = str(obligation_by_key[key].get("source_quote") or "").strip()
        if not source_quote or not any(
            source_quote_spans(citation, source_quote)
            for reference, citations in citations_by_ref.items()
            for citation in citations
            if source_quote_spans(source_evidence.get(reference, ""), source_quote)
        ):
            return False
    return True


def blueprint_obligation_is_represented(obligation, template_requirements, evidence_by_ref):
    source_ref = str(obligation.get("source_ref") or "")
    quote = str(obligation.get("source_quote") or "").strip()
    raw_evidence = evidence_by_ref.get(source_ref)
    evidence_items = raw_evidence if isinstance(raw_evidence, list) else [raw_evidence]
    evidence = next(
        (
            item
            for item in evidence_items
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ),
        None,
    )
    if not evidence or not quote:
        return False
    source_id = str(evidence.get("artifact_id") or source_ref)
    source_text = evidence["text"]
    obligation_spans = source_quote_spans(source_text, quote)
    if not obligation_spans:
        return False
    for requirement in template_requirements:
        for reference in requirement.get("source_refs", []):
            if str(reference.get("requirement_document_id") or "") != source_id:
                continue
            reference_quote = str(reference.get("source_quote") or "").strip()
            start = reference.get("source_start")
            end = reference.get("source_end")
            if (
                not reference_quote
                or isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or (start, end) not in source_quote_spans(source_text, reference_quote)
            ):
                continue
            if any(
                (obligation_start <= start and end <= obligation_end)
                or (start <= obligation_start and obligation_end <= end)
                for obligation_start, obligation_end in obligation_spans
            ):
                return True
    return False


async def resolve_existing_obligation_coverage(
    requirement_version_id,
    project_id,
    obligations,
    generated_obligation_keys,
    similar_cases,
    config,
    cache,
):
    allowed = {
        str(item.get("key")): item
        for item in obligations
        if item.get("key") and str(item.get("key")) in generated_obligation_keys
    }
    reused = {}
    seen_versions = set()
    for candidate in similar_cases:
        version_id = str(candidate.get("target_version_id") or "")
        if not version_id or version_id in seen_versions:
            continue
        seen_versions.add(version_id)
        if version_id not in cache:
            version = await require_operation(
                "GET", f"/phien-ban-ca-kiem-thu/{version_id}", config
            )
            case_id = str(version.get("test_case_id") or "")
            case = (
                await require_operation("GET", f"/ca-kiem-thu/{case_id}", config)
                if case_id
                else {}
            )
            cache[version_id] = (case, version)
        case, version = cache[version_id]
        if (
            version.get("project_id") != project_id
            or case.get("project_id") != project_id
            or version.get("_id") != version_id
        ):
            continue
        for key, obligation in allowed.items():
            if existing_test_case_supports_obligation(
                requirement_version_id, obligation, case, version
            ):
                reused.setdefault(key, []).append(
                    {
                        "test_case_id": case["_id"],
                        "test_case_version_id": version_id,
                    }
                )
    return reused


async def existing_requirement_obligation_coverage(
    requirement_id, project_id, requirement_version_id, obligations, config, page_size=500
):
    if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= 500:
        raise AutomationOperationError("TEST_CASE_DEDUPLICATION_PAGINATION_INVALID")

    page = 1
    existing_cases = []
    seen_ids = set()
    total = None
    total_pages = None
    scope_fingerprint = None
    while total_pages is None or page <= total_pages:
        query = urlencode(
            {
                "requirement_id": requirement_id,
                "page": page,
                "page_size": page_size,
                "sort": "test_case_key",
            }
        )
        result = await require_operation(
            "GET",
            f"/du-an/{project_id}/ca-kiem-thu?{query}",
            config,
        )
        items = response_items(result)
        if not isinstance(result, dict):
            raise AutomationOperationError("TEST_CASE_DEDUPLICATION_PAGINATION_INVALID")
        if not isinstance(result.get("items"), list):
            raise AutomationOperationError("TEST_CASE_DEDUPLICATION_PAGINATION_INVALID")
        for item in items:
            identifier = str(item.get("_id") or "") if isinstance(item, dict) else ""
            if not identifier:
                raise AutomationOperationError("TEST_CASE_DEDUPLICATION_PAGINATION_INVALID")
            if item.get("project_id") != project_id:
                raise AutomationOperationError("TEST_CASE_DEDUPLICATION_SCOPE_INVALID")
            if identifier in seen_ids:
                raise AutomationOperationError("TEST_CASE_DEDUPLICATION_PAGINATION_DUPLICATE")
            seen_ids.add(identifier)
            existing_cases.append(item)
        reported_values = (
            result.get("total"),
            result.get("total_pages"),
            result.get("page"),
            result.get("page_size"),
        )
        if any(not isinstance(value, int) or isinstance(value, bool) for value in reported_values):
            raise AutomationOperationError("TEST_CASE_DEDUPLICATION_PAGINATION_INVALID")
        reported_total, reported_pages, reported_page, reported_page_size = reported_values
        if (
            reported_total < 0
            or reported_pages != math.ceil(reported_total / page_size)
            or reported_page != page
            or reported_page_size != page_size
            or len(items) != min(page_size, max(0, reported_total - (page - 1) * page_size))
        ):
            raise AutomationOperationError("TEST_CASE_DEDUPLICATION_PAGINATION_INVALID")
        reported_fingerprint = result.get("scope_fingerprint")
        if not isinstance(reported_fingerprint, str) or not reported_fingerprint:
            raise AutomationOperationError("TEST_CASE_DEDUPLICATION_SCOPE_FINGERPRINT_MISSING")
        if total is not None and (reported_total != total or reported_pages != total_pages):
            raise AutomationOperationError("TEST_CASE_DEDUPLICATION_SCOPE_CHANGED_DURING_READ")
        if scope_fingerprint is not None and reported_fingerprint != scope_fingerprint:
            raise AutomationOperationError("TEST_CASE_DEDUPLICATION_SCOPE_CHANGED_DURING_READ")
        total = reported_total
        total_pages = reported_pages
        scope_fingerprint = reported_fingerprint
        if total_pages == 0:
            break
        page += 1

    if total is not None and len(existing_cases) != total:
        raise AutomationOperationError("TEST_CASE_DEDUPLICATION_PAGINATION_INCOMPLETE")

    coverage = {}
    for case in existing_cases:
        current_version = case.get("current_version") or {}
        for obligation in obligations:
            key = str(obligation.get("key") or "")
            if (
                not key
                or not existing_test_case_supports_obligation(
                    requirement_version_id,
                    obligation,
                    case,
                    current_version,
                )
            ):
                continue
            coverage.setdefault(key, []).append(
                {
                    "test_case_id": case["_id"],
                    "test_case_version_id": current_version["_id"],
                }
            )
    return coverage


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


def blueprint_source_lineage(blueprint, source_facts):
    claims = [
        (item.get("source_ref"), item.get("source_quote"))
        for item in blueprint.get("obligations", [])
    ]
    claims.extend(
        (reference, item.get("source_quote"))
        for item in blueprint.get("clarifications", [])
        for reference in item.get("evidence_refs", [])
    )
    verified_facts = []
    source_evidence = []
    seen = set()
    for reference, quote in claims:
        reference = str(reference or "")
        quote = str(quote or "").strip()
        if not reference or not quote:
            continue
        for fact in source_facts:
            fact_reference = str(fact.artifact_version_id or fact.artifact_id)
            fact_quote = str(fact.quote or "")
            start = fact.source_start
            end = fact.source_end
            if (
                fact_reference != reference
                or not fact_quote
                or not source_quote_spans(fact_quote, quote)
                or not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or end - start != len(fact_quote)
                or fact.source_offset_basis != "CANONICAL_TEXT"
            ):
                continue
            key = (
                str(fact.artifact_id),
                str(fact.artifact_version_id or ""),
                fact.source_start,
                fact.source_end,
                fact_quote,
            )
            if key in seen:
                continue
            seen.add(key)
            verified_facts.append(fact.model_dump(mode="json"))
            source_evidence.append(
                {
                    "artifact_type": fact.artifact_type,
                    "artifact_id": fact.artifact_id,
                    "artifact_version_id": fact.artifact_version_id or fact.artifact_id,
                    "source": fact.source,
                    "authority": fact.authority,
                    "relationship_path": list(fact.relationship_path),
                    "text": fact_quote,
                    "source_start": fact.source_start,
                    "source_end": fact.source_end,
                    "source_verification": "VERIFIED_BLUEPRINT_SOURCE_FACT",
                    "source_offset_basis": fact.source_offset_basis,
                }
            )
    return verified_facts, source_evidence


def generated_obligation_evidence_matches(coverage_keys, obligation_evidence, obligations):
    keys = {str(key) for key in coverage_keys}
    evidence_by_key = {
        str(item.get("obligation_key") or ""): item
        for item in obligation_evidence
        if isinstance(item, dict)
    }
    obligations_by_key = {
        str(item.get("key") or ""): item
        for item in obligations
        if isinstance(item, dict)
    }
    if not keys or set(evidence_by_key) != keys or not keys <= set(obligations_by_key):
        return False
    for key in keys:
        source_quote = str(obligations_by_key[key].get("source_quote") or "").strip()
        quotes = evidence_by_key[key].get("evidence_quotes") or []
        if not source_quote or not any(
            isinstance(item, dict)
            and (
                source_quote_spans(str(item.get("quote") or ""), source_quote)
                or source_quote_spans(source_quote, str(item.get("quote") or ""))
            )
            for item in quotes
        ):
            return False
    return True


def verified_document_facts(source_document_ids, source_documents):
    facts = []
    evidence = {}
    for document_id in source_document_ids:
        document = source_documents.get(str(document_id)) or {}
        relationship_path = authorized_document_version_path(
            str(document_id), source_documents, source_document_ids
        )
        content = document.get("normalized_content")
        if isinstance(content, str):
            source_text = content
        elif isinstance(content, (dict, list)):
            source_text = json.dumps(
                content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        else:
            continue
        version_id = str(document.get("_id") or document_id)
        reference = version_id
        evidence[reference] = {
            "artifact_type": "requirement_document",
            "artifact_id": str(document_id),
            "artifact_version_id": version_id,
            "source_version": str(document.get("source_version") or ""),
            "relationship_path": relationship_path,
            "authority": str(document.get("authority") or "PROJECT_REFERENCE"),
            "text": source_text,
            "source_offset_basis": "CANONICAL_TEXT",
        }
        cursor = 0
        seen = set()
        for line in source_text.splitlines() or [source_text]:
            for segment in re.split(r"(?<=[.!?。！？])\s+", line):
                quote = segment.strip()
                if not quote:
                    continue
                start = source_text.find(quote, cursor)
                if start < 0:
                    start = source_text.find(quote)
                if start < 0:
                    continue
                end = start + len(quote)
                identity = (start, end, quote)
                if identity in seen:
                    cursor = end
                    continue
                facts.append(
                    AutomationFact(
                        artifact_type="requirement_document",
                        artifact_id=str(document_id),
                        artifact_version_id=version_id,
                        source="document",
                        authority=str(document.get("authority") or "PROJECT_REFERENCE"),
                        relationship_path=relationship_path,
                        quote=quote,
                        fact_kind="source_text_segment",
                        source_start=start,
                        source_end=end,
                        source_offset_basis="CANONICAL_TEXT",
                    )
                )
                cursor = end
                seen.add(identity)
    return facts, evidence


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
    if snapshot.get("documents") != expected_documents:
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
        raise AutomationOperationError("AI_SOURCE_PROJECT_SCOPE_INVALID")
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
            raise AutomationOperationError("AI_SOURCE_PAGE_INVALID")
        page = require_project_scoped_sources(project_id, response["items"])
        for document in page:
            document_id = str(document.get("_id") or "")
            if not document_id or document_id in seen_ids:
                raise AutomationOperationError("AI_SOURCE_PAGINATION_DUPLICATE")
            seen_ids.add(document_id)
            documents.append(document)
        next_cursor = response.get("next_cursor")
        if next_cursor is None:
            break
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
            raise AutomationOperationError("AI_SOURCE_PAGINATION_CURSOR_INVALID")
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
    if latest_compilable_ids != sorted(set(map(str, source_document_ids))):
        raise AutomationOperationError("AI_SOURCE_SCOPE_CHANGED_DURING_COMPILATION")

    for document_id in source_document_ids:
        previous = source_documents.get(str(document_id)) or {}
        current = latest_documents.get(str(document_id)) or {}
        if (
            previous.get("project_id") != project_id
            or current.get("project_id") != project_id
            or current.get("status") != "READY"
            or current.get("ai_enabled") is not True
            or current.get("revision") != previous.get("revision")
            or current.get("source_version") != previous.get("source_version")
            or current.get("source_version_sequence")
            != previous.get("source_version_sequence")
            or current.get("source_series_id") != previous.get("source_series_id")
            or current.get("previous_source_version_id")
            != previous.get("previous_source_version_id")
            or current.get("authority") != previous.get("authority")
            or current.get("index_status") != previous.get("index_status")
            or current.get("parse_report") != previous.get("parse_report")
            or document_content_fingerprint(current)
            != document_content_fingerprint(previous)
        ):
            raise AutomationOperationError("AI_SOURCE_SNAPSHOT_CHANGED_DURING_COMPILATION")


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


def blueprint_clarification_source_ids(
    version, clarification, evidence_by_ref, source_documents
):
    quote = str(clarification.get("source_quote") or "").strip()
    if not quote:
        return []
    refs_by_document = {}
    for source_ref in version.get("source_refs", []):
        document_id = str(source_ref.get("requirement_document_id") or "")
        if document_id:
            refs_by_document.setdefault(document_id, []).append(source_ref)

    matched = []
    for evidence_ref in clarification.get("evidence_refs", []):
        evidence = evidence_by_ref.get(str(evidence_ref)) or {}
        document_id = str(evidence.get("artifact_id") or "")
        document = source_documents.get(document_id) or {}
        if (
            not document_id
            or document.get("ai_enabled") is not True
            or document.get("status") != "READY"
        ):
            continue
        content = document.get("normalized_content")
        if isinstance(content, str):
            source_text = content
        elif isinstance(content, (dict, list)):
            source_text = json.dumps(
                content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        else:
            continue

        source_version = str(document.get("source_version") or "")
        content_hash = str(document.get("content_hash") or "")
        for source_ref in refs_by_document.get(document_id, []):
            expected_version = str(source_ref.get("source_version") or "")
            expected_hash = str(source_ref.get("content_hash") or "")
            if (
                (expected_version and expected_version != source_version)
                or (expected_hash and expected_hash != content_hash)
            ):
                continue
            start = source_ref.get("source_start")
            end = source_ref.get("source_end")
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or not 0 <= start < end <= len(source_text)
            ):
                continue
            span = source_text[start:end]
            stored_quote = str(source_ref.get("source_quote") or "").strip()
            expected_span_hash = str(source_ref.get("source_text_hash") or "")
            if (
                (stored_quote and stored_quote != span)
                or (expected_span_hash and hashlib.sha256(span.encode("utf-8")).hexdigest() != expected_span_hash)
                or not source_quote_spans(span, quote)
            ):
                continue
            matched.append(document_id)
            break
    return list(dict.fromkeys(matched))


def blueprint_clarification_identity(item):
    return (
        item.get("source_ref"),
        item.get("source_quote"),
        item.get("question"),
    )


def unmapped_blueprint_clarifications_after_persistence(unmapped, persisted):
    mapped_codes = {
        str(item.get("blueprint_code"))
        for item in persisted
        if item.get("blueprint_code")
    }
    return [
        item
        for item in unmapped
        if str(item.get("code") or "") not in mapped_codes
    ]


async def persist_blueprint_clarifications(
    version,
    clarifications,
    evidence_by_ref,
    source_documents,
    config,
    obligations=None,
    before_write=None,
):
    if not clarifications:
        return [], []
    obligations_by_key = {
        str(item.get("key")): item
        for item in obligations or []
        if item.get("key")
    }
    validate_blueprint_clarification_obligation_links(
        {"obligations": obligations or [], "clarifications": clarifications}
    )
    existing = response_items(
        await require_operation(
            "GET", f"/phien-ban-yeu-cau/{version['_id']}/phieu-lam-ro", config
        )
    )
    created_or_existing = []
    unmapped = []
    for clarification in clarifications:
        source_ids = blueprint_clarification_source_ids(
            version, clarification, evidence_by_ref, source_documents
        )
        if not source_ids:
            unmapped.append(clarification)
            continue
        for source_id in source_ids:
            unlock_keys = list(dict.fromkeys(
                str(key) for key in clarification.get("unlocks_obligation_keys", [])
            ))
            unlock_quotes = list(dict.fromkeys(
                str(obligations_by_key[key].get("source_quote") or "")
                for key in unlock_keys
                if str(obligations_by_key[key].get("source_quote") or "").strip()
            ))
            payload = {
                "question": clarification["question"],
                "reason": clarification["reason"],
                "source_ref": source_id,
                "source_quote": clarification["source_quote"],
                "unlocks_obligation_keys": unlock_keys,
                "unlocks_source_quotes": unlock_quotes,
            }
            same_finding = next(
                (
                    item
                    for item in existing
                    if blueprint_clarification_identity(item)
                    == blueprint_clarification_identity(payload)
                ),
                None,
            )
            if same_finding:
                created_or_existing.append(
                    {
                        **same_finding,
                        "blueprint_code": clarification.get("code"),
                        "unlocks_obligation_keys": unlock_keys,
                        "unlocks_source_quotes": unlock_quotes,
                    }
                )
                continue
            if before_write is not None:
                await before_write()
            value = await require_operation(
                "POST",
                f"/phien-ban-yeu-cau/{version['_id']}/phieu-lam-ro",
                config,
                payload,
            )
            if (
                value.get("requirement_version_id") != version.get("_id")
                or value.get("source_ref") != source_id
                or value.get("source_quote") != clarification.get("source_quote")
                or not value.get("_id")
            ):
                raise RuntimeError("BLUEPRINT_CLARIFICATION_READBACK_INVALID")
            existing.append(value)
            created_or_existing.append(
                {
                    **value,
                    "blueprint_code": clarification.get("code"),
                    "unlocks_obligation_keys": unlock_keys,
                    "unlocks_source_quotes": unlock_quotes,
                }
            )
    return created_or_existing, unmapped


def blocking_blueprint_clarifications(open_clarifications, blueprint_clarifications):
    blueprint_by_fingerprint = {
        blueprint_clarification_identity(item): item
        for item in blueprint_clarifications
    }
    blocking = []
    for clarification in open_clarifications:
        fingerprint = blueprint_clarification_identity(clarification)
        blueprint_item = blueprint_by_fingerprint.get(fingerprint)
        if blueprint_item is None or blueprint_item.get("unlocks_obligation_keys"):
            blocking.append(clarification)
    return blocking


def classify_requirement_ingestion_outcome(unresolved):
    if not unresolved:
        return "COMPLETED", "COMPLETED", None
    input_reasons = {
        "REQUIREMENT_CLARIFICATION_REQUIRED",
        "REQUIREMENT_MATCH_NEEDS_RECONCILIATION",
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
            "automation_waiting_for_input",
            "AWAITING_INPUT",
            reason_code,
        )
    return "automation_partial_failure", "INCOMPLETE", None


def focused_requirement_generation_request(
    generation_request, missing_criteria, missing_obligation_items
):
    return {
        **generation_request,
        "acceptance_criterion_ids": sorted(missing_criteria),
        "max_cases": max(len(missing_criteria), len(missing_obligation_items), 1),
        "instruction": focused_requirement_test_generation_instruction(
            missing_obligation_items
        ),
    }


def uncovered_blueprint_obligations(
    obligations, generated_cases, reused_coverage, pending_obligation_keys
):
    covered = {str(key) for key in reused_coverage}
    covered.update(str(key) for key in pending_obligation_keys)
    for case in generated_cases:
        covered.update(
            str(key) for key in (case.get("coverage_obligations") or [])
        )
    return [
        item for item in obligations
        if str(item.get("key") or "") not in covered
    ]


def qa_test_design_handoff_versions(
    requirements, permissions, clarification_blocked_version_ids, obligations_by_version
):
    if "ai.generate_testcase" in set(permissions):
        return []
    handoffs = []
    for item in requirements:
        version = item.get("version") or {}
        version_id = str(version.get("_id") or "")
        if (
            not version_id
            or version.get("status") != "BASELINED"
            or version_id in clarification_blocked_version_ids
        ):
            continue
        criteria = version.get("acceptance_criterion_ids") or [
            criterion.get("_id")
            for criterion in version.get("acceptance_criteria", [])
            if criterion.get("_id")
        ]
        version_obligations, unlinked_obligations = obligations_by_version.get(
            version_id, ([], [])
        )
        if (criteria or version_obligations) and not unlinked_obligations:
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


def requirement_import_has_unresolved_matches(comparisons):
    return any(
        isinstance(item, dict)
        and item.get("matches")
        and safe_requirement_import_resolution(item) is None
        for item in comparisons or []
    )


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


def has_conflicting_blueprint_clarification(blueprint):
    return any(
        item.get("category") in {"CONTRADICTION", "INCONSISTENCY"}
        and not item.get("user_resolution")
        for item in blueprint.get("clarifications", [])
    )


def unresolved_blueprint_clarifications(clarifications):
    unresolved = []
    for item in clarifications or []:
        resolution = item.get("user_resolution")
        if not isinstance(resolution, dict) or not all(
            str(resolution.get(field) or "").strip()
            for field in (
                "uncertainty_code",
                "answer",
                "answered_by",
                "answered_at",
                "evidence_ref",
            )
        ):
            unresolved.append(item)
    return unresolved


def clarification_terms(value):
    return {
        token
        for token in re.findall(r"[^\W_]+", str(value or "").casefold(), flags=re.UNICODE)
        if len(token) > 2
    }


def clarification_similarity(left, right):
    left_terms = clarification_terms(left)
    right_terms = clarification_terms(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / min(len(left_terms), len(right_terms))


def clarification_document_ids(references):
    output = set()
    for reference in references or []:
        value = str(reference or "").strip()
        if not value:
            continue
        document_id, separator, suffix = value.partition(":")
        output.add(document_id if separator and suffix.isdigit() else value)
    return output


def match_user_clarification_resolutions(blueprint, conflicts, responses):
    clarifications = [
        item
        for item in blueprint.get("clarifications", [])
        if item.get("category") and item.get("response_allowed", True)
    ]
    if not clarifications or not responses:
        return []

    response_candidates = {}
    for clarification in clarifications:
        clarification_refs = clarification_document_ids(
            clarification.get("evidence_refs")
        )
        candidates = []
        for response_index, response in enumerate(responses):
            response_refs = clarification_document_ids(response.get("evidence_refs"))
            if not clarification_refs.intersection(response_refs):
                continue
            exact_code_match = bool(
                clarification.get("code")
                and response.get("uncertainty_code")
                and str(clarification.get("code")).strip()
                == str(response.get("uncertainty_code")).strip()
            )
            similarity = max(
                clarification_similarity(
                    response.get("question"),
                    " ".join(
                        [
                            str(clarification.get("question") or ""),
                            str(clarification.get("reason") or ""),
                        ]
                    ),
                ),
                clarification_similarity(
                    response.get("reason"),
                    " ".join(
                        [
                            str(clarification.get("question") or ""),
                            str(clarification.get("reason") or ""),
                        ]
                    ),
                ),
            )
            if exact_code_match or similarity >= 0.4:
                candidates.append(
                    (response_index, 1.0 if exact_code_match else similarity)
                )
        candidates.sort(key=lambda item: item[1], reverse=True)
        if (
            candidates
            and (len(candidates) == 1 or candidates[0][1] - candidates[1][1] >= 0.15)
        ):
            response_candidates[id(clarification)] = candidates[0][0]

    response_indexes = list(response_candidates.values())
    duplicated_response_indexes = {
        index for index in response_indexes if response_indexes.count(index) > 1
    }
    response_candidates = {
        clarification_id: response_index
        for clarification_id, response_index in response_candidates.items()
        if response_index not in duplicated_response_indexes
    }

    if not conflicts:
        clarification_by_id = {id(item): item for item in clarifications}
        return [
            {
                "conflict_index": None,
                "clarification": clarification_by_id[clarification_id],
                "response": responses[response_index],
            }
            for clarification_id, response_index in response_candidates.items()
        ]

    conflict_matches = {}
    for conflict_index, conflict in enumerate(conflicts):
        conflict_type = str(conflict.get("type") or "").upper()
        if conflict_type and conflict_type not in {
            "CONTRADICTION",
            "INCONSISTENCY",
        }:
            return []
        conflict_refs = clarification_document_ids(conflict.get("evidence_refs"))
        candidates = []
        for clarification in clarifications:
            if id(clarification) not in response_candidates:
                continue
            clarification_refs = clarification_document_ids(
                clarification.get("evidence_refs")
            )
            if not conflict_refs.intersection(clarification_refs):
                continue
            similarity = clarification_similarity(
                conflict.get("description") or conflict.get("reason"),
                " ".join(
                    [
                        str(clarification.get("question") or ""),
                        str(clarification.get("reason") or ""),
                    ]
                ),
            )
            if similarity >= 0.25:
                candidates.append((clarification, similarity))
        candidates.sort(key=lambda item: item[1], reverse=True)
        if candidates and not (
            len(candidates) > 1 and candidates[0][1] - candidates[1][1] < 0.15
        ):
            conflict_matches[conflict_index] = candidates[0]

    if len({id(item[0]) for item in conflict_matches.values()}) != len(
        conflict_matches
    ):
        return []
    return [
        {
            "conflict_index": conflict_index,
            "clarification": clarification,
            "response": responses[response_candidates[id(clarification)]],
        }
        for conflict_index, (clarification, _) in sorted(conflict_matches.items())
        if id(clarification) in response_candidates
    ]


def template_requirements_with_user_resolutions(template, matches):
    requirements = [dict(item) for item in template.get("requirements") or []]
    for match in matches:
        quote = str(match["clarification"].get("source_quote") or "").strip()
        response = match["response"]
        answer = str(response.get("answer") or "").strip()
        if not quote or not answer:
            return None
        candidates = []
        for index, requirement in enumerate(requirements):
            if any(
                source_quote_spans(
                    str(reference.get("source_quote") or ""), quote
                )
                or source_quote_spans(
                    quote, str(reference.get("source_quote") or "")
                )
                for reference in requirement.get("source_refs", [])
                if isinstance(reference, dict)
            ):
                candidates.append(index)
        if len(candidates) != 1:
            return None
        requirement = requirements[candidates[0]]
        business_rules = list(requirement.get("business_rules") or [])
        if answer not in business_rules:
            business_rules.append(answer)
        requirement["business_rules"] = business_rules
    return requirements


def template_user_resolution_readback_matches(template, matches):
    requirements = template.get("requirements") or []
    for match in matches:
        quote = str(match["clarification"].get("source_quote") or "").strip()
        answer = str(match["response"].get("answer") or "").strip()
        candidates = [
            requirement
            for requirement in requirements
            if any(
                source_quote_spans(str(reference.get("source_quote") or ""), quote)
                or source_quote_spans(quote, str(reference.get("source_quote") or ""))
                for reference in requirement.get("source_refs", [])
                if isinstance(reference, dict)
            )
        ]
        if (
            len(candidates) != 1
            or not answer
            or answer not in (candidates[0].get("business_rules") or [])
        ):
            return False
    return True


def apply_user_clarification_resolutions(blueprint, matches):
    resolved = dict(blueprint)
    clarifications = []
    for item in blueprint.get("clarifications", []):
        match = next(
            (candidate for candidate in matches if candidate["clarification"] is item),
            None,
        )
        if not match:
            clarifications.append(item)
            continue
        response = match["response"]
        clarifications.append(
            {
                **item,
                "user_resolution": {
                    "uncertainty_code": response.get("uncertainty_code"),
                    "answer": response.get("answer"),
                    "answered_by": response.get("answered_by"),
                    "answered_at": response.get("answered_at"),
                    "evidence_ref": response.get("evidence_ref"),
                },
            }
        )
    resolved["clarifications"] = clarifications
    return resolved


async def update_resumed_requirement_drafts(
    project_id, requirement_ids, matches, config, before_write
):
    if not matches:
        return
    permissions = set((config or {}).get("configurable", {}).get("permissions", []))
    if not {"requirement.update", "business_rule.manage"}.issubset(permissions):
        raise AutomationOperationError("REQUIREMENT_CLARIFICATION_UPDATE_PERMISSION_MISSING")
    requirements = []
    for requirement_id in dict.fromkeys(str(value) for value in requirement_ids if value):
        requirement = await require_operation(
            "GET", f"/yeu-cau/{requirement_id}", config
        )
        if requirement.get("project_id") != project_id:
            raise AutomationOperationError("RESUME_REQUIREMENT_PROJECT_MISMATCH")
        version = requirement.get("current_version") or await require_operation(
            "GET", f"/phien-ban-yeu-cau/{requirement['current_version_id']}", config
        )
        requirements.append((requirement, version))

    for match in matches:
        quote = str(match["clarification"].get("source_quote") or "").strip()
        answer = str(match["response"].get("answer") or "").strip()
        if not quote or len(answer) < 2:
            raise AutomationOperationError("CLARIFICATION_RESOLUTION_INCOMPLETE")
        candidates = []
        for requirement, version in requirements:
            if version.get("status") != "DRAFT":
                continue
            if any(
                source_quote_spans(str(reference.get("source_quote") or ""), quote)
                or source_quote_spans(quote, str(reference.get("source_quote") or ""))
                for reference in version.get("source_refs", [])
                if isinstance(reference, dict)
            ):
                candidates.append((requirement, version))
        if len(candidates) != 1:
            raise AutomationOperationError("CLARIFICATION_REQUIREMENT_MATCH_AMBIGUOUS")
        requirement, version = candidates[0]
        business_rules = list(version.get("business_rules") or [])
        if answer not in business_rules:
            updated_business_rules = [*business_rules, answer]
            await before_write()
            await require_operation(
                "PATCH",
                f"/du-an/{project_id}/yeu-cau/{requirement['_id']}",
                config,
                {
                    "expected_revision": version.get("revision"),
                    "business_rules": updated_business_rules,
                },
            )
        readback = await require_operation(
            "GET", f"/yeu-cau/{requirement['_id']}", config
        )
        readback_version = readback.get("current_version") or await require_operation(
            "GET", f"/phien-ban-yeu-cau/{readback['current_version_id']}", config
        )
        if (
            readback.get("project_id") != project_id
            or readback_version.get("status") != "DRAFT"
            or answer not in (readback_version.get("business_rules") or [])
        ):
            raise AutomationOperationError("CLARIFICATION_REQUIREMENT_READBACK_INVALID")
        clarification_payload = await require_operation(
            "GET",
            f"/phien-ban-yeu-cau/{readback_version['_id']}/phieu-lam-ro",
            config,
        )
        matching_clarifications = [
            item
            for item in response_items(clarification_payload)
            if item.get("status") in {"OPEN", "ANSWERED"}
            and (
                source_quote_spans(
                    str(item.get("source_quote") or ""), quote
                )
                or source_quote_spans(
                    quote, str(item.get("source_quote") or "")
                )
            )
        ]
        if len(matching_clarifications) == 1:
            clarification = matching_clarifications[0]
            if clarification.get("status") == "OPEN":
                await before_write()
                await require_operation(
                    "PATCH",
                    f"/phieu-lam-ro/{clarification['_id']}/tra-loi",
                    config,
                    {
                        "expected_revision": clarification.get("revision"),
                        "answer": answer,
                    },
                )
                clarification_readback = response_items(
                    await require_operation(
                        "GET",
                        f"/phien-ban-yeu-cau/{readback_version['_id']}/phieu-lam-ro",
                        config,
                    )
                )
                if not any(
                    item.get("_id") == clarification.get("_id")
                    and item.get("status") == "ANSWERED"
                    and item.get("answer") == answer
                    for item in clarification_readback
                ):
                    raise AutomationOperationError(
                        "REQUIREMENT_CLARIFICATION_ANSWER_READBACK_INVALID"
                    )


def validate_blueprint_clarification_obligation_links(blueprint):
    obligations = blueprint.get("obligations", [])
    known_keys = {str(item.get("key")) for item in obligations if item.get("key")}
    for clarification in blueprint.get("clarifications", []):
        linked_keys = [
            str(key) for key in clarification.get("unlocks_obligation_keys", [])
        ]
        if len(linked_keys) != len(set(linked_keys)) or not set(linked_keys) <= known_keys:
            raise ValueError("BLUEPRINT_CLARIFICATION_UNKNOWN_OBLIGATION_LINK")


@with_tool_access(
    ("requirement",),
    "MUTATE",
    "requirement.create",
)

async def process_ingested_requirement_document(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    document_id: Annotated[str, Field(min_length=1, description="Verified uploaded requirement document identifier")],
    source_facts: Annotated[list[AutomationFact], Field(description="Source facts extracted and quote-verified by the automation graph")] = Field(default_factory=list),
    clarification_responses: Annotated[list[dict[str, Any]], Field(description="Recorded user answers to clarification questions for this ingestion workflow")] = Field(default_factory=list),
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
    visible_document_items = await list_all_ai_readable_requirement_documents(
        project_id, project_path, config
    )
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

    extraction_gaps = source_extraction_gaps(source_document_ids, source_documents)
    extraction_warnings, extraction_warnings_truncated = source_extraction_warnings(
        source_document_ids, source_documents
    )
    if extraction_gaps:
        return json.dumps(
            {
                "status": "automation_partial_failure",
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

    evidence_by_ref = {}
    for item in configurable.get("evidence", []):
        if not isinstance(item, dict) or not item.get("artifact_id"):
            continue
        reference = str(item.get("artifact_version_id") or item.get("artifact_id"))
        evidence_by_ref.setdefault(reference, []).append(item)
    authorized_lineage_by_artifact = {
        source_id: authorized_document_version_path(
            source_id, source_documents, source_document_ids
        )
        for source_id in source_document_ids
    }
    verified_facts = facts_bound_to_authorized_evidence(
        source_facts,
        evidence_by_ref,
        source_document_ids,
        authorized_lineage_by_artifact,
        source_documents,
    )

    all_document_facts, all_document_evidence = verified_document_facts(
        source_document_ids, source_documents
    )
    facts_by_source_span = {
        (
            fact.artifact_id,
            fact.artifact_version_id,
            fact.source_start,
            fact.source_end,
            fact.quote,
        ): fact
        for fact in [*all_document_facts, *verified_facts]
    }
    verified_facts = list(facts_by_source_span.values())
    evidence_by_ref.update(all_document_evidence)

    blueprint = await compile_testability_blueprint(
        project_id,
        verified_facts,
        evidence_by_ref,
        source_document_ids,
    )
    if blueprint.get("status") != "SUCCESS":
        return json.dumps(
            {
                "status": "automation_partial_failure",
                "reason_code": "TESTABILITY_BLUEPRINT_COMPILATION_FAILED",
                "blueprint_reason_codes": blueprint.get("reason_codes", []),
                "blueprint_warnings": blueprint.get("warnings", []),
                "source_fact_count": len(verified_facts),
                "unresolved": [
                    {
                        "reason": "TESTABILITY_BLUEPRINT_COMPILATION_FAILED",
                        "reason_codes": blueprint.get("reason_codes", []),
                    }
                ],
            },
            ensure_ascii=False,
        )

    validate_blueprint_clarification_obligation_links(blueprint)

    await revalidate_compilation_sources(
        project_id, project_path, source_document_ids, source_documents, config
    )

    async def validate_source_access():
        configurable = (config or {}).get("configurable", {})
        automation_run_id = configurable.get("automation_run_id")
        if automation_run_id:
            active_run = await automation_repository.get_run(str(automation_run_id))
            if not active_run:
                raise AutomationOperationError("AUTOMATION_RUN_NOT_FOUND")
            if active_run.status == AutomationStatus.CANCELLED:
                raise AutomationOperationError(
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
                "name": "Mẫu yêu cầu từ tài liệu nguồn",
                "product_types": [project["project_type"]],
                "source_document_ids": source_document_ids,
                "source_template_ids": [],
                "instruction": requirement_document_synthesis_instruction(blueprint),
            },
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
    if not template.get("_id") or template.get("project_id") != project_id:
        raise RuntimeError("TEMPLATE_READBACK_INVALID")
    template_conflicts = (template.get("synthesis") or {}).get("conflicts") or []
    clarification_responses = list(
        clarification_responses
        or ((config or {}).get("configurable") or {}).get(
            "clarification_responses", []
        )
        or []
    )
    matches = match_user_clarification_resolutions(
        blueprint, template_conflicts, clarification_responses
    )
    if (
        template_conflicts
        or has_conflicting_blueprint_clarification(blueprint)
        or matches
    ):
        conflict_template = await require_operation(
            "GET", f"{project_path}/mau-yeu-cau/{template['_id']}", config
        )
        conflicts = (conflict_template.get("synthesis") or {}).get("conflicts") or []
        if (
            conflict_template.get("_id") != template["_id"]
            or conflict_template.get("project_id") != project_id
            or (template_conflicts and not conflicts)
        ):
            raise RuntimeError("SOURCE_CONFLICT_READBACK_INVALID")
        template = conflict_template
        if conflicts:
            matches = match_user_clarification_resolutions(
                blueprint, conflicts, clarification_responses
            )
        if (
            matches
            and "requirement.update" in permissions
            and (not conflicts or len(matches) == len(conflicts))
        ):
            resolved_requirements = template_requirements_with_user_resolutions(
                conflict_template, matches
            )
            expected_version = conflict_template.get("version")
            if (
                resolved_requirements is not None
                and isinstance(expected_version, int)
                and not isinstance(expected_version, bool)
                and expected_version >= 1
            ):
                context = conflict_template.get("context") or {}
                update_payload = {
                    "name": conflict_template.get("name"),
                    "description": conflict_template.get("description") or "",
                    "product_types": conflict_template.get("product_types") or [],
                    "context": {
                        key: context.get(key, default)
                        for key, default in (
                            ("objectives", ""),
                            ("in_scope", ""),
                            ("out_of_scope", ""),
                            ("stakeholders", []),
                            ("actors_and_systems", []),
                            ("glossary", []),
                            ("assumptions", []),
                            ("constraints", []),
                        )
                    },
                    "requirements": resolved_requirements,
                    "source_document_ids": conflict_template.get(
                        "source_document_ids", []
                    ),
                    "source_template_ids": conflict_template.get(
                        "source_template_ids", []
                    ),
                    "expected_version": expected_version,
                    "conflict_resolutions": [
                        "["
                        + str(match["response"].get("uncertainty_code") or "")
                        + "] "
                        + str(match["response"].get("answer") or "")
                        for match in matches
                    ],
                }
                write_error = None
                try:
                    await authorized_source_operation(
                        "PUT",
                        f"{project_path}/mau-yeu-cau/{template['_id']}",
                        update_payload,
                    )
                except (AutomationOperationError, httpx.TimeoutException, httpx.NetworkError) as error:
                    write_error = error
                try:
                    conflict_template = await require_operation(
                        "GET", f"{project_path}/mau-yeu-cau/{template['_id']}", config
                    )
                except (AutomationOperationError, httpx.TimeoutException, httpx.NetworkError) as error:
                    if write_error is not None:
                        raise AutomationOperationError(
                            "TEMPLATE_RESOLUTION_OUTCOME_UNRESOLVED"
                        ) from write_error
                    raise error
                resolved_conflicts = (
                    conflict_template.get("synthesis") or {}
                ).get("conflicts") or []
                resolution_readback_valid = (
                    conflict_template.get("project_id") == project_id
                    and conflict_template.get("_id") == template.get("_id")
                    and isinstance(conflict_template.get("version"), int)
                    and conflict_template.get("version") >= expected_version + 1
                    and not resolved_conflicts
                    and template_user_resolution_readback_matches(
                        conflict_template, matches
                    )
                )
                if not resolution_readback_valid and write_error is not None:
                    raise write_error
                if resolution_readback_valid:
                    template = conflict_template
                    conflicts = []
                    blueprint = apply_user_clarification_resolutions(
                        blueprint, matches
                    )
        blueprint_conflict = has_conflicting_blueprint_clarification(blueprint)
        if conflicts or blueprint_conflict:
            blueprint_source_facts, blueprint_source_evidence = blueprint_source_lineage(
                blueprint, verified_facts
            )
            return json.dumps(
                {
                    "status": "automation_waiting_for_decision",
                    "reason_code": "SOURCE_CONFLICT",
                    "template_id": template["_id"],
                    "conflict_count": len(conflicts) + sum(
                        item.get("category") in {"CONTRADICTION", "INCONSISTENCY"}
                        and not item.get("user_resolution")
                        for item in blueprint.get("clarifications", [])
                    ),
                    "conflicts": conflicts,
                    "clarifications": blueprint.get("clarifications", []),
                    "testability_blueprint": blueprint,
                    "source_facts": blueprint_source_facts,
                    "source_evidence": blueprint_source_evidence,
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
                "status": "automation_blocked",
                "reason_code": "NO_GROUNDED_REQUIREMENTS",
                "template_id": template["_id"],
                "testability_blueprint": blueprint,
            },
            ensure_ascii=False,
        )

    unrepresented_blueprint_obligation_keys = []
    for obligation in blueprint.get("obligations", []):
        if not blueprint_obligation_is_represented(
            obligation, template_requirements, evidence_by_ref
        ):
            unrepresented_blueprint_obligation_keys.append(obligation.get("key"))
    if unrepresented_blueprint_obligation_keys:
        return json.dumps(
            {
                "status": "automation_partial_failure",
                "reason_code": "BLUEPRINT_OBLIGATIONS_NOT_REFLECTED_IN_REQUIREMENTS",
                "template_id": template.get("_id"),
                "blueprint": blueprint,
                "unresolved": [
                    {
                        "reason": "BLUEPRINT_OBLIGATIONS_NOT_REFLECTED_IN_REQUIREMENTS",
                        "obligation_keys": unrepresented_blueprint_obligation_keys,
                    }
                ],
            },
            ensure_ascii=False,
        )

    resumed_requirement_ids = set()
    if resume_import_job_id and clarification_responses:
        import_job = await require_operation(
            "GET", f"/nhap-yeu-cau/{resume_import_job_id}", config
        )
        if (
            import_job.get("_id") != resume_import_job_id
            or import_job.get("project_id") != project_id
            or import_job.get("template_id") != template.get("_id")
            or import_job.get("status") != "CONFIRMED"
        ):
            raise AutomationOperationError("RESUME_IMPORT_SCOPE_MISMATCH")
        resumed_requirement_ids = {
            str(value)
            for value in [
                *(resume_requirement_ids or []),
                *(import_job.get("created_requirement_ids") or []),
            ]
            if value
        }
        if not resumed_requirement_ids:
            raise AutomationOperationError("RESUME_IMPORT_REQUIREMENTS_MISSING")
        await update_resumed_requirement_drafts(
            project_id,
            sorted(resumed_requirement_ids),
            matches,
            config,
            validate_source_access,
        )
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
                        "reason": f"Tài liệu {document_id} xác nhận cùng nội dung Requirement; chỉ bổ sung dấu vết nguồn",
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
                        "reason": (
                            f"Tài liệu {document_id} được đối chiếu với một Requirement hiện có "
                            "theo mã định danh ổn định; tạo phiên bản "
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
                        "reason": (
                            f"Tài liệu {document_id} tạo Requirement nháp riêng vì ứng viên "
                            "không trùng với Requirement hiện có; ứng viên mơ hồ khác vẫn chờ làm rõ"
                        ),
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
    clarification_blocked_version_ids = set()
    clarification_ids = set()
    clarification_plans = []
    unmapped_blueprint_clarifications = []
    persisted_blueprint_clarifications = []
    for requirement_id in sorted(linked_requirement_ids):
        requirement = await require_operation("GET", f"/yeu-cau/{requirement_id}", config)
        if requirement.get("project_id") != project_id or not requirement.get("current_version_id"):
            raise RuntimeError("REQUIREMENT_READBACK_INVALID")
        current = requirement.get("current_version") or await require_operation(
            "GET", f"/phien-ban-yeu-cau/{requirement['current_version_id']}", config
        )
        if current.get("status") == "DRAFT":
            await authorized_source_operation(
                "POST",
                f"/phien-ban-yeu-cau/{current['_id']}/phieu-lam-ro/tao-tu-ra-soat",
            )
        blueprint_clarifications, unmapped_clarifications = (
            await persist_blueprint_clarifications(
                current,
                unresolved_blueprint_clarifications(
                    blueprint.get("clarifications", [])
                ),
                evidence_by_ref,
                source_documents,
                config,
                blueprint.get("obligations", []),
                before_write=validate_source_access,
            )
        )
        unmapped_blueprint_clarifications.extend(unmapped_clarifications)
        persisted_blueprint_clarifications.extend(blueprint_clarifications)
        clarification_ids.update(
            item["_id"] for item in blueprint_clarifications if item.get("_id")
        )
        open_clarifications = await resolve_answered_clarifications(current, config)
        if open_clarifications:
            blueprint_by_identity = {
                blueprint_clarification_identity(item): item
                for item in blueprint_clarifications
            }
            enriched_clarifications = []
            for item in open_clarifications:
                blueprint_item = blueprint_by_identity.get(
                    blueprint_clarification_identity(item), {}
                )
                enriched_clarifications.append(
                    {
                        **item,
                        **{
                            key: blueprint_item[key]
                            for key in ("unlocks_obligation_keys", "unlocks_source_quotes")
                            if key in blueprint_item
                        },
                    }
                )
            open_clarifications = enriched_clarifications
            clarification_plans.extend(
                await plan_clarification_priority(current, open_clarifications, config)
            )
            clarification_ids.update(
                item["_id"] for item in open_clarifications if item.get("_id")
            )
            blocking_clarifications = blocking_blueprint_clarifications(
                open_clarifications, blueprint_clarifications
            )
            if blocking_clarifications:
                clarification_blocked_version_ids.add(current["_id"])
                unresolved.append(
                    {
                        "requirement_id": requirement_id,
                        "requirement_version_id": current["_id"],
                        "reason": "REQUIREMENT_CLARIFICATION_REQUIRED",
                        "clarification_ids": [
                            item["_id"]
                            for item in blocking_clarifications
                            if item.get("_id")
                        ],
                    }
                )
                requirements.append({"requirement": requirement, "version": current})
                continue
        if current.get("status") != "BASELINED":
            try:
                current = await publish_grounded_requirement(
                    project_id,
                    requirement,
                    current,
                    config,
                    before_write=validate_source_access,
                )
                requirement["current_version"] = current
                requirement["current_version_id"] = current["_id"]
            except AutomationOperationError as error:
                unresolved.append({
                    "requirement_id": requirement["_id"],
                    "requirement_version_id": current["_id"],
                    "reason": error.reason_code,
                })
            except (KeyError, RuntimeError) as error:
                unresolved.append({
                    "requirement_id": requirement["_id"],
                    "requirement_version_id": current["_id"],
                    "reason": str(error) or "REQUIREMENT_PUBLICATION_FAILED",
                })
        requirements.append({"requirement": requirement, "version": current})

    unresolved.extend(
        {
            "reason": "TESTABILITY_BLUEPRINT_CLARIFICATION_NOT_MAPPED_TO_REQUIREMENT",
            "clarification_code": item.get("code"),
            "question": item.get("question"),
            "evidence_refs": item.get("evidence_refs", []),
            "source_quote": item.get("source_quote"),
        }
        for item in unmapped_blueprint_clarifications_after_persistence(
            unmapped_blueprint_clarifications,
            persisted_blueprint_clarifications,
        )
    )

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
        if parsed_change_result and parsed_change_result.get("status") == "automation_waiting_for_input":
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
    approved_cases = []
    approved_case_versions = []
    skipped_duplicates = 0
    generation_warnings = []
    unapplied_categories = []
    baselined_version_ids = {
        item["version"]["_id"]
        for item in requirements
        if item["version"].get("status") == "BASELINED"
    }
    mapped_blueprint_obligation_keys, obligations_by_version = (
        map_blueprint_obligations_to_requirements(
            requirements,
            blueprint.get("obligations", []),
            evidence_by_ref,
            source_documents,
        )
    )
    blueprint_artifact_coverage = {
        str(item.get("key")): {
            "obligation_key": str(item.get("key")),
            "requirement_version_ids": [],
            "test_case_ids": [],
            "test_case_version_ids": [],
        }
        for item in blueprint.get("obligations", [])
        if item.get("key")
    }
    for requirement_version_id, (version_obligations, _) in obligations_by_version.items():
        for obligation in version_obligations:
            key = str(obligation.get("key") or "")
            entry = blueprint_artifact_coverage.get(key)
            if entry and requirement_version_id:
                entry["requirement_version_ids"].append(str(requirement_version_id))
    qa_test_design_handoff_version_ids = qa_test_design_handoff_versions(
        requirements,
        permissions,
        clarification_blocked_version_ids,
        obligations_by_version,
    )
    versions_by_id = {
        str(item["version"].get("_id")): item["version"]
        for item in requirements
        if item.get("version", {}).get("_id")
    }
    qa_test_design_handoff_evidence = []
    for version_id in qa_test_design_handoff_version_ids:
        version = versions_by_id.get(version_id)
        if not version:
            continue
        source_text = requirement_version_source_text(version)
        if not source_text.strip():
            continue
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
    reused_test_case_coverage = {}
    existing_test_case_version_cache = {}
    for item in requirements:
        version = item["version"]
        if version.get("_id") in clarification_blocked_version_ids:
            continue
        if version.get("status") != "BASELINED" or "ai.generate_testcase" not in permissions:
            continue
        criterion_ids = version.get("acceptance_criterion_ids") or [
            criterion.get("_id") for criterion in version.get("acceptance_criteria", [])
            if criterion.get("_id")
        ]
        version_obligations, unlinked_obligations = obligations_by_version.get(
            str(version.get("_id") or ""), ([], [])
        )
        if not criterion_ids and not version_obligations:
            unresolved.append({
                "requirement_version_id": version.get("_id"),
                "reason": "NO_TESTABLE_ACCEPTANCE_CRITERIA_OR_BLUEPRINT_OBLIGATION",
            })
            continue
        generation_request = {
            "categories": [],
            "max_cases": max(len(criterion_ids), len(version_obligations), 1),
            "preview_only": True,
        }
        if unlinked_obligations:
            unresolved.append(
                {
                    "requirement_version_id": version["_id"],
                    "reason": "BLUEPRINT_OBLIGATIONS_NOT_SUPPORTED_BY_REQUIREMENT_VERSION",
                    "obligation_keys": [item.get("key") for item in unlinked_obligations],
                }
            )
        generation_request["instruction"] = requirement_test_generation_instruction(
            version_obligations
        )
        version_obligation_keys = {
            str(item.get("key")) for item in version_obligations if item.get("key")
        }
        version_reused_coverage = await existing_requirement_obligation_coverage(
            requirement["_id"],
            project_id,
            version["_id"],
            version_obligations,
            config,
        )
        pending_ai_drafts = await list_resumable_ai_test_case_drafts(
            project_id, version["_id"], config
        )
        compatible_pending_drafts = []
        for pending_draft in pending_ai_drafts:
            if resumable_draft_matches_blueprint_scope(
                pending_draft,
                version["_id"],
                criterion_ids,
                version_obligations,
            ):
                compatible_pending_drafts.append(pending_draft)
                continue
            unresolved.append(
                {
                    "requirement_version_id": version["_id"],
                    "test_case_draft_id": pending_draft["_id"],
                    "reason": "RESUMABLE_TEST_CASE_DRAFT_OUTSIDE_COMPILED_BLUEPRINT_SCOPE",
                    "coverage_obligation_keys": pending_draft.get(
                        "coverage_obligations", []
                    ),
                }
            )
            generation_warnings.append(
                f"RESUMABLE_TEST_CASE_DRAFT_NOT_PUBLISHED:{pending_draft['_id']}"
            )
        created_drafts.extend(compatible_pending_drafts)
        pending_criterion_ids = {
            str(criterion_id)
            for draft in compatible_pending_drafts
            for criterion_id in (draft.get("acceptance_criterion_ids") or [])
        }
        pending_obligation_keys = {
            str(key)
            for draft in compatible_pending_drafts
            for key in (draft.get("coverage_obligations") or [])
        }
        try:
            preview = await generate_grounded_test_case_preview(
                version["_id"],
                config,
                generation_request,
                version_obligations,
                before_request=validate_source_access,
            )
        except AutomationOperationError as error:
            if error.reason_code not in {
                "GENERATION_EVIDENCE_INSUFFICIENT",
                "AI_UNGROUNDED_OUTPUT",
            }:
                raise
            unresolved.append(
                {
                    "requirement_version_id": version["_id"],
                    "reason": "TEST_CASE_GENERATION_NOT_GROUNDED",
                    "generation_reason_code": error.reason_code,
                    "acceptance_criterion_ids": criterion_ids,
                    "obligation_keys": [
                        item.get("key") for item in version_obligations if item.get("key")
                    ],
                }
            )
            generation_warnings.append(
                f"TEST_CASE_GENERATION_NOT_GROUNDED:{version['_id']}"
            )
            continue
        items = preview.get("items") or []
        generation_warnings.extend(preview.get("warnings") or [])
        unapplied_categories.extend(preview.get("unapplied_categories") or [])
        novel = []
        for generated in items:
            draft = generated.get("draft") or {}
            similar = generated.get("similar_cases") or []
            newly_covered = set(generated.get("new_criterion_ids") or [])
            draft_criteria = set(draft.get("acceptance_criterion_ids") or [])
            generated_obligation_keys = set(
                generated.get("coverage_obligations")
                or draft.get("coverage_obligations")
                or []
            )
            invalid_obligation_mapping = bool(
                version_obligation_keys
                and (
                    not generated_obligation_keys
                    or not generated_obligation_keys <= version_obligation_keys
                    or not generated_obligation_evidence_matches(
                        generated_obligation_keys,
                        draft.get("obligation_evidence") or [],
                        version_obligations,
                    )
                )
            )
            if invalid_obligation_mapping:
                generation_warnings.append("BLUEPRINT_OBLIGATION_MAPPING_INVALID")
                skipped_duplicates += 1
            elif (
                generated_obligation_keys
                and generated_obligation_keys
                <= (set(version_reused_coverage) | pending_obligation_keys)
            ):
                skipped_duplicates += 1
            elif similar or not (
                newly_covered & draft_criteria
                or generated_obligation_keys & version_obligation_keys
            ):
                if similar and generated_obligation_keys & version_obligation_keys:
                    resolved = await resolve_existing_obligation_coverage(
                        version["_id"],
                        project_id,
                        version_obligations,
                        generated_obligation_keys,
                        similar,
                        config,
                        existing_test_case_version_cache,
                    )
                    for key, matches in resolved.items():
                        version_reused_coverage.setdefault(key, []).extend(matches)
                skipped_duplicates += 1
            elif draft:
                novel.append(draft)
        coverage = preview.get("criterion_coverage") or {}
        required_criteria = set(coverage.get("criterion_ids") or [])
        already_covered = (
            set(coverage.get("linked_criterion_ids") or []) | pending_criterion_ids
        )
        newly_covered = {
            criterion_id
            for candidate in novel
            for criterion_id in candidate.get("acceptance_criterion_ids", [])
        }
        missing_criteria = required_criteria - already_covered - newly_covered
        missing_obligation_items = uncovered_blueprint_obligations(
            version_obligations,
            novel,
            version_reused_coverage,
            pending_obligation_keys,
        )
        if missing_criteria or missing_obligation_items:
            focused_request = focused_requirement_generation_request(
                generation_request, missing_criteria, missing_obligation_items
            )
            try:
                focused_preview = await generate_grounded_test_case_preview(
                    version["_id"],
                    config,
                    focused_request,
                    missing_obligation_items,
                    before_request=validate_source_access,
                )
            except AutomationOperationError as error:
                if error.reason_code not in {
                    "GENERATION_EVIDENCE_INSUFFICIENT",
                    "AI_UNGROUNDED_OUTPUT",
                }:
                    raise
                focused_preview = {"items": [], "warnings": []}
                generation_warnings.append(
                    f"FOCUSED_TEST_CASE_GENERATION_NOT_GROUNDED:{version['_id']}"
                )
            generation_warnings.extend(focused_preview.get("warnings") or [])
            unapplied_categories.extend(focused_preview.get("unapplied_categories") or [])
            for generated in focused_preview.get("items") or []:
                draft = generated.get("draft") or {}
                similar = generated.get("similar_cases") or []
                newly_covered = set(generated.get("new_criterion_ids") or [])
                draft_criteria = set(draft.get("acceptance_criterion_ids") or [])
                generated_obligation_keys = set(
                    generated.get("coverage_obligations")
                    or draft.get("coverage_obligations")
                    or []
                )
                if (
                    version_obligation_keys
                    and (
                        not generated_obligation_keys
                        or not generated_obligation_keys <= version_obligation_keys
                        or not generated_obligation_evidence_matches(
                            generated_obligation_keys,
                            draft.get("obligation_evidence") or [],
                            version_obligations,
                        )
                    )
                ):
                    generation_warnings.append("BLUEPRINT_OBLIGATION_MAPPING_INVALID")
                    skipped_duplicates += 1
                    continue
                if (
                    generated_obligation_keys
                    and generated_obligation_keys
                    <= (set(version_reused_coverage) | pending_obligation_keys)
                ):
                    skipped_duplicates += 1
                    continue
                if similar or not (
                    newly_covered & draft_criteria
                    or generated_obligation_keys & version_obligation_keys
                ):
                    if similar and generated_obligation_keys & version_obligation_keys:
                        resolved = await resolve_existing_obligation_coverage(
                            version["_id"],
                            project_id,
                            missing_obligation_items,
                            generated_obligation_keys,
                            similar,
                            config,
                            existing_test_case_version_cache,
                        )
                        for key, matches in resolved.items():
                            version_reused_coverage.setdefault(key, []).extend(matches)
                    skipped_duplicates += 1
                    continue
                signature = normalized_text(draft.get("title"))
                if not draft or not signature or signature in {normalized_text(item.get("title")) for item in novel}:
                    continue
                novel.append(draft)
                newly_covered.update(draft.get("acceptance_criterion_ids", []))
            missing_criteria = required_criteria - already_covered - newly_covered
            missing_obligation_items = uncovered_blueprint_obligations(
                version_obligations,
                novel,
                version_reused_coverage,
                pending_obligation_keys,
            )
        if missing_criteria:
            unresolved.append(
                {
                    "requirement_version_id": version["_id"],
                    "reason": "ACCEPTANCE_CRITERIA_NOT_COVERED",
                    "missing_acceptance_criterion_ids": sorted(missing_criteria),
                }
            )
        if missing_obligation_items:
            unresolved.append(
                {
                    "requirement_version_id": version["_id"],
                    "reason": "TESTABILITY_BLUEPRINT_OBLIGATIONS_NOT_COVERED",
                    "obligation_keys": [item.get("key") for item in missing_obligation_items],
                }
            )
        for key, matches in version_reused_coverage.items():
            unique = {
                (item["test_case_id"], item["test_case_version_id"]): item
                for item in matches
            }
            reused_test_case_coverage[key] = list(unique.values())
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
        if not novel:
            continue
        created = await authorized_source_operation(
            "POST", f"{project_path}/ban-nhap-ca-kiem-thu/lo", novel
        )
        created_items = created if isinstance(created, list) else created.get("items", [])
        if len(created_items) != len(novel):
            raise RuntimeError("TEST_CASE_BATCH_READBACK_INVALID")
        created_drafts.extend(created_items)

    all_blueprint_obligation_keys = {
        str(item.get("key"))
        for item in blueprint.get("obligations", [])
        if item.get("key")
    }
    unmapped_blueprint_obligation_keys = sorted(
        all_blueprint_obligation_keys - mapped_blueprint_obligation_keys
    )
    has_unresolved_requirement_match = any(
        item.get("reason") == "REQUIREMENT_MATCH_NEEDS_RECONCILIATION"
        for item in unresolved
    )
    if unmapped_blueprint_obligation_keys and has_unresolved_requirement_match:
        for item in unresolved:
            if item.get("reason") == "REQUIREMENT_MATCH_NEEDS_RECONCILIATION":
                item["unmapped_obligation_keys"] = unmapped_blueprint_obligation_keys
    elif unmapped_blueprint_obligation_keys:
        unresolved.append({
            "reason": "BLUEPRINT_OBLIGATIONS_REQUIREMENT_MAPPING_MISSING",
            "obligation_keys": unmapped_blueprint_obligation_keys,
        })

    for draft in created_drafts:
        if draft.get("project_id") != project_id or not draft.get("_id"):
            raise RuntimeError("TEST_CASE_READBACK_INVALID")
        lint = await authorized_source_operation(
            "POST", f"/ca-kiem-thu/{draft['_id']}/kiem-tra"
        )
        if not lint.get("valid"):
            unresolved.append({"test_case_draft_id": draft["_id"], "reason": "TEST_CASE_QUALITY_FAILED"})
            continue
        if not set(draft.get("requirement_version_ids", [])) <= baselined_version_ids:
            unresolved.append({"test_case_draft_id": draft["_id"], "reason": "REQUIREMENT_NOT_BASELINED"})
            continue
        try:
            case, version, publication_status = await publish_grounded_test_case(
                project_id,
                draft,
                config,
                before_write=validate_source_access,
            )
            approved_cases.append(case)
            approved_case_versions.append(version)
            for obligation_key in (
                draft.get("coverage_obligations")
                or version.get("coverage_obligations")
                or []
            ):
                entry = blueprint_artifact_coverage.get(str(obligation_key))
                if entry:
                    entry["test_case_ids"].append(str(case["_id"]))
                    entry["test_case_version_ids"].append(str(version["_id"]))
            if publication_status != "SUCCESS":
                generation_warnings.append(
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

    for obligation_key, matches in reused_test_case_coverage.items():
        entry = blueprint_artifact_coverage.get(str(obligation_key))
        if not entry:
            continue
        for match in matches:
            if match.get("test_case_id"):
                entry["test_case_ids"].append(str(match["test_case_id"]))
            if match.get("test_case_version_id"):
                entry["test_case_version_ids"].append(str(match["test_case_version_id"]))
    for entry in blueprint_artifact_coverage.values():
        for field in (
            "requirement_version_ids",
            "test_case_ids",
            "test_case_version_ids",
        ):
            entry[field] = list(dict.fromkeys(entry[field]))

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
    for case, case_version in zip(approved_cases, approved_case_versions, strict=True):
        case_readback = await require_operation("GET", f"/ca-kiem-thu/{case['_id']}", config)
        if case_readback.get("_id") != case["_id"] or case_readback.get("project_id") != project_id:
            raise RuntimeError("TEST_CASE_READBACK_INVALID")
        checks.append({"artifact_id": case["_id"], "artifact_type": "test_case"})
        version_readback = await require_operation(
            "GET", f"/phien-ban-ca-kiem-thu/{case_version['_id']}", config
        )
        if not verified_test_case_publication_readback(
            project_id, case, case_version, case_readback, version_readback
        ):
            raise RuntimeError("TEST_CASE_VERSION_READBACK_INVALID")
        checks.append(
            {"artifact_id": case_version["_id"], "artifact_type": "test_case_version"}
        )
    checked_artifacts = {
        (item["artifact_type"], str(item["artifact_id"])) for item in checks
    }
    for coverage in blueprint_artifact_coverage.values():
        for artifact_type, field, route in (
            ("test_case", "test_case_ids", "/ca-kiem-thu/{}"),
            (
                "test_case_version",
                "test_case_version_ids",
                "/phien-ban-ca-kiem-thu/{}",
            ),
        ):
            for artifact_id in coverage[field]:
                key = (artifact_type, str(artifact_id))
                if key in checked_artifacts:
                    continue
                readback = await require_operation("GET", route.format(artifact_id), config)
                if readback.get("_id") != artifact_id or readback.get("project_id") != project_id:
                    raise RuntimeError("BLUEPRINT_COVERAGE_ARTIFACT_READBACK_INVALID")
                if artifact_type == "test_case_version" and not readback.get("test_case_id"):
                    raise RuntimeError("BLUEPRINT_COVERAGE_VERSION_LINK_INVALID")
                checks.append({"artifact_id": artifact_id, "artifact_type": artifact_type})
                checked_artifacts.add(key)

    verified_source_facts, verified_source_evidence = verified_requirement_source_citations(
        template_requirements, source_documents, source_document_ids
    )
    blueprint_source_facts, blueprint_source_evidence = blueprint_source_lineage(
        blueprint, verified_facts
    )
    fact_keys = {
        (
            str(item.get("artifact_type") or ""),
            str(item.get("artifact_id") or ""),
            str(item.get("artifact_version_id") or ""),
            item.get("source_start"),
            item.get("source_end"),
            str(item.get("quote") or ""),
        )
        for item in verified_source_facts
    }
    for item in blueprint_source_facts:
        key = (
            str(item.get("artifact_type") or ""),
            str(item.get("artifact_id") or ""),
            str(item.get("artifact_version_id") or ""),
            item.get("source_start"),
            item.get("source_end"),
            str(item.get("quote") or ""),
        )
        if key not in fact_keys:
            verified_source_facts.append(item)
            fact_keys.add(key)
    verified_source_evidence.extend(blueprint_source_evidence)
    workflow_status, verification_status, reason_code = (
        classify_requirement_ingestion_outcome(unresolved)
    )
    result = {
        "status": workflow_status,
        **({"reason_code": reason_code} if reason_code else {}),
        "template_id": template["_id"],
        "testability_blueprint": blueprint,
        "requirement_import_job_id": import_job["_id"],
        "requirement_ids": [item["requirement"]["_id"] for item in requirements],
        "requirement_version_ids": [item["version"]["_id"] for item in requirements],
        "qa_test_design_handoff_version_ids": qa_test_design_handoff_version_ids,
        "qa_test_design_handoff_evidence": qa_test_design_handoff_evidence,
        "test_case_draft_ids": [item["_id"] for item in created_drafts],
        "approved_test_case_ids": [item["_id"] for item in approved_cases],
        "blueprint_artifact_coverage": [
            item for item in blueprint_artifact_coverage.values()
        ],
        "reused_test_case_coverage": reused_test_case_coverage,
        "updated_requirement_version_ids": sorted(updated_requirement_versions),
        "clarification_ids": sorted(clarification_ids),
        "clarification_plan": clarification_plans,
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

