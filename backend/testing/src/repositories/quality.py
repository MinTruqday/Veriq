from pymongo import ReturnDocument

from src.core.database import database


class QualityRepository:
    async def find_evaluation(self, evaluation_id):
        return await database.value.product_quality_evaluations.find_one(
            {"_id": evaluation_id}
        )

    async def list_evaluations(self, query, limit):
        return await database.value.product_quality_evaluations.find(query).sort(
            "created_at", -1
        ).to_list(limit)

    async def find_evaluation_by_idempotency_key(self, project_id, idempotency_key):
        return await database.value.product_quality_evaluations.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_release(self, release_id, project_id):
        return await database.value.releases.find_one(
            {"_id": release_id, "project_id": project_id}
        )

    async def find_build(self, build_id, project_id):
        return await database.value.builds.find_one(
            {"_id": build_id, "project_id": project_id}
        )

    async def find_monitoring_snapshot(self, snapshot_id, project_id, release_id):
        return await database.value.test_monitoring_snapshots.find_one(
            {"_id": snapshot_id, "project_id": project_id, "release_id": release_id}
        )

    async def list_measurement_snapshots(self, snapshot_ids, project_id, limit):
        return await database.value.measurement_snapshots.find(
            {"_id": {"$in": snapshot_ids}, "project_id": project_id}
        ).to_list(limit)

    async def find_test_plan(self, plan_id, project_id):
        return await database.value.test_plans.find_one(
            {"_id": plan_id, "project_id": project_id}
        )

    async def find_strategy(self, strategy_id, project_id):
        return await database.value.test_strategies.find_one(
            {"_id": strategy_id, "project_id": project_id}
        )

    async def find_gate_for_project(self, snapshot_id, project_id):
        return await database.value.quality_gate_evaluations.find_one(
            {"snapshot_id": snapshot_id, "project_id": project_id}
        )

    async def list_unresolved_defects(self, project_id, release_id, excluded_statuses, limit):
        return await database.value.defects.find(
            {
                "project_id": project_id,
                "release_id": release_id,
                "status": {"$nin": excluded_statuses},
            },
            {"_id": 1, "key": 1, "severity": 1, "status": 1, "title": 1},
        ).to_list(limit)

    async def find_latest_decision(self, snapshot_id, project_id):
        return await database.value.quality_decisions.find_one(
            {"snapshot_id": snapshot_id, "project_id": project_id},
            sort=[("decided_at", -1)],
        )

    async def insert_evaluation(self, value, session=None):
        await database.value.product_quality_evaluations.insert_one(value, session=session)
        return value

    async def update_evaluation(self, query, update):
        return await database.value.product_quality_evaluations.find_one_and_update(
            query, update, return_document=ReturnDocument.AFTER
        )

    async def find_active_member(self, project_id, user_id, active_status):
        return await database.value.project_members.find_one(
            {"project_id": project_id, "user_id": user_id, "status": active_status}
        )

    async def find_gate(self, snapshot_id):
        return await database.value.quality_gate_evaluations.find_one(
            {"snapshot_id": snapshot_id}
        )

    async def list_decisions(self, query, limit=1000):
        return await database.value.quality_decisions.find(query).sort(
            "decided_at", -1
        ).to_list(limit)

    async def find_decision_by_idempotency_key(self, project_id, idempotency_key):
        return await database.value.quality_decisions.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_decision(self, decision_id, project_id):
        return await database.value.quality_decisions.find_one(
            {"_id": decision_id, "project_id": project_id}
        )

    async def insert_decision(self, value, session=None):
        await database.value.quality_decisions.insert_one(value, session=session)
        return value


quality_repository = QualityRepository()
