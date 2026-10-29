import unittest
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import jwt
from fastapi import HTTPException
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.core import auth, common
from src.core.human_decisions import require_automation_publication_authority
from src.clients import ai_automation
from src.modules.execution.api import execution_context as execution_context_api
from src.modules.requirements.services.requirement_lifecycle import baseline_requirement
from src.modules.design.services.test_case_lifecycle import approve_test_case_draft_record
from src.modules.quality.services.proposal_application import apply_maintenance_proposal


class HumanReviewBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_automation_cannot_publish_without_scoped_publication_permission(self):
        user = SimpleNamespace(id="agent", _ai_automation_run_id="run-1")
        operations = [
            lambda: baseline_requirement("version", 1, "note", user),
            lambda: approve_test_case_draft_record("draft", None, user),
            lambda: apply_maintenance_proposal("proposal", None, user, "ACCEPTED"),
        ]
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaises(HTTPException) as error:
                await operation()
            self.assertEqual(error.exception.status_code, 403)
            self.assertEqual(
                error.exception.detail["code"],
                "AUTOMATION_PUBLICATION_NOT_AUTHORIZED",
            )

    def test_scoped_ai_event_can_make_only_its_automated_publication_decision(self):
        user = SimpleNamespace(
            _ai_automation_run_id="run-1",
            _ai_automation_publication_permissions=[
                "requirement.approve",
                "testcase.approve",
                "proposal.approve",
            ],
        )
        require_automation_publication_authority(user, "requirement.approve")
        require_automation_publication_authority(user, "testcase.approve")
        require_automation_publication_authority(user, "proposal.approve")
        with self.assertRaises(HTTPException) as error:
            require_automation_publication_authority(user, "release.close")
        self.assertEqual(
            error.exception.detail["code"],
            "AUTOMATION_PUBLICATION_NOT_AUTHORIZED",
        )

    async def test_signed_publication_scope_is_reduced_to_allowlisted_actions(self):
        secret = "test-secret-key-with-at-least-32-bytes"
        with patch.object(auth.settings, "SECRET_KEY", secret):
            token = jwt.encode(
                {
                    "uid": "ba-user",
                    "sub": "ba@example.test",
                    "system_role": "USER",
                    "ai_automation_run_id": "run-1",
                    "ai_automation_source_document_ids": [],
                    "ai_automation_initiator_id": "ba-user",
                    "ai_automation_publication_project_id": "project-1",
                    "ai_automation_publication_permissions": [
                        "requirement.approve",
                        "proposal.approve",
                        "testplan.approve",
                        "release.close",
                    ],
                    "exp": int(time.time()) + 60,
                },
                secret,
                algorithm="HS256",
            )
            with (
                patch(
                    "src.clients.ai_automation.automation_run_is_active",
                    new=AsyncMock(return_value=True),
                ),
                patch(
                    "src.repositories.ai_automation_access.ai_automation_access_repository.acquire",
                    new=AsyncMock(return_value=True),
                ),
            ):
                user = await auth.get_current_user(
                    SimpleNamespace(state=SimpleNamespace(), method="GET"),
                    token,
                    "run-1",
                    secret,
                )
        self.assertEqual(
            user._ai_automation_publication_permissions,
            ["proposal.approve", "release.close", "requirement.approve", "testplan.approve"],
        )
        require_automation_publication_authority(user, "release.close")

    async def test_publication_scope_is_limited_to_the_signed_project(self):
        user = SimpleNamespace(
            id="ba-user",
            system_role=SimpleNamespace(value="USER"),
        )
        repository = common.common_repository
        project = {"_id": "project-1", "administrative_status": "ACTIVE"}
        membership = {"project_role": "BA", "project_roles": ["BA"], "status": "ACTIVE"}
        automation_context = {
            "principal_id": "ba-user",
            "publication_project_id": "project-1",
            "publication_permissions": ["requirement.approve"],
        }
        with (
            patch.object(repository, "find_project", new=AsyncMock(return_value=project)),
            patch.object(repository, "find_membership", new=AsyncMock(return_value=membership)),
            patch.object(repository, "find_active_grant", new=AsyncMock(return_value=None)),
            patch.object(common, "permissions_for_membership", return_value=set()),
            patch.object(common, "audit", new=AsyncMock()),
            patch.object(common, "common_repository", repository),
        ):
            token = common.ai_automation_context.set(automation_context)
            await common.get_project("project-1", user, "requirement.approve")
            with self.assertRaises(HTTPException) as error:
                await common.get_project("project-1", user, "testcase.approve")
            common.ai_automation_context.reset(token)
        self.assertEqual(error.exception.status_code, 403)

    def test_role_overrides_cannot_grant_tester_definition_writes(self):
        mutations = {
            "testcase.create",
            "testcase.update",
            "testcase.import",
            "testcase.bulk.update",
            "testcase.approve",
            "testdata.update",
            "testsuite.update",
            "testplan.create",
            "testplan.update",
            "testplan.archive",
            "testplan.submit_review",
            "testplan.approve",
            "ai.generate_testcase",
        }
        permissions = mutations | {"testcase.read", "testcase.review", "comment.create"}
        policy = {"project_permissions": list(permissions), "role_permissions": {"TESTER": list(permissions), "QA": list(permissions)}}
        with patch.object(auth, "access_policy", return_value=policy):
            actual = auth.permissions_for_role("TESTER", {"permission_overrides": {"TESTER": {"allow": list(mutations)}}})
            self.assertTrue(mutations.isdisjoint(actual))
            self.assertIn("testcase.read", actual)
            self.assertIn("testcase.review", actual)
            self.assertTrue(mutations <= auth.permissions_for_role("QA"))

    def test_combined_ba_qa_membership_keeps_both_responsibilities(self):
        permissions = {"requirement.update", "requirement.approve", "testcase.update"}
        policy = {"project_permissions": list(permissions), "role_permissions": {"BA": list(permissions), "QA": list(permissions)}}
        with patch.object(auth, "access_policy", return_value=policy):
            self.assertEqual(auth.permissions_for_role("BA"), {"requirement.update"})
            self.assertNotIn("requirement.update", auth.permissions_for_role("QA"))
            membership = {"project_role": "BA", "project_roles": ["BA", "QA"]}
            self.assertEqual(auth.permissions_for_membership(membership), permissions)

    async def test_active_grant_cannot_bypass_tester_definition_boundary(self):
        repository = common.common_repository
        with (
            patch.object(repository, "find_project", new=AsyncMock(return_value={"_id": "project"})),
            patch.object(repository, "find_membership", new=AsyncMock(return_value={"project_role": "TESTER", "status": "ACTIVE"})),
            patch.object(repository, "find_active_grant", new=AsyncMock(return_value={"permissions": ["testcase.update"]})),
            patch.object(common, "project_permissions", return_value={"testcase.update"}),
            patch.object(common, "audit", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as error:
                await common.get_project("project", SimpleNamespace(id="tester"), "testcase.update")
        self.assertEqual(error.exception.status_code, 403)

    async def test_release_close_is_qa_only_even_with_permission_override(self):
        repository = common.common_repository
        project = {"_id": "project-1", "administrative_status": "ACTIVE"}
        cases = [
            ("BA", ["BA"], "USER", False),
            ("TESTER", ["TESTER"], "USER", False),
            ("DEVELOPER", ["DEVELOPER"], "USER", False),
            ("VIEWER", ["VIEWER"], "USER", False),
            ("BA", ["BA", "QA"], "USER", True),
            ("QA", ["QA"], "USER", True),
            ("BA", ["BA"], "ADMIN", False),
        ]
        with (
            patch.object(repository, "find_project", new=AsyncMock(return_value=project)),
            patch.object(repository, "find_active_grant", new=AsyncMock(return_value=None)),
            patch.object(common, "project_permissions", return_value={"release.close"}),
            patch.object(common, "permissions_for_membership", return_value={"release.close"}),
            patch.object(common, "audit", new=AsyncMock()),
        ):
            for primary_role, roles, system_role, allowed in cases:
                membership = {
                    "project_role": primary_role,
                    "project_roles": roles,
                    "status": "ACTIVE",
                }
                with (
                    self.subTest(roles=roles, system_role=system_role),
                    patch.object(
                        repository,
                        "find_membership",
                        new=AsyncMock(return_value=membership),
                    ),
                ):
                    user = SimpleNamespace(
                        id="user-1",
                        system_role=SimpleNamespace(value=system_role),
                    )
                    if allowed:
                        result = await common.get_project(
                            "project-1", user, "release.close"
                        )
                        self.assertEqual(result, project)
                    else:
                        with self.assertRaises(HTTPException) as error:
                            await common.get_project("project-1", user, "release.close")
                        self.assertEqual(error.exception.status_code, 403)
                        self.assertEqual(
                            error.exception.detail["code"],
                            "PROJECT_PERMISSION_DENIED",
                        )

    async def test_release_close_http_rejects_non_qa_project_roles(self):
        app = FastAPI()
        app.include_router(execution_context_api.router)
        user_holder = {"user": None}

        async def current_user():
            return user_holder["user"]

        app.dependency_overrides[auth.get_current_user] = current_user
        repository = common.common_repository
        project = {"_id": "project-1", "administrative_status": "ACTIVE"}
        cases = [
            ("BA", ["BA"], "USER"),
            ("TESTER", ["TESTER"], "USER"),
            ("DEVELOPER", ["DEVELOPER"], "USER"),
            ("VIEWER", ["VIEWER"], "USER"),
            ("BA", ["BA"], "ADMIN"),
        ]
        with (
            patch.object(
                repository,
                "find_entity_identity",
                new=AsyncMock(return_value={"project_id": "project-1"}),
            ),
            patch.object(repository, "find_project", new=AsyncMock(return_value=project)),
            patch.object(repository, "find_active_grant", new=AsyncMock(return_value=None)),
            patch.object(common, "project_permissions", return_value={"release.close"}),
            patch.object(common, "permissions_for_membership", return_value={"release.close"}),
            patch.object(common, "audit", new=AsyncMock()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                for primary_role, roles, system_role in cases:
                    membership = {
                        "project_role": primary_role,
                        "project_roles": roles,
                        "status": "ACTIVE",
                    }
                    user_holder["user"] = SimpleNamespace(
                        id="user-1",
                        system_role=SimpleNamespace(value=system_role),
                    )
                    with (
                        self.subTest(roles=roles, system_role=system_role),
                        patch.object(
                            repository,
                            "find_membership",
                            new=AsyncMock(return_value=membership),
                        ),
                    ):
                        response = await client.post(
                            "/kiem-thu/ban-phat-hanh/release-1/dong",
                            json={"expected_revision": 1, "reason": "Kiểm tra quyền"},
                        )
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(
                        response.json()["detail"]["code"],
                        "PROJECT_PERMISSION_DENIED",
                    )

    async def test_only_baselined_requirement_versions_emit_change_events(self):
        user = SimpleNamespace(id="qa", _ai_automation_run_id=None)
        version = {"_id": "v1", "project_id": "p1", "requirement_id": "r1", "revision": 1, "status": "DRAFT"}
        with patch.object(ai_automation, "emit_event", new=AsyncMock(return_value=True)) as emit:
            await ai_automation.emit_requirement_changed(version, user)
            await ai_automation.emit_requirement_changed({**version, "revision": 2, "status": "BASELINED"}, user)
        emit.assert_awaited_once()
        self.assertEqual(emit.await_args.args[0], "REQUIREMENT_CHANGED")
        self.assertEqual(emit.await_args.args[1], "requirement-version:v1:2:BASELINED")


if __name__ == "__main__":
    unittest.main()
