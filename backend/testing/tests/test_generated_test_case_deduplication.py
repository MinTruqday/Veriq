import unittest
from types import SimpleNamespace

from src.core.rich_text import text_document
from src.modules.design.services.generation import remove_duplicate_generated_cases
from src.schemas.contracts.design import TestCaseDraftCreate


def draft(title):
    return TestCaseDraftCreate(
        title=title,
        type="happy_path",
        objective_doc=text_document("Xác nhận tạo ghi chú nội bộ"),
        preconditions_doc=text_document("Nhân viên đã đăng nhập"),
        requirement_version_ids=["REQ-V1"],
        acceptance_criterion_ids=["AC-1"],
        steps=[{
            "id": "step-1",
            "order": 1,
            "action_doc": text_document("Tạo ghi chú nội bộ"),
            "expected_doc": text_document("Ghi chú được lưu và chỉ nhân viên nhìn thấy"),
        }],
        expected_result_doc=text_document("Ghi chú được lưu và chỉ nhân viên nhìn thấy"),
        techniques=["positive"],
    )


class GeneratedTestCaseDeduplicationTests(unittest.TestCase):
    def test_repeated_generated_case_is_removed_from_preview(self):
        first = draft("Tạo ghi chú thành công")
        duplicate = draft("Tạo ghi chú thành công")
        suggestions = [
            SimpleNamespace(challenge_techniques=[]),
            SimpleNamespace(challenge_techniques=[]),
        ]

        cases, kept_suggestions, removed = remove_duplicate_generated_cases(
            [first, duplicate], suggestions
        )

        self.assertEqual(cases, [first])
        self.assertEqual(kept_suggestions, suggestions[:1])
        self.assertEqual(removed, 1)

    def test_distinct_acceptance_criteria_are_not_collapsed(self):
        first = draft("Tạo ghi chú thành công")
        second = TestCaseDraftCreate(
            **{**draft("Tạo ghi chú thành công").model_dump(), "acceptance_criterion_ids": ["AC-2"]}
        )
        suggestions = [
            SimpleNamespace(challenge_techniques=[]),
            SimpleNamespace(challenge_techniques=[]),
        ]

        cases, _, removed = remove_duplicate_generated_cases(
            [first, second], suggestions
        )

        self.assertEqual(len(cases), 2)
        self.assertEqual(removed, 0)


if __name__ == "__main__":
    unittest.main()
