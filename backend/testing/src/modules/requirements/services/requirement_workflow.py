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


def prepare_requirement_candidates(job_id, candidates):
    prepared = []
    for index, value in enumerate(candidates):
        candidate = dict(value)
        candidate_type = str(candidate.get("type") or "").strip()
        candidate["type"] = candidate_type or "Chưa phân loại"
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
    if candidate.get("source_grounding_status") == "NEEDS_REVIEW":
        issues.append("REQUIREMENT_SOURCE_REVIEW_REQUIRED")
    missing_sections = candidate.get("section_states") or {}
    if any(
        state == "missing" and section != "acceptance_criteria"
        for section, state in missing_sections.items()
    ):
        issues.append("APPLICABLE_SECTION_MISSING_FOR_BASELINE")
    return issues


def candidate_fingerprint(candidate):
    return hashlib.sha256(
        serialized_content(candidate).encode("utf-8")
    ).hexdigest()
