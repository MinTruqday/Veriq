import unittest
from unittest.mock import AsyncMock, patch

from src.api.automation import get_internal_run_execution_status
from src.schemas.automation import (
    AutomationKind,
    AutomationRun,
    AutomationStatus,
    AutomationTrigger,
)
from src.services.automation import AutomationService


def document_run(status=AutomationStatus.RUNNING, revision=4):
    return AutomationRun(
        project_id="project-1",
        requester_user_id="ba-1",
        requester_role="BA",
        execution_user_id="ba-1",
        execution_role="BA",
        kind=AutomationKind.EVENT,
        trigger=AutomationTrigger.DOCUMENT_INGESTED,
        source_event_id="requirement-document:document-1:7",
        objective="Process an authorized source document",
        status=status,
        revision=revision,
    )


class AutomationDocumentConsentRevocationTests(unittest.IsolatedAsyncioTestCase):
    async def test_internal_status_contract_allows_queue_preflight_and_running_only(self):
        queued = document_run(status=AutomationStatus.QUEUED)
        running = document_run(status=AutomationStatus.RUNNING)
        cancelled = document_run(status=AutomationStatus.CANCELLED)
        with patch(
            "src.api.automation.automation_repository.get_run",
            new=AsyncMock(side_effect=[queued, running, cancelled]),
        ):
            queued_result = await get_internal_run_execution_status(
                queued.automation_run_id
            )
            running_result = await get_internal_run_execution_status(
                running.automation_run_id
            )
            cancelled_result = await get_internal_run_execution_status(
                cancelled.automation_run_id
            )

        self.assertTrue(queued_result["active"])
        self.assertTrue(running_result["active"])
        self.assertFalse(cancelled_result["active"])

    async def test_revocation_cancels_dispatched_run_and_persists_final_checkpoint(self):
        running = document_run()
        cancelled = running.model_copy(
            update={
                "status": AutomationStatus.CANCELLED,
                "error_code": "AI_READ_PERMISSION_REVOKED",
                "revision": running.revision + 1,
            }
        )
        with (
            patch(
                "src.services.automation.automation_repository.list_incomplete_document_ingestion_runs",
                new=AsyncMock(return_value=[running]),
            ) as listing,
            patch.object(
                AutomationService, "_revoke_testing_run_access", new=AsyncMock()
            ) as revoke_access,
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=cancelled),
            ) as transition,
        ):
            count = await AutomationService().cancel_document_ingestion_runs("document-1")

        self.assertEqual(count, 1)
        listing.assert_awaited_once_with("document-1")
        revoke_access.assert_awaited_once_with(running.automation_run_id)
        self.assertEqual(
            transition.await_args.kwargs["phase"].value,
            "FINALIZED",
        )
        self.assertEqual(
            transition.await_args.kwargs["detail"]["reason_code"],
            "AI_READ_PERMISSION_REVOKED",
        )
        self.assertEqual(
            transition.await_args.args[2]["status"], AutomationStatus.CANCELLED
        )

    async def test_run_conflict_reloads_and_preserves_a_completed_run(self):
        running = document_run()
        completed = document_run(status=AutomationStatus.COMPLETED, revision=5)
        with (
            patch(
                "src.services.automation.automation_repository.list_incomplete_document_ingestion_runs",
                new=AsyncMock(return_value=[running]),
            ),
            patch.object(
                AutomationService, "_revoke_testing_run_access", new=AsyncMock()
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=None),
            ) as transition,
            patch(
                "src.services.automation.automation_repository.get_run",
                new=AsyncMock(return_value=completed),
            ) as reread,
        ):
            count = await AutomationService().cancel_document_ingestion_runs("document-1")

        self.assertEqual(count, 0)
        transition.assert_awaited_once()
        reread.assert_awaited_once_with(running.automation_run_id)

    async def test_cancellation_conflict_does_not_report_success(self):
        running = document_run()
        with (
            patch(
                "src.services.automation.automation_repository.list_incomplete_document_ingestion_runs",
                new=AsyncMock(return_value=[running]),
            ),
            patch.object(
                AutomationService, "_revoke_testing_run_access", new=AsyncMock()
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.automation.automation_repository.get_run",
                new=AsyncMock(return_value=running),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "DOCUMENT_INGESTION_RUN_CANCELLATION_CONFLICT"
            ):
                await AutomationService().cancel_document_ingestion_runs("document-1")

    async def test_run_transition_is_not_attempted_when_testing_requests_do_not_drain(self):
        running = document_run()
        with (
            patch(
                "src.services.automation.automation_repository.list_incomplete_document_ingestion_runs",
                new=AsyncMock(return_value=[running]),
            ),
            patch.object(
                AutomationService,
                "_revoke_testing_run_access",
                new=AsyncMock(side_effect=RuntimeError("in-flight request did not drain")),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
        ):
            with self.assertRaisesRegex(RuntimeError, "did not drain"):
                await AutomationService().cancel_document_ingestion_runs("document-1")

        transition.assert_not_awaited()

    async def test_cancelled_run_is_still_fenced_for_a_request_already_in_flight(self):
        cancelled = document_run(status=AutomationStatus.CANCELLED)
        with (
            patch(
                "src.services.automation.automation_repository.list_incomplete_document_ingestion_runs",
                new=AsyncMock(return_value=[cancelled]),
            ),
            patch.object(
                AutomationService, "_revoke_testing_run_access", new=AsyncMock()
            ) as revoke_access,
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
        ):
            count = await AutomationService().cancel_document_ingestion_runs("document-1")

        self.assertEqual(count, 0)
        revoke_access.assert_awaited_once_with(cancelled.automation_run_id)
        transition.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
