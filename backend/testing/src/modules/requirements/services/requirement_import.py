import csv
import hashlib
import io
import json
import re
import zipfile

from defusedxml import ElementTree
from fastapi import HTTPException
from pypdf import PdfReader
import yaml

from src.modules.requirements.services.requirement_workflow import text_doc



def supported_requirement_formats():
    return set(['pdf', 'docx', 'md', 'txt', 'csv', 'xlsx', 'openapi', 'postman'])


def safe_requirement_filename(value: str, fallback: str = "source.bin") -> str:
    filename = re.sub(
        '[^a-zA-Z0-9._-]', "_", value or fallback
    )
    return filename or fallback


def source_document_text(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, dict) or content.get("type") != "doc":
        raise HTTPException(status_code=422, detail={"code": "SOURCE_DOCUMENT_INVALID"})

    def render(node):
        if not isinstance(node, dict):
            return ""
        kind = node.get("type")
        if kind == "text":
            return str(node.get("text") or "")
        if kind == "hardBreak":
            return "\n"
        children = [render(child) for child in node.get("content", [])]
        if kind == "heading":
            level = (node.get("attrs") or {}).get("level", 1)
            return f"{'#' * level} {''.join(children).strip()}" if isinstance(level, int) and 1 <= level <= 6 else "".join(children)
        if kind in {"doc", "blockquote"}:
            return "\n\n".join(child for child in children if child.strip())
        if kind == "bulletList":
            return "\n".join(f"- {child}" for child in children if child.strip())
        if kind == "orderedList":
            return "\n".join(f"{index}. {child}" for index, child in enumerate(children, 1) if child.strip())
        if kind == "listItem":
            return " ".join(child for child in children if child.strip())
        if kind == "table":
            return "\n".join(child for child in children if child.strip())
        if kind == "tableRow":
            return " | ".join(children)
        return "".join(children)

    return render(content)


def parse_requirement_import(content, format):
    if format in set(['openapi', 'postman']):
        value = parse_api_content(content, format)
        return parse_api_artifact(value, format)
    if format == "csv":
        rows = list(csv.DictReader(io.StringIO(str(content))))
        return [
            {
                "requirement_key": row.get("requirement_key") or None,
                "title": row.get("title") or f"Requirement nhập dòng {index + 1}",
                "type": row.get("type") or "functional",
                "priority": row.get("priority") or "medium",
                "risk": row.get("risk") or "medium",
                "content_doc": text_doc(row.get("content") or row.get("description") or ""),
                "acceptance_criteria": [],
            }
            for index, row in enumerate(rows)
        ]
    text = str(content)
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    return [
        {
            "title": block.splitlines()[0][: 300],
            "content_doc": text_doc(block),
            "acceptance_criteria": [],
        }
        for block in blocks
    ]


def atomic_requirement_candidates(document):
    content = document["normalized_content"]
    if document["format"] in set(['csv', 'xlsx', 'openapi', 'postman']):
        candidates = parse_requirement_import(content, document["format"])
        for index, candidate in enumerate(candidates):
            source_reference = {
                "requirement_document_id": document["_id"],
                "content_hash": document["content_hash"],
                "source_version": document.get("source_version"),
                "candidate_index": index,
                "format": document["format"],
            }
            if document["format"] in {"openapi", "postman"}:
                source_reference["operation"] = candidate.get("source_refs", [{}])[0]
                candidate["details"]["api_operations"] = [
                    {"requirement_document_id": document["_id"], **operation}
                    for operation in candidate["details"]["api_operations"]
                ]
            candidate["source_refs"] = [source_reference]
        return candidates
    text = str(content)
    candidates = []
    sections = []
    paragraph_start = None
    paragraph_end = 0

    def add_paragraph(start, end):
        raw = text[start:end].strip()
        value = re.sub(r"^\s*(?:[-*•]+|\d+[.)])\s*", "", raw).strip()
        if len(value) < 2:
            return
        source_start = text.find(value, start, end)
        if source_start < 0:
            source_start = start
        source_end = source_start + len(value)
        candidates.append(
            {
                "title": value.splitlines()[0][: 300],
                "content_doc": text_doc(value),
                "acceptance_criteria": [],
                "source_refs": [
                    {
                        "requirement_document_id": document["_id"],
                        "content_hash": document["content_hash"],
                        "source_version": document.get("source_version"),
                        "source_start": source_start,
                        "source_end": source_end,
                        "source_text_hash": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                        "section": " / ".join(sections),
                        "format": document["format"],
                    }
                ],
            }
        )
        if len(candidates) > 500:
            raise HTTPException(status_code=413, detail={"code": "IMPORT_CANDIDATE_LIMIT_EXCEEDED"})

    position = 0
    for line in text.splitlines(keepends=True):
        line_start = position
        position += len(line)
        stripped = line.strip()
        heading = re.fullmatch(r"(#{1,6})\s+(.+)", stripped)
        if heading or not stripped:
            if paragraph_start is not None:
                add_paragraph(paragraph_start, paragraph_end)
                paragraph_start = None
            if heading:
                sections = sections[: len(heading.group(1)) - 1]
                sections.append(heading.group(2).strip())
            continue
        if paragraph_start is None:
            paragraph_start = line_start
        paragraph_end = position
    if paragraph_start is not None:
        add_paragraph(paragraph_start, paragraph_end)
    return candidates


def extract_file_content(data, format):
    if format == "pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    if format == "docx":
        return extract_docx(data)
    if format == "xlsx":
        return extract_xlsx_csv(data)
    text = data.decode("utf-8-sig")
    if format in set(['openapi', 'postman']):
        return parse_api_content(text, format)
    return text


def parse_api_content(content, artifact_format):
    if not isinstance(content, str):
        value = content
    else:
        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            if artifact_format != "openapi":
                raise HTTPException(status_code=422, detail={"code": "API_DEFINITION_INVALID"})
            try:
                value = yaml.safe_load(content)
            except yaml.YAMLError as error:
                raise HTTPException(status_code=422, detail={"code": "API_DEFINITION_INVALID"}) from error
    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail={"code": "API_DEFINITION_INVALID"})
    return value


def extract_docx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t")).strip()
        if text:
            properties = paragraph.find(f"{namespace}pPr")
            style = properties.find(f"{namespace}pStyle") if properties is not None else None
            outline = properties.find(f"{namespace}outlineLvl") if properties is not None else None
            style_name = style.attrib.get(f"{namespace}val", "") if style is not None else ""
            match = re.search(r"Heading([1-6])$", style_name, re.IGNORECASE)
            level = int(match.group(1)) if match else None
            if outline is not None and level is None:
                level = min(int(outline.attrib.get(f"{namespace}val", "0")) + 1, 6)
            paragraphs.append(f"{'#' * level} {text}" if level else text)
    return "\n\n".join(paragraphs)


def extract_xlsx_csv(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.iter() if node.tag.endswith("}t"))
                for item in root
            ]
        sheets = sorted(
            name
            for name in names
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        )
        rows = []
        for sheet in sheets:
            root = ElementTree.fromstring(archive.read(sheet))
            for row in (node for node in root.iter() if node.tag.endswith("}row")):
                values = []
                for cell in (node for node in row if node.tag.endswith("}c")):
                    cell_type = cell.attrib.get("t")
                    if cell_type == "inlineStr":
                        value = "".join(
                            node.text or "" for node in cell.iter() if node.tag.endswith("}t")
                        )
                    else:
                        value_node = next((node for node in cell if node.tag.endswith("}v")), None)
                        value = value_node.text if value_node is not None else ""
                    if cell_type == "s" and value:
                        value = shared[int(value)]
                    values.append(value or "")
                rows.append(values)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerows(rows)
    return stream.getvalue()


def api_operation_identifiers(content, artifact_format):
    value = parse_api_content(content, artifact_format)
    operations = []
    if artifact_format == "openapi":
        paths = value.get("paths", {})
        if not isinstance(paths, dict):
            raise HTTPException(status_code=422, detail={"code": "API_DEFINITION_INVALID"})
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() in {"get", "post", "put", "patch", "delete"} and isinstance(operation, dict):
                    operations.append({"method": method.upper(), "path": path, "operation_id": operation.get("operationId")})
    elif artifact_format == "postman":
        def walk(nodes, folder=""):
            if not isinstance(nodes, list):
                raise HTTPException(status_code=422, detail={"code": "API_DEFINITION_INVALID"})
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if "item" in node:
                    walk(node["item"], "/".join(filter(None, [folder, node.get("name", "")])))
                elif isinstance(node.get("request"), dict):
                    request = node["request"]
                    url = request.get("url", {})
                    raw_url = url.get("raw", "") if isinstance(url, dict) else str(url)
                    operations.append({"method": str(request.get("method") or "GET").upper(), "url_template": raw_url.split("?", 1)[0], "folder": folder})
        walk(value.get("item", []))
    else:
        raise HTTPException(status_code=422, detail={"code": "API_DEFINITION_INVALID"})
    return operations


def parse_api_artifact(value, artifact_format):
    items = []
    if artifact_format == "openapi":
        paths = value.get("paths", {})
        if not isinstance(paths, dict):
            raise HTTPException(status_code=422, detail={"code": "API_DEFINITION_INVALID"})
        for path, operations in paths.items():
            if not isinstance(operations, dict):
                continue
            for method, operation in operations.items():
                if method.lower() not in set(['get', 'post', 'put', 'patch', 'delete']):
                    continue
                if not isinstance(operation, dict):
                    continue
                description = str(operation.get("description") or "").strip()
                if not description:
                    continue
                items.append(
                    {
                        "title": operation.get("summary") or f"{method.upper()} {path}",
                        "type": "api",
                        "content_doc": text_doc(description),
                        "details": {"api_operations": [{"path": path, "method": method.upper(), "operation_id": operation.get("operationId")}]},
                        "source_refs": [{"type": "openapi", "path": path, "method": method.upper(), "operation_id": operation.get("operationId")}],
                        "acceptance_criteria": [],
                    }
                )
                if len(items) > 500:
                    raise HTTPException(status_code=413, detail={"code": "IMPORT_CANDIDATE_LIMIT_EXCEEDED"})
    else:
        def walk(nodes, folder=""):
            if not isinstance(nodes, list):
                raise HTTPException(status_code=422, detail={"code": "API_DEFINITION_INVALID"})
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if "item" in node:
                    walk(node["item"], "/".join(filter(None, [folder, node.get("name", "")])))
                elif "request" in node:
                    request = node["request"]
                    if not isinstance(request, dict):
                        continue
                    description = request.get("description") or node.get("description") or ""
                    if isinstance(description, dict):
                        description = description.get("content") or ""
                    description = str(description).strip()
                    if not description:
                        continue
                    url = request.get("url", {})
                    raw_url = url.get("raw", "") if isinstance(url, dict) else str(url)
                    items.append(
                        {
                            "title": node.get("name")
                            or f"{request.get('method', 'GET')} {raw_url}",
                            "type": "api",
                            "content_doc": text_doc(description),
                            "details": {"api_operations": [{"folder": folder, "method": str(request.get("method") or "GET").upper(), "url_template": raw_url.split("?", 1)[0]}]},
                            "source_refs": [{"type": "postman", "folder": folder, "method": request.get("method"), "url_template": raw_url.split("?", 1)[0]}],
                            "acceptance_criteria": [],
                        }
                    )
                    if len(items) > 500:
                        raise HTTPException(status_code=413, detail={"code": "IMPORT_CANDIDATE_LIMIT_EXCEEDED"})

        walk(value.get("item", []))
    return items
