from src.core.database import database


class QualityRepository:
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
