import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone as datetime_timezone
from zoneinfo import ZoneInfo



REPORT_RENDERER_VERSION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

SUPPORTED_NODES = {
    "doc", "text", "paragraph", "heading", "bulletList", "orderedList", "listItem",
    "taskList", "taskItem", "blockquote", "codeBlock", "hardBreak", "horizontalRule",
    "table", "tableRow", "tableCell", "tableHeader", "image",
}
SUPPORTED_MARKS = {"bold", "italic", "underline", "strike", "link", "textStyle", "highlight", "subscript", "superscript", "code"}


def validate_report_document(value):
    if not isinstance(value, dict) or value.get("type") != "doc":
        raise ValueError("REPORT_DOCUMENT_INVALID")
    if len(json.dumps(value, ensure_ascii=False).encode()) > 2_000_000:
        raise ValueError("REPORT_DOCUMENT_TOO_LARGE")
    nodes = 0

    def visit(node, depth):
        nonlocal nodes
        nodes += 1
        if depth > 40 or nodes > 20000 or not isinstance(node, dict):
            raise ValueError("REPORT_DOCUMENT_TOO_COMPLEX")
        if node.get("type") not in SUPPORTED_NODES:
            raise ValueError(f"REPORT_NODE_UNSUPPORTED:{node.get('type')}")
        for mark in node.get("marks", []):
            if not isinstance(mark, dict) or mark.get("type") not in SUPPORTED_MARKS:
                raise ValueError("REPORT_MARK_UNSUPPORTED")
        if node.get("type") == "text":
            import re
            if not isinstance(node.get("text"), str):
                raise ValueError("REPORT_DOCUMENT_TEXT_INVALID")
            if any(value.strip() not in REPORT_FIELDS for value in re.findall(r"\{\{([^{}]+)\}\}", node["text"])):
                raise ValueError("REPORT_TEMPLATE_FIELD_UNKNOWN")
        if node.get("type") == "image":
            import math
            attrs = node.get("attrs") or {}
            if not isinstance(attrs.get("asset_id"), str) or not attrs["asset_id"] or len(attrs["asset_id"]) > 200:
                raise ValueError("REPORT_IMAGE_UPLOAD_REQUIRED")
            width = attrs.get("width_cm", 14)
            if not isinstance(width, (int, float)) or isinstance(width, bool) or not math.isfinite(width) or not 0.5 <= width <= 16:
                raise ValueError("REPORT_IMAGE_WIDTH_INVALID")
        if node.get("type") == "heading":
            level = (node.get("attrs") or {}).get("level", 1)
            if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 6:
                raise ValueError("REPORT_HEADING_INVALID")
        for mark in node.get("marks", []):
            if mark.get("type") == "link":
                href = (mark.get("attrs") or {}).get("href", "")
                if not isinstance(href, str) or not href.startswith(("https://", "http://", "mailto:")):
                    raise ValueError("REPORT_LINK_INVALID")
        if node.get("type") == "table":
            if not node.get("content") or any(row.get("type") != "tableRow" for row in node["content"]):
                raise ValueError("REPORT_TABLE_INVALID")
            rows = node["content"]
            occupied = set()
            coverage = {}
            columns = None
            for y, row in enumerate(rows):
                x = 0
                if not row.get("content"):
                    raise ValueError("REPORT_TABLE_INVALID")
                for cell in row["content"]:
                    if cell.get("type") not in {"tableCell", "tableHeader"}:
                        raise ValueError("REPORT_TABLE_INVALID")
                    while (y, x) in occupied:
                        x += 1
                    attrs = cell.get("attrs") or {}
                    colspan, rowspan = attrs.get("colspan", 1), attrs.get("rowspan", 1)
                    if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in (colspan, rowspan)) or colspan > 40 or rowspan > len(rows) - y:
                        raise ValueError("REPORT_TABLE_SPAN_INVALID")
                    for yy in range(y, y + rowspan):
                        for xx in range(x, x + colspan):
                            if (yy, xx) in occupied:
                                raise ValueError("REPORT_TABLE_SPAN_INVALID")
                            occupied.add((yy, xx))
                            coverage.setdefault(yy, set()).add(xx)
                            if len(occupied) > 20000:
                                raise ValueError("REPORT_TABLE_TOO_LARGE")
                    x += colspan
                extent = max(coverage.get(y, set()), default=-1) + 1
                columns = columns or extent
                if extent != columns or columns > 40 or len(coverage.get(y, set())) != columns:
                    raise ValueError("REPORT_TABLE_SPAN_INVALID")
        children = node.get("content", [])
        if not isinstance(children, list):
            raise ValueError("REPORT_DOCUMENT_INVALID")
        for child in children:
            visit(child, depth + 1)

    visit(value, 0)
    return value


def document_text(node):
    if node.get("type") == "text":
        return str(node.get("text") or "")
    if node.get("type") == "hardBreak":
        return "\n"
    children = node.get("content") or []
    separator = "\n" if node.get("type") in {"doc", "table", "tableRow", "listItem"} else ""
    return separator.join(document_text(child) for child in children)


def paragraph(text="", heading=None):
    return {"type": "heading" if heading else "paragraph", **({"attrs": {"level": heading}} if heading else {}), "content": [{"type": "text", "text": text}] if text else []}


REPORT_FIELDS = {"report.title", "period.start", "period.end", "project.name", "owner.name", "metrics.work_items_total", "metrics.work_items_completed_at_capture", "metrics.work_items_changed_in_period", "snapshot.captured_at"}


def format_report_datetime(value, timezone_name, language):
    if not isinstance(value, datetime):
        try:
            value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return str(value or "")
    zone = ZoneInfo(timezone_name)
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime_timezone.utc)
    local = value.astimezone(zone)
    return local.strftime("%d/%m/%Y %H:%M" if language.lower().startswith("vi") else "%b %d, %Y %H:%M")


def resolve_report_fields(report):
    import copy
    import re
    value = copy.deepcopy(report["content_doc"])
    period = report["period"]
    timezone_name = period.get("timezone", "UTC")
    language = report.get("output_language", "en")
    template_id = (report.get("template_snapshot") or {}).get("template_id", "")
    if template_id.startswith("standard-"):
        redundant_placeholders = {"{{project.name}}", "{{period.start}} → {{period.end}}", "{{period.start}} — {{period.end}}", "{{owner.name}}"}
        value["content"] = [
            node for node in value.get("content", [])
            if not (node.get("type") == "paragraph" and document_text(node).strip() in redundant_placeholders)
        ]
    context = {
        "report.title": report["title"], "period.start": format_report_datetime(period["start_at"], timezone_name, language), "period.end": format_report_datetime(period["end_at"], timezone_name, language),
        "project.name": report.get("project_name", ""), "owner.name": report.get("owner_name", ""),
        "snapshot.captured_at": format_report_datetime(report["snapshot"]["captured_at"], timezone_name, language),
        **{f"metrics.{key}": str(item) for key, item in report["snapshot"]["metrics"].items()},
    }
    def replace(node):
        if node.get("type") == "text":
            def field(match):
                name = match.group(1).strip()
                if name not in context:
                    raise ValueError("REPORT_TEMPLATE_FIELD_UNKNOWN")
                return str(context[name])
            node["text"] = re.sub(r"\{\{([^{}]+)\}\}", field, str(node.get("text") or ""))
        for child in node.get("content", []):
            replace(child)
    replace(value)
    if template_id.startswith("standard-"):
        start_text = format_report_datetime(period["start_at"], timezone_name, language)
        end_text = format_report_datetime(period["end_at"], timezone_name, language)
        redundant_values = {
            str(report.get("project_name") or "").strip(),
            str(report.get("title") or "").strip(),
            str(report.get("owner_name") or "").strip(),
            f"{start_text} → {end_text}",
            f"{start_text} — {end_text}",
        } - {""}
        value["content"] = [
            node for node in value.get("content", [])
            if not (node.get("type") == "paragraph" and document_text(node).strip() in redundant_values)
        ]
        vi = str(report.get("output_language", "vi")).lower().startswith("vi")
        content_with_sections = []
        for node in value["content"]:
            text = document_text(node).lower()
            is_metrics = node.get("type") == "table" and (("công việc" in text and ("hoàn thành khi chốt" in text or "hoàn tất tại thời điểm chốt" in text) and "thay đổi trong kỳ" in text) or ("work item" in text and "changed" in text and "complete" in text))
            if is_metrics:
                node.setdefault("attrs", {})["report_metrics"] = True
                previous = content_with_sections[-1] if content_with_sections else {}
                if previous.get("type") != "heading":
                    content_with_sections.append({"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "SỐ LIỆU CÔNG VIỆC" if vi else "WORK ITEM METRICS"}]})
            content_with_sections.append(node)
        value["content"] = content_with_sections
        kind = report.get("kind", "PROJECT")
        status = report.get("status", "DRAFT")
        labels = {
            "vi": {
                "info": "THÔNG TIN BÁO CÁO", "project": "Dự án", "project_code": "Mã dự án",
                "report_code": "Mã báo cáo", "kind": "Loại báo cáo", "period": "Kỳ báo cáo",
                "author": "Người thực hiện", "reviewer": "Người xác nhận",
                "created": "Ngày giờ lập", "exported": "Ngày giờ xuất", "due": "Hạn báo cáo",
                "version": "Phiên bản", "state": "Trạng thái",
                "kinds": {"PERSONAL": "Cá nhân", "TEAM": "Nhóm", "PROJECT": "Dự án"},
                "states": {"DRAFT": "Bản nháp", "IN_REVIEW": "Đang rà soát", "APPROVED": "Đã duyệt", "PUBLISHED": "Đã phát hành", "ARCHIVED": "Đã lưu trữ"},
            },
            "en": {
                "info": "REPORT DETAILS", "project": "Project", "project_code": "Project code",
                "report_code": "Report ID", "kind": "Report type", "period": "Reporting period",
                "author": "Prepared by", "reviewer": "Confirmed by",
                "created": "Created at", "exported": "Exported at", "due": "Due date",
                "version": "Version", "state": "Status",
                "kinds": {"PERSONAL": "Personal", "TEAM": "Team", "PROJECT": "Project"},
                "states": {"DRAFT": "Draft", "IN_REVIEW": "In review", "APPROVED": "Approved", "PUBLISHED": "Published", "ARCHIVED": "Archived"},
            },
        }["vi" if vi else "en"]
        rows = [
            (labels["project"], report.get("project_name", "")),
            (labels["project_code"], report.get("project_key") or report.get("project_id", "")),
            (labels["report_code"], report.get("_id", "")),
            (labels["kind"], labels["kinds"].get(kind, kind)),
            (labels["period"], f"{format_report_datetime(period['start_at'], timezone_name, language)} - {format_report_datetime(period['end_at'], timezone_name, language)}"),
            (labels["author"], report.get("owner_name", "")),
            (labels["reviewer"], report.get("reviewer_name", "")),
            (labels["created"], format_report_datetime(report.get("created_at"), timezone_name, language)),
            (labels["due"], format_report_datetime(report.get("due_at"), timezone_name, language) if report.get("due_at") else "—"),
            (labels["version"], report.get("version", "—")),
            (labels["state"], labels["states"].get(status, status)),
        ]
        if report.get("exported_at"):
            rows.insert(8, (labels["exported"], format_report_datetime(report["exported_at"], timezone_name, language)))
        metadata_table = {
            "type": "table",
            "attrs": {"report_metadata": True},
            "content": [
                {"type": "tableRow", "content": [
                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": label}]}]},
                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(item or "—")}]}]},
                ]}
                for label, item in rows
            ],
        }
        value.setdefault("content", [])
        value["content"] = [
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": labels["info"]}]},
            metadata_table,
            *value["content"],
        ]
    signature_labels = {
        "vi": {"signatures": "XÁC NHẬN", "confirmer": "NGƯỜI XÁC NHẬN", "performer": "NGƯỜI THỰC HIỆN", "sign": "(Ký, ghi rõ họ tên)", "unassigned": "Chưa phân công"},
        "en": {"signatures": "CONFIRMATION", "confirmer": "CONFIRMED BY", "performer": "PREPARED BY", "sign": "(Signature and full name)"},
    }["vi" if str(report.get("output_language", "vi")).lower().startswith("vi") else "en"]
    def marked(text, mark="bold"):
        return {"type": "text", "text": text, "marks": [{"type": mark}]}
    def signature_cell(label, name):
        return {"type": "tableCell", "content": [
            {"type": "paragraph", "attrs": {"textAlign": "center"}, "content": [marked(label)]},
            {"type": "paragraph", "attrs": {"textAlign": "center"}, "content": [{"type": "text", "text": signature_labels["sign"]}]},
            {"type": "paragraph", "content": []},
            {"type": "paragraph", "content": []},
            {"type": "paragraph", "attrs": {"textAlign": "center"}, "content": [{"type": "text", "text": str(name or signature_labels.get("unassigned", "Unassigned"))}]},
        ]}
    roman = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
    value["content"].append({"type": "table", "attrs": {"report_signatures": True}, "content": [
        {"type": "tableRow", "content": [
            signature_cell(signature_labels["confirmer"], report.get("reviewer_name")),
            signature_cell(signature_labels["performer"], report.get("owner_name")),
        ]}
    ]})
    section_index = 0
    for node in value["content"]:
        if template_id.startswith("standard-") and node.get("type") == "heading" and int((node.get("attrs") or {}).get("level", 1)) == 2:
            import re
            parts = list(node.get("content") or [])
            first_text = next((index for index, part in enumerate(parts) if part.get("type") == "text"), None)
            text = str(parts[first_text].get("text") or "") if first_text is not None else ""
            text = re.sub(r"^(?:[IVXLCDM]+|\d+)\.\s+", "", text)
            number = roman[min(section_index, len(roman) - 1)]
            if first_text is None:
                parts.insert(0, {"type": "text", "text": f"{number}. "})
            else:
                parts[first_text] = {**parts[first_text], "text": f"{number}. {text}"}
            node["content"] = parts
            section_index += 1
    return value


def export_report_docx(report, assets=None, base_docx=None):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    content = validate_report_document(resolve_report_fields(report))
    doc = Document(io.BytesIO(base_docx)) if base_docx else Document()
    if base_docx:
        for child in list(doc.element.body):
            if child.tag != qn("w:sectPr"):
                doc.element.body.remove(child)
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = section.right_margin = Cm(2)
    section.left_margin = Cm(3)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(1.5)
    section.different_first_page_header_footer = True
    for name in ["Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4", "Heading 5", "Heading 6", "List Bullet", "List Number", "Caption", "Header", "Footer"]:
        style = doc.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(16 if name == "Title" else 14)
        style.font.color.rgb = RGBColor(0, 0, 0)
        if name == "Title":
            style.font.bold = True
        style.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.element.get_or_add_rPr().rFonts.set(qn("w:cs"), "Times New Roman")
        fonts = style.element.get_or_add_rPr().rFonts
        for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "csTheme"):
            fonts.attrib.pop(qn(f"w:{attribute}"), None)
        for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn(f"w:{attribute}"), "Times New Roman")
        properties = style.element.find(qn("w:pPr"))
        if properties is not None:
            for border in list(properties.findall(qn("w:pBdr"))):
                properties.remove(border)
        style.paragraph_format.space_before = Pt(6)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.line_spacing = 1.15
        if name == "Normal":
            style.paragraph_format.first_line_indent = Cm(1.27)
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            style.paragraph_format.first_line_indent = Cm(0)
        if name.startswith("Heading"):
            style.font.bold = True
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.space_before = Pt(14)
            style.paragraph_format.space_after = Pt(6)
            style.paragraph_format.left_indent = Cm(0)
            style.paragraph_format.right_indent = Cm(0)
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header = section.first_page_header
    spacer = header.paragraphs[0]
    spacer.paragraph_format.first_line_indent = Cm(0)
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(0)
    spacer.paragraph_format.line_spacing = Pt(1)
    spacer.paragraph_format.keep_with_next = True
    table = header.add_table(rows=1, cols=2, width=Cm(16))
    table.autofit = False
    table.columns[0].width = Cm(4.2)
    table.columns[1].width = Cm(11.8)
    table.cell(0, 0).width = Cm(4.2)
    table.cell(0, 1).width = Cm(11.8)
    for cell_index in (0, 1):
        cell = table.cell(0, cell_index)
        cell.vertical_alignment = 1
        properties = cell._tc.get_or_add_tcPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "FFFFFF")
        properties.append(shading)
        borders = OxmlElement("w:tcBorders")
        for edge in ("top", "left", "bottom", "right"):
            border = OxmlElement(f"w:{edge}")
            border.set(qn("w:val"), "single")
            border.set(qn("w:sz"), "5")
            border.set(qn("w:color"), "FFFFFF")
            borders.append(border)
        properties.append(borders)
    table_borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "nil")
        table_borders.append(border)
    table._tbl.tblPr.append(table_borders)
    logo_paragraph = table.cell(0, 0).paragraphs[0]
    logo_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo_paragraph.paragraph_format.first_line_indent = Cm(0)
    logo_paragraph.paragraph_format.space_before = Pt(0)
    logo_paragraph.paragraph_format.space_after = Pt(0)
    brand_logo = Path(__file__).resolve().parents[3] / "assets" / "veriq-logo.png"
    if brand_logo.is_file():
        logo_paragraph.add_run().add_picture(str(brand_logo), width=Cm(3.7))
        from PIL import Image
        with Image.open(brand_logo) as original:
            watermark = original.convert("RGBA")
            watermark.putalpha(watermark.getchannel("A").point(lambda value: round(value * 0.09)))
            watermark_bytes = io.BytesIO()
            watermark.save(watermark_bytes, format="PNG")
        for watermark_header in (section.first_page_header, section.header):
            watermark_bytes.seek(0)
            shape = watermark_header.paragraphs[0].add_run().add_picture(watermark_bytes, width=Cm(12))
            inline_shape = shape._inline
            anchor = OxmlElement("wp:anchor")
            for key, value in {"distT": "0", "distB": "0", "distL": "0", "distR": "0", "simplePos": "0", "relativeHeight": "0", "behindDoc": "1", "locked": "0", "layoutInCell": "1", "allowOverlap": "1"}.items():
                anchor.set(key, value)
            simple = OxmlElement("wp:simplePos")
            simple.set("x", "0")
            simple.set("y", "0")
            anchor.append(simple)
            for axis in ("H", "V"):
                position = OxmlElement(f"wp:position{axis}")
                position.set("relativeFrom", "page")
                align = OxmlElement("wp:align")
                align.text = "center"
                position.append(align)
                anchor.append(position)
            anchor.append(inline_shape.find(qn("wp:extent")))
            effect = OxmlElement("wp:effectExtent")
            for edge in ("l", "t", "r", "b"):
                effect.set(edge, "0")
            anchor.append(effect)
            anchor.append(OxmlElement("wp:wrapNone"))
            anchor.append(inline_shape.find(qn("wp:docPr")))
            anchor.append(inline_shape.find(qn("wp:cNvGraphicFramePr")))
            anchor.append(inline_shape.find(qn("a:graphic")))
            inline_shape.getparent().replace(inline_shape, anchor)
    title_paragraph = table.cell(0, 1).paragraphs[0]
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_paragraph.paragraph_format.first_line_indent = Cm(0)
    title_paragraph.paragraph_format.space_before = Pt(0)
    title_paragraph.paragraph_format.space_after = Pt(0)
    document_titles = ({"PERSONAL": "BÁO CÁO CÁ NHÂN", "TEAM": "BÁO CÁO NHÓM", "PROJECT": "BÁO CÁO TIẾN ĐỘ CÔNG VIỆC"} if str(report.get("output_language", "vi")).lower().startswith("vi") else {"PERSONAL": "PERSONAL REPORT", "TEAM": "TEAM REPORT", "PROJECT": "WORK PROGRESS REPORT"})
    title_run = title_paragraph.add_run(document_titles.get(report.get("kind"), str(report.get("title") or "").upper()))
    title_run.bold = True
    title_run.font.size = Pt(20)
    title_run.font.name = "Times New Roman"
    for footer_part in (section.first_page_footer, section.footer):
        footer = footer_part.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        footer.paragraph_format.first_line_indent = Cm(0)
        footer.paragraph_format.space_before = Pt(4)
        footer.paragraph_format.space_after = Pt(0)
        footer.add_run("Trang " if str(report.get("output_language", "vi")).lower().startswith("vi") else "Page ")
        page = OxmlElement("w:fldSimple")
        page.set(qn("w:instr"), "PAGE")
        footer._p.append(page)
        footer.add_run(" / " if str(report.get("output_language", "vi")).lower().startswith("vi") else " of ")
        pages = OxmlElement("w:fldSimple")
        pages.set(qn("w:instr"), "NUMPAGES")
        footer._p.append(pages)
    alignments = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT, "justify": WD_ALIGN_PARAGRAPH.JUSTIFY}

    def inline(parent, node):
        if node.get("type") == "hardBreak":
            parent.add_run().add_break()
        elif node.get("type") == "text":
            run = parent.add_run(str(node.get("text") or ""))
            marks = {mark["type"]: mark.get("attrs") or {} for mark in node.get("marks", [])}
            run.bold = "bold" in marks
            run.italic = "italic" in marks
            run.underline = "underline" in marks
            run.font.strike = "strike" in marks
            if "highlight" in marks:
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            run.font.subscript = "subscript" in marks
            run.font.superscript = "superscript" in marks
            if "link" in marks:
                href = str(marks["link"].get("href") or "")
                if href.startswith(("https://", "http://", "mailto:")):
                    relationship = parent.part.relate_to(href, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
                    link = OxmlElement("w:hyperlink")
                    link.set(qn("r:id"), relationship)
                    link.append(run._r)
                    parent._p.append(link)
        else:
            for child in node.get("content", []):
                inline(parent, child)

    def list_numbering(ordered, start, depth):
        numbering = doc.part.numbering_part.element
        abstract_id = max((int(item.get(qn("w:abstractNumId"))) for item in numbering.findall(qn("w:abstractNum"))), default=-1) + 1
        number_id = max((int(item.get(qn("w:numId"))) for item in numbering.findall(qn("w:num"))), default=0) + 1
        abstract = OxmlElement("w:abstractNum")
        abstract.set(qn("w:abstractNumId"), str(abstract_id))
        level = OxmlElement("w:lvl")
        level.set(qn("w:ilvl"), "0")
        for name, value in (("start", str(start)), ("numFmt", "decimal" if ordered else "bullet"), ("lvlText", "%1." if ordered else "•")):
            child = OxmlElement(f"w:{name}")
            child.set(qn("w:val"), value)
            level.append(child)
        properties = OxmlElement("w:pPr")
        indent = OxmlElement("w:ind")
        indent.set(qn("w:left"), str(720 + depth * 360))
        indent.set(qn("w:hanging"), "360")
        properties.append(indent)
        level.append(properties)
        abstract.append(level)
        numbering.append(abstract)
        number = OxmlElement("w:num")
        number.set(qn("w:numId"), str(number_id))
        reference = OxmlElement("w:abstractNumId")
        reference.set(qn("w:val"), str(abstract_id))
        number.append(reference)
        numbering.append(number)
        return number_id

    def render(container, node, list_style=None, depth=0):
        kind = node["type"]
        attrs = node.get("attrs") or {}
        children = node.get("content") or []
        if kind in {"paragraph", "heading", "codeBlock"}:
            style = f"Heading {min(6, max(1, int(attrs.get('level', 1))))}" if kind == "heading" else None
            p = container.add_paragraph(style=style)
            if list_style or container is not doc:
                p.paragraph_format.first_line_indent = Cm(0)
            if list_style:
                number = p._p.get_or_add_pPr().get_or_add_numPr()
                number.get_or_add_ilvl().val = 0
                number.get_or_add_numId().val = list_style
            if attrs.get("textAlign") in alignments:
                p.alignment = alignments[attrs["textAlign"]]
            for child in children:
                inline(p, child)
            if kind == "heading":
                for run in p.runs:
                    run.bold = True
                    if (report.get("template_snapshot") or {}).get("template_id", "").startswith("standard-") and int(attrs.get("level", 1)) == 2:
                        run.text = run.text.upper()
        elif kind in {"bulletList", "taskList", "orderedList"}:
            import copy
            number_id = list_numbering(kind == "orderedList", max(1, int(attrs.get("start", 1))), depth)
            for child in children:
                child = copy.deepcopy(child)
                if kind == "taskList":
                    prefix = "[x] " if (child.get("attrs") or {}).get("checked") else "[ ] "
                    first = next((item for item in child.get("content", []) if item.get("type") == "paragraph"), None)
                    if first is not None:
                        first.setdefault("content", []).insert(0, {"type": "text", "text": prefix})
                render(container, child, number_id, depth + 1)
        elif kind in {"doc", "listItem", "taskItem", "blockquote"}:
            for index, child in enumerate(children):
                render(container, child, list_style if index == 0 or kind in {"doc", "blockquote"} else None, depth)
        elif kind == "table":
            columns = max(sum(int((cell.get("attrs") or {}).get("colspan", 1)) for cell in row.get("content", [])) for row in children)
            if columns > 40:
                raise ValueError("REPORT_TABLE_TOO_WIDE")
            if attrs.get("report_signatures"):
                gap = container.add_paragraph()
                gap.paragraph_format.space_before = Pt(0)
                gap.paragraph_format.space_after = Pt(0)
                gap.paragraph_format.line_spacing = Pt(18)
                gap.paragraph_format.keep_with_next = True
            table = container.add_table(rows=len(children), cols=columns)
            table.style = "Normal Table" if attrs.get("report_signatures") else "Table Grid"
            if attrs.get("report_metadata") or attrs.get("report_metrics"):
                indent = OxmlElement("w:tblInd")
                indent.set(qn("w:w"), "108")
                indent.set(qn("w:type"), "dxa")
                table._tbl.tblPr.append(indent)
            if attrs.get("report_signatures"):
                table_borders = OxmlElement("w:tblBorders")
                for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
                    border = OxmlElement(f"w:{edge}")
                    border.set(qn("w:val"), "nil")
                    table_borders.append(border)
                table._tbl.tblPr.append(table_borders)
            if all(int((cell.get("attrs") or {}).get("colspan", 1)) == 1 for cell in children[0].get("content", [])):
                import math
                widths = []
                if attrs.get("report_metadata") and columns == 2:
                    widths = [4.0, 12.0]
                elif attrs.get("report_signatures") and columns == 2:
                    widths = [7.0, 9.0]
                elif attrs.get("report_metrics") and columns == 3:
                    widths = [1.0, 1.0, 1.0]
                for column in (range(columns) if not widths else []):
                    explicit = ((children[0]["content"][column].get("attrs") or {}).get("colwidth") or [None])[0]
                    if explicit:
                        widths.append(float(explicit))
                    else:
                        maximum = max((len(document_text(row.get("content", [])[column])) for row in children[:20] if len(row.get("content", [])) > column), default=10)
                        widths.append(max(2, math.sqrt(maximum)))
                table.autofit = False
                parent_width = getattr(container, "width", None)
                available_width = min(16, parent_width.cm) if parent_width is not None else 16
                for column, width in enumerate(widths):
                    table.columns[column].width = Cm(available_width * width / sum(widths))
                    for cell in table.columns[column].cells:
                        cell.width = Cm(available_width * width / sum(widths))
            occupied = set()
            for y, row in enumerate(children):
                x = 0
                for cell_node in row.get("content", []):
                    while (y, x) in occupied:
                        x += 1
                    a = cell_node.get("attrs") or {}
                    colspan, rowspan = int(a.get("colspan", 1)), int(a.get("rowspan", 1))
                    if colspan < 1 or rowspan < 1 or x + colspan > columns or y + rowspan > len(children):
                        raise ValueError("REPORT_TABLE_SPAN_INVALID")
                    cell = table.cell(y, x)
                    if colspan > 1 or rowspan > 1:
                        cell = cell.merge(table.cell(y + rowspan - 1, x + colspan - 1))
                    for yy in range(y, y + rowspan):
                        for xx in range(x, x + colspan):
                            occupied.add((yy, xx))
                    for child in cell_node.get("content", []):
                        render(cell, child)
                    if cell_node.get("type") == "tableHeader":
                        for p in cell.paragraphs:
                            for run in p.runs:
                                run.bold = True
                    if len(cell.paragraphs) > 1 and not cell.paragraphs[0].text:
                        cell._tc.remove(cell.paragraphs[0]._p)
                    x += colspan
                if y == 0 and all(cell.get("type") == "tableHeader" for cell in row.get("content", [])):
                    repeat = OxmlElement("w:tblHeader")
                    table.rows[y]._tr.get_or_add_trPr().append(repeat)
        elif kind == "image":
            source = (assets or {}).get(attrs.get("asset_id"))
            if not source:
                raise ValueError("REPORT_IMAGE_UNAVAILABLE")
            p = container.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)
            available_width = getattr(container, "width", None)
            maximum_width = available_width.cm if available_width is not None else 16
            p.add_run().add_picture(io.BytesIO(source), width=Cm(min(maximum_width, 16, float(attrs.get("width_cm", 14)))))
            if attrs.get("alt"):
                container.add_paragraph(str(attrs["alt"]), "Caption")
        elif kind == "horizontalRule":
            container.add_paragraph()
        else:
            raise ValueError(f"REPORT_NODE_UNSUPPORTED:{kind}")

    render(doc, content)
    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()


def convert_report_pdf(docx_bytes):
    binary = os.environ.get("REPORT_LIBREOFFICE_BIN") or shutil.which("libreoffice") or shutil.which("soffice")
    if not binary:
        raise RuntimeError("REPORT_PDF_CONVERTER_UNAVAILABLE")
    match = subprocess.run(["fc-match", "-f", "%{family}", "Times New Roman"], capture_output=True, text=True, timeout=10, check=True)
    if "times new roman" not in match.stdout.lower():
        raise RuntimeError("REPORT_TIMES_NEW_ROMAN_MISSING")
    with tempfile.TemporaryDirectory(prefix="veriq-report-") as directory:
        root = Path(directory)
        source = root / "report.docx"
        source.write_bytes(docx_bytes)
        command = [str(binary), f"-env:UserInstallation={(root / 'profile').as_uri()}", "--headless", "--norestore", "--nodefault", "--convert-to", "pdf", "--outdir", str(root), str(source)]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, "HOME": str(root)}, start_new_session=True) as process:
            try:
                process.communicate(timeout=120)
            except subprocess.TimeoutExpired as error:
                import signal
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise RuntimeError("REPORT_PDF_CONVERSION_TIMEOUT") from error
            return_code = process.returncode
        target = root / "report.pdf"
        if return_code or not target.exists() or target.stat().st_size == 0:
            raise RuntimeError("REPORT_PDF_CONVERSION_FAILED")
        return target.read_bytes()


def legacy_report_document(report, rows, title):
    content = []
    for label, value in rows:
        content.append(paragraph(label, 2))
        content.extend(paragraph(line) for line in str(value or "").split("\n"))
    period = report.get("reporting_period") or {}
    return {
        "title": title,
        "period": {"start_at": period.get("start_at", report.get("reporting_period_start", "")), "end_at": period.get("end_at", report.get("reporting_period_end", ""))},
        "snapshot": {"captured_at": (report.get("snapshot_basis") or {}).get("snapshot_at") or report.get("created_at", ""), "metrics": {}},
        "content_doc": {"type": "doc", "content": content},
    }
