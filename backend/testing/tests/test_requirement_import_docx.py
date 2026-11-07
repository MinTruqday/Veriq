import hashlib
import io
import unittest
import zipfile

from src.modules.requirements.services.requirement_import import (
    atomic_requirement_candidates,
    extract_docx,
    explicit_acceptance_criteria,
)
from src.modules.requirements.services.requirement_workflow import (
    prepare_requirement_candidates,
)
from src.modules.requirements.services.requirement_import_workflow import (
    grounded_requirement_candidates,
)


class RequirementDocxTableExtractionTests(unittest.TestCase):
    def test_table_cells_keep_requirement_and_related_requirement_separate(self):
        namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

        def cell(value):
            return (
                f'<w:tc><w:p><w:r><w:t>{value}</w:t></w:r></w:p></w:tc>'
            )

        document = (
            f'<w:document xmlns:w="{namespace}"><w:body><w:tbl>'
            f'<w:tr>{cell("Tiêu đề")}{cell("Yêu cầu liên quan")}</w:tr>'
            f'<w:tr>{cell("Đăng nhập tài khoản")}{cell("REQ-01")}</w:tr>'
            "</w:tbl><w:sectPr/></w:body></w:document>"
        )
        source = io.BytesIO()
        with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", document)

        extracted = extract_docx(source.getvalue())

        self.assertIn("| Tiêu đề | Yêu cầu liên quan |", extracted)
        self.assertIn("| Đăng nhập tài khoản | REQ-01 |", extracted)
        self.assertNotIn("Đăng nhập tài khoản Yêu cầu liên quan", extracted)

        document_record = {
            "_id": "doc-1",
            "content_hash": "hash-1",
            "source_version": 1,
            "format": "docx",
            "normalized_content": extracted,
        }
        candidates = atomic_requirement_candidates(document_record)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["title"], "Đăng nhập tài khoản")
        self.assertEqual(candidates[0]["dependencies"], ["REQ-01"])
        self.assertEqual(candidates[0]["source_refs"][0]["source_quote"], "| Đăng nhập tài khoản | REQ-01 |")
        self.assertEqual(
            candidates[0]["source_refs"][0]["source_text_hash"],
            hashlib.sha256("| Đăng nhập tài khoản | REQ-01 |".encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            candidates[0]["content_doc"]["content"][0]["content"][0]["text"],
            "Đăng nhập tài khoản",
        )

        preview = prepare_requirement_candidates("RIMP-test", candidates)

        self.assertEqual(preview[0]["candidate_status"], "ACTIVE")
        self.assertNotIn("REQUIREMENT_CONTENT_MISSING", preview[0]["quality_issues"])
        self.assertNotIn("REQUIREMENT_SOURCE_MISSING", preview[0]["quality_issues"])

    def test_requirement_table_keeps_description_and_acceptance_criteria_separate(self):
        content = (
            "| Mã yêu cầu | Tiêu đề | Mô tả | Tiêu chí chấp nhận | Yêu cầu liên quan |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| REQ-LOGIN | Đăng nhập tài khoản | Người dùng đăng nhập bằng email và mật khẩu. | "
            "Email hợp lệ thì tạo phiên đăng nhập. | REQ-ACCOUNT |\n"
        )
        document_record = {
            "_id": "doc-2",
            "content_hash": "hash-2",
            "source_version": 2,
            "format": "docx",
            "normalized_content": content,
        }

        candidates = atomic_requirement_candidates(document_record)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["requirement_key"], "REQ-LOGIN")
        self.assertEqual(candidate["title"], "Đăng nhập tài khoản")
        self.assertEqual(candidate["dependencies"], ["REQ-ACCOUNT"])
        self.assertEqual(candidate["acceptance_criteria"][0]["content_doc"]["content"][0]["content"][0]["text"], "Email hợp lệ thì tạo phiên đăng nhập.")
        self.assertNotIn("Yêu cầu liên quan", candidate["title"])

    def test_key_value_table_keeps_related_requirement_out_of_title(self):
        content = (
            "| Tiêu đề | Đăng nhập tài khoản |\n"
            "| Mô tả | Người dùng đăng nhập bằng email. |\n"
            "| Yêu cầu liên quan | REQ-ACCOUNT |\n"
        )
        document_record = {
            "_id": "doc-3",
            "content_hash": "hash-3",
            "source_version": 1,
            "format": "docx",
            "normalized_content": content,
        }

        candidates = atomic_requirement_candidates(document_record)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["title"], "Đăng nhập tài khoản")
        self.assertEqual(candidates[0]["dependencies"], ["REQ-ACCOUNT"])
        self.assertEqual(
            candidates[0]["content_doc"]["content"][0]["content"][0]["text"],
            "Người dùng đăng nhập bằng email.",
        )

    def test_description_sentences_are_not_inferred_as_acceptance_criteria(self):
        content = "Người dùng tạo ghi chú nội bộ. Ghi chú chỉ hiển thị với nhân viên."
        document = {
            "_id": "doc-4",
            "content_hash": "hash-4",
            "source_version": 1,
            "format": "docx",
            "source_type": "REFERENCE",
            "normalized_content": content,
        }
        results = [{
            "conflicts": [],
            "suggestions": [{
                "requirement_key": None,
                "title": "Ghi chú nội bộ",
                "type": "functional",
                "content": content,
                "acceptance_criteria": [
                    "Hệ thống quản lý đặt phòng khách sạn cung cấp chức năng thêm ghi chú nội bộ vào một đặt phòng đã tồn tại.",
                    "Người dùng mở chi tiết đặt phòng, nhập nội dung ghi chú và chọn Lưu.",
                    "Hệ thống xử lý thao tác theo quyền của người dùng hiện tại.",
                ],
                "actors": [],
                "business_rules": [],
                "dependencies": [],
                "missing_sections": [],
                "not_applicable_sections": [],
                "evidence_refs": ["doc-4:0"],
                "source_quotes": {"doc-4:0": content},
            }],
        }]

        candidates, _ = grounded_requirement_candidates(document, results)

        self.assertEqual(candidates[0]["content_doc"]["content"][0]["content"][0]["text"], content)
        self.assertEqual(candidates[0]["acceptance_criteria"], [])

    def test_only_explicit_acceptance_criteria_are_retained_from_ai(self):
        content = (
            "Thêm ghi chú nội bộ cho đặt phòng.\n\n"
            "AC-01: Khi nhân viên lễ tân lưu ghi chú, hệ thống lưu và hiển thị nội dung.\n"
            "AC-02: Người không có quyền không thể thêm ghi chú."
        )
        document = {
            "_id": "doc-5",
            "content_hash": "hash-5",
            "source_version": 1,
            "format": "docx",
            "source_type": "REFERENCE",
            "normalized_content": content,
        }
        result = [{
            "conflicts": [],
            "suggestions": [{
                "requirement_key": None,
                "title": "Thêm ghi chú nội bộ cho đặt phòng",
                "type": "functional",
                "content": "Thêm ghi chú nội bộ cho đặt phòng.",
                "acceptance_criteria": [
                    "Thêm ghi chú nội bộ cho đặt phòng.",
                    "AC-01: Khi nhân viên lễ tân lưu ghi chú, hệ thống lưu và hiển thị nội dung.",
                    "AC-02: Người không có quyền không thể thêm ghi chú.",
                ],
                "actors": [],
                "business_rules": [],
                "dependencies": [],
                "missing_sections": [],
                "not_applicable_sections": [],
                "evidence_refs": ["doc-5:0"],
                "source_quotes": {"doc-5:0": content},
            }],
        }]

        candidates, _ = grounded_requirement_candidates(document, result)

        self.assertEqual(
            [item["content_doc"]["content"][0]["content"][0]["text"] for item in candidates[0]["acceptance_criteria"]],
            [
                "Khi nhân viên lễ tân lưu ghi chú, hệ thống lưu và hiển thị nội dung.",
                "Người không có quyền không thể thêm ghi chú.",
            ],
        )

    def test_acceptance_criteria_section_keeps_each_list_item_separate(self):
        document = {
            "_id": "doc-6",
            "content_hash": "hash-6",
            "source_version": 1,
            "format": "md",
            "normalized_content": (
                "Mô tả: Ghi chú được lưu trong hệ thống.\n\n"
                "## Tiêu chí chấp nhận\n"
                "- Khi lưu ghi chú, hệ thống hiển thị nội dung đã lưu.\n"
                "- Người không có quyền không thể thêm ghi chú.\n\n"
                "## Quy tắc nghiệp vụ\n"
                "- Ghi chú chỉ hiển thị với nhân viên."
            ),
        }

        criteria = explicit_acceptance_criteria(document)

        self.assertEqual(len(criteria), 2)
        self.assertIn("khi lưu ghi chú, hệ thống hiển thị nội dung đã lưu.", criteria)
        self.assertIn("người không có quyền không thể thêm ghi chú.", criteria)
        self.assertNotIn("ghi chú chỉ hiển thị với nhân viên.", criteria)

    def test_import_does_not_promote_requirement_body_sentences_to_acceptance_criteria(self):
        content = (
            "ĐẶC TẢ YÊU CẦU PHẦN MỀM\n\n"
            "1. THÔNG TIN YÊU CẦU\n"
            "Nội dung yêu cầu: Hệ thống quản lý đặt phòng khách sạn cung cấp chức năng thêm ghi chú nội bộ vào một đặt phòng đã tồn tại. "
            "Người dùng mở chi tiết đặt phòng, nhập nội dung ghi chú và chọn Lưu. "
            "Hệ thống xử lý thao tác theo quyền của người dùng hiện tại.\n\n"
            "2. TIÊU CHÍ CHẤP NHẬN (AC)\n"
            "AC-01: Khi nhân viên lễ tân lưu ghi chú, hệ thống lưu và hiển thị nội dung.\n"
            "AC-02: Người không có quyền không thể thêm ghi chú.\n\n"
            "3. QUY TẮC NGHIỆP VỤ (BR)\n"
            "BR-01: Chỉ nhân viên lễ tân được phép sửa ghi chú."
        )
        document = {
            "_id": "doc-body-criteria",
            "content_hash": "hash-body-criteria",
            "source_version": 1,
            "format": "docx",
            "normalized_content": content,
        }
        suggestion = {
            "requirement_key": None,
            "title": "Thêm ghi chú nội bộ",
            "type": "functional",
            "content": content,
            "acceptance_criteria": [
                "Hệ thống quản lý đặt phòng khách sạn cung cấp chức năng thêm ghi chú nội bộ vào một đặt phòng đã tồn tại.",
                "Người dùng mở chi tiết đặt phòng, nhập nội dung ghi chú và chọn Lưu.",
                "Hệ thống xử lý thao tác theo quyền của người dùng hiện tại.",
                "AC-01: Khi nhân viên lễ tân lưu ghi chú, hệ thống lưu và hiển thị nội dung.",
                "AC-02: Người không có quyền không thể thêm ghi chú.",
            ],
            "actors": [],
            "business_rules": [],
            "dependencies": [],
            "missing_sections": [],
            "not_applicable_sections": [],
            "evidence_refs": ["doc-body-criteria:0"],
            "source_quotes": {"doc-body-criteria:0": content},
        }

        candidates, _ = grounded_requirement_candidates(document, [{"conflicts": [], "suggestions": [suggestion]}])

        self.assertEqual(
            [item["content_doc"]["content"][0]["content"][0]["text"] for item in candidates[0]["acceptance_criteria"]],
            [
                "Khi nhân viên lễ tân lưu ghi chú, hệ thống lưu và hiển thị nội dung.",
                "Người không có quyền không thể thêm ghi chú.",
            ],
        )

    def test_explicit_acceptance_criteria_table_values_remain_available(self):
        document = {
            "_id": "doc-table-criteria",
            "content_hash": "hash-table-criteria",
            "source_version": 1,
            "format": "md",
            "normalized_content": (
                "| Mã yêu cầu | Tiêu đề | Mô tả | Tiêu chí chấp nhận |\n"
                "| --- | --- | --- | --- |\n"
                "| REQ-1 | Ghi chú | Lưu ghi chú. | Ghi chú được lưu và hiển thị. |\n"
            ),
        }

        criteria = explicit_acceptance_criteria(document)

        self.assertEqual(criteria, {"ghi chú được lưu và hiển thị."})


if __name__ == "__main__":
    unittest.main()
