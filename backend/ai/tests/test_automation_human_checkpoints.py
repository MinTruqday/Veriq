import json
import unittest
import unicodedata
from unittest.mock import AsyncMock, patch

from src.tools.execution_workflows import process_approved_test_plan, process_changed_test_plan
from src.tools.testing import resolve_answered_clarifications, source_contains_exact_phrase
from src.tools.testing_api import AutomationOperationError


class AutomationHumanCheckpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_plan_approval_event_does_not_create_a_run(self):
        config = {
            "configurable": {
                "automation_run_id": "automation-run",
                "permissions": ["testrun.create", "testrun.execute"],
                "evidence": [
                    {
                        "project_id": "project",
                        "artifact_type": "test_plan",
                        "artifact_id": "plan",
                        "artifact_revision": 1,
                    }
                ],
            }
        }
        current_plan = {
            "_id": "plan",
            "project_id": "project",
            "revision": 2,
            "status": "APPROVED",
            "approved_snapshot": {"test_case_version_ids": ["case-v2"]},
            "approved_snapshot_hash": "new-snapshot-hash",
        }
        with (
            patch(
                "src.tools.execution_workflows.call",
                new=AsyncMock(return_value=json.dumps(current_plan)),
            ),
            patch(
                "src.tools.execution_workflows._start_test_run_from_approved_plan",
                new=AsyncMock(),
            ) as start_run,
        ):
            result = json.loads(
                await process_approved_test_plan.ainvoke(
                    {
                        "project_id": "project",
                        "test_plan_id": "plan",
                        "expected_revision": 1,
                        "source_event_id": "test-plan:plan:1:TEST_PLAN_APPROVED",
                    },
                    config,
                )
            )

        self.assertEqual(result["reason_code"], "TEST_PLAN_APPROVAL_EVENT_SUPERSEDED")
        start_run.assert_not_awaited()

    def test_clarification_evidence_requires_phrase_boundaries(self):
        self.assertTrue(source_contains_exact_phrase("Tài khoản đăng nhập hợp lệ", "đăng nhập"))
        self.assertFalse(source_contains_exact_phrase("Tài khoản đăng nhập hợp lệ", "nhập h"))
        self.assertFalse(source_contains_exact_phrase("Tài khoản đăng nhập hợp lệ", "login"))
        self.assertTrue(
            source_contains_exact_phrase(
                unicodedata.normalize("NFD", "Tài khoản đăng nhập"),
                unicodedata.normalize("NFC", "đăng nhập"),
            )
        )

    async def test_complete_plan_is_approved_and_locked_before_run_creation(self):
        config = {"configurable": {"automation_run_id": "run", "permissions": ["testplan.approve", "testrun.create", "testrun.execute"], "evidence": [{"project_id": "project", "artifact_type": "test_plan", "artifact_id": "plan", "artifact_revision": 4}]}}
        approved = {"_id": "plan", "project_id": "project", "status": "APPROVED", "approved_snapshot": {"test_case_version_ids": ["case-v1"]}, "approved_snapshot_hash": "same", "baseline_hash": "same"}
        with (
            patch("src.tools.execution_workflows.call", new=AsyncMock(side_effect=[json.dumps({"_id": "plan", "project_id": "project", "status": "DRAFT", "revision": 4, "test_case_version_ids": ["case-v1"]}), json.dumps({"ready_for_approval": True}), json.dumps(approved), json.dumps(approved)])) as call,
            patch("src.tools.execution_workflows._start_test_run_from_approved_plan", new=AsyncMock(return_value=json.dumps({"status": "completed", "verification": {"checks": []}}))) as start_run,
        ):
            result = json.loads(await process_changed_test_plan.ainvoke({"project_id": "project", "test_plan_id": "plan", "expected_revision": 4}, config))
        self.assertEqual(result["status"], "completed")
        self.assertIn("test_plan_approval_readback", result["verification"]["checks"])
        self.assertEqual(call.await_args_list[2].args[:2], ("POST", "/ke-hoach-kiem-thu/plan/phe-duyet"))
        self.assertEqual(call.await_args_list[2].args[3]["expected_revision"], 4)
        start_run.assert_awaited_once()

    async def test_agent_created_run_requests_confirmed_skill_autodistribution(self):
        from src.tools.execution_workflows import _start_test_run_from_approved_plan

        config = {"configurable": {"automation_run_id": "automation-run", "permissions": ["testrun.create", "testrun.execute"]}}
        run = {
            "_id": "run",
            "project_id": "project",
            "test_plan_id": "plan",
            "test_plan_snapshot_hash": "snapshot-hash",
            "status": "IN_PROGRESS",
            "test_case_version_ids": ["case-v1"],
            "test_case_assignments": {"case-v1": "tester-a"},
            "test_case_assignment_decisions": {
                "case-v1": {
                    "assignee_id": "tester-a",
                    "skill_profile_revision": 2,
                    "availability_at_assignment": "AVAILABLE",
                    "required_skills": ["API"],
                    "matched_skills": ["API"],
                    "active_run_count_before_assignment": 1,
                    "active_case_count_before_assignment": 3,
                }
            },
            "unassigned_assignment_reasons": [],
        }
        with patch(
            "src.tools.execution_workflows.call",
            new=AsyncMock(side_effect=[json.dumps(run), json.dumps(run)]),
        ) as call:
            result = json.loads(await _start_test_run_from_approved_plan(
                "project", "plan", {"name": "Smoke"},
                {"test_case_version_ids": ["case-v1"]}, "automation-run", "snapshot-hash", config,
            ))

        self.assertEqual(result["status"], "completed")
        self.assertIn("confirmed_assignment_snapshot", result["verification"]["checks"])
        self.assertEqual(call.await_args_list[0].args[1], "/du-an/project/lan-chay-kiem-thu")
        self.assertEqual(call.await_args_list[0].args[3]["assignment_strategy"], "PROFILE_EVIDENCE")
        self.assertEqual(
            call.await_args_list[0].args[3]["expected_test_plan_snapshot_hash"],
            "snapshot-hash",
        )

    async def test_agent_accepts_a_limited_but_confirmed_tester_assignment(self):
        from src.tools.execution_workflows import _start_test_run_from_approved_plan

        config = {"configurable": {"automation_run_id": "automation-run", "permissions": ["testrun.create", "testrun.execute"]}}
        run = {
            "_id": "run",
            "project_id": "project",
            "test_plan_id": "plan",
            "test_plan_snapshot_hash": "snapshot-hash",
            "status": "IN_PROGRESS",
            "test_case_version_ids": ["case-v1"],
            "test_case_assignments": {"case-v1": "tester-a"},
            "test_case_assignment_decisions": {
                "case-v1": {
                    "assignee_id": "tester-a",
                    "skill_profile_revision": 2,
                    "availability_at_assignment": "LIMITED",
                    "required_skills": ["API"],
                    "matched_skills": ["API"],
                    "active_run_count_before_assignment": 1,
                    "active_case_count_before_assignment": 3,
                }
            },
            "unassigned_assignment_reasons": [],
        }
        with patch(
            "src.tools.execution_workflows.call",
            new=AsyncMock(side_effect=[json.dumps(run), json.dumps(run)]),
        ) as call:
            result = json.loads(await _start_test_run_from_approved_plan(
                "project", "plan", {"name": "Smoke"},
                {"test_case_version_ids": ["case-v1"]}, "automation-run", "snapshot-hash", config,
            ))

        self.assertEqual(result["status"], "completed")
        self.assertIn("confirmed_assignment_snapshot", result["verification"]["checks"])
        self.assertEqual(call.await_args_list[0].args[3]["assignment_strategy"], "PROFILE_EVIDENCE")

    async def test_automation_does_not_start_run_when_assignment_snapshot_is_incomplete(self):
        from src.tools.execution_workflows import _start_test_run_from_approved_plan

        config = {"configurable": {"automation_run_id": "automation-run", "permissions": ["testrun.create", "testrun.execute"]}}
        run = {
            "_id": "run",
            "project_id": "project",
            "test_plan_id": "plan",
            "test_plan_snapshot_hash": "snapshot-hash",
            "status": "DRAFT",
            "test_case_version_ids": ["case-v1", "case-v2"],
            "test_case_assignments": {"case-v1": "tester-a"},
            "test_case_assignment_decisions": {},
            "unassigned_assignment_reasons": [],
        }
        with patch(
            "src.tools.execution_workflows.call",
            new=AsyncMock(return_value=json.dumps(run)),
        ) as call:
            result = json.loads(await _start_test_run_from_approved_plan(
                "project", "plan", {"name": "Smoke"},
                {"test_case_version_ids": ["case-v1", "case-v2"]},
                "automation-run", "snapshot-hash", config,
            ))

        self.assertEqual(result["status"], "automation_partial_failure")
        self.assertEqual(result["reason_code"], "TEST_RUN_ASSIGNMENT_SNAPSHOT_INVALID")
        self.assertEqual(len(call.await_args_list), 1)
        self.assertNotIn("bat-dau", call.await_args_list[0].args[1])

    async def test_automation_starts_assigned_cases_and_reports_unassigned_cases(self):
        from src.tools.execution_workflows import _start_test_run_from_approved_plan

        config = {"configurable": {"automation_run_id": "automation-run", "permissions": ["testrun.create", "testrun.execute"]}}
        run = {
            "_id": "run",
            "project_id": "project",
            "test_plan_id": "plan",
            "test_plan_snapshot_hash": "snapshot-hash",
            "status": "DRAFT",
            "test_case_version_ids": ["case-v1", "case-v2"],
            "test_case_assignments": {"case-v1": "tester-a"},
            "test_case_assignment_decisions": {
                "case-v1": {
                    "assignee_id": "tester-a",
                    "skill_profile_revision": 2,
                    "availability_at_assignment": "AVAILABLE",
                    "required_skills": ["API"],
                    "matched_skills": ["API"],
                    "active_run_count_before_assignment": 0,
                    "active_case_count_before_assignment": 0,
                }
            },
            "unassigned_assignment_reasons": [
                {"test_case_version_id": "case-v2", "reason": "NO_FULL_SKILL_MATCH"}
            ],
        }
        started_run = {**run, "status": "IN_PROGRESS"}
        with patch(
            "src.tools.execution_workflows.call",
            new=AsyncMock(
                side_effect=[
                    json.dumps(run),
                    json.dumps(started_run),
                    json.dumps(started_run),
                ]
            ),
        ) as call:
            result = json.loads(await _start_test_run_from_approved_plan(
                "project", "plan", {"name": "Smoke"},
                {"test_case_version_ids": ["case-v1", "case-v2"]},
                "automation-run", "snapshot-hash", config,
            ))

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["status_after_start"], "IN_PROGRESS")
        self.assertEqual(result["unassigned_assignment_reasons"], run["unassigned_assignment_reasons"])
        self.assertEqual(len(call.await_args_list), 3)
        self.assertEqual(call.await_args_list[1].args[1], "/lan-chay-kiem-thu/run/bat-dau")
        self.assertEqual(call.await_args_list[2].args[1], "/lan-chay-kiem-thu/run")

    async def test_automation_reports_supported_profile_assignment_gaps_as_blocked(self):
        from src.tools.execution_workflows import _start_test_run_from_approved_plan

        config = {"configurable": {"automation_run_id": "automation-run", "permissions": ["testrun.create", "testrun.execute"]}}
        for reason in ("PROFILE_NOT_CONFIRMED", "NO_AVAILABLE_TESTER"):
            run = {
                "_id": "run",
                "project_id": "project",
                "test_plan_id": "plan",
                "test_plan_snapshot_hash": "snapshot-hash",
                "status": "DRAFT",
                "test_case_version_ids": ["case-v1"],
                "test_case_assignments": {},
                "test_case_assignment_decisions": {},
                "unassigned_assignment_reasons": [
                    {"test_case_version_id": "case-v1", "reason": reason}
                ],
            }
            with patch(
                "src.tools.execution_workflows.call",
                new=AsyncMock(return_value=json.dumps(run)),
            ) as call:
                result = json.loads(await _start_test_run_from_approved_plan(
                    "project", "plan", {"name": "Smoke"},
                    {"test_case_version_ids": ["case-v1"]}, "automation-run", "snapshot-hash", config,
                ))

            self.assertEqual(result["status"], "automation_blocked")
            self.assertEqual(result["reason_code"], "TEST_RUN_HAS_UNASSIGNED_CASES")
            self.assertEqual(result["unassigned_assignment_reasons"][0]["reason"], reason)
            self.assertEqual(len(call.await_args_list), 1)
            self.assertNotIn("bat-dau", call.await_args_list[0].args[1])

    async def test_plan_does_not_approve_when_deterministic_gate_fails(self):
        config = {"configurable": {"automation_run_id": "run", "permissions": ["testplan.approve", "testrun.create"], "evidence": [{"project_id": "project", "artifact_type": "test_plan", "artifact_id": "plan", "artifact_revision": 4}]}}
        with patch("src.tools.execution_workflows.call", new=AsyncMock(side_effect=[json.dumps({"_id": "plan", "project_id": "project", "status": "DRAFT", "revision": 4, "test_case_version_ids": ["case-v1"]}), json.dumps({"ready_for_approval": False, "findings": [{"code": "MISSING_SCOPE"}]})])) as call:
            result = json.loads(await process_changed_test_plan.ainvoke({"project_id": "project", "test_plan_id": "plan", "expected_revision": 4}, config))
        self.assertEqual(result["reason_code"], "TEST_PLAN_INCOMPLETE")
        self.assertFalse(any("phe-duyet" in item.args[1] for item in call.await_args_list))

    async def test_plan_without_signed_approval_permission_is_not_mutated(self):
        config = {"configurable": {"automation_run_id": "run", "permissions": ["testrun.create"], "evidence": [{"project_id": "project", "artifact_type": "test_plan", "artifact_id": "plan", "artifact_revision": 4}]}}
        with patch("src.tools.execution_workflows.call", new=AsyncMock()) as call:
            result = json.loads(await process_changed_test_plan.ainvoke({"project_id": "project", "test_plan_id": "plan", "expected_revision": 4}, config))
        self.assertEqual(result["reason_code"], "TEST_PLAN_APPROVAL_PERMISSION_REQUIRED")
        call.assert_not_awaited()

    async def test_answer_in_updated_source_is_resolved_by_qa_automation(self):
        question = {"_id": "clarification", "status": "ANSWERED", "answer": "Five attempts", "revision": 2}
        config = {"configurable": {"permissions": ["requirement.approve"]}}
        with patch(
            "src.tools.testing.require_operation",
            new=AsyncMock(side_effect=[[question], {"_id": "clarification", "status": "RESOLVED"}]),
        ) as operation:
            pending = await resolve_answered_clarifications(
                {"_id": "v1", "plain_text_projection": "Five attempts"}, config
            )
        self.assertEqual(pending, [])
        operation.assert_any_await(
            "POST",
            "/phieu-lam-ro/clarification/xac-nhan-giai-quyet",
            config,
            {
                "expected_revision": 2,
                "requirement_version_id": "v1",
                "evidence_quote": "Five attempts",
            },
        )

    async def test_answer_matching_source_without_case_difference_is_resolved(self):
        question = {"_id": "clarification", "status": "ANSWERED", "answer": "five attempts", "revision": 2}
        config = {"configurable": {"permissions": ["requirement.approve"]}}
        with patch(
            "src.tools.testing.require_operation",
            new=AsyncMock(side_effect=[[question], {"_id": "clarification", "status": "RESOLVED"}]),
        ) as operation:
            pending = await resolve_answered_clarifications(
                {"_id": "v1", "plain_text_projection": "Five Attempts"}, config
            )

        self.assertEqual(pending, [])
        self.assertEqual(
            operation.await_args_list[1].args[3]["evidence_quote"],
            "five attempts",
        )

    async def test_answer_absent_from_updated_source_keeps_clarification_blocked(self):
        question = {"_id": "clarification", "status": "ANSWERED", "answer": "Five attempts", "revision": 2}
        config = {"configurable": {"permissions": ["requirement.approve"]}}
        with patch("src.tools.testing.require_operation", new=AsyncMock(return_value=[question])) as operation:
            pending = await resolve_answered_clarifications(
                {"_id": "v1", "plain_text_projection": "The answer is not present"}, config
            )
        self.assertEqual(pending, [question])
        operation.assert_awaited_once_with("GET", "/phien-ban-yeu-cau/v1/phieu-lam-ro", config)

    async def test_answer_cannot_match_across_requirement_fields(self):
        question = {"_id": "clarification", "status": "ANSWERED", "answer": "dùng đăng nhập", "revision": 2}
        config = {"configurable": {"permissions": ["requirement.approve"]}}
        with patch(
            "src.tools.testing.require_operation", new=AsyncMock(return_value=[question])
        ) as operation:
            pending = await resolve_answered_clarifications(
                {
                    "_id": "v1",
                    "plain_text_projection": "Người dùng",
                    "acceptance_criteria": [{"plain_text": "đăng nhập"}],
                },
                config,
            )

        self.assertEqual(pending, [question])
        operation.assert_awaited_once_with("GET", "/phien-ban-yeu-cau/v1/phieu-lam-ro", config)

    async def test_non_qa_automation_does_not_resolve_answered_clarification(self):
        question = {"_id": "clarification", "status": "ANSWERED", "answer": "Five attempts", "revision": 2}
        config = {"configurable": {"permissions": ["requirement.create"]}}
        with patch("src.tools.testing.require_operation", new=AsyncMock(return_value=[question])) as operation:
            pending = await resolve_answered_clarifications(
                {"_id": "v1", "plain_text_projection": "Five attempts"}, config
            )
        self.assertEqual(pending, [question])
        operation.assert_awaited_once_with("GET", "/phien-ban-yeu-cau/v1/phieu-lam-ro", config)

    async def test_resolution_permission_denial_is_not_treated_as_success(self):
        question = {"_id": "clarification", "status": "ANSWERED", "answer": "Five attempts", "revision": 2}
        config = {"configurable": {"permissions": ["requirement.approve"]}}
        with patch(
            "src.tools.testing.require_operation",
            new=AsyncMock(side_effect=[
                [question],
                AutomationOperationError("PROJECT_PERMISSION_DENIED"),
                [question],
            ]),
        ) as operation:
            with self.assertRaisesRegex(AutomationOperationError, "PROJECT_PERMISSION_DENIED"):
                await resolve_answered_clarifications(
                    {"_id": "v1", "plain_text_projection": "Five attempts"}, config
                )
        self.assertEqual(operation.await_count, 3)

    async def test_concurrent_resolution_is_idempotent_after_exact_readback(self):
        question = {"_id": "clarification", "status": "ANSWERED", "answer": "Five attempts", "revision": 2}
        resolved = {
            **question,
            "status": "RESOLVED",
            "resolved_requirement_version_id": "v1",
            "resolution_evidence_quote": "Five attempts",
        }
        config = {"configurable": {"permissions": ["requirement.approve"]}}
        with patch(
            "src.tools.testing.require_operation",
            new=AsyncMock(side_effect=[[question], AutomationOperationError("INVALID_STATE_TRANSITION"), [resolved]]),
        ) as operation:
            pending = await resolve_answered_clarifications(
                {"_id": "v1", "plain_text_projection": "Five attempts"}, config
            )
        self.assertEqual(pending, [])
        self.assertEqual(operation.await_count, 3)


if __name__ == "__main__":
    unittest.main()
