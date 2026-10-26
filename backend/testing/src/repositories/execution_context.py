import asyncio

from src.core.database import database
from src.schemas.test_monitoring import source_fingerprint


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

    async def find_approved_completion(self, project_id, release_id, statuses, session=None):
        return await database.value.test_completion_reports.find_one(
            {
                "project_id": project_id,
                "release_id": release_id,
                "status": {"$in": statuses},
            },
            sort=[("approved_at", -1), ("created_at", -1)],
            **({"session": session} if session is not None else {}),
        )

    async def list_approved_completions(self, project_id, release_id, statuses, session=None):
        return await database.value.test_completion_reports.find(
            {
                "project_id": project_id,
                "release_id": release_id,
                "status": {"$in": statuses},
            },
            **({"session": session} if session is not None else {}),
        ).sort([("approved_at", -1), ("created_at", -1)]).to_list(None)

    async def list_automation_completions(self, project_id, release_id, automation_run_id, session=None):
        return await database.value.test_completion_reports.find(
            {
                "project_id": project_id,
                "release_id": release_id,
                "automation_run_id": automation_run_id,
                "status": "DRAFT",
            },
            **({"session": session} if session is not None else {}),
        ).sort("created_at", -1).to_list(None)

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
                    "severity": {
                        "$in": ["blocker", "critical", "BLOCKER", "CRITICAL"]
                    },
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

    async def list_active_member_ids(self, project_id, user_ids, session=None):
        if not user_ids:
            return []
        members = await database.value.project_members.find(
            {
                "project_id": project_id,
                "user_id": {"$in": sorted(set(user_ids))},
                "status": "ACTIVE",
            },
            {"_id": 0, "user_id": 1},
            **({"session": session} if session is not None else {}),
        ).to_list(len(set(user_ids)))
        return [item["user_id"] for item in members]

    async def release_evidence_changed_since(self, project_id, release_id, run_ids, since, session=None):
        options = {"session": session} if session is not None else {}
        checks = [
            database.value.test_runs.find_one(
                {"project_id": project_id, "release_id": release_id, "updated_at": {"$gt": since}},
                {"_id": 1},
                **options,
            ),
            database.value.defects.find_one(
                {"project_id": project_id, "release_id": release_id, "updated_at": {"$gt": since}},
                {"_id": 1},
                **options,
            ),
            database.value.test_monitoring_snapshots.find_one(
                {"project_id": project_id, "release_id": release_id, "created_at": {"$gt": since}},
                {"_id": 1},
                **options,
            ),
            database.value.test_plans.find_one(
                {
                    "project_id": project_id,
                    "release_id": release_id,
                    "status": "APPROVED",
                    "updated_at": {"$gt": since},
                },
                {"_id": 1},
                **options,
            ),
        ]
        if run_ids:
            checks.append(
                database.value.test_results.find_one(
                    {
                        "project_id": project_id,
                        "test_run_id": {"$in": sorted(set(run_ids))},
                        "updated_at": {"$gt": since},
                    },
                    {"_id": 1},
                    **options,
                )
            )
        results = await asyncio.gather(*checks)
        return any(results)

    async def release_snapshot_sources_changed(
        self,
        project_id,
        snapshot_id,
        release_id=None,
        test_plan_id=None,
        run_ids=None,
        session=None,
    ):
        options = {"session": session} if session is not None else {}
        snapshot = await database.value.test_monitoring_snapshots.find_one(
            {"_id": snapshot_id, "project_id": project_id}, **options
        )
        if not snapshot:
            return True
        if (
            (release_id and snapshot.get("release_id") != release_id)
            or (test_plan_id and snapshot.get("test_plan_id") != test_plan_id)
        ):
            return True
        source_state = snapshot.get("source_state")
        if (
            not isinstance(source_state, dict)
            or not source_state
            or snapshot.get("source_fingerprint") != source_fingerprint(source_state)
        ):
            return True
        snapshot_run_ids = sorted(
            item.get("id")
            for item in source_state.get("runs", [])
            if isinstance(item, dict) and item.get("id")
        )
        if run_ids is not None and snapshot_run_ids != sorted(set(run_ids)):
            return True

        specifications = (
            ("runs", "test_runs", {"revision": "revision", "status": "status", "scope_hash": "frozen_scope_hash"}),
            ("results", "test_results", {"revision": "revision", "status": "status"}),
            ("defects", "defects", {"revision": "revision", "status": "status", "severity": "severity"}),
            ("conditions", "test_conditions", {"revision": "revision", "hash": "snapshot_hash"}),
            ("nfr_plans", "non_functional_test_plans", {"revision": "revision"}),
            ("environment_incidents", "environment_incidents", {"revision": "revision", "status": "status", "severity": "severity", "environment_id": "environment_id", "build_id": "build_id"}),
        )
        for state_key, collection_name, field_map in specifications:
            states = source_state.get(state_key, [])
            if not isinstance(states, list):
                return True
            keyed = [item for item in states if isinstance(item, dict) and item.get("id")]
            if len(keyed) != len(states):
                return True
            if not keyed:
                continue
            records = await getattr(database.value, collection_name).find(
                {"_id": {"$in": [item["id"] for item in keyed]}, "project_id": project_id},
                **options,
            ).to_list(len(keyed))
            by_id = {item["_id"]: item for item in records}
            for state in keyed:
                current = by_id.get(state["id"])
                if not current or any(
                    current.get(record_field) != state.get(snapshot_field)
                    for snapshot_field, record_field in field_map.items()
                ):
                    return True

        plan_state = source_state.get("plan")
        if not isinstance(plan_state, dict) or not plan_state.get("id"):
            return True
        plan = await database.value.test_plans.find_one(
            {"_id": plan_state["id"], "project_id": project_id},
            **options,
        )
        if (
            not plan
            or plan.get("revision") != plan_state.get("revision")
            or plan.get("approved_snapshot_hash") != plan_state.get("hash")
        ):
            return True

        run_query = {"project_id": project_id, "test_plan_id": plan_state["id"]}
        if release_id:
            run_query["release_id"] = release_id
        current_run_ids = sorted(
            item["_id"]
            for item in await database.value.test_runs.find(
                run_query, {"_id": 1}, **options
            ).to_list(None)
        )
        if current_run_ids != snapshot_run_ids:
            return True

        expected_result_ids = sorted(
            item.get("id")
            for item in source_state.get("results", [])
            if isinstance(item, dict) and item.get("id")
        )
        current_result_ids = sorted(
            item["_id"]
            for item in await database.value.test_results.find(
                {
                    "project_id": project_id,
                    "test_run_id": {"$in": snapshot_run_ids},
                },
                {"_id": 1},
                **options,
            ).to_list(None)
        ) if snapshot_run_ids else []
        if current_result_ids != expected_result_ids:
            return True

        defect_query = {"project_id": project_id}
        if release_id:
            defect_query["release_id"] = release_id
        expected_defect_ids = sorted(
            item.get("id")
            for item in source_state.get("defects", [])
            if isinstance(item, dict) and item.get("id")
        )
        current_defect_ids = sorted(
            item["_id"]
            for item in await database.value.defects.find(
                defect_query, {"_id": 1}, **options
            ).to_list(None)
        )
        if current_defect_ids != expected_defect_ids:
            return True

        plan_snapshot = plan.get("approved_snapshot") or {}
        scoped_version_ids = sorted(
            set(plan_snapshot.get("requirement_version_ids") or [])
        )
        if not scoped_version_ids:
            return True
        scoped_versions = await database.value.requirement_versions.find(
            {
                "_id": {"$in": scoped_version_ids},
                "project_id": project_id,
            },
            {"_id": 1, "requirement_id": 1},
            **options,
        ).to_list(len(scoped_version_ids))
        if len(scoped_versions) != len(scoped_version_ids):
            return True
        requirement_ids = sorted(
            {item.get("requirement_id") for item in scoped_versions if item.get("requirement_id")}
        )
        requirements = await database.value.requirements.find(
            {
                "_id": {"$in": requirement_ids},
                "project_id": project_id,
                "status": "BASELINED",
            },
            {"_id": 1, "current_version_id": 1},
            **options,
        ).to_list(len(requirement_ids))
        current_scoped_versions = [
            item.get("current_version_id") for item in requirements
        ]
        if (
            len(requirements) != len(requirement_ids)
            or any(not item for item in current_scoped_versions)
            or sorted(current_scoped_versions) != scoped_version_ids
        ):
            return True

        current_api_operations = await database.value.api_operations.find(
            {"project_id": project_id}, {"_id": 1}, **options
        ).to_list(20000)
        if sorted(item["_id"] for item in current_api_operations) != sorted(
            source_state.get("api_operations", [])
        ):
            return True
        return False

    async def list_approved_test_plan_scopes(self, project_id, release_id, session=None):
        return await database.value.test_plans.find(
            {
                "project_id": project_id,
                "release_id": release_id,
                "status": "APPROVED",
            },
            **({"session": session} if session is not None else {}),
        ).to_list(None)

    async def list_adequacy_assessments(self, project_id, requirement_version_ids, session=None):
        return await database.value.test_adequacy_assessments.find(
            {
                "project_id": project_id,
                "requirement_version_id": {"$in": requirement_version_ids},
            },
            **({"session": session} if session is not None else {}),
        ).to_list(len(requirement_version_ids))

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
