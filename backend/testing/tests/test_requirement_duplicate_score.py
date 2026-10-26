import unittest

from src.modules.design.services.linters import requirement_duplicate_score


class RequirementDuplicateScoreTests(unittest.TestCase):
    def test_shared_actor_does_not_make_distinct_behaviors_duplicates(self):
        successful_login = {
            "type": "functional",
            "title": "LOGIN_SUCCESS_SESSION",
            "actors": ["Người dùng"],
            "acceptance_criteria": [],
        }
        rejected_login = {
            "type": "functional",
            "title": "LOGIN_FAILURE_WRONG_PASSWORD",
            "actors": ["Người dùng"],
            "acceptance_criteria": [
                {"plain_text": "Khi mật khẩu sai, hệ thống từ chối đăng nhập và không tạo phiên."}
            ],
        }

        score, reasons = requirement_duplicate_score(successful_login, rejected_login)

        self.assertLess(score, 0.72)
        self.assertIn("Có tác nhân nghiệp vụ chung", reasons)

    def test_exact_behavior_remains_a_duplicate(self):
        left = {
            "type": "functional",
            "title": "Tạo phiên đăng nhập",
            "content_doc": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Khi thông tin hợp lệ, hệ thống tạo phiên."}]}]},
            "actors": ["Người dùng"],
        }
        right = {
            **left,
            "actors": ["Người dùng"],
        }

        score, reasons = requirement_duplicate_score(left, right)

        self.assertEqual(score, 1)
        self.assertIn("Nội dung yêu cầu trùng khớp hoàn toàn", reasons)


if __name__ == "__main__":
    unittest.main()
