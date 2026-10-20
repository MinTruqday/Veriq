from datetime import datetime, timezone

from pymongo import DESCENDING, ReturnDocument, UpdateOne

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationDefinition,
    AutomationRun,
    AutomationStatus,
    AutomationTrigger,
    DerivationReceipt,
    SourceFact,
)


class AutomationRepository:
    @property
    def _database(self):
        return database.mongodb[settings.AI_DB_NAME]

    async def create_run(self, run: AutomationRun) -> AutomationRun:
        payload = run.model_dump(mode="python")
        payload["_id"] = payload.pop("automation_run_id")
        await self._database.automation_runs.insert_one(payload)
        return run

    async def create_definition(self, definition: AutomationDefinition) -> AutomationDefinition:
        payload = definition.model_dump(mode="python")
        payload["_id"] = payload.pop("definition_id")
        await self._database.automation_definitions.insert_one(payload)
        return definition

    async def get_definition(self, definition_id: str) -> AutomationDefinition | None:
        payload = await self._database.automation_definitions.find_one({"_id": definition_id})
        if not payload:
            return None
        payload["definition_id"] = str(payload.pop("_id"))
        return AutomationDefinition.model_validate(payload)

    async def list_definitions(self, project_id: str, limit: int = 100) -> list[AutomationDefinition]:
        values = await self._database.automation_definitions.find({"project_id": project_id}).sort(
            [("updated_at", DESCENDING), ("_id", 1)]
        ).to_list(length=limit)
        for value in values:
            value["definition_id"] = str(value.pop("_id"))
        return [AutomationDefinition.model_validate(value) for value in values]

    async def list_enabled_definitions(
        self, project_id: str, trigger: AutomationTrigger
    ) -> list[AutomationDefinition]:
        values = await self._database.automation_definitions.find(
            {"project_id": project_id, "trigger": trigger.value, "enabled": True}
        ).sort([("updated_at", DESCENDING), ("_id", 1)]).to_list(length=100)
        for value in values:
            value["definition_id"] = str(value.pop("_id"))
        return [AutomationDefinition.model_validate(value) for value in values]

    async def patch_definition(
        self, definition_id: str, expected_revision: int, values: dict
    ) -> AutomationDefinition | None:
        values = {**values, "updated_at": datetime.now(timezone.utc)}
        result = await self._database.automation_definitions.find_one_and_update(
            {"_id": definition_id, "revision": expected_revision},
            {"$set": values, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            return None
        result["definition_id"] = str(result.pop("_id"))
        return AutomationDefinition.model_validate(result)

    async def get_run(self, automation_run_id: str) -> AutomationRun | None:
        payload = await self._database.automation_runs.find_one({"_id": automation_run_id})
        if not payload:
            return None
        payload["automation_run_id"] = str(payload.pop("_id"))
        return AutomationRun.model_validate(payload)

    async def find_event_run(self, project_id: str, source_event_id: str) -> AutomationRun | None:
        payload = await self._database.automation_runs.find_one(
            {"project_id": project_id, "source_event_id": source_event_id}
        )
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

    async def recover_interrupted_runs(self) -> list[AutomationRun]:
        values = await self._database.automation_runs.find({
            "status": AutomationStatus.RUNNING.value,
        }).to_list(length=None)
        recovered = []
        for value in values:
            latest = await self.latest_checkpoint(str(value["_id"]))
            snapshot = latest.state_snapshot if latest else None
            action_outcome_uncertain = bool(
                latest
                and latest.phase == AutomationCheckpointPhase.ACTION_STARTED
                and (
                    latest.detail.get("action") != "READ"
                    or latest.detail.get("task_has_mutation") is True
                )
            )
            can_resume = snapshot is not None and not action_outcome_uncertain
            next_status = AutomationStatus.QUEUED if can_resume else AutomationStatus.DEGRADED
            reason_code = (
                "AUTOMATION_ACTION_OUTCOME_UNCERTAIN"
                if action_outcome_uncertain
                else None
                if can_resume
                else "AUTOMATION_INTERRUPTED_WITHOUT_CHECKPOINT"
            )
            result = await self._database.automation_runs.find_one_and_update(
                {"_id": value["_id"], "revision": value["revision"]},
                {
                    "$set": {
                        "status": next_status.value,
                        "error_code": reason_code,
                        "updated_at": datetime.now(timezone.utc),
                    },
                    "$inc": {"revision": 1},
                },
                return_document=ReturnDocument.AFTER,
            )
            if result:
                result["automation_run_id"] = str(result.pop("_id"))
                run = AutomationRun.model_validate(result)
                recovered.append(run)
                await self.save_checkpoint(
                    AutomationCheckpoint(
                        automation_run_id=run.automation_run_id,
                        phase=(AutomationCheckpointPhase.QUEUED if can_resume else AutomationCheckpointPhase.FINALIZED),
                        status=next_status,
                        detail=(
                            {"reason_code": "AUTOMATION_RESUMED_FROM_CHECKPOINT", "resuming_after": snapshot.completed_phase.value}
                            if can_resume
                            else {
                                "reason_code": reason_code,
                                "retryable": not action_outcome_uncertain,
                                "task_id": latest.detail.get("task_id") if latest else None,
                                "tool_name": latest.detail.get("tool_name") if latest else None,
                            }
                        ),
                        state_snapshot=snapshot if can_resume else None,
                    )
                )
        return recovered

    async def latest_checkpoint(self, automation_run_id: str) -> AutomationCheckpoint | None:
        value = await self._database.automation_checkpoints.find_one(
            {"automation_run_id": automation_run_id},
            sort=[("created_at", DESCENDING), ("_id", DESCENDING)],
        )
        if not value:
            return None
        value["checkpoint_id"] = str(value.pop("_id"))
        return AutomationCheckpoint.model_validate(value)

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
        operations = []
        for fact in facts:
            payload = fact.model_dump(mode="python")
            payload["_id"] = payload.pop("source_fact_id")
            operations.append(
                UpdateOne(
                    {"_id": payload["_id"]},
                    {"$set": payload},
                    upsert=True,
                )
            )
        await self._database.automation_source_facts.bulk_write(operations, ordered=True)

    async def replace_provenance(
        self,
        automation_run_id: str,
        facts: list[SourceFact],
        receipt: DerivationReceipt,
    ) -> None:
        # Write the new immutable evidence before replacing the run's receipt. A
        # retry must never erase the last complete provenance record first.
        await self.save_source_facts(facts)
        await self.save_receipt(receipt)
        fact_ids = [fact.source_fact_id for fact in facts]
        await self._database.automation_source_facts.delete_many(
            {
                "automation_run_id": automation_run_id,
                "_id": {"$nin": fact_ids},
            }
        )

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
        receipt_id = payload.pop("_id")
        await self._database.automation_derivation_receipts.update_one(
            {"automation_run_id": receipt.automation_run_id},
            {"$set": payload, "$setOnInsert": {"_id": receipt_id}},
            upsert=True,
        )

    async def complete_receipt(
        self,
        automation_run_id: str,
        outcome: str,
        output_evidence_refs: list[str],
    ) -> None:
        await self._database.automation_derivation_receipts.update_one(
            {"automation_run_id": automation_run_id},
            {
                "$set": {
                    "outcome": outcome,
                    "output_evidence_refs": output_evidence_refs,
                }
            },
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
