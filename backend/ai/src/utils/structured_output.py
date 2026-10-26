import json
import re
from types import UnionType
from typing import Any, Type, Union, get_args, get_origin


class StructuredOutputError(ValueError):
    pass


def _balanced_candidates(text: str):
    for start, character in enumerate(text):
        if character not in "[{":
            continue
        stack = []
        quoted = False
        escaped = False
        for index in range(start, len(text)):
            current = text[index]
            if quoted:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    quoted = False
                continue
            if current == '"':
                quoted = True
            elif current in "[{":
                stack.append(current)
            elif current in "]}":
                if not stack:
                    break
                opening = stack.pop()
                if (opening, current) not in {("[", "]"), ("{", "}")}:
                    break
                if not stack:
                    yield text[start : index + 1]
                    break


def extract_json_values(text: Any) -> list[Any]:
    if isinstance(text, (dict, list)):
        return [text]
    if not isinstance(text, str) or not text.strip():
        raise StructuredOutputError("Model output is empty")
    cleaned = re.sub(
        r"<(think|thought)>.*?</\1>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    candidates = [cleaned]
    candidates.extend(
        match.group(1).strip()
        for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", cleaned, flags=re.IGNORECASE)
    )
    candidates.extend(_balanced_candidates(cleaned))
    failures = []
    values = []
    fingerprints = set()
    for candidate in candidates:
        variants = [candidate, re.sub(r",\s*([}\]])", r"\1", candidate)]
        for variant in variants:
            try:
                value = json.loads(variant)
                fingerprint = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                if fingerprint not in fingerprints:
                    fingerprints.add(fingerprint)
                    values.append(value)
                break
            except (TypeError, json.JSONDecodeError) as error:
                failures.append(str(error))
    if values:
        return values
    detail = failures[-1] if failures else "No JSON object or array found"
    raise StructuredOutputError(f"Invalid structured model output: {detail}")


def extract_json_value(text: Any) -> Any:
    return extract_json_values(text)[0]


def normalize_schema_collections(value: Any, schema: Type[Any]) -> Any:
    if not isinstance(value, dict) or not hasattr(schema, "model_fields"):
        return value
    normalized = {
        name: item
        for name, item in value.items()
        if name in schema.model_fields
    }
    for name, field in schema.model_fields.items():
        if name not in normalized:
            continue
        normalized[name] = normalize_annotation_value(normalized[name], field.annotation)
    return normalized


def normalize_annotation_value(value: Any, annotation: Any) -> Any:
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is list:
        if value is None:
            return []
        if isinstance(value, list) and arguments:
            return [normalize_annotation_value(item, arguments[0]) for item in value]
        return value
    if origin is dict:
        if not isinstance(value, dict) or len(arguments) != 2:
            return value
        value_annotation = arguments[1]
        if value_annotation is Any:
            return value
        return {
            key: normalize_annotation_value(item, value_annotation)
            for key, item in value.items()
        }
    if origin in {Union, UnionType}:
        for option in arguments:
            normalized = normalize_annotation_value(value, option)
            if normalized is not value or option is type(None):
                return normalized
        return value
    if isinstance(value, dict) and hasattr(annotation, "model_fields"):
        return normalize_schema_collections(value, annotation)
    return value


def validate_structured_output(text: Any, schema: Type[Any]) -> Any:
    errors = []
    for value in extract_json_values(text):
        try:
            if hasattr(schema, "model_validate"):
                return schema.model_validate(normalize_schema_collections(value, schema))
            return schema.parse_obj(value)
        except Exception as error:
            errors.append(error)
    if errors:
        raise StructuredOutputError(
            f"Structured output did not match schema: {errors[0]}"
        ) from errors[0]
    raise StructuredOutputError("Structured output did not contain a candidate")
