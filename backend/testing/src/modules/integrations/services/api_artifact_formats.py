import hashlib
import io
import re
import zipfile
from xml.sax.saxutils import escape

from src.core.common import now


def secret_pattern():
    return re.compile('token|secret|password|authorization|cookie|api[-_]?key', re.I)


def public_api_import(value, include_preview=False):
    result = {key: item for key, item in value.items() if key not in {"raw_content", "preview"}}
    result["preview_count"] = len(value.get("preview") or [])
    if include_preview:
        result["preview"] = value.get("preview") or []
    return result


def operation_identity(operation):
    return f"{operation.get('method', '').upper()} {operation.get('path', '')}"


def operation_fingerprint(operation):
    comparable = {
        key: value
        for key, value in operation.items()
        if key not in {"_id", "project_id", "import_id", "created_at"}
    }
    return hashlib.sha256(
        json_bytes(comparable)
    ).hexdigest()


def json_bytes(value):
    import json

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def create_xlsx(rows):
    sheet_rows = []
    for row_index, row in enumerate(rows, 1):
        cells = []
        for column_index, value in enumerate(row, 1):
            reference = f"{xlsx_column(column_index)}{row_index}"
            normalized = re.sub(
                r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", "" if value is None else str(value)
            )
            cells.append(
                f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{escape(normalized)}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'
    root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    workbook = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Test Cases" sheetId="1" r:id="rId1"/></sheets></workbook>'
    workbook_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
    worksheet = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


def xlsx_column(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def parse_openapi(value):
    
    operations = []
    inherited_security = value.get("security", [])
    schemas = value.get("components", {}).get("schemas", {})
    for path, path_item in value.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() not in set(['get', 'post', 'put', 'patch', 'delete', 'options', 'head']):
                continue
            operations.append(
                {
                    "source_type": "openapi",
                    "operation_id": operation.get("operationId"),
                    "title": operation.get("summary") or f"{method.upper()} {path}",
                    "path": path,
                    "method": method.upper(),
                    "parameters": sanitize(
                        operation.get("parameters", []) + path_item.get("parameters", [])
                    ),
                    "request_body": sanitize(operation.get("requestBody", {})),
                    "responses": sanitize(operation.get("responses", {})),
                    "security": sanitize(operation.get("security", inherited_security)),
                    "schemas": sanitize(schemas),
                    "tags": operation.get("tags", []),
                }
            )
    return operations[: 5000]


def parse_postman(value):
    
    operations = []
    variable_names = [
        item.get("key")
        for item in value.get("variable") or []
        if item.get("key") and not secret_pattern().search(item.get("key", ""))
    ]

    def walk(nodes, folder=""):
        for node in nodes or []:
            if "item" in node:
                walk(node["item"], "/".join(filter(None, [folder, node.get("name", "")])))
                continue
            request = node.get("request")
            if not request:
                continue
            url = request.get("url", {})
            raw = url.get("raw", "") if isinstance(url, dict) else str(url)
            operations.append(
                {
                    "source_type": "postman",
                    "operation_id": node.get("id"),
                    "title": node.get("name")
                    or f"{request.get('method', 'GET')} {raw}",
                    "folder": folder,
                    "path": raw.split("?", 1)[0],
                    "method": request.get("method", "GET").upper(),
                    "header_names": [
                        item.get("key")
                        for item in request.get("header") or []
                        if item.get("key") and not secret_pattern().search(item.get("key", ""))
                    ],
                    "body": sanitize(request.get("body", {})),
                    "responses": {
                        str(response["code"]): {"name": response.get("name", "")}
                        for response in node.get("response") or []
                        if isinstance(response, dict)
                        and isinstance(response.get("code"), int)
                        and 100 <= response["code"] <= 599
                    },
                    "script_events": [item.get("listen") for item in node.get("event") or []],
                    "variable_names": variable_names,
                }
            )

    walk(value.get("item", []))
    return operations[: 5000]


def api_case_blueprints(operation):
    responses = operation.get("responses") or {}
    if not isinstance(responses, dict):
        return []
    cases = []
    for code, response in responses.items():
        status = str(code).strip()
        if not status.isdigit() or not 100 <= int(status) <= 599:
            continue
        detail = response if isinstance(response, dict) else {}
        description = str(detail.get("description") or detail.get("name") or "").strip()
        cases.append({
            "response_code": status,
            "title": f"{operation['method']} {operation['path']} phản hồi {status}",
            "expected": f"HTTP {status} {description}".strip(),
        })
    return cases


def sanitize(value, sensitive_context=False):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            key_text = str(key)
            key_sensitive = bool(secret_pattern().search(key_text))
            if sensitive_context and key_text.lower() in {
                "value", "example", "examples", "default", "enum", "const"
            }:
                result[key] = '{{VERIQ_SECRET_VALUE}}'
            elif key_sensitive and not isinstance(item, (dict, list)):
                result[key] = '{{VERIQ_SECRET_VALUE}}'
            else:
                result[key] = sanitize(item, sensitive_context or key_sensitive)
        return result
    if isinstance(value, list):
        return [sanitize(item, sensitive_context) for item in value]
    return value


def sanitize_postman(value):
    
    
    if isinstance(value, list):
        return [sanitize_postman(item) for item in value]
    if isinstance(value, dict):
        marker = str(value.get("key") or value.get("name") or "")
        sensitive_entry = bool(secret_pattern().search(marker))
        result = {}
        for key, item in value.items():
            if sensitive_entry and key in {"value", "current", "initial"}:
                suffix = (
                    re.sub(r"[^A-Za-z0-9]+", "_", marker).upper()
                    or 'VALUE'
                )
                result[key] = f"{'{{VERIQ_SECRET_'}{suffix}}}}}"
            elif secret_pattern().search(str(key)) and key not in {"key", "name"}:
                result[key] = '{{VERIQ_SECRET_VALUE}}'
            else:
                result[key] = sanitize_postman(item)
        return result
    if isinstance(value, str):
        sanitized = re.sub(
            '(?i)([?&](?:token|secret|password|api[-_]?key)=)(?!Đã%20ẩn|Đã ẩn)[^&#\\s]+',
            '\\1{{VERIQ_SECRET_VALUE}}',
            value,
        )
        return re.sub(
            '(?i)(authorization|token|secret|password|api[-_]?key)(\\s*[:=]\\s*)[\'"]?(?!Đã ẩn)[^\'"\\s;,&]+',
            '\\1={{VERIQ_SECRET_VALUE}}',
            sanitized,
        )
    return value


def terms(value):
    
    return {
        item
        for item in re.findall('[a-zA-Z0-9_]+', value.lower())
        if len(item) >= 3
    }


def lexical_similarity(left, right):
    left_terms = terms(left)
    right_terms = terms(right)
    union = left_terms | right_terms
    return round(len(left_terms & right_terms) / len(union), 4) if union else 0


def model_metadata(model):
    return {
        "provider": "hybrid-deterministic",
        "model": model,
        "prompt_version": "ai_assistance",
        "tool_schema_version": "1",
        "retrieval_version": "project_evidence",
        "created_at": now(),
    }
