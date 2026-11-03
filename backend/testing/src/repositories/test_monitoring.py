from pymongo import ReturnDocument

from src.core.database import database


class TestMonitoringRepository:
    async def find_test_plan(self, test_plan_id, project_id):
        return await database.value.test_plans.find_one(
            {"_id": test_plan_id, "project_id": project_id}
        )

    async def release_exists(self, release_id, project_id):
        return bool(
            await database.value.releases.find_one(
                {"_id": release_id, "project_id": project_id}, {"_id": 1}
            )
        )

    async def find_snapshot(self, snapshot_id, project_id=None):
        query = {"_id": snapshot_id}
        if project_id:
            query["project_id"] = project_id
        return await database.value.test_monitoring_snapshots.find_one(query)

    async def find_snapshot_by_idempotency(self, project_id, idempotency_key):
        return await database.value.test_monitoring_snapshots.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_latest_snapshot(self, project_id, test_plan_id, release_id):
        return await database.value.test_monitoring_snapshots.find_one(
            {
                "project_id": project_id,
                "test_plan_id": test_plan_id,
                "release_id": release_id,
            },
            sort=[("snapshot_at", -1)],
        )

    async def list_snapshots(self, project_id, test_plan_id=None, release_id=None, limit=100):
        query = {"project_id": project_id}
        if test_plan_id:
            query["test_plan_id"] = test_plan_id
        if release_id:
            query["release_id"] = release_id
        return await database.value.test_monitoring_snapshots.find(query).sort(
            "snapshot_at", -1
        ).limit(limit).to_list(limit)

    async def insert_snapshot(self, snapshot, session=None):
        await database.value.test_monitoring_snapshots.insert_one(snapshot, session=session)
        return snapshot

    async def insert_gate_evaluation(self, evaluation, session=None):
        await database.value.quality_gate_evaluations.insert_one(evaluation, session=session)
        return evaluation

    async def list_overrides(self, snapshot_id, limit):
        return await database.value.test_monitoring_overrides.find(
            {"snapshot_id": snapshot_id}
        ).sort("created_at", 1).to_list(limit)

    async def insert_override(self, value):
        await database.value.test_monitoring_overrides.insert_one(value)
        return value

    async def find_active_membership(
        self, project_id, user_id, active_status, projection=None
    ):
        return await database.value.project_members.find_one(
            {"project_id": project_id, "user_id": user_id, "status": active_status},
            projection,
        )

    async def insert_control_action(self, value):
        await database.value.test_control_actions.insert_one(value)
        return value

    async def find_control_action(self, action_id):
        return await database.value.test_control_actions.find_one({"_id": action_id})

    async def update_control_action(self, action_id, project_id, revision, changes, updated_at):
        cleaned = {key: value for key, value in changes.items() if value is not None}
        cleaned["updated_at"] = updated_at
        return await database.value.test_control_actions.find_one_and_update(
            {"_id": action_id, "project_id": project_id, "revision": revision},
            {"$set": cleaned, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def list_control_actions(self, project_id, snapshot_id=None, status=None, limit=500):
        query = {"project_id": project_id}
        if snapshot_id:
            query["snapshot_id"] = snapshot_id
        if status:
            query["status"] = status
        return await database.value.test_control_actions.find(query).sort(
            "updated_at", -1
        ).limit(limit).to_list(limit)

    async def list_test_runs(self, project_id, test_plan_id, release_id, limit):
        query = {"project_id": project_id, "test_plan_id": test_plan_id}
        if release_id:
            query["release_id"] = release_id
        return await database.value.test_runs.find(query).to_list(limit)

    async def list_test_results(self, project_id, run_ids, limit):
        if not run_ids:
            return []
        return await database.value.test_results.find(
            {"project_id": project_id, "test_run_id": {"$in": run_ids}}
        ).to_list(limit)

    async def list_defects(self, project_id, release_id, limit):
        query = {"project_id": project_id}
        if release_id:
            query["release_id"] = release_id
        return await database.value.defects.find(query).to_list(limit)

    async def list_baselined_requirements(self, project_id, baselined_status, limit):
        return await database.value.requirements.find(
            {"project_id": project_id, "status": baselined_status},
            {"current_version_id": 1},
        ).to_list(limit)

    async def list_acceptance_criteria(self, project_id, version_ids, limit):
        if not version_ids:
            return []
        return await database.value.acceptance_criteria.find(
            {"project_id": project_id, "requirement_version_id": {"$in": version_ids}},
            {"_id": 1},
        ).to_list(limit)

    async def list_approved_conditions(self, project_id, approved_status, limit):
        return await database.value.test_conditions.find(
            {"project_id": project_id, "status": approved_status},
            {"_id": 1, "risk": 1, "revision": 1, "snapshot_hash": 1},
        ).to_list(limit)

    async def list_test_case_versions(self, project_id, version_ids, limit):
        if not version_ids:
            return []
        return await database.value.test_case_versions.find(
            {"project_id": project_id, "_id": {"$in": version_ids}},
            {
                "requirement_version_ids": 1,
                "acceptance_criterion_ids": 1,
                "test_condition_ids": 1,
                "source_evidence": 1,
                "risk": 1,
            },
        ).to_list(limit)

    async def list_api_operations(self, project_id, limit):
        return await database.value.api_operations.find(
            {"project_id": project_id}, {"_id": 1}
        ).to_list(limit)

    async def list_approved_non_functional_plans(
        self, project_id, approved_status, limit
    ):
        return await database.value.non_functional_test_plans.find(
            {"project_id": project_id, "status": approved_status},
            {"_id": 1, "test_condition_ids": 1, "test_case_version_ids": 1, "revision": 1},
        ).to_list(limit)

    async def count_requirement_changes(self, project_id, since):
        query = {"project_id": project_id}
        if since:
            query["created_at"] = {"$gt": since}
        return await database.value.requirement_change_sets.count_documents(query)

    async def count_pending_impact_analyses(self, project_id, terminal_statuses):
        return await database.value.impact_analyses.count_documents(
            {"project_id": project_id, "status": {"$nin": terminal_statuses}}
        )

    async def count_pending_maintenance_proposals(self, project_id, statuses):
        return await database.value.maintenance_proposals.count_documents(
            {"project_id": project_id, "status": {"$in": statuses}}
        )

    async def count_stale_test_cases(self, project_id, status):
        return await database.value.test_cases.count_documents(
            {"project_id": project_id, "status": status}
        )

    async def list_environment_incidents(
        self, project_id, statuses, release_scoped, build_ids, run_ids, limit
    ):
        query = {"project_id": project_id, "status": {"$in": statuses}}
        if release_scoped:
            query["$or"] = [
                {"build_id": {"$in": build_ids}},
                {"affected_run_ids": {"$in": run_ids}},
            ]
        return await database.value.environment_incidents.find(query).to_list(limit)


test_monitoring_repository = TestMonitoringRepository()
