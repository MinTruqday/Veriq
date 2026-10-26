from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import OperationFailure

from src.core.common import audit, get_project, get_project_role, get_project_roles, new_id, now, optimistic_patch, resolve_user_reference
from src.core.database import database
from src.repositories.project import project_repository


def task_summary(tasks):
    applicable = [task for task in tasks if task.get("status") != "CANCELLED"]
    denominator = sum(float(task.get("weight", 0)) for task in applicable)
    completed_weight = sum(
        float(task.get("weight", 0))
        for task in applicable
        if task.get("status") == "COMPLETED"
    )
    return {
        "total": len(tasks),
        "completed": sum(task.get("status") == "COMPLETED" for task in tasks),
        "in_progress": sum(task.get("status") == "IN_PROGRESS" for task in tasks),
        "blocked": sum(task.get("status") == "BLOCKED" for task in tasks),
        "cancelled": sum(task.get("status") == "CANCELLED" for task in tasks),
        "applicable_total": len(applicable),
        "completion_percent": round(completed_weight * 100 / denominator, 2) if denominator else None,
    }


async def task_summaries(project_ids):
    if not project_ids:
        return {}
    migrated = {
        value["project_id"]
        for value in await database.value.project_task_migrations.find(
            {"project_id": {"$in": project_ids}}
        ).to_list(len(project_ids))
    }
    legacy_tasks = await project_repository.list_tasks_for_projects(
        [project_id for project_id in project_ids if project_id not in migrated]
    )
    work_items = await database.value.work_items.find(
        {
            "project_id": {"$in": project_ids},
            "item_type": {"$in": ["TASK", "SUBTASK"]},
        }
    ).to_list(length=None)
    workflows = await database.value.planning_workflows.find(
        {"project_id": {"$in": project_ids}}
    ).to_list(len(project_ids))
    completed_statuses = {
        workflow["project_id"]: {
            value["key"] for value in workflow.get("statuses", []) if value.get("counts_as_completed")
        }
        for workflow in workflows
    }
    grouped = {project_id: [] for project_id in project_ids}
    for task in legacy_tasks:
        grouped.setdefault(task["project_id"], []).append(task)
    for item in work_items:
        grouped.setdefault(item["project_id"], []).append(
            {
                "status": "COMPLETED"
                if item["status"] in completed_statuses.get(item["project_id"], {"DONE"})
                else item["status"],
                "weight": item.get("estimate") or 1,
            }
        )
    return {project_id: task_summary(items) for project_id, items in grouped.items()}


async def _ensure_legacy_task_catalog_writable(project_id, session):
    lock = await project_repository.lock_legacy_task_catalog(project_id, session)
    if lock.matched_count != 1:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    if await database.value.project_task_migrations.find_one(
        {"project_id": project_id}, session=session
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "PROJECT_TASKS_MIGRATED_USE_WORK_ITEM"},
        )


async def _run_legacy_task_write(project_id, operation):
    client = database.client
    if client is None:
        raise RuntimeError("Cơ sở dữ liệu chưa sẵn sàng")
    async with await client.start_session() as session:
        try:
            return await session.with_transaction(operation)
        except OperationFailure as exc:
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "PROJECT_TASK_CATALOG_CONCURRENT_UPDATE"},
                ) from exc
            raise


class ProjectProgressService:
    @staticmethod
    async def _require_qa(project_id, user):
        await get_project(project_id, user, "project.read")
        if "QA" not in await get_project_roles(project_id, user.id):
            raise HTTPException(status_code=403, detail={"code": "QA_PROJECT_PROGRESS_REQUIRED"})

    @staticmethod
    async def update_project_progress(project_id, payload, user):
        await get_project(project_id, user, "project.read")
        await ProjectProgressService._require_qa(project_id, user)

        async def operation(session):
            current = await database.value.projects.find_one(
                {"_id": project_id, "revision": payload.expected_revision},
                session=session,
            )
            if not current:
                return await optimistic_patch(
                    "projects",
                    project_id,
                    project_id,
                    payload.expected_revision,
                    {"project_completion_percent": payload.project_completion_percent},
                    session=session,
                )
            updated = await optimistic_patch(
                "projects",
                project_id,
                project_id,
                payload.expected_revision,
                {"project_completion_percent": payload.project_completion_percent},
                session=session,
            )
            await audit(
                user.id,
                "project_completion_percent_updated",
                "Project",
                project_id,
                project_id,
                {
                    "previous_value": int(current.get("project_completion_percent", 0)),
                    "new_value": payload.project_completion_percent,
                    "note": payload.note,
                },
                session=session,
            )
            return updated

        client = database.client
        if client is None:
            raise RuntimeError("Cơ sở dữ liệu chưa sẵn sàng")
        async with await client.start_session() as session:
            return await session.with_transaction(operation)

    @staticmethod
    async def list_tasks(project_id, user, status=None):
        await get_project(project_id, user, "project.read")
        migration = await database.value.project_task_migrations.find_one(
            {"project_id": project_id}
        )
        if migration:
            return {
                "items": [],
                "summary": task_summary([]),
                "migration": migration,
                "read_only": True,
            }
        items = await project_repository.list_tasks(project_id, status=status)
        return {"items": items, "summary": task_summary(items)}

    @staticmethod
    async def create_task(project_id, payload, user):
        await ProjectProgressService._require_qa(project_id, user)
        assignee_id = await ProjectProgressService._resolve_assignee(project_id, payload.assignee_id)
        timestamp = now()
        task = {
            "_id": new_id("PTK"),
            "project_id": project_id,
            **payload.model_dump(exclude={"assignee_id"}),
            "assignee_id": assignee_id,
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        async def operation(session):
            await _ensure_legacy_task_catalog_writable(project_id, session)
            await database.value.project_tasks.insert_one(task, session=session)
            await audit(
                user.id,
                "project_task_created",
                "ProjectTask",
                task["_id"],
                project_id,
                session=session,
            )

        await _run_legacy_task_write(project_id, operation)
        return task

    @staticmethod
    async def update_task(project_id, task_id, payload, user):
        await ProjectProgressService._require_qa(project_id, user)
        changes = payload.model_dump(exclude_unset=True)
        changes.pop("expected_revision", None)
        if not changes:
            raise HTTPException(status_code=422, detail={"code": "PROJECT_TASK_EMPTY"})
        if "assignee_id" in changes:
            changes["assignee_id"] = await ProjectProgressService._resolve_assignee(
                project_id, changes["assignee_id"]
            )
        changes["updated_at"] = now()

        async def operation(session):
            await _ensure_legacy_task_catalog_writable(project_id, session)
            updated = await database.value.project_tasks.find_one_and_update(
                {
                    "_id": task_id,
                    "project_id": project_id,
                    "revision": payload.expected_revision,
                },
                {"$set": changes, "$inc": {"revision": 1}},
                return_document=ReturnDocument.AFTER,
                session=session,
            )
            if not updated:
                existing = await database.value.project_tasks.find_one(
                    {"_id": task_id, "project_id": project_id}, session=session
                )
                if not existing:
                    raise HTTPException(
                        status_code=404,
                        detail={"code": "PROJECT_TASK_NOT_FOUND"},
                    )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "REVISION_CONFLICT",
                        "current_revision": existing.get("revision"),
                    },
                )
            await audit(
                user.id,
                "project_task_updated",
                "ProjectTask",
                task_id,
                project_id,
                {"changed": sorted(changes)},
                session=session,
            )
            return updated

        updated = await _run_legacy_task_write(project_id, operation)
        return updated

    @staticmethod
    async def delete_task(project_id, task_id, payload, user):
        await ProjectProgressService._require_qa(project_id, user)

        async def operation(session):
            await _ensure_legacy_task_catalog_writable(project_id, session)
            result = await database.value.project_tasks.delete_one(
                {
                    "_id": task_id,
                    "project_id": project_id,
                    "revision": payload.expected_revision,
                },
                session=session,
            )
            if not result.deleted_count:
                existing = await database.value.project_tasks.find_one(
                    {"_id": task_id, "project_id": project_id}, session=session
                )
                if not existing:
                    raise HTTPException(
                        status_code=404,
                        detail={"code": "PROJECT_TASK_NOT_FOUND"},
                    )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "REVISION_CONFLICT",
                        "current_revision": existing.get("revision"),
                    },
                )
            await audit(
                user.id,
                "project_task_deleted",
                "ProjectTask",
                task_id,
                project_id,
                session=session,
            )

        await _run_legacy_task_write(project_id, operation)
        return {"deleted": True, "task_id": task_id}

    @staticmethod
    async def _resolve_assignee(project_id, value):
        if value is None or not str(value).strip():
            return None
        user_id = await resolve_user_reference(value)
        membership = await project_repository.find_member(project_id, user_id, status="ACTIVE")
        if not membership:
            raise HTTPException(status_code=422, detail={"code": "PROJECT_TASK_ASSIGNEE_INVALID"})
        return user_id
