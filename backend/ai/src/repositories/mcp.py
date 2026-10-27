from datetime import datetime, timedelta, timezone

from pymongo import DESCENDING, ReturnDocument

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.runtime.limits import limits
from src.schemas.mcp import MCPConnection, MCPToolCallAudit


class MCPRepository:
    @property
    def _collection(self):
        return database.mongodb[settings.AI_DB_NAME].mcp_connections

    @property
    def _audit_collection(self):
        return database.mongodb[settings.AI_DB_NAME].mcp_tool_call_audits

    async def record_call_audit(self, audit: MCPToolCallAudit) -> MCPToolCallAudit:
        value = audit.model_dump(mode="python")
        value["_id"] = value.pop("audit_id")
        await self._audit_collection.insert_one(value)
        return audit

    async def complete_call_audit(
        self,
        audit_id: str,
        *,
        status: str,
        reason_code: str | None,
        connection_revision: int | None,
        output_sha256: str,
        completed_at: datetime,
    ) -> bool:
        result = await self._audit_collection.update_one(
            {"_id": audit_id, "status": "running"},
            {
                "$set": {
                    "status": status,
                    "reason_code": reason_code,
                    "connection_revision": connection_revision,
                    "output_sha256": output_sha256,
                    "completed_at": completed_at,
                }
            },
        )
        return result.modified_count == 1

    async def recover_interrupted_call_audits(self) -> int:
        now = datetime.now(timezone.utc)
        stale_after_seconds = (
            limits.task_timeout_seconds + limits.message_ack_timeout_seconds
        )
        result = await self._audit_collection.update_many(
            {
                "status": "running",
                "started_at": {
                    "$lte": now - timedelta(seconds=stale_after_seconds)
                },
            },
            {
                "$set": {
                    "status": "degraded",
                    "reason_code": "MCP_CALL_INTERRUPTED_DURING_WORKER_RESTART",
                    "completed_at": now,
                }
            },
        )
        return result.modified_count

    async def list_call_audits(
        self,
        project_id: str,
        limit: int = 100,
        automation_run_id: str | None = None,
        task_id: str | None = None,
    ) -> list[MCPToolCallAudit]:
        query = {"project_id": project_id}
        if automation_run_id is not None:
            query["automation_run_id"] = automation_run_id
        if task_id is not None:
            query["task_id"] = task_id
        values = await self._audit_collection.find(query).sort(
            [("completed_at", DESCENDING), ("_id", DESCENDING)]
        ).to_list(length=max(1, min(limit, 500)))
        for value in values:
            value["audit_id"] = str(value.pop("_id"))
        return [MCPToolCallAudit.model_validate(value) for value in values]

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
        values = await self._collection.find(
            {"$or": [{"project_id": project_id}, {"project_id": None}]}
        ).sort(
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
