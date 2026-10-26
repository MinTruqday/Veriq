import unittest
from unittest.mock import AsyncMock, patch

from pydantic import BaseModel

from src.agents.agent import execute_task
from src.runtime.automation_worker import terminal_status_for_agent_run
from src.schemas.agent import (
    AgentResult,
    AgentRunStatus,
    AgentTask,
    AgentTaskStatus,
    EvidenceItem,
    ToolAccess,
    ToolCall,
    ToolDecision,
    ToolExecutionStatus,
    VeriqRunState,
)
from src.schemas.automation import AutomationStatus
from src.tools.registry import invoke_tool, verify_application


class AutomationTerminalStatusTests(unittest.TestCase):
    def make_run(self, status, error_code=None):
        return VeriqRunState(
            project_id="PRJ-1",
            user_id="USER-1",
            role="BA",
            objective="Process project source",
            status=status,
            error_code=error_code,
        )

    def test_clarification_wait_is_not_reported_as_failure_or_degraded(self):
        run = self.make_run(
            AgentRunStatus.FAILED,
            "AUTOMATION_WAITING_FOR_INPUT",
        )

        self.assertEqual(
            terminal_status_for_agent_run(run),
            AutomationStatus.AWAITING_INPUT,
        )

    def test_insufficient_evidence_without_a_clarification_remains_degraded(self):
        run = self.make_run(AgentRunStatus.FAILED, "INSUFFICIENT_EVIDENCE")

        self.assertEqual(
            terminal_status_for_agent_run(run),
            AutomationStatus.DEGRADED,
        )

    def test_execution_error_remains_failed(self):
        run = self.make_run(AgentRunStatus.FAILED, "AI_PROVIDER_UNAVAILABLE")

        self.assertEqual(
            terminal_status_for_agent_run(run),
            AutomationStatus.FAILED,
        )


class AutomationClarificationOutcomeTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_automation_run_cannot_invoke_another_tool(self):
        class Arguments(BaseModel):
            project_id: str

        class MutatingTool:
            name = "test_cancelled_run_tool"
            metadata = {}
            args_schema = Arguments

            async def ainvoke(self, *_args, **_kwargs):
                raise AssertionError("cancelled run invoked a tool")

        tool = MutatingTool()
        task = AgentTask(
            task_id="TASK-1",
            run_id="RUN-1",
            project_id="PRJ-1",
            user_id="USER-1",
            domain="requirement",
            objective="Process source",
        )
        access = ToolAccess(
            name=tool.name,
            domains={"requirement"},
            action="MUTATE",
            permission="requirement.create",
        )
        decision = ToolDecision(allowed=True, reason_code="ALLOWED", access=access)
        cancelled = type(
            "Run",
            (),
            {"status": AutomationStatus.CANCELLED},
        )()
        with (
            patch("src.tools.registry.registered_tools", return_value={tool.name: tool}),
            patch("src.tools.registry.authorize_tool", return_value=decision),
            patch(
                "src.repositories.automation.automation_repository.get_run",
                new=AsyncMock(return_value=cancelled),
            ),
            patch("src.tools.registry.agentops.record_tool_call"),
            patch("src.tools.registry.add_tool_usage"),
        ):
            outcome = await invoke_tool(
                task,
                tool.name,
                {"project_id": "PRJ-1"},
                ["requirement.create"],
                "token",
                automation_run_id="AUT-CANCELLED-1",
            )

        self.assertEqual(outcome["status"], ToolExecutionStatus.DENIED)
        self.assertEqual(outcome["reason_code"], "AUTOMATION_RUN_NOT_ACTIVE")

    async def test_input_wait_is_successful_tool_outcome_with_verified_partial_artifacts(self):
        class Arguments(BaseModel):
            project_id: str

        class WaitingTool:
            name = "test_waiting_tool"
            metadata = {}
            args_schema = Arguments

            async def ainvoke(self, *_args, **_kwargs):
                return (
                    '{"status":"automation_waiting_for_input",'
                    '"reason_code":"REQUIREMENT_CLARIFICATION_REQUIRED",'
                    '"verification":{"status":"AWAITING_INPUT",'
                    '"project_id":"PRJ-1","artifact_ids":["REQ-1","RCL-1"]}}'
                )

        task = AgentTask(
            task_id="TASK-1",
            run_id="RUN-1",
            project_id="PRJ-1",
            user_id="USER-1",
            domain="requirement",
            objective="Process source",
        )
        access = ToolAccess(
            name="test_waiting_tool",
            domains={"requirement"},
            action="MUTATE",
            permission="requirement.create",
        )
        tool = WaitingTool()
        decision = ToolDecision(allowed=True, reason_code="ALLOWED", access=access)

        with (
            patch("src.tools.registry.registered_tools", return_value={tool.name: tool}),
            patch("src.tools.registry.authorize_tool", return_value=decision),
            patch("src.tools.registry.agentops.record_tool_call"),
            patch("src.tools.registry.add_tool_usage"),
        ):
            outcome = await invoke_tool(
                task,
                tool.name,
                {"project_id": "PRJ-1"},
                ["requirement.create"],
                "token",
            )
            verification = await verify_application(
                task,
                tool.name,
                {"project_id": "PRJ-1"},
                outcome,
                "token",
            )

        self.assertEqual(outcome["status"], ToolExecutionStatus.COMPLETED)
        self.assertEqual(outcome["result"]["status"], "automation_waiting_for_input")
        self.assertEqual(verification["status"], ToolExecutionStatus.COMPLETED)
        self.assertEqual(verification["artifact_ids"], ["REQ-1", "RCL-1"])

    async def test_safe_source_extraction_stop_is_a_completed_no_mutation_tool_outcome(self):
        class Arguments(BaseModel):
            project_id: str

        class IngestionTool:
            name = "process_ingested_requirement_document"
            metadata = {
                "domains": ["requirement"],
                "action": "MUTATE",
                "permission": "requirement.create",
            }
            args_schema = Arguments

            async def ainvoke(self, *_args, **_kwargs):
                return (
                    '{"status":"automation_partial_failure",'
                    '"reason_code":"SOURCE_EXTRACTION_INCOMPLETE",'
                    '"safe_no_mutation":true,'
                    '"verification":{"status":"INCOMPLETE",'
                    '"project_id":"PRJ-1","artifact_ids":[]}}'
                )

        tool = IngestionTool()
        task = AgentTask(
            task_id="TASK-EXTRACTION",
            run_id="RUN-EXTRACTION",
            project_id="PRJ-1",
            user_id="USER-1",
            domain="requirement",
            objective="Process a source document",
        )
        access = ToolAccess(
            name=tool.name,
            domains={"requirement"},
            action="MUTATE",
            permission="requirement.create",
        )
        with (
            patch("src.tools.registry.registered_tools", return_value={tool.name: tool}),
            patch(
                "src.tools.registry.authorize_tool",
                return_value=ToolDecision(allowed=True, reason_code="ALLOWED", access=access),
            ),
            patch("src.tools.registry.agentops.record_tool_call"),
            patch("src.tools.registry.add_tool_usage"),
        ):
            outcome = await invoke_tool(
                task, tool.name, {"project_id": "PRJ-1"}, ["requirement.create"], "token"
            )
            verification = await verify_application(
                task, tool.name, {"project_id": "PRJ-1"}, outcome, "token"
            )

        self.assertEqual(outcome["status"], ToolExecutionStatus.COMPLETED)
        self.assertEqual(outcome["result"]["reason_code"], "SOURCE_EXTRACTION_INCOMPLETE")
        self.assertEqual(verification["status"], ToolExecutionStatus.COMPLETED)
        self.assertEqual(verification["reason_code"], "SAFE_NO_MUTATION_OUTCOME")
        self.assertEqual(verification["artifact_ids"], [])

    async def test_waiting_for_input_tool_result_is_not_reclassified_as_tool_failure(self):
        task = AgentTask(
            task_id="TASK-1",
            run_id="RUN-1",
            project_id="PRJ-1",
            user_id="USER-1",
            domain="requirement",
            objective="Ingest a project source",
            evidence_refs=["DOC-1"],
            tool_calls=[
                ToolCall(
                    tool_name="process_ingested_requirement_document",
                    arguments={"project_id": "PRJ-1", "document_id": "DOC-1"},
                )
            ],
        )
        evidence = [
            EvidenceItem(
                artifact_type="requirement_document",
                artifact_id="DOC-1",
                source="document",
                authority="project",
                text="Grounded source text",
                project_id="PRJ-1",
            )
        ]
        access = ToolAccess(
            name="process_ingested_requirement_document",
            domains={"requirement"},
            action="MUTATE",
            permission="requirement.create",
        )
        outcome = {
            "status": ToolExecutionStatus.COMPLETED,
            "tool_name": access.name,
            "result": {
                "status": "automation_waiting_for_input",
                "reason_code": "REQUIREMENT_CLARIFICATION_REQUIRED",
                "verification": {
                    "status": "AWAITING_INPUT",
                    "project_id": "PRJ-1",
                    "artifact_ids": ["REQ-1", "RCL-1"],
                },
            },
            "verification": {"status": ToolExecutionStatus.COMPLETED},
        }

        with (
            patch(
                "src.agents.agent.authorize_tool",
                return_value=ToolDecision(allowed=True, reason_code="ALLOWED", access=access),
            ),
            patch("src.agents.agent.invoke_tool", new=AsyncMock(return_value=outcome)),
            patch(
                "src.agents.agent.structured",
                new=AsyncMock(
                    return_value=AgentResult(
                        task_id=task.task_id,
                        status=AgentTaskStatus.COMPLETED,
                        summary="Saved the grounded parts.",
                        evidence_refs=["DOC-1"],
                    )
                ),
            ),
            patch(
                "src.core.security.guardrails.guardrails_engine.async_inspect_tool_output",
                new=AsyncMock(return_value={"is_safe": True, "sanitized_text": "verified"}),
            ),
            patch(
                "src.tools.registry.verify_application",
                new=AsyncMock(return_value={"status": ToolExecutionStatus.COMPLETED}),
            ),
        ):
            result, observations = await execute_task(
                task,
                evidence,
                ["requirement.create"],
                "token",
            )

        self.assertEqual(result.status, AgentTaskStatus.INSUFFICIENT_EVIDENCE)
        self.assertIn("REQUIREMENT_CLARIFICATION_REQUIRED", result.reason_codes)
        self.assertIn("CLARIFICATION_REQUIRED", result.warnings)
        self.assertNotIn("TOOL_FAILED", result.reason_codes)
        self.assertEqual(observations[0]["status"], ToolExecutionStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
