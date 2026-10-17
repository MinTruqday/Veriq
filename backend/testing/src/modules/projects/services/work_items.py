from fastapi import HTTPException
from pymongo import UpdateOne

from src.core.common import audit, get_project, get_project_role, new_id, now, resolve_user_reference
from src.core.database import database
from src.repositories.project import project_repository
from src.repositories.work_item import work_item_repository


def _conflict(existing):
    raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "current_revision": existing.get("revision")})


async def _project_planning(project_id, user):
    return await get_project(project_id, user, "project.read")


async def _require_ba(project_id, user):
    await _project_planning(project_id, user)
    if await get_project_role(project_id, user.id) != "BA":
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
        board = await _board(project_id, "SCRUM")
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


async def _validate_dependency_cycle(project_id, source_id, target_id):
    dependencies = await work_item_repository.list_dependencies(project_id)
    links = {}
    for dependency in dependencies:
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
        await _validate_parent(project_id, payload.item_type, payload.parent_id)
        await _validate_requirements(project_id, payload.requirement_ids)
        timestamp = now()
        item = {
            "_id": new_id("WI"), "project_id": project_id, **payload.model_dump(),
            "assignee_id": await _resolve_assignee(project_id, payload.assignee_id),
            "status": "BACKLOG", "sprint_id": None,
            "backlog_rank": await work_item_repository.next_rank(project_id),
            "revision": 1, "created_by": user.id, "created_at": timestamp, "updated_at": timestamp,
        }
        await work_item_repository.create_item(item)
        await audit(user.id, "work_item_created", "WorkItem", item["_id"], project_id)
        return item

    @staticmethod
    async def update_item(project_id, item_id, payload, user):
        await _require_ba(project_id, user)
        changes = payload.model_dump(exclude_unset=True)
        changes.pop("expected_revision", None)
        if not changes:
            raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_EMPTY"})
        if "assignee_id" in changes:
            changes["assignee_id"] = await _resolve_assignee(project_id, changes["assignee_id"])
        if "requirement_ids" in changes:
            await _validate_requirements(project_id, changes["requirement_ids"])
        changes["updated_at"] = now()
        updated = await work_item_repository.patch_item(project_id, item_id, payload.expected_revision, changes)
        if not updated:
            existing = await work_item_repository.find_item(project_id, item_id)
            if not existing:
                raise HTTPException(status_code=404, detail={"code": "WORK_ITEM_NOT_FOUND"})
            _conflict(existing)
        await audit(user.id, "work_item_updated", "WorkItem", item_id, project_id, {"changed": sorted(changes)})
        return updated

    @staticmethod
    async def transition_item(project_id, item_id, payload, user):
        project = await _project_planning(project_id, user)
        item = await work_item_repository.find_item(project_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "WORK_ITEM_NOT_FOUND"})
        role = await get_project_role(project_id, user.id)
        if role != "BA" and not (role == "DEVELOPER" and item.get("assignee_id") == user.id):
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
        if not transition or role not in transition["allowed_roles"]:
            raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_WORKFLOW_TRANSITION_INVALID"})
        if payload.status == "IN_PROGRESS" and item.get("sprint_id") is None and project.get("planning_method") == "SCRUM":
            raise HTTPException(status_code=422, detail={"code": "SCRUM_SPRINT_SCOPE_REQUIRED"})
        if project.get("planning_method") == "KANBAN":
            board = await _board(project_id, project.get("planning_method", "KANBAN"))
            column = next((value for value in board["columns"] if value["status"] == payload.status), None)
            if column and column.get("wip_limit"):
                active_count = len(
                    await work_item_repository.list_items(
                        project_id,
                        {"project_id": project_id, "status": payload.status},
                    )
                )
                if item["status"] != payload.status and active_count >= column["wip_limit"]:
                    raise HTTPException(status_code=422, detail={"code": "KANBAN_WIP_LIMIT_REACHED"})
        updated = await work_item_repository.patch_item(project_id, item_id, payload.expected_revision, {"status": payload.status, "updated_at": now()})
        if not updated:
            _conflict(await work_item_repository.find_item(project_id, item_id))
        await audit(user.id, "work_item_transitioned", "WorkItem", item_id, project_id, {"status": payload.status, "reason": payload.reason})
        return updated

    @staticmethod
    async def create_dependency(project_id, item_id, payload, user):
        await _require_ba(project_id, user)
        source = await work_item_repository.find_item(project_id, item_id)
        target = await work_item_repository.find_item(project_id, payload.target_item_id)
        if not source or not target or source["_id"] == target["_id"]:
            raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_DEPENDENCY_INVALID"})
        if await work_item_repository.find_dependency(project_id, item_id, target["_id"], payload.dependency_type):
            raise HTTPException(status_code=409, detail={"code": "WORK_ITEM_DEPENDENCY_EXISTS"})
        await _validate_dependency_cycle(project_id, item_id, target["_id"])
        value = {"_id": new_id("WID"), "project_id": project_id, "source_item_id": item_id, "target_item_id": target["_id"], "dependency_type": payload.dependency_type, "created_by": user.id, "created_at": now()}
        await work_item_repository.create_dependency(value)
        await audit(user.id, "work_item_dependency_created", "WorkItemDependency", value["_id"], project_id)
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
        workflow = await _workflow(project_id)
        workflow_statuses = {value["key"] for value in workflow.get("statuses", [])}
        if workflow_statuses and any(status not in workflow_statuses for status in statuses):
            raise HTTPException(status_code=422, detail={"code": "BOARD_COLUMN_STATUS_INVALID"})
        positions = [column.position for column in payload.columns]
        if len(positions) != len(set(positions)):
            raise HTTPException(status_code=422, detail={"code": "BOARD_COLUMN_POSITION_DUPLICATE"})
        board = await _board(project_id, project.get("planning_method", "SCRUM"))
        updated = await work_item_repository.patch_board(
            project_id,
            payload.expected_revision,
            {"columns": [column.model_dump() for column in payload.columns], "updated_at": now()},
        )
        if not updated:
            _conflict(await work_item_repository.find_board(project_id))
        await audit(user.id, "planning_board_updated", "PlanningBoard", board["_id"], project_id)
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
        updated = await work_item_repository.patch_workflow(
            project_id,
            payload.expected_revision,
            {"statuses": statuses, "transitions": transitions, "updated_at": now()},
        )
        if not updated:
            _conflict(await work_item_repository.find_workflow(project_id))
        await audit(user.id, "planning_workflow_updated", "PlanningWorkflow", workflow["_id"], project_id)
        return updated

    @staticmethod
    async def rank_item(project_id, item_id, payload, user):
        await _require_ba(project_id, user)
        item = await work_item_repository.find_item(project_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "WORK_ITEM_NOT_FOUND"})
        if item["revision"] != payload.expected_revision:
            _conflict(item)
        before = None
        if payload.before_item_id:
            before = await work_item_repository.find_item(project_id, payload.before_item_id)
            if not before or before["_id"] == item_id:
                raise HTTPException(status_code=422, detail={"code": "WORK_ITEM_RANK_TARGET_INVALID"})
        if before:
            items = await work_item_repository.list_items(project_id, {"project_id": project_id})
            prior = next((value for value in reversed(items[: items.index(before)]) if value["_id"] != item_id), None)
            rank = (int(prior["backlog_rank"]) + int(before["backlog_rank"])) // 2 if prior else int(before["backlog_rank"]) - 1024
        else:
            rank = await work_item_repository.next_rank(project_id)
        updated = await work_item_repository.patch_item(project_id, item_id, item["revision"], {"backlog_rank": rank, "updated_at": now()})
        if not updated:
            _conflict(await work_item_repository.find_item(project_id, item_id))
        await audit(user.id, "work_item_ranked", "WorkItem", item_id, project_id, {"before_item_id": payload.before_item_id})
        return updated

    @staticmethod
    async def roadmap(project_id, user):
        await _project_planning(project_id, user)
        items = await work_item_repository.list_items(project_id, {"project_id": project_id, "item_type": {"$in": ["INITIATIVE", "EPIC"]}})
        releases = await database.value.releases.find({"project_id": project_id}).sort("planned_start_at", 1).to_list(500)
        return {"items": items, "releases": releases, "dependencies": await work_item_repository.list_dependencies(project_id)}

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
        sprint = await work_item_repository.find_sprint(project_id, sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail={"code": "SPRINT_NOT_FOUND"})
        if sprint.get("status") != "PLANNED":
            raise HTTPException(status_code=409, detail={"code": "SPRINT_SCOPE_LOCKED"})
        identifiers = list(dict.fromkeys(payload.work_item_ids))
        items = await work_item_repository.list_items(project_id, {"project_id": project_id, "_id": {"$in": identifiers}})
        if len(items) != len(identifiers):
            raise HTTPException(status_code=422, detail={"code": "SPRINT_WORK_ITEM_INVALID"})
        updated = await work_item_repository.patch_sprint(project_id, sprint_id, payload.expected_revision, {"work_item_ids": identifiers, "updated_at": now()})
        if not updated:
            _conflict(await work_item_repository.find_sprint(project_id, sprint_id))
        for item in items:
            await work_item_repository.patch_item(project_id, item["_id"], item["revision"], {"sprint_id": sprint_id, "updated_at": now()})
        await audit(user.id, "sprint_scope_updated", "Sprint", sprint_id, project_id)
        return updated

    @staticmethod
    async def transition_sprint(project_id, sprint_id, payload, user):
        await _require_ba(project_id, user)
        sprint = await work_item_repository.find_sprint(project_id, sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail={"code": "SPRINT_NOT_FOUND"})
        target, source = ("ACTIVE", "PLANNED") if payload.action == "START" else ("COMPLETED", "ACTIVE")
        if sprint.get("status") != source:
            raise HTTPException(status_code=409, detail={"code": "SPRINT_TRANSITION_INVALID"})
        if payload.action == "COMPLETE":
            items = await work_item_repository.list_items(
                project_id, {"project_id": project_id, "sprint_id": sprint_id}
            )
            workflow = await _workflow(project_id)
            completed_statuses = {
                value["key"] for value in workflow.get("statuses", []) if value.get("counts_as_completed")
            }
            unfinished = [item for item in items if item.get("status") not in completed_statuses]
            if unfinished and not payload.unfinished_action:
                raise HTTPException(status_code=422, detail={"code": "SPRINT_UNFINISHED_ACTION_REQUIRED"})
            changes_by_item = {}
            if unfinished and payload.unfinished_action == "NEXT_SPRINT":
                target_sprint = await work_item_repository.find_sprint(project_id, payload.target_sprint_id or "")
                if not target_sprint or target_sprint.get("status") != "PLANNED" or target_sprint["_id"] == sprint_id:
                    raise HTTPException(status_code=422, detail={"code": "SPRINT_TARGET_INVALID"})
                target_ids = list(dict.fromkeys([*target_sprint.get("work_item_ids", []), *[item["_id"] for item in unfinished]]))
                target_updated = await work_item_repository.patch_sprint(
                    project_id,
                    target_sprint["_id"],
                    target_sprint["revision"],
                    {"work_item_ids": target_ids, "updated_at": now()},
                )
                if not target_updated:
                    _conflict(await work_item_repository.find_sprint(project_id, target_sprint["_id"]))
                changes_by_item = {item["_id"]: {"sprint_id": target_sprint["_id"]} for item in unfinished}
            elif unfinished and payload.unfinished_action == "BACKLOG":
                changes_by_item = {item["_id"]: {"sprint_id": None} for item in unfinished}
            elif unfinished and payload.unfinished_action == "CANCEL":
                status_keys = {value["key"] for value in workflow.get("statuses", [])}
                if not payload.target_status or payload.target_status not in status_keys:
                    raise HTTPException(status_code=422, detail={"code": "SPRINT_CANCEL_STATUS_INVALID"})
                changes_by_item = {
                    item["_id"]: {"sprint_id": None, "status": payload.target_status} for item in unfinished
                }
            elif unfinished:
                raise HTTPException(status_code=422, detail={"code": "SPRINT_UNFINISHED_ACTION_INVALID"})
            for item in unfinished:
                updated_item = await work_item_repository.patch_item(
                    project_id,
                    item["_id"],
                    item["revision"],
                    {**changes_by_item[item["_id"]], "updated_at": now()},
                )
                if not updated_item:
                    _conflict(await work_item_repository.find_item(project_id, item["_id"]))
        updated = await work_item_repository.patch_sprint(project_id, sprint_id, payload.expected_revision, {"status": target, "updated_at": now()})
        if not updated:
            _conflict(await work_item_repository.find_sprint(project_id, sprint_id))
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
        prior = await work_item_repository.find_migration(project_id)
        if prior:
            return {"migration": prior, "created": 0, "already_migrated": True}
        tasks = await project_repository.list_tasks(project_id)
        timestamp = now()
        mappings = {value.legacy_status: value.target_status for value in payload.mappings}
        legacy_statuses = {task.get("status") or "UNKNOWN" for task in tasks}
        workflow_statuses = {value["key"] for value in (await _workflow(project_id)).get("statuses", [])}
        if legacy_statuses - set(mappings) or any(status not in workflow_statuses for status in mappings.values()):
            raise HTTPException(status_code=422, detail={"code": "PROJECT_TASK_MIGRATION_MAPPING_INVALID"})
        migration = {
            "_id": new_id("PTM"),
            "project_id": project_id,
            "created_by": user.id,
            "created_at": timestamp,
            "legacy_task_ids": [task["_id"] for task in tasks],
            "work_item_ids": [],
        }
        client = database.client
        if client is None:
            raise RuntimeError("Cơ sở dữ liệu chưa sẵn sàng")

        async def operation(session):
            duplicate = await database.value.project_task_migrations.find_one({"project_id": project_id}, session=session)
            if duplicate:
                return duplicate
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
                        "backlog_rank": (index + 1) * 1024,
                        "legacy_project_task_id": task["_id"],
                        "revision": 1,
                        "created_by": task.get("created_by") or user.id,
                        "created_at": task.get("created_at") or timestamp,
                        "updated_at": timestamp,
                    }
                )
            if documents:
                await database.value.work_items.insert_many(documents, session=session)
            saved = {**migration, "work_item_ids": [document["_id"] for document in documents]}
            await database.value.project_task_migrations.insert_one(saved, session=session)
            if tasks:
                await database.value.project_tasks.bulk_write(
                    [UpdateOne({"_id": task["_id"], "project_id": project_id}, {"$set": {"migration_id": saved["_id"], "migrated_at": timestamp}}) for task in tasks],
                    session=session,
                )
            return saved

        async with await client.start_session() as session:
            saved = await session.with_transaction(operation)
        await audit(user.id, "project_tasks_migrated", "ProjectTaskMigration", saved["_id"], project_id, {"created": len(saved["work_item_ids"]), "mappings": mappings})
        return {"migration": saved, "created": len(saved["work_item_ids"]), "already_migrated": False}
