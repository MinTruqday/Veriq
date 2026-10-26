"""Safe serialization for dynamic values embedded in prompt markup."""

import json


def prompt_json(value):
    """Serialize a value as JSON data that cannot close its surrounding prompt tag."""
    return (
        json.dumps(value, ensure_ascii=False, default=str)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
