from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from pymongo.errors import DuplicateKeyError

from src.repositories.proposal_application import ProposalApplicationRepository


class ProposalTraceIdempotencyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.value = {
            "_id": "TL-RETRY",
            "project_id": "PRJ-1",
            "source_type": "requirement_version",
            "source_id": "REQV-2",
            "target_type": "test_case_version",
            "target_id": "TCV-2",
            "link_type": "verifies",
            "status": "CONFIRMED",
            "confidence": 1,
            "origin": "manual",
            "revision": 1,
            "evidence": ["AC-2"],
            "created_by": "qa-1",
            "created_at": "2026-10-25T00:00:00Z",
            "updated_at": "2026-10-25T00:00:00Z",
        }

    async def test_confirmed_trace_uses_compound_identity_upsert(self):
        collection = SimpleNamespace(
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1))
        )
        repository = ProposalApplicationRepository()
        with patch(
            "src.repositories.proposal_application.database",
            SimpleNamespace(value=SimpleNamespace(trace_links=collection)),
        ):
            await repository.ensure_confirmed_requirement_trace(self.value)

        identity = collection.update_one.await_args.args[0]
        update = collection.update_one.await_args.args[1]
        self.assertEqual(
            identity,
            {
                "project_id": "PRJ-1",
                "source_type": "requirement_version",
                "source_id": "REQV-2",
                "target_type": "test_case_version",
                "target_id": "TCV-2",
                "link_type": "verifies",
            },
        )
        self.assertTrue(collection.update_one.await_args.kwargs["upsert"])
        self.assertEqual(update["$set"]["status"], "CONFIRMED")
        self.assertEqual(update["$set"]["evidence"], ["AC-2"])
        self.assertEqual(update["$setOnInsert"]["_id"], "TL-RETRY")

    async def test_unique_identity_race_retries_as_an_update(self):
        collection = SimpleNamespace(
            update_one=AsyncMock(
                side_effect=[
                    DuplicateKeyError("concurrent trace upsert"),
                    SimpleNamespace(matched_count=1),
                ]
            )
        )
        repository = ProposalApplicationRepository()
        with patch(
            "src.repositories.proposal_application.database",
            SimpleNamespace(value=SimpleNamespace(trace_links=collection)),
        ):
            await repository.ensure_confirmed_requirement_trace(self.value)

        self.assertEqual(collection.update_one.await_count, 2)
        self.assertNotIn("upsert", collection.update_one.await_args.kwargs)
        self.assertEqual(
            collection.update_one.await_args.args[0],
            collection.update_one.await_args_list[0].args[0],
        )

