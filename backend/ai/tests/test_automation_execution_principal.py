import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import jwt
from fastapi import HTTPException

from src.services.automation import AutomationService
from src.services.project_access import project_access


class AutomationExecutionPrincipalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        secret_key_patch = patch(
            "src.services.automation.settings.SECRET_KEY",
            "veriq-test-secret-key-with-at-least-32-bytes",
        )
        secret_key_patch.start()
        self.addCleanup(secret_key_patch.stop)

    async def test_document_event_requests_ba_preparation_identity(self):
        event = SimpleNamespace(requester_user_id="ba", project_id="project-1", trigger="DOCUMENT_INGESTED")
        with (
            patch("src.services.automation.require_operation", new=AsyncMock(return_value={"executor_user_id": "ba"})) as resolve,
            patch("src.services.automation.project_access", new=AsyncMock(return_value=("BA", ["requirement.create"]))),
        ):
            result = await AutomationService()._default_execution_principal(event)
        self.assertEqual(result[0:2], ("ba", "BA"))
        self.assertEqual(resolve.await_args.args[3]["required_role"], "BA")

    async def test_release_event_uses_release_close_as_execution_permission(self):
        event = SimpleNamespace(
            requester_user_id="qa-user",
            project_id="project-1",
            trigger="RELEASE_CHANGED",
        )
        with (
            patch(
                "src.services.automation.require_operation",
                new=AsyncMock(return_value={"executor_user_id": "release-executor"}),
            ),
            patch(
                "src.services.automation.project_access",
                new=AsyncMock(return_value=("RELEASE_OPERATOR", ["release.close"])),
            ) as read_executor_access,
        ):
            principal = await AutomationService()._default_execution_principal(event)

        self.assertEqual(
            principal,
            ("release-executor", "RELEASE_OPERATOR", ["release.close"]),
        )
        self.assertEqual(
            read_executor_access.await_args.kwargs["preferred_role"], "QA"
        )

    async def test_release_event_without_release_close_is_not_dispatched(self):
        event = SimpleNamespace(
            requester_user_id="qa-user",
            project_id="project-1",
            trigger="RELEASE_CHANGED",
        )
        with (
            patch(
                "src.services.automation.require_operation",
                new=AsyncMock(return_value={"executor_user_id": "release-executor"}),
            ),
            patch(
                "src.services.automation.project_access",
                new=AsyncMock(return_value=("RELEASE_OPERATOR", ["ai.generate_testcase"])),
            ),
        ):
            principal = await AutomationService()._default_execution_principal(event)

        self.assertEqual(principal, (None, None, []))

    async def test_work_item_observation_uses_authorized_event_requester(self):
        event = SimpleNamespace(
            requester_user_id="developer",
            project_id="project-1",
            trigger="WORK_ITEM_CHANGED",
        )
        with (
            patch("src.services.automation.require_operation", new=AsyncMock()) as resolve,
            patch("src.services.automation.project_access", new=AsyncMock()) as read_access,
        ):
            principal = await AutomationService()._default_execution_principal(
                event, "DEVELOPER", ["project.read", "workitem.update"]
            )

        self.assertEqual(
            principal,
            ("developer", "DEVELOPER", ["project.read", "workitem.update"]),
        )
        resolve.assert_not_awaited()
        read_access.assert_not_awaited()

    async def test_work_item_observation_without_project_read_is_not_dispatched(self):
        event = SimpleNamespace(
            requester_user_id="developer",
            project_id="project-1",
            trigger="WORK_ITEM_CHANGED",
        )
        principal = await AutomationService()._default_execution_principal(
            event, "DEVELOPER", ["workitem.update"]
        )

        self.assertEqual(principal, (None, None, []))

    async def test_document_event_token_has_only_scoped_publication_rights(self):
        run = SimpleNamespace(
            execution_user_id="ba-user",
            execution_role="BA",
            automation_run_id="run-1",
            requester_user_id="requester",
            definition_id=None,
            project_id="project-1",
            trigger="DOCUMENT_INGESTED",
            source_event_id="requirement-document:RDOC-1:4",
        )
        with (
            patch("src.services.automation.settings.SECRET_KEY", "test-secret-key-with-at-least-32-bytes"),
            patch("src.services.automation.automation_repository.get_run", new=AsyncMock(return_value=run)),
        ):
            token = await AutomationService().token_for("run-1")
        payload = jwt.decode(token, options={"verify_signature": False})
        self.assertEqual(payload["ai_automation_publication_project_id"], "project-1")
        self.assertEqual(payload["ai_automation_source_document_ids"], ["RDOC-1"])
        self.assertEqual(
            set(payload["ai_automation_publication_permissions"]),
            {
                "requirement.submit_review",
                "requirement.approve",
                "testcase.submit_review",
                "testcase.approve",
                "proposal.approve",
            },
        )

    async def test_manual_run_token_cannot_publish(self):
        run = SimpleNamespace(
            execution_user_id="qa-user",
            execution_role="QA",
            automation_run_id="run-2",
            requester_user_id="requester",
            definition_id=None,
            project_id="project-1",
            trigger="MANUAL",
            source_event_id=None,
        )
        with (
            patch("src.services.automation.settings.SECRET_KEY", "test-secret-key-with-at-least-32-bytes"),
            patch("src.services.automation.automation_repository.get_run", new=AsyncMock(return_value=run)),
        ):
            token = await AutomationService().token_for("run-2")
        payload = jwt.decode(token, options={"verify_signature": False})
        self.assertIsNone(payload["ai_automation_publication_project_id"])
        self.assertEqual(payload["ai_automation_publication_permissions"], [])
        self.assertEqual(payload["ai_automation_source_document_ids"], [])

    async def test_worker_token_is_bound_to_the_claimed_revision(self):
        run = SimpleNamespace(
            execution_user_id="qa-user",
            execution_role="QA",
            automation_run_id="run-fenced",
            requester_user_id="requester",
            definition_id=None,
            project_id="project-1",
            trigger="MANUAL",
            source_event_id=None,
            status="RUNNING",
            revision=12,
        )
        with (
            patch("src.services.automation.settings.SECRET_KEY", "test-secret-key-with-at-least-32-bytes"),
            patch("src.services.automation.automation_repository.get_run", new=AsyncMock(return_value=run)),
        ):
            token = await AutomationService().token_for("run-fenced", worker_revision=12)

        payload = jwt.decode(token, options={"verify_signature": False})
        self.assertEqual(payload["ai_automation_worker_revision"], 12)

    async def test_test_plan_change_token_has_only_test_plan_approval_scope(self):
        run = SimpleNamespace(
            execution_user_id="qa-user",
            execution_role="QA",
            automation_run_id="run-plan-change",
            requester_user_id="requester",
            definition_id=None,
            project_id="project-1",
            trigger="TEST_PLAN_CHANGED",
            source_event_id="test-plan:plan-1:1:TEST_PLAN_CHANGED",
        )
        with (
            patch("src.services.automation.settings.SECRET_KEY", "test-secret-key-with-at-least-32-bytes"),
            patch("src.services.automation.automation_repository.get_run", new=AsyncMock(return_value=run)),
        ):
            token = await AutomationService().token_for(run.automation_run_id)
        payload = jwt.decode(token, options={"verify_signature": False})
        self.assertEqual(payload["ai_automation_publication_project_id"], "project-1")
        self.assertEqual(payload["ai_automation_publication_permissions"], ["testplan.approve"])

    async def test_release_change_token_has_only_release_gate_scope(self):
        run = SimpleNamespace(
            execution_user_id="qa-user",
            execution_role="QA",
            automation_run_id="run-release-change",
            requester_user_id="requester",
            definition_id=None,
            project_id="project-1",
            trigger="RELEASE_CHANGED",
            source_event_id="release:release-1:1:RELEASE_CHANGED",
        )
        with (
            patch("src.services.automation.settings.SECRET_KEY", "test-secret-key-with-at-least-32-bytes"),
            patch("src.services.automation.automation_repository.get_run", new=AsyncMock(return_value=run)),
        ):
            token = await AutomationService().token_for(run.automation_run_id)
        payload = jwt.decode(token, options={"verify_signature": False})
        self.assertEqual(payload["ai_automation_publication_project_id"], "project-1")
        self.assertEqual(
            set(payload["ai_automation_publication_permissions"]),
            {"release.close", "testmonitor.snapshot.create", "testcompletion.create"},
        )

    async def test_ba_event_uses_the_active_project_qa_as_execution_principal(self):
        event = SimpleNamespace(
            requester_user_id="ba-user", project_id="project-1"
        )
        with (
            patch(
                "src.services.automation.require_operation",
                new=AsyncMock(return_value={"executor_user_id": "qa-user"}),
            ) as resolve_principal,
            patch(
                "src.services.automation.project_access",
                new=AsyncMock(return_value=("QA", ["requirement.approve", "testcase.approve"])),
            ) as read_executor_access,
        ):
            execution_user_id, execution_role, execution_permissions = (
                await AutomationService()._default_execution_principal(
                    event, "BA", ["requirement.create"]
                )
            )

        self.assertEqual(execution_user_id, "qa-user")
        self.assertEqual(execution_role, "QA")
        self.assertEqual(execution_permissions, ["requirement.approve", "testcase.approve"])
        self.assertEqual(
            resolve_principal.await_args.args[1],
            "/noi-bo/quan-tri/tu-dong-hoa/du-an/project-1/nguoi-thuc-thi",
        )
        self.assertEqual(read_executor_access.await_args.args[0], "project-1")

    async def test_ba_qa_member_can_remain_the_same_execution_principal(self):
        event = SimpleNamespace(
            requester_user_id="member-ba-qa",
            project_id="project-1",
            trigger="DOCUMENT_INGESTED",
        )
        with (
            patch(
                "src.services.automation.require_operation",
                new=AsyncMock(return_value={"executor_user_id": event.requester_user_id}),
            ),
            patch(
                "src.services.automation.project_access",
                new=AsyncMock(return_value=("BA", ["requirement.create", "testcase.approve"])),
            ) as read_executor_access,
        ):
            principal = await AutomationService()._default_execution_principal(
                event, "QA", ["requirement.approve"]
            )

        self.assertEqual(principal[0], event.requester_user_id)
        self.assertEqual(principal[1], "BA")
        self.assertEqual(
            read_executor_access.await_args.kwargs["preferred_role"], "BA"
        )

    async def test_member_with_ba_and_qa_roles_can_run_the_full_workflow_as_self(self):
        event = SimpleNamespace(requester_user_id="member-ba-qa", project_id="project-1")
        permissions = ["requirement.create", "requirement.approve", "testcase.approve"]
        project_context = {
            "project": {
                "_id": "project-1",
                "current_membership": {
                    "user_id": event.requester_user_id,
                    "project_role": "BA",
                    "project_roles": ["BA", "QA"],
                },
                "current_permissions": permissions,
            }
        }

        with patch(
            "src.services.project_access.get_project_context",
            new=SimpleNamespace(
                ainvoke=AsyncMock(return_value=json.dumps(project_context))
            ),
        ):
            role, live_permissions = await project_access("project-1", "session-token")

        with (
            patch(
                "src.services.automation.require_operation",
                new=AsyncMock(return_value={"executor_user_id": event.requester_user_id}),
            ),
            patch(
                "src.services.automation.project_access",
                new=AsyncMock(return_value=("QA", permissions)),
            ),
        ):
            execution_user_id, execution_role, execution_permissions = (
                await AutomationService()._default_execution_principal(
                    event, role, live_permissions
                )
            )

        self.assertEqual(execution_user_id, event.requester_user_id)
        self.assertEqual(execution_role, "QA")
        self.assertEqual(set(execution_permissions), set(permissions))

    async def test_project_access_honors_stage_role_for_dual_role_member(self):
        context = {
            "project": {
                "_id": "project-1",
                "current_membership": {
                    "project_role": "BA",
                    "project_roles": ["BA", "QA"],
                },
                "current_permissions": ["requirement.create", "ai.generate_testcase"],
            }
        }
        with patch(
            "src.services.project_access.get_project_context",
            new=SimpleNamespace(ainvoke=AsyncMock(return_value=json.dumps(context))),
        ):
            ba_role, _ = await project_access(
                "project-1", "session-token", preferred_role="BA"
            )
            qa_role, _ = await project_access(
                "project-1", "session-token", preferred_role="QA"
            )

        self.assertEqual(ba_role, "BA")
        self.assertEqual(qa_role, "QA")

    async def test_project_access_does_not_fallback_when_stage_role_was_revoked(self):
        context = {
            "project": {
                "_id": "project-1",
                "current_membership": {
                    "project_role": "QA",
                    "project_roles": ["QA"],
                },
                "current_permissions": ["ai.generate_testcase"],
            }
        }
        with patch(
            "src.services.project_access.get_project_context",
            new=SimpleNamespace(ainvoke=AsyncMock(return_value=json.dumps(context))),
        ):
            with self.assertRaises(HTTPException) as raised:
                await project_access(
                    "project-1", "session-token", preferred_role="BA"
                )

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail["code"], "PROJECT_ROLE_NOT_ACTIVE")


if __name__ == "__main__":
    unittest.main()
