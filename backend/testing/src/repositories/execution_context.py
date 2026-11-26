from src.core.database import database


class ExecutionContextRepository:
    async def advance_release_gate_revision(
        self,
        project_id,
        release_id,
        session=None,
        expected_revision=None,
        required_status=None,
        require_open=False,
    ):
        query = {"_id": release_id, "project_id": project_id}
        if required_status:
            query["status"] = required_status
        elif require_open:
            query["status"] = {"$in": ["PLANNED", "ACTIVE"]}
        if expected_revision is not None:
            if expected_revision == 0:
                query["$or"] = [
                    {"gate_revision": 0},
                    {"gate_revision": {"$exists": False}},
                ]
            else:
                query["gate_revision"] = expected_revision
        result = await database.value.releases.update_one(
            query,
            {"$inc": {"gate_revision": 1}},
            **({"session": session} if session is not None else {}),
        )
        return result.matched_count == 1

    async def project_settings(self, project_id):
        return await database.value.projects.find_one({"_id": project_id}, {"settings": 1})

    async def list_open_blocking_defects(self, project_id, release_id, session=None):
        pipeline = [
            {
                "$match": {
                    "project_id": project_id,
                    "status": {
                        "$in": [
                            "NEW",
                            "CONFIRMED",
                            "IN_PROGRESS",
                            "READY_FOR_RETEST",
                            "REOPENED",
                        ]
                    },
                    "severity_blocks_release": True,
                }
            },
            {
                "$lookup": {
                    "from": "test_results",
                    "let": {"result_id": "$linked_test_result_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$_id", "$$result_id"]},
                                        {"$eq": ["$project_id", project_id]},
                                    ]
                                }
                            }
                        },
                        {"$project": {"_id": 0, "test_run_id": 1}},
                    ],
                    "as": "linked_result",
                }
            },
            {
                "$unwind": {
                    "path": "$linked_result",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            {
                "$lookup": {
                    "from": "test_runs",
                    "let": {"run_id": "$linked_result.test_run_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$_id", "$$run_id"]},
                                        {"$eq": ["$project_id", project_id]},
                                        {"$eq": ["$release_id", release_id]},
                                    ]
                                }
                            }
                        },
                        {"$project": {"_id": 1}},
                    ],
                    "as": "linked_run",
                }
            },
            {
                "$match": {
                    "$or": [
                        {"release_id": release_id},
                        {"linked_run.0": {"$exists": True}},
                    ]
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "defect_key": 1,
                    "status": 1,
                    "severity": 1,
                }
            },
            {"$limit": 1000},
        ]
        options = {"session": session} if session is not None else {}
        return await database.value.defects.aggregate(pipeline, **options).to_list(1000)

    async def list_releases(self, query, limit=500):
        return await database.value.releases.find(query).sort(
            "updated_at", -1
        ).to_list(limit)

    async def find_release(self, project_id, release_id):
        return await database.value.releases.find_one(
            {"_id": release_id, "project_id": project_id}
        )

    async def insert_release(self, value, session=None):
        await database.value.releases.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def set_current_release(self, project_id, release_id, active_status, session=None):
        await database.value.releases.update_many(
            {
                "project_id": project_id,
                "_id": {"$ne": release_id},
                "status": active_status,
            },
            {"$set": {"is_current": False}},
            **({"session": session} if session is not None else {}),
        )
        await database.value.releases.update_one(
            {"_id": release_id},
            {"$set": {"is_current": True}},
            **({"session": session} if session is not None else {}),
        )

    async def list_builds(self, query, limit=500):
        return await database.value.builds.find(query).sort(
            "created_at", -1
        ).to_list(limit)

    async def insert_build(self, value):
        await database.value.builds.insert_one(value)
        return value

    async def set_current_build(self, project_id, build_id, session=None):
        await database.value.builds.update_many(
            {"project_id": project_id, "_id": {"$ne": build_id}},
            {"$set": {"is_current": False}},
            **({"session": session} if session is not None else {}),
        )
        result = await database.value.builds.update_one(
            {"project_id": project_id, "_id": build_id, "status": "ACTIVE"},
            {"$set": {"is_current": True}},
            **({"session": session} if session is not None else {}),
        )
        return result.matched_count == 1

    async def list_active_environments(self, project_id, archived_status, limit=500):
        return await database.value.test_environments.find(
            {"project_id": project_id, "status": {"$ne": archived_status}}
        ).sort("updated_at", -1).to_list(limit)

    async def insert_environment(self, value):
        await database.value.test_environments.insert_one(value)
        return value


execution_context_repository = ExecutionContextRepository()
