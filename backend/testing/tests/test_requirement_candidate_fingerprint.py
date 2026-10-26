import unittest

from src.modules.requirements.services.requirement_workflow import candidate_fingerprint


class RequirementCandidateFingerprintTests(unittest.TestCase):
    def test_fingerprint_changes_when_acceptance_criteria_change(self):
        original = {
            "candidate_id": "candidate-1",
            "title": "Đăng nhập",
            "content_doc": {"type": "doc", "content": []},
            "source_refs": [{"requirement_document_id": "document-1"}],
            "acceptance_criteria": [{"key": "AC-1", "plain_text": "Tạo phiên"}],
        }
        changed = {
            **original,
            "acceptance_criteria": [{"key": "AC-1", "plain_text": "Không tạo phiên"}],
        }

        self.assertNotEqual(candidate_fingerprint(original), candidate_fingerprint(changed))

    def test_fingerprint_is_independent_of_mapping_key_order(self):
        left = {"candidate_id": "candidate-1", "actors": ["Người dùng"], "title": "Đăng nhập"}
        right = {"title": "Đăng nhập", "actors": ["Người dùng"], "candidate_id": "candidate-1"}

        self.assertEqual(candidate_fingerprint(left), candidate_fingerprint(right))


if __name__ == "__main__":
    unittest.main()
