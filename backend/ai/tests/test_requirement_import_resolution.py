import unittest

from src.tools.requirement_document_workflow import (
    requirement_versions_requiring_maintenance,
    safe_in_import_duplicate_resolution,
    safe_requirement_import_resolution,
)


class SafeRequirementImportResolutionTests(unittest.TestCase):
    def test_resumed_import_recovers_versions_that_need_downstream_maintenance(self):
        self.assertEqual(
            requirement_versions_requiring_maintenance(
                {
                    "resolutions": [
                        {
                            "action": "create_version",
                            "to_version_id": "REQV-2",
                        },
                        {
                            "action": "link_source",
                            "to_version_id": "REQV-3",
                        },
                        {
                            "action": "create_requirement",
                            "to_version_id": "REQV-4",
                        },
                        {"action": "create_version", "to_version_id": " "},
                        {"action": "create_version", "to_version_id": None},
                    ]
                }
            ),
            {"REQV-2"},
        )

    def test_resumed_import_without_resolution_records_needs_no_maintenance(self):
        self.assertEqual(requirement_versions_requiring_maintenance({}), set())
        self.assertEqual(
            requirement_versions_requiring_maintenance({"resolutions": None}), set()
        )

    def test_exact_duplicate_of_resolved_candidate_links_its_source(self):
        target = {
            "candidate_id": "CAND-1",
            "match_type": "IN_IMPORT",
        }
        exact = {
            "requirement_id": "REQ-1",
            "version_id": "REQV-1",
            "match_type": "EXACT",
        }

        self.assertEqual(
            safe_in_import_duplicate_resolution(
                {"matches": [exact]},
                [target],
                [
                    {
                        "candidate_id": "CAND-1",
                        "requirement_id": "REQ-1",
                    }
                ],
            ),
            ("link_source", exact),
        )

    def test_same_key_duplicate_is_not_automatically_linked(self):
        self.assertIsNone(
            safe_in_import_duplicate_resolution(
                {"matches": [{"requirement_id": "REQ-1", "match_type": "SAME_KEY"}]},
                [{"candidate_id": "CAND-1", "match_type": "SAME_KEY_IN_IMPORT"}],
                [{"candidate_id": "CAND-1", "requirement_id": "REQ-1"}],
            )
        )

    def test_internal_duplicate_waits_until_target_is_resolved_exactly(self):
        self.assertIsNone(
            safe_in_import_duplicate_resolution(
                {"matches": [{"requirement_id": "REQ-1", "match_type": "POSSIBLE"}]},
                [{"candidate_id": "CAND-1", "match_type": "IN_IMPORT"}],
                [],
            )
        )

    def test_internal_duplicate_waits_until_every_possible_target_is_resolved(self):
        self.assertIsNone(
            safe_in_import_duplicate_resolution(
                {"matches": [{"requirement_id": "REQ-1", "match_type": "EXACT"}]},
                [
                    {"candidate_id": "CAND-1", "match_type": "IN_IMPORT"},
                    {"candidate_id": "CAND-2", "match_type": "IN_IMPORT"},
                ],
                [{"candidate_id": "CAND-1", "requirement_id": "REQ-1"}],
            )
        )

    def test_unmatched_candidate_is_created_without_resolving_other_candidates(self):
        candidate = {"matches": []}

        self.assertEqual(
            safe_requirement_import_resolution(candidate),
            ("create_requirement", None),
        )

    def test_missing_match_data_does_not_authorize_creating_a_requirement(self):
        self.assertIsNone(safe_requirement_import_resolution({}))

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
