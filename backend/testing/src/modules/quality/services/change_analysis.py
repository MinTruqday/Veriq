import re
from difflib import SequenceMatcher

from src.core.common import plain_text

def _criterion_snapshot(items):
    return [
        {
            "key": str(item.get("key") or ""),
            "text": plain_text(item.get("content_doc") or {}).strip(),
            "source_span": item.get("source_span"),
        }
        for item in items or []
    ]


def semantic_candidate_score(requirement_text, test_text):
    
    requirement_tokens = set(re.findall('[\\w-]+', requirement_text.casefold()))
    test_tokens = set(re.findall('[\\w-]+', test_text.casefold()))
    if not requirement_tokens or not test_tokens:
        return 0.0
    return len(requirement_tokens & test_tokens) / max(1, len(requirement_tokens))


def semantic_changes(before, after):
    
    before_text = before.get("plain_text_projection", "")
    after_text = after.get("plain_text_projection", "")

    before_criteria = _criterion_snapshot(before.get("acceptance_criteria"))
    after_criteria = _criterion_snapshot(after.get("acceptance_criteria"))
    changed_fields = [
        field
        for field in [
            "title",
            "actors",
            "business_rules",
            "dependencies",
        ]
        if before.get(field) != after.get(field)
    ]
    criteria_changed = before_criteria != after_criteria
    if criteria_changed:
        changed_fields.append("acceptance_criteria")
    content_changed = before_text.strip() != after_text.strip()
    if not content_changed and not changed_fields:
        return []
    ratio = SequenceMatcher(None, before_text.lower(), after_text.lower()).ratio()
    source_changed = content_changed or bool(changed_fields)
    evidence = [
        {
            "artifact_version_id": before["_id"],
            "text": before_text[:500],
        },
        {
            "artifact_version_id": after["_id"],
            "text": after_text[:500],
        },
    ]
    if criteria_changed:
        evidence = [
            {
                "artifact_version_id": before["_id"],
                "text": "\n".join(item["text"] for item in before_criteria if item["text"]),
                "acceptance_criteria": before_criteria,
            },
            {
                "artifact_version_id": after["_id"],
                "text": "\n".join(item["text"] for item in after_criteria if item["text"]),
                "acceptance_criteria": after_criteria,
            },
        ]
    return [
        {
            "type": "MODIFIED_INPUT" if source_changed else "TEXT_ONLY",
            "subject": "content" if content_changed else ",".join(changed_fields),
            "before": {
                "text": before_text[: 500],
                "fields": {
                    field: before_criteria if field == "acceptance_criteria" else before.get(field)
                    for field in changed_fields
                },
            },
            "after": {
                "text": after_text[: 500],
                "fields": {
                    field: after_criteria if field == "acceptance_criteria" else after.get(field)
                    for field in changed_fields
                },
            },
            "confidence": round(
                max(
                    0.55,
                    1 - ratio / 2.0,
                ),
                4,
            ),
            "evidence": evidence,
        }
    ]


def classify_test_impact(test_version, changes, direct_trace):
    
    classification = (
        'POTENTIALLY_AFFECTED'
        if direct_trace
        else 'STILL_VALID'
    )
    confidence = (
        0.78
        if direct_trace
        else 0.45
    )
    reasons = [
        "Có liên kết truy vết trực tiếp tới Requirement thay đổi"
        if direct_trace
        else "Không có liên kết truy vết trực tiếp tới Requirement thay đổi"
    ]
    return {
        "test_case_id": test_version["test_case_id"],
        "test_case_version_id": test_version["_id"],
        "test_case_key": test_version.get("test_case_key"),
        "classification": classification,
        "confidence": confidence,
        "reasons": reasons,
        "evidence": [
            {
                "artifact_type": "test_case_version",
                "artifact_version_id": test_version["_id"],
                "direct_trace": direct_trace,
            }
        ],
        "proposed_actions": [],
    }
