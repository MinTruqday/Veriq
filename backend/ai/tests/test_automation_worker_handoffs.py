import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.runtime.automation_worker import AutomationWorker
from src.schemas.automation import AutomationStatus, AutomationTrigger
from src.tools.requirement_document_workflow import qa_test_design_handoff_versions


class RequirementHandoffSelectionTests(unittest.TestCase):
    def test_only_baselined_testable_unblocked_versions_are_handed_to_qa(self):
        requirements = [
            {"version": {"_id": "base", "status": "BASELINED", "acceptance_criterion_ids": ["ac-1"]}},
            {"version": {"_id": "draft", "status": "DRAFT", "acceptance_criterion_ids": ["ac-2"]}},
            {"version": {"_id": "clarified", "status": "BASELINED", "acceptance_criterion_ids": ["ac-3"]}},
            {"version": {"_id": "unlinked", "status": "BASELINED"}},
            {"version": {"_id": "empty", "status": "BASELINED"}},
        ]
        obligations = {
            "unlinked": ([{"key": "ob-1"}], [{"key": "ob-orphan"}]),
        }

        handoffs = qa_test_design_handoff_versions(
            requirements,
            permissions=["requirement.create"],
            clarification_blocked_version_ids={"clarified"},
            obligations_by_version=obligations,
        )

        self.assertEqual(handoffs, ["base"])

    def test_combined_ba_qa_principal_does_not_create_a_second_handoff(self):
        handoffs = qa_test_design_handoff_versions(
            [{"version": {"_id": "base", "status": "BASELINED", "acceptance_criterion_ids": ["ac-1"]}}],
            permissions=["requirement.create", "ai.generate_testcase"],
            clarification_blocked_version_ids=set(),
            obligations_by_version={},
        )

        self.assertEqual(handoffs, [])


class AutomationWorkerHandoffTests(unittest.IsolatedAsyncioTestCase):
    async def test_verified_baseline_is_dispatched_to_a_separate_qa_stage_idempotently(self):
        worker = AutomationWorker()
        parent = SimpleNamespace(
            automation_run_id="parent-run",
            project_id="project-1",
            requester_user_id="ba-1",
            trigger=AutomationTrigger.DOCUMENT_INGESTED,
        )
        completed = SimpleNamespace(
            observations=[
                {
                    "tool_name": "process_ingested_requirement_document",
                    "status": "COMPLETED",
                    "verification": {"status": "COMPLETED"},
                    "result": {
                        "status": "COMPLETED",
                        "qa_test_design_handoff_version_ids": ["req-v1", "req-v1"],
                        "qa_test_design_handoff_evidence": [
                            {
                                "artifact_type": "requirement_version",
                                "artifact_id": "req-v1",
                                "artifact_version_id": "req-v1",
                                "source": "database",
                                "authority": "PROJECT_REQUIREMENT",
                                "text": "Authoritative saved requirement version content.",
                            }
                        ],
                        "source_facts": [
                            {
                                "artifact_version_id": "req-v1",
                                "quote": "Grounded acceptance criterion.",
                            },
                            {
                                "artifact_version_id": "req-v2",
                                "quote": "Must not leak into req-v1.",
                            },
                        ],
                    },
                }
            ]
        )
        qa_run = SimpleNamespace(
            automation_run_id="qa-run",
            status=AutomationStatus.QUEUED,
            error_code=None,
        )
        with patch(
            "src.runtime.automation_worker.automation_service.enqueue_event",
            new=AsyncMock(return_value=[qa_run]),
        ) as enqueue:
            workflows = await worker._enqueue_requirement_test_design_handoffs(
                parent, completed
            )

        self.assertEqual(
            workflows,
            [
                {
                    "requirement_version_id": "req-v1",
                    "automation_run_id": "qa-run",
                    "status": "QUEUED",
                    "reason_code": None,
                }
            ],
        )
        event = enqueue.await_args.args[0]
        self.assertEqual(event.event_id, "requirement-version:req-v1:INGESTED_TEST_DESIGN")
        self.assertEqual(event.project_id, "project-1")
        self.assertEqual(event.requester_user_id, "ba-1")
        self.assertEqual(event.parent_automation_run_id, "parent-run")
        self.assertEqual(event.trigger, AutomationTrigger.REQUIREMENT_CHANGED)
        self.assertEqual(event.target_artifact_ids, ["req-v1"])
        self.assertEqual(event.evidence[0].artifact_version_id, "req-v1")
        self.assertEqual(event.evidence[0].text, "Authoritative saved requirement version content.")

        with patch(
            "src.runtime.automation_worker.automation_service.enqueue_event",
            new=AsyncMock(return_value=[qa_run]),
        ) as replay_enqueue:
            await worker._enqueue_requirement_test_design_handoffs(parent, completed)
        replay_event = replay_enqueue.await_args.args[0]
        self.assertEqual(replay_event.event_id, event.event_id)

    async def test_missing_saved_requirement_evidence_is_not_sent_as_a_qa_event(self):
        worker = AutomationWorker()
        parent = SimpleNamespace(
            automation_run_id="parent-run",
            project_id="project-1",
            requester_user_id="ba-1",
            trigger=AutomationTrigger.DOCUMENT_INGESTED,
        )
        completed = SimpleNamespace(
            observations=[
                {
                    "tool_name": "process_ingested_requirement_document",
                    "status": "COMPLETED",
                    "verification": {"status": "COMPLETED"},
                    "result": {
                        "status": "COMPLETED",
                        "qa_test_design_handoff_version_ids": ["req-v1"],
                    },
                }
            ]
        )
        with patch(
            "src.runtime.automation_worker.automation_service.enqueue_event",
            new=AsyncMock(),
        ) as enqueue:
            workflows = await worker._enqueue_requirement_test_design_handoffs(
                parent, completed
            )

        self.assertEqual(
            workflows,
            [
                {
                    "requirement_version_id": "req-v1",
                    "status": "EVIDENCE_MISSING",
                    "reason_code": "QA_TEST_DESIGN_SOURCE_EVIDENCE_MISSING",
                }
            ],
        )
        enqueue.assert_not_awaited()

    async def test_unverified_or_incomplete_ingestion_never_dispatches_qa_work(self):
        worker = AutomationWorker()
        parent = SimpleNamespace(
            automation_run_id="parent-run",
            project_id="project-1",
            requester_user_id="ba-1",
            trigger=AutomationTrigger.DOCUMENT_INGESTED,
        )
        completed = SimpleNamespace(
            observations=[
                {
                    "tool_name": "process_ingested_requirement_document",
                    "status": "COMPLETED",
                    "verification": {"status": "COMPLETED"},
                    "result": {
                        "status": "automation_partial_failure",
                        "qa_test_design_handoff_version_ids": ["req-v1"],
                    },
                }
            ]
        )
        with patch(
            "src.runtime.automation_worker.automation_service.enqueue_event",
            new=AsyncMock(),
        ) as enqueue:
            workflows = await worker._enqueue_requirement_test_design_handoffs(
                parent, completed
            )

        self.assertEqual(workflows, [])
        enqueue.assert_not_awaited()

    async def test_non_document_events_do_not_dispatch_document_handoffs(self):
        worker = AutomationWorker()
        parent = SimpleNamespace(
            automation_run_id="parent-run",
            project_id="project-1",
            requester_user_id="qa-1",
            trigger=AutomationTrigger.TEST_CASE_CHANGED,
        )
        completed = SimpleNamespace(observations=[])
        with patch(
            "src.runtime.automation_worker.automation_service.enqueue_event",
            new=AsyncMock(),
        ) as enqueue:
            workflows = await worker._enqueue_requirement_test_design_handoffs(
                parent, completed
            )

        self.assertEqual(workflows, [])
        enqueue.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
