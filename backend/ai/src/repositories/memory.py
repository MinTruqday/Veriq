from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database


class MemoryRepository:
    @property
    def _database(self):
        return database.mongodb[settings.AI_DB_NAME]

    async def list_long_term(self, project_id, requester_id, limit):
        return await self._database.long_term_memory.find(
            {
                "project_id": project_id,
                "trusted": True,
                "owner_id": requester_id,
            }
        ).sort("created_at", -1).to_list(length=limit)

    async def record_long_term(self, run_id, value):
        await self._database.long_term_memory.update_one(
            {"run_id": run_id}, {"$setOnInsert": value}, upsert=True
        )

    async def save_run(self, payload):
        await self._database.agent_runs.replace_one({"_id": payload["_id"]}, payload, upsert=True)

    async def find_run(self, run_id, project_id=None):
        query = {"_id": run_id}
        if project_id:
            query["project_id"] = project_id
        return await self._database.agent_runs.find_one(query)

    async def count_runs(self, statuses):
        return await self._database.agent_runs.count_documents({"status": {"$in": statuses}})


memory_repository = MemoryRepository()
