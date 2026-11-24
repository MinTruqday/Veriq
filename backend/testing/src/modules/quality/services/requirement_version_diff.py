"""Compare requirement content without treating formatting as business changes."""

import difflib
import re
import unicodedata

from src.core.common import plain_text


def _normalize(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(value or ""))).strip()


def _lines(values):
    return sorted(_normalize(item) for item in values or [] if _normalize(item))


def compare_requirement_versions(previous, current, previous_criteria, current_criteria):
    """Return explicit textual differences; it does not infer semantic equivalence."""
    sections = {
        "title": (_normalize(previous.get("title")), _normalize(current.get("title"))),
        "content": (
            _normalize(plain_text(previous.get("content_doc") or {})),
            _normalize(plain_text(current.get("content_doc") or {})),
        ),
        "business_rules": (
            "\n".join(_lines(previous.get("business_rules"))),
            "\n".join(_lines(current.get("business_rules"))),
        ),
        "acceptance_criteria": (
            "\n".join(_lines(plain_text(item.get("content_doc") or {}) for item in previous_criteria)),
            "\n".join(_lines(plain_text(item.get("content_doc") or {}) for item in current_criteria)),
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
