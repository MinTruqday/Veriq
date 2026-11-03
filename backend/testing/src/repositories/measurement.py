from pymongo import ReturnDocument

from src.core.database import database


class MeasurementRepository:
    async def list_definitions(self, project_id, limit):
        return (
            await database.value.measurement_definitions.find(
                {"$or": [{"project_id": project_id}, {"project_id": None}]}
            )
            .sort([("key", 1), ("version", -1)])
            .to_list(limit)
        )

    async def find_definition_idempotency(self, project_id, idempotency_key):
        return await database.value.measurement_definitions.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_latest_definition(self, project_id, key):
        return await database.value.measurement_definitions.find_one(
            {"project_id": project_id, "key": key}, sort=[("version", -1)]
        )

    async def find_definition(self, definition_id, query=None):
        return await database.value.measurement_definitions.find_one(
            {"_id": definition_id, **(query or {})}
        )

    async def insert_definition(self, value, session=None):
        await database.value.measurement_definitions.insert_one(value, session=session)

    async def update_definition(
        self, definition_id, revision, source_status, changes
    ):
        return await database.value.measurement_definitions.find_one_and_update(
            {"_id": definition_id, "revision": revision, "status": source_status},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def archive_other_active_definitions(
        self, project_id, key, excluded_id, active_status, archived_status, updated_at
    ):
        await database.value.measurement_definitions.update_many(
            {
                "project_id": project_id,
                "key": key,
                "status": active_status,
                "_id": {"$ne": excluded_id},
            },
            {
                "$set": {"status": archived_status, "updated_at": updated_at},
                "$inc": {"revision": 1},
            },
        )

    async def find_release(self, release_id, project_id):
        return await database.value.releases.find_one(
            {"_id": release_id, "project_id": project_id}
        )

    async def count_releases(self, project_id, release_ids):
        return await database.value.releases.count_documents(
            {"_id": {"$in": release_ids}, "project_id": project_id}
        )

    async def find_snapshot_idempotency(self, project_id, idempotency_key):
        return await database.value.measurement_snapshots.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_snapshot(self, value, session=None):
        await database.value.measurement_snapshots.insert_one(value, session=session)

    async def find_snapshot(self, snapshot_id):
        return await database.value.measurement_snapshots.find_one({"_id": snapshot_id})

    async def list_snapshots(self, query, sort_direction, limit):
        return (
            await database.value.measurement_snapshots.find(query)
            .sort("measured_at", sort_direction)
            .to_list(limit)
        )

    async def find_latest_snapshot(self, project_id, definition_id):
        return await database.value.measurement_snapshots.find_one(
            {"project_id": project_id, "measurement_definition_id": definition_id},
            sort=[("measured_at", -1)],
        )

    async def list_active_definitions(self, project_id, status, limit):
        return await database.value.measurement_definitions.find(
            {"project_id": project_id, "status": status}
        ).to_list(limit)

    async def set_dashboard_pin(self, key, definition_id, pinned_at):
        await database.value.metric_dashboard_pins.update_one(
            key,
            {
                "$set": {
                    **key,
                    "definition_id": definition_id,
                    "pinned_at": pinned_at,
                }
            },
            upsert=True,
        )

    async def delete_dashboard_pin(self, key):
        await database.value.metric_dashboard_pins.delete_one(key)

    async def find_monitoring_snapshot(self, project_id, release_id=None):
        query = {"project_id": project_id}
        if release_id:
            query["release_id"] = release_id
        return await database.value.test_monitoring_snapshots.find_one(
            query, sort=[("snapshot_at", -1)]
        )

    async def count_collection(self, collection_name, query):
        return await database.value[collection_name].count_documents(query)

    async def list_defect_dates(self, query, projection, limit):
        return await database.value.defects.find(query, projection).to_list(limit)

    async def distinct_changed_requirements(self, project_id):
        return await database.value.requirement_versions.distinct(
            "requirement_id", {"project_id": project_id, "version": {"$gt": 1}}
        )

    async def list_regression_results(self, project_id, limit):
        return await database.value.regression_recommendations.find(
            {"project_id": project_id},
            {"selected_test_case_ids": 1, "detected_defect_ids": 1},
        ).to_list(limit)

    async def list_automation_statuses(self, query, limit):
        return await database.value.automation_executions.find(
            query, {"status": 1}
        ).to_list(limit)


measurement_repository = MeasurementRepository()
