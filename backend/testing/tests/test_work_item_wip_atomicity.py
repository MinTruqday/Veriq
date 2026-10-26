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


def _setup_transition(monkeypatch, *, active_count, board_advance):
    project = {"_id": "project-a", "planning_method": "KANBAN"}
    item = {
        "_id": "item-a",
        "project_id": "project-a",
        "revision": 1,
        "status": "TODO",
        "assignee_id": "developer-a",
    }
    board = {
        "_id": "board-a",
        "project_id": "project-a",
        "planning_method": "KANBAN",
        "revision": 6,
        "columns": [{"status": "IN_PROGRESS", "wip_limit": 2}],
    }
    updated = {**item, "status": "IN_PROGRESS", "revision": 2}
    monkeypatch.setattr(service, "_project_planning", AsyncMock(return_value=project))
    monkeypatch.setattr(service, "_workflow", AsyncMock(return_value={
        "transitions": [
            {"from_status": "TODO", "to_status": "IN_PROGRESS", "allowed_roles": ["DEVELOPER"]}
        ]
    }))
    monkeypatch.setattr(service, "_board", AsyncMock(return_value=board))
    monkeypatch.setattr(service, "get_project_roles", AsyncMock(return_value={"DEVELOPER"}))
    monkeypatch.setattr(service, "database", SimpleNamespace(client=_Client()))

    repository = service.work_item_repository
    monkeypatch.setattr(repository, "find_item", AsyncMock(return_value=item))
    monkeypatch.setattr(repository, "find_board", AsyncMock(return_value=board))
    monkeypatch.setattr(repository, "count_items", AsyncMock(return_value=active_count))
    monkeypatch.setattr(repository, "advance_board_revision", AsyncMock(return_value=board_advance))
    patch_item = AsyncMock(return_value=updated)
    monkeypatch.setattr(repository, "patch_item", patch_item)
    monkeypatch.setattr(service, "audit", AsyncMock())
    monkeypatch.setattr(
        "src.clients.ai_automation.emit_work_item_changed", AsyncMock()
    )
    payload = SimpleNamespace(status="IN_PROGRESS", expected_revision=1, reason="Start")
    user = SimpleNamespace(id="developer-a")
    return payload, user, repository, patch_item


def test_kanban_wip_limit_rejects_entry_before_mutation(monkeypatch):
    payload, user, repository, patch_item = _setup_transition(
        monkeypatch, active_count=2, board_advance={"revision": 7}
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.WorkItemService.transition_item("project-a", "item-a", payload, user))

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "KANBAN_WIP_LIMIT_REACHED"
    repository.advance_board_revision.assert_not_awaited()
    patch_item.assert_not_awaited()


def test_kanban_wip_revision_conflict_rejects_concurrent_entry(monkeypatch):
    payload, user, repository, patch_item = _setup_transition(
        monkeypatch, active_count=1, board_advance=None
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.WorkItemService.transition_item("project-a", "item-a", payload, user))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "KANBAN_WIP_CONCURRENT_UPDATE"
    assert repository.advance_board_revision.await_count == 1
    patch_item.assert_not_awaited()


def test_kanban_transition_fails_closed_when_board_disappears(monkeypatch):
    payload, user, repository, patch_item = _setup_transition(
        monkeypatch, active_count=0, board_advance={"revision": 7}
    )
    repository.find_board = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.WorkItemService.transition_item("project-a", "item-a", payload, user))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "KANBAN_BOARD_UNAVAILABLE"
    repository.count_items.assert_not_awaited()
    patch_item.assert_not_awaited()


def test_kanban_wip_capacity_check_and_item_write_share_transaction(monkeypatch):
    payload, user, repository, patch_item = _setup_transition(
        monkeypatch, active_count=1, board_advance={"revision": 7}
    )

    result = asyncio.run(
        service.WorkItemService.transition_item("project-a", "item-a", payload, user)
    )

    assert result["status"] == "IN_PROGRESS"
    assert repository.count_items.await_args.kwargs["session"] is not None
    assert repository.advance_board_revision.await_args.kwargs["session"] is patch_item.await_args.kwargs["session"]
    assert patch_item.await_args.kwargs["session"] is not None
