"""Compare requirement content without treating formatting as business changes."""

import difflib
import json
import re
import unicodedata

from src.core.common import plain_text


def _normalize(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(value or ""))).strip()


def _lines(values):
    return [_normalize(item) for item in values or [] if _normalize(item)]


def _structured(value):
    if value in (None, {}, []):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _details(value):
    if not isinstance(value, dict):
        return _structured(value)
    ignored = {"actor", "actors", "progress_status", "change_impact"}
    return _structured({key: item for key, item in value.items() if key not in ignored})


def _criteria(values):
    keyed = []
    for index, item in enumerate(values or [], 1):
        text = _normalize(plain_text(item.get("content_doc") or {}))
        key = _normalize(item.get("key")) or str(index)
        if key or text:
            keyed.append((key, text))
    return "\n".join(f"{key}: {text}" for key, text in keyed if text)


def compare_requirement_versions(previous, current, previous_criteria, current_criteria):
    """Return explicit textual differences; it does not infer semantic equivalence."""
    sections = {
        "title": (_normalize(previous.get("title")), _normalize(current.get("title"))),
        "type": (_normalize(previous.get("type")), _normalize(current.get("type"))),
        "priority": (_normalize(previous.get("priority")), _normalize(current.get("priority"))),
        "content": (
            _normalize(plain_text(previous.get("content_doc") or {})),
            _normalize(plain_text(current.get("content_doc") or {})),
        ),
        "business_rules": (
            "\n".join(_lines(previous.get("business_rules"))),
            "\n".join(_lines(current.get("business_rules"))),
        ),
        "dependencies": (
            _structured(previous.get("dependencies")),
            _structured(current.get("dependencies")),
        ),
        "details": (
            _details(previous.get("details")),
            _details(current.get("details")),
        ),
        "custom_values": (
            _structured(previous.get("custom_values")),
            _structured(current.get("custom_values")),
        ),
        "acceptance_criteria": (
            _criteria(previous_criteria),
            _criteria(current_criteria),
        ),
    }
    changes = []
    for name, (before, after) in sections.items():
        if before == after:
            continue
        changes.append({
            "field": name,
            "before": before,
            "after": after,
            "diff": [
                {"operation": op, "before": before[i:j], "after": after[k:l]}
                for op, i, j, k, l in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
                if op != "equal"
            ],
        })
    return {"has_content_changes": bool(changes), "changes": changes}
