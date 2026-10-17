from datetime import datetime, timezone

from pymongo import DESCENDING, ReturnDocument

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.schemas.automation import AutomationCheckpoint, AutomationRun, DerivationReceipt, SourceFact


class AutomationRepository:
    @property
    def _database(self):
        return database.mongodb[settings.AI_DB_NAME]

    async def create_run(self, run: AutomationRun) -> AutomationRun:
        payload = run.model_dump(mode="python")
        payload["_id"] = payload.pop("automation_run_id")
        await self._database.automation_runs.insert_one(payload)
        return run

    async def get_run(self, automation_run_id: str) -> AutomationRun | None:
        payload = await self._database.automation_runs.find_one({"_id": automation_run_id})
        if not payload:
            return None
        payload["automation_run_id"] = str(payload.pop("_id"))
        return AutomationRun.model_validate(payload)

    async def list_runs(self, project_id: str, limit: int) -> list[AutomationRun]:
        values = await self._database.automation_runs.find({"project_id": project_id}).sort(
            "updated_at", DESCENDING
        ).to_list(length=limit)
        for value in values:
            value["automation_run_id"] = str(value.pop("_id"))
        return [AutomationRun.model_validate(value) for value in values]

    async def transition(
        self,
        automation_run_id: str,
        expected_revision: int,
        values: dict,
    ) -> AutomationRun | None:
        values = {**values, "updated_at": datetime.now(timezone.utc)}
        result = await self._database.automation_runs.find_one_and_update(
            {"_id": automation_run_id, "revision": expected_revision},
            {"$set": values, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            return None
        result["automation_run_id"] = str(result.pop("_id"))
        return AutomationRun.model_validate(result)

    async def save_checkpoint(self, checkpoint: AutomationCheckpoint) -> None:
        payload = checkpoint.model_dump(mode="python")
        payload["_id"] = payload.pop("checkpoint_id")
        await self._database.automation_checkpoints.insert_one(payload)

    async def list_checkpoints(self, automation_run_id: str) -> list[AutomationCheckpoint]:
        values = await self._database.automation_checkpoints.find(
            {"automation_run_id": automation_run_id}
        ).sort("created_at", 1).to_list(length=None)
        for value in values:
            value["checkpoint_id"] = str(value.pop("_id"))
        return [AutomationCheckpoint.model_validate(value) for value in values]

    async def save_source_facts(self, facts: list[SourceFact]) -> None:
        if not facts:
            return
        values = []
        for fact in facts:
            payload = fact.model_dump(mode="python")
            payload["_id"] = payload.pop("source_fact_id")
            values.append(payload)
        await self._database.automation_source_facts.insert_many(values)

    async def clear_provenance(self, automation_run_id: str) -> None:
        await self._database.automation_source_facts.delete_many(
            {"automation_run_id": automation_run_id}
        )
        await self._database.automation_derivation_receipts.delete_many(
            {"automation_run_id": automation_run_id}
        )

    async def save_receipt(self, receipt: DerivationReceipt) -> None:
        payload = receipt.model_dump(mode="python")
        payload["_id"] = payload.pop("receipt_id")
        await self._database.automation_derivation_receipts.replace_one(
            {"_id": payload["_id"]}, payload, upsert=True
        )

    async def get_receipt(self, automation_run_id: str) -> DerivationReceipt | None:
        payload = await self._database.automation_derivation_receipts.find_one(
            {"automation_run_id": automation_run_id}
        )
        if not payload:
            return None
        payload["receipt_id"] = str(payload.pop("_id"))
        return DerivationReceipt.model_validate(payload)

    async def list_source_facts(self, automation_run_id: str) -> list[SourceFact]:
        values = await self._database.automation_source_facts.find(
            {"automation_run_id": automation_run_id}
        ).sort("created_at", 1).to_list(length=None)
        for value in values:
            value["source_fact_id"] = str(value.pop("_id"))
        return [SourceFact.model_validate(value) for value in values]


automation_repository = AutomationRepository()
