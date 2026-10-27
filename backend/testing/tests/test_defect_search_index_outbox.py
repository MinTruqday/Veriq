import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pymongo import ReturnDocument

from src.repositories import defect_search_index as repository_module


def test_enqueue_is_revision_scoped_and_uses_domain_transaction(monkeypatch):
    async def run():
        update_one = AsyncMock()
        monkeypatch.setattr(
            repository_module,
            "database",
            SimpleNamespace(value=SimpleNamespace(defect_search_index_outbox=SimpleNamespace(update_one=update_one))),
        )
        timestamp = datetime(2026, 10, 27, tzinfo=timezone.utc)
        monkeypatch.setattr(repository_module, "now", lambda: timestamp)
        session = object()
        defect = {"_id": "defect-a", "project_id": "project-a", "revision": 7}

        event_id = await repository_module.defect_search_index_repository.enqueue(
            defect, session=session
        )

        assert event_id == "defect-search:project-a:defect-a:7"
        query, update = update_one.await_args.args[:2]
        assert query == {"_id": event_id}
        assert update["$setOnInsert"] == {
            "project_id": "project-a",
            "defect_id": "defect-a",
            "requested_revision": 7,
            "status": "PENDING",
            "attempts": 0,
            "next_attempt_at": timestamp,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        assert update_one.await_args.kwargs == {
            "upsert": True,
            "session": session,
        }

    asyncio.run(run())


def test_claim_uses_expired_lease_recovery_and_compare_token(monkeypatch):
    async def run():
        claimed = {"_id": "event-a", "lease_token": "token-a"}
        find_one_and_update = AsyncMock(return_value=claimed)
        monkeypatch.setattr(
            repository_module,
            "database",
            SimpleNamespace(value=SimpleNamespace(defect_search_index_outbox=SimpleNamespace(find_one_and_update=find_one_and_update))),
        )
        timestamp = datetime(2026, 10, 27, tzinfo=timezone.utc)
        monkeypatch.setattr(repository_module, "now", lambda: timestamp)

        result = await repository_module.defect_search_index_repository.claim_next(45)

        assert result is claimed
        query, update = find_one_and_update.await_args.args[:2]
        assert query["$or"] == [
            {"status": "PENDING", "next_attempt_at": {"$lte": timestamp}},
            {"status": "PROCESSING", "lease_expires_at": {"$lte": timestamp}},
        ]
        assert update["$set"]["status"] == "PROCESSING"
        assert update["$set"]["lease_expires_at"] == timestamp.replace(second=45)
        assert update["$set"]["lease_token"]
        assert find_one_and_update.await_args.kwargs["return_document"] == ReturnDocument.AFTER

    asyncio.run(run())


def test_completion_and_retry_are_fenced_by_the_claim_lease(monkeypatch):
    async def run():
        update_one = AsyncMock(return_value=SimpleNamespace(modified_count=1))
        monkeypatch.setattr(
            repository_module,
            "database",
            SimpleNamespace(value=SimpleNamespace(defect_search_index_outbox=SimpleNamespace(update_one=update_one))),
        )
        timestamp = datetime(2026, 10, 27, tzinfo=timezone.utc)
        monkeypatch.setattr(repository_module, "now", lambda: timestamp)
        entry = {"_id": "event-a", "lease_token": "token-a", "attempts": 1}

        assert await repository_module.defect_search_index_repository.complete(entry, 7)
        complete_query, complete_update = update_one.await_args.args[:2]
        assert complete_query == {
            "_id": "event-a",
            "status": "PROCESSING",
            "lease_token": "token-a",
        }
        assert complete_update["$set"]["status"] == "COMPLETED"
        assert complete_update["$set"]["indexed_revision"] == 7

        assert await repository_module.defect_search_index_repository.defer(
            entry, "INDEX_SYNC_FAILED"
        )
        retry_query, retry_update = update_one.await_args.args[:2]
        assert retry_query == complete_query
        assert retry_update["$set"]["status"] == "PENDING"
        assert retry_update["$set"]["attempts"] == 2
        assert retry_update["$set"]["next_attempt_at"] == timestamp.replace(second=10)
        assert retry_update["$set"]["last_error"] == "INDEX_SYNC_FAILED"

    asyncio.run(run())
