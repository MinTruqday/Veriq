import unittest

from src.tools.requirement_document_workflow import safe_requirement_import_resolution


class SafeRequirementImportResolutionTests(unittest.TestCase):
    def test_exact_match_only_links_source(self):
        candidate = {
            "matches": [
                {
                    "requirement_id": "REQ-1",
                    "version_id": "REQV-1",
                    "match_type": "EXACT",
                }
            ]
        }

        self.assertEqual(
            safe_requirement_import_resolution(candidate),
            ("link_source", candidate["matches"][0]),
        )

    def test_stable_key_match_creates_new_version(self):
        candidate = {
            "matches": [
                {
                    "requirement_id": "REQ-1",
                    "version_id": "REQV-1",
                    "match_type": "SAME_KEY",
                }
            ]
        }

        self.assertEqual(
            safe_requirement_import_resolution(candidate),
            ("create_version", candidate["matches"][0]),
        )

    def test_single_semantic_match_is_not_enough_to_merge(self):
        candidate = {
            "matches": [
                {
                    "requirement_id": "REQ-1",
                    "version_id": "REQV-1",
                    "match_type": "POSSIBLE",
                }
            ]
        }

        self.assertIsNone(safe_requirement_import_resolution(candidate))

    def test_multiple_possible_matches_remain_unresolved(self):
        candidate = {
            "matches": [
                {"requirement_id": "REQ-1", "match_type": "POSSIBLE"},
                {"requirement_id": "REQ-2", "match_type": "POSSIBLE"},
            ]
        }

        self.assertIsNone(safe_requirement_import_resolution(candidate))

    def test_multiple_exact_matches_are_not_resolved_by_a_stable_key_fallback(self):
        candidate = {
            "matches": [
                {"requirement_id": "REQ-1", "match_type": "EXACT"},
                {"requirement_id": "REQ-2", "match_type": "EXACT"},
                {"requirement_id": "REQ-3", "match_type": "SAME_KEY"},
            ]
        }

        self.assertIsNone(safe_requirement_import_resolution(candidate))

    def test_exact_match_without_target_version_remains_unresolved(self):
        candidate = {
            "matches": [
                {"requirement_id": "REQ-1", "match_type": "EXACT"},
            ]
        }

        self.assertIsNone(safe_requirement_import_resolution(candidate))

    def test_stable_key_match_without_target_version_remains_unresolved(self):
        candidate = {
            "matches": [
                {"requirement_id": "REQ-1", "match_type": "SAME_KEY"},
            ]
        }

        self.assertIsNone(safe_requirement_import_resolution(candidate))

    def test_obsolete_stable_key_match_is_not_automatically_reactivated(self):
        candidate = {
            "matches": [
                {
                    "requirement_id": "REQ-1",
                    "version_id": "REQV-1",
                    "requirement_status": "OBSOLETE",
                    "match_type": "SAME_KEY",
                }
            ]
        }

        self.assertIsNone(safe_requirement_import_resolution(candidate))

    def test_archived_exact_match_is_not_automatically_reused(self):
        candidate = {
            "matches": [
                {
                    "requirement_id": "REQ-1",
                    "version_id": "REQV-1",
                    "requirement_status": "ARCHIVED",
                    "match_type": "EXACT",
                }
            ]
        }

        self.assertIsNone(safe_requirement_import_resolution(candidate))


if __name__ == "__main__":
    unittest.main()
