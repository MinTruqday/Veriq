from functools import lru_cache
from math import isfinite

from fastapi import HTTPException


@lru_cache(maxsize=1)
def default_project_settings():
    return {
        "impact_confidence_threshold": 0.75,
        "testcase_duplicate_threshold": 0.72,
        "trace_recovery_minimum_confidence": 0.18,
        "completion_open_blocker_threshold": 0,
        "read_after_archive_policy": "ALLOW_READ",
    }


def resolve_project_settings(settings):
    values = {**default_project_settings(), **(settings or {})}
    # Maker-checker is enforced by the approval services, not a project toggle.
    values.pop("require_independent_review", None)
    return values


def validate_project_settings(settings):
    values = resolve_project_settings(settings)
    numeric_ranges = {
        "impact_confidence_threshold": (0, 1, False),
        "testcase_duplicate_threshold": (0, 1, False),
        "trace_recovery_minimum_confidence": (0, 1, False),
        "completion_open_blocker_threshold": (0, 1000, True),
    }
    for key, (minimum, maximum, integral) in numeric_ranges.items():
        value = values[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or not minimum <= value <= maximum
            or integral and not isinstance(value, int)
        ):
            raise HTTPException(
                status_code=422,
                detail={"code": "PROJECT_SETTING_VALUE_INVALID", "setting": key},
            )
    if values.get("read_after_archive_policy") not in {"ALLOW_READ", "DENY_READ"}:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_SETTING_VALUE_INVALID", "setting": "read_after_archive_policy"},
        )
    return values


def resolve_testcase_duplicate_threshold(settings):
    return float(resolve_project_settings(settings)["testcase_duplicate_threshold"])
