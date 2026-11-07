import unittest

from src.core.rich_text import text_document
from src.modules.design.services.generation import merge_duplicate_generated_cases
from src.schemas.contracts.design import TestCaseDraftCreate
from src.schemas.test_analysis import GeneratedCase


SOURCE_EVIDENCE = [
    {"artifact_version_id": "REQ-V1", "text": "Ghi chú nội bộ"},
    {"artifact_version_id": "AC-1", "text": "Ghi chú được lưu và chỉ nhân viên nhìn thấy"},
    {"artifact_version_id": "AC-2", "text": "Ghi chú được lưu và chỉ nhân viên nhìn thấy"},
]


def draft(
    title,
    criterion_id="AC-1",
    expected="Ghi chú được lưu và chỉ nhân viên nhìn thấy",
    action="Tạo ghi chú nội bộ",
    techniques=None,
):
    return TestCaseDraftCreate(
        title=title,
        type="happy_path",
        objective_doc=text_document("Xác nhận tạo ghi chú nội bộ"),
        preconditions_doc=text_document("Nhân viên đã đăng nhập"),
        requirement_version_ids=["REQ-V1"],
        acceptance_criterion_ids=[criterion_id],
        steps=[{
            "id": "step-1",
            "order": 1,
            "action_doc": text_document(action),
            "expected_doc": text_document(expected),
        }],
        expected_result_doc=text_document(expected),
        techniques=techniques or ["positive"],
        source_evidence=SOURCE_EVIDENCE,
        evidence_refs=["REQ-V1", criterion_id],
        evidence_quotes=[{
            "evidence_ref": criterion_id,
            "quote": "Ghi chú được lưu và chỉ nhân viên nhìn thấy",
        }],
    )


def suggestion(
    criterion_id="AC-1",
    expected="Ghi chú được lưu và chỉ nhân viên nhìn thấy",
    techniques=None,
):
    return GeneratedCase(
        title="Tạo ghi chú thành công",
        category="happy_path",
        objective="Xác nhận tạo ghi chú nội bộ",
        preconditions="Nhân viên đã đăng nhập",
        steps=[{
            "action": "Tạo ghi chú nội bộ",
            "expected": expected,
        }],
        expected=expected,
        acceptance_criterion_ids=[criterion_id],
        evidence_refs=[criterion_id],
        evidence_quotes=[{
            "evidence_ref": criterion_id,
            "quote": "Ghi chú được lưu và chỉ nhân viên nhìn thấy",
        }],
        techniques=techniques or ["positive"],
    )


class GeneratedTestCaseDeduplicationTests(unittest.TestCase):
    def test_repeated_case_for_same_criterion_is_merged(self):
        cases, suggestions, merged = merge_duplicate_generated_cases(
            [draft("Tạo ghi chú thành công"), draft("Tạo ghi chú thành công")],
            [suggestion(), suggestion()],
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(merged, 1)
        self.assertEqual(cases[0].acceptance_criterion_ids, ["AC-1"])

    def test_duplicate_case_across_criteria_keeps_both_trace_links(self):
        cases, suggestions, merged = merge_duplicate_generated_cases(
            [draft("Tạo ghi chú thành công"), draft("Tạo ghi chú thành công", "AC-2")],
            [suggestion(), suggestion("AC-2")],
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(merged, 1)
        self.assertEqual(cases[0].acceptance_criterion_ids, ["AC-1", "AC-2"])
        self.assertEqual(set(cases[0].evidence_refs), {"AC-1", "AC-2"})
        self.assertEqual(cases[0].requirement_version_ids, ["REQ-V1"])
        self.assertEqual(set(suggestions[0].acceptance_criterion_ids), {"AC-1", "AC-2"})
        self.assertEqual(set(suggestions[0].evidence_refs), {"AC-1", "AC-2"})

    def test_distinct_expected_results_remain_separate(self):
        cases, _, merged = merge_duplicate_generated_cases(
            [
                draft("Tạo ghi chú thành công"),
                draft("Từ chối ghi chú khi không có quyền", "AC-2", "Hệ thống từ chối và không lưu ghi chú"),
            ],
            [
                suggestion(),
                suggestion("AC-2", "Hệ thống từ chối và không lưu ghi chú"),
            ],
        )

        self.assertEqual(len(cases), 2)
        self.assertEqual(merged, 0)

    def test_distinct_actions_remain_separate_even_when_expected_result_matches(self):
        cases, _, merged = merge_duplicate_generated_cases(
            [
                draft("Tạo ghi chú thành công"),
                draft("Xóa ghi chú thành công", "AC-2", action="Xóa ghi chú nội bộ"),
            ],
            [suggestion(), suggestion("AC-2")],
        )

        self.assertEqual(len(cases), 2)
        self.assertEqual(merged, 0)

    def test_same_case_across_techniques_is_merged_and_keeps_techniques(self):
        cases, suggestions, merged = merge_duplicate_generated_cases(
            [
                draft("Tạo ghi chú thành công", techniques=["equivalence_partitioning"]),
                draft("Tạo ghi chú thành công", "AC-2", techniques=["boundary_value"]),
            ],
            [
                suggestion(techniques=["equivalence_partitioning"]),
                suggestion("AC-2", techniques=["boundary_value"]),
            ],
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(merged, 1)
        self.assertEqual(set(cases[0].techniques), {"equivalence_partitioning", "boundary_value"})
        self.assertEqual(set(suggestions[0].techniques), {"equivalence_partitioning", "boundary_value"})


if __name__ == "__main__":
    unittest.main()
