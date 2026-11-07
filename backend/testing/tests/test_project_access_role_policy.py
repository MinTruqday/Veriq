import unittest

from src.core.auth import _access_policy_context, permissions_for_membership
from src.repositories.project_access import ProjectAccessRepository


class RequirementRolePolicyTests(unittest.TestCase):
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
