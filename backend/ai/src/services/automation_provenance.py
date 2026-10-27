import hashlib
import math
import re
from collections.abc import Iterable, Mapping

from src.core.text_matching import source_quote_spans


def is_source_fact_evidence(item) -> bool:
    if not isinstance(item, Mapping):
        return False
    artifact_type = str(item.get("artifact_type") or "").strip().casefold()
    authority = str(item.get("authority") or "").strip().casefold()
    return artifact_type != "automation_clarification" and authority not in {
        "user_clarification",
        "user_answer",
    }


def verified_release_gate_control_evidence(state) -> list[dict]:
    if not isinstance(state, Mapping):
        return []
    run = state.get("run") or {}
    if not isinstance(run, Mapping):
        return []
    constraints = state.get("constraints") or {}
    if (
        state.get("automatic") is not True
        or state.get("source_event_verified") is not True
        or not isinstance(constraints, Mapping)
        or constraints.get("trigger") != "RELEASE_CHANGED"
    ):
        return []
    project_id = str(run.get("project_id") or "")
    event_id = str(run.get("source_event_id") or "")
    if not project_id or not event_id:
        return []
    output = []
    for item in state.get("evidence") or []:
        if not isinstance(item, Mapping):
            continue
        artifact_id = str(item.get("artifact_id") or "")
        revision = item.get("artifact_revision")
        if (
            item.get("artifact_type") == "release"
            and item.get("authority") == "release_gate"
            and str(item.get("project_id") or "") == project_id
            and artifact_id
            and event_id.startswith(f"release-gate:{artifact_id}:")
            and re.fullmatch(
                rf"release-gate:{re.escape(artifact_id)}:(?:test-result|defect):.+:r[1-9][0-9]*",
                event_id,
            )
            and type(revision) is int
            and revision >= 1
        ):
            output.append(item)
    return output


def verified_release_gate_mutation_refs(
    *,
    automatic: bool,
    source_event_verified: bool,
    trigger: str,
    project_id: str,
    source_event_id: str,
    control_evidence: Iterable[dict],
    tool_name: str,
    arguments: Mapping,
    input_refs: Iterable[str],
    output_refs: Iterable[str],
) -> list[str]:
    if (
        tool_name != "process_changed_release"
        or automatic is not True
        or source_event_verified is not True
        or trigger != "RELEASE_CHANGED"
        or not project_id
    ):
        return []
    inputs = {str(value) for value in input_refs if value}
    outputs = {str(value) for value in output_refs if value}
    release_ids = {
        str(item.get("artifact_id") or "")
        for item in control_evidence
        if isinstance(item, Mapping)
        and item.get("artifact_type") == "release"
        and item.get("authority") == "release_gate"
        and str(item.get("project_id") or "") == project_id
        and type(item.get("artifact_revision")) is int
        and item.get("artifact_revision") >= 1
        and str(item.get("artifact_id") or "") in inputs
        and str(item.get("artifact_id") or "") in outputs
    }
    if len(release_ids) != 1:
        return []
    release_id = next(iter(release_ids))
    if not re.fullmatch(
        rf"release-gate:{re.escape(release_id)}:(?:test-result|defect):.+:r[1-9][0-9]*",
        source_event_id,
    ):
        return []
    return [source_event_id]


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
    if item.get("source_verification") == "VERIFIED_BLUEPRINT_SOURCE_FACT":
        if item.get("source_offset_basis") == "CANONICAL_TEXT":
            return "CANONICAL_TEXT"
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
                    "VERIFIED_BLUEPRINT_SOURCE_FACT",
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
    rejected_blueprint_count: int = 0,
    unmapped_blueprint_obligation_count: int = 0,
) -> bool:
    return (
        rejected_source_fact_count > 0
        or unlinked_mutation_count > 0
        or rejected_blueprint_count > 0
        or unmapped_blueprint_obligation_count > 0
    )


def _verified_facts_by_reference(
    source_facts: Iterable,
    *,
    project_id: str | None = None,
    automation_run_id: str | None = None,
) -> dict[str, list]:
    """Index facts only when their full source identity is present and unambiguous."""
    facts_by_reference: dict[str, list] = {}
    identities_by_reference: dict[str, set[tuple[str, str, str]]] = {}
    for fact in source_facts:
        fact_project_id = str(getattr(fact, "project_id", "") or "")
        fact_run_id = str(getattr(fact, "automation_run_id", "") or "")
        if project_id is not None and fact_project_id != str(project_id):
            continue
        if automation_run_id is not None and fact_run_id != str(automation_run_id):
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


def missing_blueprint_artifact_coverage_count(
    blueprint: dict | None, artifact_lineage: Iterable[dict]
) -> int:
    """Count obligations lacking either a Requirement version or frozen Test Case version."""
    if blueprint is None:
        return 0
    covered = {}
    for item in artifact_lineage:
        obligation_key = str(item.get("obligation_key") or "")
        artifact_type = str(item.get("artifact_type") or "")
        if obligation_key:
            covered.setdefault(obligation_key, set()).add(artifact_type)
    missing = 0
    for obligation in blueprint.get("obligations", []):
        key = str(obligation.get("key") or "")
        artifact_types = covered.get(key, set())
        if not key or not {
            "requirement_version",
            "test_case_version",
        }.issubset(artifact_types):
            missing += 1
    return missing


def verified_blueprint_snapshot(
    blueprint: dict,
    source_facts: Iterable,
    *,
    project_id: str | None = None,
    automation_run_id: str | None = None,
) -> dict | None:
    """Keep a blueprint in the receipt only when each claim resolves to a verified source fact."""
    if not isinstance(blueprint, dict):
        return None
    required_fields = {
        "capability",
        "obligations",
        "clarifications",
        "evidence_refs",
        "confidence",
        "warnings",
    }
    if not required_fields.issubset(blueprint):
        return None
    evidence_refs = blueprint.get("evidence_refs")
    obligations = blueprint.get("obligations")
    clarifications = blueprint.get("clarifications")
    confidence = blueprint.get("confidence")
    warnings = blueprint.get("warnings")
    if (
        blueprint.get("capability") != "testability_blueprint_compilation"
        or not isinstance(evidence_refs, list)
        or not evidence_refs
        or any(not isinstance(value, str) or not value.strip() for value in evidence_refs)
        or not isinstance(obligations, list)
        or any(
            not isinstance(item, dict)
            or any(
                not isinstance(item.get(field), str) or not item[field].strip()
                for field in ("key", "source_ref", "source_quote")
            )
            for item in obligations
        )
        or not isinstance(clarifications, list)
        or any(
            not isinstance(item, dict)
            or any(
                not isinstance(item.get(field), str) or not item[field].strip()
                for field in ("code", "source_quote")
            )
            or not isinstance(item.get("evidence_refs"), list)
            or any(
                not isinstance(value, str) or not value.strip()
                for value in item.get("evidence_refs", [])
            )
            or not isinstance(item.get("unlocks_obligation_keys"), list)
            or any(
                not isinstance(value, str) or not value.strip()
                for value in item.get("unlocks_obligation_keys", [])
            )
            for item in clarifications
        )
        or isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
        or not isinstance(warnings, list)
        or any(not isinstance(item, str) for item in warnings)
    ):
        return None
    facts_by_reference = _verified_facts_by_reference(
        source_facts, project_id=project_id, automation_run_id=automation_run_id
    )

    refs = set(evidence_refs)
    if not refs or not refs.issubset(facts_by_reference):
        return None
    obligation_keys = {str(item.get("key") or "") for item in obligations}
    if len(obligation_keys) != len(obligations) or "" in obligation_keys:
        return None
    for item in obligations:
        source_ref = str(item.get("source_ref") or "")
        quote = str(item.get("source_quote") or "")
        if source_ref not in refs or not quote or not any(
            source_quote_spans(str(getattr(fact, "quote", "") or ""), quote)
            for fact in facts_by_reference.get(source_ref, [])
        ):
            return None

    clarification_codes = {str(item.get("code") or "") for item in clarifications}
    if len(clarification_codes) != len(clarifications) or "" in clarification_codes:
        return None
    for item in clarifications:
        evidence_refs = set(item.get("evidence_refs") or [])
        quote = str(item.get("source_quote") or "")
        if (
            not evidence_refs
            or not evidence_refs.issubset(refs)
            or not quote
            or not any(
                source_quote_spans(str(getattr(fact, "quote", "") or ""), quote)
                for ref in evidence_refs
                for fact in facts_by_reference.get(ref, [])
            )
            or not set(item.get("unlocks_obligation_keys") or []).issubset(obligation_keys)
        ):
            return None
    return {
        key: blueprint[key]
        for key in (
            "capability",
            "obligations",
            "clarifications",
            "evidence_refs",
            "confidence",
            "warnings",
        )
    }


def verified_blueprint_from_observations(
    observations: Iterable[dict],
    source_facts: Iterable,
    *,
    project_id: str | None = None,
    automation_run_id: str | None = None,
) -> tuple[dict | None, int]:
    """Persist any compiler blueprint whose claims resolve to verified source facts.

    A compiler can produce a valid, grounded blueprint while the wider import
    remains incomplete (for example, because a separate clarification is
    still open). Keep that verified intermediate result in the receipt without
    treating the overall compiler operation as successful.
    """
    blueprint = None
    rejected_count = 0
    compiler_tools = {
        "process_ingested_requirement_document",
        "process_changed_requirement_version",
    }
    for observation in observations:
        if observation.get("tool_name") not in compiler_tools:
            continue
        result = observation.get("result") or {}
        candidate = result.get("testability_blueprint")
        verified = verified_blueprint_snapshot(
            candidate,
            source_facts,
            project_id=project_id,
            automation_run_id=automation_run_id,
        )
        operation_verified = (
            observation.get("status") == "COMPLETED"
            and (observation.get("verification") or {}).get("status") == "COMPLETED"
        )
        if verified is None and (candidate is not None or operation_verified):
            rejected_count += 1
            continue
        if verified is not None:
            blueprint = verified
    return blueprint, rejected_count


def verified_blueprint_claim_lineage(
    blueprint: dict | None,
    source_facts: Iterable,
    *,
    project_id: str | None = None,
    automation_run_id: str | None = None,
) -> list[dict] | None:
    """Map every accepted blueprint claim to the verified fact quotes that support it."""
    if blueprint is None:
        return []

    facts_by_reference = _verified_facts_by_reference(
        source_facts, project_id=project_id, automation_run_id=automation_run_id
    )
    lineage = []
    claims = [
        ("OBLIGATION", item.get("key"), [item.get("source_ref")], item.get("source_quote"))
        for item in blueprint.get("obligations", [])
    ]
    claims.extend(
        (
            "CLARIFICATION",
            item.get("code"),
            item.get("evidence_refs") or [],
            item.get("source_quote"),
        )
        for item in blueprint.get("clarifications", [])
    )

    for claim_type, claim_key, references, quote in claims:
        quote = str(quote or "")
        reference_set = {str(value) for value in references if value}
        fact_ids = []
        for reference in reference_set:
            for fact in facts_by_reference.get(reference, []):
                artifact_refs = {
                    str(getattr(fact, "artifact_id", "") or ""),
                    str(getattr(fact, "artifact_version_id", "") or ""),
                } - {""}
                fact_quote = str(getattr(fact, "quote", "") or "")
                fact_id = str(getattr(fact, "source_fact_id", "") or "")
                if (
                    reference in artifact_refs
                    and quote
                    and source_quote_spans(fact_quote, quote)
                    and fact_id
                ):
                    fact_ids.append(fact_id)
        if not fact_ids:
            return None
        lineage.append(
            {
                "claim_type": claim_type,
                "claim_key": str(claim_key or ""),
                "source_fact_ids": list(dict.fromkeys(fact_ids)),
                "source_quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            }
        )
    return lineage


def verified_blueprint_artifact_lineage(
    blueprint: dict | None,
    claim_lineage: Iterable[dict],
    observations: Iterable[dict],
    project_id: str,
) -> tuple[list[dict], int]:
    """Keep obligation-to-artifact links only when the tool read them back in this project."""
    if blueprint is None:
        return [], 0

    facts_by_obligation = {
        str(item.get("claim_key") or ""): list(item.get("source_fact_ids") or [])
        for item in claim_lineage
        if item.get("claim_type") == "OBLIGATION"
    }
    known_obligations = {
        str(item.get("key") or "") for item in blueprint.get("obligations", [])
    }
    lineage = []
    rejected_count = 0
    for observation in observations:
        if observation.get("tool_name") not in {
            "process_ingested_requirement_document",
            "process_changed_requirement_version",
        }:
            continue
        result = observation.get("result") or {}
        coverage = result.get("blueprint_artifact_coverage") or []
        if not coverage:
            continue
        observation_verification = observation.get("verification") or {}
        if (
            observation.get("status") != "COMPLETED"
            or observation_verification.get("status") != "COMPLETED"
        ):
            rejected_count += 1
            continue
        verification = result.get("verification") or {}
        if str(verification.get("project_id") or "") != str(project_id):
            rejected_count += 1
            continue
        verified_artifacts = set()
        for check in verification.get("checks") or []:
            if not isinstance(check, dict):
                continue
            artifact_type = str(check.get("artifact_type") or "")
            artifact_id = str(check.get("artifact_id") or "")
            if artifact_type in {
                "requirement_version",
                "test_case",
                "test_case_version",
            } and artifact_id:
                verified_artifacts.add((artifact_type, artifact_id))
        if not isinstance(coverage, list):
            rejected_count += 1
            continue
        for item in coverage:
            if not isinstance(item, dict):
                rejected_count += 1
                continue
            obligation_key = str(item.get("obligation_key") or "")
            source_fact_ids = facts_by_obligation.get(obligation_key, [])
            if obligation_key not in known_obligations or not source_fact_ids:
                rejected_count += 1
                continue
            mappings = []
            for field, artifact_type in (
                ("requirement_version_ids", "requirement_version"),
                ("test_case_ids", "test_case"),
                ("test_case_version_ids", "test_case_version"),
            ):
                identifiers = item.get(field) or []
                if not isinstance(identifiers, list):
                    rejected_count += 1
                    continue
                mappings.extend((artifact_type, str(identifier)) for identifier in identifiers if identifier)
            for artifact_type, artifact_id in dict.fromkeys(mappings):
                if (artifact_type, artifact_id) not in verified_artifacts:
                    rejected_count += 1
                    continue
                lineage.append(
                    {
                        "obligation_key": obligation_key,
                        "source_fact_ids": source_fact_ids,
                        "artifact_type": artifact_type,
                        "artifact_id": artifact_id,
                    }
                )
    unique = {
        (item["obligation_key"], item["artifact_type"], item["artifact_id"]): item
        for item in lineage
    }
    return list(unique.values()), rejected_count
