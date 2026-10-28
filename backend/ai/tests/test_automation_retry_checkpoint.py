import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException

from src.agents.runner.automation_graph import (
    project_source_evidence,
    safety_inspection_evidence,
)
from src.schemas.agent import VeriqRunState
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationClarificationResponseRequest,
    AutomationFact,
    AutomationGraphSnapshot,
    AutomationKind,
    AutomationRun,
    AutomationStatus,
    AutomationUncertainty,
    EvidenceItem,
)
from src.services.automation import AutomationService


class AutomationRetryCheckpointTests(unittest.IsolatedAsyncioTestCase):
    def test_safety_inspection_uses_sources_and_clarifications_not_tool_output(self):
        document = {
            "artifact_type": "requirement_document",
            "artifact_id": "RDOC-1",
            "authority": "PROJECT_REFERENCE",
        }
        tool_output = {
            "artifact_type": "tool_result",
            "artifact_id": "TASK-1",
            "authority": "verified_tool:process_ingested_requirement_document",
        }
        clarification = {
            "artifact_type": "automation_clarification",
            "artifact_id": "CLARIFICATION-1",
            "authority": "user_clarification",
        }

        result = safety_inspection_evidence(
            [document, tool_output, clarification], set()
        )

        self.assertEqual(result, [document, clarification])
        self.assertEqual(project_source_evidence([document, tool_output, clarification], set()), [document])

    def make_run(self, status=AutomationStatus.FAILED, error_code="AUTOMATION_EXECUTION_FAILED"):
        return AutomationRun(
            automation_run_id="AUT-RETRY-1",
            project_id="PRJ-1",
            requester_user_id="USER-1",
            requester_role="QA",
            execution_user_id="USER-1",
            execution_role="QA",
            kind=AutomationKind.EVENT,
            objective="Tiếp tục luồng tự động hóa",
            status=status,
            error_code=error_code,
            revision=3,
        )

    def make_snapshot(self, phase=AutomationCheckpointPhase.ACTIONS_EXECUTED):
        run = VeriqRunState(
            run_id="AUT-RETRY-1",
            project_id="PRJ-1",
            user_id="USER-1",
            role="QA",
            objective="Tiếp tục luồng tự động hóa",
        )
        return AutomationGraphSnapshot(completed_phase=phase, run=run)

    async def test_answerable_nonblocking_uncertainty_resumes_awaiting_run(self):
        service = AutomationService()
        run = self.make_run(
            status=AutomationStatus.AWAITING_INPUT,
            error_code="AUTOMATION_WAITING_FOR_INPUT",
        )
        run = run.model_copy(
            update={
                "revision": 4,
                "evidence": [
                    EvidenceItem(
                        artifact_type="requirement_document",
                        artifact_id="RDOC-1",
                        source="database",
                        authority="PROJECT_REFERENCE",
                        text="Source text",
                        project_id="PRJ-1",
                    )
                ],
            }
        )
        uncertainty = AutomationUncertainty(
            code="LOCKOUT_THRESHOLD",
            question="What is the account lockout threshold?",
            reason="The source says repeated attempts without a number.",
            blocking=False,
            response_allowed=True,
        )
        snapshot = self.make_snapshot(AutomationCheckpointPhase.FINALIZED).model_copy(
            update={
                "uncertainties": [uncertainty],
                "source_facts": [
                    AutomationFact(
                        automation_run_id=run.automation_run_id,
                        project_id=run.project_id,
                        artifact_type="requirement_document",
                        artifact_id="RDOC-1",
                        artifact_version_id="RDOC-1",
                        source="database",
                        authority="PROJECT_REFERENCE",
                        quote="Source text",
                    )
                ],
            }
        )
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.FINALIZED,
            status=AutomationStatus.AWAITING_INPUT,
            state_snapshot=snapshot,
        )
        queued = run.model_copy(
            update={"status": AutomationStatus.QUEUED, "error_code": None, "revision": 5}
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=queued),
            ) as transition,
            patch("src.services.automation.mq.publish", new=AsyncMock(return_value=True)),
        ):
            result = await service.provide_clarification(
                run,
                AutomationClarificationResponseRequest(
                    expected_revision=4,
                    uncertainty_code="LOCKOUT_THRESHOLD",
                    answer="Five consecutive failed attempts.",
                ),
                "USER-BA",
            )

        self.assertEqual(result.status, AutomationStatus.QUEUED)
        self.assertEqual(
            transition.await_args.kwargs["detail"]["reason_code"],
            "AUTOMATION_RESUMED_WITH_USER_CLARIFICATION",
        )
        resumed_snapshot = transition.await_args.kwargs["state_snapshot"]
        self.assertEqual(
            resumed_snapshot.completed_phase,
            AutomationCheckpointPhase.FACTS_EXTRACTED,
        )
        self.assertEqual(
            transition.await_args.kwargs["detail"]["resuming_after"],
            AutomationCheckpointPhase.FACTS_EXTRACTED.value,
        )
        clarification_response = transition.await_args.args[2]["constraints"][
            "clarification_responses"
        ][0]
        self.assertEqual(clarification_response["question"], uncertainty.question)
        self.assertEqual(clarification_response["reason"], uncertainty.reason)
        self.assertEqual(clarification_response["answer"], "Five consecutive failed attempts.")
        self.assertEqual(resumed_snapshot.uncertainties[0].resolution_status, "USER_ANSWERED")
        self.assertEqual(resumed_snapshot.uncertainties[0].answer, "Five consecutive failed attempts.")
        self.assertTrue(
            all(
                isinstance(item, dict)
                for item in transition.await_args.args[2]["evidence"]
            )
        )

    async def test_nonanswerable_uncertainty_does_not_resume_run(self):
        service = AutomationService()
        run = self.make_run(
            status=AutomationStatus.AWAITING_INPUT,
            error_code="AUTOMATION_WAITING_FOR_INPUT",
        )
        uncertainty = AutomationUncertainty(
            code="SOURCE_ACCESS",
            question="Can the source be read?",
            reason="The source is not authorized.",
            blocking=False,
            response_allowed=False,
        )
        snapshot = self.make_snapshot(AutomationCheckpointPhase.FINALIZED).model_copy(
            update={"uncertainties": [uncertainty]}
        )
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.FINALIZED,
            status=AutomationStatus.AWAITING_INPUT,
            state_snapshot=snapshot,
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.provide_clarification(
                    run,
                    AutomationClarificationResponseRequest(
                        expected_revision=3,
                        uncertainty_code="SOURCE_ACCESS",
                        answer="Please allow access.",
                    ),
                    "USER-BA",
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(
            error.exception.detail["code"],
            "AUTOMATION_CLARIFICATION_REQUIRES_SOURCE_OR_SYSTEM_RECOVERY",
        )
        transition.assert_not_awaited()

    async def test_retry_preserves_last_safe_snapshot_for_worker_resume(self):
        service = AutomationService()
        run = self.make_run()
        snapshot = self.make_snapshot()
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.ACTIONS_EXECUTED,
            status=AutomationStatus.RUNNING,
            state_snapshot=snapshot,
        )
        queued = run.model_copy(
            update={"status": AutomationStatus.QUEUED, "error_code": None, "revision": 4}
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=queued),
            ) as transition,
            patch("src.services.automation.mq.publish", new=AsyncMock(return_value=True)),
        ):
            result = await service.authorize_retry(run, expected_revision=3)

        self.assertEqual(result.status, AutomationStatus.QUEUED)
        self.assertEqual(transition.await_args.kwargs["phase"], AutomationCheckpointPhase.QUEUED)
        self.assertEqual(transition.await_args.kwargs["state_snapshot"], snapshot)
        self.assertEqual(
            transition.await_args.kwargs["detail"]["reason_code"],
            "AUTOMATION_RESUMED_FROM_CHECKPOINT",
        )

    async def test_retry_refuses_checkpoint_before_unknown_mutation_outcome(self):
        service = AutomationService()
        run = self.make_run()
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.ACTION_STARTED,
            status=AutomationStatus.RUNNING,
            detail={"action": "MUTATE", "task_has_mutation": True},
            state_snapshot=self.make_snapshot(AutomationCheckpointPhase.ACTION_STARTED),
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.authorize_retry(run, expected_revision=3)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(
            error.exception.detail["code"], "AUTOMATION_RETRY_REQUIRES_RECONCILIATION"
        )
        transition.assert_not_awaited()
        publish.assert_not_awaited()

    async def test_retry_refuses_failed_run_without_a_durable_checkpoint(self):
        service = AutomationService()
        run = self.make_run()
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.authorize_retry(run, expected_revision=3)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(
            error.exception.detail["code"], "AUTOMATION_RETRY_REQUIRES_RECONCILIATION"
        )
        transition.assert_not_awaited()
        publish.assert_not_awaited()

    async def test_retry_refuses_finalized_checkpoint_without_resume_snapshot(self):
        service = AutomationService()
        run = self.make_run()
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.FINALIZED,
            status=AutomationStatus.FAILED,
            detail={"reason_code": "AUTOMATION_WORKER_FAILED", "resumable": False},
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.authorize_retry(run, expected_revision=3)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(
            error.exception.detail["code"], "AUTOMATION_RETRY_REQUIRES_RECONCILIATION"
        )
        transition.assert_not_awaited()
        publish.assert_not_awaited()

    async def test_queue_publish_failure_preserves_the_resumable_snapshot(self):
        service = AutomationService()
        run = self.make_run()
        snapshot = self.make_snapshot()
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.ACTIONS_EXECUTED,
            status=AutomationStatus.RUNNING,
            state_snapshot=snapshot,
        )
        queued = run.model_copy(
            update={"status": AutomationStatus.QUEUED, "error_code": None, "revision": 4}
        )
        degraded = queued.model_copy(
            update={
                "status": AutomationStatus.DEGRADED,
                "error_code": "AUTOMATION_QUEUE_UNAVAILABLE",
                "revision": 5,
            }
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(side_effect=[queued, degraded]),
            ) as transition_with_checkpoint,
            patch("src.services.automation.mq.publish", new=AsyncMock(return_value=False)),
        ):
            result = await service.authorize_retry(run, expected_revision=3)

        self.assertEqual(result.status, AutomationStatus.DEGRADED)
        self.assertEqual(
            transition_with_checkpoint.await_args.kwargs["phase"],
            AutomationCheckpointPhase.FINALIZED,
        )
        self.assertEqual(transition_with_checkpoint.await_args.kwargs["state_snapshot"], snapshot)

    async def test_authorization_retry_may_start_without_workflow_checkpoint(self):
        service = AutomationService()
        run = self.make_run(
            status=AutomationStatus.AWAITING_AUTHORIZATION,
            error_code="AUTHORIZATION_EXPIRED",
        )
        queued = run.model_copy(
            update={"status": AutomationStatus.QUEUED, "error_code": None, "revision": 4}
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=queued),
            ) as transition,
            patch("src.services.automation.mq.publish", new=AsyncMock(return_value=True)),
        ):
            result = await service.authorize_retry(run, expected_revision=3)

        self.assertEqual(result.status, AutomationStatus.QUEUED)
        self.assertIsNone(transition.await_args.kwargs["state_snapshot"])
        self.assertEqual(
            transition.await_args.kwargs["detail"]["reason_code"],
            "AUTOMATION_RETRY_STARTED",
        )

    async def test_authorization_retry_preserves_completed_graph_without_replaying_actions(self):
        service = AutomationService()
        run = self.make_run(
            status=AutomationStatus.AWAITING_AUTHORIZATION,
            error_code="PROJECT_ACCESS_REVOKED_DURING_RUN",
        )
        snapshot = self.make_snapshot(AutomationCheckpointPhase.GRAPH_COMPLETED)
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.FINALIZED,
            status=AutomationStatus.AWAITING_AUTHORIZATION,
            state_snapshot=snapshot,
        )
        queued = run.model_copy(
            update={"status": AutomationStatus.QUEUED, "error_code": None, "revision": 4}
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=queued),
            ) as transition,
            patch("src.services.automation.mq.publish", new=AsyncMock(return_value=True)),
        ):
            result = await service.authorize_retry(run, expected_revision=3)

        self.assertEqual(result.status, AutomationStatus.QUEUED)
        retry_checkpoint = transition.await_args.kwargs["state_snapshot"]
        self.assertEqual(retry_checkpoint, snapshot)
        self.assertEqual(
            retry_checkpoint.completed_phase,
            AutomationCheckpointPhase.GRAPH_COMPLETED,
        )

    async def test_authorization_retry_refuses_uncertain_mutation_from_prior_attempt(self):
        service = AutomationService()
        run = self.make_run(
            status=AutomationStatus.AWAITING_AUTHORIZATION,
            error_code="AUTHORIZATION_EXPIRED",
        )
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.ACTION_STARTED,
            status=AutomationStatus.RUNNING,
            detail={"action": "MUTATE", "task_has_mutation": True},
            state_snapshot=self.make_snapshot(AutomationCheckpointPhase.ACTION_STARTED),
        )
        with (
            patch(
                "src.services.automation.automation_repository.latest_checkpoint",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.authorize_retry(run, expected_revision=3)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(
            error.exception.detail["code"], "AUTOMATION_RETRY_REQUIRES_RECONCILIATION"
        )
        transition.assert_not_awaited()
        publish.assert_not_awaited()

    async def test_running_cancel_drains_run_scoped_actions_before_final_transition(self):
        service = AutomationService()
        run = self.make_run(status=AutomationStatus.RUNNING, error_code=None)
        cancelled = run.model_copy(
            update={"status": AutomationStatus.CANCELLED, "revision": 4}
        )
        with (
            patch.object(
                service, "_revoke_testing_run_access", new=AsyncMock()
            ) as revoke,
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(return_value=cancelled),
            ) as transition,
        ):
            result = await service.cancel(run, expected_revision=3)

        self.assertEqual(result.status, AutomationStatus.CANCELLED)
        revoke.assert_awaited_once_with(run.automation_run_id)
        self.assertEqual(
            transition.await_args.kwargs["phase"], AutomationCheckpointPhase.FINALIZED
        )
        self.assertEqual(
            transition.await_args.kwargs["detail"]["reason_code"],
            "AUTOMATION_CANCELLED",
        )

    async def test_running_cancel_does_not_mark_cancelled_when_action_drain_fails(self):
        service = AutomationService()
        run = self.make_run(status=AutomationStatus.RUNNING, error_code=None)
        with (
            patch.object(
                service,
                "_revoke_testing_run_access",
                new=AsyncMock(
                    side_effect=httpx.ConnectError("drain unavailable")
                ),
            ),
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(),
            ) as transition,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.cancel(run, expected_revision=3)

        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(
            error.exception.detail["code"], "AUTOMATION_CANCEL_DRAIN_UNAVAILABLE"
        )
        transition.assert_not_awaited()

    async def test_running_cancel_retries_against_latest_revision_after_worker_checkpoint(self):
        service = AutomationService()
        run = self.make_run(status=AutomationStatus.RUNNING, error_code=None)
        latest = run.model_copy(update={"revision": 4})
        cancelled = latest.model_copy(
            update={"status": AutomationStatus.CANCELLED, "revision": 5}
        )
        with (
            patch.object(
                service, "_revoke_testing_run_access", new=AsyncMock()
            ) as revoke,
            patch(
                "src.services.automation.automation_repository.transition_with_checkpoint",
                new=AsyncMock(side_effect=[None, cancelled]),
            ) as transition,
            patch(
                "src.services.automation.automation_repository.get_run",
                new=AsyncMock(return_value=latest),
            ) as get_run,
        ):
            result = await service.cancel(run, expected_revision=3)

        self.assertEqual(result.status, AutomationStatus.CANCELLED)
        self.assertEqual(transition.await_count, 2)
        self.assertEqual(transition.await_args_list[0].args[1], 3)
        self.assertEqual(transition.await_args_list[1].args[1], 4)
        revoke.assert_awaited_once_with(run.automation_run_id)
        get_run.assert_awaited_once_with(run.automation_run_id)


if __name__ == "__main__":
    unittest.main()
