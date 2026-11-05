import csv
import io
import json





def display(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def report_rows(report):
    period = report.get("reporting_period") or {}
    basis = report.get("snapshot_basis") or {}
    metrics = basis.get("metrics") or {}
    rows = [
        ("Mã báo cáo", report.get("_id")),
        ("Dự án", report.get("project_id")),
        ("Kế hoạch kiểm thử", report.get("test_plan_id")),
        ("Phiên bản chiến lược", report.get("strategy_version_id")),
        ("Bản phát hành", report.get("release_id")),
        ("Bản dựng", report.get("build_id")),
        ("Kỳ báo cáo bắt đầu", report.get("reporting_period_start", period.get("start_at"))),
        ("Kỳ báo cáo kết thúc", report.get("reporting_period_end", period.get("end_at"))),
        ("Ảnh chụp", report.get("snapshot_id")),
        ("Dấu vân tay nguồn", report.get("snapshot_source_fingerprint")),
        ("Trạng thái", report.get("status")),
        ("Khuyến nghị", report.get("recommendation")),
        ("Tóm tắt điều hành", report.get("executive_summary")),
        ("Tóm tắt tiến độ", report.get("progress_summary")),
        ("Tóm tắt độ phủ", report.get("coverage_summary")),
        ("Tóm tắt lỗi", report.get("defect_summary")),
        ("Tóm tắt bảo trì", report.get("maintenance_summary")),
        ("Diễn giải rủi ro", report.get("risk_explanation")),
        ("Dự báo", report.get("forecast")),
        ("Diễn giải khuyến nghị", report.get("recommendation_narrative")),
        ("Tỷ lệ thực thi", metrics.get("execution_percent")),
        ("Tỷ lệ đạt", metrics.get("pass_rate")),
        ("Độ phủ yêu cầu", metrics.get("requirement_coverage")),
        ("Độ phủ điều kiện kiểm thử", metrics.get("test_condition_coverage")),
        ("Cổng chất lượng", basis.get("quality_gate_status")),
        ("Sai lệch", report.get("deviations", [])),
        ("Trở ngại", report.get("blockers", [])),
        ("Rủi ro", report.get("risks", [])),
        ("Hành động kiểm soát", report.get("control_actions", [])),
        ("Mã hành động kiểm soát", report.get("control_action_ids", [])),
        ("Phân phối", report.get("distribution", [])),
        ("Bằng chứng", report.get("evidence_refs", [])),
    ]
    return [(label, display(value)) for label, value in rows]


def export_csv(report):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Trường", "Giá trị"])
    writer.writerows(report_rows(report))
    return stream.getvalue().encode("utf-8-sig")


def export_docx(report):
    from src.modules.execution.services.report_document import export_report_docx, legacy_report_document
    return export_report_docx(legacy_report_document(report, report_rows(report), "Báo cáo trạng thái kiểm thử"))


def export_pdf(report):
    from src.modules.execution.services.report_document import convert_report_pdf
    return convert_report_pdf(export_docx(report))


def export_status_report(report, format_name):
    exporters = dict(
        zip(['csv', 'docx', 'pdf'], (export_csv, export_docx, export_pdf))
    )
    if format_name not in exporters:
        raise ValueError('STATUS_REPORT_EXPORT_FORMAT_UNSUPPORTED')
    return exporters[format_name](report)
