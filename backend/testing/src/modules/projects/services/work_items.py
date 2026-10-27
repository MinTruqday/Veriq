from fastapi import HTTPException
from pymongo import ReturnDocument, UpdateOne
from pymongo.errors import DuplicateKeyError, OperationFailure

from src.core.common import audit, get_project, get_project_role, get_project_roles, new_id, now, resolve_user_reference
from src.core.database import database
from src.repositories.project import project_repository
from src.repositories.work_item import work_item_repository


def _conflict(existing):
    raise HTTPException(
        status_code=409,
        detail={
            "code": "REVISION_CONFLICT",
            "current_revision": existing.get("revision") if existing else None,
        },
    )


async def _project_planning(project_id, user):
    return await get_project(project_id, user, "project.read")


async def _require_ba(project_id, user):
    await _project_planning(project_id, user)
    if "BA" not in await get_project_roles(project_id, user.id):
        raise HTTPException(status_code=403, detail={"code": "BA_PLANNING_REQUIRED"})


async def _resolve_assignee(project_id, value):
    if value is None or not str(value).strip():
        return None
    user_id = await resolve_user_reference(value)
    if not await project_repository.find_member(project_id, user_id, status="ACTIVE"):
        raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_ASSIGNEE_INVALID"})
    return user_id


async def _validate_parent(project_id, item_type, parent_id):
    if not parent_id:
        if item_type.value == "SUBTASK":
            raise HTTPException(status_code=422, detail={"code": "SUBTASK_PARENT_REQUIRED"})
        return
    parent = await work_item_repository.find_item(project_id, parent_id)
    if not parent:
        raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_PARENT_INVALID"})
    allowed = {"EPIC": {"INITIATIVE"}, "STORY": {"EPIC"}, "TASK": {"EPIC"}, "SUBTASK": {"STORY", "TASK"}}
    if item_type.value in {"INITIATIVE", "BUG"} or parent.get("item_type") not in allowed.get(item_type.value, set()):
        raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_HIERARCHY_INVALID"})


async def _validate_requirements(project_id, requirement_ids):
    if not requirement_ids:
        return
    identifiers = list(dict.fromkeys(requirement_ids))
    found = await database.value.requirements.find({"_id": {"$in": identifiers}, "project_id": project_id}, {"_id": 1}).to_list(len(identifiers))
    if len(found) != len(identifiers):
        raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_REQUIREMENT_INVALID"})


def _validate_planned_dates(planned_start_at, planned_end_at):
    if planned_start_at and planned_end_at:
        try:
            valid_range = planned_end_at > planned_start_at
        except TypeError as exc:
            raise HTTPException(
                status_code=422, detail={"code": "WORK_ITEM_SCHEDULE_TIMEZONE_MISMATCH"}
            ) from exc
        if not valid_range:
            raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_SCHEDULE_INVALID"})


async def _board(project_id, planning_method):
    board = await work_item_repository.find_board(project_id)
    if board:
        return board
    timestamp = now()
    board = {
        "_id": new_id("BRD"),
        "project_id": project_id,
        "planning_method": planning_method,
        "revision": 1,
        "columns": [
            {"status": "BACKLOG", "name": "Danh sách chờ", "position": 0, "wip_limit": None},
            {"status": "TODO", "name": "Cần làm", "position": 1, "wip_limit": None},
            {"status": "IN_PROGRESS", "name": "Đang thực hiện", "position": 2, "wip_limit": None},
            {"status": "BLOCKED", "name": "Bị chặn", "position": 3, "wip_limit": None},
            {"status": "DONE", "name": "Hoàn thành", "position": 4, "wip_limit": None},
            {"status": "CANCELLED", "name": "Đã hủy", "position": 5, "wip_limit": None},
        ],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        return await work_item_repository.create_board(board)
    except Exception:
        existing = await work_item_repository.find_board(project_id)
        if existing:
            return existing
        raise


async def _workflow(project_id):
    workflow = await work_item_repository.find_workflow(project_id)
    if workflow:
        if not workflow.get("statuses"):
            board = await work_item_repository.find_board(project_id)
            workflow = {
                **workflow,
                "statuses": [
                    {
                        "key": column["status"],
                        "name": column.get("name") or column["status"],
                        "counts_as_completed": column["status"] == "DONE",
                    }
                    for column in (board or {}).get("columns", [])
                ],
            }
        return workflow
    statuses = ("BACKLOG", "TODO", "IN_PROGRESS", "BLOCKED", "DONE", "CANCELLED")
    transitions = [
        {"from_status": source, "to_status": target, "allowed_roles": ["BA", "DEVELOPER"]}
        for source in statuses
        for target in statuses
        if source != target
    ]
    board = await work_item_repository.find_board(project_id)
    if not board:
        project = await database.value.projects.find_one(
            {"_id": project_id}, {"planning_method": 1}
        )
        board = await _board(
            project_id, (project or {}).get("planning_method", "SCRUM")
        )
    value = {
        "_id": new_id("WFL"),
        "project_id": project_id,
        "revision": 1,
        "statuses": [
            {
                "key": column["status"],
                "name": column.get("name") or column["status"],
                "counts_as_completed": column["status"] == "DONE",
            }
            for column in board.get("columns", [])
        ],
        "transitions": transitions,
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        return await work_item_repository.create_workflow(value)
    except Exception:
        existing = await work_item_repository.find_workflow(project_id)
        if existing:
            return existing
        raise


async def _validate_dependency_cycle(
    project_id, source_id, target_id, dependency_type="BLOCKS", session=None
):
    if dependency_type != "BLOCKS":
        return
    dependencies = await work_item_repository.list_dependencies(
        project_id, session=session
    )
    links = {}
    for dependency in dependencies:
        if dependency.get("dependency_type") != "BLOCKS":
            continue
        links.setdefault(dependency["target_item_id"], set()).add(dependency["source_item_id"])
    links.setdefault(target_id, set()).add(source_id)
    pending = [source_id]
    visited = set()
    while pending:
        item_id = pending.pop()
        if item_id == target_id:
            raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_DEPENDENCY_CYCLE"})
        if item_id in visited:
            continue
        visited.add(item_id)
        pending.extend(links.get(item_id, set()) - visited)


class WorkItemService:
    @staticmethod
    async def get_item(project_id, item_id, user):
        await _project_planning(project_id, user)
        item = await work_item_repository.find_item(project_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
        return item

    @staticmethod
    async def list_items(project_id, filters, user):
        await _project_planning(project_id, user)
        query = {"project_id": project_id}
        for key in ("item_type", "status", "parent_id", "sprint_id", "release_id", "assignee_id"):
            if filters.get(key):
                query[key] = filters[key]
        if filters.get("backlog_only"):
            query["sprint_id"] = None
        return await work_item_repository.list_items(project_id, query)

    @staticmethod
    async def create_item(project_id, payload, user):
        await _require_ba(project_id, user)
        project = await _project_planning(project_id, user)
        await _validate_parent(project_id, payload.item_type, payload.parent_id)
        await _validate_requirements(project_id, payload.requirement_ids)
        _validate_planned_dates(payload.planned_start_at, payload.planned_end_at)
        timestamp = now()
        item = {
            "_id": new_id("WI"), "project_id": project_id, **payload.model_dump(),
            "assignee_id": await _resolve_assignee(project_id, payload.assignee_id),
            "status": "BACKLOG", "sprint_id": None,
            "revision": 1, "created_by": user.id, "created_at": timestamp, "updated_at": timestamp,
        }
        await _board(project_id, project.get("planning_method", "SCRUM"))
        from src.clients.ai_automation import emit_work_item_changed

        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    board = await work_item_repository.find_board(project_id, session=session)
                    if not board or not isinstance(board.get("revision"), int) or isinstance(board.get("revision"), bool):
                        raise HTTPException(
                            status_code=409, detail={"code": "WORK_ITEM_PLANNING_BOARD_UNAVAILABLE"}
                        )
                    if not await work_item_repository.advance_board_revision(
                        project_id, board["revision"], timestamp, session=session
                    ):
                        raise HTTPException(
                            status_code=409, detail={"code": "WORK_ITEM_RANK_CONCURRENT_UPDATE"}
                        )
                    item["backlog_rank"] = await work_item_repository.next_rank(
                        project_id, session=session
                    )
                    await work_item_repository.create_item(item, session=session)
                    await audit(
                        user.id, "work_item_created", "WorkItem", item["_id"], project_id,
                        session=session,
                    )
                    await emit_work_item_changed(item, user, session=session)
        except OperationFailure as exc:
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "WORK_ITEM_RANK_CONCURRENT_UPDATE"},
                ) from exc
            raise
        return item

    @staticmethod
    async def update_item(project_id, item_id, payload, user):
        await _require_ba(project_id, user)
        item = await work_item_repository.find_item(project_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "WORK_ITEM_NOT_FOUND"})
        if item.get("revision", 1) != payload.expected_revision:
            _conflict(item)
        changes = payload.model_dump(exclude_unset=True)
        changes.pop("expected_revision", None)
        if not changes:
            raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_EMPTY"})
        if "assignee_id" in changes:
            changes["assignee_id"] = await _resolve_assignee(project_id, changes["assignee_id"])
        if "requirement_ids" in changes:
            await _validate_requirements(project_id, changes["requirement_ids"])
        if {"planned_start_at", "planned_end_at"} & set(changes):
            _validate_planned_dates(
                changes.get("planned_start_at", item.get("planned_start_at")),
                changes.get("planned_end_at", item.get("planned_end_at")),
            )
        changes["updated_at"] = now()
        from src.clients.ai_automation import emit_work_item_changed

        async with await database.client.start_session() as session:
            async with session.start_transaction():
                updated = await work_item_repository.patch_item(
                    project_id, item_id, payload.expected_revision, changes, session=session
                )
                if not updated:
                    existing = await work_item_repository.find_item(project_id, item_id)
                    if not existing:
                        raise HTTPException(status_code=404, detail={"code": "WORK_ITEM_NOT_FOUND"})
                    _conflict(existing)
                await audit(
                    user.id, "work_item_updated", "WorkItem", item_id, project_id,
                    {"changed": sorted(changes)}, session=session,
                )
                await emit_work_item_changed(updated, user, session=session)
        return updated

    @staticmethod
    async def transition_item(project_id, item_id, payload, user):
        project = await _project_planning(project_id, user)
        item = await work_item_repository.find_item(project_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "WORK_ITEM_NOT_FOUND"})
        roles = await get_project_roles(project_id, user.id)
        if "BA" not in roles and not ("DEVELOPER" in roles and item.get("assignee_id") == user.id):
            raise HTTPException(status_code=403, detail={"code": "WORK_ITEM_TRANSITION_DENIED"})
        workflow = await _workflow(project_id)
        transition = next(
            (
                value
                for value in workflow["transitions"]
                if value["from_status"] == item["status"] and value["to_status"] == payload.status
            ),
            None,
        )
        if not transition or not roles.intersection(transition["allowed_roles"]):
            raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_WORKFLOW_TRANSITION_INVALID"})
        if payload.status == "IN_PROGRESS" and item.get("sprint_id") is None and project.get("planning_method") == "SCRUM":
            raise HTTPException(status_code=422, detail={"code": "SCRUM_SPRINT_SCOPE_REQUIRED"})
        is_kanban = project.get("planning_method") == "KANBAN"
        if is_kanban:
            await _board(project_id, "KANBAN")
        from src.clients.ai_automation import emit_work_item_changed

        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    current_workflow = await work_item_repository.find_workflow(
                        project_id, session=session
                    )
                    if (
                        not current_workflow
                        or current_workflow.get("revision") != workflow.get("revision")
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "WORK_ITEM_WORKFLOW_CHANGED"},
                        )
                    current_transition = next(
                        (
                            value
                            for value in current_workflow.get("transitions", [])
                            if value["from_status"] == item["status"]
                            and value["to_status"] == payload.status
                        ),
                        None,
                    )
                    if (
                        not current_transition
                        or not roles.intersection(current_transition["allowed_roles"])
                    ):
                        raise HTTPException(
                            status_code=422,
                            detail={"code": "WORK_ITEM_WORKFLOW_TRANSITION_INVALID"},
                        )
                    if not await work_item_repository.guard_workflow_transition(
                        project_id,
                        current_workflow["revision"],
                        session=session,
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "WORK_ITEM_WORKFLOW_CHANGED"},
                        )
                    if is_kanban and item["status"] != payload.status:
                        board = await work_item_repository.find_board(project_id, session=session)
                        if not board or board.get("planning_method") != "KANBAN":
                            raise HTTPException(
                                status_code=409,
                                detail={"code": "KANBAN_BOARD_UNAVAILABLE"},
                            )
                        column = next(
                            (
                                value
                                for value in board.get("columns", [])
                                if value.get("status") == payload.status
                            ),
                            None,
                        )
                        if not column:
                            raise HTTPException(
                                status_code=422,
                                detail={
                                    "code": "KANBAN_STATUS_COLUMN_MISSING",
                                    "status": payload.status,
                                },
                            )
                        wip_limit = column.get("wip_limit")
                        if wip_limit is not None:
                            if (
                                not isinstance(wip_limit, int)
                                or isinstance(wip_limit, bool)
                                or wip_limit < 1
                                or not isinstance(board.get("revision"), int)
                                or isinstance(board.get("revision"), bool)
                            ):
                                raise HTTPException(
                                    status_code=409,
                                    detail={"code": "KANBAN_WIP_CONFIGURATION_INVALID"},
                                )
                            active_count = await work_item_repository.count_items(
                                {"project_id": project_id, "status": payload.status},
                                session=session,
                            )
                            if active_count >= wip_limit:
                                raise HTTPException(
                                    status_code=422,
                                    detail={
                                        "code": "KANBAN_WIP_LIMIT_REACHED",
                                        "status": payload.status,
                                        "limit": wip_limit,
                                        "active_count": active_count,
                                    },
                                )
                            advanced_board = await work_item_repository.advance_board_revision(
                                project_id,
                                board["revision"],
                                now(),
                                session=session,
                            )
                            if not advanced_board:
                                raise HTTPException(
                                    status_code=409,
                                    detail={"code": "KANBAN_WIP_CONCURRENT_UPDATE"},
                                )

                    updated = await work_item_repository.patch_item(
                        project_id,
                        item_id,
                        payload.expected_revision,
                        {"status": payload.status, "updated_at": now()},
                        session=session,
                    )
                    if not updated:
                        _conflict(await work_item_repository.find_item(project_id, item_id))
                    await audit(
                        user.id,
                        "work_item_transitioned",
                        "WorkItem",
                        item_id,
                        project_id,
                        {"status": payload.status, "reason": payload.reason},
                        session=session,
                    )
                    await emit_work_item_changed(updated, user, session=session)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "WORK_ITEM_TRANSITION_CONFLICT"},
            ) from exc
        except OperationFailure as exc:
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "WORK_ITEM_PLANNING_CONCURRENT_UPDATE"},
                ) from exc
            raise
        return updated

    @staticmethod
    async def create_dependency(project_id, item_id, payload, user):
        await _require_ba(project_id, user)
        project = await _project_planning(project_id, user)
        source = await work_item_repository.find_item(project_id, item_id)
        target = await work_item_repository.find_item(project_id, payload.target_item_id)
        if not source or not target or source["_id"] == target["_id"]:
            raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_DEPENDENCY_INVALID"})
        await _board(project_id, project.get("planning_method", "SCRUM"))
        value = {"_id": new_id("WID"), "project_id": project_id, "source_item_id": item_id, "target_item_id": target["_id"], "dependency_type": payload.dependency_type, "created_by": user.id, "created_at": now()}
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    source = await work_item_repository.find_item(
                        project_id, item_id, session=session
                    )
                    target = await work_item_repository.find_item(
                        project_id, payload.target_item_id, session=session
                    )
                    if not source or not target or source["_id"] == target["_id"]:
                        raise HTTPException(
                            status_code=422,
                            detail={"code": "WORK_ITEM_DEPENDENCY_INVALID"},
                        )
                    if await work_item_repository.find_dependency(
                        project_id,
                        item_id,
                        target["_id"],
                        payload.dependency_type,
                        session=session,
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "WORK_ITEM_DEPENDENCY_EXISTS"},
                        )
                    board = await work_item_repository.find_board(
                        project_id, session=session
                    )
                    board_revision = (board or {}).get("revision")
                    if (
                        not board
                        or not isinstance(board_revision, int)
                        or isinstance(board_revision, bool)
                        or board_revision < 1
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "WORK_ITEM_PLANNING_BOARD_UNAVAILABLE"},
                        )
                    if not await work_item_repository.advance_board_revision(
                        project_id, board_revision, now(), session=session
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "WORK_ITEM_DEPENDENCY_CONCURRENT_UPDATE"},
                        )
                    await _validate_dependency_cycle(
                        project_id,
                        item_id,
                        target["_id"],
                        dependency_type=payload.dependency_type,
                        session=session,
                    )
                    await work_item_repository.create_dependency(value, session=session)
                    from src.clients.ai_automation import emit_work_item_dependency_changed

                    await emit_work_item_dependency_changed(
                        value, source, target, user, session=session
                    )
                    await audit(
                        user.id,
                        "work_item_dependency_created",
                        "WorkItemDependency",
                        value["_id"],
                        project_id,
                        session=session,
                    )
        except OperationFailure as exc:
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "WORK_ITEM_DEPENDENCY_CONCURRENT_UPDATE"},
                ) from exc
            raise
        return value

    @staticmethod
    async def board(project_id, user):
        project = await _project_planning(project_id, user)
        board = await _board(project_id, project.get("planning_method", "SCRUM"))
        return {
            "planning_method": project.get("planning_method", "SCRUM"),
            "board": board,
            "workflow": await _workflow(project_id),
            "items": await work_item_repository.list_items(project_id, {"project_id": project_id}),
        }

    @staticmethod
    async def update_board(project_id, payload, user):
        project = await _project_planning(project_id, user)
        await _require_ba(project_id, user)
        statuses = [column.status for column in payload.columns]
        if len(statuses) != len(set(statuses)):
            raise HTTPException(status_code=422, detail={"code": "BOARD_COLUMN_STATUS_DUPLICATE"})
        if project.get("planning_method") != "KANBAN" and any(
            column.wip_limit is not None for column in payload.columns
        ):
            raise HTTPException(
                status_code=422,
                detail={"code": "BOARD_WIP_LIMIT_REQUIRES_KANBAN"},
            )
        workflow = await _workflow(project_id)
        workflow_statuses = {value["key"] for value in workflow.get("statuses", [])}
        if workflow_statuses and any(status not in workflow_statuses for status in statuses):
            raise HTTPException(status_code=422, detail={"code": "BOARD_COLUMN_STATUS_INVALID"})
        positions = [column.position for column in payload.columns]
        if len(positions) != len(set(positions)):
            raise HTTPException(status_code=422, detail={"code": "BOARD_COLUMN_POSITION_DUPLICATE"})
        board = await _board(project_id, project.get("planning_method", "SCRUM"))
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    updated = await work_item_repository.patch_board(
                        project_id,
                        payload.expected_revision,
                        {
                            "columns": [column.model_dump() for column in payload.columns],
                            "updated_at": now(),
                        },
                        session=session,
                    )
                    if not updated:
                        _conflict(
                            await work_item_repository.find_board(
                                project_id, session=session
                            )
                        )
                    await audit(
                        user.id,
                        "planning_board_updated",
                        "PlanningBoard",
                        board["_id"],
                        project_id,
                        session=session,
                    )
        except OperationFailure as exc:
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "WORK_ITEM_PLANNING_CONCURRENT_UPDATE"},
                ) from exc
            raise
        return updated

    @staticmethod
    async def update_workflow(project_id, payload, user):
        await _require_ba(project_id, user)
        transitions = [value.model_dump() for value in payload.transitions]
        statuses = [value.model_dump() for value in payload.statuses]
        status_keys = {value["key"] for value in statuses}
        if len(status_keys) != len(statuses):
            raise HTTPException(status_code=422, detail={"code": "WORKFLOW_STATUS_DUPLICATE"})
        if any(value["from_status"] not in status_keys or value["to_status"] not in status_keys for value in transitions):
            raise HTTPException(status_code=422, detail={"code": "WORKFLOW_TRANSITION_STATUS_INVALID"})
        identities = {(value.from_status, value.to_status) for value in payload.transitions}
        if len(identities) != len(transitions):
            raise HTTPException(status_code=422, detail={"code": "WORKFLOW_TRANSITION_DUPLICATE"})
        workflow = await _workflow(project_id)
        removed_statuses = {
            value["key"] for value in workflow.get("statuses", [])
        } - status_keys
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    if removed_statuses:
                        active_count = await work_item_repository.count_items(
                            {
                                "project_id": project_id,
                                "status": {"$in": sorted(removed_statuses)},
                            },
                            session=session,
                        )
                        if active_count:
                            raise HTTPException(
                                status_code=422,
                                detail={
                                    "code": "WORKFLOW_STATUS_IN_USE",
                                    "statuses": sorted(removed_statuses),
                                    "active_count": active_count,
                                },
                            )
                    updated = await work_item_repository.patch_workflow(
                        project_id,
                        payload.expected_revision,
                        {
                            "statuses": statuses,
                            "transitions": transitions,
                            "updated_at": now(),
                        },
                        session=session,
                    )
                    if not updated:
                        _conflict(
                            await work_item_repository.find_workflow(
                                project_id, session=session
                            )
                        )
                    await audit(
                        user.id,
                        "planning_workflow_updated",
                        "PlanningWorkflow",
                        workflow["_id"],
                        project_id,
                        session=session,
                    )
        except OperationFailure as exc:
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "WORK_ITEM_PLANNING_CONCURRENT_UPDATE"},
                ) from exc
            raise
        return updated

    @staticmethod
    async def rank_item(project_id, item_id, payload, user):
        await _require_ba(project_id, user)
        from src.clients.ai_automation import emit_work_item_changed

        timestamp = now()
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    item = await work_item_repository.find_item(
                        project_id, item_id, session=session
                    )
                    if not item:
                        raise HTTPException(
                            status_code=404, detail={"code": "WORK_ITEM_NOT_FOUND"}
                        )
                    if item["revision"] != payload.expected_revision:
                        _conflict(item)

                    board = await work_item_repository.find_board(
                        project_id, session=session
                    )
                    if (
                        not board
                        or not isinstance(board.get("revision"), int)
                        or isinstance(board.get("revision"), bool)
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "WORK_ITEM_PLANNING_BOARD_UNAVAILABLE"},
                        )
                    if not await work_item_repository.advance_board_revision(
                        project_id, board["revision"], timestamp, session=session
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "WORK_ITEM_RANK_CONCURRENT_UPDATE"},
                        )

                    items = await work_item_repository.list_items(
                        project_id,
                        {"project_id": project_id},
                        limit=None,
                        session=session,
                    )
                    ordered = [value for value in items if value["_id"] != item_id]
                    if payload.before_item_id:
                        target_index = next(
                            (
                                index
                                for index, value in enumerate(ordered)
                                if value["_id"] == payload.before_item_id
                            ),
                            None,
                        )
                        if target_index is None:
                            raise HTTPException(
                                status_code=422,
                                detail={"code": "WORK_ITEM_RANK_TARGET_INVALID"},
                            )
                    try:
                        ranks = [int(value["backlog_rank"]) for value in ordered]
                        needs_rebalance = any(
                            right - left <= 1 for left, right in zip(ranks, ranks[1:])
                        )
                    except (KeyError, TypeError, ValueError):
                        needs_rebalance = True

                    changed_items = []
                    if needs_rebalance:
                        if payload.before_item_id:
                            ordered.insert(target_index, item)
                        else:
                            ordered.append(item)
                        desired = enumerate(ordered, start=1)
                        for index, value in desired:
                            new_rank = index * 1024
                            if value.get("backlog_rank") == new_rank:
                                if value["_id"] == item_id:
                                    updated = value
                                continue
                            ranked = await work_item_repository.patch_item(
                                project_id,
                                value["_id"],
                                value.get("revision", 1),
                                {"backlog_rank": new_rank, "updated_at": timestamp},
                                session=session,
                            )
                            if not ranked:
                                _conflict(
                                    await work_item_repository.find_item(
                                        project_id, value["_id"], session=session
                                    )
                                )
                            changed_items.append(ranked)
                            if value["_id"] == item_id:
                                updated = ranked
                    else:
                        target_index = (
                            target_index
                            if payload.before_item_id
                            else len(ordered)
                        )
                        upper = (
                            int(ordered[target_index]["backlog_rank"])
                            if target_index < len(ordered)
                            else None
                        )
                        lower = (
                            int(ordered[target_index - 1]["backlog_rank"])
                            if target_index > 0
                            else None
                        )
                        rank = (
                            (lower + upper) // 2
                            if lower is not None and upper is not None
                            else upper - 1024
                            if upper is not None
                            else await work_item_repository.next_rank(
                                project_id, session=session
                            )
                        )
                        if rank == item.get("backlog_rank"):
                            updated = item
                        else:
                            updated = await work_item_repository.patch_item(
                                project_id,
                                item_id,
                                payload.expected_revision,
                                {"backlog_rank": rank, "updated_at": timestamp},
                                session=session,
                            )
                            if not updated:
                                _conflict(
                                    await work_item_repository.find_item(
                                        project_id, item_id, session=session
                                    )
                                )
                            changed_items.append(updated)

                    for changed in changed_items:
                        await emit_work_item_changed(changed, user, session=session)
                        if changed["_id"] != item_id:
                            await audit(
                                user.id,
                                "work_item_rank_rebalanced",
                                "WorkItem",
                                changed["_id"],
                                project_id,
                                {"backlog_rank": changed["backlog_rank"]},
                                session=session,
                            )
                    await audit(
                        user.id,
                        "work_item_ranked",
                        "WorkItem",
                        item_id,
                        project_id,
                        {"before_item_id": payload.before_item_id},
                        session=session,
                    )
        except OperationFailure as exc:
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "WORK_ITEM_RANK_CONCURRENT_UPDATE"},
                ) from exc
            raise
        return updated

    @staticmethod
    async def roadmap(project_id, user):
        await _project_planning(project_id, user)
        items = await work_item_repository.list_items(project_id, {"project_id": project_id, "item_type": {"$in": ["INITIATIVE", "EPIC"]}})
        releases = await database.value.releases.find({"project_id": project_id}).sort("planned_start_at", 1).to_list(500)
        dependencies = await work_item_repository.list_dependencies(project_id)
        dependency_item_ids = list(
            {
                item_id
                for dependency in dependencies
                for item_id in (
                    dependency.get("source_item_id"),
                    dependency.get("target_item_id"),
                )
                if item_id
            }
        )
        dependency_items = await database.value.work_items.find(
            {"project_id": project_id, "_id": {"$in": dependency_item_ids}},
            {"_id": 1, "title": 1, "item_type": 1},
        ).to_list(len(dependency_item_ids)) if dependency_item_ids else []
        dependency_items_by_id = {
            item["_id"]: item for item in dependency_items
        }
        enriched_dependencies = [
            {
                **dependency,
                "source_item_title": dependency_items_by_id.get(
                    dependency.get("source_item_id"), {}
                ).get("title"),
                "source_item_type": dependency_items_by_id.get(
                    dependency.get("source_item_id"), {}
                ).get("item_type"),
                "target_item_title": dependency_items_by_id.get(
                    dependency.get("target_item_id"), {}
                ).get("title"),
                "target_item_type": dependency_items_by_id.get(
                    dependency.get("target_item_id"), {}
                ).get("item_type"),
            }
            for dependency in dependencies
        ]
        return {
            "items": items,
            "releases": releases,
            "dependencies": enriched_dependencies,
        }

    @staticmethod
    async def list_sprints(project_id, user):
        project = await _project_planning(project_id, user)
        if project.get("planning_method", "SCRUM") != "SCRUM":
            raise HTTPException(status_code=422, detail={"code": "SCRUM_REQUIRED"})
        return await work_item_repository.list_sprints(project_id)

    @staticmethod
    async def create_sprint(project_id, payload, user):
        project = await _project_planning(project_id, user)
        await _require_ba(project_id, user)
        if project.get("planning_method", "SCRUM") != "SCRUM":
            raise HTTPException(status_code=422, detail={"code": "SCRUM_REQUIRED"})
        if payload.end_at <= payload.start_at:
            raise HTTPException(status_code=422, detail={"code": "SPRINT_DATES_INVALID"})
        value = {"_id": new_id("SPR"), "project_id": project_id, **payload.model_dump(), "status": "PLANNED", "work_item_ids": [], "revision": 1, "created_by": user.id, "created_at": now(), "updated_at": now()}
        await work_item_repository.create_sprint(value)
        await audit(user.id, "sprint_created", "Sprint", value["_id"], project_id)
        return value

    @staticmethod
    async def patch_sprint_scope(project_id, sprint_id, payload, user):
        await _require_ba(project_id, user)
        client = database.client
        if client is None:
            raise RuntimeError("Cơ sở dữ liệu chưa sẵn sàng")
        identifiers = list(dict.fromkeys(payload.work_item_ids))
        timestamp = now()

        async def operation(session):
            sprint = await database.value.sprints.find_one(
                {"_id": sprint_id, "project_id": project_id}, session=session
            )
            if not sprint:
                raise HTTPException(status_code=404, detail={"code": "SPRINT_NOT_FOUND"})
            if sprint.get("status") != "PLANNED":
                raise HTTPException(status_code=409, detail={"code": "SPRINT_SCOPE_LOCKED"})
            if sprint.get("revision", 1) != payload.expected_revision:
                _conflict(sprint)

            items = await database.value.work_items.find(
                {"project_id": project_id, "_id": {"$in": identifiers}}, session=session
            ).to_list(len(identifiers))
            if len(items) != len(identifiers):
                raise HTTPException(status_code=422, detail={"code": "SPRINT_WORK_ITEM_INVALID"})
            current_ids = set(sprint.get("work_item_ids", []))
            for item in items:
                assigned_sprint = item.get("sprint_id")
                if assigned_sprint and assigned_sprint != sprint_id:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "SPRINT_ITEM_ALREADY_ASSIGNED",
                            "work_item_id": item["_id"],
                            "sprint_id": assigned_sprint,
                        },
                    )

            updated = await database.value.sprints.find_one_and_update(
                {
                    "_id": sprint_id,
                    "project_id": project_id,
                    "revision": payload.expected_revision,
                    "status": "PLANNED",
                },
                {
                    "$set": {"work_item_ids": identifiers, "updated_at": timestamp},
                    "$inc": {"revision": 1},
                },
                return_document=ReturnDocument.AFTER,
                session=session,
            )
            if not updated:
                latest = await database.value.sprints.find_one(
                    {"_id": sprint_id, "project_id": project_id}, session=session
                )
                if latest:
                    _conflict(latest)
                raise HTTPException(status_code=404, detail={"code": "SPRINT_NOT_FOUND"})

            for item_id in current_ids - set(identifiers):
                item = await database.value.work_items.find_one(
                    {"_id": item_id, "project_id": project_id, "sprint_id": sprint_id},
                    session=session,
                )
                if item:
                    result = await database.value.work_items.update_one(
                        {
                            "_id": item_id,
                            "project_id": project_id,
                            "sprint_id": sprint_id,
                            "revision": item.get("revision", 1),
                        },
                        {"$set": {"sprint_id": None, "updated_at": timestamp}, "$inc": {"revision": 1}},
                        session=session,
                    )
                    if result.modified_count != 1:
                        latest = await database.value.sprints.find_one(
                            {"_id": sprint_id, "project_id": project_id}, session=session
                        )
                        _conflict(latest or sprint)
            for item in items:
                if item.get("sprint_id") == sprint_id:
                    continue
                result = await database.value.work_items.update_one(
                    {
                        "_id": item["_id"],
                        "project_id": project_id,
                        "revision": item.get("revision", 1),
                        "$or": [{"sprint_id": None}, {"sprint_id": {"$exists": False}}],
                    },
                    {"$set": {"sprint_id": sprint_id, "updated_at": timestamp}, "$inc": {"revision": 1}},
                    session=session,
                )
                if result.modified_count != 1:
                    latest = await database.value.sprints.find_one(
                        {"_id": sprint_id, "project_id": project_id}, session=session
                    )
                    _conflict(latest or sprint)
            return updated

        async with await client.start_session() as session:
            updated = await session.with_transaction(operation)
        await audit(user.id, "sprint_scope_updated", "Sprint", sprint_id, project_id)
        return updated

    @staticmethod
    async def transition_sprint(project_id, sprint_id, payload, user):
        await _require_ba(project_id, user)
        workflow = await _workflow(project_id) if payload.action == "COMPLETE" else None
        client = database.client
        if client is None:
            raise RuntimeError("Cơ sở dữ liệu chưa sẵn sàng")
        target, source = ("ACTIVE", "PLANNED") if payload.action == "START" else ("COMPLETED", "ACTIVE")
        timestamp = now()

        async def operation(session):
            sprint = await database.value.sprints.find_one(
                {"_id": sprint_id, "project_id": project_id}, session=session
            )
            if not sprint:
                raise HTTPException(status_code=404, detail={"code": "SPRINT_NOT_FOUND"})
            if sprint.get("revision", 1) != payload.expected_revision:
                _conflict(sprint)
            if sprint.get("status") != source:
                raise HTTPException(status_code=409, detail={"code": "SPRINT_TRANSITION_INVALID"})

            unfinished = []
            target_sprint = None
            if payload.action == "COMPLETE":
                items = await database.value.work_items.find(
                    {"project_id": project_id, "sprint_id": sprint_id}, session=session
                ).to_list(2000)
                completed_statuses = {
                    value["key"] for value in workflow.get("statuses", []) if value.get("counts_as_completed")
                }
                unfinished = [item for item in items if item.get("status") not in completed_statuses]
                if unfinished and not payload.unfinished_action:
                    raise HTTPException(status_code=422, detail={"code": "SPRINT_UNFINISHED_ACTION_REQUIRED"})
                if unfinished and payload.unfinished_action == "NEXT_SPRINT":
                    target_sprint = await database.value.sprints.find_one(
                        {"_id": payload.target_sprint_id, "project_id": project_id}, session=session
                    )
                    if not target_sprint or target_sprint.get("status") != "PLANNED" or target_sprint["_id"] == sprint_id:
                        raise HTTPException(status_code=422, detail={"code": "SPRINT_TARGET_INVALID"})
                elif unfinished and payload.unfinished_action == "CANCEL":
                    status_keys = {value["key"] for value in workflow.get("statuses", [])}
                    if not payload.target_status or payload.target_status not in status_keys:
                        raise HTTPException(status_code=422, detail={"code": "SPRINT_CANCEL_STATUS_INVALID"})
                elif unfinished and payload.unfinished_action != "BACKLOG":
                    raise HTTPException(status_code=422, detail={"code": "SPRINT_UNFINISHED_ACTION_INVALID"})

            if target_sprint:
                target_ids = list(dict.fromkeys([
                    *target_sprint.get("work_item_ids", []),
                    *[item["_id"] for item in unfinished],
                ]))
                target_updated = await database.value.sprints.find_one_and_update(
                    {
                        "_id": target_sprint["_id"],
                        "project_id": project_id,
                        "revision": target_sprint.get("revision", 1),
                        "status": "PLANNED",
                    },
                    {"$set": {"work_item_ids": target_ids, "updated_at": timestamp}, "$inc": {"revision": 1}},
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )
                if not target_updated:
                    latest = await database.value.sprints.find_one(
                        {"_id": target_sprint["_id"], "project_id": project_id}, session=session
                    )
                    _conflict(latest or target_sprint)

            updated = await database.value.sprints.find_one_and_update(
                {
                    "_id": sprint_id,
                    "project_id": project_id,
                    "revision": payload.expected_revision,
                    "status": source,
                },
                {"$set": {"status": target, "updated_at": timestamp}, "$inc": {"revision": 1}},
                return_document=ReturnDocument.AFTER,
                session=session,
            )
            if not updated:
                latest = await database.value.sprints.find_one(
                    {"_id": sprint_id, "project_id": project_id}, session=session
                )
                _conflict(latest or sprint)

            for item in unfinished:
                changes = {"sprint_id": target_sprint["_id"] if target_sprint else None}
                if payload.unfinished_action == "CANCEL":
                    changes["status"] = payload.target_status
                result = await database.value.work_items.update_one(
                    {
                        "_id": item["_id"],
                        "project_id": project_id,
                        "sprint_id": sprint_id,
                        "revision": item.get("revision", 1),
                    },
                    {"$set": {**changes, "updated_at": timestamp}, "$inc": {"revision": 1}},
                    session=session,
                )
                if result.modified_count != 1:
                    latest = await database.value.work_items.find_one(
                        {"_id": item["_id"], "project_id": project_id}, session=session
                    )
                    _conflict(latest or item)
            return updated

        async with await client.start_session() as session:
            updated = await session.with_transaction(operation)
        await audit(user.id, "sprint_transitioned", "Sprint", sprint_id, project_id, {"action": payload.action, "reason": payload.reason, "unfinished_action": payload.unfinished_action, "target_sprint_id": payload.target_sprint_id, "target_status": payload.target_status})
        return updated

    @staticmethod
    async def preview_project_task_migration(project_id, user):
        await _require_ba(project_id, user)
        prior = await work_item_repository.find_migration(project_id)
        tasks = await project_repository.list_tasks(project_id)
        workflow = await _workflow(project_id)
        return {
            "already_migrated": bool(prior),
            "migration": prior,
            "legacy_statuses": sorted({task.get("status") or "UNKNOWN" for task in tasks}),
            "task_count": len(tasks),
            "workflow_statuses": workflow.get("statuses", []),
        }

    @staticmethod
    async def migrate_project_tasks(project_id, payload, user):
        await _require_ba(project_id, user)
        project = await _project_planning(project_id, user)
        await _board(project_id, project.get("planning_method", "SCRUM"))
        timestamp = now()
        mappings = {value.legacy_status: value.target_status for value in payload.mappings}
        workflow_statuses = {
            value["key"] for value in (await _workflow(project_id)).get("statuses", [])
        }
        client = database.client
        if client is None:
            raise RuntimeError("Cơ sở dữ liệu chưa sẵn sàng")
        from src.clients.ai_automation import emit_work_item_changed

        async def operation(session):
            lock_result = await project_repository.lock_legacy_task_catalog(
                project_id, session
            )
            if lock_result.matched_count != 1:
                raise HTTPException(
                    status_code=404, detail={"code": "PROJECT_NOT_FOUND"}
                )
            duplicate = await database.value.project_task_migrations.find_one(
                {"project_id": project_id}, session=session
            )
            if duplicate:
                return duplicate, True
            tasks = await database.value.project_tasks.find(
                {"project_id": project_id}, session=session
            ).sort([("updated_at", 1), ("_id", 1)]).to_list(length=None)
            legacy_statuses = {task.get("status") or "UNKNOWN" for task in tasks}
            if legacy_statuses - set(mappings) or any(
                status not in workflow_statuses for status in mappings.values()
            ):
                raise HTTPException(
                    status_code=422,
                    detail={"code": "PROJECT_TASK_MIGRATION_MAPPING_INVALID"},
                )

            board = await work_item_repository.find_board(project_id, session=session)
            board_revision = (board or {}).get("revision")
            if (
                not board
                or not isinstance(board_revision, int)
                or isinstance(board_revision, bool)
            ):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "WORK_ITEM_PLANNING_BOARD_UNAVAILABLE"},
                )
            if not await work_item_repository.advance_board_revision(
                project_id, board_revision, timestamp, session=session
            ):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "PROJECT_TASK_MIGRATION_CONCURRENT_UPDATE"},
                )

            first_rank = await work_item_repository.next_rank(
                project_id, session=session
            )
            documents = []
            for index, task in enumerate(tasks):
                documents.append(
                    {
                        "_id": new_id("WI"),
                        "project_id": project_id,
                        "item_type": "TASK",
                        "title": task["title"],
                        "description": task.get("description", ""),
                        "parent_id": None,
                        "priority": "MEDIUM",
                        "estimate": task.get("weight"),
                        "assignee_id": task.get("assignee_id"),
                        "due_at": task.get("due_at"),
                        "requirement_ids": [],
                        "release_id": None,
                        "status": mappings[task.get("status") or "UNKNOWN"],
                        "sprint_id": None,
                        "backlog_rank": first_rank + index * 1024,
                        "legacy_project_task_id": task["_id"],
                        "revision": 1,
                        "created_by": task.get("created_by") or user.id,
                        "created_at": task.get("created_at") or timestamp,
                        "updated_at": timestamp,
                    }
                )
            if documents:
                await database.value.work_items.insert_many(documents, session=session)
            saved = {
                "_id": new_id("PTM"),
                "project_id": project_id,
                "created_by": user.id,
                "created_at": timestamp,
                "legacy_task_ids": [task["_id"] for task in tasks],
                "work_item_ids": [document["_id"] for document in documents],
            }
            await database.value.project_task_migrations.insert_one(saved, session=session)
            if tasks:
                result = await database.value.project_tasks.bulk_write(
                    [
                        UpdateOne(
                            {"_id": task["_id"], "project_id": project_id},
                            {"$set": {"migration_id": saved["_id"], "migrated_at": timestamp}},
                        )
                        for task in tasks
                    ],
                    session=session,
                )
                if result.matched_count != len(tasks):
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "PROJECT_TASK_MIGRATION_SOURCE_CHANGED"},
                    )
            for document in documents:
                await emit_work_item_changed(document, user, session=session)
            await audit(
                user.id,
                "project_tasks_migrated",
                "ProjectTaskMigration",
                saved["_id"],
                project_id,
                {"created": len(saved["work_item_ids"]), "mappings": mappings},
                session=session,
            )
            return saved, False

        async with await client.start_session() as session:
            saved, already_migrated = await session.with_transaction(operation)
        return {
            "migration": saved,
            "created": 0 if already_migrated else len(saved["work_item_ids"]),
            "already_migrated": already_migrated,
        }
