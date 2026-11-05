import io
from datetime import timedelta
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException

from src.clients.storage import storage_client
from src.core.common import get_project, new_id, now
from src.modules.execution.services.report_document import paragraph, validate_report_document
from src.modules.execution.services.reporting import fail
from src.repositories.reporting import reporting_repository as repository


def parse_docx_template(data):
    from docx import Document
    from docx.opc.exceptions import OpcError
    from lxml.etree import XMLSyntaxError
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    warnings = set()
    embedded_images = {}
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 3000 or sum(item.file_size for item in entries) > 64 * 1024 * 1024:
                fail("REPORT_TEMPLATE_ARCHIVE_TOO_LARGE", 422)
            if any("vbaProject" in item.filename or "embeddings/" in item.filename for item in entries):
                fail("REPORT_TEMPLATE_ACTIVE_CONTENT_FORBIDDEN", 422)
            if any(item.filename.startswith("/") or ".." in item.filename.split("/") for item in entries):
                fail("REPORT_TEMPLATE_ARCHIVE_INVALID", 422)
            from defusedxml import ElementTree
            for entry in entries:
                if entry.filename.endswith(".rels"):
                    root = ElementTree.fromstring(archive.read(entry))
                    if any(rel.get("TargetMode") == "External" and not rel.get("Type", "").endswith("/hyperlink") for rel in root):
                        fail("REPORT_TEMPLATE_EXTERNAL_RESOURCE_FORBIDDEN", 422)
                elif entry.filename.endswith(".xml"):
                    raw = archive.read(entry)
                    if any(token in raw.upper() for token in (b"INCLUDEPICTURE", b"INCLUDETEXT", b"DDEAUTO", b"ALTCHUNK")):
                        fail("REPORT_TEMPLATE_ACTIVE_CONTENT_FORBIDDEN", 422)
        doc = Document(io.BytesIO(data))
    except (BadZipFile, KeyError, ValueError, OpcError, XMLSyntaxError) as error:
        raise HTTPException(status_code=422, detail={"code": "REPORT_TEMPLATE_INVALID"}) from error
    if doc.settings.element.find(qn("w:documentProtection")) is not None:
        fail("REPORT_TEMPLATE_PROTECTED", 422)
    if doc.element.xpath(".//w:ins | .//w:del"):
        fail("REPORT_TEMPLATE_TRACKED_CHANGES_UNRESOLVED", 422)
    if doc.element.xpath(".//w:pict"):
        warnings.add("IMAGES_REQUIRE_REINSERTION")
    if doc.element.xpath(".//w:txbxContent"):
        warnings.add("TEXTBOX_LAYOUT_REQUIRES_REVIEW")
    if len(doc.sections) > 1:
        warnings.add("MULTIPLE_SECTIONS_NORMALIZED_TO_A4")
    if any(relation.is_external for relation in doc.part.rels.values()):
        warnings.add("EXTERNAL_REFERENCES_NOT_FETCHED")

    def convert_paragraph(p):
        content = []
        for item in p.iter_inner_content():
            for run in getattr(item, "runs", [item]):
                marks = [{"type": name} for name, enabled in (("bold", run.bold), ("italic", run.italic), ("underline", run.underline), ("strike", run.font.strike)) if enabled]
                href = getattr(item, "url", "")
                if href.startswith(("https://", "http://", "mailto:")):
                    marks.append({"type": "link", "attrs": {"href": href}})
                lines = run.text.split("\n")
                for index, text in enumerate(lines):
                    if index:
                        content.append({"type": "hardBreak"})
                    if text:
                        content.append({"type": "text", "text": text, **({"marks": marks} if marks else {})})
        if not content and p.text:
            content = [{"type": "text", "text": p.text}]
        style = p.style.name if p.style is not None else ""
        level = int(style[-1]) if style.startswith("Heading ") and style[-1].isdigit() else 1 if style == "Title" else None
        attrs = {}
        if level:
            attrs["level"] = min(level, 6)
        alignment = {0: "left", 1: "center", 2: "right", 3: "justify"}.get(p.alignment if p.alignment is not None else p.style.paragraph_format.alignment if p.style is not None else None)
        if alignment:
            attrs["textAlign"] = alignment
        node = {"type": "heading" if level else "paragraph", "content": content, **({"attrs": attrs} if attrs else {})}
        if p._p.xpath("./w:pPr/w:numPr") or style.startswith("List"):
            warnings.add("LIST_NUMBERING_REQUIRES_REVIEW")
            node = {"type": "orderedList" if "Number" in style else "bulletList", "content": [{"type": "listItem", "content": [node]}]}
        return node

    def paragraph_images(p):
        result = []
        for blip in p._p.xpath(".//a:blip"):
            relationship = blip.get(qn("r:embed"))
            part = doc.part.related_parts.get(relationship)
            if not part or part.content_type not in {"image/png", "image/jpeg"}:
                warnings.add("IMAGES_REQUIRE_REINSERTION")
                continue
            identifier = f"import:{relationship}"
            embedded_images[identifier] = part.blob
            result.append({"type": "image", "attrs": {"asset_id": identifier, "alt": "", "width_cm": 14}})
            if p.text.strip():
                warnings.add("INLINE_IMAGES_MOVED_TO_BLOCK")
        return result

    content = []
    for element in doc.element.body:
        if element.tag == qn("w:p"):
            item = Paragraph(element, doc)
            content.append(convert_paragraph(item))
            content.extend(paragraph_images(item))
        elif element.tag == qn("w:tbl"):
            table = Table(element, doc)
            rows, spans = [], {}
            for tr in table._tbl.tr_lst:
                cells, column = [], 0
                for tc in tr.tc_lst:
                    grid = tc.tcPr.gridSpan if tc.tcPr is not None else None
                    width = int(grid.val) if grid is not None else 1
                    merge = tc.tcPr.vMerge if tc.tcPr is not None else None
                    if merge is not None and merge.val == "continue" and column in spans:
                        spans[column]["attrs"]["rowspan"] += 1
                    else:
                        cell = {"type": "tableCell", "attrs": {"colspan": width, "rowspan": 1}, "content": [node for p in tc.p_lst for node in [convert_paragraph(Paragraph(p, doc)), *paragraph_images(Paragraph(p, doc))]] or [paragraph()]}
                        cells.append(cell)
                        if merge is not None:
                            spans[column] = cell
                        else:
                            spans.pop(column, None)
                    column += width
                rows.append({"type": "tableRow", "content": cells})
            content.append({"type": "table", "content": rows})
    value = {"type": "doc", "content": content or [paragraph()]}
    validate_report_document(value)
    return value, sorted(warnings), embedded_images


async def preview_template(project_id, filename, data, user):
    await get_project(project_id, user, "workreport.manage")
    if not filename.lower().endswith(".docx") or not data or len(data) > 25 * 1024 * 1024:
        fail("REPORT_TEMPLATE_FILE_INVALID", 422)
    import asyncio
    content, warnings, embedded_images = await asyncio.to_thread(parse_docx_template, data)
    from src.modules.execution.services.report_assets import upload_image, normalize_image_urls
    replacements = {}
    for placeholder, source in embedded_images.items():
        asset = await upload_image(project_id, source, user)
        replacements[placeholder] = asset["_id"]
    def replace_images(node):
        if node.get("type") == "image":
            node["attrs"]["asset_id"] = replacements[node["attrs"]["asset_id"]]
        for child in node.get("content", []):
            replace_images(child)
    replace_images(content)
    content = normalize_image_urls(content, project_id)
    preview_id = new_id("RTPREV")
    stored = await storage_client.store_report_asset(project_id, preview_id, "template.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", data)
    value = {"_id": preview_id, "project_id": project_id, "created_by": user.id, "filename": filename, "content_doc": content, "warnings": warnings, "original_file": stored, "created_at": now(), "updated_at": now(), "expires_at": now() + timedelta(days=7)}
    await repository.insert("report_template_previews", value)
    return {key: value[key] for key in ("_id", "filename", "content_doc", "warnings", "expires_at")}
