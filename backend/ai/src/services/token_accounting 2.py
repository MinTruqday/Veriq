from typing import Any


def usage_values(response: Any, input_chars: int, output_chars: int) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if isinstance(usage, dict):
        get_value = usage.get
    else:
        def get_value(key, default=0):
            return getattr(usage, key, default)
    prompt = int(get_value("prompt_tokens", 0) or get_value("input_tokens", 0) or 0)
    completion = int(get_value("completion_tokens", 0) or get_value("output_tokens", 0) or 0)
    cached = int(get_value("cached_tokens", 0) or get_value("cache_read_input_tokens", 0) or 0)
    return {
        "input_tokens": prompt or max(1, input_chars // 4),
        "output_tokens": completion or max(1, output_chars // 4),
        "cached_tokens": cached,
    }


def record_usage(response: Any, input_chars: int, output_chars: int) -> dict[str, int]:
    return usage_values(response, input_chars, output_chars)
