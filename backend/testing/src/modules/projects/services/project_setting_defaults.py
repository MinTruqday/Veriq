import json
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException


@lru_cache(maxsize=1)
def default_project_settings():
    path = Path(__file__).resolve().parents[3] / "config" / "project_setting_defaults.json"
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_project_settings(settings):
    return {**default_project_settings(), **(settings or {})}


def resolve_testcase_duplicate_threshold(settings):
    value = resolve_project_settings(settings).get("testcase_duplicate_threshold")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_TESTCASE_DUPLICATE_THRESHOLD_INVALID"},
        )
    return float(value)
