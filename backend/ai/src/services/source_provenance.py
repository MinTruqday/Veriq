import hashlib
import math
from collections.abc import Iterable, Mapping

from src.core.text_matching import source_quote_spans


def is_source_fact_evidence(item) -> bool:
    if not isinstance(item, Mapping):
        return False
    artifact_type = str(item.get("artifact_type") or "").strip().casefold()
    authority = str(item.get("authority") or "").strip().casefold()
    source = str(item.get("source") or "").strip().casefold()
    return (
        artifact_type not in {"ai_run_clarification", "longtermmemory"}
        and source not in {"memory", "agent_memory"}
        and authority not in {"user_clarification", "user_answer"}
    )


def source_fact_identity(fact: dict) -> tuple:
    """Identify the same cited fact across parent/version ID aliases.

    Some authoritative workflow tools return a version ID as ``artifact_id``
    while the event evidence uses the stable parent ID. The version, exact
    span, quote, and type still identify the same fact. When verified event
    evidence contains both aliases, prefer its stable parent artifact ID.
    """
    return (
        str(fact.get("artifact_type") or ""),
        str(fact.get("artifact_version_id") or ""),
        fact.get("source_start"),
        fact.get("source_end"),
        str(fact.get("quote") or ""),
    )


def source_location_metadata(item: dict) -> dict:
    """Copy only well-formed, server-returned source location metadata."""
    chunk_index = item.get("chunk_index")
    if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index < 0:
        chunk_index = None
    page_numbers = item.get("page_numbers")
    if not isinstance(page_numbers, list):
        page_numbers = []
    page_numbers = list(dict.fromkeys(
        page for page in page_numbers
        if isinstance(page, int) and not isinstance(page, bool) and page >= 1
    ))
    source_spans = item.get("source_spans")
    if not isinstance(source_spans, list):
        source_spans = []
    source_spans = [dict(span) for span in source_spans if isinstance(span, dict)]
    return {
        "source_chunk_id": (
            item.get("chunk_id").strip()
            if isinstance(item.get("chunk_id"), str) and item.get("chunk_id").strip()
            else None
        ),
        "source_chunk_index": chunk_index,
        "source_chunk_type": (
            item.get("chunk_type") if isinstance(item.get("chunk_type"), str) else None
        ),
        "source_page_numbers": page_numbers,
        "source_spans": source_spans,
        "source_hash": (
            item.get("source_hash") if isinstance(item.get("source_hash"), str) else None
        ),
    }


def verified_source_offset_basis(item: dict | None) -> str:
    if not isinstance(item, dict):
        return "UNKNOWN"
    if item.get("source_verification") == "VERIFIED_REQUIREMENT_SOURCE_CITATION":
        return "SOURCE_CITATION"
    if item.get("source_offset_basis") == "CANONICAL_TEXT":
        return "CANONICAL_TEXT"
    location = source_location_metadata(item)
    if (
        location["source_chunk_id"]
        or location["source_chunk_index"] is not None
        or location["source_page_numbers"]
        or location["source_spans"]
    ):
        return "RETRIEVED_CHUNK"
    return "UNKNOWN"


def canonicalize_source_facts(facts: Iterable[dict], evidence: Iterable[dict]) -> list[dict]:
    """Resolve verified parent/version aliases and deduplicate cited facts."""
    parent_ids_by_version = {}
    for item in evidence:
        artifact_id = str(item.get("artifact_id") or "")
        version_id = str(item.get("artifact_version_id") or "")
        if not artifact_id or not version_id or artifact_id == version_id:
            continue
        key = (str(item.get("artifact_type") or ""), version_id)
        parent_ids_by_version.setdefault(key, artifact_id)
    canonical = []
    seen = set()
    for raw_fact in facts:
        fact = dict(raw_fact)
        if not is_source_fact_evidence(fact):
            continue
        parent_id = parent_ids_by_version.get(
            (
                str(fact.get("artifact_type") or ""),
                str(fact.get("artifact_version_id") or ""),
            )
        )
        if parent_id:
            fact["artifact_id"] = parent_id
        identity = source_fact_identity(fact)
        if identity in seen:
            continue
        seen.add(identity)
        canonical.append(fact)
    return canonical


def verified_source_span(fact: dict, evidence: Iterable[dict]) -> dict | None:
    """Return a source fact only when its revision and exact quote position are verifiable."""
    evidence = list(evidence)
    artifact_id = str(fact.get("artifact_id") or "").strip()
    version_id = str(fact.get("artifact_version_id") or "").strip()
    artifact_type = str(fact.get("artifact_type") or "").strip()
    quote = str(fact.get("quote") or "")
    if not artifact_id or not version_id or not quote:
        return None

    matching_evidence = [
        item
        for item in evidence
        if is_source_fact_evidence(item)
        and str(item.get("artifact_id") or "") == artifact_id
        and str(item.get("artifact_version_id") or "") == version_id
        and (
            not item.get("artifact_type")
            or not artifact_type
            or str(item.get("artifact_type")) == artifact_type
        )
        and str(item.get("text") or "")
    ]
    matching_texts = list(dict.fromkeys(str(item.get("text") or "") for item in matching_evidence))
    if not matching_texts:
        return None

    start = fact.get("source_start")
    end = fact.get("source_end")
    matched_source = None
    if start is not None or end is not None:
        valid_range = (
            isinstance(start, int)
            and not isinstance(start, bool)
            and start >= 0
            and isinstance(end, int)
            and not isinstance(end, bool)
            and end > start
            and end - start == len(quote)
        )
        full_document_match = valid_range and any(
            (start, end) in source_quote_spans(text, quote)
            for text in matching_texts
        )
        if full_document_match:
            matched_source = next(
                item
                for item in matching_evidence
                if str(item.get("text") or "")[start:end] == quote
                and (start, end)
                in source_quote_spans(str(item.get("text") or ""), quote)
            )
        verified_citation_source = next(
            (
                item
                for item in matching_evidence
                if item.get("source_verification") in {
                    "VERIFIED_REQUIREMENT_SOURCE_CITATION",
                }
                and item.get("source_start") == start
                and item.get("source_end") == end
                and str(item.get("text") or "") == quote
                and len(quote) == end - start
            ),
            None,
        ) if valid_range else None
        verified_citation_match = verified_citation_source is not None
        if not matched_source and verified_citation_source:
            matched_source = verified_citation_source
        if not full_document_match and not verified_citation_match:
            return None
    else:
        matches = []
        for item in matching_evidence:
            text = str(item.get("text") or "")
            matches.extend(
                (item, start, end) for start, end in source_quote_spans(text, quote)
            )
        if len(matches) != 1:
            return None
        matched_source, start, end = matches[0]

    relationship_path = []
    for item in matching_evidence:
        path = item.get("relationship_path")
        if not isinstance(path, list) or len(path) > 50:
            continue
        normalized = [str(value).strip() for value in path]
        if any(not value or len(value) > 200 for value in normalized):
            continue
        if normalized:
            relationship_path = normalized
            break
    offset_basis = verified_source_offset_basis(matched_source)
    return {
        **fact,
        "relationship_path": relationship_path,
        "source_start": start,
        "source_end": end,
        **source_location_metadata(matched_source or {}),
        "source_offset_basis": offset_basis,
    }


def carry_source_fact_lineage(
    input_refs: Iterable[str], output_refs: Iterable[str], lineage: dict
) -> list[str]:
    """Propagate source-fact ancestry through a verified transformation receipt step."""
    source_fact_ids = list(
        dict.fromkeys(
            fact_id
            for reference in input_refs
            for fact_id in lineage.get(str(reference), [])
        )
    )
    for reference in output_refs:
        lineage[str(reference)] = list(source_fact_ids)
    return source_fact_ids


def has_provenance_gap(
    rejected_source_fact_count: int,
    unlinked_mutation_count: int,
) -> bool:
    return rejected_source_fact_count > 0 or unlinked_mutation_count > 0


def _verified_facts_by_reference(
    source_facts: Iterable,
    *,
    project_id: str | None = None,
    ai_run_id: str | None = None,
) -> dict[str, list]:
    """Index facts only when their full source identity is present and unambiguous."""
    facts_by_reference: dict[str, list] = {}
    identities_by_reference: dict[str, set[tuple[str, str, str]]] = {}
    for fact in source_facts:
        fact_project_id = str(getattr(fact, "project_id", "") or "")
        fact_run_id = str(getattr(fact, "ai_run_id", "") or "")
        if project_id is not None and fact_project_id != str(project_id):
            continue
        if ai_run_id is not None and fact_run_id != str(ai_run_id):
            continue
        artifact_type = str(getattr(fact, "artifact_type", "") or "")
        artifact_id = str(getattr(fact, "artifact_id", "") or "")
        version_id = str(getattr(fact, "artifact_version_id", "") or "")
        quote = str(getattr(fact, "quote", "") or "")
        quote_sha256 = str(getattr(fact, "quote_sha256", "") or "")
        if (
            not is_source_fact_evidence(
                {
                    "artifact_type": artifact_type,
                    "authority": getattr(fact, "authority", ""),
                }
            )
            or not artifact_type
            or not artifact_id
            or not version_id
            or not quote
            or quote_sha256 != hashlib.sha256(quote.encode("utf-8")).hexdigest()
        ):
            continue
        identity = (artifact_type, artifact_id, version_id)
        for reference in {artifact_id, version_id}:
            identities_by_reference.setdefault(reference, set()).add(identity)
            facts_by_reference.setdefault(reference, []).append(fact)

    return {
        reference: facts
        for reference, facts in facts_by_reference.items()
        if len(identities_by_reference[reference]) == 1
    }
