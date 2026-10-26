import json
import unittest
from unittest.mock import AsyncMock, patch

from src.tools.execution_workflows import process_changed_release


class AutomationReleaseCloseTests(unittest.IsolatedAsyncioTestCase):
    def config(self, *, permissions=None, evidence=None):
        return {
            "configurable": {
                "automation_run_id": "run-1",
                "source_event_id": "release-gate:REL-1:test-result:RESULT-1:r1",
                "permissions": permissions or ["release.close"],
                "evidence": evidence or [
                    {
                        "project_id": "project-1",
                        "artifact_type": "release",
                        "artifact_id": "REL-1",
                        "artifact_revision": 7,
                        "authority": "release_gate",
                    }
                ],
            }
        }

    async def test_active_release_closes_only_via_gated_api_and_is_read_back(self):
        active = {"_id": "REL-1", "project_id": "project-1", "status": "ACTIVE", "revision": 7}
        closed = {"_id": "REL-1", "project_id": "project-1", "status": "CLOSED", "revision": 8}
        plan = {"_id": "PLAN-1", "project_id": "project-1", "status": "APPROVED", "approved_snapshot": {"release_id": "REL-1", "build_id": "BUILD-1"}, "approved_snapshot_hash": "same", "baseline_hash": "same"}
        monitoring = {"_id": "SNAPSHOT-1", "project_id": "project-1"}
        report = {"_id": "REPORT-1", "project_id": "project-1", "release_id": "REL-1", "test_plan_id": "PLAN-1", "monitoring_snapshot_id": "SNAPSHOT-1", "status": "DRAFT", "automation_run_id": "run-1"}
        with patch(
            "src.tools.execution_workflows.call",
            new=AsyncMock(side_effect=[json.dumps(active), json.dumps([plan]), json.dumps(monitoring), json.dumps(report), json.dumps(closed), json.dumps(closed)]),
        ) as call:
            result = json.loads(
                await process_changed_release.ainvoke(
                    {"project_id": "project-1", "release_id": "REL-1", "expected_revision": 7}, self.config()
                )
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["release_status"], "CLOSED")
        self.assertEqual(
            call.await_args_list[4].args[:2],
            ("POST", "/ban-phat-hanh/REL-1/dong"),
        )
        self.assertEqual(call.await_args_list[4].args[3]["expected_revision"], 7)
        self.assertIn("release_assurance_gate", result["verification"]["checks"])

    async def test_release_gate_failure_preserves_active_release(self):
        active = {"_id": "REL-1", "project_id": "project-1", "status": "ACTIVE", "revision": 7}
        plan = {"_id": "PLAN-1", "project_id": "project-1", "status": "APPROVED", "approved_snapshot": {"release_id": "REL-1", "build_id": "BUILD-1"}, "approved_snapshot_hash": "same", "baseline_hash": "same"}
        monitoring = {"_id": "SNAPSHOT-1", "project_id": "project-1"}
        report = {"_id": "REPORT-1", "project_id": "project-1", "release_id": "REL-1", "test_plan_id": "PLAN-1", "monitoring_snapshot_id": "SNAPSHOT-1", "status": "DRAFT", "automation_run_id": "run-1"}
        with patch(
            "src.tools.execution_workflows.call",
            new=AsyncMock(
                side_effect=[json.dumps(active), json.dumps([plan]), json.dumps(monitoring), json.dumps(report), json.dumps({"status": "qa_operation_failed", "upstream_status": 409, "error": {"code": "RELEASE_EXIT_CRITERIA_INCOMPLETE"}})]
            ),
        ) as call:
            result = json.loads(
                await process_changed_release.ainvoke(
                    {"project_id": "project-1", "release_id": "REL-1", "expected_revision": 7}, self.config()
                )
            )

        self.assertEqual(result["status"], "automation_blocked")
        self.assertEqual(result["reason_code"], "RELEASE_EXIT_CRITERIA_INCOMPLETE")
        self.assertEqual(result["release_status"], "ACTIVE")
        self.assertEqual(call.await_count, 5)

    async def test_wrong_project_event_never_reads_or_closes_release(self):
        with patch("src.tools.execution_workflows.call", new=AsyncMock()) as call:
            result = json.loads(
                await process_changed_release.ainvoke(
                    {"project_id": "project-2", "release_id": "REL-1", "expected_revision": 7}, self.config()
                )
            )
        self.assertEqual(
            result["reason_code"], "VERIFIED_RELEASE_GATE_RECHECK_EVENT_REQUIRED"
        )
        call.assert_not_awaited()

    async def test_release_metadata_event_cannot_trigger_gate_close(self):
        evidence = [
            {
                "project_id": "project-1",
                "artifact_type": "release",
                "artifact_id": "REL-1",
                "artifact_revision": 7,
                "authority": "release",
            }
        ]
        config = self.config(evidence=evidence)
        config["configurable"]["source_event_id"] = "release:REL-1:7:RELEASE_CHANGED"
        with patch("src.tools.execution_workflows.call", new=AsyncMock()) as call:
            result = json.loads(
                await process_changed_release.ainvoke(
                    {"project_id": "project-1", "release_id": "REL-1", "expected_revision": 7},
                    config,
                )
            )
        self.assertEqual(
            result["reason_code"], "VERIFIED_RELEASE_GATE_RECHECK_EVENT_REQUIRED"
        )
        call.assert_not_awaited()

    async def test_missing_scoped_permission_never_reads_or_closes_release(self):
        with patch("src.tools.execution_workflows.call", new=AsyncMock()) as call:
            result = json.loads(
                await process_changed_release.ainvoke(
                    {"project_id": "project-1", "release_id": "REL-1", "expected_revision": 7},
                    self.config(permissions=["release.read"]),
                )
            )
        self.assertEqual(result["reason_code"], "RELEASE_CLOSE_PERMISSION_REQUIRED")
        call.assert_not_awaited()

    async def test_non_active_release_is_left_unchanged(self):
        planned = {"_id": "REL-1", "project_id": "project-1", "status": "PLANNED", "revision": 7}
        with patch(
            "src.tools.execution_workflows.call", new=AsyncMock(return_value=json.dumps(planned))
        ) as call:
            result = json.loads(
                await process_changed_release.ainvoke(
                    {"project_id": "project-1", "release_id": "REL-1", "expected_revision": 7}, self.config()
                )
            )
        self.assertEqual(result["reason_code"], "RELEASE_NOT_ACTIVE")
        self.assertFalse(result["close_attempted"])
        self.assertEqual(call.await_count, 1)


if __name__ == "__main__":
    unittest.main()
