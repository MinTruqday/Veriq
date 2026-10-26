import unittest
from unittest.mock import AsyncMock, patch

from src.agents.agent import execute_task
from src.schemas.agent import (
    AgentResult,
    AgentTask,
    AgentTaskStatus,
    EvidenceItem,
    ToolAccess,
    ToolCall,
    ToolDecision,
    ToolExecutionStatus,
)


class AgentDecisionOutcomeTests(unittest.IsolatedAsyncioTestCase):
    async def test_verified_source_conflict_is_a_resolved_run_needing_input(self):
        task = AgentTask(
            task_id="TASK-1",
            run_id="RUN-1",
            project_id="PRJ-1",
            user_id="USER-1",
            domain="requirement",
            objective="Synthesize source documents",
            evidence_refs=["RDOC-1"],
            tool_calls=[
                ToolCall(
                    tool_name="process_ingested_requirement_document",
                    arguments={"project_id": "PRJ-1", "document_id": "RDOC-1"},
                )
            ],
        )
        evidence = [
            EvidenceItem(
                artifact_type="requirement_document",
                artifact_id="RDOC-1",
                source="document",
                authority="project",
                text="Source statement",
                project_id="PRJ-1",
            )
        ]
        access = ToolAccess(
            name="process_ingested_requirement_document",
            domains={"requirement"},
            action="MUTATE",
            permission="requirement.create",
        )
        tool_observation = {
            "status": ToolExecutionStatus.COMPLETED,
            "tool_name": access.name,
            "result": {
                "status": "automation_waiting_for_decision",
                "reason_code": "SOURCE_CONFLICT",
                "template_id": "RTPL-1",
                "verification": {
                    "status": "COMPLETED",
                    "project_id": "PRJ-1",
                    "artifact_ids": ["RTPL-1"],
                },
            },
        }

        with (
            patch(
                "src.agents.agent.authorize_tool",
                return_value=ToolDecision(allowed=True, reason_code="ALLOWED", access=access),
            ),
            patch(
                "src.agents.agent.invoke_tool",
                new=AsyncMock(return_value=tool_observation),
            ),
            patch(
                "src.agents.agent.structured",
                new=AsyncMock(
                    return_value=AgentResult(
                        task_id=task.task_id,
                        status=AgentTaskStatus.COMPLETED,
                        summary="A template was created.",
                        evidence_refs=["RDOC-1"],
                    )
                ),
            ),
            patch(
                "src.core.security.guardrails.guardrails_engine.async_inspect_tool_output",
                new=AsyncMock(return_value={"is_safe": True, "sanitized_text": "verified"}),
            ),
            patch(
                "src.tools.registry.verify_application",
                new=AsyncMock(
                    return_value={"status": ToolExecutionStatus.COMPLETED}
                ),
            ),
        ):
            result, observations = await execute_task(task, evidence, ["requirement.create"], "token")

        self.assertEqual(result.status, AgentTaskStatus.INSUFFICIENT_EVIDENCE)
        self.assertIn("SOURCE_CONFLICT", result.reason_codes)
        self.assertIn("USER_DECISION_REQUIRED", result.warnings)
        self.assertEqual(observations[0]["status"], ToolExecutionStatus.COMPLETED)
        self.assertEqual(observations[0]["result"]["template_id"], "RTPL-1")

    async def test_grounded_partial_workflow_waits_for_clarification_without_tool_failure(self):
        task = AgentTask(
            task_id="TASK-2",
            run_id="RUN-2",
            project_id="PRJ-1",
            user_id="USER-1",
            domain="requirement",
            objective="Process a newly uploaded Requirement document",
            evidence_refs=["RDOC-2"],
            tool_calls=[
                ToolCall(
                    tool_name="process_ingested_requirement_document",
                    arguments={"project_id": "PRJ-1", "document_id": "RDOC-2"},
                )
            ],
        )
        evidence = [
            EvidenceItem(
                artifact_type="requirement_document",
                artifact_id="RDOC-2",
                source="document",
                authority="project",
                text="A verified source statement",
                project_id="PRJ-1",
            )
        ]
        access = ToolAccess(
            name="process_ingested_requirement_document",
            domains={"requirement"},
            action="MUTATE",
            permission="requirement.create",
        )
        tool_observation = {
            "status": ToolExecutionStatus.COMPLETED,
            "tool_name": access.name,
            "result": {
                "status": "automation_waiting_for_input",
                "reason_code": "REQUIREMENT_CLARIFICATION_REQUIRED",
                "requirement_ids": ["REQ-2"],
                "clarification_ids": ["RCL-2"],
                "verification": {
                    "status": "AWAITING_INPUT",
                    "project_id": "PRJ-1",
                    "artifact_ids": ["REQ-2", "RCL-2"],
                },
            },
            "verification": {"status": ToolExecutionStatus.COMPLETED},
        }

        with (
            patch(
                "src.agents.agent.authorize_tool",
                return_value=ToolDecision(allowed=True, reason_code="ALLOWED", access=access),
            ),
            patch(
                "src.agents.agent.invoke_tool",
                new=AsyncMock(return_value=tool_observation),
            ),
            patch(
                "src.agents.agent.structured",
                new=AsyncMock(
                    return_value=AgentResult(
                        task_id=task.task_id,
                        status=AgentTaskStatus.COMPLETED,
                        summary="The grounded artifacts were created.",
                        evidence_refs=["RDOC-2"],
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
                task, evidence, ["requirement.create"], "token"
            )

        self.assertEqual(result.status, AgentTaskStatus.INSUFFICIENT_EVIDENCE)
        self.assertIn("REQUIREMENT_CLARIFICATION_REQUIRED", result.reason_codes)
        self.assertIn("CLARIFICATION_REQUIRED", result.warnings)
        self.assertNotIn("TOOL_FAILED", result.reason_codes)
        self.assertEqual(observations[0]["status"], ToolExecutionStatus.COMPLETED)

    async def test_partial_failure_result_cannot_be_reported_as_a_completed_task(self):
        task = AgentTask(
            task_id="TASK-EXTRACTION",
            run_id="RUN-EXTRACTION",
            project_id="PRJ-1",
            user_id="USER-1",
            domain="requirement",
            objective="Process a newly uploaded Requirement document",
            evidence_refs=["RDOC-3"],
            tool_calls=[
                ToolCall(
                    tool_name="process_ingested_requirement_document",
                    arguments={"project_id": "PRJ-1", "document_id": "RDOC-3"},
                ),
                ToolCall(
                    tool_name="publish_grounded_requirement",
                    arguments={"project_id": "PRJ-1", "requirement_id": "REQ-3"},
                ),
            ],
        )
        evidence = [
            EvidenceItem(
                artifact_type="requirement_document",
                artifact_id="RDOC-3",
                source="document",
                authority="project",
                text="A source with incomplete extraction",
                project_id="PRJ-1",
            )
        ]
        access = ToolAccess(
            name="process_ingested_requirement_document",
            domains={"requirement"},
            action="MUTATE",
            permission="requirement.create",
        )
        tool_observation = {
            "status": ToolExecutionStatus.COMPLETED,
            "tool_name": access.name,
            "result": {
                "status": "automation_partial_failure",
                "reason_code": "SOURCE_EXTRACTION_INCOMPLETE",
                "safe_no_mutation": True,
                "source_extraction_gaps": [{"document_id": "RDOC-3"}],
            },
            "verification": {
                "status": ToolExecutionStatus.COMPLETED,
                "reason_code": "SAFE_NO_MUTATION_OUTCOME",
                "artifact_ids": [],
            },
        }

        with (
            patch(
                "src.agents.agent.authorize_tool",
                return_value=ToolDecision(allowed=True, reason_code="ALLOWED", access=access),
            ),
            patch(
                "src.agents.agent.invoke_tool",
                new=AsyncMock(return_value=tool_observation),
            ) as invoke,
            patch(
                "src.agents.agent.structured",
                new=AsyncMock(
                    return_value=AgentResult(
                        task_id=task.task_id,
                        status=AgentTaskStatus.COMPLETED,
                        summary="The document was processed successfully.",
                        evidence_refs=["RDOC-3"],
                    )
                ),
            ),
            patch(
                "src.core.security.guardrails.guardrails_engine.async_inspect_tool_output",
                new=AsyncMock(return_value={"is_safe": True, "sanitized_text": "verified"}),
            ),
            patch(
                "src.tools.registry.verify_application",
                new=AsyncMock(return_value=tool_observation["verification"]),
            ),
        ):
            result, observations = await execute_task(
                task, evidence, ["requirement.create"], "token"
            )

        self.assertEqual(result.status, AgentTaskStatus.INSUFFICIENT_EVIDENCE)
        self.assertIn("SOURCE_EXTRACTION_INCOMPLETE", result.reason_codes)
        self.assertIn("AUTOMATION_PARTIAL_FAILURE", result.warnings)
        self.assertEqual(observations[0]["status"], ToolExecutionStatus.COMPLETED)
        invoke.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
