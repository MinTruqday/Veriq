import json
from collections import OrderedDict

from src.schemas.inference_requests import TestingEvidence
from src.services.automation_provenance import source_quote_spans


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
                and source_quote_spans(str(item.get("text") or ""), fact.quote)
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
            canonical_span_matches = (
                fact.source_offset_basis == "CANONICAL_TEXT"
                and isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
                and 0 <= start < end <= len(authoritative_text)
                and end - start == len(fact.quote)
                and authoritative_text[start:end] == fact.quote
                and (start, end) in source_quote_spans(authoritative_text, fact.quote)
            )
            if not canonical_span_matches:
                positions = [start for start, _ in source_quote_spans(authoritative_text, fact.quote)]
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
            and (start, end) in source_quote_spans(authoritative_text, fact.quote)
        ):
            positions = [start for start, _ in source_quote_spans(authoritative_text, fact.quote)]
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
        matching_sources = [
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
            and source_quote_spans(str(item.get("text") or ""), quote)
        ]
        source_start = fact.source_start
        source_end = fact.source_end
        span_matching_sources = [
            item
            for item in matching_sources
            if isinstance(source_start, int)
            and not isinstance(source_start, bool)
            and source_start >= 0
            and isinstance(source_end, int)
            and not isinstance(source_end, bool)
            and source_end > source_start
            and str(item.get("text") or "")[source_start:source_end] == quote
            and source_end - source_start == len(quote)
        ]
        if fact.source_offset_basis == "CANONICAL_TEXT":
            source = next(
                (
                    item
                    for item in span_matching_sources
                    if item.get("source_offset_basis") == "CANONICAL_TEXT"
                ),
                None,
            )
        else:
            source = next(iter(span_matching_sources), None)
        verified_citation_span = False
        if source is None and fact.source_offset_basis == "SOURCE_CITATION":
            source = next(
                (
                    item
                    for item in matching_sources
                    if item.get("source_verification")
                    == "VERIFIED_REQUIREMENT_SOURCE_CITATION"
                    and isinstance(source_start, int)
                    and not isinstance(source_start, bool)
                    and source_start >= 0
                    and isinstance(source_end, int)
                    and not isinstance(source_end, bool)
                    and source_end > source_start
                    and source_end - source_start == len(quote)
                    and item.get("source_start") == source_start
                    and item.get("source_end") == source_end
                    and str(item.get("text") or "") == quote
                ),
                None,
            )
            verified_citation_span = source is not None
        source_text = str((source or {}).get("text") or "")
        source_span_matches_text = (
            isinstance(source_start, int)
            and not isinstance(source_start, bool)
            and isinstance(source_end, int)
            and not isinstance(source_end, bool)
            and 0 <= source_start < source_end <= len(source_text)
            and source_end - source_start == len(quote)
            and source_text[source_start:source_end] == quote
            and (source_start, source_end) in source_quote_spans(source_text, quote)
        )
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
            or not (source_span_matches_text or verified_citation_span)
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
