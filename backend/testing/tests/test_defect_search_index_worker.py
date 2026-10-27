import asyncio
from unittest.mock import AsyncMock

from src.modules.quality.services import defect_search_index_worker as worker


def test_index_worker_indexes_current_defect_and_completes_claim(monkeypatch):
    async def run():
        entry = {
            "_id": "event-a",
            "project_id": "project-a",
            "defect_id": "defect-a",
            "requested_revision": 2,
            "lease_token": "lease-a",
        }
        defect = {"_id": "defect-a", "project_id": "project-a", "revision": 2}
        monkeypatch.setattr(
            worker.defect_search_index_repository, "claim_next", AsyncMock(return_value=entry)
        )
        monkeypatch.setattr(
            worker.defect_search_index_repository, "complete", AsyncMock(return_value=True)
        )
        monkeypatch.setattr(
            worker.defect_search_index_repository, "defer", AsyncMock(return_value=True)
        )
        monkeypatch.setattr(
            worker.defect_search_index_repository, "enqueue", AsyncMock()
        )
        monkeypatch.setattr(
            worker.defect_repository,
            "find_defect",
            AsyncMock(side_effect=[defect, defect]),
        )
        index = AsyncMock(return_value=True)
        monkeypatch.setattr(worker, "index_defect_for_search", index)

        assert await worker.process_next_defect_search_index() is True
        index.assert_awaited_once_with("project-a", defect)
        worker.defect_search_index_repository.complete.assert_awaited_once_with(
            entry, 2, status="COMPLETED"
        )
        worker.defect_search_index_repository.defer.assert_not_awaited()

    asyncio.run(run())


def test_index_worker_queues_latest_revision_after_concurrent_change(monkeypatch):
    async def run():
        entry = {
            "_id": "event-old",
            "project_id": "project-a",
            "defect_id": "defect-a",
            "requested_revision": 2,
            "lease_token": "lease-old",
        }
        indexed_defect = {"_id": "defect-a", "project_id": "project-a", "revision": 2}
        latest_defect = {"_id": "defect-a", "project_id": "project-a", "revision": 3}
        monkeypatch.setattr(
            worker.defect_search_index_repository, "claim_next", AsyncMock(return_value=entry)
        )
        monkeypatch.setattr(
            worker.defect_search_index_repository, "complete", AsyncMock(return_value=True)
        )
        monkeypatch.setattr(
            worker.defect_search_index_repository, "defer", AsyncMock(return_value=True)
        )
        enqueue = AsyncMock()
        monkeypatch.setattr(worker.defect_search_index_repository, "enqueue", enqueue)
        monkeypatch.setattr(
            worker.defect_repository,
            "find_defect",
            AsyncMock(side_effect=[indexed_defect, latest_defect]),
        )
        monkeypatch.setattr(worker, "index_defect_for_search", AsyncMock(return_value=True))

        assert await worker.process_next_defect_search_index() is True
        enqueue.assert_awaited_once_with(latest_defect)
        worker.defect_search_index_repository.complete.assert_awaited_once_with(
            entry, 2, status="COMPLETED"
        )

    asyncio.run(run())


def test_index_worker_defers_provider_failure_without_losing_entry(monkeypatch):
    async def run():
        entry = {
            "_id": "event-a",
            "project_id": "project-a",
            "defect_id": "defect-a",
            "requested_revision": 2,
            "lease_token": "lease-a",
        }
        defect = {"_id": "defect-a", "project_id": "project-a", "revision": 2}
        monkeypatch.setattr(
            worker.defect_search_index_repository, "claim_next", AsyncMock(return_value=entry)
        )
        monkeypatch.setattr(
            worker.defect_search_index_repository, "complete", AsyncMock(return_value=True)
        )
        defer = AsyncMock(return_value=True)
        monkeypatch.setattr(worker.defect_search_index_repository, "defer", defer)
        monkeypatch.setattr(
            worker.defect_repository, "find_defect", AsyncMock(return_value=defect)
        )
        monkeypatch.setattr(worker, "index_defect_for_search", AsyncMock(return_value=False))

        assert await worker.process_next_defect_search_index() is True
        defer.assert_awaited_once_with(entry, "INDEX_SYNC_FAILED")
        worker.defect_search_index_repository.complete.assert_not_awaited()

    asyncio.run(run())


def test_index_worker_removes_orphaned_artifact(monkeypatch):
    async def run():
        entry = {
            "_id": "event-a",
            "project_id": "project-a",
            "defect_id": "defect-a",
            "requested_revision": 2,
            "lease_token": "lease-a",
        }
        monkeypatch.setattr(
            worker.defect_search_index_repository, "claim_next", AsyncMock(return_value=entry)
        )
        complete = AsyncMock(return_value=True)
        monkeypatch.setattr(worker.defect_search_index_repository, "complete", complete)
        monkeypatch.setattr(
            worker.defect_search_index_repository, "defer", AsyncMock(return_value=True)
        )
        monkeypatch.setattr(
            worker.defect_repository, "find_defect", AsyncMock(return_value=None)
        )
        remove = AsyncMock(return_value=True)
        monkeypatch.setattr(worker, "remove_artifact", remove)

        assert await worker.process_next_defect_search_index() is True
        remove.assert_awaited_once_with("project-a", "defect-a")
        complete.assert_awaited_once_with(entry, None, status="REMOVED")

    asyncio.run(run())
