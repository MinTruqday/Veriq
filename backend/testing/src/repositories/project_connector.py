from pymongo import ReturnDocument

from src.core.database import database


class ProjectConnectorRepository:
    @property
    def connectors(self):
        return database.value.project_connectors

    @property
    def jobs(self):
        return database.value.connector_sync_jobs

    @property
    def conflicts(self):
        return database.value.connector_sync_conflicts

    async def list_connectors(self, project_id, limit=100):
        return await self.connectors.find({"project_id": project_id}).sort(
            "updated_at", -1
        ).to_list(limit)

    async def insert_connector(self, value):
        await self.connectors.insert_one(value)
        return value

    async def update_connector(self, connector_id, project_id, revision, changes):
        return await self.connectors.find_one_and_update(
            {"_id": connector_id, "project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def unbind_connector(
        self, connector_id, project_id, revision, bound_status, changes
    ):
        return await self.connectors.find_one_and_update(
            {
                "_id": connector_id,
                "project_id": project_id,
                "revision": revision,
                "status": bound_status,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def find_job_by_idempotency_key(self, project_id, idempotency_key):
        return await self.jobs.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_job(self, value, session=None):
        await self.jobs.insert_one(value, session=session)
        return value

    async def list_jobs(self, project_id, limit=1000):
        return await self.jobs.find({"project_id": project_id}).sort(
            "created_at", -1
        ).to_list(limit)

    async def list_conflicts(self, project_id, limit=1000):
        return await self.conflicts.find({"project_id": project_id}).sort(
            "created_at", -1
        ).to_list(limit)

    async def resolve_conflict(
        self, conflict_id, project_id, revision, open_status, changes
    ):
        return await self.conflicts.find_one_and_update(
            {
                "_id": conflict_id,
                "project_id": project_id,
                "revision": revision,
                "status": open_status,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )


project_connector_repository = ProjectConnectorRepository()
