from pymongo import ReturnDocument

from src.core.database import database


class NonFunctionalTestRepository:
    async def count_project_entities(self, collection_name, project_id, entity_ids):
        return await database.value[collection_name].count_documents(
            {"project_id": project_id, "_id": {"$in": entity_ids}}
        )

    async def find_plan(self, plan_id):
        return await database.value.non_functional_test_plans.find_one({"_id": plan_id})

    async def list_plans(self, query, limit):
        return await database.value.non_functional_test_plans.find(query).sort(
            "updated_at", -1
        ).to_list(limit)

    async def find_plan_by_idempotency_key(self, project_id, idempotency_key):
        return await database.value.non_functional_test_plans.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_plan(self, value):
        await database.value.non_functional_test_plans.insert_one(value)
        return value

    async def update_plan(self, plan_id, revision, statuses, changes):
        return await database.value.non_functional_test_plans.find_one_and_update(
            {"_id": plan_id, "revision": revision, "status": {"$in": statuses}},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def transition_plan(self, plan_id, revision, source_status, changes, session=None):
        return await database.value.non_functional_test_plans.find_one_and_update(
            {"_id": plan_id, "revision": revision, "status": source_status},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def find_evidence_by_idempotency_key(self, project_id, idempotency_key):
        return await database.value.non_functional_test_evidence.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_evidence(self, value):
        await database.value.non_functional_test_evidence.insert_one(value)
        return value

    async def attach_evidence(self, plan_id, evidence_id, result_summary, updated_at):
        await database.value.non_functional_test_plans.update_one(
            {"_id": plan_id},
            {
                "$addToSet": {"external_evidence_ids": evidence_id},
                "$set": {"result_summary": result_summary, "updated_at": updated_at},
                "$inc": {"revision": 1},
            },
        )

    async def list_evidence(self, plan_id, limit):
        return await database.value.non_functional_test_evidence.find(
            {"plan_id": plan_id}
        ).sort("created_at", -1).to_list(limit)


non_functional_test_repository = NonFunctionalTestRepository()
