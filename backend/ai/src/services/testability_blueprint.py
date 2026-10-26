import hashlib
import json
from collections import OrderedDict

from src.schemas.inference_requests import TestingAutomationRequest, TestingEvidence
from src.services.ai_automation import generate_ai_automation


def verified_document_lineage(path, artifact_id, allowed_document_ids):
    """Keep only a readable document-version chain ending at its cited source."""
    if not isinstance(path, list) or not path or len(path) > 50:
        return []
    normalized = [value.strip() for value in path if isinstance(value, str)]
    if (
        len(normalized) != len(path)
        or any(not value or len(value) > 200 for value in normalized)
        or len(set(normalized)) != len(normalized)
        or normalized[-1] != str(artifact_id)
        or not set(normalized) <= set(allowed_document_ids)
    ):
        return []
    return normalized


def requirement_version_source_segments(version):
    """Return verbatim text fields that belong to one saved Requirement version."""
    segments = []
    title = str(version.get("title") or "").strip()
    if title:
        segments.append(("requirement_title", title))
    content = str(version.get("plain_text_projection") or "").strip()
    if content:
        segments.append(("requirement_content", content))

    for criterion in version.get("acceptance_criteria") or []:
        if not isinstance(criterion, dict):
            continue
        text = str(criterion.get("plain_text") or "").strip()
        if text:
            segments.append(("acceptance_criterion", text))

    for field, fact_kind in (
        ("business_rules", "business_rule"),
        ("actors", "actor"),
        ("dependencies", "dependency"),
    ):
        values = version.get(field) or []
        if isinstance(values, str):
            values = [values]
        for value in values:
            text = str(value or "").strip()
            if text:
                segments.append((fact_kind, text))

    def collect_strings(value):
        if isinstance(value, str):
            normalized = value.strip()
            return [normalized] if normalized else []
        if isinstance(value, dict):
            return [text for child in value.values() for text in collect_strings(child)]
        if isinstance(value, (list, tuple)):
            return [text for child in value for text in collect_strings(child)]
        return []

    for field in ("details", "custom_values"):
        segments.extend(
            ("requirement_detail", text) for text in collect_strings(version.get(field))
        )
    return segments


def requirement_version_source_text(version):
    return "\n".join(text for _, text in requirement_version_source_segments(version))


def facts_bound_to_authorized_evidence(
    source_facts,
    evidence_by_ref,
    allowed_document_ids,
    authorized_lineage_by_artifact,
    source_documents=None,
):
    """Bind facts to authorized quotes and API-verified document version ancestry."""
    verified = []
    allowed_document_ids = set(allowed_document_ids)
    for fact in source_facts:
        reference = str(fact.artifact_version_id or fact.artifact_id)
        raw_sources = evidence_by_ref.get(reference)
        candidates = raw_sources if isinstance(raw_sources, list) else [raw_sources]
        if fact.artifact_id not in allowed_document_ids or not fact.quote:
            continue
        source = next(
            (
                item
                for item in candidates
                if isinstance(item, dict)
                and str(item.get("artifact_id")) == fact.artifact_id
                and (
                    not item.get("artifact_type")
                    or str(item.get("artifact_type")) == fact.artifact_type
                )
                and (
                    not item.get("artifact_version_id")
                    or str(item.get("artifact_version_id")) == reference
                )
                and fact.quote in str(item.get("text") or "")
            ),
            None,
        )
        if not source:
            continue

        authoritative = (source_documents or {}).get(fact.artifact_id) or {}
        normalized_content = authoritative.get("normalized_content")
        has_authoritative_text = isinstance(normalized_content, (str, dict, list))
        if source_documents is not None and not has_authoritative_text:
            continue
        if isinstance(normalized_content, str):
            authoritative_text = normalized_content
        elif isinstance(normalized_content, (dict, list)):
            authoritative_text = json.dumps(
                normalized_content,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        else:
            authoritative_text = str(source.get("text") or "")

        start = fact.source_start
        end = fact.source_end
        if has_authoritative_text:
            positions = []
            cursor = 0
            while True:
                position = authoritative_text.find(fact.quote, cursor)
                if position < 0:
                    break
                positions.append(position)
                cursor = position + 1
            if len(positions) != 1:
                continue
            start = positions[0]
            end = start + len(fact.quote)
        elif not (
            isinstance(start, int)
            and not isinstance(start, bool)
            and 0 <= start
            and isinstance(end, int)
            and not isinstance(end, bool)
            and start < end <= len(authoritative_text)
            and end - start == len(fact.quote)
            and authoritative_text[start:end] == fact.quote
        ):
            positions = []
            cursor = 0
            while True:
                position = authoritative_text.find(fact.quote, cursor)
                if position < 0:
                    break
                positions.append(position)
                cursor = position + 1
            if len(positions) != 1:
                continue
            start = positions[0]
            end = start + len(fact.quote)
        relationship_path = verified_document_lineage(
            authorized_lineage_by_artifact.get(fact.artifact_id),
            fact.artifact_id,
            allowed_document_ids,
        )
        verified.append(
            fact.model_copy(
                update={
                    "relationship_path": relationship_path,
                    "source_start": start,
                    "source_end": end,
                    "source_offset_basis": "CANONICAL_TEXT",
                }
            )
        )
    return verified


def verified_fact_evidence(source_facts, evidence_by_ref, allowed_document_ids):
    grouped = OrderedDict()
    allowed_document_ids = set(allowed_document_ids)

    for fact in source_facts:
        reference = str(fact.artifact_version_id or "")
        quote = str(fact.quote or "").strip()
        raw_sources = evidence_by_ref.get(reference)
        candidates = raw_sources if isinstance(raw_sources, list) else [raw_sources]
        source = next(
            (
                item
                for item in candidates
                if isinstance(item, dict)
                and str(item.get("artifact_id")) == fact.artifact_id
                and (
                    not item.get("artifact_type")
                    or str(item.get("artifact_type")) == fact.artifact_type
                )
                and (
                    not item.get("artifact_version_id")
                    or str(item.get("artifact_version_id")) == reference
                )
                and quote
                and quote in str(item.get("text") or "")
            ),
            None,
        )
        source_text = str((source or {}).get("text") or "")
        source_start = fact.source_start
        source_end = fact.source_end
        if (
            not reference
            or not source
            or fact.artifact_id not in allowed_document_ids
            or not quote
            or source_start is None
            or source_end is None
            or not isinstance(source_start, int)
            or isinstance(source_start, bool)
            or not isinstance(source_end, int)
            or isinstance(source_end, bool)
            or not 0 <= source_start < source_end <= len(source_text)
            or source_end - source_start != len(quote)
            or source_text[source_start:source_end] != quote
        ):
            continue

        item = grouped.setdefault(
            reference,
            {
                "artifact_type": str(source.get("artifact_type") or fact.artifact_type),
                "artifact_id": str(source.get("artifact_id")),
                "artifact_version_id": str(
                    source.get("artifact_version_id") or reference
                ),
                "source_version": source.get("source_version"),
                "authority": str(source.get("authority") or fact.authority),
                "quotes": [],
                "relationship_paths": [],
                "verified_facts": [],
            },
        )
        if quote not in item["quotes"]:
            item["quotes"].append(quote)
        fact_citation = {
            "source_fact_id": getattr(fact, "source_fact_id", None),
            "fact_kind": str(getattr(fact, "fact_kind", None) or "source_evidence"),
            "quote": quote,
            "source_start": source_start,
            "source_end": source_end,
            "source_offset_basis": str(
                getattr(fact, "source_offset_basis", None) or "UNKNOWN"
            ),
        }
        if fact_citation not in item["verified_facts"]:
            item["verified_facts"].append(fact_citation)
        relationship_path = verified_document_lineage(
            source.get("relationship_path"), fact.artifact_id, allowed_document_ids
        )
        if relationship_path and relationship_path not in item["relationship_paths"]:
            item["relationship_paths"].append(relationship_path)

    evidence = []
    for item in grouped.values():
        chunk = []
        chunk_length = 0
        for quote in item["quotes"]:
            if len(quote) > 4000:
                raise ValueError("BLUEPRINT_SOURCE_FACT_TOO_LONG")
            if chunk and chunk_length + len(quote) + 1 > 4000:
                evidence.append(
                    TestingEvidence(
                        artifact_type=item["artifact_type"],
                        artifact_id=item["artifact_id"],
                        artifact_version_id=item["artifact_version_id"],
                        source_version=item["source_version"],
                        authority=item["authority"],
                        relationship_paths=item["relationship_paths"],
                        verified_facts=[
                            fact
                            for fact in item["verified_facts"]
                            if fact["quote"] in chunk
                        ],
                        text="\n".join(chunk),
                    )
                )
                chunk = []
                chunk_length = 0
            chunk.append(quote)
            chunk_length += len(quote) + bool(chunk)
        if chunk:
            evidence.append(
                TestingEvidence(
                    artifact_type=item["artifact_type"],
                    artifact_id=item["artifact_id"],
                    artifact_version_id=item["artifact_version_id"],
                    source_version=item["source_version"],
                    authority=item["authority"],
                    relationship_paths=item["relationship_paths"],
                    verified_facts=[
                        fact
                        for fact in item["verified_facts"]
                        if fact["quote"] in chunk
                    ],
                    text="\n".join(chunk),
                )
            )
    return evidence


async def compile_testability_blueprint(
    project_id, source_facts, evidence_by_ref, allowed_document_ids
):
    try:
        evidence = verified_fact_evidence(source_facts, evidence_by_ref, allowed_document_ids)
    except ValueError as error:
        return {
            "status": "DEGRADED",
            "reason_codes": [str(error)],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": [],
            "warnings": [],
        }
    if not evidence:
        return {
            "status": "DEGRADED",
            "reason_codes": ["NO_VERIFIED_BLUEPRINT_EVIDENCE"],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": [],
            "warnings": [],
        }
    if len(evidence) > 100:
        return {
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_EVIDENCE_LIMIT_EXCEEDED"],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": [],
            "warnings": [],
        }

    request = TestingAutomationRequest(
        capability="testability_blueprint_compilation", project_id=project_id, evidence=evidence
    )
    try:
        result = await generate_ai_automation(request)
    except Exception as error:
        return {
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_MODEL_CALL_FAILED"],
            "obligations": [],
            "clarifications": [],
            "evidence_refs": [
                str(item.artifact_version_id or item.artifact_id) for item in evidence
            ],
            "warnings": [type(error).__name__],
        }
    output = result.model_dump(mode="json")
    if output.get("status") != "SUCCESS" or output.get("degraded_mode"):
        return output

    if not output.get("obligations") and not output.get("clarifications"):
        return {
            **output,
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_HAS_NO_TESTABILITY_OUTCOMES"],
            "warnings": list(
                dict.fromkeys(
                    [
                        *(output.get("warnings") or []),
                        "Không tạo nghĩa vụ kiểm thử hoặc câu hỏi làm rõ từ nguồn đã xác minh",
                    ]
                )
            ),
        }

    source_text_by_ref = {
        str(item.artifact_version_id or item.artifact_id): "\n".join(
            value.text
            for value in evidence
            if str(value.artifact_version_id or value.artifact_id)
            == str(item.artifact_version_id or item.artifact_id)
        )
        for item in evidence
    }
    allowed_refs = set(source_text_by_ref)
    verified_fact_quotes_by_ref = {
        reference: [
            fact.quote
            for item in evidence
            if str(item.artifact_version_id or item.artifact_id) == reference
            for fact in item.verified_facts
        ]
        for reference in source_text_by_ref
    }
    if not set(output.get("evidence_refs", [])) <= allowed_refs:
        return {
            **output,
            "status": "DEGRADED",
            "reason_codes": ["BLUEPRINT_EVIDENCE_REFERENCE_INVALID"],
            "obligations": [],
            "clarifications": [],
        }

    for obligation in output.get("obligations", []):
        reference = str(obligation.get("source_ref") or "")
        quote = str(obligation.get("source_quote") or "").strip()
        if (
            reference not in allowed_refs
            or not quote
            or quote not in source_text_by_ref[reference]
            or not any(
                quote in fact_quote
                for fact_quote in verified_fact_quotes_by_ref.get(reference, [])
            )
        ):
            return {
                **output,
                "status": "DEGRADED",
                "reason_codes": ["BLUEPRINT_OBLIGATION_GROUNDING_INVALID"],
                "obligations": [],
                "clarifications": [],
            }

    for clarification in output.get("clarifications", []):
        references = set(clarification.get("evidence_refs", []))
        quote = str(clarification.get("source_quote") or "").strip()
        reason = str(clarification.get("reason") or "").strip()
        if len(reason) < 2:
            return {
                **output,
                "status": "DEGRADED",
                "reason_codes": ["BLUEPRINT_CLARIFICATION_REASON_MISSING"],
                "obligations": [],
                "clarifications": [],
            }
        if (
            not references
            or not references <= allowed_refs
            or not quote
            or not any(quote in source_text_by_ref[reference] for reference in references)
            or not any(
                quote in fact_quote
                for reference in references
                for fact_quote in verified_fact_quotes_by_ref.get(reference, [])
            )
        ):
            return {
                **output,
                "status": "DEGRADED",
                "reason_codes": ["BLUEPRINT_CLARIFICATION_GROUNDING_INVALID"],
                "obligations": [],
                "clarifications": [],
            }

    return output


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
            is_supported = bool(quote and any(quote in text for text in version_texts))
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
            quote_is_linked = bool(quote and cited_quote and quote in cited_quote)
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
