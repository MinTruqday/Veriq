import csv
import io
import json






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
    from src.modules.execution.services.report_document import export_report_docx, legacy_report_document
    return export_report_docx(legacy_report_document(report, completion_rows(report), "Báo cáo hoàn tất kiểm thử"))


def export_pdf(report):
    from src.modules.execution.services.report_document import convert_report_pdf
    return convert_report_pdf(export_docx(report))


def export_completion_report(report, format_name):
    exporters = {"csv": export_csv, "docx": export_docx, "pdf": export_pdf}
    if format_name not in exporters:
        raise ValueError('COMPLETION_REPORT_EXPORT_FORMAT_UNSUPPORTED')
    return exporters[format_name](report)
