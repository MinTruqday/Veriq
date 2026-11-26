from pymongo import ReturnDocument

from src.core.database import database


class TestAnalysisRepository:
    async def list_conditions(self, project_id, archived_status, limit):
        return await database.value.test_conditions.find(
            {"project_id": project_id, "status": {"$ne": archived_status}}
        ).sort([("_id", 1)]).limit(limit + 1).to_list(limit + 1)

    async def list_findings(self, query, limit):
        return await database.value.test_analysis_findings.find(query).sort(
            "updated_at", -1
        ).limit(limit).to_list(limit)

    async def find_basis(self, collection_name, identifier, project_id):
        return await database.value[collection_name].find_one(
            {"_id": identifier, "project_id": project_id}, {"_id": 1}
        )

    async def insert_finding(self, value):
        await database.value.test_analysis_findings.insert_one(value)
        return value

    async def find_finding(self, finding_id):
        return await database.value.test_analysis_findings.find_one({"_id": finding_id})

    async def find_active_member(self, project_id, user_id, status):
        return await database.value.project_members.find_one(
            {"project_id": project_id, "user_id": user_id, "status": status}
        )

    async def update_finding(self, query, changes):
        return await database.value.test_analysis_findings.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )


test_analysis_repository = TestAnalysisRepository()
