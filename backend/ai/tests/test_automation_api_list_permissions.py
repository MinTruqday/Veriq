import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.api.automation import (
    _controllable_definition,
    _readable_run,
    build_automation_workflow_snapshot,
    create_automation_definition,
    create_automation_run,
    get_automation_run,
    list_automation_definitions,
    list_automation_runs,
    list_project_testability_blueprints,
    retry_automation_run,
)
from src.schemas.auth import CurrentUser, SystemRole
from src.schemas.automation import (
    AutomationDefinition,
    AutomationDefinitionRequest,
    AutomationKind,
    AutomationRun,
    AutomationRunRequest,
    AutomationRetryRequest,
    AutomationStatus,
    AutomationTrigger,
)


class AutomationListPermissionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = CurrentUser(_id="user-1", email="user@example.test")
        self.project_access = patch("src.api.automation.project_access", new_callable=AsyncMock)
        self.repository_runs = patch(
            "src.api.automation.automation_repository.list_runs", new_callable=AsyncMock
        )
        self.repository_definitions = patch(
            "src.api.automation.automation_repository.list_definitions", new_callable=AsyncMock
        )
        self.get_run = patch(
            "src.api.automation.automation_repository.get_run", new_callable=AsyncMock
        )
        self.get_definition = patch(
            "src.api.automation.automation_repository.get_definition", new_callable=AsyncMock
        )
        self.project_blueprints = patch(
            "src.api.automation.automation_repository.list_project_blueprints",
            new_callable=AsyncMock,
        )
        self.create_definition = patch(
            "src.api.automation.automation_service.create_definition",
            new_callable=AsyncMock,
        )
        self.create_run = patch(
            "src.api.automation.automation_service.create", new_callable=AsyncMock
        )
        self.access_mock = self.project_access.start()
        self.runs_mock = self.repository_runs.start()
        self.runs_mock.return_value = []
        self.definitions_mock = self.repository_definitions.start()
        self.get_run_mock = self.get_run.start()
        self.get_definition_mock = self.get_definition.start()
        self.project_blueprints_mock = self.project_blueprints.start()
        self.create_definition_mock = self.create_definition.start()
        self.create_run_mock = self.create_run.start()
        self.addCleanup(self.project_access.stop)
        self.addCleanup(self.repository_runs.stop)
        self.addCleanup(self.repository_definitions.stop)
        self.addCleanup(self.get_run.stop)
        self.addCleanup(self.get_definition.stop)
        self.addCleanup(self.project_blueprints.stop)
        self.addCleanup(self.create_definition.stop)
        self.addCleanup(self.create_run.stop)

    @staticmethod
    def make_run(requester="user-1"):
        return AutomationRun(
            automation_run_id="run-1",
            project_id="project-1",
            requester_user_id=requester,
            requester_role="QA",
            execution_user_id=requester,
            execution_role="QA",
            kind=AutomationKind.ON_DEMAND,
            objective="Read automation run state",
        )

    @staticmethod
    def make_definition(owner="user-1"):
        return AutomationDefinition(
            definition_id="definition-1",
            project_id="project-1",
            owner_user_id=owner,
            owner_role="QA",
            name="Requirement event automation",
            trigger=AutomationTrigger.DOCUMENT_INGESTED,
            objective="Process an approved requirement",
        )

    async def test_run_list_denies_member_without_automation_or_proposal_read(self):
        self.access_mock.return_value = ("Tester", ["project.read"])

        with self.assertRaises(HTTPException) as raised:
            await list_automation_runs("project-1", 50, "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)
        self.runs_mock.assert_not_awaited()

    async def test_automation_read_lists_only_requesters_runs(self):
        self.access_mock.return_value = ("Tester", ["automation.read"])

        await list_automation_runs("project-1", 500, "token", self.user)

        self.runs_mock.assert_awaited_once_with(
            "project-1", 100, requester_user_id="user-1"
        )

    async def test_proposal_read_lists_all_project_runs(self):
        self.access_mock.return_value = ("QA", ["proposal.read"])

        await list_automation_runs("project-1", 25, "token", self.user)

        self.runs_mock.assert_awaited_once_with(
            "project-1", 25, requester_user_id=None
        )

    async def test_run_list_includes_workflow_summary_for_visible_rows(self):
        root = self.make_run().model_copy(
            update={"status": AutomationStatus.COMPLETED}
        )
        child = self.make_run().model_copy(
            update={
                "automation_run_id": "child-run",
                "status": AutomationStatus.RUNNING,
                "constraints": {"parent_automation_run_id": root.automation_run_id},
            }
        )
        self.access_mock.return_value = ("QA", ["proposal.read"])
        self.runs_mock.return_value = [root]

        with patch(
            "src.api.automation.automation_repository.list_child_runs",
            new=AsyncMock(side_effect=[[child], []]),
        ):
            result = await list_automation_runs("project-1", 50, "token", self.user)

        self.assertEqual(result[0]["status"], AutomationStatus.COMPLETED.value)
        self.assertEqual(result[0]["workflow"]["status"], AutomationStatus.RUNNING.value)
        self.assertEqual(result[0]["workflow"]["active_count"], 1)

    async def test_definition_list_requires_automation_read(self):
        self.access_mock.return_value = ("Tester", ["project.read"])

        with self.assertRaises(HTTPException) as raised:
            await list_automation_definitions("project-1", "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)
        self.definitions_mock.assert_not_awaited()

    async def test_definition_list_is_available_to_automation_readers(self):
        self.access_mock.return_value = ("QA", ["automation.read"])

        await list_automation_definitions("project-1", "token", self.user)

        self.definitions_mock.assert_awaited_once_with("project-1")

    async def test_platform_admin_can_list_project_runs_without_member_lookup(self):
        admin = CurrentUser(
            _id="admin-1", email="admin@example.test", system_role=SystemRole.ADMIN
        )

        await list_automation_runs("project-1", 50, "token", admin)

        self.access_mock.assert_not_awaited()
        self.runs_mock.assert_awaited_once_with(
            "project-1", 50, requester_user_id=None
        )

    async def test_run_owner_requires_current_project_access_and_automation_read(self):
        self.get_run_mock.return_value = self.make_run()
        self.access_mock.return_value = ("Tester", ["project.read"])

        with self.assertRaises(HTTPException) as raised:
            await _readable_run("run-1", "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)
        self.access_mock.assert_awaited_once_with("project-1", "token")

    async def test_run_owner_can_read_after_live_permission_check(self):
        run = self.make_run()
        self.get_run_mock.return_value = run
        self.access_mock.return_value = ("Tester", ["automation.read"])

        result = await _readable_run("run-1", "token", self.user)

        self.assertIs(result, run)

    async def test_proposal_reader_can_read_another_members_run(self):
        run = self.make_run(requester="another-user")
        self.get_run_mock.return_value = run
        self.access_mock.return_value = ("BA", ["proposal.read"])

        result = await _readable_run("run-1", "token", self.user)

        self.assertIs(result, run)

    def test_workflow_snapshot_stays_running_while_test_design_child_is_running(self):
        root = self.make_run().model_copy(
            update={"status": AutomationStatus.COMPLETED}
        )
        child = self.make_run().model_copy(
            update={
                "automation_run_id": "child-run",
                "status": AutomationStatus.RUNNING,
                "trigger": AutomationTrigger.REQUIREMENT_CHANGED,
                "constraints": {"parent_automation_run_id": root.automation_run_id},
            }
        )

        snapshot = build_automation_workflow_snapshot(root, [child])

        self.assertEqual(snapshot.status, AutomationStatus.RUNNING)
        self.assertFalse(snapshot.terminal)
        self.assertFalse(snapshot.succeeded)
        self.assertEqual(snapshot.active_count, 1)
        self.assertEqual(snapshot.runs[1].parent_automation_run_id, "run-1")

    def test_workflow_snapshot_surfaces_child_failure_after_parent_completion(self):
        root = self.make_run().model_copy(
            update={"status": AutomationStatus.COMPLETED}
        )
        child = self.make_run().model_copy(
            update={
                "automation_run_id": "child-run",
                "status": AutomationStatus.FAILED,
                "error_code": "TEST_CASE_PUBLICATION_FAILED",
                "constraints": {"parent_automation_run_id": root.automation_run_id},
            }
        )

        snapshot = build_automation_workflow_snapshot(root, [child])

        self.assertEqual(snapshot.status, AutomationStatus.FAILED)
        self.assertTrue(snapshot.terminal)
        self.assertFalse(snapshot.succeeded)
        self.assertEqual(snapshot.failed_count, 1)

    def test_workflow_snapshot_waiting_for_clarification_is_resumable_not_terminal(self):
        root = self.make_run().model_copy(
            update={"status": AutomationStatus.AWAITING_INPUT}
        )

        snapshot = build_automation_workflow_snapshot(root, [])

        self.assertEqual(snapshot.status, AutomationStatus.AWAITING_INPUT)
        self.assertFalse(snapshot.terminal)
        self.assertFalse(snapshot.succeeded)
        self.assertEqual(snapshot.blocked_count, 1)

    def test_workflow_snapshot_waiting_for_authorization_is_resumable_not_terminal(self):
        root = self.make_run().model_copy(
            update={"status": AutomationStatus.AWAITING_AUTHORIZATION}
        )

        snapshot = build_automation_workflow_snapshot(root, [])

        self.assertEqual(snapshot.status, AutomationStatus.AWAITING_AUTHORIZATION)
        self.assertFalse(snapshot.terminal)
        self.assertFalse(snapshot.succeeded)
        self.assertEqual(snapshot.blocked_count, 1)

    def test_truncated_workflow_snapshot_never_claims_success(self):
        root = self.make_run().model_copy(
            update={"status": AutomationStatus.COMPLETED}
        )

        snapshot = build_automation_workflow_snapshot(root, [], truncated=True)

        self.assertEqual(snapshot.status, AutomationStatus.DEGRADED)
        self.assertFalse(snapshot.terminal)
        self.assertFalse(snapshot.succeeded)

    async def test_run_detail_includes_live_descendant_workflow_status(self):
        root = self.make_run().model_copy(
            update={"status": AutomationStatus.COMPLETED}
        )
        child = self.make_run().model_copy(
            update={
                "automation_run_id": "child-run",
                "status": AutomationStatus.RUNNING,
                "trigger": AutomationTrigger.REQUIREMENT_CHANGED,
                "constraints": {"parent_automation_run_id": root.automation_run_id},
            }
        )
        self.get_run_mock.return_value = root
        self.access_mock.return_value = ("BA", ["automation.read"])
        with (
            patch(
                "src.api.automation.automation_repository.list_child_runs",
                new=AsyncMock(side_effect=[[child], []]),
            ),
            patch(
                "src.api.automation.automation_repository.list_checkpoints",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.api.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.api.automation.automation_repository.get_receipt",
                new=AsyncMock(return_value=None),
            ),
        ):
            response = await get_automation_run("run-1", "token", self.user)

        self.assertEqual(response["run"].status, AutomationStatus.COMPLETED)
        self.assertEqual(response["workflow"].status, AutomationStatus.RUNNING)
        self.assertEqual(response["workflow"].active_count, 1)

    async def test_definition_owner_must_still_be_project_automation_manager(self):
        self.get_definition_mock.return_value = self.make_definition()
        self.access_mock.return_value = ("Tester", ["project.read", "automation.read"])

        with self.assertRaises(HTTPException) as raised:
            await _controllable_definition("definition-1", "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)

    async def test_definition_owner_with_current_qa_permission_can_manage(self):
        definition = self.make_definition()
        self.get_definition_mock.return_value = definition
        self.access_mock.return_value = ("QA", ["automation.create"])

        result = await _controllable_definition("definition-1", "token", self.user)

        self.assertIs(result, definition)

    async def test_project_blueprint_history_requires_requirement_read(self):
        self.access_mock.return_value = ("Tester", ["project.read"])

        with self.assertRaises(HTTPException) as raised:
            await list_project_testability_blueprints("project-1", 50, "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)
        self.project_blueprints_mock.assert_not_awaited()

    async def test_project_blueprint_history_is_available_to_requirement_readers(self):
        self.access_mock.return_value = ("BA", ["requirement.read"])
        self.project_blueprints_mock.return_value = []

        result = await list_project_testability_blueprints("project-1", 500, "token", self.user)

        self.assertEqual(result["versions"], [])
        self.project_blueprints_mock.assert_awaited_once_with("project-1", 100)

    async def test_automation_definition_creation_requires_create_permission(self):
        self.access_mock.return_value = ("QA", ["automation.read"])
        payload = AutomationDefinitionRequest(
            project_id="project-1",
            name="Document automation",
            trigger=AutomationTrigger.DOCUMENT_INGESTED,
            objective="Process documents when ingested",
        )

        with self.assertRaises(HTTPException) as raised:
            await create_automation_definition(payload, "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)
        self.create_definition_mock.assert_not_awaited()

    async def test_automation_run_creation_requires_create_permission(self):
        self.access_mock.return_value = ("Tester", ["project.read"])
        payload = AutomationRunRequest(
            project_id="project-1", objective="Review the latest requirement source"
        )

        with self.assertRaises(HTTPException) as raised:
            await create_automation_run(payload, "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)
        self.create_run_mock.assert_not_awaited()

    async def test_automation_run_creation_is_event_driven_even_for_authorized_member(self):
        self.access_mock.return_value = ("QA", ["automation.create"])
        payload = AutomationRunRequest(
            project_id="project-1", objective="Review the latest requirement source"
        )

        with self.assertRaises(HTTPException) as raised:
            await create_automation_run(payload, "token", self.user)

        self.assertEqual(raised.exception.status_code, 410)
        self.assertEqual(raised.exception.detail["code"], "DIRECT_AUTOMATION_RUN_RETIRED")
        self.create_run_mock.assert_not_awaited()

    async def test_retry_requires_the_requester_and_current_project_permission(self):
        self.get_run_mock.return_value = self.make_run()
        self.access_mock.return_value = ("QA", ["automation.read"])
        payload = AutomationRetryRequest(expected_revision=3)
        authorize_retry = AsyncMock(return_value={"status": "QUEUED"})

        with patch(
            "src.api.automation.automation_service.authorize_retry",
            new=authorize_retry,
        ):
            result = await retry_automation_run("run-1", payload, "token", self.user)

        self.assertEqual(result, {"status": "QUEUED"})
        authorize_retry.assert_awaited_once_with(self.get_run_mock.return_value, 3)

    async def test_another_project_reader_cannot_retry_a_run(self):
        self.get_run_mock.return_value = self.make_run(requester="another-user")
        self.access_mock.return_value = ("QA", ["proposal.read"])

        with (
            patch(
                "src.api.automation.automation_service.authorize_retry",
                new=AsyncMock(),
            ) as authorize_retry,
            self.assertRaises(HTTPException) as raised,
        ):
            await retry_automation_run(
                "run-1",
                AutomationRetryRequest(expected_revision=3),
                "token",
                self.user,
            )

        self.assertEqual(raised.exception.status_code, 403)
        authorize_retry.assert_not_awaited()

