from pymongo import ReturnDocument

from src.core.database import database


class ProcessImprovementRepository:
    async def find_active_member(self, project_id, user_id, active_status):
        return await database.value.project_members.find_one(
            {"project_id": project_id, "user_id": user_id, "status": active_status}
        )

    async def find_proposal(self, proposal_id):
        return await database.value.process_improvement_proposals.find_one(
            {"_id": proposal_id}
        )

    async def list_proposals(self, project_id, limit):
        return (
            await database.value.process_improvement_proposals.find(
                {"project_id": project_id}
            )
            .sort("updated_at", -1)
            .to_list(limit)
        )

    async def find_by_idempotency(self, project_id, idempotency_key):
        return await database.value.process_improvement_proposals.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_proposal(self, value, session=None):
        await database.value.process_improvement_proposals.insert_one(value, session=session)

    async def update_proposal(
        self,
        proposal_id,
        revision,
        source_status,
        changes,
        history_entry=None,
    ):
        update = {"$set": changes, "$inc": {"revision": 1}}
        if history_entry:
            update["$push"] = {"history": history_entry}
        return await database.value.process_improvement_proposals.find_one_and_update(
            {"_id": proposal_id, "revision": revision, "status": source_status},
            update,
            return_document=ReturnDocument.AFTER,
        )

    async def list_causal_analyses(self, project_id, identifiers, limit):
        return await database.value.causal_analyses.find(
            {"_id": {"$in": identifiers}, "project_id": project_id}
        ).to_list(limit)

    async def list_completion_lessons(self, project_id, lesson_ids, limit):
        return await database.value.test_completion_reports.find(
            {
                "project_id": project_id,
                "lessons_learned.lesson_id": {"$in": lesson_ids},
            },
            {"lessons_learned": 1},
        ).to_list(limit)

    async def list_measurement_snapshots(self, project_id, references, limit):
        return await database.value.measurement_snapshots.find(
            {"_id": {"$in": references}, "project_id": project_id}
        ).to_list(limit)


process_improvement_repository = ProcessImprovementRepository()
