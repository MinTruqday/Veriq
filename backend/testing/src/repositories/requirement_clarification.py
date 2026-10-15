from pymongo import ReturnDocument

from src.core.database import database


class RequirementClarificationRepository:
    @property
    def collection(self):
        return database.value.requirement_clarifications

    async def insert(self, value):
        await self.collection.insert_one(value)
        return value

    async def list_for_version(self, project_id, requirement_version_id):
        return await self.collection.find(
            {"project_id": project_id, "requirement_version_id": requirement_version_id}
        ).sort("created_at", -1).to_list(1000)

    async def list_open_for_version(self, project_id, requirement_version_id):
        return await self.collection.find(
            {
                "project_id": project_id,
                "requirement_version_id": requirement_version_id,
                "status": {"$in": ["OPEN", "ANSWERED"]},
            }
        ).to_list(1000)

    async def list_open_for_versions(self, project_id, requirement_version_ids):
        if not requirement_version_ids:
            return []
        return await self.collection.find(
            {
                "project_id": project_id,
                "requirement_version_id": {"$in": list(requirement_version_ids)},
                "status": {"$in": ["OPEN", "ANSWERED"]},
            }
        ).to_list(5000)

    async def find(self, clarification_id, project_id=None):
        query = {"_id": clarification_id}
        if project_id:
            query["project_id"] = project_id
        return await self.collection.find_one(query)

    async def find_active_finding(self, project_id, requirement_version_id, finding_key):
        return await self.collection.find_one(
            {
                "project_id": project_id,
                "requirement_version_id": requirement_version_id,
                "finding_key": finding_key,
                "status": {"$in": ["OPEN", "ANSWERED"]},
            }
        )

    async def replace(self, clarification_id, project_id, revision, changes):
        return await self.collection.find_one_and_update(
            {"_id": clarification_id, "project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def supersede_for_requirement(self, project_id, requirement_id, keep_version_id, timestamp):
        await self.collection.update_many(
            {
                "project_id": project_id,
                "requirement_id": requirement_id,
                "requirement_version_id": {"$ne": keep_version_id},
                "status": {"$in": ["OPEN", "ANSWERED"]},
            },
            {"$set": {"status": "SUPERSEDED", "superseded_at": timestamp, "updated_at": timestamp}, "$inc": {"revision": 1}},
        )


requirement_clarification_repository = RequirementClarificationRepository()
