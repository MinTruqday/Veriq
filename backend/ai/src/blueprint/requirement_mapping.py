import hashlib
import json

from src.services.automation_provenance import source_quote_spans
from src.blueprint.source_evidence import requirement_version_source_text


def obligations_supported_by_requirement_version(
    version, obligations, evidence_by_ref, source_documents=None
):
    source_documents = source_documents or {}
    version_sources = {}
    for item in version.get("source_refs", []):
        source_id = str(item.get("requirement_document_id") or "")
        if source_id:
            version_sources.setdefault(source_id, []).append(item)
    version_texts = [requirement_version_source_text(version)]
    supported = []
    unsupported = []
    for obligation in obligations:
        source = evidence_record_for_reference(
            evidence_by_ref, obligation.get("source_ref")
        )
        source_id = str(source.get("artifact_id") or obligation.get("source_ref") or "")
        quote = str(obligation.get("source_quote") or "").strip()
        if source_id == str(version.get("_id") or ""):
            is_supported = bool(
                quote and any(source_quote_spans(text, quote) for text in version_texts)
            )
            if is_supported:
                supported.append(obligation)
            else:
                unsupported.append(obligation)
            continue

        source_refs = version_sources.get(source_id)
        if not source_refs:
            continue
        document = source_documents.get(source_id) or {}
        normalized_content = document.get("normalized_content")
        if isinstance(normalized_content, str):
            source_text = normalized_content
        elif isinstance(normalized_content, (dict, list)):
            source_text = json.dumps(
                normalized_content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        else:
            source_text = str(source.get("text") or "")
        current_hash = str(document.get("content_hash") or "")
        current_version = str(document.get("source_version") or "")
        linked_to_requirement = False
        supported_by_source = False
        for source_ref in source_refs:
            expected_hash = str(source_ref.get("content_hash") or "")
            expected_version = str(source_ref.get("source_version") or "")
            document_revision_matches = bool(
                (not expected_hash or (current_hash and current_hash == expected_hash))
                and (
                    not expected_version
                    or (current_version and current_version == expected_version)
                )
            )
            cited_start = source_ref.get("source_start")
            cited_end = source_ref.get("source_end")
            stored_quote = str(source_ref.get("source_quote") or "").strip()
            span_quote = ""
            if (
                isinstance(cited_start, int)
                and not isinstance(cited_start, bool)
                and isinstance(cited_end, int)
                and not isinstance(cited_end, bool)
                and 0 <= cited_start < cited_end <= len(source_text)
            ):
                span_quote = source_text[cited_start:cited_end]
            cited_quote = stored_quote or span_quote
            quote_is_linked = bool(
                quote and cited_quote and source_quote_spans(cited_quote, quote)
            )
            claim_spans = source_quote_spans(source_text, quote) if quote else []
            if not quote_is_linked and span_quote and claim_spans:
                quote_is_linked = any(
                    (claim_start <= cited_start and cited_end <= claim_end)
                    or (cited_start <= claim_start and claim_end <= cited_end)
                    for claim_start, claim_end in claim_spans
                )
            if not quote_is_linked:
                continue
            linked_to_requirement = True
            precise_span_matches = bool(
                span_quote
                and (not stored_quote or stored_quote == span_quote)
                and (
                    not source_ref.get("source_text_hash")
                    or hashlib.sha256(span_quote.encode("utf-8")).hexdigest()
                    == source_ref.get("source_text_hash")
                )
            )
            if (
                document_revision_matches
                and source_id == str(document.get("_id") or source_id)
                and precise_span_matches
            ):
                supported_by_source = True
                break
        if supported_by_source:
            supported.append(obligation)
        elif linked_to_requirement:
            unsupported.append(obligation)
    return supported, unsupported


def evidence_record_for_reference(evidence_by_ref, reference):
    reference = str(reference or "")
    raw_sources = evidence_by_ref.get(reference)
    candidates = raw_sources if isinstance(raw_sources, list) else [raw_sources]
    candidates = [item for item in candidates if isinstance(item, dict)]
    matched = [
        item
        for item in candidates
        if str(item.get("artifact_version_id") or "") == reference
        or str(item.get("artifact_id") or "") == reference
    ]
    if len(matched) == 1:
        return matched[0]
    if not matched and len(candidates) == 1:
        return candidates[0]
    return {}


def map_blueprint_obligations_to_requirements(
    requirements, obligations, evidence_by_ref, source_documents=None
):
    """Map grounded obligations independently of workflow readiness.

    A clarification may block Test Case generation for a Requirement version,
    but it must not make already-linked, source-backed obligations appear
    unmapped in the project-level blueprint.
    """
    mapped_keys = set()
    obligations_by_version = {}
    for item in requirements:
        version = item.get("version") or item
        version_id = str(version.get("_id") or "")
        supported, unsupported = obligations_supported_by_requirement_version(
            version, obligations, evidence_by_ref, source_documents
        )
        obligations_by_version[version_id] = (supported, unsupported)
        mapped_keys.update(
            str(obligation.get("key")) for obligation in supported if obligation.get("key")
        )
    return mapped_keys, obligations_by_version
