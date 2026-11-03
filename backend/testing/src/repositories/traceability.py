from pymongo import ReturnDocument

from src.core.database import database


class TraceabilityRepository:
    async def artifact_exists(self, collection, artifact_id, project_id):
        return bool(
            await database.value[collection].find_one(
                {"_id": artifact_id, "project_id": project_id}, {"_id": 1}
            )
        )

    async def find_link(self, query):
        return await database.value.trace_links.find_one(query)

    async def insert_link(self, link):
        await database.value.trace_links.insert_one(link)

    async def transition_link(self, link_id, project_id, source_status, changes):
        return await database.value.trace_links.find_one_and_update(
            {"_id": link_id, "project_id": project_id, "status": source_status},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def count_links(self, query):
        return await database.value.trace_links.count_documents(query)

    async def list_records(self, collection, query, limit, sort=None, projection=None):
        cursor = database.value[collection].find(query, projection)
        if sort:
            cursor = cursor.sort(*sort)
        return await cursor.to_list(limit)

    async def count_records(self, collection, query):
        return await database.value[collection].count_documents(query)

    async def find_snapshot(self, project_id, idempotency_key):
        return await database.value.coverage_snapshots.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_snapshot(self, snapshot, session=None):
        await database.value.coverage_snapshots.insert_one(snapshot, session=session)


traceability_repository = TraceabilityRepository()
