from datetime import datetime, timezone

from pymongo import DESCENDING, ReturnDocument

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.schemas.mcp import MCPConnection


class MCPRepository:
    @property
    def _collection(self):
        return database.mongodb[settings.AI_DB_NAME].mcp_connections

    async def create(self, connection: MCPConnection) -> MCPConnection:
        value = connection.model_dump(mode="python")
        value["_id"] = value.pop("connection_id")
        await self._collection.insert_one(value)
        return connection

    async def get(self, connection_id: str) -> MCPConnection | None:
        value = await self._collection.find_one({"_id": connection_id})
        if not value:
            return None
        value["connection_id"] = str(value.pop("_id"))
        return MCPConnection.model_validate(value)

    async def list_project(self, project_id: str, limit: int = 100) -> list[MCPConnection]:
        values = await self._collection.find({"project_id": project_id}).sort(
            [("updated_at", DESCENDING), ("_id", 1)]
        ).to_list(length=limit)
        for value in values:
            value["connection_id"] = str(value.pop("_id"))
        return [MCPConnection.model_validate(value) for value in values]

    async def patch(
        self, connection_id: str, expected_revision: int, values: dict
    ) -> MCPConnection | None:
        result = await self._collection.find_one_and_update(
            {"_id": connection_id, "revision": expected_revision},
            {"$set": {**values, "updated_at": datetime.now(timezone.utc)}, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            return None
        result["connection_id"] = str(result.pop("_id"))
        return MCPConnection.model_validate(result)


mcp_repository = MCPRepository()
