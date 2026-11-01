import csv
import io
import json
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile






def display(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def completion_rows(report):
    rows = [
        ("Mã báo cáo", report.get("completion_key") or report.get("_id")),
        ("Dự án", report.get("project_id")),
        ("Kế hoạch kiểm thử", report.get("test_plan_id")),
        ("Chiến lược kiểm thử", report.get("strategy_version_id")),
        ("Cách tiếp cận kiểm thử", report.get("strategy_approach_snapshot")),
        ("Bản phát hành", report.get("release_id")),
        ("Các bản dựng", report.get("build_ids", [report.get("build_id")])),
        ("Ảnh chụp cuối", report.get("final_snapshot_id") or report.get("monitoring_snapshot_id")),
        ("Trạng thái", report.get("status")),
        ("Khuyến nghị", report.get("recommendation")),
        ("Tóm tắt điều hành", report.get("executive_summary")),
        ("Tổng kết đóng kiểm thử", report.get("closure_summary")),
        ("Tóm tắt thực thi", report.get("execution_summary")),
        ("Tóm tắt độ phủ", report.get("coverage_summary")),
        ("Tóm tắt lỗi", report.get("defect_summary")),
        ("Tóm tắt bảo trì", report.get("maintenance_summary")),
        ("Phạm vi chưa thực thi", report.get("unexecuted_scope", [])),
        ("Hạng mục chưa giải quyết", report.get("unresolved_items", [])),
        ("Rủi ro còn lại", report.get("residual_risks", [])),
        (
            "Đánh giá tiêu chí thoát",
            report.get("exit_criteria_evaluations", report.get("exit_criteria_evaluation", [])),
        ),
        ("Sai lệch", report.get("deviations", [])),
        ("Bàn giao tài sản kiểm thử", report.get("testware_handover", [])),
        ("Tài sản lưu trữ", report.get("archived_artifacts", [])),
        ("Đóng môi trường", report.get("environment_closure", [])),
        ("Bài học kinh nghiệm", report.get("lessons_learned", [])),
        ("Hành động cải tiến", report.get("improvement_actions", [])),
        ("Xác nhận", report.get("sign_offs", [])),
        ("Dấu vân tay đã phê duyệt", report.get("approved_snapshot_hash")),
    ]
    return [(label, display(value)) for label, value in rows]


def export_csv(report):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Trường", "Giá trị"])
    writer.writerows(completion_rows(report))
    return stream.getvalue().encode("utf-8-sig")


def export_docx(report):
    paragraphs = "".join(
        f'<w:p><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{escape(label)}: </w:t></w:r><w:r><w:t xml:space="preserve">{escape(value)}</w:t></w:r></w:p>'
        for label, value in completion_rows(report)
    )
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{paragraphs}<w:sectPr/></w:body></w:document>'
    content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    relationships = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return stream.getvalue()


def export_pdf(report):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    font_name = "Helvetica"
    try:
        pdfmetrics.registerFont(
            TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        )
        font_name = "DejaVuSans"
    except (OSError, ValueError):
        font_name = "Helvetica"
    stream = io.BytesIO()
    page = canvas.Canvas(stream, pagesize=A4)
    _, height = A4
    y = height - 42
    page.setFont(font_name, 13)
    page.drawString(42, y, "Báo cáo hoàn tất kiểm thử")
    y -= 28
    page.setFont(font_name, 8)
    for label, value in completion_rows(report):
        text = f"{label}: {value}"
        while text:
            line = text[:120]
            text = text[120:]
            if y < 42:
                page.showPage()
                page.setFont(font_name, 8)
                y = height - 42
            page.drawString(42, y, line)
            y -= 12
    page.save()
    return stream.getvalue()


def export_completion_report(report, format_name):
    exporters = {"csv": export_csv, "docx": export_docx, "pdf": export_pdf}
    if format_name not in exporters:
        raise ValueError('COMPLETION_REPORT_EXPORT_FORMAT_UNSUPPORTED')
    return exporters[format_name](report)
