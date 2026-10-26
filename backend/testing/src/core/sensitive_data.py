import re

REDACTED_VALUE = "Đã ẩn"
FIELD_NAME_PATTERN = r"token|secret|password|authorization|cookie|api[-_]?key"
AUTHORIZATION_PATTERN = r"(authorization)(\s*[:=]\s*)(?!['\"]?Đã(?:%20|\s)ẩn)['\"]?[^'\";,&]+"
RAW_ASSIGNMENT_PATTERN = r"(password|secret|token|api[_-]?key)(\s*[:=]\s*)['\"](?!\$\{|<|Đã ẩn)[^'\"]{4,}['\"]"
INLINE_VALUE_PATTERN = r"(authorization|token|secret|password|api[-_]?key)(\s*[:=]\s*)(?!['\"]?Đã(?:%20|\s)ẩn)['\"]?(?!\$\{|<)[^'\"\s;,&]+"
URL_VALUE_PATTERN = r"(?i)([?&](?:token|secret|password|api[-_]?key)=)(?!Đã%20ẩn|Đã ẩn)[^&#\s]+"


def secret_pattern():
    return re.compile(FIELD_NAME_PATTERN, re.I)


def redact_sensitive_text(value):
    result = re.sub(
        URL_VALUE_PATTERN,
        lambda match: f"{match.group(1)}{REDACTED_VALUE}",
        value,
    )
    result = re.sub(
        AUTHORIZATION_PATTERN,
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED_VALUE}",
        result,
        flags=re.I,
    )
    for pattern in (RAW_ASSIGNMENT_PATTERN, INLINE_VALUE_PATTERN):
        result = re.sub(
            pattern,
            lambda match: f"{match.group(1)}{match.group(2)}{REDACTED_VALUE}",
            result,
            flags=re.I,
        )
    return result


def redact_sensitive_data(value):
    if isinstance(value, dict):
        return {
            key: REDACTED_VALUE
            if secret_pattern().search(str(key))
            else redact_sensitive_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value
