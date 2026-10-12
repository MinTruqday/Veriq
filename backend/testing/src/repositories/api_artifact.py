from pymongo import ReturnDocument

from src.core.database import database


class APIArtifactRepository:
    async def list_imports(self, query, limit, sort=None):
        cursor = database.value.api_imports.find(query)
        if sort:
            cursor = cursor.sort(*sort)
        return await cursor.to_list(limit)

    async def find_import(self, artifact_id, project_id):
        return await database.value.api_imports.find_one(
            {"_id": artifact_id, "project_id": project_id}
        )

    async def insert_import(self, value):
        await database.value.api_imports.insert_one(value)

    async def transition_import(self, query, changes, increment_revision=False):
        update = {"$set": changes}
        if increment_revision:
            update["$inc"] = {"revision": 1}
        return await database.value.api_imports.find_one_and_update(
            query, update, return_document=ReturnDocument.AFTER
        )

    async def list_operations(self, query, limit, sort=None):
        cursor = database.value.api_operations.find(query)
        if sort:
            cursor = cursor.sort(*sort)
        return await cursor.to_list(limit)

    async def find_operation(self, operation_id, project_id):
        return await database.value.api_operations.find_one(
            {"_id": operation_id, "project_id": project_id}
        )

    async def upsert_operation(self, value):
        await database.value.api_operations.update_one(
            {"_id": value["_id"]}, {"$setOnInsert": value}, upsert=True
        )

    async def find_impact(self, project_id, source_type, from_id, to_id):
        return await database.value.impact_analyses.find_one(
            {
                "project_id": project_id,
                "source_type": source_type,
                "from_artifact_id": from_id,
                "to_artifact_id": to_id,
            }
        )

    async def list_test_cases(self, project_id, statuses, limit):
        return await database.value.test_cases.find(
            {"project_id": project_id, "status": {"$in": statuses}}
        ).to_list(limit)

    async def list_test_case_versions(self, project_id, version_ids, limit):
        return await database.value.test_case_versions.find(
            {"project_id": project_id, "_id": {"$in": version_ids}}
        ).to_list(limit)

    async def insert_impact(self, value):
        await database.value.impact_analyses.insert_one(value)


api_artifact_repository = APIArtifactRepository()
