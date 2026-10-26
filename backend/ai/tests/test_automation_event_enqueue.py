import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from src.api.automation import receive_automation_event
from src.schemas.automation import (
    AutomationEventAcceptedResponse,
    AutomationEventRequest,
    AutomationEventSuppressedResponse,
    AutomationStatus,
    AutomationTrigger,
)
from src.services.automation import AutomationService


class AutomationEventEnqueueTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        secret_key_patch = patch(
            "src.services.automation.settings.SECRET_KEY",
            "veriq-test-secret-key-with-at-least-32-bytes",
        )
        secret_key_patch.start()
        self.addCleanup(secret_key_patch.stop)

    def make_event(self):
        return AutomationEventRequest(
            event_id="test-case:TC-1:2:TEST_CASE_CHANGED",
            project_id="project-1",
            requester_user_id="ba-user",
            trigger=AutomationTrigger.TEST_CASE_CHANGED,
            target_artifact_ids=["TC-1"],
            evidence=[
                {
                    "artifact_type": "test_case_draft",
                    "artifact_id": "TC-1",
                    "artifact_version_id": "TC-1-v2",
                    "source": "database",
                    "authority": "project",
                    "score": 1,
                    "text": "Saved Test Case draft",
                    "relationship_path": ["source-root", "source-v2", "source-v3"],
                    "project_id": "project-1",
                }
            ],
        )

    def make_existing_event_run(self, event, status, automation_run_id):
        return SimpleNamespace(
            status=status,
            automation_run_id=automation_run_id,
            project_id=event.project_id,
            source_event_id=event.event_id,
            requester_user_id=event.requester_user_id,
            trigger=event.trigger,
            constraints={},
            target_artifact_ids=list(event.target_artifact_ids),
            evidence=list(event.evidence),
        )

    async def test_new_event_is_persisted_and_published_for_the_project_qa_executor(self):
        service = AutomationService()
        with (
            patch(
                "src.services.automation.project_access",
                new=AsyncMock(return_value=("BA", ["project.read"])),
            ),
            patch.object(
                service,
                "_default_execution_principal",
                new=AsyncMock(return_value=("qa-user", "QA", ["testcase.lint"])),
            ),
            patch(
                "src.services.automation.automation_repository.find_event_run",
                new=AsyncMock(side_effect=[None, None]),
            ),
            patch(
                "src.services.automation.automation_repository.list_definitions",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.automation.automation_repository.create_run_with_checkpoint",
                new=AsyncMock(side_effect=lambda run, **_: run),
            ) as create_run,
            patch(
                "src.services.automation.mq.publish", new=AsyncMock(return_value=True)
            ) as publish,
        ):
            runs = await service.enqueue_event(self.make_event())

        self.assertEqual(len(runs), 1)
        run = runs[0]
        self.assertEqual(run.status, AutomationStatus.QUEUED)
        self.assertEqual(run.requester_user_id, "ba-user")
        self.assertEqual(run.execution_user_id, "qa-user")
        self.assertEqual(run.execution_role, "QA")
        self.assertEqual(run.trigger, AutomationTrigger.TEST_CASE_CHANGED)
        self.assertTrue(run.source_event_verified)
        self.assertEqual(run.source_event_id, "test-case:TC-1:2:TEST_CASE_CHANGED")
        self.assertEqual(
            run.evidence[0].relationship_path,
            ["source-root", "source-v2", "source-v3"],
        )
        create_run.assert_awaited_once()
        publish.assert_awaited_once_with(
            "ai.automation", {"automation_run_id": run.automation_run_id}
        )

    async def test_duplicate_completed_event_is_not_queued_twice(self):
        service = AutomationService()
        event = self.make_event()
        existing = self.make_existing_event_run(
            event, AutomationStatus.COMPLETED, "run-existing"
        )
        with (
            patch(
                "src.services.automation.automation_repository.find_event_run",
                new=AsyncMock(return_value=existing),
            ),
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
            patch("src.services.automation.project_access", new=AsyncMock()) as access,
        ):
            runs = await service.enqueue_event(event)

        self.assertEqual(runs, [existing])
        publish.assert_not_awaited()
        access.assert_not_awaited()

    async def test_duplicate_queued_event_republishes_the_existing_run_only(self):
        service = AutomationService()
        event = self.make_event()
        existing = self.make_existing_event_run(
            event, AutomationStatus.QUEUED, "run-queued-existing"
        )
        with (
            patch(
                "src.services.automation.automation_repository.find_event_run",
                new=AsyncMock(return_value=existing),
            ),
            patch(
                "src.services.automation.automation_repository.create_run_with_checkpoint",
                new=AsyncMock(),
            ) as create_run,
            patch("src.services.automation.mq.publish", new=AsyncMock(return_value=True)) as publish,
            patch("src.services.automation.project_access", new=AsyncMock()) as access,
        ):
            runs = await service.enqueue_event(event)

        self.assertEqual(runs, [existing])
        create_run.assert_not_awaited()
        publish.assert_awaited_once_with(
            "ai.automation",
            {"automation_run_id": "run-queued-existing"},
        )
        access.assert_not_awaited()

    async def test_reused_event_id_with_changed_evidence_is_rejected(self):
        service = AutomationService()
        event = self.make_event()
        existing = self.make_existing_event_run(
            event, AutomationStatus.COMPLETED, "run-existing"
        )
        changed_event = event.model_copy(deep=True)
        changed_event.evidence[0].text = "Different saved source content"
        with (
            patch(
                "src.services.automation.automation_repository.find_event_run",
                new=AsyncMock(return_value=existing),
            ),
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.enqueue_event(changed_event)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(
            error.exception.detail["code"], "AUTOMATION_EVENT_ID_REUSE_CONFLICT"
        )
        publish.assert_not_awaited()

    async def test_disabled_matching_trigger_is_suppressed_without_creating_a_run(self):
        service = AutomationService()
        disabled_definition = type(
            "Definition",
            (),
            {"trigger": AutomationTrigger.TEST_CASE_CHANGED, "enabled": False},
        )()
        with (
            patch(
                "src.services.automation.automation_repository.find_event_run",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.automation.project_access",
                new=AsyncMock(return_value=("BA", ["project.read"])),
            ),
            patch.object(
                service,
                "_default_execution_principal",
                new=AsyncMock(return_value=("qa-user", "QA", ["testcase.lint"])),
            ),
            patch(
                "src.services.automation.automation_repository.list_definitions",
                new=AsyncMock(return_value=[disabled_definition]),
            ),
            patch(
                "src.services.automation.automation_repository.create_run_with_checkpoint",
                new=AsyncMock(),
            ) as create_run,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            runs = await service.enqueue_event(self.make_event())

        self.assertEqual(runs, [])
        create_run.assert_not_awaited()
        publish.assert_not_awaited()

    async def test_internal_event_api_explains_suppressed_trigger(self):
        with patch(
            "src.api.automation.automation_service.enqueue_event",
            new=AsyncMock(return_value=[]),
        ):
            result = await receive_automation_event(self.make_event())

        self.assertEqual(
            result,
            {
                "status": "suppressed",
                "reason_code": "AUTOMATION_TRIGGER_DISABLED",
                "runs": [],
            },
        )

    async def test_internal_event_api_confirms_created_run_ids(self):
        run = type("Run", (), {"automation_run_id": "run-1", "status": AutomationStatus.QUEUED})()
        with patch(
            "src.api.automation.automation_service.enqueue_event",
            new=AsyncMock(return_value=[run]),
        ):
            result = await receive_automation_event(self.make_event())

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["runs"], [run])

    def test_event_response_contract_rejects_ambiguous_outcomes(self):
        with self.assertRaises(ValidationError):
            AutomationEventAcceptedResponse(runs=[])
        with self.assertRaises(ValidationError):
            AutomationEventSuppressedResponse(
                reason_code="AUTOMATION_TRIGGER_DISABLED",
                runs=[object()],
            )

    async def test_event_with_cross_project_evidence_is_rejected_before_dispatch(self):
        service = AutomationService()
        event = self.make_event()
        event.evidence[0].project_id = "other-project"
        with (
            patch(
                "src.services.automation.automation_repository.find_event_run", new=AsyncMock()
            ) as find_run,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.enqueue_event(event)

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.detail["code"], "AUTOMATION_EVIDENCE_PROJECT_MISMATCH")
        find_run.assert_not_awaited()
        publish.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
