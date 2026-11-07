from pymongo import ReturnDocument

from src.core.database import database


class InternalAdminRepository:
    async def list_memberships(self, query, projection, limit, sort=None):
        cursor = database.value.project_members.find(query, projection)
        if sort:
            cursor = cursor.sort(*sort)
        return await cursor.to_list(limit)

    async def list_projects(self, query, projection, limit, sort=None):
        cursor = database.value.projects.find(query, projection)
        if sort:
            cursor = cursor.sort(*sort)
        return await cursor.limit(limit).to_list(limit)

    async def member_counts(self, project_ids, limit):
        return await database.value.project_members.aggregate(
            [
                {"$match": {"project_id": {"$in": project_ids}}},
                {"$group": {"_id": "$project_id", "count": {"$sum": 1}}},
            ]
        ).to_list(limit)

    async def find_project(self, project_id, projection=None):
        return await database.value.projects.find_one({"_id": project_id}, projection)

    async def count_members(self, project_id, status=None):
        query = {"project_id": project_id}
        if status:
            query["status"] = status
        return await database.value.project_members.count_documents(query)

    async def update_project(self, project_id, changes, increment_revision=True):
        update = {"$set": changes}
        if increment_revision:
            update["$inc"] = {"revision": 1}
        return await database.value.projects.find_one_and_update(
            {"_id": project_id}, update, return_document=ReturnDocument.AFTER
        )

    async def purge_project(self, project_id, excluded_collections, counter_pattern):
        deleted = {}
        for collection_name in await database.value.list_collection_names():
            if collection_name in excluded_collections:
                continue
            result = await database.value[collection_name].delete_many(
                {"project_id": project_id}
            )
            if result.deleted_count:
                deleted[collection_name] = result.deleted_count
        await database.value.audit_events.update_many(
            {"project_id": project_id},
            {"$set": {"project_deleted": True}, "$unset": {"details": ""}},
        )
        await database.value.counters.delete_many({"_id": {"$regex": counter_pattern}})
        await database.value.projects.delete_one({"_id": project_id})
        return deleted

    async def list_break_glass_grants(self, query, limit):
        return (
            await database.value.break_glass_grants.find(query)
            .sort("created_at", -1)
            .to_list(limit)
        )

    async def insert_break_glass_grant(self, value):
        await database.value.break_glass_grants.insert_one(value)

    async def revoke_break_glass_grant(
        self, grant_id, active_status, revoked_status, changes
    ):
        return await database.value.break_glass_grants.find_one_and_update(
            {"_id": grant_id, "status": active_status},
            {"$set": {**changes, "status": revoked_status}},
            return_document=ReturnDocument.AFTER,
        )

    async def count_records(self, collection, query):
        return await database.value[collection].count_documents(query)

    async def index_status_counts(self, collection, unknown_status, limit):
        rows = await database.value[collection].aggregate(
            [{"$group": {"_id": "$index_status", "count": {"$sum": 1}}}]
        ).to_list(limit)
        return {(row["_id"] or unknown_status): row["count"] for row in rows}

    async def distinct_ids(self, collection, project_id, status):
        return await database.value[collection].distinct(
            "_id", {"project_id": project_id, "status": status}
        )

    async def list_project_documents(self, collection, project_id, field, limit):
        return await database.value[collection].find(
            {"project_id": project_id}, {field: 1}
        ).to_list(limit)


internal_admin_repository = InternalAdminRepository()
