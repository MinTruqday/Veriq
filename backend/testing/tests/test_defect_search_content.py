from src.modules.quality.services.defect_search import defect_search_text


def _doc(text):
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]}
        ],
    }


def test_defect_search_text_uses_same_diagnostic_fields_for_create_and_update():
    text = defect_search_text(
        {
            "title": "Đăng nhập lỗi",
            "description_doc": _doc("Tài khoản hợp lệ"),
            "actual_result_doc": _doc("Màn hình báo sai mật khẩu"),
            "expected_result_doc": _doc("Mở trang tổng quan"),
            "steps_to_reproduce": [
                {
                    "action": "Nhập thông tin",
                    "data": "email có dấu",
                    "expected_result": "Đăng nhập thành công",
                }
            ],
        }
    )

    assert text == (
        "Đăng nhập lỗi Tài khoản hợp lệ Màn hình báo sai mật khẩu "
        "Mở trang tổng quan Nhập thông tin email có dấu Đăng nhập thành công"
    )


def test_defect_search_text_reads_frozen_test_case_step_shape():
    text = defect_search_text(
        {
            "steps_to_reproduce": [
                {
                    "id": "step-1",
                    "action_doc": _doc("Điền tài khoản"),
                    "test_data": {"email": "qa@example.test"},
                    "expected_doc": _doc("Hiện trang tổng quan"),
                }
            ]
        }
    )

    assert "Điền tài khoản" in text
    assert '"email": "qa@example.test"' in text
    assert "Hiện trang tổng quan" in text


def test_defect_search_text_ignores_malformed_steps_and_blank_fields():
    assert defect_search_text(
        {"title": "Lỗi", "description_doc": _doc(" "), "steps_to_reproduce": [None, "bad"]}
    ) == "Lỗi"


def test_defect_search_text_redacts_sensitive_step_data_and_inline_credentials():
    text = defect_search_text(
        {
            "description_doc": _doc('Dùng password="sample-secret-value"'),
            "steps_to_reproduce": [
                {"test_data": {"password": "sample-secret-value", "email": "qa@example.test"}}
            ],
        }
    )

    assert "sample-secret-value" not in text
    assert "qa@example.test" in text
