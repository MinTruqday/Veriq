import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.main import release_ai_automation_access_lease
from src.modules.operations.api.internal_jobs import revoke_ai_run_access
from src.repositories.ai_automation_access import AIAutomationAccessRepository


class AIAutomationAccessLeaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_acquire_uses_atomic_fence_filter_and_records_request(self):
        collection = SimpleNamespace(
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1, upserted_id=None))
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            admitted = await repository.acquire("run-1", "lease-1")

        self.assertTrue(admitted)
        query = collection.update_one.await_args.args[0]
        update = collection.update_one.await_args.args[1]
        self.assertEqual(query, {"_id": "run-1", "revoked": {"$ne": True}})
        self.assertEqual(update["$addToSet"], {"active_lease_ids": "lease-1"})

    async def test_acquire_fails_closed_when_revocation_wins_upsert_race(self):
        collection = SimpleNamespace(
            update_one=AsyncMock(side_effect=DuplicateKeyError("revoked run already exists")),
            find_one=AsyncMock(return_value={"revoked": True}),
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            admitted = await repository.acquire("run-1", "lease-1")

        self.assertFalse(admitted)

    async def test_first_insert_collision_retries_when_run_is_not_revoked(self):
        collection = SimpleNamespace(
            update_one=AsyncMock(
                side_effect=[
                    DuplicateKeyError("another request created the run lease"),
                    SimpleNamespace(matched_count=1),
                ]
            ),
            find_one=AsyncMock(return_value={"revoked": False}),
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            admitted = await repository.acquire("run-1", "lease-2")

        self.assertTrue(admitted)
        self.assertEqual(collection.update_one.await_count, 2)
        self.assertEqual(
            collection.update_one.await_args_list[1].args[1]["$addToSet"],
            {"active_lease_ids": "lease-2"},
        )

    async def test_revoke_fences_then_waits_until_admitted_request_releases(self):
        collection = SimpleNamespace(
            update_one=AsyncMock(),
            find_one=AsyncMock(
                side_effect=[
                    {"active_lease_ids": ["lease-1"]},
                    {"active_lease_ids": []},
                ]
            ),
        )
        repository = AIAutomationAccessRepository()
        with (
            patch(
                "src.repositories.ai_automation_access.database",
                SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
            ),
            patch("src.repositories.ai_automation_access.asyncio.sleep", new=AsyncMock()),
        ):
            drained = await repository.revoke_and_wait("run-1")

        self.assertTrue(drained)
        self.assertTrue(collection.update_one.await_args.kwargs["upsert"])
        self.assertIs(collection.update_one.await_args.args[1]["$set"]["revoked"], True)
        collection.find_one.assert_awaited()

    async def test_revoke_remains_pending_when_request_does_not_drain(self):
        collection = SimpleNamespace(
            update_one=AsyncMock(),
            find_one=AsyncMock(return_value={"active_lease_ids": ["lease-1"]}),
        )
        repository = AIAutomationAccessRepository()
        with (
            patch(
                "src.repositories.ai_automation_access.database",
                SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
            ),
            patch("src.repositories.ai_automation_access.asyncio.sleep", new=AsyncMock()),
            patch(
                "src.repositories.ai_automation_access.asyncio.get_running_loop",
                return_value=SimpleNamespace(time=Mock(side_effect=[0, 0, 21])),
            ),
        ):
            drained = await repository.revoke_and_wait("run-1", timeout_seconds=20)

        self.assertFalse(drained)

    async def test_allow_source_reopens_only_the_revocation_epoch_it_observed(self):
        collection = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[
                    {"revoked": True, "active_lease_ids": [], "revocation_epoch": 4},
                    {"revoked": True, "active_lease_ids": [], "revocation_epoch": 4},
                    {"revoked": True, "active_lease_ids": [], "revocation_epoch": 5},
                ]
            ),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=0)),
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            reopened = await repository.allow_source("source-1")

        self.assertFalse(reopened)
        self.assertEqual(collection.update_one.await_args.args[0]["revocation_epoch"], 4)

    async def test_allow_source_refuses_to_reopen_while_requests_are_active(self):
        collection = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[
                    {"revoked": True, "active_lease_ids": ["lease-1"], "revocation_epoch": 4},
                    {"revoked": True, "active_lease_ids": ["lease-1"], "revocation_epoch": 4},
                ]
            ),
            update_one=AsyncMock(),
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            reopened = await repository.allow_source("source-1")

        self.assertFalse(reopened)
        collection.update_one.assert_not_awaited()

    async def test_allow_source_is_idempotent_when_active_scope_is_already_open(self):
        collection = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[
                    {"revoked": False, "active_lease_ids": ["lease-1"]},
                    {"revoked": False, "active_lease_ids": ["lease-1"]},
                ]
            ),
            update_one=AsyncMock(),
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            reopened = await repository.allow_source("source-1")

        self.assertTrue(reopened)
        collection.update_one.assert_not_awaited()

    async def test_allow_source_reopens_a_drained_revoked_scope_with_epoch_cas(self):
        collection = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[
                    {"revoked": True, "active_lease_ids": [], "revocation_epoch": 4},
                    {"revoked": True, "active_lease_ids": [], "revocation_epoch": 4},
                ]
            ),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            reopened = await repository.allow_source("source-1")

        self.assertTrue(reopened)
        query = collection.update_one.await_args.args[0]
        self.assertEqual(query["revocation_epoch"], 4)
        self.assertEqual(query["active_lease_ids"], [])
        update = collection.update_one.await_args.args[1]
        self.assertIs(update["$set"]["revoked"], False)

    async def test_heartbeat_extends_only_an_existing_lease(self):
        collection = SimpleNamespace(
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1))
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            renewed = await repository.heartbeat("source-1", "lease-1")

        self.assertTrue(renewed)
        self.assertEqual(
            collection.update_one.await_args.args[0],
            {"_id": "source-1", "active_lease_ids": "lease-1"},
        )
        self.assertIn("lease_expirations.lease-1", collection.update_one.await_args.args[1]["$set"])

    async def test_request_is_cancelled_when_lease_heartbeat_is_lost(self):
        request = SimpleNamespace(
            state=SimpleNamespace(ai_automation_leases=[("scope-1", "lease-1")])
        )
        repository = SimpleNamespace(
            heartbeat=AsyncMock(return_value=False),
            release=AsyncMock(),
        )

        async def wait_for_request_completion(_request):
            await asyncio.Event().wait()

        with (
            patch("src.main.asyncio.sleep", new=AsyncMock(return_value=None)),
            patch(
                "src.repositories.ai_automation_access.ai_automation_access_repository",
                repository,
            ),
        ):
            response = await release_ai_automation_access_lease(
                request, wait_for_request_completion
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"AI_AUTOMATION_ACCESS_LEASE_LOST", response.body)
        repository.heartbeat.assert_awaited_once_with("scope-1", "lease-1")
        repository.release.assert_awaited_once_with("scope-1", "lease-1")

    async def test_expired_lease_is_pruned_with_expiration_compare_and_set(self):
        expired_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        collection = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "active_lease_ids": ["lease-1"],
                    "lease_expirations": {"lease-1": expired_at},
                }
            ),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        )
        repository = AIAutomationAccessRepository()
        with patch(
            "src.repositories.ai_automation_access.database",
            SimpleNamespace(value=SimpleNamespace(ai_automation_access_leases=collection)),
        ):
            await repository._prune_expired_leases("source-1")

        query = collection.update_one.await_args.args[0]
        self.assertEqual(query["active_lease_ids"], "lease-1")
        self.assertEqual(query["lease_expirations.lease-1"], expired_at)
        self.assertEqual(collection.update_one.await_args.args[1]["$pull"], {"active_lease_ids": "lease-1"})

    async def test_internal_revoke_endpoint_reports_drained_fence(self):
        with patch(
            "src.modules.operations.api.internal_jobs.ai_automation_access_repository.revoke_and_wait",
            new=AsyncMock(return_value=True),
        ) as revoke:
            result = await revoke_ai_run_access("run-1")

        self.assertEqual(result["data"]["automation_run_id"], "run-1")
        self.assertIs(result["data"]["access_revoked"], True)
        self.assertIs(result["data"]["drained"], True)
        revoke.assert_awaited_once_with("run:run-1")

    async def test_internal_revoke_endpoint_returns_retryable_pending_on_timeout(self):
        with patch(
            "src.modules.operations.api.internal_jobs.ai_automation_access_repository.revoke_and_wait",
            new=AsyncMock(return_value=False),
        ):
            with self.assertRaises(HTTPException) as raised:
                await revoke_ai_run_access("run-1")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(
            raised.exception.detail["code"], "AI_AUTOMATION_REQUESTS_STILL_ACTIVE"
        )


if __name__ == "__main__":
    unittest.main()
