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

memory_repository = MemoryRepository()
