import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.agents.runner.automation_event_tasks import (
    direct_approved_plan_task,
    direct_capability_task,
    direct_change_simulation_task,
    direct_changed_plan_task,
    direct_defect_event_task,
    direct_document_ingestion_task,
    direct_event_observation_task,
    direct_performance_configuration_task,
    direct_recorded_test_execution_task,
    direct_requirement_change_task,
    direct_test_case_change_impact_task,
    simulation_linked_test_case_version_ids,
)
from src.agents.runner.graph import canonical_workflow
from src.agents.runner.nodes import aggregate, plan, route_after_agent, verify
from src.agents.runner.automation_validation import mutation_fingerprint
from src.schemas.agent import (
    AgentPlan,
    AgentResult,
    AgentRunStatus,
    AgentTask,
    AgentTaskStatus,
    ToolCall,
    VeriqRunState,
)
from src.schemas.automation import AutomationRunRequest
from src.tools.registry import registered_tools


class AutomationEventTaskTests(unittest.TestCase):
    def test_approved_performance_configuration_creates_only_a_source_scoped_task(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="qa-1",
            role="QA",
            permissions=["ai.generate_performance_plan"],
            objective="Tạo bản nháp kế hoạch hiệu năng từ cấu hình đã duyệt",
            source_event_id=(
                "performance-configuration:NFR-1:4:PERFORMANCE_CONFIGURATION_APPROVED"
            ),
        )
        state = {
            "automatic": True,
            "source_event_verified": True,
            "constraints": {"trigger": "PERFORMANCE_CONFIGURATION_APPROVED"},
            "evidence": [
                {
                    "artifact_type": "non_functional_test_plan",
                    "artifact_id": "NFR-1",
                    "artifact_version_id": "NFR-1",
                    "artifact_revision": 4,
                    "project_id": "project-1",
                }
            ],
        }

        task = direct_performance_configuration_task(run, state, ["NFR-1"])

        self.assertIsNotNone(task)
        self.assertEqual(
            task.tool_calls[0].tool_name,
            "process_approved_performance_configuration",
        )
        self.assertEqual(task.tool_calls[0].arguments["plan_id"], "NFR-1")
        self.assertEqual(task.tool_calls[0].arguments["source_event_revision"], 4)
        self.assertEqual(
            task.tool_calls[0].arguments["source_event_id"], run.source_event_id
        )

    def test_performance_configuration_event_without_verified_scope_is_ignored(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="qa-1",
            role="QA",
            permissions=["ai.generate_performance_plan"],
            objective="Tạo bản nháp kế hoạch hiệu năng",
            source_event_id="performance-configuration:NFR-1:4:PERFORMANCE_CONFIGURATION_APPROVED",
        )
        state = {
            "automatic": True,
            "source_event_verified": False,
            "constraints": {"trigger": "PERFORMANCE_CONFIGURATION_APPROVED"},
            "evidence": [
                {
                    "artifact_type": "non_functional_test_plan",
                    "artifact_id": "NFR-1",
                    "artifact_revision": 4,
                    "project_id": "project-1",
                }
            ],
        }

        self.assertIsNone(
            direct_performance_configuration_task(run, state, ["NFR-1"])
        )

    def test_change_simulation_replan_route_returns_to_the_planner(self):
        graph_edges = canonical_workflow.get_graph().edges

        self.assertTrue(
            any(edge.source == "execute" and edge.target == "plan" for edge in graph_edges)
        )

    def test_noncompleted_agent_outcome_stops_remaining_preplanned_tasks(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="ba-1",
            role="BA",
            objective="Xử lý tài liệu chưa được đọc đầy đủ",
            agent_results=[
                AgentResult(
                    task_id="task-source-analysis",
                    status=AgentTaskStatus.INSUFFICIENT_EVIDENCE,
                    summary="Nguồn còn phần chưa trích xuất",
                    reason_codes=["SOURCE_EXTRACTION_INCOMPLETE"],
                ).model_dump(mode="python")
            ],
        )
        state = {
            "run": run.model_dump(mode="python"),
            "tasks": [
                {"task_id": "task-source-analysis"},
                {"task_id": "task-create-requirements"},
            ],
        }

        self.assertEqual(route_after_agent(state), "finalize")

    def test_document_ingestion_task_receives_checkpointed_verified_fact_lineage(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="ba-1",
            role="BA",
            permissions=["project.read", "requirement.create"],
            objective="Xử lý tài liệu yêu cầu mới",
            evidence_refs=["doc-1-v1"],
        )
        source_fact = {
            "artifact_type": "requirement_document",
            "artifact_id": "doc-1",
            "artifact_version_id": "doc-1-v1",
            "source": "document",
            "authority": "project",
            "quote": "Tài khoản khóa sau 5 lần sai.",
            "source_start": 0,
            "source_end": 30,
            "relationship_path": ["source-root", "series-v2", "doc-1-v1"],
        }
        task = direct_document_ingestion_task(
            run,
            {
                "automatic": True,
                "source_event_verified": True,
                "constraints": {"trigger": "DOCUMENT_INGESTED"},
                "target_artifact_ids": ["doc-1"],
                "evidence": [{
                    "artifact_type": "requirement_document",
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "text": source_fact["quote"],
                }],
                "source_facts": [source_fact],
            },
            ["doc-1-v1"],
        )

        self.assertIsNotNone(task)
        arguments = task.tool_calls[0].arguments
        self.assertEqual(arguments["source_facts"], [source_fact])
        self.assertTrue(task.constraints["workflow_terminal"])

    def test_document_event_can_replan_after_ingestion_for_scoped_mcp_read(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="ba-1",
            role="BA",
            permissions=["project.read", "requirement.create"],
            objective="Process a newly uploaded requirements document",
            evidence_refs=["doc-1-v1"],
        )
        state = {
            "automatic": True,
            "source_event_verified": True,
            "constraints": {
                "trigger": "DOCUMENT_INGESTED",
                "automation_actions": [
                    "CREATE_REQUIREMENT_CANDIDATES",
                    "READ_PROJECT_MCP",
                ],
            },
            "target_artifact_ids": ["doc-1"],
            "evidence": [{
                "artifact_type": "requirement_document",
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v1",
                "text": "The source document",
            }],
            "source_facts": [],
        }

        task = direct_document_ingestion_task(run, state, ["doc-1-v1"])

        self.assertIsNotNone(task)
        self.assertFalse(task.constraints["workflow_terminal"])

        run.observations.append({
            "tool_name": "process_ingested_requirement_document",
            "status": "COMPLETED",
            "verification": {"status": "COMPLETED"},
            "result": {"requirement_import_job_id": "RIMP-1"},
        })

        self.assertIsNone(direct_document_ingestion_task(run, state, ["doc-1-v1"]))

    def test_document_event_core_ingestion_is_not_blocked_by_additional_action_scope(self):
        for actions, expected_terminal in (
            ([], True),
            (["READ_PROJECT_MCP"], False),
        ):
            with self.subTest(actions=actions):
                run = VeriqRunState(
                    project_id="project-1",
                    user_id="ba-1",
                    role="BA",
                    permissions=["project.read", "requirement.create"],
                    objective="Process a newly uploaded requirements document",
                    evidence_refs=["doc-1-v1"],
                )
                state = {
                    "automatic": True,
                    "source_event_verified": True,
                    "run": run.model_dump(mode="python"),
                    "token": "Bearer session-token",
                    "constraints": {
                        "trigger": "DOCUMENT_INGESTED",
                        "automation_actions": actions,
                    },
                    "target_artifact_ids": ["doc-1"],
                    "evidence": [{
                        "artifact_type": "requirement_document",
                        "artifact_id": "doc-1",
                        "artifact_version_id": "doc-1-v1",
                        "text": "The source document",
                    }],
                    "source_facts": [],
                }

                planned = asyncio.run(plan(state))

                self.assertEqual(len(planned["tasks"]), 1)
                task = planned["tasks"][0]
                self.assertEqual(
                    task["tool_calls"][0]["tool_name"],
                    "process_ingested_requirement_document",
                )
                self.assertEqual(task["constraints"]["workflow_terminal"], expected_terminal)

    def test_document_ingestion_resume_passes_clarification_records_to_mutation(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="ba-1",
            role="BA",
            permissions=["project.read", "requirement.create"],
            objective="Resume document processing after a user clarification",
            evidence_refs=["doc-1-v1"],
            observations=[
                {
                    "tool_name": "process_ingested_requirement_document",
                    "status": "COMPLETED",
                    "result": {
                        "requirement_import_job_id": "RIMP-1",
                        "requirement_ids": ["REQ-1"],
                    },
                }
            ],
            tool_calls=[
                {
                    "tool_name": "process_ingested_requirement_document",
                    "arguments": {
                        "project_id": "project-1",
                        "document_id": "doc-1",
                        "source_facts": [],
                    },
                    "mutation_fingerprint": mutation_fingerprint(
                        "process_ingested_requirement_document",
                        {
                            "project_id": "project-1",
                            "document_id": "doc-1",
                            "source_facts": [],
                        },
                    ),
                }
            ],
        )
        clarification = {
            "uncertainty_code": "LOCKOUT_THRESHOLD",
            "question": "How many attempts?",
            "reason": "The source does not specify a number.",
            "evidence_refs": ["doc-1-v1"],
            "answer": "Five consecutive failed attempts.",
            "answered_by": "ba-1",
            "answered_at": "2026-10-28T04:00:00+00:00",
            "evidence_ref": "clarification-1",
        }

        task = direct_document_ingestion_task(
            run,
            {
                "automatic": True,
                "source_event_verified": True,
                "constraints": {
                    "trigger": "DOCUMENT_INGESTED",
                    "clarification_responses": [clarification],
                },
                "target_artifact_ids": ["doc-1"],
                "evidence": [{
                    "artifact_type": "requirement_document",
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "text": "The source document",
                }],
                "source_facts": [],
            },
            ["doc-1-v1"],
        )

        self.assertIsNotNone(task)
        self.assertTrue(task.constraints["resume_after_clarification"])
        self.assertEqual(
            task.tool_calls[0].arguments["clarification_responses"],
            [clarification],
        )
        self.assertEqual(task.tool_calls[0].arguments["resume_import_job_id"], "RIMP-1")
        self.assertEqual(task.tool_calls[0].arguments["resume_requirement_ids"], ["REQ-1"])

    def test_project_discovered_mcp_read_tools_are_given_to_the_agent_planner(self):
        run = VeriqRunState(
            run_id="run-mcp-plan",
            project_id="project-1",
            user_id="qa-1",
            role="QA",
            permissions=["project.read"],
            objective="Find the project API contract using the configured read-only source",
        )
        discovered_tools = [
            {
                "connection_id": "postman-project-1",
                "server": "Postman",
                "tool_name": "getCollection",
                "call_tool": "call_mcp_read_tool",
                "required_arguments": {
                    "connection_id": "postman-project-1",
                    "tool_name": "getCollection",
                },
            }
        ]
        state = {
            "run": run.model_dump(mode="python"),
            "token": "Bearer live-session-token",
            "evidence": [],
            "target_artifact_ids": [],
            "constraints": {},
        }

        with (
            patch(
                "src.agents.runner.nodes.discover_project_tools_with_diagnostics",
                new=AsyncMock(return_value={
                    "tools": discovered_tools,
                    "issues": [{
                        "connection_id": "postman-project-1",
                        "reason_code": "MCP_DISCOVERY_TIMEOUT",
                    }],
                }),
            ) as discover,
            patch(
                "src.agents.runner.nodes.structured",
                new=AsyncMock(return_value=AgentPlan(intent="project_question")),
            ) as planner,
        ):
            asyncio.run(plan(state))

        discover.assert_awaited_once_with(
            "project-1",
            ["project.read"],
            token="Bearer live-session-token",
            automation_run_id="run-mcp-plan",
        )
        prompt = planner.await_args.args[0]
        self.assertIn('"connection_id": "postman-project-1"', prompt)
        self.assertIn('"tool_name": "getCollection"', prompt)
        self.assertNotIn("deleteCollection", prompt)
        self.assertIn('"reason_code": "MCP_DISCOVERY_TIMEOUT"', prompt)

    def test_event_replanner_can_execute_only_a_discovered_mcp_read_tool(self):
        run = VeriqRunState(
            run_id="run-event-mcp-plan",
            project_id="project-1",
            user_id="qa-1",
            role="QA",
            permissions=["project.read"],
            objective="Review the changed Test Case and consult its configured API contract source if relevant",
            completed_tasks=[
                {
                    "task_id": "task-test-case-read",
                    "run_id": "run-event-mcp-plan",
                    "project_id": "project-1",
                    "user_id": "qa-1",
                    "domain": "test_design",
                    "objective": "Read and lint the changed Test Case draft",
                    "evidence_refs": ["draft-1"],
                    "constraints": {"event_trigger": "TEST_CASE_CHANGED"},
                    "tool_calls": [],
                }
            ],
            agent_results=[
                AgentResult(
                    task_id="task-test-case-read",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã đọc và lint bản nháp",
                ).model_dump(mode="python")
            ],
            tool_calls=[
                {
                    "tool_name": "lint_testcase",
                    "arguments": {"test_case_draft_id": "draft-1"},
                    "read_fingerprint": "already-linted",
                }
            ],
            evidence_refs=["draft-1"],
        )
        state = {
            "automatic": True,
            "source_event_verified": True,
            "run": run.model_dump(mode="python"),
            "token": "Bearer live-session-token",
            "evidence": [
                {
                    "artifact_type": "test_case_draft",
                    "artifact_id": "draft-1",
                    "artifact_version_id": "draft-1",
                    "project_id": "project-1",
                    "source": "database",
                    "authority": "project",
                    "text": "API contract is needed for this case",
                }
            ],
            "target_artifact_ids": ["draft-1"],
            "constraints": {"trigger": "TEST_CASE_CHANGED"},
            "source_facts": [],
        }
        discovered_tools = [
            {
                "connection_id": "project-postman-1",
                "tool_name": "getCollection",
                "call_tool": "call_mcp_read_tool",
            }
        ]
        selected_call = {
            "connection_id": "project-postman-1",
            "tool_name": "getCollection",
            "arguments": {},
        }
        planner_output = AgentPlan(
            intent="project_question",
            tasks=[
                {
                    "domain": "analysis",
                    "objective": "Read the linked API contract for impact context",
                    "evidence_refs": ["draft-1"],
                    "tool_calls": [
                        {
                            "tool_name": "call_mcp_read_tool",
                            "arguments": selected_call,
                        }
                    ],
                }
            ],
        )

        with (
            patch(
                "src.agents.runner.nodes.discover_project_tools_with_diagnostics",
                new=AsyncMock(return_value={"tools": discovered_tools, "issues": []}),
            ),
            patch(
                "src.agents.runner.nodes.structured",
                new=AsyncMock(return_value=planner_output),
            ),
        ):
            accepted = asyncio.run(plan(state))

        self.assertEqual(len(accepted["tasks"]), 1)
        self.assertEqual(
            accepted["tasks"][0]["tool_calls"][0]["arguments"]["connection_id"],
            "project-postman-1",
        )

        with (
            patch(
                "src.agents.runner.nodes.discover_project_tools_with_diagnostics",
                new=AsyncMock(return_value={"tools": [], "issues": []}),
            ),
            patch(
                "src.agents.runner.nodes.structured",
                new=AsyncMock(return_value=planner_output),
            ),
        ):
            rejected = asyncio.run(plan(state))

        self.assertEqual(rejected["tasks"], [])
        policy_result = next(
            item for item in rejected["results"]
            if item.get("task_id") == "MCP-PLAN-run-event-mcp-plan"
        )
        self.assertEqual(policy_result["status"], AgentTaskStatus.INSUFFICIENT_EVIDENCE)
        self.assertEqual(policy_result["reason_codes"], ["MCP_TOOL_PLAN_REJECTED"])

    def test_event_replanner_rejects_a_mcp_connection_not_discovered_for_project(self):
        run = VeriqRunState(
            run_id="run-event-mcp-deny",
            project_id="project-1",
            user_id="qa-1",
            role="QA",
            permissions=["project.read", "trace.read"],
            objective="Review the changed Test Case",
            completed_tasks=[
                {
                    "task_id": "task-test-case-read",
                    "run_id": "run-event-mcp-deny",
                    "project_id": "project-1",
                    "user_id": "qa-1",
                    "domain": "test_design",
                    "objective": "Read and lint the changed Test Case draft",
                    "evidence_refs": ["draft-1"],
                    "constraints": {"event_trigger": "TEST_CASE_CHANGED"},
                    "tool_calls": [],
                }
            ],
            agent_results=[
                AgentResult(
                    task_id="task-test-case-read",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã đọc và lint bản nháp",
                ).model_dump(mode="python")
            ],
            tool_calls=[
                {
                    "tool_name": "lint_testcase",
                    "arguments": {"test_case_draft_id": "draft-1"},
                    "read_fingerprint": "already-linted",
                }
            ],
            evidence_refs=["draft-1"],
        )
        state = {
            "automatic": True,
            "source_event_verified": True,
            "run": run.model_dump(mode="python"),
            "token": "Bearer live-session-token",
            "evidence": [
                {
                    "artifact_type": "test_case_draft",
                    "artifact_id": "draft-1",
                    "artifact_version_id": "draft-1",
                    "project_id": "project-1",
                    "source": "database",
                    "authority": "project",
                    "text": "API contract is needed for this case",
                }
            ],
            "target_artifact_ids": ["draft-1"],
            "constraints": {"trigger": "TEST_CASE_CHANGED"},
            "source_facts": [],
        }

        with (
            patch(
                "src.agents.runner.nodes.discover_project_tools_with_diagnostics",
                new=AsyncMock(return_value={"tools": [], "issues": []}),
            ),
            patch(
                "src.agents.runner.nodes.structured",
                new=AsyncMock(
                    return_value=AgentPlan(
                        intent="project_question",
                        tasks=[
                            {
                                "domain": "analysis",
                                "objective": "Try an unlisted external connection",
                                "evidence_refs": ["draft-1"],
                                "tool_calls": [
                                    {
                                        "tool_name": "call_mcp_read_tool",
                                        "arguments": {
                                            "connection_id": "other-project-connection",
                                            "tool_name": "getCollection",
                                            "arguments": {},
                                        },
                                    },
                                    {
                                        "tool_name": "get_traceability_links",
                                        "arguments": {"requirement_version_id": "draft-1"},
                                    },
                                ],
                            }
                        ],
                    )
                ),
            ),
        ):
            rejected = asyncio.run(plan(state))

        self.assertEqual(rejected["tasks"], [])
        self.assertEqual(rejected["results"][-1]["reason_codes"], ["MCP_TOOL_PLAN_REJECTED"])
        self.assertEqual(
            rejected["results"][-1]["status"],
            AgentTaskStatus.INSUFFICIENT_EVIDENCE,
        )

    def test_explicit_mcp_capability_arguments_reach_the_validated_read_task(self):
        tool = registered_tools()["call_mcp_read_tool"]
        arguments = {
            "connection_id": "global-postman",
            "tool_name": "getAuthenticatedUser",
            "arguments": {},
        }
        payload = AutomationRunRequest(
            project_id="project-1",
            objective="Read the authenticated Postman connection status",
            intent="call_mcp_read_tool",
            intent_arguments=arguments,
        )
        run = VeriqRunState(
            project_id=payload.project_id,
            user_id="qa-1",
            role="QA",
            permissions=["project.read"],
            objective=payload.objective,
            intent=payload.intent,
            intent_arguments=payload.intent_arguments,
        )

        with patch(
            "src.agents.runner.automation_event_tasks.registered_tools",
            return_value={tool.name: tool},
        ):
            task = direct_capability_task(run, [])

        self.assertIsNotNone(task)
        self.assertEqual(task.tool_calls[0].tool_name, "call_mcp_read_tool")
        self.assertEqual(task.tool_calls[0].arguments, arguments)
        self.assertEqual(task.constraints["workflow_terminal"], True)

    def test_rejected_mcp_plan_cannot_verify_an_event_run_as_completed(self):
        run = VeriqRunState(
            run_id="run-event-mcp-rejected",
            project_id="project-1",
            user_id="qa-1",
            role="QA",
            permissions=["project.read"],
            objective="Review the changed Test Case",
            evidence_refs=["draft-1"],
        )
        state = {
            "run": run.model_dump(mode="python"),
            "results": [
                AgentResult(
                    task_id="task-test-case-read",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Draft lint completed",
                    evidence_refs=["draft-1"],
                ).model_dump(mode="python"),
                AgentResult(
                    task_id="MCP-PLAN-run-event-mcp-rejected",
                    status=AgentTaskStatus.INSUFFICIENT_EVIDENCE,
                    summary="The MCP request was rejected before execution",
                    evidence_refs=["draft-1"],
                    reason_codes=["MCP_TOOL_PLAN_REJECTED"],
                ).model_dump(mode="python"),
            ],
        }

        output = asyncio.run(verify(state))
        verified_run = VeriqRunState(**output["run"])

        self.assertEqual(verified_run.status, AgentRunStatus.FAILED)
        self.assertEqual(verified_run.error_code, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(verified_run.proposal["verification"]["verified"])

    def test_capability_arguments_cannot_be_supplied_without_an_intent(self):
        with self.assertRaises(ValueError):
            AutomationRunRequest(
                project_id="project-1",
                objective="Read an MCP source",
                intent_arguments={"tool_name": "getAuthenticatedUser"},
            )

    def test_lifecycle_triggers_choose_their_domain_workflow(self):
        cases = [
            (
                direct_recorded_test_execution_task,
                "TEST_EXECUTION_RECORDED",
                "test_result",
                "result-1",
                "process_recorded_test_execution",
                "result_id",
                "allowed",
            ),
            (
                direct_defect_event_task,
                "DEFECT_RECORDED",
                "defect",
                "defect-1",
                "process_recorded_defect",
                "defect_id",
                "allowed",
            ),
            (
                direct_approved_plan_task,
                "TEST_PLAN_APPROVED",
                "test_plan",
                "plan-approved-1",
                "process_approved_test_plan",
                "test_plan_id",
                "allowed",
            ),
            (
                direct_changed_plan_task,
                "TEST_PLAN_CHANGED",
                "test_plan",
                "plan-changed-1",
                "process_changed_test_plan",
                "test_plan_id",
                "allowed",
            ),
            (
                direct_event_observation_task,
                "RELEASE_CHANGED",
                "release",
                "release-1",
                "process_changed_release",
                "release_id",
                "release.close",
            ),
        ]

        for planner, trigger, artifact_type, artifact_id, tool_name, argument_name, permission in cases:
            with self.subTest(trigger=trigger):
                registered = {
                    tool_name: SimpleNamespace(
                        args_schema=SimpleNamespace(
                            model_json_schema=lambda: {"properties": {"project_id": {}}}
                        )
                    )
                }
                run = SimpleNamespace(
                    project_id="project-1",
                    permissions=[permission],
                    tool_calls=[],
                    source_event_id=(
                        "defect:defect-1:1"
                        if trigger == "DEFECT_RECORDED"
                        else "test-plan:plan-approved-1:1:TEST_PLAN_APPROVED"
                        if trigger == "TEST_PLAN_APPROVED"
                        else None
                    ),
                )
                state = {
                    "automatic": True,
                    "source_event_verified": True,
                    "constraints": {"trigger": trigger},
                    "target_artifact_ids": [artifact_id],
                    "evidence": [
                        {
                            "artifact_type": artifact_type,
                            "artifact_id": artifact_id,
                            "artifact_version_id": artifact_id,
                            "project_id": "project-1",
                            "artifact_revision": 1,
                            "text": "Saved source evidence",
                            **(
                                {"authority": "release_gate"}
                                if trigger == "RELEASE_CHANGED"
                                else {}
                            ),
                        }
                    ],
                }
                with (
                    patch(
                        "src.agents.runner.automation_event_tasks.registered_tools",
                        return_value=registered,
                    ),
                    patch(
                        "src.agents.runner.automation_event_tasks.tool_access",
                        return_value=SimpleNamespace(name=tool_name, permission=permission),
                    ),
                    patch(
                        "src.agents.runner.automation_event_tasks.validated_tasks",
                        side_effect=lambda tasks, *_args, **_kwargs: tasks,
                    ),
                ):
                    task = planner(run, state, [artifact_id])

                self.assertIsNotNone(task)
                self.assertEqual(len(task.tool_calls), 1)
                self.assertEqual(task.tool_calls[0].tool_name, tool_name)
                self.assertEqual(task.tool_calls[0].arguments[argument_name], artifact_id)
                if trigger == "TEST_PLAN_APPROVED":
                    self.assertEqual(task.tool_calls[0].arguments["expected_revision"], 1)
                    self.assertEqual(
                        task.tool_calls[0].arguments["source_event_id"],
                        "test-plan:plan-approved-1:1:TEST_PLAN_APPROVED",
                    )
                self.assertTrue(task.constraints["workflow_terminal"])

    def task_for(
        self, trigger, artifact_type, artifact_id, permission, tool_name,
        tool_properties, artifact_revision=None, source_event_id=None, relationship=None,
    ):
        tool = SimpleNamespace(
            name=tool_name,
            args_schema=SimpleNamespace(model_json_schema=lambda: {"properties": tool_properties})
        )
        tools = {tool_name: tool}
        access_by_name = {tool_name: SimpleNamespace(name=tool_name, permission=permission)}
        if trigger == "TEST_CASE_CHANGED":
            tools["get_test_case_draft"] = SimpleNamespace(
                name="get_test_case_draft",
                args_schema=SimpleNamespace(model_json_schema=lambda: {"properties": {"draft_id": {}}}),
            )
            tools["find_near_duplicates"] = SimpleNamespace(
                name="find_near_duplicates",
                args_schema=SimpleNamespace(model_json_schema=lambda: {"properties": {
                    "project_id": {}, "test_case_draft_id": {}, "expected_revision": {}
                }}),
            )
            access_by_name.update(
                {
                    "get_test_case_draft": SimpleNamespace(name="get_test_case_draft", permission="testcase.read"),
                    "find_near_duplicates": SimpleNamespace(name="find_near_duplicates", permission="testcase.duplicate_check"),
                }
            )
        access = SimpleNamespace(name=tool_name)
        run_permissions = list(dict.fromkeys(item.permission for item in access_by_name.values()))
        if trigger == "TEST_CASE_CHANGED":
            run_permissions.append("ai.run_duplicate_check")
        run = SimpleNamespace(
            project_id="project-1",
            permissions=run_permissions,
            tool_calls=[],
            source_event_id=source_event_id or (
                f"work-item:{artifact_id}:{artifact_revision}:WORK_ITEM_CHANGED"
                if trigger == "WORK_ITEM_CHANGED" and artifact_revision is not None
                else f"defect:{artifact_id}:{artifact_revision}"
                if trigger == "DEFECT_RECORDED" and artifact_revision is not None
                else None
            ),
        )
        state = {
            "automatic": True,
            "source_event_verified": True,
            "constraints": {"trigger": trigger},
            "evidence": [
                {
                    "artifact_type": artifact_type,
                    "artifact_id": artifact_id,
                    "artifact_version_id": artifact_id,
                    "project_id": "project-1",
                    **({"relationship": relationship} if relationship is not None else {}),
                    **(
                        {"artifact_revision": artifact_revision}
                        if artifact_revision is not None
                        else {"artifact_revision": 1}
                        if trigger in {
                            "API_OPERATION_CONFIRMED",
                            "TEST_CASE_APPROVED",
                            "TEST_PLAN_CHANGED",
                        }
                        else {}
                    ),
                    **(
                        {"authority": "release_gate"}
                        if trigger == "RELEASE_CHANGED"
                        else {}
                    ),
                }
            ],
        }
        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value=tools,
            ),
            patch(
                "src.agents.runner.automation_event_tasks.tool_access",
                side_effect=lambda value: access_by_name.get(getattr(value, "name", ""), access),
            ),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            return direct_event_observation_task(run, state, [artifact_id])

    def test_test_case_events_choose_the_scoped_automation_workflow(self):
        cases = [
            (
                "API_OPERATION_CONFIRMED",
                "api_operation",
                "api-operation-1",
                "ai.generate_api_testcase",
                "process_confirmed_api_operation",
                {"operation_id": {}, "project_id": {}},
            ),
            (
                "TEST_CASE_CHANGED",
                "test_case_draft",
                "draft-1",
                "testcase.lint",
                "lint_testcase",
                {"test_case_draft_id": {}},
            ),
            (
                "TEST_CASE_APPROVED",
                "test_case_version",
                "version-1",
                "testcase.read",
                "refresh_assurance_after_test_case_approval",
                {"project_id": {}, "version_id": {}},
            ),
        ]
        for trigger, artifact_type, artifact_id, permission, tool_name, properties in cases:
            with self.subTest(trigger=trigger):
                task = self.task_for(
                    trigger,
                    artifact_type,
                    artifact_id,
                    permission,
                    tool_name,
                    properties,
                    artifact_revision=1,
                )
                self.assertIsNotNone(task)
                self.assertEqual(
                    task.constraints["workflow_terminal"], trigger == "TEST_CASE_APPROVED"
                    or trigger == "API_OPERATION_CONFIRMED"
                )
                self.assertTrue(task.constraints["continue_after_observation"])
                if trigger == "TEST_CASE_CHANGED":
                    self.assertEqual(
                        [call.tool_name for call in task.tool_calls],
                        ["get_test_case_draft", "lint_testcase", "find_near_duplicates"],
                    )
                    self.assertEqual(
                        task.tool_calls[-1].arguments,
                        {
                            "project_id": "project-1",
                            "test_case_draft_id": "draft-1",
                            "expected_revision": 1,
                        },
                    )

    def test_release_metadata_events_do_not_schedule_release_close(self):
        task = self.task_for(
            "RELEASE_CHANGED",
            "release",
            "release-1",
            "release.close",
            "process_changed_release",
            {"project_id": {}, "release_id": {}},
        )
        self.assertIsNone(task)

    def test_test_case_change_requires_source_revision(self):
        task = self.task_for(
            "TEST_CASE_CHANGED",
            "test_case_draft",
            "draft-1",
            "testcase.lint",
            "lint_testcase",
            {"test_case_draft_id": {}},
        )

        self.assertIsNone(task)

    def test_test_case_creation_stops_without_a_change_baseline(self):
        task = self.task_for(
            "TEST_CASE_CHANGED",
            "test_case_draft",
            "draft-1",
            "testcase.lint",
            "lint_testcase",
            {"test_case_draft_id": {}},
            artifact_revision=1,
        )
        completed_task = AgentTask(
            run_id="run-1",
            project_id="project-1",
            user_id="user-1",
            **task.model_dump(mode="python"),
        )
        run = VeriqRunState(
            project_id="project-1",
            user_id="user-1",
            role="QA",
            objective="Tự xử lý thay đổi Test Case",
            completed_tasks=[completed_task.model_dump(mode="python")],
            agent_results=[
                AgentResult(
                    task_id=completed_task.task_id,
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã kiểm tra bản nháp",
                ).model_dump(mode="python")
            ],
        )
        state = {
            "run": run.model_dump(mode="python"),
            "tasks": [completed_task.model_dump(mode="python")],
            "automatic": True,
            "planning_round": 1,
            "evidence": [{"text": "Event type: TEST_CASE_CREATED\nCurrent revision: 1"}],
        }

        self.assertFalse(task.constraints["workflow_terminal"])
        self.assertEqual(route_after_agent(state), "finalize")

    def test_test_case_update_reads_only_parent_version_and_project_trace_matrix(self):
        tools = {
            "get_test_case_version_by_id": SimpleNamespace(
                name="get_test_case_version_by_id",
                args_schema=SimpleNamespace(
                    model_json_schema=lambda: {"properties": {"version_id": {}}}
                ),
            ),
            "get_traceability_links": SimpleNamespace(
                name="get_traceability_links",
                args_schema=SimpleNamespace(
                    model_json_schema=lambda: {
                        "properties": {"project_id": {}, "requirement_version_ids": {}}
                    }
                ),
            ),
        }
        access = {
            "get_test_case_version_by_id": SimpleNamespace(
                name="get_test_case_version_by_id", permission="testcase.version.read"
            ),
            "get_traceability_links": SimpleNamespace(
                name="get_traceability_links", permission="trace.read"
            ),
        }
        run = SimpleNamespace(
            project_id="project-1",
            permissions=["testcase.version.read", "trace.read"],
            observations=[
                {
                    "tool_name": "get_test_case_draft",
                    "status": "COMPLETED",
                    "result": {
                        "_id": "draft-1",
                        "project_id": "project-1",
                        "revision": 2,
                        "parent_version_id": "TCV-1",
                        "requirement_version_ids": ["REQV-1", "REQV-2", "REQV-1"],
                    },
                }
            ],
            tool_calls=[],
        )
        evidence = [
            {
                "project_id": "project-1",
                "text": (
                    "Event type: TEST_CASE_UPDATED\nCurrent revision: 2\n"
                    "Previous revision: 1\nChanged fields: steps\n"
                    "Before Test Case content:\nsteps: old\n"
                    "Current Test Case content:\nsteps: new"
                ),
            }
        ]
        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value=tools,
            ),
            patch(
                "src.agents.runner.automation_event_tasks.tool_access",
                side_effect=lambda value: access.get(getattr(value, "name", "")),
            ),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_test_case_change_impact_task(
                run,
                {
                    "automatic": True,
                    "source_event_verified": True,
                    "constraints": {"trigger": "TEST_CASE_CHANGED"},
                    "evidence": evidence,
                },
                ["draft-1", "REQV-1"],
            )

        self.assertIsNotNone(task)
        self.assertEqual(task.constraints["test_case_change_stage"], "PARENT_VERSION_READ")
        self.assertEqual(
            [(call.tool_name, call.arguments) for call in task.tool_calls],
            [("get_test_case_version_by_id", {"version_id": "TCV-1"})],
        )

        run.observations.append({
            "tool_name": "get_test_case_version_by_id",
            "status": "COMPLETED",
            "result": {
                "_id": "TCV-1",
                "project_id": "project-1",
                "requirement_version_ids": ["REQV-OLD", "REQV-2"],
            },
        })
        run.tool_calls.append({
            "tool_name": "get_test_case_version_by_id",
            "status": "COMPLETED",
            "arguments": {"version_id": "TCV-1"},
        })
        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value=tools,
            ),
            patch(
                "src.agents.runner.automation_event_tasks.tool_access",
                side_effect=lambda value: access.get(getattr(value, "name", "")),
            ),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_test_case_change_impact_task(
                run,
                {
                    "automatic": True,
                    "source_event_verified": True,
                    "constraints": {"trigger": "TEST_CASE_CHANGED"},
                    "evidence": evidence,
                },
                ["draft-1", "REQV-1", "REQV-2", "REQV-OLD"],
            )

        self.assertIsNotNone(task)
        self.assertTrue(task.constraints["workflow_terminal"])
        self.assertEqual(
            [(call.tool_name, call.arguments) for call in task.tool_calls],
            [(
                "get_traceability_links",
                {
                    "project_id": "project-1",
                    "requirement_version_ids": ["REQV-1", "REQV-2", "REQV-OLD"],
                },
            )],
        )

    def test_test_case_update_skips_traceability_when_requirement_scope_is_missing(self):
        tools = {
            "get_test_case_version_by_id": SimpleNamespace(
                name="get_test_case_version_by_id",
                args_schema=SimpleNamespace(
                    model_json_schema=lambda: {"properties": {"version_id": {}}}
                ),
            ),
            "get_traceability_links": SimpleNamespace(
                name="get_traceability_links",
                args_schema=SimpleNamespace(
                    model_json_schema=lambda: {
                        "properties": {"project_id": {}, "requirement_version_ids": {}}
                    }
                ),
            ),
        }
        access = {
            "get_test_case_version_by_id": SimpleNamespace(permission="testcase.version.read"),
            "get_traceability_links": SimpleNamespace(permission="trace.read"),
        }
        run = SimpleNamespace(
            project_id="project-1",
            permissions=["testcase.version.read", "trace.read"],
            observations=[{
                "tool_name": "get_test_case_draft",
                "status": "COMPLETED",
                "result": {
                    "_id": "draft-1", "project_id": "project-1", "revision": 2,
                    "parent_version_id": "TCV-1", "requirement_version_ids": [],
                },
            }],
            tool_calls=[],
        )
        with (
            patch("src.agents.runner.automation_event_tasks.registered_tools", return_value=tools),
            patch(
                "src.agents.runner.automation_event_tasks.tool_access",
                side_effect=lambda value: access.get(getattr(value, "name", "")),
            ),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_test_case_change_impact_task(
                run,
                {
                    "automatic": True,
                    "source_event_verified": True,
                    "constraints": {"trigger": "TEST_CASE_CHANGED"},
                    "evidence": [{
                        "project_id": "project-1",
                        "text": "Event type: TEST_CASE_UPDATED\nCurrent revision: 2\nPrevious revision: 1",
                    }],
                },
                ["draft-1"],
            )

        self.assertIsNone(task)

    def test_test_case_update_does_not_analyze_stale_revision_or_cross_project_draft(self):
        with patch(
            "src.agents.runner.automation_event_tasks.registered_tools",
            return_value={},
        ):
            for revision, project_id in ((1, "project-1"), (2, "other-project")):
                with self.subTest(revision=revision, project_id=project_id):
                    run = SimpleNamespace(
                        project_id="project-1",
                        permissions=["testcase.version.read", "trace.read"],
                        observations=[
                            {
                                "tool_name": "get_test_case_draft",
                                "status": "COMPLETED",
                                "result": {
                                    "_id": "draft-1",
                                    "project_id": project_id,
                                    "revision": revision,
                                    "parent_version_id": "TCV-1",
                                    "requirement_version_ids": ["REQV-1"],
                                },
                            }
                        ],
                        tool_calls=[],
                    )
                    evidence = [{
                        "project_id": "project-1",
                        "text": (
                            "Event type: TEST_CASE_UPDATED\nCurrent revision: 2\n"
                            "Previous revision: 1\nChanged fields: steps\n"
                            "Before Test Case content:\nsteps: old\n"
                            "Current Test Case content:\nsteps: new"
                        ),
                    }]
                    task = direct_test_case_change_impact_task(
                        run,
                        {
                            "automatic": True,
                            "source_event_verified": True,
                            "constraints": {"trigger": "TEST_CASE_CHANGED"},
                            "evidence": evidence,
                        },
                        ["draft-1", "REQV-1"],
                    )
                    self.assertIsNone(task)

    def test_test_case_update_replans_only_with_matching_before_after_revision_and_source(self):
        task = AgentTask(
            run_id="run-1",
            project_id="project-1",
            user_id="user-1",
            domain="test_design",
            objective="Rà soát thay đổi có căn cứ",
            constraints={"event_trigger": "TEST_CASE_CHANGED"},
            tool_calls=[
                ToolCall(tool_name="get_test_case_draft", arguments={"draft_id": "draft-1"}),
                ToolCall(tool_name="lint_testcase", arguments={"test_case_draft_id": "draft-1"}),
                ToolCall(tool_name="find_near_duplicates", arguments={"project_id": "project-1"}),
            ],
        )
        run = VeriqRunState(
            project_id="project-1",
            user_id="user-1",
            role="QA",
            objective="Rà soát thay đổi Test Case",
            completed_tasks=[task.model_dump(mode="python")],
            agent_results=[AgentResult(task_id=task.task_id, status=AgentTaskStatus.COMPLETED, summary="Đã rà soát").model_dump(mode="python")],
            observations=[{
                "tool_name": "get_test_case_draft",
                "status": "COMPLETED",
                "result": {"revision": 2, "requirement_version_ids": ["REQ-V1"]},
            }],
        )
        state = {
            "run": run.model_dump(mode="python"),
            "tasks": [task.model_dump(mode="python")],
            "automatic": True,
            "planning_round": 1,
            "evidence": [{"text": "Event type: TEST_CASE_UPDATED\nCurrent revision: 2\nPrevious revision: 1\nChanged fields: steps\nBefore Test Case content:\nCurrent Test Case content:"}],
        }
        self.assertEqual(route_after_agent(state), "replan")

    def test_replanning_passes_completed_step_context_to_the_planner(self):
        completed_task = AgentTask(
            task_id="task-lint",
            run_id="run-1",
            project_id="project-1",
            user_id="user-1",
            domain="test_design",
            objective="Đọc bản nháp và kiểm tra chất lượng Test Case vừa đổi",
            evidence_refs=["draft-1"],
            constraints={
                "event_trigger": "TEST_CASE_CHANGED",
                "continue_after_observation": True,
                "workflow_terminal": False,
            },
            tool_calls=[
                ToolCall(tool_name="lint_testcase", arguments={"test_case_draft_id": "draft-1"})
            ],
        )
        run = VeriqRunState(
            run_id="run-1",
            project_id="project-1",
            user_id="user-1",
            role="QA",
            permissions=["testcase.read", "testcase.lint", "trace.read"],
            objective="Tự xử lý thay đổi Test Case",
            completed_tasks=[completed_task.model_dump(mode="python")],
            agent_results=[
                AgentResult(
                    task_id="task-lint",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Bản nháp đã được lint, không có lỗi cấu trúc",
                ).model_dump(mode="python")
            ],
            tool_calls=[
                {
                    "tool_name": "lint_testcase",
                    "arguments": {"test_case_draft_id": "draft-1"},
                    "read_fingerprint": "verified-lint-read",
                }
            ],
            evidence_refs=["draft-1"],
        )
        state = {
            "automatic": True,
            "source_event_verified": True,
            "run": run.model_dump(mode="python"),
            "evidence": [
                {
                    "artifact_type": "test_case_draft",
                    "artifact_id": "draft-1",
                    "artifact_version_id": "draft-1",
                    "project_id": "project-1",
                    "text": "Bản nháp Test Case",
                }
            ],
            "target_artifact_ids": ["draft-1"],
            "constraints": {"trigger": "TEST_CASE_CHANGED"},
            "source_facts": [],
        }

        with (
            patch(
                "src.agents.runner.nodes.discover_project_tools_with_diagnostics",
                new=AsyncMock(return_value={"tools": [], "issues": []}),
            ),
            patch(
                "src.agents.runner.nodes.structured",
                new=AsyncMock(return_value=AgentPlan(intent="project_question")),
            ) as planner,
        ):
            asyncio.run(plan(state))

        prompt = planner.await_args.args[0]
        self.assertIn("completed_task_context", prompt)
        self.assertIn("Đọc bản nháp và kiểm tra chất lượng Test Case vừa đổi", prompt)
        self.assertIn("Bản nháp đã được lint", prompt)

    def test_work_item_and_release_events_stop_after_scoped_impact_read(self):
        task = self.task_for(
            "WORK_ITEM_CHANGED",
            "work_item",
            "work-item-1",
            "project.read",
            "get_work_item_impact_context",
            {"work_item_id": {}, "project_id": {}, "expected_revision": {}},
            artifact_revision=4,
        )
        self.assertIsNotNone(task)
        self.assertTrue(task.constraints["workflow_terminal"])
        self.assertEqual(task.tool_calls[0].arguments["expected_revision"], 4)

    def test_work_item_event_without_saved_revision_is_not_processed(self):
        task = self.task_for(
            "WORK_ITEM_CHANGED",
            "work_item",
            "work-item-1",
            "project.read",
            "get_work_item_impact_context",
            {"work_item_id": {}, "project_id": {}, "expected_revision": {}},
        )
        self.assertIsNone(task)

    def test_work_item_event_with_an_unmatched_event_id_is_not_processed(self):
        task = self.task_for(
            "WORK_ITEM_CHANGED",
            "work_item",
            "work-item-1",
            "project.read",
            "get_work_item_impact_context",
            {"work_item_id": {}, "project_id": {}, "expected_revision": {}},
            artifact_revision=4,
            source_event_id="work-item:work-item-1:3:WORK_ITEM_CHANGED",
        )
        self.assertIsNone(task)

    def test_dependency_event_id_is_bound_to_the_affected_work_item(self):
        relationship = {
            "relationship_id": "dependency-1",
            "relationship_type": "BLOCKS",
            "project_id": "project-1",
            "source_artifact_id": "work-item-1",
            "target_artifact_id": "work-item-2",
        }
        task = self.task_for(
            "WORK_ITEM_CHANGED",
            "work_item",
            "work-item-1",
            "project.read",
            "get_work_item_impact_context",
            {"work_item_id": {}, "project_id": {}, "expected_revision": {}},
            artifact_revision=4,
            source_event_id=(
                "work-item-dependency:dependency-1:work-item-1:WORK_ITEM_CHANGED"
            ),
            relationship=relationship,
        )
        self.assertIsNotNone(task)
        self.assertEqual(
            task.constraints["dependency_edge"]["relationship_id"],
            "dependency-1",
        )

    def test_work_item_event_finishes_after_read_and_reports_observed_links(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="qa-1",
            role="QA",
            objective="Rà soát tác động Work Item",
            evidence_refs=["work-item-1"],
            completed_tasks=[
                {
                    "task_id": "task-work-item-read",
                    "project_id": "project-1",
                    "constraints": {"workflow_terminal": True},
                }
            ],
            agent_results=[
                AgentResult(
                    task_id="task-work-item-read",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã đọc Work Item",
                    evidence_refs=["work-item-1"],
                ).model_dump(mode="python")
            ],
            observations=[
                {
                    "tool_name": "get_work_item_impact_context",
                    "status": "COMPLETED",
                    "result": {
                        "status": "completed",
                        "work_item": {"key": "APP-12"},
                        "linked_requirements": [{"requirement": {"_id": "REQ-1"}}],
                        "linked_test_cases": [{"_id": "TC-1"}, {"_id": "TC-2"}],
                    },
                }
            ],
        )
        state = {
            "run": run.model_dump(mode="python"),
            "tasks": [{"task_id": "task-work-item-read"}],
            "results": [
                AgentResult(
                    task_id="task-work-item-read",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã đọc Work Item",
                    evidence_refs=["work-item-1"],
                ).model_dump(mode="python")
            ],
            "automatic": True,
            "planning_round": 1,
            "constraints": {"trigger": "WORK_ITEM_CHANGED"},
        }

        self.assertEqual(route_after_agent(state), "finalize")
        aggregated = asyncio.run(aggregate(state))["run"]
        self.assertIn("đọc được 1 Requirement và 2 Test Case", aggregated["proposal"]["summary"])
        self.assertIn("không tự tạo hoặc sửa", aggregated["proposal"]["summary"])

        task = self.task_for(
            "RELEASE_CHANGED",
            "release",
            "release-1",
            "release.close",
            "process_changed_release",
            {"project_id": {}, "release_id": {}},
            artifact_revision=1,
        )
        self.assertIsNotNone(task)
        self.assertTrue(task.constraints["workflow_terminal"])

    def test_requirement_change_compiler_receives_only_facts_for_target_version(self):
        compiler_tool = SimpleNamespace(
            args_schema=SimpleNamespace(
                model_json_schema=lambda: {
                    "properties": {
                        "project_id": {},
                        "requirement_version_id": {},
                        "source_facts": {},
                    }
                }
            )
        )
        recommendation_tool = SimpleNamespace(
            args_schema=SimpleNamespace(
                model_json_schema=lambda: {
                    "properties": {
                        "project_id": {},
                        "requirement_version_id": {},
                        "expected_revision": {},
                    }
                }
            )
        )
        compiler_access = SimpleNamespace(
            name="process_changed_requirement_version", permission="requirement.approve"
        )
        recommendation_access = SimpleNamespace(
            name="recommend_test_design_techniques_for_requirement_change",
            permission="ai.generate_testcase",
        )
        run = SimpleNamespace(
            project_id="project-1",
            permissions=["requirement.approve", "ai.generate_testcase"],
            source_event_id="requirement-version:REQV-2:3:BASELINED",
        )
        state = {
            "automatic": True,
            "source_event_verified": True,
            "constraints": {"trigger": "REQUIREMENT_CHANGED"},
            "target_artifact_ids": ["REQV-2"],
            "evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-2",
                    "artifact_revision": 3,
                    "project_id": "project-1",
                }
            ],
            "source_facts": [
                {"artifact_id": "REQ-1", "artifact_version_id": "REQV-2", "quote": "new source"},
                {"artifact_id": "REQ-OLD", "artifact_version_id": "REQV-1", "quote": "old source"},
            ],
        }
        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value={
                    "process_changed_requirement_version": compiler_tool,
                    "recommend_test_design_techniques_for_requirement_change": recommendation_tool,
                },
            ),
            patch(
                "src.agents.runner.automation_event_tasks.tool_access",
                side_effect=lambda tool: (
                    None
                    if tool is None
                    else compiler_access
                    if tool is compiler_tool
                    else recommendation_access
                ),
            ),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_requirement_change_task(run, state, ["REQV-2"])

        self.assertIsNotNone(task)
        self.assertEqual(
            [call.tool_name for call in task.tool_calls],
            [
                "recommend_test_design_techniques_for_requirement_change",
                "process_changed_requirement_version",
            ],
        )
        self.assertEqual(task.tool_calls[0].arguments["expected_revision"], 3)
        self.assertEqual(task.tool_calls[1].arguments["requirement_version_id"], "REQV-2")
        self.assertEqual(task.tool_calls[1].arguments["source_facts"], [state["source_facts"][0]])

    def test_change_simulation_reads_only_the_explicit_requirement_baseline(self):
        tool_names = {"get_requirement_version", "get_traceability_links"}
        tools = {
            name: SimpleNamespace(
                args_schema=SimpleNamespace(
                    model_json_schema=lambda: {
                        "properties": {"project_id": {}, "requirement_version_id": {}}
                    }
                )
            )
            for name in tool_names
        }
        accesses = {
            name: SimpleNamespace(name=name, permission="project.read") for name in tool_names
        }
        run = SimpleNamespace(
            project_id="project-1",
            permissions=["project.read"],
            objective="Mô phỏng thay đổi yêu cầu",
        )
        simulation = {
            "base_requirement_version_id": "REQV-current",
            "proposed_source_text": "Yêu cầu đề xuất đã thay đổi",
        }
        state = {
            "constraints": {"change_simulation": True, "change_simulation_input": simulation},
            "evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-current",
                    "project_id": "project-1",
                },
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-old",
                    "project_id": "project-1",
                },
            ],
        }
        with (
            patch("src.agents.runner.automation_event_tasks.registered_tools", return_value=tools),
            patch(
                "src.agents.runner.automation_event_tasks.tool_access",
                side_effect=lambda tool: (
                    accesses[tool.args_schema.name]
                    if hasattr(tool.args_schema, "name")
                    else next(access for name, access in accesses.items() if tools[name] is tool)
                ),
            ),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_change_simulation_task(run, state, ["REQV-current", "REQV-old"])

        self.assertIsNotNone(task)
        self.assertEqual(
            [call.tool_name for call in task.tool_calls],
            ["get_requirement_version", "get_traceability_links"],
        )
        self.assertEqual(task.tool_calls[0].arguments["requirement_version_id"], "REQV-current")
        self.assertEqual(
            task.tool_calls[1].arguments,
            {"project_id": "project-1", "requirement_version_id": "REQV-current"},
        )
        self.assertTrue(task.constraints["change_simulation"])
        self.assertFalse(task.constraints["workflow_terminal"])
        self.assertEqual(task.constraints["change_simulation_input"], simulation)

    def test_change_simulation_follows_only_active_links_from_exact_baseline(self):
        observations = [
            {
                "tool_name": "get_traceability_links",
                "status": "COMPLETED",
                "result": {
                    "trace_links": [
                        {
                            "source_type": "requirement_version",
                            "source_id": "REQV-current",
                            "target_type": "test_case_version",
                            "target_id": "TCV-1",
                            "status": "CONFIRMED",
                        },
                        {
                            "source_type": "requirement_version",
                            "source_id": "REQV-current",
                            "target_type": "test_case_version",
                            "target_id": "TCV-2",
                            "status": "SUGGESTED",
                        },
                        {
                            "source_type": "requirement_version",
                            "source_id": "REQV-current",
                            "target_type": "test_case_version",
                            "target_id": "TCV-2",
                            "status": "SUGGESTED",
                        },
                        {
                            "source_type": "requirement_version",
                            "source_id": "REQV-old",
                            "target_type": "test_case_version",
                            "target_id": "TCV-old",
                            "status": "CONFIRMED",
                        },
                        {
                            "source_type": "acceptance_criterion",
                            "source_id": "AC-1",
                            "target_type": "test_case_version",
                            "target_id": "TCV-ac",
                            "status": "CONFIRMED",
                        },
                        {
                            "source_type": "requirement_version",
                            "source_id": "REQV-current",
                            "target_type": "test_case_version",
                            "target_id": "TCV-revoked",
                            "status": "REVOKED",
                        },
                    ]
                },
            },
            {
                "tool_name": "get_traceability_links",
                "status": "COMPLETED",
                "output_security": {"status": "REDACTED"},
                "result": {
                    "trace_links": [
                        {
                            "source_type": "requirement_version",
                            "source_id": "REQV-current",
                            "target_type": "test_case_version",
                            "target_id": "TCV-redacted",
                            "status": "CONFIRMED",
                        }
                    ]
                },
            },
        ]

        self.assertEqual(
            simulation_linked_test_case_version_ids(observations, "REQV-current"),
            ["TCV-1"],
        )

    def test_change_simulation_includes_cases_linked_through_baseline_acceptance_criteria(self):
        observations = [
            {
                "tool_name": "get_traceability_links",
                "status": "COMPLETED",
                "result": {
                    "acceptance_criteria": [
                        {"_id": "AC-current", "requirement_version_id": "REQV-current"},
                        {"_id": "AC-old", "requirement_version_id": "REQV-old"},
                    ],
                    "trace_links": [
                        {
                            "source_type": "acceptance_criterion",
                            "source_id": "AC-current",
                            "target_type": "test_case_version",
                            "target_id": "TCV-current-ac",
                            "status": "CONFIRMED",
                        },
                        {
                            "source_type": "acceptance_criterion",
                            "source_id": "AC-old",
                            "target_type": "test_case_version",
                            "target_id": "TCV-old-ac",
                            "status": "CONFIRMED",
                        },
                        {
                            "source_type": "acceptance_criterion",
                            "source_id": "AC-current",
                            "target_type": "test_case_version",
                            "target_id": "TCV-revoked-ac",
                            "status": "REVOKED",
                        },
                    ],
                },
            }
        ]

        self.assertEqual(
            simulation_linked_test_case_version_ids(observations, "REQV-current"),
            ["TCV-current-ac"],
        )

    def test_change_simulation_second_pass_reads_linked_versions_with_a_bounded_tool_batch(self):
        version_tool = SimpleNamespace(
            args_schema=SimpleNamespace(
                model_json_schema=lambda: {"properties": {"version_id": {}}}
            )
        )
        run = SimpleNamespace(
            project_id="project-1",
            permissions=["project.read", "testcase.version.read"],
            objective="Mô phỏng thay đổi yêu cầu",
            completed_tasks=[{"constraints": {"change_simulation_stage": "DISCOVERY"}}],
            tool_calls=[],
            observations=[
                {
                    "tool_name": "get_traceability_links",
                    "status": "COMPLETED",
                    "result": {
                        "trace_links": [
                            {
                                "source_type": "requirement_version",
                                "source_id": "REQV-current",
                                "target_type": "test_case_version",
                                "target_id": f"TCV-{index}",
                                "status": "CONFIRMED",
                            }
                            for index in range(9)
                        ]
                    },
                }
            ],
        )
        state = {
            "constraints": {
                "change_simulation": True,
                "change_simulation_input": {
                    "base_requirement_version_id": "REQV-current",
                    "proposed_source_text": "Yêu cầu đề xuất đã thay đổi",
                },
            },
            "evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-current",
                    "project_id": "project-1",
                }
            ],
        }
        access = SimpleNamespace(
            name="get_test_case_version_by_id", permission="testcase.version.read"
        )
        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value={"get_test_case_version_by_id": version_tool},
            ),
            patch("src.agents.runner.automation_event_tasks.tool_access", return_value=access),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_change_simulation_task(run, state, ["REQV-current"])

        self.assertIsNotNone(task)
        self.assertEqual(task.constraints["change_simulation_stage"], "LINKED_TEST_CASES")
        self.assertFalse(task.constraints["workflow_terminal"])
        self.assertTrue(task.constraints["continue_after_observation"])
        self.assertEqual(len(task.tool_calls), 6)
        self.assertEqual(task.constraints["omitted_linked_test_case_count"], 3)
        self.assertEqual(
            [call.arguments["version_id"] for call in task.tool_calls],
            [f"TCV-{index}" for index in range(6)],
        )

        run.tool_calls = [
            {
                "tool_name": "get_test_case_version_by_id",
                "arguments": {"version_id": f"TCV-{index}"},
            }
            for index in range(6)
        ]
        run.observations.extend(
            {
                "tool_name": "get_test_case_version_by_id",
                "status": "COMPLETED",
                "source_version_id": f"TCV-{index}",
                "result": {"_id": f"TCV-{index}"},
            }
            for index in range(6)
        )
        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value={"get_test_case_version_by_id": version_tool},
            ),
            patch("src.agents.runner.automation_event_tasks.tool_access", return_value=access),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            next_task = direct_change_simulation_task(run, state, ["REQV-current"])

        self.assertIsNotNone(next_task)
        self.assertEqual(
            [call.arguments["version_id"] for call in next_task.tool_calls],
            [f"TCV-{index}" for index in range(6, 9)],
        )
        self.assertEqual(next_task.constraints["omitted_linked_test_case_count"], 0)
        self.assertTrue(next_task.constraints["continue_after_observation"])
        self.assertFalse(next_task.constraints["workflow_terminal"])

    def test_change_simulation_retries_failed_version_reads_instead_of_skipping_them(self):
        run = SimpleNamespace(
            project_id="project-1",
            permissions=["project.read", "testcase.version.read"],
            objective="Mô phỏng thay đổi yêu cầu",
            completed_tasks=[{"constraints": {"change_simulation_stage": "DISCOVERY"}}],
            tool_calls=[
                {
                    "tool_name": "get_test_case_version_by_id",
                    "arguments": {"version_id": "TCV-5"},
                }
            ],
            observations=[
                {
                    "tool_name": "get_traceability_links",
                    "status": "COMPLETED",
                    "result": {
                        "trace_links": [
                            {
                                "source_type": "requirement_version",
                                "source_id": "REQV-current",
                                "target_type": "test_case_version",
                                "target_id": f"TCV-{index}",
                                "status": "CONFIRMED",
                            }
                            for index in range(9)
                        ]
                    },
                },
                *[
                    {
                        "tool_name": "get_test_case_version_by_id",
                        "status": "COMPLETED",
                        "source_version_id": f"TCV-{index}",
                        "result": {"_id": f"TCV-{index}"},
                    }
                    for index in range(5)
                ],
                {
                    "tool_name": "get_test_case_version_by_id",
                    "status": "FAILED",
                    "source_version_id": "TCV-5",
                    "result": None,
                },
            ],
        )
        state = {
            "constraints": {
                "change_simulation": True,
                "change_simulation_input": {
                    "base_requirement_version_id": "REQV-current",
                    "proposed_source_text": "Yêu cầu đề xuất đã thay đổi",
                },
            },
            "evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-current",
                    "project_id": "project-1",
                }
            ],
        }
        version_tool = SimpleNamespace(
            args_schema=SimpleNamespace(
                model_json_schema=lambda: {"properties": {"version_id": {}}}
            )
        )
        access = SimpleNamespace(
            name="get_test_case_version_by_id", permission="testcase.version.read"
        )
        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value={"get_test_case_version_by_id": version_tool},
            ),
            patch("src.agents.runner.automation_event_tasks.tool_access", return_value=access),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_change_simulation_task(run, state, ["REQV-current"])

        self.assertIsNotNone(task)
        self.assertEqual(
            [call.arguments["version_id"] for call in task.tool_calls],
            ["TCV-5", "TCV-6", "TCV-7", "TCV-8"],
        )
        self.assertFalse(task.constraints["workflow_terminal"])

    def test_change_simulation_does_not_count_unlinked_reads_against_remaining_scope(self):
        version_tool = SimpleNamespace(
            args_schema=SimpleNamespace(
                model_json_schema=lambda: {"properties": {"version_id": {}}}
            )
        )
        trace_links = [
            {
                "source_type": "requirement_version",
                "source_id": "REQV-current",
                "target_type": "test_case_version",
                "target_id": f"TCV-{index}",
                "status": "CONFIRMED",
            }
            for index in range(9)
        ]
        run = SimpleNamespace(
            project_id="project-1",
            permissions=["project.read", "testcase.version.read"],
            objective="Mô phỏng thay đổi yêu cầu",
            completed_tasks=[{"constraints": {"change_simulation_stage": "DISCOVERY"}}],
            tool_calls=[],
            observations=[
                {
                    "tool_name": "get_traceability_links",
                    "status": "COMPLETED",
                    "result": {"trace_links": trace_links},
                },
                *[
                    {
                        "tool_name": "get_test_case_version_by_id",
                        "status": "COMPLETED",
                        "source_version_id": f"TCV-unrelated-{index}",
                        "result": {"_id": f"TCV-unrelated-{index}"},
                    }
                    for index in range(6)
                ],
            ],
        )
        state = {
            "constraints": {
                "change_simulation": True,
                "change_simulation_input": {
                    "base_requirement_version_id": "REQV-current",
                    "proposed_source_text": "Yêu cầu đề xuất đã thay đổi",
                },
            },
            "evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-current",
                    "project_id": "project-1",
                }
            ],
        }
        access = SimpleNamespace(
            name="get_test_case_version_by_id", permission="testcase.version.read"
        )
        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value={"get_test_case_version_by_id": version_tool},
            ),
            patch("src.agents.runner.automation_event_tasks.tool_access", return_value=access),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_change_simulation_task(run, state, ["REQV-current"])

        self.assertIsNotNone(task)
        self.assertEqual(task.constraints["omitted_linked_test_case_count"], 3)
        self.assertFalse(task.constraints["workflow_terminal"])
        self.assertEqual(
            [call.arguments["version_id"] for call in task.tool_calls],
            [f"TCV-{index}" for index in range(6)],
        )

    def test_change_simulation_fails_closed_without_matching_baseline_evidence(self):
        run = SimpleNamespace(project_id="project-1", permissions=["project.read"])
        state = {
            "constraints": {
                "change_simulation": True,
                "change_simulation_input": {
                    "base_requirement_version_id": "REQV-current",
                    "proposed_source_text": "Yêu cầu đề xuất",
                },
            },
            "evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-old",
                }
            ],
        }
        with patch("src.agents.runner.automation_event_tasks.validated_tasks") as validate:
            task = direct_change_simulation_task(run, state, ["REQV-old"])

        self.assertIsNone(task)
        validate.assert_not_called()

    def test_change_simulation_replans_after_discovery_to_revalidate_scope(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="user-1",
            role="QA",
            objective="Mô phỏng thay đổi",
            completed_tasks=[
                {
                    "task_id": "task-discovery",
                    "constraints": {"change_simulation_stage": "DISCOVERY"},
                }
            ],
            agent_results=[
                AgentResult(
                    task_id="task-discovery",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã đọc baseline",
                ).model_dump(mode="python")
            ],
            observations=[
                {
                    "tool_name": "get_traceability_links",
                    "status": "COMPLETED",
                    "result": {
                        "trace_links": [
                            {
                                "source_type": "requirement_version",
                                "source_id": "REQV-current",
                                "target_type": "test_case_version",
                                "target_id": "TCV-linked",
                                "status": "CONFIRMED",
                            }
                        ]
                    },
                }
            ],
        )
        state = {
            "run": run.model_dump(mode="python"),
            "tasks": [{"task_id": "task-discovery"}],
            "constraints": {
                "change_simulation": True,
                "change_simulation_input": {"base_requirement_version_id": "REQV-current"},
            },
        }
        self.assertEqual(route_after_agent(state), "replan")

        run.observations = []
        state["run"] = run.model_dump(mode="python")
        self.assertEqual(route_after_agent(state), "replan")

    def test_change_simulation_finishes_after_linked_test_case_read_stage(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="user-1",
            role="QA",
            objective="Mô phỏng thay đổi",
            completed_tasks=[
                {
                    "task_id": "task-linked-cases",
                    "constraints": {
                        "change_simulation_stage": "LINKED_TEST_CASES",
                        "workflow_terminal": True,
                    },
                }
            ],
            agent_results=[
                AgentResult(
                    task_id="task-linked-cases",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã đối chiếu Test Case",
                ).model_dump(mode="python")
            ],
        )
        state = {
            "run": run.model_dump(mode="python"),
            "tasks": [{"task_id": "task-linked-cases"}],
            "constraints": {"change_simulation": True},
        }
        self.assertEqual(route_after_agent(state), "finalize")

    def test_change_simulation_replans_after_a_nonterminal_linked_case_batch(self):
        run = VeriqRunState(
            project_id="project-1",
            user_id="user-1",
            role="QA",
            objective="Mô phỏng thay đổi",
            completed_tasks=[
                {
                    "task_id": "task-discovery",
                    "constraints": {"change_simulation_stage": "DISCOVERY"},
                },
                {
                    "task_id": "task-linked-cases-1",
                    "constraints": {
                        "change_simulation_stage": "LINKED_TEST_CASES",
                        "continue_after_observation": True,
                        "workflow_terminal": False,
                    },
                },
            ],
            agent_results=[
                AgentResult(
                    task_id="task-discovery",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã đọc baseline",
                ).model_dump(mode="python"),
                AgentResult(
                    task_id="task-linked-cases-1",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã đọc lô phiên bản đầu tiên",
                ).model_dump(mode="python"),
            ],
        )
        state = {
            "run": run.model_dump(mode="python"),
            "tasks": [{"task_id": "task-linked-cases-1"}],
            "constraints": {"change_simulation": True},
            "automatic": True,
            "planning_round": 3,
        }

        self.assertEqual(route_after_agent(state), "replan")


if __name__ == "__main__":
    unittest.main()
