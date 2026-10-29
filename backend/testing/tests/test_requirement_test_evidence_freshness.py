from src.modules.design.services.test_evidence import (
    requirement_test_evidence_matches,
    requirement_test_evidence_text,
)


def test_requirement_evidence_freshness_includes_all_testable_sections():
    version = {
        "plain_text_projection": "Người dùng đăng nhập bằng thông tin hợp lệ.",
        "actors": ["Người dùng"],
        "business_rules": ["Tài khoản phải đang hoạt động."],
        "dependencies": ["Dịch vụ xác thực"],
        "details": {"exception_flow": "Từ chối tài khoản đã khóa."},
    }
    expected = requirement_test_evidence_text(version)

    assert requirement_test_evidence_matches(version, expected)

    changed = {
        **version,
        "business_rules": ["Tài khoản phải đang hoạt động và đã xác minh."],
    }

    assert not requirement_test_evidence_matches(changed, expected)
