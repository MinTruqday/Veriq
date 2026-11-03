from pymongo import ReturnDocument

from src.core.database import database


class StatisticalQualityRepository:
    async def find_analysis(self, analysis_id):
        return await database.value.process_control_baselines.find_one(
            {"_id": analysis_id}
        )

    async def list_analyses(self, query, limit):
        return await database.value.process_control_baselines.find(query).sort(
            "created_at", -1
        ).to_list(limit)

    async def find_by_idempotency(self, project_id, idempotency_key):
        return await database.value.process_control_baselines.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_definition(self, definition_id, project_id):
        return await database.value.measurement_definitions.find_one(
            {"_id": definition_id, "project_id": project_id}
        )

    async def list_snapshots(self, project_id, definition_id, snapshot_ids, limit):
        return await database.value.measurement_snapshots.find(
            {
                "_id": {"$in": snapshot_ids},
                "project_id": project_id,
                "measurement_definition_id": definition_id,
            }
        ).sort("measured_at", 1).to_list(limit)

    async def insert_analysis(self, value, session=None):
        await database.value.process_control_baselines.insert_one(value, session=session)
        return value

    async def annotate(self, analysis_id, revision, cause, updated_at):
        return await database.value.process_control_baselines.find_one_and_update(
            {"_id": analysis_id, "revision": revision},
            {
                "$push": {"special_causes": cause},
                "$set": {"updated_at": updated_at},
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def list_analyses_by_ids(self, project_id, analysis_ids, limit):
        return await database.value.process_control_baselines.find(
            {"_id": {"$in": analysis_ids}, "project_id": project_id}
        ).to_list(limit)

    async def find_improvement(self, improvement_id, project_id):
        return await database.value.process_improvement_proposals.find_one(
            {"_id": improvement_id, "project_id": project_id}
        )


statistical_quality_repository = StatisticalQualityRepository()
