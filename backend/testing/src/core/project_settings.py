from functools import lru_cache
from math import isfinite

from fastapi import HTTPException


@lru_cache(maxsize=1)
def default_project_settings():
    return {
        "impact_confidence_threshold": 0.75,
        "testcase_duplicate_threshold": 0.72,
        "trace_recovery_minimum_confidence": 0.18,
        "completion_open_blocker_threshold": 0,
        "rca_reopen_threshold": 2,
        "rca_duplicate_threshold": 3,
        "read_after_archive_policy": "ALLOW_READ",
        "require_independent_review": False,
        "work_item_planning": {
            "columns": [
                {"status": "BACKLOG", "name": "Danh sách chờ", "position": 0, "wip_limit": None},
                {"status": "TODO", "name": "Cần làm", "position": 1, "wip_limit": None},
                {"status": "IN_PROGRESS", "name": "Đang thực hiện", "position": 2, "wip_limit": None},
                {"status": "BLOCKED", "name": "Bị chặn", "position": 3, "wip_limit": None},
                {"status": "DONE", "name": "Hoàn thành", "position": 4, "wip_limit": None},
                {"status": "CANCELLED", "name": "Đã hủy", "position": 5, "wip_limit": None},
            ],
            "completed_statuses": ["DONE"],
            "requires_sprint_statuses": ["IN_PROGRESS"],
        },
        "complexity_dimensions": [
            {"id": "SCOPE", "label": "Phạm vi và phân rã", "description": "Phạm vi sản phẩm, phân hệ, luồng và ranh giới kiểm thử."},
            {"id": "BUSINESS_RULES", "label": "Quy tắc nghiệp vụ", "description": "Quy tắc, ngoại lệ và điều kiện nghiệp vụ."},
            {"id": "REQUIREMENT_TESTABILITY", "label": "Độ rõ của yêu cầu", "description": "Mức cụ thể, đo được và có thể xác minh của yêu cầu."},
            {"id": "INTEGRATIONS", "label": "Tích hợp và phụ thuộc", "description": "Hệ thống, dịch vụ và tổ chức phụ thuộc."},
            {"id": "DATA_LIFECYCLE", "label": "Dữ liệu và vòng đời", "description": "Cấu trúc, biến đổi, lưu trữ, quyền riêng tư và vòng đời dữ liệu."},
            {"id": "SECURITY_COMPLIANCE", "label": "Bảo mật và tuân thủ", "description": "Ranh giới tin cậy, kiểm soát bảo mật và nghĩa vụ tuân thủ."},
            {"id": "NON_FUNCTIONAL", "label": "Yêu cầu phi chức năng", "description": "Hiệu năng, độ tin cậy, khả năng truy cập và các thuộc tính chất lượng."},
            {"id": "ARCHITECTURE_ENVIRONMENT", "label": "Kiến trúc và môi trường", "description": "Kiến trúc, cấu hình, nền tảng và biến thể môi trường."},
            {"id": "TEST_COMBINATORICS", "label": "Tổ hợp kiểm thử", "description": "Số lượng tổ hợp trạng thái, dữ liệu, quyền và cấu hình cần kiểm tra."},
            {"id": "AUTOMATION_OBSERVABILITY", "label": "Tự động hóa và khả năng quan sát", "description": "Khả năng thực thi, thu thập tín hiệu và chẩn đoán kết quả kiểm thử."},
            {"id": "BUSINESS_RISK", "label": "Rủi ro kinh doanh", "description": "Tác động nghiệp vụ được chứng minh bởi tài liệu nguồn."},
            {"id": "UNCERTAINTY_CHANGE", "label": "Bất định và thay đổi", "description": "Mức thiếu thông tin, mâu thuẫn và biến động phạm vi."},
        ],
    }


def resolve_project_settings(settings):
    return {**default_project_settings(), **(settings or {})}


def validate_project_settings(settings):
    values = resolve_project_settings(settings)
    numeric_ranges = {
        "impact_confidence_threshold": (0, 1, False),
        "testcase_duplicate_threshold": (0, 1, False),
        "trace_recovery_minimum_confidence": (0, 1, False),
        "completion_open_blocker_threshold": (0, 1000, True),
        "rca_reopen_threshold": (1, 100, True),
        "rca_duplicate_threshold": (2, 100, True),
    }
    for key, (minimum, maximum, integral) in numeric_ranges.items():
        value = values[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or not minimum <= value <= maximum
            or integral and not isinstance(value, int)
        ):
            raise HTTPException(
                status_code=422,
                detail={"code": "PROJECT_SETTING_VALUE_INVALID", "setting": key},
            )
    if values.get("read_after_archive_policy") not in {"ALLOW_READ", "DENY_READ"}:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_SETTING_VALUE_INVALID", "setting": "read_after_archive_policy"},
        )
    if not isinstance(values.get("require_independent_review"), bool):
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_SETTING_VALUE_INVALID", "setting": "require_independent_review"},
        )
    return values


def resolve_testcase_duplicate_threshold(settings):
    return float(resolve_project_settings(settings)["testcase_duplicate_threshold"])
