from pymongo import ReturnDocument

from src.core.database import database


class TestAdequacyRepository:
    async def find(self, project_id, requirement_version_id):
        return await database.value.test_adequacy_assessments.find_one(
            {"project_id": project_id, "requirement_version_id": requirement_version_id}
        )

    async def insert(self, value):
        await database.value.test_adequacy_assessments.insert_one(value)
        return value

    async def replace(self, assessment_id, project_id, revision, value):
        return await database.value.test_adequacy_assessments.find_one_and_update(
            {"_id": assessment_id, "project_id": project_id, "revision": revision},
            {"$set": value, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def list_for_requirement(self, project_id, requirement_id):
        return await database.value.test_adequacy_assessments.find(
            {"project_id": project_id, "requirement_id": requirement_id}
        ).to_list(1000)

    async def list_for_versions(self, project_id, requirement_version_ids):
        if not requirement_version_ids:
            return []
        return await database.value.test_adequacy_assessments.find(
            {"project_id": project_id, "requirement_version_id": {"$in": list(requirement_version_ids)}}
        ).to_list(len(requirement_version_ids))

    async def supersede_for_requirement(self, project_id, requirement_id, keep_version_id, timestamp):
        await database.value.test_adequacy_assessments.update_many(
            {
                "project_id": project_id,
                "requirement_id": requirement_id,
                "requirement_version_id": {"$ne": keep_version_id},
                "status": {"$ne": "SUPERSEDED"},
            },
            {"$set": {"status": "SUPERSEDED", "superseded_at": timestamp, "updated_at": timestamp}},
        )

    async def invalidate_for_requirement_versions(self, project_id, requirement_version_ids, timestamp):
        if not requirement_version_ids:
            return
        await database.value.test_adequacy_assessments.update_many(
            {
                "project_id": project_id,
                "requirement_version_id": {"$in": requirement_version_ids},
                "status": {"$ne": "SUPERSEDED"},
            },
            {"$set": {"status": "DRAFT", "updated_at": timestamp}, "$inc": {"revision": 1}},
        )


test_adequacy_repository = TestAdequacyRepository()
