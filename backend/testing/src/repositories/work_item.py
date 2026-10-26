from pymongo import ReturnDocument

from src.core.database import database


class WorkItemRepository:
    @property
    def items(self):
        return database.value.work_items

    @property
    def dependencies(self):
        return database.value.work_item_dependencies

    @property
    def sprints(self):
        return database.value.sprints

    @property
    def boards(self):
        return database.value.planning_boards

    @property
    def workflows(self):
        return database.value.planning_workflows

    @property
    def migrations(self):
        return database.value.project_task_migrations

    async def list_items(self, project_id, query, limit=2000, session=None):
        return await self.items.find(query, session=session).sort([("backlog_rank", 1), ("updated_at", -1)]).to_list(limit)

    async def count_items(self, query, session=None):
        return await self.items.count_documents(query, session=session)

    async def find_item(self, project_id, item_id, session=None):
        return await self.items.find_one(
            {"_id": item_id, "project_id": project_id},
            **({"session": session} if session is not None else {}),
        )

    async def create_item(self, item, session=None):
        await self.items.insert_one(item, session=session)
        return item

    async def patch_item(self, project_id, item_id, revision, changes, session=None):
        return await self.items.find_one_and_update(
            {"_id": item_id, "project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            session=session,
        )

    async def next_rank(self, project_id, session=None):
        item = await self.items.find_one(
            {"project_id": project_id}, sort=[("backlog_rank", -1)], session=session
        )
        return int((item or {}).get("backlog_rank", 0)) + 1024

    async def list_dependencies(self, project_id, item_id=None, session=None):
        query = {"project_id": project_id}
        if item_id:
            query["$or"] = [{"source_item_id": item_id}, {"target_item_id": item_id}]
        cursor = self.dependencies.find(
            query, **({"session": session} if session is not None else {})
        ).sort("created_at", -1)
        return await cursor.to_list(length=None)

    async def find_dependency(
        self, project_id, source_item_id, target_item_id, dependency_type, session=None
    ):
        return await self.dependencies.find_one(
            {
                "project_id": project_id,
                "source_item_id": source_item_id,
                "target_item_id": target_item_id,
                "dependency_type": dependency_type,
            },
            **({"session": session} if session is not None else {}),
        )

    async def create_dependency(self, dependency, session=None):
        await self.dependencies.insert_one(dependency, session=session)
        return dependency

    async def list_sprints(self, project_id):
        return await self.sprints.find({"project_id": project_id}).sort("start_at", -1).to_list(500)

    async def find_sprint(self, project_id, sprint_id):
        return await self.sprints.find_one({"_id": sprint_id, "project_id": project_id})

    async def create_sprint(self, sprint):
        await self.sprints.insert_one(sprint)
        return sprint

    async def patch_sprint(self, project_id, sprint_id, revision, changes):
        return await self.sprints.find_one_and_update(
            {"_id": sprint_id, "project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def find_board(self, project_id, session=None):
        return await self.boards.find_one(
            {"project_id": project_id},
            **({"session": session} if session is not None else {}),
        )

    async def create_board(self, board):
        await self.boards.insert_one(board)
        return board

    async def patch_board(self, project_id, revision, changes, session=None):
        return await self.boards.find_one_and_update(
            {"project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def advance_board_revision(self, project_id, revision, updated_at, session=None):
        return await self.patch_board(
            project_id,
            revision,
            {"updated_at": updated_at},
            session=session,
        )

    async def find_workflow(self, project_id):
        return await self.workflows.find_one({"project_id": project_id})

    async def create_workflow(self, workflow):
        await self.workflows.insert_one(workflow)
        return workflow

    async def patch_workflow(self, project_id, revision, changes):
        return await self.workflows.find_one_and_update(
            {"project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def find_migration(self, project_id):
        return await self.migrations.find_one({"project_id": project_id})


work_item_repository = WorkItemRepository()
