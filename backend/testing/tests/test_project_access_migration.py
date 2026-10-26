import unittest
from unittest.mock import patch

from pydantic import ValidationError

from src.core import auth
from src.schemas.project_access import ProjectAccessControl


class ProjectAccessMigrationTests(unittest.TestCase):
    def setUp(self):
        self.legacy = {
            "project_permissions": ["project.read", "testcase.read", "testcase.update", "requirement.approve"],
            "read_only_permissions": ["project.read", "testcase.read"],
            "role_permissions": {"QA": ["project.read", "testcase.update"], "TESTER": ["project.read", "testcase.read"], "BA": ["project.read"]},
            "policy_permissions": {"tester_can_bulk_update": {"role": "TESTER", "permissions": ["testcase.update"]}},
            "conditional_permissions": [{"role": "BA", "setting": "ba_can_approve", "enabled": True, "permissions": ["requirement.approve"]}],
            "conditional_denials": [{"role": "TESTER", "setting": "allow_read", "enabled": False, "permissions": ["testcase.read"]}],
        }

    def test_migration_preserves_grants_conditions_and_denials(self):
        migrated = ProjectAccessControl.from_legacy(self.legacy).permission_values()
        for role in ("QA", "BA", "TESTER"):
            for settings in ({}, {"tester_can_bulk_update": True, "ba_can_approve": True}, {"allow_read": False}):
                with self.subTest(role=role, settings=settings):
                    with patch.object(auth, "access_policy", return_value=self.legacy):
                        before = auth.permissions_for_role(role, settings)
                    with patch.object(auth, "access_policy", return_value=migrated):
                        after = auth.permissions_for_role(role, settings)
                    self.assertEqual(before, after)

    def test_unknown_capability_blocks_migration_instead_of_dropping_data(self):
        self.legacy["role_permissions"]["QA"].append("unregistered.write")
        with self.assertRaises(ValidationError):
            ProjectAccessControl.from_legacy(self.legacy)

    def test_unknown_legacy_rule_family_requires_explicit_migration(self):
        with self.assertRaisesRegex(ValueError, "UNRECOGNIZED_LEGACY_ACCESS_FIELDS"):
            ProjectAccessControl.from_legacy({**self.legacy, "new_rule_type": []})


if __name__ == "__main__":
    unittest.main()
