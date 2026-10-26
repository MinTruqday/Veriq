import json
import unittest
from unittest.mock import AsyncMock, patch

from src.tools.execution_workflows import process_approved_performance_configuration


class ApprovedPerformanceConfigurationTests(unittest.IsolatedAsyncioTestCase):
    def config(self):
        return {
            "configurable": {
                "automation_run_id": "run-1",
                "trigger": "PERFORMANCE_CONFIGURATION_APPROVED",
                "permissions": ["ai.generate_performance_plan"],
                "evidence": [
                    {
                        "project_id": "project-1",
                        "artifact_type": "non_functional_test_plan",
                        "artifact_id": "NFR-1",
                        "artifact_revision": 4,
                    }
                ],
            }
        }

    async def test_missing_configuration_input_is_returned_as_waiting_not_guessed(self):
        source_event_id = (
            "performance-configuration:NFR-1:4:PERFORMANCE_CONFIGURATION_APPROVED"
        )
        approved_plan = {
            "_id": "NFR-1",
            "project_id": "project-1",
            "plan_type": "PERFORMANCE_TEST_PLAN",
            "status": "APPROVED",
            "revision": 4,
        }
        waiting = {
            "status": "automation_waiting_for_input",
            "reason_code": "CLARIFICATION_REQUIRED",
            "source_configuration_id": "NFR-1",
            "source_event_id": source_event_id,
            "source_event_revision": 4,
            "missing_inputs": ["duration_minutes"],
            "question": "Bổ sung duration_minutes.",
        }
        with patch(
            "src.tools.execution_workflows.call",
            new=AsyncMock(
                side_effect=[json.dumps(approved_plan), json.dumps(waiting)]
            ),
        ) as call:
            result = json.loads(
                await process_approved_performance_configuration.ainvoke(
                    {
                        "project_id": "project-1",
                        "plan_id": "NFR-1",
                        "source_event_id": source_event_id,
                        "source_event_revision": 4,
                    },
                    self.config(),
                )
            )

        self.assertEqual(result["status"], "automation_waiting_for_input")
        self.assertEqual(result["missing_inputs"], ["duration_minutes"])
        self.assertEqual(call.await_count, 2)

    async def test_event_from_another_trigger_cannot_read_configuration(self):
        with patch("src.tools.execution_workflows.call", new=AsyncMock()) as call:
            result = json.loads(
                await process_approved_performance_configuration.ainvoke(
                    {
                        "project_id": "project-1",
                        "plan_id": "NFR-1",
                        "source_event_id": "unrelated-event",
                        "source_event_revision": 4,
                    },
                    {
                        "configurable": {
                            **self.config()["configurable"],
                            "trigger": "REQUIREMENT_CHANGED",
                        }
                    },
                )
            )

        self.assertEqual(result["status"], "automation_blocked")
        self.assertEqual(
            result["reason_code"],
            "VERIFIED_PERFORMANCE_CONFIGURATION_EVENT_REQUIRED",
        )
        call.assert_not_awaited()
