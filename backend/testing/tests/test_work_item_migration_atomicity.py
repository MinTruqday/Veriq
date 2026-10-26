import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.modules.projects.services import work_items as service


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def with_transaction(self, callback):
        return await callback(self)


class _Client:
    async def start_session(self):
        return _Session()


class _Cursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, _fields):
        return self

    async def to_list(self, length=None):
        return self.documents if length is None else self.documents[:length]


def _setup_migration(monkeypatch, *, tasks=None, prior=None, matched_count=None):
    tasks = tasks or []
    user = SimpleNamespace(id="ba-a", _ai_automation_run_id=None)
    project = {"_id": "project-a", "planning_method": "SCRUM"}
    payload = SimpleNamespace(
        mappings=[SimpleNamespace(legacy_status="OPEN", target_status="TODO")]
    )
    board = {"_id": "board-a", "project_id": "project-a", "revision": 4}
    monkeypatch.setattr(service, "_require_ba", AsyncMock())
    monkeypatch.setattr(service, "_project_planning", AsyncMock(return_value=project))
    monkeypatch.setattr(service, "_board", AsyncMock(return_value=board))
    monkeypatch.setattr(
        service,
        "_workflow",
        AsyncMock(return_value={"statuses": [{"key": "TODO"}]}),
    )

    lock_result = SimpleNamespace(matched_count=1)
    lock = AsyncMock(return_value=lock_result)
    monkeypatch.setattr(
        service.project_repository, "lock_legacy_task_catalog", lock
    )
    database_value = SimpleNamespace(
        project_task_migrations=SimpleNamespace(
            find_one=AsyncMock(return_value=prior),
            insert_one=AsyncMock(),
        ),
        project_tasks=SimpleNamespace(
            find=lambda _query, session=None: _Cursor(tasks),
            bulk_write=AsyncMock(
                return_value=SimpleNamespace(
                    matched_count=len(tasks) if matched_count is None else matched_count
                )
            ),
        ),
        work_items=SimpleNamespace(insert_many=AsyncMock()),
    )
    monkeypatch.setattr(
        service, "database", SimpleNamespace(client=_Client(), value=database_value)
    )
    repository = service.work_item_repository
    monkeypatch.setattr(repository, "find_board", AsyncMock(return_value=board))
    advance = AsyncMock(return_value={"revision": 5})
    monkeypatch.setattr(repository, "advance_board_revision", advance)
    monkeypatch.setattr(repository, "next_rank", AsyncMock(return_value=4096))
    audit = AsyncMock()
    monkeypatch.setattr(service, "audit", audit)
    emit = AsyncMock(return_value=True)
    monkeypatch.setattr("src.clients.ai_automation.emit_work_item_changed", emit)
    return user, payload, database_value, lock, advance, audit, emit


def _legacy_tasks():
    return [
        {"_id": "legacy-a", "project_id": "project-a", "title": "Task A", "status": "OPEN"},
        {"_id": "legacy-b", "project_id": "project-a", "title": "Task B", "status": "OPEN"},
    ]


def test_migration_keeps_history_and_commits_rank_audit_and_ai_events_together(monkeypatch):
    (
        user,
        payload,
        database_value,
        lock,
        advance,
        audit,
        emit,
    ) = _setup_migration(monkeypatch, tasks=_legacy_tasks())

    result = asyncio.run(
        service.WorkItemService.migrate_project_tasks("project-a", payload, user)
    )

    assert result["created"] == 2
    assert result["already_migrated"] is False
    documents = database_value.work_items.insert_many.await_args.args[0]
    assert [value["legacy_project_task_id"] for value in documents] == [
        "legacy-a",
        "legacy-b",
    ]
    assert [value["backlog_rank"] for value in documents] == [4096, 5120]
    session = lock.await_args.args[1]
    assert advance.await_args.kwargs["session"] is session
    assert database_value.project_task_migrations.insert_one.await_args.kwargs[
        "session"
    ] is session
    assert database_value.project_tasks.bulk_write.await_args.kwargs["session"] is session
    assert audit.await_args.kwargs["session"] is session
    assert emit.await_count == 2
    assert all(call.kwargs["session"] is session for call in emit.await_args_list)


def test_migration_retry_returns_existing_record_without_duplicate_artifacts(monkeypatch):
    prior = {
        "_id": "migration-existing",
        "project_id": "project-a",
        "work_item_ids": ["work-item-existing"],
    }
    user, payload, database_value, lock, advance, audit, emit = _setup_migration(
        monkeypatch, tasks=_legacy_tasks(), prior=prior
    )

    result = asyncio.run(
        service.WorkItemService.migrate_project_tasks("project-a", payload, user)
    )

    assert result == {
        "migration": prior,
        "created": 0,
        "already_migrated": True,
    }
    lock.assert_awaited_once()
    advance.assert_not_awaited()
    database_value.work_items.insert_many.assert_not_awaited()
    database_value.project_tasks.bulk_write.assert_not_awaited()
    database_value.project_task_migrations.insert_one.assert_not_awaited()
    audit.assert_not_awaited()
    emit.assert_not_awaited()


def test_migration_rejects_unmapped_legacy_status_before_creating_anything(monkeypatch):
    task = {"_id": "legacy-a", "project_id": "project-a", "title": "Task A", "status": "UNKNOWN"}
    user, payload, database_value, lock, advance, audit, emit = _setup_migration(
        monkeypatch, tasks=[task]
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.WorkItemService.migrate_project_tasks("project-a", payload, user)
        )

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "PROJECT_TASK_MIGRATION_MAPPING_INVALID"
    advance.assert_not_awaited()
    database_value.work_items.insert_many.assert_not_awaited()
    database_value.project_task_migrations.insert_one.assert_not_awaited()
    database_value.project_tasks.bulk_write.assert_not_awaited()
    audit.assert_not_awaited()
    emit.assert_not_awaited()
