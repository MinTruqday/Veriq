import csv
import hashlib
import io
import json
import re
import unicodedata
import zipfile

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from fastapi import HTTPException
from pypdf import PdfReader
import yaml

from src.modules.requirements.services.requirement_workflow import text_doc


ACCEPTANCE_CRITERION_LINE = re.compile(
    r"^\s*(?:[-*•]\s*)?((?:AC|ACCEPTANCE[-_ ]?CRITERION)[-_ ]?\d+)\s*[:.)\-–—]\s*(.+?)\s*$",
    re.IGNORECASE,
)
TABLE_ACCEPTANCE_CRITERION_LINE = re.compile(
    r"^\s*\|?\s*((?:AC|ACCEPTANCE[-_ ]?CRITERION)[-_ ]?\d+)\s*[:.)\-–—]?\s*\|\s*(.+?)\s*\|?\s*$",
    re.IGNORECASE,
)
MARKDOWN_TABLE_SEPARATOR = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)
ACCEPTANCE_CRITERIA_SECTION = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\d+(?:\.\d+)*[.)]?\s*)?(?:acceptance criteria|acceptance criterion|tiêu chí chấp nhận|điều kiện chấp nhận)(?:\s*\([^)]*\))?\s*[:.]?\s*$",
    re.IGNORECASE,
)
NUMBERED_UPPERCASE_SECTION = re.compile(
    r"^\s*(?:#{1,6}\s*)?\d+(?:\.\d+)*[.)]?\s+[A-ZÀ-Ỹ0-9][A-ZÀ-Ỹ0-9\s()/:_-]{3,}\s*$"
)
REQUIREMENT_TABLE_FIELDS = {
    "requirement_key": {
        "key",
        "id",
        "requirement id",
        "requirement key",
        "ma",
        "ma yeu cau",
        "ma requirement",
    },
    "title": {
        "title",
        "name",
        "requirement",
        "requirement name",
        "ten",
        "ten yeu cau",
        "tieu de",
    },
    "content": {
        "description",
        "content",
        "details",
        "mo ta",
        "noi dung",
        "chi tiet",
    },
    "acceptance_criteria": {
        "acceptance criteria",
        "acceptance criterion",
        "criteria",
        "tieu chi",
        "tieu chi chap nhan",
        "dieu kien chap nhan",
    },
    "dependencies": {
        "dependency",
        "dependencies",
        "related requirement",
        "related requirements",
        "yeu cau lien quan",
        "phu thuoc",
    },
    "type": {"type", "loai", "loai yeu cau"},
    "priority": {"priority", "uu tien", "muc uu tien"},
    "risk": {"risk", "rui ro", "muc do rui ro"},
    "actors": {"actor", "actors", "tac nhan", "nguoi dung"},
    "business_rules": {"business rule", "business rules", "quy tac nghiep vu"},
    "tags": {"tag", "tags", "the"},
}
REQUIREMENT_TABLE_FIELD_BY_LABEL = {
    label: field for field, labels in REQUIREMENT_TABLE_FIELDS.items() for label in labels
}


def is_labeled_acceptance_criterion_line(line):
    return bool(
        ACCEPTANCE_CRITERION_LINE.match(line)
        or TABLE_ACCEPTANCE_CRITERION_LINE.match(line)
    )


def is_acceptance_criteria_table_header(line):
    cells = [cell.strip().casefold() for cell in line.strip().strip("|").split("|")]
    return len(cells) >= 2 and any(
        "acceptance" in cell
        or "criteria" in cell
        or "criterion" in cell
        or "tiêu chí" in cell
        or cell == "ac"
        for cell in cells
    )


def extract_labeled_acceptance_criteria(text):
    criteria = []
    position = 0
    pending = None
    for line in str(text or "").splitlines(keepends=True):
        content_line = line.rstrip("\r\n")
        match = ACCEPTANCE_CRITERION_LINE.match(content_line)
        table_match = None if match else TABLE_ACCEPTANCE_CRITERION_LINE.match(content_line)
        match = match or table_match
        if match:
            if pending:
                criteria.append(pending)
            pending = {
                "key": match.group(1).strip(),
                "content": match.group(2).strip(),
                "source_start": position,
                "source_end": position + len(line.rstrip("\r\n")),
            }
        elif pending and line[:1].isspace() and line.strip():
            pending["content"] = f"{pending['content']} {line.strip()}"
            pending["source_end"] = position + len(line.rstrip("\r\n"))
        elif pending:
            criteria.append(pending)
            pending = None
        position += len(line)
    if pending:
        criteria.append(pending)
    return criteria


def normalized_acceptance_criterion(value):
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    normalized = re.sub(
        r"^(?:AC|ACCEPTANCE[-_ ]?CRITERION)[-_ ]?\d+\s*[:.)\-–—]?\s*",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized.casefold()


def normalized_acceptance_criterion_key(value):
    match = re.fullmatch(r"\s*(AC|ACCEPTANCE[-_ ]?CRITERION)[-_ ]?(\d+)\s*", str(value or ""), re.IGNORECASE)
    return f"AC-{int(match.group(2))}" if match else str(value or "").strip().casefold()


def explicit_acceptance_criteria(document):
    text = source_document_text(document["normalized_content"])
    values = [item["content"] for item in extract_labeled_acceptance_criteria(text)]
    in_criteria_section = False
    pending = []

    def retain_pending():
        if pending:
            values.append(" ".join(pending).strip())
            pending.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if ACCEPTANCE_CRITERIA_SECTION.match(stripped):
            retain_pending()
            in_criteria_section = True
            continue
        if in_criteria_section and (
            stripped.startswith("#") or NUMBERED_UPPERCASE_SECTION.match(stripped)
        ):
            retain_pending()
            in_criteria_section = False
        if not in_criteria_section:
            continue
        if not stripped:
            retain_pending()
            continue
        labeled = ACCEPTANCE_CRITERION_LINE.match(stripped)
        if labeled:
            retain_pending()
            values.append(labeled.group(2).strip())
            continue
        bullet = re.match(r"^(?:[-*•]|\d+[.)])\s+(.+)$", stripped)
        if bullet:
            retain_pending()
            values.append(bullet.group(1).strip())
            continue
        pending.append(stripped)
    retain_pending()
    values.extend(
        source_document_text(criterion.get("content_doc", {}))
        for candidate in atomic_requirement_candidates(document)
        if any(
            reference.get("section") == "requirement_table_row"
            for reference in candidate.get("source_refs", [])
        )
        for criterion in candidate.get("acceptance_criteria", [])
    )
    return {
        normalized
        for value in values
        if (normalized := normalized_acceptance_criterion(value))
    }


def attach_labeled_acceptance_criteria(candidates, document):
    text = source_document_text(document["normalized_content"])
    criteria = extract_labeled_acceptance_criteria(text)
    if not candidates or not criteria:
        return candidates

    anchors = []
    for index, candidate in enumerate(candidates):
        positions = [
            reference.get("source_start")
            for reference in candidate.get("source_refs", [])
            if isinstance(reference.get("source_start"), int)
        ]
        if positions:
            anchors.append((index, positions))
    if not anchors:
        if len(candidates) != 1:
            return candidates
        anchors = [(0, [0])]

    for criterion in criteria:
        candidate_index = min(
            anchors,
            key=lambda item: min(
                abs(position - criterion["source_start"]) for position in item[1]
            ),
        )[0]
        source_text = text[criterion["source_start"] : criterion["source_end"]]
        criterion_value = {
            "key": criterion["key"],
            "content_doc": text_doc(criterion["content"]),
            "source_span": {
                "requirement_document_id": document["_id"],
                "content_hash": document["content_hash"],
                "source_version": document.get("source_version"),
                "source_start": criterion["source_start"],
                "source_end": criterion["source_end"],
                "source_text_hash": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
                "source_quote": source_text,
                "section": "acceptance_criteria",
                "format": document["format"],
            },
        }
        values = candidates[candidate_index].setdefault("acceptance_criteria", [])
        existing_keys = {
            normalized_acceptance_criterion_key(item.get("key")) for item in values
        }
        if normalized_acceptance_criterion_key(criterion_value["key"]) not in existing_keys:
            values.append(criterion_value)
        states = candidates[candidate_index].setdefault("section_states", {})
        states["acceptance_criteria"] = "provided"
    return candidates



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


def _normalized_requirement_table_label(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = value.replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _requirement_table_field(value):
    return REQUIREMENT_TABLE_FIELD_BY_LABEL.get(
        _normalized_requirement_table_label(value)
    )


def _markdown_table_cells(line):
    value = line.strip()
    if not value.startswith("|"):
        return []
    if value.endswith("|"):
        value = value[1:-1]
    else:
        value = value[1:]
    cells = []
    current = []
    escaped = False
    for character in value:
        if character == "|" and not escaped:
            cells.append("".join(current).replace("\\|", "|").replace("<br>", "\n").strip())
            current = []
        else:
            current.append(character)
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    cells.append("".join(current).replace("\\|", "|").replace("<br>", "\n").strip())
    return cells


def _requirement_table_list(value):
    return [
        item.strip(" \t\r\n-•")
        for item in re.split(r"[,;\n、]+", str(value or ""))
        if item.strip(" \t\r\n-•")
    ]


def _requirement_table_enum(field, value):
    normalized = _normalized_requirement_table_label(value)
    allowed = {
        "type": {
            "functional": "functional",
            "chuc nang": "functional",
            "non functional": "non_functional",
            "phi chuc nang": "non_functional",
            "business rule": "business_rule",
            "quy tac nghiep vu": "business_rule",
            "api": "api",
            "ui": "ui",
            "giao dien": "ui",
            "data": "data",
            "du lieu": "data",
            "permission": "permission",
            "phan quyen": "permission",
            "integration": "integration",
            "tich hop": "integration",
            "constraint": "constraint",
            "rang buoc": "constraint",
        },
        "priority": {
            "critical": "critical",
            "nghiem trong": "critical",
            "high": "high",
            "cao": "high",
            "medium": "medium",
            "trung binh": "medium",
            "low": "low",
            "thap": "low",
        },
        "risk": {
            "critical": "critical",
            "nghiem trong": "critical",
            "high": "high",
            "cao": "high",
            "medium": "medium",
            "trung binh": "medium",
            "low": "low",
            "thap": "low",
        },
    }
    return allowed.get(field, {}).get(normalized)


def _build_requirement_table_candidate(document, text, source_start, source_end, values):
    title = str(values.get("title") or "").strip()
    if len(title) < 2:
        return None
    source_quote = text[source_start:source_end].strip()
    source_start = text.find(source_quote, source_start, source_end)
    if source_start < 0:
        return None
    source_end = source_start + len(source_quote)
    source_ref = {
        "requirement_document_id": document["_id"],
        "content_hash": document["content_hash"],
        "source_version": document.get("source_version"),
        "source_start": source_start,
        "source_end": source_end,
        "source_text_hash": hashlib.sha256(source_quote.encode("utf-8")).hexdigest(),
        "source_quote": source_quote,
        "section": "requirement_table_row",
        "format": document["format"],
    }
    description = str(values.get("content") or title).strip()
    candidate = {
        "requirement_key": str(values.get("requirement_key") or "").strip() or None,
        "title": title[:300],
        "type": _requirement_table_enum("type", values.get("type")) or "functional",
        "priority": _requirement_table_enum("priority", values.get("priority")) or "medium",
        "risk": _requirement_table_enum("risk", values.get("risk")) or "medium",
        "content_doc": text_doc(description),
        "acceptance_criteria": [],
        "business_rules": _requirement_table_list(values.get("business_rules")),
        "actors": _requirement_table_list(values.get("actors")),
        "dependencies": _requirement_table_list(values.get("dependencies")),
        "tags": _requirement_table_list(values.get("tags")),
        "source_refs": [source_ref],
    }
    for index, criterion in enumerate(
        _requirement_table_list(values.get("acceptance_criteria")), 1
    ):
        candidate["acceptance_criteria"].append(
            {
                "key": f"AC-{index}",
                "content_doc": text_doc(criterion),
                "source_span": source_ref,
            }
        )
    return candidate


def _requirements_from_markdown_table(document, text, table_rows):
    parsed_rows = []
    for line_start, line_end, line in table_rows:
        if MARKDOWN_TABLE_SEPARATOR.match(line.strip()):
            continue
        cells = _markdown_table_cells(line)
        if cells:
            parsed_rows.append((line_start, line_end, cells))
    if not parsed_rows:
        return []

    header_fields = [_requirement_table_field(value) for value in parsed_rows[0][2]]
    if "title" in header_fields and any(field for field in header_fields if field != "title"):
        candidates = []
        for line_start, line_end, cells in parsed_rows[1:]:
            if len(cells) == len(header_fields) and all(
                _requirement_table_field(cell) == field
                for cell, field in zip(cells, header_fields)
            ):
                continue
            values = {
                field: cells[index]
                for index, field in enumerate(header_fields)
                if field and index < len(cells) and cells[index]
            }
            candidate = _build_requirement_table_candidate(
                document, text, line_start, line_end, values
            )
            if candidate:
                candidates.append(candidate)
        if candidates:
            return candidates

    values = {}
    candidate_ranges = []
    first_data_line = None
    last_data_line = None
    for line_start, line_end, cells in parsed_rows:
        if len(cells) < 2:
            continue
        field = _requirement_table_field(cells[0])
        if field == "title" and values.get("title"):
            candidate_ranges.append((first_data_line, last_data_line, values))
            values = {}
            first_data_line = None
            last_data_line = None
        if field:
            values[field] = cells[1]
            first_data_line = line_start if first_data_line is None else first_data_line
            last_data_line = line_end
            continue
        inferred_field = _requirement_table_field(cells[1])
        if not values.get("title") and inferred_field == "title":
            values["title"] = cells[0]
            first_data_line = line_start
            last_data_line = line_end
    if values.get("title") and first_data_line is not None and last_data_line is not None:
        candidate_ranges.append((first_data_line, last_data_line, values))
    return [
        candidate
        for start, end, table_values in candidate_ranges
        if start is not None and end is not None
        if (candidate := _build_requirement_table_candidate(document, text, start, end, table_values))
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
    lines = text.splitlines(keepends=True)

    def add_paragraph(start, end):
        raw = text[start:end].strip()
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if lines and all(is_labeled_acceptance_criterion_line(line) for line in lines):
            return
        if len(lines) == 1 and (
            MARKDOWN_TABLE_SEPARATOR.match(lines[0])
            or ("|" in lines[0] and is_acceptance_criteria_table_header(lines[0]))
        ):
            return
        if (
            len(lines) > 1
            and "|" in lines[0]
            and (
                is_acceptance_criteria_table_header(lines[0])
                or any(is_labeled_acceptance_criterion_line(line) for line in lines[1:])
            )
            and all(
                is_labeled_acceptance_criterion_line(line)
                or MARKDOWN_TABLE_SEPARATOR.match(line)
                for line in lines[1:]
            )
        ):
            return
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
    line_index = 0
    while line_index < len(lines):
        line = lines[line_index]
        line_start = position
        position += len(line)
        stripped = line.strip()
        if stripped.startswith("|"):
            if paragraph_start is not None:
                add_paragraph(paragraph_start, paragraph_end)
                paragraph_start = None
            table_rows = [(line_start, position, stripped)]
            line_index += 1
            while line_index < len(lines) and lines[line_index].strip().startswith("|"):
                table_line = lines[line_index]
                table_start = position
                position += len(table_line)
                table_rows.append((table_start, position, table_line.strip()))
                line_index += 1
            table_candidates = _requirements_from_markdown_table(document, text, table_rows)
            if table_candidates:
                candidates.extend(table_candidates)
                if len(candidates) > 500:
                    raise HTTPException(
                        status_code=413,
                        detail={"code": "IMPORT_CANDIDATE_LIMIT_EXCEEDED"},
                    )
            else:
                add_paragraph(table_rows[0][0], table_rows[-1][1])
            continue
        heading = re.fullmatch(r"(#{1,6})\s+(.+)", stripped)
        if heading or not stripped:
            if paragraph_start is not None:
                add_paragraph(paragraph_start, paragraph_end)
                paragraph_start = None
            if heading:
                sections = sections[: len(heading.group(1)) - 1]
                sections.append(heading.group(2).strip())
            line_index += 1
            continue
        if paragraph_start is None:
            paragraph_start = line_start
        paragraph_end = position
        line_index += 1
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

    def paragraph_text(paragraph):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t")).strip()
        if not text:
            return ""
        properties = paragraph.find(f"{namespace}pPr")
        style = properties.find(f"{namespace}pStyle") if properties is not None else None
        outline = properties.find(f"{namespace}outlineLvl") if properties is not None else None
        style_name = style.attrib.get(f"{namespace}val", "") if style is not None else ""
        match = re.search(r"Heading([1-6])$", style_name, re.IGNORECASE)
        level = int(match.group(1)) if match else None
        if outline is not None and level is None:
            level = min(int(outline.attrib.get(f"{namespace}val", "0")) + 1, 6)
        return f"{'#' * level} {text}" if level else text

    body = root.find(f".//{namespace}body")
    if body is None:
        return ""
    blocks = []
    for element in body:
        if element.tag == f"{namespace}p":
            text = paragraph_text(element)
            if text:
                blocks.append(text)
            continue
        if element.tag != f"{namespace}tbl":
            continue
        rows = []
        column_counts = []
        for row in element.findall(f"{namespace}tr"):
            cells = []
            for cell in row.findall(f"{namespace}tc"):
                cell_paragraphs = [
                    text
                    for paragraph in cell.findall(f"{namespace}p")
                    if (text := paragraph_text(paragraph))
                ]
                cells.append("<br>".join(cell_paragraphs).replace("|", "\\|"))
            if any(cells):
                rows.append("| " + " | ".join(cells) + " |")
                column_counts.append(len(cells))
        if rows:
            if len(rows) > 1 and column_counts[0] == column_counts[1]:
                separator = "|" + "|".join(" --- " for _ in range(column_counts[0])) + "|"
                rows.insert(1, separator)
            blocks.append("\n".join(rows))
    return "\n\n".join(blocks)


def extract_xlsx_csv(data):
    try:
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
                        reference = cell.attrib.get("r", "")
                        column = "".join(character for character in reference if character.isalpha())
                        if column:
                            position = 0
                            for character in column.upper():
                                position = position * 26 + ord(character) - ord("A") + 1
                            while len(values) < position - 1:
                                values.append("")
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
    except (zipfile.BadZipFile, KeyError, IndexError, ValueError, DefusedXmlException, ElementTree.ParseError) as error:
        raise HTTPException(status_code=422, detail={"code": "IMPORT_XLSX_INVALID"}) from error
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
