from types import SimpleNamespace
import hashlib
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.quality.services.proposal_application import apply_maintenance_proposal


class ProposalApplyRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_proposal_claims_stable_version_id_before_mutation(self):
        stored = {
            "_id": "MP-1",
            "project_id": "PRJ-1",
            "proposal_type": "UPDATE_TEST_CASE",
            "status": "PENDING",
            "revision": 3,
        }
        claimed = {
            **stored,
            "status": "APPLYING",
            "revision": 4,
            "partial_version_id": "TCV-" + hashlib.sha256(b"MP-1").hexdigest(),
        }
        payload = SimpleNamespace(
            expected_revision=3,
            patch=None,
            review_note="Đã đối chiếu nguồn và phiên bản tác động.",
        )
        user = SimpleNamespace(id="qa-1")

        with (
            patch(
                "src.modules.quality.services.proposal_application.require_automation_publication_authority"
            ),
            patch(
                "src.modules.quality.services.proposal_application.get_project_entity",
                new=AsyncMock(return_value=stored),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.transition_proposal",
                new=AsyncMock(return_value=claimed),
            ) as claim,
            patch(
                "src.modules.quality.services.proposal_application.create_test_version_from_proposal",
                new=AsyncMock(return_value={"_id": claimed["partial_version_id"]}),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.update_proposal",
                new=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.find_proposal",
                new=AsyncMock(return_value={**claimed, "status": "ACCEPTED", "applied_artifact_id": claimed["partial_version_id"]}),
            ),
            patch(
                "src.modules.quality.services.proposal_application.update_proposal_acceptance_rate",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.quality.services.proposal_application.audit",
                new=AsyncMock(),
            ),
        ):
            await apply_maintenance_proposal("MP-1", payload, user, "ACCEPTED")

        changes = claim.await_args.args[4]
        self.assertEqual(changes["partial_version_id"], claimed["partial_version_id"])
        self.assertIsNotNone(changes["apply_lease_expires_at"])

    async def test_live_apply_lease_prevents_a_second_worker_from_taking_over(self):
        proposal = {
            "_id": "MP-2",
            "project_id": "PRJ-1",
            "proposal_type": "UPDATE_TEST_CASE",
            "status": "APPLYING",
            "revision": 8,
        }
        payload = SimpleNamespace(expected_revision=8, patch=None, review_note="Retry sau timeout.")

        with (
            patch(
                "src.modules.quality.services.proposal_application.require_automation_publication_authority"
            ),
            patch(
                "src.modules.quality.services.proposal_application.get_project_entity",
                new=AsyncMock(return_value=proposal),
            ),
            patch(
                "src.modules.quality.services.proposal_application.proposal_application_repository.take_over_expired_proposal_application",
                new=AsyncMock(return_value=None),
            ) as take_over,
            patch(
                "src.modules.quality.services.proposal_application.create_test_version_from_proposal",
                new=AsyncMock(),
            ) as create_version,
        ):
            with self.assertRaises(HTTPException) as raised:
                await apply_maintenance_proposal(
                    "MP-2", payload, SimpleNamespace(id="qa-1"), "ACCEPTED"
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "PROPOSAL_APPLY_IN_PROGRESS")
        take_over.assert_awaited_once()
        create_version.assert_not_awaited()
