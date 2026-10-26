from pymongo import ReturnDocument

from src.core.database import database


class MaintenanceProposalRepository:
    async def list_by_impact_and_status(self, analysis_id, status, limit):
        return await database.value.maintenance_proposals.find(
            {"impact_analysis_id": analysis_id, "status": status}
        ).to_list(limit)

    async def find_change_set(self, change_set_id):
        return await database.value.requirement_change_sets.find_one(
            {"_id": change_set_id}
        )

    async def insert_many(self, values):
        if values:
            await database.value.maintenance_proposals.insert_many(values)
        return values

    async def insert(self, value):
        await database.value.maintenance_proposals.insert_one(value)
        return value

    async def list_proposals(self, query, sort_field, direction, limit, skip=0):
        cursor = database.value.maintenance_proposals.find(query).sort(
            [(sort_field, direction), ("_id", 1)]
        )
        if skip:
            cursor = cursor.skip(skip)
        return await cursor.to_list(limit)

    async def proposal_scope_snapshot(self, query, sort_field, direction):
        projection = {
            "_id": 1,
            "project_id": 1,
            "impact_analysis_id": 1,
            "proposal_type": 1,
            "target_artifact_id": 1,
            "base_version_id": 1,
            "status": 1,
            "revision": 1,
        }
        return await database.value.maintenance_proposals.find(query, projection).sort(
            [(sort_field, direction), ("_id", 1)]
        ).to_list(None)

    async def list_test_case_versions(self, project_id, version_ids, limit):
        return await database.value.test_case_versions.find(
            {"project_id": project_id, "_id": {"$in": version_ids}}
        ).to_list(limit)

    async def list_impact_analyses(self, project_id, analysis_ids, limit):
        return await database.value.impact_analyses.find(
            {"project_id": project_id, "_id": {"$in": analysis_ids}},
            {"_id": 1, "snapshot_number": 1, "change_set_id": 1},
        ).to_list(limit)

    async def update(self, query, changes):
        return await database.value.maintenance_proposals.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def count_by_statuses(self, project_id, statuses):
        return await database.value.maintenance_proposals.count_documents(
            {"project_id": project_id, "status": {"$in": statuses}}
        )

    async def rollback_supersede(
        self, proposal_id, project_id, replacement_id, pending_status, updated_at
    ):
        await database.value.maintenance_proposals.update_one(
            {
                "_id": proposal_id,
                "project_id": project_id,
                "superseded_by": replacement_id,
            },
            {
                "$set": {"status": pending_status, "updated_at": updated_at},
                "$unset": {"superseded_by": ""},
                "$inc": {"revision": 1},
            },
        )


maintenance_proposal_repository = MaintenanceProposalRepository()
