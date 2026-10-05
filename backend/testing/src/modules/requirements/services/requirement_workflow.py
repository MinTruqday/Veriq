import hashlib
import json

from src.core.common import plain_text





def text_doc(value):
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(value)}]}],
    }


def serialized_content(content):
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def acceptance_criterion_text(item):
    return str(item.get("plain_text") or plain_text(item.get("content_doc", {})) or "").strip()


def normalized_business_rule_lines(values):
    normalized = []
    for index, value in enumerate(values or [], 1):
        text = str(value).strip()
        if not text:
            continue
        prefix, separator, remainder = text.partition(":")
        identity = prefix.upper()
        prefix_length = len('BR-')
        if (
            separator
            and identity.startswith('BR-')
            and identity[prefix_length:].isdigit()
        ):
            normalized.append(f"{identity}: {remainder.strip()}")
        else:
            normalized.append(f"{'BR-'}{index:02d}: {text}")
    return normalized


def prepare_requirement_ai_suggestion(candidate, acceptance_criteria):
    suggestion = dict(candidate)
    patch = {}
    
    for source, target in {'revised_actors': 'actors',
 'revised_business_rules': 'business_rules',
 'revised_dependencies': 'dependencies'}.items():
        if suggestion.get(source) is not None:
            patch[target] = (
                normalized_business_rule_lines(suggestion[source])
                if source == "revised_business_rules"
                else suggestion[source]
            )
    if suggestion.get("revised_acceptance_criteria") is not None:
        existing = {item.get("key"): item for item in acceptance_criteria}
        patch["acceptance_criteria"] = [
            {
                "key": item["key"],
                "content_doc": text_doc(item["content"]),
                "status": existing.get(item["key"], {}).get(
                    "status", 'draft'
                ),
                "source_span": existing.get(item["key"], {}).get("source_span"),
            }
            for item in suggestion["revised_acceptance_criteria"]
        ]
    suggestion["patch"] = patch
    return suggestion


def requirement_suggestion_changes(version, suggestion, acceptance_criteria=None):
    current_title = str(version.get("title") or "").strip()
    current_content = str(
        version.get("plain_text_projection") or plain_text(version.get("content_doc", {})) or ""
    ).strip()
    revised_title = str(suggestion.get("revised_title") or "").strip()
    revised_content = str(suggestion.get("revised_content") or "").strip()
    patch = suggestion.get("patch") if isinstance(suggestion.get("patch"), dict) else {}
    current_criteria = [acceptance_criterion_text(item) for item in (acceptance_criteria or [])]
    proposed_criteria = [
        acceptance_criterion_text(item) for item in patch.get("acceptance_criteria", [])
    ]
    return bool(
        revised_title
        and revised_title != current_title
        or revised_content
        and revised_content != current_content
        or "actors" in patch
        and patch["actors"] != version.get("actors", [])
        or "business_rules" in patch
        and patch["business_rules"] != version.get("business_rules", [])
        or "dependencies" in patch
        and patch["dependencies"] != version.get("dependencies", [])
        or "acceptance_criteria" in patch
        and proposed_criteria != current_criteria
    )


def prepare_requirement_candidates(job_id, candidates):
    prepared = []
    for index, value in enumerate(candidates):
        candidate = dict(value)
        candidate["quality_issues"] = candidate_quality_issues(candidate)
        candidate["candidate_id"] = candidate.get("candidate_id") or (
            f"{job_id}{'-CAND-'}{index + 1}"
        )
        candidate["candidate_status"] = 'ACTIVE'
        candidate["candidate_revision"] = int(
            candidate.get("candidate_revision", 1)
        )
        candidate["parent_candidate_ids"] = list(candidate.get("parent_candidate_ids", []))
        prepared.append(candidate)
    return prepared


def candidate_quality_issues(candidate):
    issues = []
    if not str(candidate.get("title") or "").strip() or not plain_text(candidate.get("content_doc") or {}).strip():
        issues.append("REQUIREMENT_CONTENT_MISSING")
    if not candidate.get("source_refs"):
        issues.append("REQUIREMENT_SOURCE_MISSING")
    if candidate.get("type") in ("functional", "api", "permission", "integration") and not candidate.get("acceptance_criteria"):
        issues.append("ACCEPTANCE_CRITERIA_MISSING_FOR_BASELINE")
    if "missing" in (candidate.get("section_states") or {}).values():
        issues.append("APPLICABLE_SECTION_MISSING_FOR_BASELINE")
    return issues


def candidate_fingerprint(candidate):
    return hashlib.sha256(
        serialized_content(
            {
                "candidate_id": candidate.get("candidate_id"),
                "title": candidate.get("title"),
                "content_doc": candidate.get("content_doc"),
                "source_refs": candidate.get("source_refs", []),
            }
        ).encode("utf-8")
    ).hexdigest()
