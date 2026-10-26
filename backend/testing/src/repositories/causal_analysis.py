from pymongo import ReturnDocument

from src.core.database import database


class CausalAnalysisRepository:
    async def find_active_member(self, project_id, user_id, status):
        return await database.value.project_members.find_one(
            {"project_id": project_id, "user_id": user_id, "status": status}
        )

    async def find_analysis(self, analysis_id):
        return await database.value.causal_analyses.find_one({"_id": analysis_id})

    async def list_analyses(self, query, limit, projection=None):
        return await database.value.causal_analyses.find(query, projection).sort(
            "updated_at", -1
        ).to_list(limit)

    async def find_analysis_by_idempotency(self, project_id, idempotency_key):
        return await database.value.causal_analyses.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_analysis(self, value):
        await database.value.causal_analyses.insert_one(value)
        return value

    async def update_analysis(self, query, changes, add_to_set=None):
        update = {"$set": changes, "$inc": {"revision": 1}}
        if add_to_set:
            update["$addToSet"] = add_to_set
        return await database.value.causal_analyses.find_one_and_update(
            query, update, return_document=ReturnDocument.AFTER
        )

    async def list_defects(self, query, limit, projection=None):
        return await database.value.defects.find(query, projection).sort(
            "updated_at", -1
        ).to_list(limit)

    async def find_action(self, action_id):
        return await database.value.preventive_actions.find_one({"_id": action_id})

    async def list_actions(self, analysis_id, limit):
        return await database.value.preventive_actions.find(
            {"causal_analysis_id": analysis_id}
        ).sort("created_at", 1).to_list(limit)

    async def insert_action(self, value):
        await database.value.preventive_actions.insert_one(value)
        return value

    async def delete_action(self, action_id):
        await database.value.preventive_actions.delete_one({"_id": action_id})

    async def update_action(self, query, changes):
        return await database.value.preventive_actions.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def find_ai_result_by_idempotency(self, project_id, idempotency_key):
        return await database.value.ai_results.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_latest_ai_result(self, project_id, subject_id, result_type, projection=None):
        return await database.value.ai_results.find_one(
            {
                "project_id": project_id,
                "subject_id": subject_id,
                "result_type": result_type,
            },
            projection,
            sort=[("created_at", -1), ("_id", -1)],
        )

    async def insert_ai_result(self, value):
        await database.value.ai_results.insert_one(value)
        return value


causal_analysis_repository = CausalAnalysisRepository()
