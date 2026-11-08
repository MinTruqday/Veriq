import re

from fastapi import HTTPException

from src.core.project_settings import default_project_settings, validate_project_settings


def _default_dimensions():
    return default_project_settings()["complexity_dimensions"]


def resolve_project_complexity_dimensions(settings):
    values = (settings or {}).get("complexity_dimensions")
    if values is None:
        values = _default_dimensions()
    if not isinstance(values, list) or not 1 <= len(values) <= 100:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_COMPLEXITY_DIMENSIONS_INVALID"},
        )
    normalized = []
    seen = set()
    for value in values:
        if not isinstance(value, dict):
            raise HTTPException(
                status_code=422,
                detail={"code": "PROJECT_COMPLEXITY_DIMENSIONS_INVALID"},
            )
        dimension_id = str(value.get("id") or "").strip()
        label = str(value.get("label") or "").strip()
        description = str(value.get("description") or "").strip()
        key = dimension_id.casefold()
        if (
            not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,99}", dimension_id)
            or len(label) < 2
            or len(label) > 200
            or len(description) > 2000
            or key in seen
        ):
            raise HTTPException(
                status_code=422,
                detail={"code": "PROJECT_COMPLEXITY_DIMENSIONS_INVALID"},
            )
        seen.add(key)
        normalized.append({"id": dimension_id, "label": label, "description": description})
    return normalized


def normalize_project_settings(settings):
    values = validate_project_settings(settings)
    values["complexity_dimensions"] = resolve_project_complexity_dimensions(values)
    return values
