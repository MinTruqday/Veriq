import unittest

from src.core.auth import _access_policy_context, permissions_for_membership
from src.repositories.project_access import ProjectAccessRepository


class RequirementRolePolicyTests(unittest.TestCase):
    def test_project_settings_are_managed_by_ba_not_qa(self):
        document = {
            "_id": "active",
            "schema_version": 1,
            "revision": 3,
            "capabilities": [
                {"name": "project.read", "business_roles": ["BA", "QA"]},
                {"name": "project.update", "business_roles": ["BA"]},
                {"name": "project.settings.manage", "business_roles": ["BA"]},
            ],
            "role_grants": [
                {"role": "BA", "permissions": ["project.read"]},
                {
                    "role": "QA",
                    "permissions": [
                        "project.read",
                        "project.update",
                        "project.settings.manage",
                    ],
                },
            ],
        }

        updated = ProjectAccessRepository.project_settings_role_policy_preview(document)
        grants = {item.role: set(item.permissions) for item in updated.role_grants}

        self.assertEqual(updated.revision, 4)
        self.assertTrue({"project.update", "project.settings.manage"} <= grants["BA"])
        self.assertFalse({"project.update", "project.settings.manage"} & grants["QA"])
        repeated = ProjectAccessRepository.project_settings_role_policy_preview(updated.model_dump())
        self.assertEqual(repeated, updated)

    def test_project_settings_policy_adds_missing_roles_when_grants_are_empty(self):
        document = {
            "_id": "active",
            "schema_version": 1,
            "revision": 1,
            "capabilities": [
                {"name": "project.update", "business_roles": ["BA"]},
                {"name": "project.settings.manage", "business_roles": ["BA"]},
            ],
            "role_grants": [],
        }

        updated = ProjectAccessRepository.project_settings_role_policy_preview(document)
        grants = {item.role: set(item.permissions) for item in updated.role_grants}

        self.assertEqual([item.role for item in updated.role_grants], ["BA", "QA"])
        self.assertEqual(
            grants["BA"], {"project.update", "project.settings.manage"}
        )
        self.assertEqual(grants["QA"], set())
        repeated = ProjectAccessRepository.project_settings_role_policy_preview(
            updated.model_dump()
        )
        self.assertEqual(repeated, updated)

    def test_project_settings_policy_adds_ba_when_only_unrelated_role_exists(self):
        document = {
            "_id": "active",
            "schema_version": 1,
            "revision": 2,
            "capabilities": [
                {"name": "project.update", "business_roles": ["BA"]},
                {"name": "project.settings.manage", "business_roles": ["BA"]},
            ],
            "role_grants": [{"role": "VIEWER", "permissions": []}],
        }

        updated = ProjectAccessRepository.project_settings_role_policy_preview(document)
        grants = {item.role: set(item.permissions) for item in updated.role_grants}

        self.assertEqual(
            grants["BA"], {"project.update", "project.settings.manage"}
        )
        self.assertEqual(grants["VIEWER"], set())

    def test_qa_approval_is_not_gated_by_business_confirmation_responsibility(self):
        document = {
            "_id": "active",
            "schema_version": 1,
            "revision": 7,
            "capabilities": [
                {
                    "name": "requirement.approve",
                    "read_only": False,
                    "business_roles": ["QA"],
                    "responsibility": "business_confirmation",
                },
                {
                    "name": "requirement.review",
                    "read_only": False,
                    "business_roles": ["QA"],
                    "responsibility": None,
                },
                {
                    "name": "requirement.submit_review",
                    "read_only": False,
                    "business_roles": ["BA"],
                    "responsibility": None,
                },
            ],
            "role_grants": [
                {"role": "BA", "permissions": ["requirement.submit_review", "requirement.approve"]},
                {"role": "QA", "permissions": ["requirement.review"]},
                {"role": "TESTER", "permissions": []},
                {"role": "DEVELOPER", "permissions": []},
                {"role": "VIEWER", "permissions": []},
            ],
        }

        updated, required_roles = ProjectAccessRepository.requirement_role_policy_preview(document)
        capabilities = {item.name: item for item in updated.capabilities}
        grants = {item.role: set(item.permissions) for item in updated.role_grants}

        self.assertIsNone(capabilities["requirement.approve"].responsibility)
        self.assertEqual(capabilities["requirement.approve"].business_roles, ["QA"])
        self.assertEqual(required_roles["requirement.approve"], {"QA"})
        self.assertIn("requirement.approve", grants["QA"])
        self.assertNotIn("requirement.approve", grants["BA"])
        self.assertIn("requirement.review", grants["QA"])
        self.assertIn("requirement.submit_review", grants["BA"])

        token = _access_policy_context.set(updated.permission_values())
        try:
            qa_permissions = permissions_for_membership(
                {"status": "ACTIVE", "project_role": "QA", "user_id": "qa-user"},
                {"responsibilities": {"business_confirmation": "ba-user"}},
            )
            ba_permissions = permissions_for_membership(
                {"status": "ACTIVE", "project_role": "BA", "user_id": "ba-user"},
                {"responsibilities": {"business_confirmation": "ba-user"}},
            )
        finally:
            _access_policy_context.reset(token)

        self.assertIn("requirement.approve", qa_permissions)
        self.assertNotIn("requirement.approve", ba_permissions)

        repeated, _ = ProjectAccessRepository.requirement_role_policy_preview(updated.model_dump())

        self.assertEqual(repeated.capabilities, updated.capabilities)
        self.assertEqual(repeated.role_grants, updated.role_grants)


if __name__ == "__main__":
    unittest.main()
