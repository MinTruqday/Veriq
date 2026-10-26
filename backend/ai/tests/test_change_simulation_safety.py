import unittest
from unittest.mock import AsyncMock, patch

from src.agents.runner.nodes import execute_agent
from src.schemas.agent import AgentRunStatus, AgentTask, ToolCall, VeriqRunState


class ChangeSimulationSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_mutating_tool_is_blocked_before_invocation(self):
        task = AgentTask(
            run_id="run-simulation",
            project_id="project-1",
            user_id="qa-1",
            domain="test_design",
            objective="Tạo Test Case từ nội dung mô phỏng",
            evidence_refs=["REQV-1"],
            tool_calls=[
                ToolCall(
                    tool_name="create_test_case_draft",
                    arguments={"project_id": "project-1", "draft_json": "{}"},
                )
            ],
        )
        run = VeriqRunState(
            run_id="run-simulation",
            project_id="project-1",
            user_id="qa-1",
            role="QA",
            permissions=["testcase.create"],
            objective="Mô phỏng thay đổi Requirement",
            status=AgentRunStatus.RUNNING,
        )
        state = {
            "run": run.model_dump(mode="python"),
            "tasks": [task.model_dump(mode="python")],
            "evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-1",
                    "source": "database",
                    "authority": "project",
                    "text": "Yêu cầu chuẩn đã lưu.",
                    "project_id": "project-1",
                }
            ],
            "constraints": {"change_simulation": True},
            "automatic": True,
            "token": "test-token",
        }
        tool = object()
        access = type("Access", (), {"action": "MUTATE"})()

        with (
            patch("src.agents.runner.nodes.registered_tools", return_value={"create_test_case_draft": tool}),
            patch("src.agents.runner.nodes.tool_access", return_value=access),
            patch("src.agents.runner.nodes.execute_task", new=AsyncMock()) as invoke,
        ):
            result = await execute_agent(state)

        invoke.assert_not_awaited()
        updated = VeriqRunState(**result["run"])
        self.assertEqual(updated.agent_results[-1]["status"], "FAILED")
        self.assertEqual(updated.agent_results[-1]["reason_codes"], ["CHANGE_SIMULATION_MUTATION_BLOCKED"])
        self.assertEqual(updated.observations[-1]["status"], "DENIED")


if __name__ == "__main__":
    unittest.main()
