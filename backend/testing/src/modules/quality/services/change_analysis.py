import re

from src.modules.quality.services.requirement_version_diff import compare_requirement_versions


def semantic_candidate_score(requirement_text, test_text):
    requirement_tokens = set(re.findall(r"[\w-]+", str(requirement_text or "").casefold()))
    test_tokens = set(re.findall(r"[\w-]+", str(test_text or "").casefold()))
    if not requirement_tokens or not test_tokens:
        return 0.0
    return len(requirement_tokens & test_tokens) / max(1, len(requirement_tokens))


def semantic_changes(before, after):
    comparison = compare_requirement_versions(
        before,
        after,
        before.get("acceptance_criteria") or [],
        after.get("acceptance_criteria") or [],
    )
    return [
        {
            "type": "MODIFIED_INPUT",
            "field": item["field"],
            "before": item["before"],
            "after": item["after"],
            "diff": item["diff"],
        }
        for item in comparison["changes"]
    ]


def classify_test_impact(test_version, direct_trace):
    classification = "POTENTIALLY_AFFECTED" if direct_trace else "STILL_VALID"
    confidence = 0.78 if direct_trace else 0.45
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
