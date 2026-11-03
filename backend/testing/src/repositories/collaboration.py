from pymongo import ReturnDocument

from src.core.database import database


class CollaborationRepository:
    async def find_requirement_version(self, version_id, project_id):
        return await database.value.requirement_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def upsert_presence(self, query, changes, insert_values):
        return await database.value.collaboration_sessions.find_one_and_update(
            query,
            {"$set": changes, "$setOnInsert": insert_values},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def list_presence(self, query, limit):
        return await database.value.collaboration_sessions.find(query).sort(
            "last_seen_at", -1
        ).to_list(limit)

    async def find_operation(self, project_id, operation_id):
        return await database.value.collaboration_operations.find_one(
            {"project_id": project_id, "operation_id": operation_id}
        )

    async def list_operations_since(
        self, project_id, artifact_type, artifact_id, base_revision, limit
    ):
        return await database.value.collaboration_operations.find(
            {
                "project_id": project_id,
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
                "result_revision": {"$gt": base_revision},
            }
        ).to_list(limit)

    async def insert_conflict(self, value):
        await database.value.draft_conflicts.insert_one(value)
        return value

    async def insert_operation(self, value, session=None):
        await database.value.collaboration_operations.insert_one(value, session=session)
        return value

    async def list_conflicts(self, project_id, limit):
        return await database.value.draft_conflicts.find(
            {"project_id": project_id}
        ).sort("created_at", -1).to_list(limit)

    async def resolve_conflict(self, conflict_id, project_id, status, revision, changes):
        return await database.value.draft_conflicts.find_one_and_update(
            {
                "_id": conflict_id,
                "project_id": project_id,
                "status": status,
                "revision": revision,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )


collaboration_repository = CollaborationRepository()
