from src.core.ai_assistance import request_ai_assistance





def document(value):
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": value}]}],
    }


def normalize_maintenance_patch(value):
    if not isinstance(value, dict):
        return {}
    patch = {
        key: value[key]
        for key in ("title", "type", "test_data")
        if value.get(key) is not None
    }
    for source, target in (
        ("objective", "objective_doc"),
        ("preconditions", "preconditions_doc"),
        ("expected", "expected_result_doc"),
    ):
        text = value.get(source)
        if isinstance(text, str) and text.strip():
            patch[target] = document(text.strip())
    steps = value.get("steps")
    if isinstance(steps, list) and steps:
        normalized_steps = []
        for index, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                return {}
            action = str(step.get("action") or "").strip()
            expected = str(step.get("expected") or "").strip()
            if not action or not expected:
                return {}
            normalized_steps.append(
                {
                    "id": f"step-{index}",
                    "order": index,
                    "action_doc": document(action),
                    "expected_doc": document(expected),
                    "test_data": step.get("test_data")
                    if isinstance(step.get("test_data"), dict)
                    else {},
                }
            )
        patch["steps"] = normalized_steps
    return patch


async def request_impact_classification(project_id, change_set, candidates):
    evidence = [
        {
            "artifact_type": "requirement_change_set",
            "artifact_id": change_set["_id"],
            "artifact_version_id": change_set.get("to_version_id"),
            "authority": 'PROJECT_BASELINE',
            "text": str(change_set.get("changes", [])),
        }
    ]
    evidence.extend(
        {
            "artifact_type": "test_case_version",
            "artifact_id": item.get("test_case_id"),
            "artifact_version_id": item.get("_id"),
            "authority": 'PROJECT_BASELINE',
            "text": str(item.get("plain_text_projection", "")),
        }
        for item in candidates[:99]
    )
    return await request_ai_assistance(
        "impact_analysis",
        project_id,
        "",
        evidence,
    )


def apply_ai_impact_suggestions(items, ai_result):
    
    allowed = {
        'STILL_VALID',
        'POTENTIALLY_AFFECTED',
        'NEEDS_UPDATE',
        'OBSOLETE',
    }
    by_version = {item["test_case_version_id"]: item for item in items}
    applied = []
    for suggestion in ai_result.get("suggestions", []):
        version_id = suggestion.get("test_case_version_id") or suggestion.get("artifact_version_id")
        classification = suggestion.get("classification")
        if version_id not in by_version or classification not in allowed:
            continue
        target = by_version[version_id]
        target["ai_classification"] = classification
        target["ai_confidence"] = max(
            0, min(1, float(suggestion.get("confidence", ai_result.get("confidence", 0))))
        )
        target["ai_reason"] = str(suggestion.get("reason") or "")[:2000]
        patch = normalize_maintenance_patch(suggestion.get("maintenance_patch"))
        if patch:
            target["ai_maintenance_patch"] = patch
        target["evidence"].append(
            {
                "artifact_type": "ai_impact_classification",
                "artifact_version_id": version_id,
                "classification": classification,
                "confidence": target["ai_confidence"],
            }
        )
        if (
            target["ai_confidence"] >= 0.7
            and target["confidence"] < 0.9
        ):
            target["classification"] = classification
            target["confidence"] = max(target["confidence"], target["ai_confidence"])
            target["reasons"].append(target["ai_reason"])
        applied.append(version_id)
    return applied


def ai_new_test_requirements(ai_result, requirement_version_id):
    items = []
    for candidate in ai_result.get("new_test_candidates", []):
        patch = normalize_maintenance_patch(candidate.get("patch"))
        if not patch or not patch.get("title") or not patch.get("steps"):
            continue
        patch["requirement_version_ids"] = [requirement_version_id]
        items.append(
            {
                "classification": 'NEW_TEST_REQUIRED',
                "reason": str(candidate.get("reason") or "")[:5000],
                "confidence": max(0, min(1, float(candidate.get("confidence", 0)))),
                "patch": patch,
                "evidence": ai_result.get("evidence_refs", []),
            }
        )
    return items
