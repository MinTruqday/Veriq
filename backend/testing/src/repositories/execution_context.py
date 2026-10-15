from src.core.database import database


class ExecutionContextRepository:
    async def project_settings(self, project_id):
        return await database.value.projects.find_one({"_id": project_id}, {"settings": 1})

    async def approved_completion_exists(self, project_id, release_id, statuses):
        return bool(
            await database.value.test_completion_reports.find_one(
                {
                    "project_id": project_id,
                    "release_id": release_id,
                    "status": {"$in": statuses},
                },
                {"_id": 1},
            )
        )

    async def list_approved_test_plan_scopes(self, project_id, release_id):
        return await database.value.test_plans.find(
            {
                "project_id": project_id,
                "release_id": release_id,
                "status": "APPROVED",
            },
            {"_id": 1, "approved_snapshot": 1, "requirement_version_ids": 1},
        ).to_list(1000)

    async def list_adequacy_assessments(self, project_id, requirement_version_ids):
        return await database.value.test_adequacy_assessments.find(
            {
                "project_id": project_id,
                "requirement_version_id": {"$in": requirement_version_ids},
            }
        ).to_list(len(requirement_version_ids))

    async def list_releases(self, query, limit=500):
        return await database.value.releases.find(query).sort(
            "updated_at", -1
        ).to_list(limit)

    async def insert_release(self, value):
        await database.value.releases.insert_one(value)
        return value

    async def set_current_release(self, project_id, release_id, active_status):
        await database.value.releases.update_many(
            {
                "project_id": project_id,
                "_id": {"$ne": release_id},
                "status": active_status,
            },
            {"$set": {"is_current": False}},
        )
        await database.value.releases.update_one(
            {"_id": release_id}, {"$set": {"is_current": True}}
        )

    async def list_builds(self, query, limit=500):
        return await database.value.builds.find(query).sort(
            "created_at", -1
        ).to_list(limit)

    async def insert_build(self, value):
        await database.value.builds.insert_one(value)
        return value

    async def set_current_build(self, project_id, build_id):
        return await database.value.builds.update_many(
            {"project_id": project_id, "_id": {"$ne": build_id}},
            {"$set": {"is_current": False}},
        )

    async def list_active_environments(self, project_id, archived_status, limit=500):
        return await database.value.test_environments.find(
            {"project_id": project_id, "status": {"$ne": archived_status}}
        ).sort("updated_at", -1).to_list(limit)

    async def insert_environment(self, value):
        await database.value.test_environments.insert_one(value)
        return value


execution_context_repository = ExecutionContextRepository()
