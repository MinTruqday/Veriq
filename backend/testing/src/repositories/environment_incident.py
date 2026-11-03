from pymongo import ReturnDocument

from src.core.database import database


class EnvironmentIncidentRepository:
    async def find_environment(self, environment_id, project_id, archived_status):
        return await database.value.test_environments.find_one(
            {"_id": environment_id, "project_id": project_id, "status": {"$ne": archived_status}}
        )

    async def find_build(self, build_id, project_id):
        return await database.value.builds.find_one({"_id": build_id, "project_id": project_id})

    async def count_environment_runs(self, run_ids, project_id, environment_id):
        return await database.value.test_runs.count_documents(
            {"_id": {"$in": run_ids}, "project_id": project_id, "environment_id": environment_id}
        )

    async def find_active_member(self, project_id, user_id, active_status):
        return await database.value.project_members.find_one(
            {"project_id": project_id, "user_id": user_id, "status": active_status}
        )

    async def find_incident(self, incident_id, project_id=None):
        query = {"_id": incident_id}
        if project_id:
            query["project_id"] = project_id
        return await database.value.environment_incidents.find_one(query)

    async def list_incidents(self, query, limit):
        return await database.value.environment_incidents.find(query).sort(
            "observed_at", -1
        ).to_list(limit)

    async def find_by_idempotency_key(self, project_id, idempotency_key):
        return await database.value.environment_incidents.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def next_sequence(self, counter_id):
        return await database.value.counters.find_one_and_update(
            {"_id": counter_id},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def insert_incident(self, value, session=None):
        await database.value.environment_incidents.insert_one(value, session=session)
        return value

    async def mark_environment_unavailable(
        self, environment_id, expected_revision, incident_id, availability, updated_at, session=None
    ):
        query = {"_id": environment_id}
        if expected_revision is not None:
            query["revision"] = expected_revision
        return await database.value.test_environments.update_one(
            query,
            {
                "$set": {
                    "availability": availability,
                    "active_incident_id": incident_id,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
            session=session,
        )

    async def pause_runs(
        self, run_ids, project_id, incident_id, in_progress_status, updated_at, session=None
    ):
        await database.value.test_runs.update_many(
            {"_id": {"$in": run_ids}, "project_id": project_id, "status": in_progress_status},
            {
                "$set": {
                    "execution_paused": True,
                    "paused_by_environment_incident_id": incident_id,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
            session=session,
        )

    async def update_incident(self, incident_id, revision, statuses, changes):
        query = {"_id": incident_id, "revision": revision}
        if isinstance(statuses, str):
            query["status"] = statuses
        else:
            query["status"] = {"$in": statuses}
        return await database.value.environment_incidents.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def count_other_active_blocking(self, project_id, environment_id, incident_id, severities, statuses):
        return await database.value.environment_incidents.count_documents(
            {
                "project_id": project_id,
                "environment_id": environment_id,
                "severity": {"$in": severities},
                "status": {"$in": statuses},
                "_id": {"$ne": incident_id},
            }
        )

    async def restore_environment(
        self, environment_id, availability, archived_status, updated_at
    ):
        await database.value.test_environments.update_one(
            {"_id": environment_id, "status": {"$ne": archived_status}},
            {
                "$set": {
                    "availability": availability,
                    "active_incident_id": None,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
        )

    async def resume_runs(self, project_id, incident_id, updated_at):
        await database.value.test_runs.update_many(
            {"project_id": project_id, "paused_by_environment_incident_id": incident_id},
            {
                "$set": {
                    "execution_paused": False,
                    "paused_by_environment_incident_id": None,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
        )


environment_incident_repository = EnvironmentIncidentRepository()
