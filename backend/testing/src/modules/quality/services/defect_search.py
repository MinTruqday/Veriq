import json

from src.clients.project_knowledge import index_artifact
from src.core.common import plain_text
from src.core.sensitive_data import redact_sensitive_data, redact_sensitive_text


def defect_search_text(defect):
    step_values = []
    for step in defect.get("steps_to_reproduce") or []:
        if not isinstance(step, dict):
            continue
        for field in ("action_doc", "expected_doc"):
            value = plain_text(step.get(field) or {})
            if value:
                step_values.append(value)
        for field in ("action", "data", "expected_result"):
            value = str(step.get(field) or "").strip()
            if value:
                step_values.append(value)
        for field in ("test_data",):
            value = step.get(field)
            if isinstance(value, dict):
                value = json.dumps(
                    redact_sensitive_data(value),
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
            elif value is not None:
                value = str(value).strip()
            if value:
                step_values.append(value)
    step_text = " ".join(dict.fromkeys(step_values))
    return redact_sensitive_text(
        " ".join(
            value
            for value in (
                defect.get("title"),
                plain_text(defect.get("description_doc") or {}),
                plain_text(defect.get("actual_result_doc") or {}),
                plain_text(defect.get("expected_result_doc") or {}),
                step_text,
            )
            if str(value or "").strip()
        )
    )


async def index_defect_for_search(project_id, defect):
    return await index_artifact(
        project_id,
        "defect",
        defect["_id"],
        defect["_id"],
        defect.get("title") or "",
        defect_search_text(defect),
        defect.get("status") or "NEW",
        "PROJECT_REFERENCE",
        defect.get("revision"),
        linked_test_result_id=defect.get("linked_test_result_id"),
        linked_test_case_version_id=defect.get("linked_test_case_version_id"),
        linked_requirement_version_ids=defect.get("linked_requirement_version_ids") or [],
    )
