import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.modules.projects.services import work_items as service


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Session(_AsyncContext):
    def start_transaction(self):
        return _AsyncContext()


class _Client:
    async def start_session(self):
        return _Session()


def _setup_rank(monkeypatch, items, *, board_revision_ok=True):
    user = SimpleNamespace(id="ba-a", _ai_automation_run_id=None)
    payload = SimpleNamespace(expected_revision=3, before_item_id="item-b")
    monkeypatch.setattr(service, "_require_ba", AsyncMock())
    monkeypatch.setattr(service, "database", SimpleNamespace(client=_Client()))
    repository = service.work_item_repository
    item = next(value.copy() for value in items if value["_id"] == "item-c")
    board = {"_id": "board-a", "revision": 7}
    monkeypatch.setattr(repository, "find_item", AsyncMock(return_value=item))
    monkeypatch.setattr(repository, "find_board", AsyncMock(return_value=board))
    advance = AsyncMock(return_value=board_revision_ok)
    monkeypatch.setattr(repository, "advance_board_revision", advance)
    list_items = AsyncMock(return_value=items)
    monkeypatch.setattr(repository, "list_items", list_items)

    async def patch_item(project_id, item_id, revision, changes, session=None):
        old = next(value for value in items if value["_id"] == item_id)
        return {**old, **changes, "revision": revision + 1}

    patch_item_mock = AsyncMock(side_effect=patch_item)
    monkeypatch.setattr(repository, "patch_item", patch_item_mock)
    next_rank = AsyncMock(return_value=4096)
    monkeypatch.setattr(repository, "next_rank", next_rank)
    audit = AsyncMock()
    monkeypatch.setattr(service, "audit", audit)
    emit = AsyncMock(return_value=True)
    monkeypatch.setattr("src.clients.ai_automation.emit_work_item_changed", emit)
    return user, payload, repository, advance, list_items, patch_item_mock, next_rank, audit, emit


def _items(ranks):
    return [
        {
            "_id": f"item-{name}",
            "project_id": "project-a",
            "revision": 3,
            "backlog_rank": rank,
        }
        for name, rank in zip(("a", "b", "c"), ranks)
    ]


def test_rank_move_uses_one_transaction_for_board_item_audit_and_ai_event(monkeypatch):
    items = _items([1024, 2048, 3072])
    (
        user,
        payload,
        repository,
        advance,
        list_items,
        patch_item,
        next_rank,
        audit,
        emit,
    ) = _setup_rank(monkeypatch, items)

    result = asyncio.run(
        service.WorkItemService.rank_item("project-a", "item-c", payload, user)
    )

    assert result["backlog_rank"] == 1536
    session = advance.await_args.kwargs["session"]
    assert list_items.await_args.kwargs["session"] is session
    assert list_items.await_args.kwargs["limit"] is None
    assert patch_item.await_args.kwargs["session"] is session
    assert audit.await_args.kwargs["session"] is session
    assert emit.await_args.kwargs["session"] is session
    next_rank.assert_not_awaited()


def test_rank_gap_exhaustion_rebalances_atomically_and_records_each_changed_item(monkeypatch):
    items = _items([100, 101, 102])
    (
        user,
        payload,
        repository,
        advance,
        list_items,
        patch_item,
        next_rank,
        audit,
        emit,
    ) = _setup_rank(monkeypatch, items)

    result = asyncio.run(
        service.WorkItemService.rank_item("project-a", "item-c", payload, user)
    )

    assert result["backlog_rank"] == 2048
    assert [call.args[1] for call in patch_item.await_args_list] == [
        "item-a",
        "item-c",
        "item-b",
    ]
    assert [call.args[3]["backlog_rank"] for call in patch_item.await_args_list] == [
        1024,
        2048,
        3072,
    ]
    assert emit.await_count == 3
    assert audit.await_count == 3
    transaction_session = advance.await_args.kwargs["session"]
    assert all(
        call.kwargs["session"] is transaction_session
        for call in audit.await_args_list
    )
    next_rank.assert_not_awaited()


def test_rank_board_conflict_rolls_back_before_work_item_write(monkeypatch):
    items = _items([1024, 2048, 3072])
    (
        user,
        payload,
        repository,
        advance,
        list_items,
        patch_item,
        next_rank,
        audit,
        emit,
    ) = _setup_rank(monkeypatch, items, board_revision_ok=False)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.WorkItemService.rank_item("project-a", "item-c", payload, user)
        )

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "WORK_ITEM_RANK_CONCURRENT_UPDATE"
    list_items.assert_not_awaited()
    patch_item.assert_not_awaited()
    audit.assert_not_awaited()
    emit.assert_not_awaited()
