import unittest
from unittest.mock import AsyncMock, patch

from src.agents.runner.automation_graph import route_resume
from src.runtime.automation_worker import AutomationWorker, resume_run_with_live_permissions
from src.schemas.agent import AgentRunStatus, VeriqRunState
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationGraphSnapshot,
    AutomationKind,
    AutomationRun,
    AutomationStatus,
)


class AutomationResumePermissionsTests(unittest.IsolatedAsyncioTestCase):
    def test_retry_after_graph_completion_does_not_reenter_mutating_nodes(self):
        self.assertEqual(
            route_resume(
                {"resume_after_phase": AutomationCheckpointPhase.GRAPH_COMPLETED.value}
            ),
            "end",
        )

    def test_resume_replaces_checkpoint_permissions_with_live_project_permissions(self):
        saved_run = VeriqRunState(
            run_id="run-1",
            project_id="project-1",
            user_id="user-1",
            role="QA",
            permissions=["project.read", "testcase.approve", "release.close"],
            objective="Resume after a safe checkpoint",
        )
        snapshot = AutomationGraphSnapshot(
            completed_phase=AutomationCheckpointPhase.ACTIONS_EXECUTED,
            run=saved_run,
        )

        resumed_run = resume_run_with_live_permissions(
            snapshot, ["project.read", "testcase.read"]
        )

        self.assertEqual(resumed_run.permissions, ["project.read", "testcase.read"])
        self.assertEqual(
            snapshot.run.permissions,
            ["project.read", "testcase.approve", "release.close"],
        )

    def test_fresh_run_does_not_claim_a_checkpoint_permission_snapshot(self):
        self.assertIsNone(resume_run_with_live_permissions(None, ["project.read"]))

    async def test_worker_passes_fresh_permissions_into_the_resumed_graph(self):
        run = AutomationRun(
            automation_run_id="AUT-RESUME-PERMISSION-1",
            project_id="project-1",
            requester_user_id="user-1",
            requester_role="QA",
            execution_user_id="user-1",
            execution_role="QA",
            kind=AutomationKind.EVENT,
            objective="Resume with live permissions",
            status=AutomationStatus.QUEUED,
        )
        checkpoint_run = VeriqRunState(
            run_id=run.automation_run_id,
            project_id=run.project_id,
            user_id=run.execution_user_id,
            role="QA",
            permissions=["project.read", "testcase.approve"],
            objective=run.objective,
        )
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.ACTIONS_EXECUTED,
            status=AutomationStatus.RUNNING,
            state_snapshot=AutomationGraphSnapshot(
                completed_phase=AutomationCheckpointPhase.ACTIONS_EXECUTED,
                run=checkpoint_run,
            ),
        )
        running = run.model_copy(update={"status": AutomationStatus.RUNNING, "revision": 2})
        running = running.model_copy(update={"trace_id": "trace-1"})
        completed = running.model_copy(update={"status": AutomationStatus.COMPLETED, "revision": 3})
        graph_output = checkpoint_run.model_copy(
            update={"status": AgentRunStatus.COMPLETED, "permissions": ["project.read"]}
        )
        graph = AsyncMock(
            return_value={"run": graph_output.model_dump(mode="python"), "evidence": [], "source_facts": []}
        )
        transitions = AsyncMock(side_effect=[running, completed])

        with (
            patch("src.runtime.automation_worker.automation_repository.get_run", new=AsyncMock(return_value=run)),
            patch("src.runtime.automation_worker.automation_repository.latest_checkpoint", new=AsyncMock(return_value=checkpoint)),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=transitions,
            ),
            patch("src.runtime.automation_worker.automation_repository.replace_provenance", new=AsyncMock()),
            patch("src.runtime.automation_worker.automation_service.token_for", new=AsyncMock(return_value="live-token")),
            patch("src.runtime.automation_worker.project_access", new=AsyncMock(return_value=("QA", ["project.read"]))),
            patch("src.runtime.automation_worker.automation_workflow.ainvoke", new=graph),
            patch("src.runtime.automation_worker.verified_blueprint_from_observations", return_value=(None, 0)),
            patch("src.runtime.automation_worker.agentops.record_session_start"),
            patch("src.runtime.automation_worker.agentops.record_session_end"),
            patch("src.runtime.automation_worker.run_store.save", new=AsyncMock()),
            patch("src.runtime.automation_worker.long_term_memory.record_verified", new=AsyncMock()),
            patch.object(AutomationWorker, "_enqueue_requirement_test_design_handoffs", new=AsyncMock(return_value=[])),
        ):
            await AutomationWorker()._process({"automation_run_id": run.automation_run_id})

        resumed_graph_state = graph.await_args.args[0]
        self.assertEqual(resumed_graph_state["run"]["permissions"], ["project.read"])
        self.assertEqual(
            checkpoint.state_snapshot.run.permissions,
            ["project.read", "testcase.approve"],
        )
        self.assertEqual(transitions.await_count, 2)
        self.assertEqual(
            transitions.await_args_list[0].kwargs["phase"],
            AutomationCheckpointPhase.WORKER_STARTED,
        )
        self.assertEqual(
            transitions.await_args_list[0].kwargs["state_snapshot"].completed_phase,
            AutomationCheckpointPhase.ACTIONS_EXECUTED,
        )
        self.assertEqual(
            transitions.await_args_list[1].kwargs["phase"],
            AutomationCheckpointPhase.FINALIZED,
        )
        self.assertEqual(
            transitions.await_args_list[1].kwargs["detail"]["agent_run_id"],
            graph_output.run_id,
        )

    async def test_worker_does_not_complete_or_handoff_after_access_is_revoked_mid_run(self):
        run = AutomationRun(
            automation_run_id="AUT-REVOKED-MID-RUN",
            project_id="project-1",
            requester_user_id="user-1",
            requester_role="QA",
            execution_user_id="user-1",
            execution_role="QA",
            kind=AutomationKind.EVENT,
            objective="Do not report completion after permission revocation",
            status=AutomationStatus.QUEUED,
        )
        checkpoint_run = VeriqRunState(
            run_id=run.automation_run_id,
            project_id=run.project_id,
            user_id="user-1",
            role="QA",
            permissions=["project.read"],
            objective=run.objective,
        )
        safe_checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.ACTIONS_EXECUTED,
            status=AutomationStatus.RUNNING,
            state_snapshot=AutomationGraphSnapshot(
                completed_phase=AutomationCheckpointPhase.ACTIONS_EXECUTED,
                run=checkpoint_run,
            ),
        )
        graph_output = checkpoint_run.model_copy(
            update={"status": AgentRunStatus.COMPLETED}
        )
        graph_completed_checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            phase=AutomationCheckpointPhase.GRAPH_COMPLETED,
            status=AutomationStatus.COMPLETED,
            state_snapshot=AutomationGraphSnapshot(
                completed_phase=AutomationCheckpointPhase.GRAPH_COMPLETED,
                run=graph_output,
            ),
        )
        graph = AsyncMock(
            return_value={
                "run": graph_output.model_dump(mode="python"),
                "evidence": [],
                "source_facts": [],
            }
        )
        running = run.model_copy(
            update={"status": AutomationStatus.RUNNING, "revision": 2}
        )
        running = running.model_copy(update={"trace_id": "trace-revoked"})
        awaiting_authorization = running.model_copy(
            update={
                "status": AutomationStatus.AWAITING_AUTHORIZATION,
                "error_code": "PROJECT_ACCESS_REVOKED_DURING_RUN",
                "revision": 3,
            }
        )
        transitions = AsyncMock(side_effect=[running, awaiting_authorization])
        handoff = AsyncMock(return_value=[])

        with (
            patch(
                "src.runtime.automation_worker.automation_repository.get_run",
                new=AsyncMock(return_value=run),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.latest_checkpoint",
                new=AsyncMock(side_effect=[safe_checkpoint, graph_completed_checkpoint]),
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.transition_with_checkpoint",
                new=transitions,
            ),
            patch(
                "src.runtime.automation_worker.automation_repository.replace_provenance",
                new=AsyncMock(),
            ),
            patch(
                "src.runtime.automation_worker.automation_service.token_for",
                new=AsyncMock(return_value="live-token"),
            ),
            patch(
                "src.runtime.automation_worker.project_access",
                new=AsyncMock(
                    side_effect=[("QA", ["project.read"]), ("QA", [])]
                ),
            ),
            patch(
                "src.runtime.automation_worker.automation_workflow.ainvoke",
                new=graph,
            ),
            patch(
                "src.runtime.automation_worker.verified_blueprint_from_observations",
                return_value=(None, 0),
            ),
            patch("src.runtime.automation_worker.agentops.record_session_start"),
            patch("src.runtime.automation_worker.agentops.record_session_end"),
            patch("src.runtime.automation_worker.run_store.save", new=AsyncMock()),
            patch(
                "src.runtime.automation_worker.long_term_memory.record_verified",
                new=AsyncMock(),
            ) as record_verified,
            patch.object(
                AutomationWorker,
                "_enqueue_requirement_test_design_handoffs",
                new=handoff,
            ),
        ):
            await AutomationWorker()._process(
                {"automation_run_id": run.automation_run_id}
            )

        self.assertEqual(transitions.await_count, 2)
        final_transition = transitions.await_args_list[-1]
        self.assertEqual(
            final_transition.args[2]["status"],
            AutomationStatus.AWAITING_AUTHORIZATION,
        )
        self.assertEqual(
            final_transition.args[2]["error_code"],
            "PROJECT_ACCESS_REVOKED_DURING_RUN",
        )
        self.assertEqual(
            final_transition.kwargs["phase"],
            AutomationCheckpointPhase.FINALIZED,
        )
        self.assertEqual(
            final_transition.kwargs["state_snapshot"],
            graph_completed_checkpoint.state_snapshot,
        )
        handoff.assert_not_awaited()
        record_verified.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
