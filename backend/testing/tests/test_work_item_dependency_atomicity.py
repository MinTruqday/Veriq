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


def _setup_dependency(monkeypatch, *, graph, existing=None):
    project = {"_id": "project-a", "planning_method": "KANBAN"}
    source = {"_id": "item-a", "project_id": "project-a"}
    target = {"_id": "item-b", "project_id": "project-a"}
    board = {"_id": "board-a", "revision": 3, "planning_method": "KANBAN"}
    user = SimpleNamespace(id="ba-a")
    payload = SimpleNamespace(target_item_id="item-b", dependency_type="BLOCKS")

    monkeypatch.setattr(service, "_require_ba", AsyncMock())
    monkeypatch.setattr(service, "_project_planning", AsyncMock(return_value=project))
    monkeypatch.setattr(service, "_board", AsyncMock(return_value=board))
    monkeypatch.setattr(service, "database", SimpleNamespace(client=_Client()))
    repository = service.work_item_repository
    monkeypatch.setattr(
        repository,
        "find_item",
        AsyncMock(side_effect=[source, target, source, target]),
    )
    monkeypatch.setattr(repository, "find_dependency", AsyncMock(return_value=existing))
    monkeypatch.setattr(repository, "find_board", AsyncMock(return_value=board))
    advance = AsyncMock(return_value={"revision": 4})
    monkeypatch.setattr(repository, "advance_board_revision", advance)
    list_dependencies = AsyncMock(return_value=graph)
    monkeypatch.setattr(repository, "list_dependencies", list_dependencies)
    create_dependency = AsyncMock()
    monkeypatch.setattr(repository, "create_dependency", create_dependency)
    audit = AsyncMock()
    monkeypatch.setattr(service, "audit", audit)
    emit_dependency = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.clients.ai_automation.emit_work_item_dependency_changed", emit_dependency
    )
    return (
        user,
        payload,
        repository,
        advance,
        list_dependencies,
        create_dependency,
        audit,
        emit_dependency,
    )


def test_dependency_cycle_aborts_edge_and_audit_in_the_same_transaction(monkeypatch):
    graph = [
        {
            "source_item_id": "item-b",
            "target_item_id": "item-a",
            "dependency_type": "BLOCKS",
        }
    ]
    (
        user,
        payload,
        repository,
        advance,
        list_dependencies,
        create_dependency,
        audit,
        emit_dependency,
    ) = _setup_dependency(monkeypatch, graph=graph)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.WorkItemService.create_dependency("project-a", "item-a", payload, user)
        )

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "WORK_ITEM_DEPENDENCY_CYCLE"
    assert advance.await_args.kwargs["session"] is list_dependencies.await_args.kwargs[
        "session"
    ]
    create_dependency.assert_not_awaited()
    audit.assert_not_awaited()
    emit_dependency.assert_not_awaited()


def test_dependency_edge_and_audit_share_transaction_session(monkeypatch):
    (
        user,
        payload,
        repository,
        advance,
        list_dependencies,
        create_dependency,
        audit,
        emit_dependency,
    ) = _setup_dependency(monkeypatch, graph=[])

    result = asyncio.run(
        service.WorkItemService.create_dependency("project-a", "item-a", payload, user)
    )

    assert result["source_item_id"] == "item-a"
    assert result["target_item_id"] == "item-b"
    session = advance.await_args.kwargs["session"]
    assert session is list_dependencies.await_args.kwargs["session"]
    assert session is create_dependency.await_args.kwargs["session"]
    assert session is audit.await_args.kwargs["session"]
    assert emit_dependency.await_args.kwargs["session"] is session
    assert repository.find_dependency.await_args.kwargs["session"] is session


def test_existing_dependency_is_rejected_before_board_revision_write(monkeypatch):
    existing = {"_id": "dep-existing"}
    (
        user,
        payload,
        repository,
        advance,
        list_dependencies,
        create_dependency,
        audit,
        emit_dependency,
    ) = _setup_dependency(monkeypatch, graph=[], existing=existing)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.WorkItemService.create_dependency("project-a", "item-a", payload, user)
        )

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "WORK_ITEM_DEPENDENCY_EXISTS"
    advance.assert_not_awaited()
    list_dependencies.assert_not_awaited()
    create_dependency.assert_not_awaited()
    audit.assert_not_awaited()
    emit_dependency.assert_not_awaited()
