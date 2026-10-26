from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.quality.services.proposal_application import (
    create_test_draft_from_proposal,
    create_test_version_from_proposal,
)
from src.modules.design.services.test_case_records import (
    acceptance_criteria_snapshot_matches,
)


class MaintenanceProposalEvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_approved_revision_creates_child_version_without_mutating_frozen_base(self):
        base_version = {
            "_id": "TCV-1",
            "project_id": "PRJ-1",
            "test_case_id": "TC-1",
            "version": 1,
            "status": "ACTIVE",
            "title": "Đăng nhập",
            "plain_text_projection": "Đăng nhập",
            "steps": [{"id": "step-1", "order": 1}],
            "requirement_version_ids": ["REQV-1"],
        }
        original_base = dict(base_version)
        proposal = {
            "_id": "PROP-1",
            "project_id": "PRJ-1",
            "target_artifact_id": "TC-1",
            "base_version_id": "TCV-1",
            "impact_analysis_id": "IMPACT-1",
            "reason": "Requirement đã thay đổi",
            "evidence": ["REQV-2"],
        }
        test_case = {"_id": "TC-1", "current_version_id": "TCV-1"}

        with (
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_test_case",
                new=AsyncMock(return_value=test_case),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_test_version",
                new=AsyncMock(
                    side_effect=lambda version_id, *_args: (
                        base_version if version_id == "TCV-1" else None
                    )
                ),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_impact_analysis",
                new=AsyncMock(return_value={"change_set_id": "CHANGE-1"}),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_change_set",
                new=AsyncMock(return_value={"to_version_id": "REQV-2"}),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_requirement_version",
                new=AsyncMock(return_value={"_id": "REQV-2", "requirement_id": "REQ-1"}),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.list_acceptance_criteria_by_ids",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.list_acceptance_criteria_for_version",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.insert_test_version",
                new=AsyncMock(),
            ) as insert_version,
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.update_proposal",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.activate_test_version",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.mark_previous_traces",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.ensure_confirmed_requirement_trace",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.quality.services.proposal_application.index_artifact",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.quality.services.proposal_application.new_id",
                return_value="TCV-2",
            ),
            patch(
                "src.modules.quality.services.proposal_application.now",
                return_value="2026-10-24T00:00:00Z",
            ),
        ):
            with patch(
                "src.modules.design.services.linters.lint_test_case",
                return_value=[],
            ):
                result = await create_test_version_from_proposal(
                    proposal,
                    {"title": "Đăng nhập theo yêu cầu mới"},
                    SimpleNamespace(id="qa-1"),
                )

        inserted = insert_version.await_args.args[0]
        self.assertEqual(result["_id"], "TCV-2")
        self.assertEqual(inserted["parent_version_id"], "TCV-1")
        self.assertEqual(inserted["version"], 2)
        self.assertEqual(inserted["title"], "Đăng nhập theo yêu cầu mới")
        self.assertEqual(base_version, original_base)

    async def test_partial_recovery_never_overwrites_a_newer_test_case_version(self):
        from src.modules.quality.services.proposal_application import recover_partial_proposal

        partial = {
            "_id": "TCV-PARTIAL",
            "project_id": "PRJ-1",
            "test_case_id": "TC-1",
            "parent_version_id": "TCV-1",
        }
        proposal = {
            "project_id": "PRJ-1",
            "target_artifact_id": "TC-1",
            "base_version_id": "TCV-1",
            "partial_version_id": "TCV-PARTIAL",
        }
        with (
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_test_version",
                new=AsyncMock(return_value=partial),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_test_case",
                new=AsyncMock(
                    return_value={"_id": "TC-1", "current_version_id": "TCV-3"}
                ),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.activate_test_version",
                new=AsyncMock(return_value=True),
            ) as activate,
        ):
            with self.assertRaises(HTTPException) as raised:
                await recover_partial_proposal(proposal, SimpleNamespace(id="qa-1"))

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "STALE_PROPOSAL")
        activate.assert_not_awaited()

    async def test_created_test_draft_uses_readback_requirement_evidence(self):
        version = {
            "_id": "REQV-1",
            "plain_text_projection": "Người dùng có thể đăng nhập bằng email.",
            "actors": ["Người dùng"],
        }
        proposal = {
            "project_id": "PRJ-1",
            "evidence": ["REQV-1", "TCV-OLD"],
        }
        patch_data = {
            "title": "Đăng nhập thành công",
            "steps": [{"id": "step-1", "order": 1}],
            "expected_result_doc": {"type": "doc", "content": []},
            "requirement_version_ids": ["REQV-1"],
        }

        with (
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_requirement_version",
                new=AsyncMock(return_value=version),
            ),
            patch(
                "src.modules.quality.services.proposal_application.create_test_case_draft_record",
                new=AsyncMock(return_value={"_id": "TCD-1"}),
            ) as create_draft,
        ):
            result = await create_test_draft_from_proposal(
                proposal, patch_data, SimpleNamespace(id="user-1")
            )

        self.assertEqual(result["_id"], "TCD-1")
        payload = create_draft.await_args.args[1]
        self.assertEqual(payload.evidence_refs, ["REQV-1"])
        self.assertEqual(
            payload.source_evidence,
            [
                {
                    "artifact_type": "requirement_version",
                    "artifact_version_id": "REQV-1",
                    "text": "Người dùng có thể đăng nhập bằng email.\n\nTác nhân:\nNgười dùng",
                }
            ],
        )
        self.assertNotIn("TCV-OLD", payload.evidence_refs)

    async def test_missing_requirement_version_blocks_test_draft_creation(self):
        with (
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_requirement_version",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.modules.quality.services.proposal_application.create_test_case_draft_record",
                new=AsyncMock(),
            ) as create_draft,
        ):
            with self.assertRaises(HTTPException) as raised:
                await create_test_draft_from_proposal(
                    {"project_id": "PRJ-1", "evidence": ["REQV-1"]},
                    {
                        "title": "Đăng nhập thành công",
                        "steps": [{"id": "step-1", "order": 1}],
                        "expected_result_doc": {"type": "doc", "content": []},
                        "requirement_version_ids": ["REQV-1"],
                    },
                    SimpleNamespace(id="user-1"),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "REQUIREMENT_VERSION_NOT_FOUND")
        create_draft.assert_not_awaited()


class AcceptanceCriteriaSnapshotTests(unittest.TestCase):
    def test_cited_subset_is_valid_when_full_source_snapshot_is_unchanged(self):
        snapshot = ["AC-1", "AC-2", "AC-3"]
        cited_criterion_ids = ["AC-2"]

        self.assertTrue(
            acceptance_criteria_snapshot_matches(snapshot, ["AC-1", "AC-2", "AC-3"])
        )
        self.assertNotEqual(set(snapshot), set(cited_criterion_ids))

    def test_added_or_removed_criterion_invalidates_preview(self):
        snapshot = ["AC-1", "AC-2"]

        self.assertFalse(
            acceptance_criteria_snapshot_matches(snapshot, ["AC-1", "AC-2", "AC-3"])
        )
        self.assertFalse(acceptance_criteria_snapshot_matches(snapshot, ["AC-1"]))

    def test_duplicate_snapshot_identifier_is_rejected(self):
        self.assertFalse(
            acceptance_criteria_snapshot_matches(["AC-1", "AC-1"], ["AC-1"])
        )

    def test_legacy_payload_uses_existing_count_based_validation(self):
        self.assertIsNone(acceptance_criteria_snapshot_matches(None, ["AC-1"]))
