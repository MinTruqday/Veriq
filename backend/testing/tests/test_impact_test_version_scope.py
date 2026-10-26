import unittest

from src.modules.quality.services.impact_analysis import impact_test_version_ids


class ImpactTestVersionScopeTests(unittest.TestCase):
    def test_includes_current_and_frozen_directly_traced_versions_once(self):
        current_tests = [
            {"_id": "TC-1", "current_version_id": "TCV-3"},
            {"_id": "TC-2", "current_version_id": "TCV-1"},
            {"_id": "TC-3", "current_version_id": None},
        ]

        version_ids = impact_test_version_ids(
            current_tests,
            {"TCV-2", "TCV-3", "OTHER-ARTIFACT"},
        )

        self.assertEqual(
            version_ids,
            ["TCV-3", "TCV-1", "OTHER-ARTIFACT", "TCV-2"],
        )


if __name__ == "__main__":
    unittest.main()
