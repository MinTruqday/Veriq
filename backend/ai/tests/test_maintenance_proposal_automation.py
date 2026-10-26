import unittest
from unittest.mock import AsyncMock, patch

from src.tools.requirement_change_workflow import apply_grounded_maintenance_proposal
from src.tools.testing_api import AutomationOperationError


class MaintenanceProposalAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_applies_only_reviewed_exact_target_and_reads_back_current_version(self):
        analysis = {
            "_id": "impact-1",
            "project_id": "project-1",
            "status": "REVIEWED",
            "reviewed_affected_test_cases": [
                {
                    "classification": "NEEDS_UPDATE",
                    "test_case_id": "case-1",
                    "test_case_version_id": "case-v1",
                    "ai_maintenance_patch": {"steps": []},
                }
            ],
        }
        proposal = {
            "_id": "proposal-1",
            "project_id": "project-1",
            "impact_analysis_id": "impact-1",
            "proposal_type": "UPDATE_TEST_CASE",
            "target_artifact_id": "case-1",
            "base_version_id": "case-v1",
            "evidence": [{"source": "change-set"}],
            "status": "PENDING",
            "revision": 3,
        }
        readbacks = [
            {
                "_id": "proposal-1",
                "project_id": "project-1",
                "impact_analysis_id": "impact-1",
                "status": "ACCEPTED",
                "applied_artifact_id": "case-v2",
            },
            {
                "_id": "case-v2",
                "project_id": "project-1",
                "test_case_id": "case-1",
                "parent_version_id": "case-v1",
                "status": "ACTIVE",
                "requirement_version_ids": ["req-v2"],
            },
            {"_id": "case-1", "project_id": "project-1", "current_version_id": "case-v2"},
        ]
        with patch(
            "src.tools.requirement_change_workflow.require_operation",
            new=AsyncMock(side_effect=[{}, *readbacks]),
        ) as operation:
            result = await apply_grounded_maintenance_proposal(
                "project-1", "req-v2", analysis, proposal, {}
            )

        self.assertEqual(result["test_case_version_id"], "case-v2")
        self.assertEqual(operation.await_count, 4)
        self.assertEqual(
            operation.await_args_list[0].args[1],
            "/de-xuat-bao-tri/proposal-1/chap-nhan",
        )
        self.assertEqual(operation.await_args_list[0].args[3]["expected_revision"], 3)

    async def test_update_with_wrong_project_or_changed_parent_never_applies(self):
        analysis = {
            "_id": "impact-1",
            "project_id": "project-1",
            "status": "REVIEWED",
            "affected_test_cases": [
                {
                    "classification": "NEEDS_UPDATE",
                    "test_case_id": "case-1",
                    "test_case_version_id": "case-v1",
                    "ai_maintenance_patch": {"steps": []},
                }
            ],
        }
        proposal = {
            "_id": "proposal-1",
            "project_id": "other-project",
            "impact_analysis_id": "impact-1",
            "proposal_type": "UPDATE_TEST_CASE",
            "target_artifact_id": "case-1",
            "base_version_id": "case-v1",
            "evidence": [{"source": "change-set"}],
            "status": "PENDING",
            "revision": 1,
        }
        with patch(
            "src.tools.requirement_change_workflow.require_operation",
            new=AsyncMock(),
        ) as operation:
            with self.assertRaisesRegex(
                AutomationOperationError, "MAINTENANCE_PROPOSAL_SOURCE_SCOPE_INVALID"
            ):
                await apply_grounded_maintenance_proposal(
                    "project-1", "req-v2", analysis, proposal, {}
                )
        operation.assert_not_awaited()

    async def test_create_requires_exact_requirement_scope_and_evidence_before_mutation(self):
        analysis = {"_id": "impact-1", "project_id": "project-1", "status": "REVIEWED"}
        proposal = {
            "_id": "proposal-2",
            "project_id": "project-1",
            "impact_analysis_id": "impact-1",
            "proposal_type": "CREATE_TEST_CASE",
            "patch": {
                "title": "Verify login",
                "steps": [{"action_doc": {"text": "Sign in"}}],
                "requirement_version_ids": ["req-other"],
            },
            "evidence": ["source quote"],
            "status": "PENDING",
            "revision": 1,
        }
        with patch(
            "src.tools.requirement_change_workflow.require_operation",
            new=AsyncMock(),
        ) as operation:
            with self.assertRaisesRegex(
                AutomationOperationError,
                "MAINTENANCE_PROPOSAL_REQUIREMENT_SCOPE_INVALID",
            ):
                await apply_grounded_maintenance_proposal(
                    "project-1", "req-v2", analysis, proposal, {}
                )
        operation.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
