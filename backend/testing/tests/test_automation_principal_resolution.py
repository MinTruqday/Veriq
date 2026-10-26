import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.operations.services.internal_admin import InternalAdminService
from src.schemas.internal_admin import AutomationPrincipalResolve


class AutomationPrincipalResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_document_stage_uses_ba_instead_of_impersonating_qa(self):
        repository = "src.modules.operations.services.internal_admin.internal_admin_repository"
        requester = {"user_id": "ba-1", "project_role": "BA", "status": "ACTIVE"}
        with (
            patch(f"{repository}.find_project", new=AsyncMock(return_value={"_id": "project-1"})),
            patch(f"{repository}.find_active_membership", new=AsyncMock(return_value=requester)),
            patch(f"{repository}.list_active_qa_members", new=AsyncMock()) as candidates,
        ):
            result = await InternalAdminService.resolve_automation_principal(
                "project-1", AutomationPrincipalResolve(requester_user_id="ba-1", required_role="BA")
            )
        self.assertEqual(result["executor_role"], "BA")
        self.assertEqual(result["executor_user_id"], "ba-1")
        candidates.assert_not_awaited()

    async def test_ba_uses_the_projects_active_initial_qa(self):
        project = {"_id": "project-1", "initial_qa_user_id": "qa-1"}
        requester = {"user_id": "ba-1", "project_role": "BA", "status": "ACTIVE"}
        qa = {"user_id": "qa-1", "project_role": "QA", "status": "ACTIVE"}
        with (
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_project",
                new=AsyncMock(return_value=project),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_active_membership",
                new=AsyncMock(side_effect=[requester, qa]),
            ) as find_membership,
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.list_active_qa_members",
                new=AsyncMock(return_value=[]),
            ) as list_qa,
        ):
            result = await InternalAdminService.resolve_automation_principal(
                "project-1", AutomationPrincipalResolve(requester_user_id="ba-1")
            )

        self.assertEqual(result["executor_user_id"], "qa-1")
        self.assertEqual(result["requester_user_id"], "ba-1")
        self.assertEqual(find_membership.await_count, 2)
        list_qa.assert_not_awaited()

    async def test_member_with_ba_and_qa_roles_is_its_own_executor(self):
        project = {"_id": "project-1", "initial_qa_user_id": "qa-1"}
        requester = {
            "user_id": "member-1",
            "project_role": "BA",
            "project_roles": ["BA", "QA"],
            "status": "ACTIVE",
        }
        with (
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_project",
                new=AsyncMock(return_value=project),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_active_membership",
                new=AsyncMock(return_value=requester),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.list_active_qa_members",
                new=AsyncMock(),
            ) as list_qa,
        ):
            result = await InternalAdminService.resolve_automation_principal(
                "project-1", AutomationPrincipalResolve(requester_user_id="member-1")
            )

        self.assertEqual(result["executor_user_id"], "member-1")
        self.assertEqual(result["executor_role"], "QA")
        list_qa.assert_not_awaited()

    async def test_inactive_initial_qa_falls_back_to_another_active_qa(self):
        project = {"_id": "project-1", "initial_qa_user_id": "qa-old"}
        requester = {"user_id": "ba-1", "project_role": "BA", "status": "ACTIVE"}
        active_qa = {"user_id": "qa-current", "project_role": "QA", "status": "ACTIVE"}
        with (
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_project",
                new=AsyncMock(return_value=project),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_active_membership",
                new=AsyncMock(side_effect=[requester, None]),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.list_active_qa_members",
                new=AsyncMock(return_value=[active_qa]),
            ),
        ):
            result = await InternalAdminService.resolve_automation_principal(
                "project-1", AutomationPrincipalResolve(requester_user_id="ba-1")
            )

        self.assertEqual(result["executor_user_id"], "qa-current")

    async def test_non_member_cannot_start_project_automation(self):
        with (
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_project",
                new=AsyncMock(return_value={"_id": "project-1"}),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_active_membership",
                new=AsyncMock(return_value=None),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await InternalAdminService.resolve_automation_principal(
                    "project-1", AutomationPrincipalResolve(requester_user_id="outsider")
                )

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail["code"], "PROJECT_MEMBERSHIP_REQUIRED")

    async def test_project_without_active_qa_fails_closed(self):
        requester = {"user_id": "ba-1", "project_role": "BA", "status": "ACTIVE"}
        with (
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_project",
                new=AsyncMock(return_value={"_id": "project-1"}),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_active_membership",
                new=AsyncMock(return_value=requester),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.list_active_qa_members",
                new=AsyncMock(return_value=[]),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await InternalAdminService.resolve_automation_principal(
                    "project-1", AutomationPrincipalResolve(requester_user_id="ba-1")
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "PROJECT_QA_EXECUTOR_UNAVAILABLE")

    async def test_suspended_project_does_not_resolve_an_executor(self):
        with (
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_project",
                new=AsyncMock(
                    return_value={"_id": "project-1", "administrative_status": "SUSPENDED"}
                ),
            ),
            patch(
                "src.modules.operations.services.internal_admin.internal_admin_repository.find_active_membership",
                new=AsyncMock(),
            ) as find_membership,
        ):
            with self.assertRaises(HTTPException) as raised:
                await InternalAdminService.resolve_automation_principal(
                    "project-1", AutomationPrincipalResolve(requester_user_id="ba-1")
                )

        self.assertEqual(raised.exception.status_code, 423)
        find_membership.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
