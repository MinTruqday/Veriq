from pymongo import ReturnDocument

from src.core.database import database
from src.repositories.common import common_repository


class TestAdequacyRepository:
    async def find(self, project_id, requirement_version_id):
        return await database.value.test_adequacy_assessments.find_one(
            {"project_id": project_id, "requirement_version_id": requirement_version_id}
        )

    async def insert(self, value, session=None):
        await database.value.test_adequacy_assessments.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def replace(
        self, assessment_id, project_id, revision, value, session=None,
        expected_status=None,
    ):
        query = {"_id": assessment_id, "project_id": project_id, "revision": revision}
        if expected_status is not None:
            query["status"] = expected_status
        return await database.value.test_adequacy_assessments.find_one_and_update(
            query,
            {"$set": value, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def list_for_requirement(self, project_id, requirement_id):
        return await common_repository.list_all_by_id(
            "test_adequacy_assessments",
            {"project_id": project_id, "requirement_id": requirement_id},
        )

    async def list_for_versions(self, project_id, requirement_version_ids):
        if not requirement_version_ids:
            return []
        return await database.value.test_adequacy_assessments.find(
            {"project_id": project_id, "requirement_version_id": {"$in": list(requirement_version_ids)}}
        ).to_list(len(requirement_version_ids))

    async def supersede_for_requirement(
        self, project_id, requirement_id, keep_version_id, timestamp, session=None
    ):
        await database.value.test_adequacy_assessments.update_many(
            {
                "project_id": project_id,
                "requirement_id": requirement_id,
                "requirement_version_id": {"$ne": keep_version_id},
                "status": {"$ne": "SUPERSEDED"},
            },
            {"$set": {"status": "SUPERSEDED", "superseded_at": timestamp, "updated_at": timestamp}},
            **({"session": session} if session is not None else {}),
        )

    async def invalidate_for_requirement_versions(
        self, project_id, requirement_version_ids, timestamp, invalidation_id
    ):
        if not requirement_version_ids or not invalidation_id:
            return
        await database.value.test_adequacy_assessments.update_many(
            {
                "project_id": project_id,
                "requirement_version_id": {"$in": requirement_version_ids},
                "status": {"$ne": "SUPERSEDED"},
                "test_case_invalidation_ids": {"$ne": invalidation_id},
            },
            {
                "$set": {"status": "DRAFT", "updated_at": timestamp},
                "$addToSet": {"test_case_invalidation_ids": invalidation_id},
                "$inc": {"revision": 1},
            },
        )


test_adequacy_repository = TestAdequacyRepository()
