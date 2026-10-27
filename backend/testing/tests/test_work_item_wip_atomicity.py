import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

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
    workflow = {
        "revision": 3,
        "transitions": [
            {"from_status": "TODO", "to_status": "IN_PROGRESS", "allowed_roles": ["DEVELOPER"]}
        ],
    }
    monkeypatch.setattr(service, "_workflow", AsyncMock(return_value=workflow))
    monkeypatch.setattr(service, "_board", AsyncMock(return_value=board))
    monkeypatch.setattr(service, "get_project_roles", AsyncMock(return_value={"DEVELOPER"}))
    monkeypatch.setattr(service, "database", SimpleNamespace(client=_Client()))

    repository = service.work_item_repository
    monkeypatch.setattr(repository, "find_item", AsyncMock(return_value=item))
    monkeypatch.setattr(repository, "find_workflow", AsyncMock(return_value=workflow))
    monkeypatch.setattr(repository, "guard_workflow_transition", AsyncMock(return_value=True))
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


def test_workflow_change_conflict_blocks_transition_before_item_write(monkeypatch):
    payload, user, repository, patch_item = _setup_transition(
        monkeypatch, active_count=0, board_advance={"revision": 7}
    )
    repository.find_workflow = AsyncMock(
        return_value={
            "revision": 4,
            "transitions": [
                {
                    "from_status": "TODO",
                    "to_status": "IN_PROGRESS",
                    "allowed_roles": ["DEVELOPER"],
                }
            ],
        }
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.WorkItemService.transition_item("project-a", "item-a", payload, user))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "WORK_ITEM_WORKFLOW_CHANGED"
    repository.guard_workflow_transition.assert_not_awaited()
    patch_item.assert_not_awaited()


def test_workflow_guard_conflict_blocks_transition_before_item_write(monkeypatch):
    payload, user, repository, patch_item = _setup_transition(
        monkeypatch, active_count=0, board_advance={"revision": 7}
    )
    repository.guard_workflow_transition = AsyncMock(return_value=False)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.WorkItemService.transition_item("project-a", "item-a", payload, user))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "WORK_ITEM_WORKFLOW_CHANGED"
    repository.guard_workflow_transition.assert_awaited_once()
    repository.count_items.assert_not_awaited()
    patch_item.assert_not_awaited()


def test_duplicate_key_during_transition_is_not_reported_as_dependency_duplicate(monkeypatch):
    payload, user, repository, patch_item = _setup_transition(
        monkeypatch, active_count=0, board_advance={"revision": 7}
    )
    patch_item.side_effect = DuplicateKeyError("duplicate transition record")

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.WorkItemService.transition_item("project-a", "item-a", payload, user))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "WORK_ITEM_TRANSITION_CONFLICT"
    patch_item.assert_awaited_once()


def test_kanban_wip_capacity_check_and_item_write_share_transaction(monkeypatch):
    payload, user, repository, patch_item = _setup_transition(
        monkeypatch, active_count=1, board_advance={"revision": 7}
    )

    result = asyncio.run(
        service.WorkItemService.transition_item("project-a", "item-a", payload, user)
    )

    assert result["status"] == "IN_PROGRESS"
    assert repository.guard_workflow_transition.await_args.kwargs["session"] is not None
    assert repository.count_items.await_args.kwargs["session"] is not None
    assert repository.guard_workflow_transition.await_args.kwargs["session"] is patch_item.await_args.kwargs["session"]
    assert repository.advance_board_revision.await_args.kwargs["session"] is patch_item.await_args.kwargs["session"]
    assert patch_item.await_args.kwargs["session"] is not None


def test_scrum_board_rejects_kanban_wip_configuration(monkeypatch):
    monkeypatch.setattr(
        service,
        "_project_planning",
        AsyncMock(return_value={"_id": "project-a", "planning_method": "SCRUM"}),
    )
    monkeypatch.setattr(service, "_require_ba", AsyncMock())
    patch_board = AsyncMock()
    monkeypatch.setattr(service.work_item_repository, "patch_board", patch_board)
    payload = SimpleNamespace(
        columns=[SimpleNamespace(status="IN_PROGRESS", position=0, wip_limit=2)],
        expected_revision=1,
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.WorkItemService.update_board(
                "project-a", payload, SimpleNamespace(id="ba-a")
            )
        )

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "BOARD_WIP_LIMIT_REQUIRES_KANBAN"
    patch_board.assert_not_awaited()


def test_board_configuration_and_audit_share_one_transaction(monkeypatch):
    board = {"_id": "board-a", "revision": 1}
    updated = {**board, "revision": 2}
    monkeypatch.setattr(
        service,
        "_project_planning",
        AsyncMock(return_value={"_id": "project-a", "planning_method": "KANBAN"}),
    )
    monkeypatch.setattr(service, "_require_ba", AsyncMock())
    monkeypatch.setattr(
        service,
        "_workflow",
        AsyncMock(return_value={"statuses": [{"key": "TODO"}]}),
    )
    monkeypatch.setattr(service, "_board", AsyncMock(return_value=board))
    monkeypatch.setattr(service, "database", SimpleNamespace(client=_Client()))
    patch_board = AsyncMock(return_value=updated)
    audit = AsyncMock()
    monkeypatch.setattr(service.work_item_repository, "patch_board", patch_board)
    monkeypatch.setattr(service, "audit", audit)
    column = SimpleNamespace(
        status="TODO",
        position=0,
        wip_limit=2,
        model_dump=lambda: {"status": "TODO", "position": 0, "wip_limit": 2},
    )
    payload = SimpleNamespace(columns=[column], expected_revision=1)

    result = asyncio.run(
        service.WorkItemService.update_board(
            "project-a", payload, SimpleNamespace(id="ba-a")
        )
    )

    assert result == updated
    assert patch_board.await_args.kwargs["session"] is audit.await_args.kwargs["session"]


def test_workflow_configuration_and_audit_share_one_transaction(monkeypatch):
    workflow = {"_id": "workflow-a", "revision": 1}
    updated = {**workflow, "revision": 2}
    monkeypatch.setattr(service, "_require_ba", AsyncMock())
    monkeypatch.setattr(service, "_workflow", AsyncMock(return_value=workflow))
    monkeypatch.setattr(service, "database", SimpleNamespace(client=_Client()))
    patch_workflow = AsyncMock(return_value=updated)
    audit = AsyncMock()
    monkeypatch.setattr(service.work_item_repository, "patch_workflow", patch_workflow)
    monkeypatch.setattr(service, "audit", audit)
    status = SimpleNamespace(
        key="TODO",
        model_dump=lambda: {"key": "TODO", "name": "Cần làm", "counts_as_completed": False},
    )
    payload = SimpleNamespace(
        statuses=[status],
        transitions=[],
        expected_revision=1,
    )

    result = asyncio.run(
        service.WorkItemService.update_workflow(
            "project-a", payload, SimpleNamespace(id="ba-a")
        )
    )

    assert result == updated
    assert patch_workflow.await_args.kwargs["session"] is audit.await_args.kwargs["session"]


def test_workflow_cannot_remove_a_status_used_by_work_items(monkeypatch):
    monkeypatch.setattr(service, "_require_ba", AsyncMock())
    monkeypatch.setattr(
        service,
        "_workflow",
        AsyncMock(
            return_value={
                "_id": "workflow-a",
                "statuses": [{"key": "TODO"}, {"key": "IN_PROGRESS"}],
            }
        ),
    )
    monkeypatch.setattr(service, "database", SimpleNamespace(client=_Client()))
    count_items = AsyncMock(return_value=1)
    patch_workflow = AsyncMock()
    monkeypatch.setattr(service.work_item_repository, "count_items", count_items)
    monkeypatch.setattr(service.work_item_repository, "patch_workflow", patch_workflow)
    status = SimpleNamespace(
        key="TODO",
        model_dump=lambda: {"key": "TODO", "name": "Cần làm", "counts_as_completed": False},
    )
    payload = SimpleNamespace(
        statuses=[status],
        transitions=[],
        expected_revision=1,
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.WorkItemService.update_workflow(
                "project-a", payload, SimpleNamespace(id="ba-a")
            )
        )

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "WORKFLOW_STATUS_IN_USE"
    assert raised.value.detail["statuses"] == ["IN_PROGRESS"]
    assert count_items.await_args.kwargs["session"] is not None
    patch_workflow.assert_not_awaited()
