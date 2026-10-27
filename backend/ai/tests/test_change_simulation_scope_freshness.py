import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.agents.runner.automation_event_tasks import (
    direct_change_simulation_task,
    simulation_baseline_trace_links,
    simulation_baseline_trace_snapshot,
    simulation_linked_test_case_version_ids,
)
from src.services.change_simulation import simulation_trace_scope_is_current


class ChangeSimulationScopeFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.discovery = [
            {
                "source_type": "acceptance_criterion",
                "source_id": "AC-1",
                "target_type": "test_case_version",
                "target_id": "TCV-1",
                "link_type": "verifies",
                "status": "CONFIRMED",
            }
        ]

    def test_same_revalidated_scope_allows_current_report(self):
        self.assertTrue(
            simulation_trace_scope_is_current(self.discovery, list(self.discovery), True)
        )

    def test_added_link_invalidates_discovered_scope(self):
        changed = [
            *self.discovery,
            {
                "source_type": "requirement_version",
                "source_id": "REQV-1",
                "target_type": "test_case_version",
                "target_id": "TCV-2",
                "status": "CONFIRMED",
            },
        ]
        self.assertFalse(simulation_trace_scope_is_current(self.discovery, changed, True))

    def test_revoked_or_reclassified_link_invalidates_discovered_scope(self):
        changed = [{**self.discovery[0], "status": "REVOKED"}]
        self.assertFalse(simulation_trace_scope_is_current(self.discovery, changed, True))

    def test_changed_link_type_invalidates_discovered_scope(self):
        changed = [{**self.discovery[0], "link_type": "relates_to"}]
        self.assertFalse(simulation_trace_scope_is_current(self.discovery, changed, True))

    def test_missing_revalidation_never_confirms_scope(self):
        self.assertFalse(simulation_trace_scope_is_current(self.discovery, self.discovery, False))

    def _scope_observation(self, stage, criterion_content="Nội dung AC"):
        return {
            "tool_name": "get_traceability_links",
            "status": "COMPLETED",
            "change_simulation_stage": stage,
            "result": {
                "requirement_versions": [
                    {
                        "_id": "REQV-1",
                        "requirement_id": "REQ-1",
                        "version": 1,
                        "content_doc": {"text": "Yêu cầu gốc"},
                    }
                ],
                "acceptance_criteria": [
                    {
                        "_id": "AC-1",
                        "requirement_version_id": "REQV-1",
                        "content_doc": {"text": criterion_content},
                        "status": "approved",
                    }
                ],
                "trace_links": list(self.discovery),
            },
        }

    def test_criterion_change_invalidates_report_even_when_links_are_unchanged(self):
        discovery = simulation_baseline_trace_snapshot(
            [self._scope_observation("DISCOVERY")], "REQV-1", "DISCOVERY"
        )
        revalidated = simulation_baseline_trace_snapshot(
            [self._scope_observation("SCOPE_REVALIDATION", "Nội dung AC đã đổi")],
            "REQV-1",
            "SCOPE_REVALIDATION",
        )

        self.assertFalse(
            simulation_trace_scope_is_current(discovery, revalidated, True)
        )

    def test_trace_readback_missing_scoped_criteria_fails_closed(self):
        observation = self._scope_observation("SCOPE_REVALIDATION")
        del observation["result"]["acceptance_criteria"]

        snapshot = simulation_baseline_trace_snapshot(
            [observation], "REQV-1", "SCOPE_REVALIDATION"
        )

        self.assertIsNone(snapshot)
        self.assertFalse(simulation_trace_scope_is_current({}, snapshot, True))

    def test_suggested_links_are_reported_but_not_read_as_confirmed_test_cases(self):
        observations = [
            {
                "tool_name": "get_traceability_links",
                "status": "COMPLETED",
                "result": {
                    "trace_links": [
                        {
                            "source_type": "requirement_version",
                            "source_id": "REQV-1",
                            "target_type": "test_case_version",
                            "target_id": "TCV-confirmed",
                            "status": "CONFIRMED",
                        },
                        {
                            "source_type": "requirement_version",
                            "source_id": "REQV-1",
                            "target_type": "test_case_version",
                            "target_id": "TCV-suggested",
                            "status": "SUGGESTED",
                        },
                    ]
                },
            }
        ]

        baseline_links = simulation_baseline_trace_links(observations, "REQV-1", stage="DISCOVERY")

        self.assertEqual(
            [link["status"] for link in baseline_links],
            ["CONFIRMED", "SUGGESTED"],
        )
        self.assertEqual(
            simulation_linked_test_case_version_ids(observations, "REQV-1"),
            ["TCV-confirmed"],
        )

    def test_final_linked_case_batch_schedules_baseline_scope_revalidation(self):
        trace_tool = SimpleNamespace(
            args_schema=SimpleNamespace(
                model_json_schema=lambda: {"properties": {"project_id": {}, "requirement_version_id": {}}}
            )
        )
        run = SimpleNamespace(
            project_id="project-1",
            permissions=["project.read", "trace.read", "testcase.version.read"],
            objective="Mô phỏng thay đổi yêu cầu",
            completed_tasks=[{"constraints": {"change_simulation_stage": "DISCOVERY"}}],
            observations=[
                {
                    "tool_name": "get_traceability_links",
                    "status": "COMPLETED",
                    "result": {
                        "trace_links": [
                            {
                                "source_type": "requirement_version",
                                "source_id": "REQV-1",
                                "target_type": "test_case_version",
                                "target_id": "TCV-1",
                                "status": "CONFIRMED",
                            }
                        ]
                    },
                },
                {
                    "tool_name": "get_test_case_version_by_id",
                    "status": "COMPLETED",
                    "source_version_id": "TCV-1",
                    "result": {"_id": "TCV-1"},
                },
            ],
        )
        state = {
            "constraints": {
                "change_simulation": True,
                "change_simulation_input": {
                    "base_requirement_version_id": "REQV-1",
                    "proposed_source_text": "Nội dung đề xuất",
                },
            },
            "evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_id": "REQ-1",
                    "artifact_version_id": "REQV-1",
                    "project_id": "project-1",
                }
            ],
        }
        access = SimpleNamespace(name="get_traceability_links", permission="trace.read")

        with (
            patch(
                "src.agents.runner.automation_event_tasks.registered_tools",
                return_value={"get_traceability_links": trace_tool},
            ),
            patch("src.agents.runner.automation_event_tasks.tool_access", return_value=access),
            patch(
                "src.agents.runner.automation_event_tasks.validated_tasks",
                side_effect=lambda tasks, *_args, **_kwargs: tasks,
            ),
        ):
            task = direct_change_simulation_task(run, state, ["REQV-1"])

        self.assertEqual(task.constraints["change_simulation_stage"], "SCOPE_REVALIDATION")
        self.assertTrue(task.constraints["workflow_terminal"])
        self.assertEqual(task.tool_calls[0].tool_name, "get_traceability_links")
        self.assertEqual(
            task.tool_calls[0].arguments,
            {"project_id": "project-1", "requirement_version_id": "REQV-1"},
        )


if __name__ == "__main__":
    unittest.main()
