import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, PropertyMock, patch

from src.repositories.jobs import WorkerJobRepository


class WorkerExecutionLeaseRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_claim_is_atomic_and_records_fencing_token(self):
        collection = type("Collection", (), {})()
        collection.find_one_and_update = AsyncMock(return_value={"_id": "job-1"})
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(minutes=30)

        with patch.object(WorkerJobRepository, "collection", new_callable=PropertyMock) as target:
            target.return_value = collection
            result = await WorkerJobRepository().claim_execution(
                "job-1", "lease-1", now, lease_until
            )

        self.assertEqual(result["_id"], "job-1")
        query, update = collection.find_one_and_update.await_args.args[:2]
        self.assertEqual(query, {"_id": "job-1", "status": "queued"})
        self.assertEqual(update["$set"]["execution_lease_token"], "lease-1")
        self.assertEqual(update["$set"]["execution_lease_until"], lease_until)

    async def test_heartbeat_and_finalize_are_fenced_by_owner_token(self):
        collection = type("Collection", (), {})()
        collection.update_one = AsyncMock(return_value=type("Result", (), {"matched_count": 1})())
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(minutes=30)
        repository = WorkerJobRepository()

        with patch.object(WorkerJobRepository, "collection", new_callable=PropertyMock) as target:
            target.return_value = collection
            await repository.renew_execution_lease("job-2", "lease-owner", now, lease_until)
            await repository.finalize_execution(
                "job-2", "lease-owner", {"status": "completed", "result": {"ok": True}}
            )

        heartbeat_query, heartbeat_update = collection.update_one.await_args_list[0].args[:2]
        final_query, final_update = collection.update_one.await_args_list[1].args[:2]
        self.assertEqual(
            heartbeat_query,
            {"_id": "job-2", "status": "running", "execution_lease_token": "lease-owner"},
        )
        self.assertEqual(heartbeat_update["$set"]["execution_lease_until"], lease_until)
        self.assertEqual(final_query, heartbeat_query)
        self.assertEqual(final_update["$set"]["status"], "completed")
        self.assertIn("execution_lease_token", final_update["$unset"])

    async def test_expired_running_job_requires_reconciliation_not_replay(self):
        collection = type("Collection", (), {})()
        collection.update_many = AsyncMock(return_value=type("Result", (), {"modified_count": 1})())
        now = datetime.now(timezone.utc)

        with patch.object(WorkerJobRepository, "collection", new_callable=PropertyMock) as target:
            target.return_value = collection
            result = await WorkerJobRepository().mark_expired_executions_for_reconciliation(now)

        query, update = collection.update_many.await_args.args
        self.assertEqual(result.modified_count, 1)
        self.assertEqual(query["status"], "running")
        self.assertEqual(query["execution_lease_until"], {"$lte": now})
        self.assertEqual(update["$set"]["status"], "reconciliation_required")
        self.assertIn("execution_lease_token", update["$unset"])


if __name__ == "__main__":
    unittest.main()
