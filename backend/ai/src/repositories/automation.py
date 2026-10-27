import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import DESCENDING, ReturnDocument, UpdateOne
from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.runtime.limits import limits
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationDefinition,
    AutomationRun,
    AutomationStatus,
    AutomationTrigger,
    BlueprintSourceRevision,
    DerivationReceipt,
    ProjectTestabilityBlueprint,
    SourceFact,
)


class AutomationRepository:
    @property
    def _database(self):
        return database.mongodb[settings.AI_DB_NAME]

    async def create_run_with_checkpoint(
        self,
        run: AutomationRun,
        *,
        phase: AutomationCheckpointPhase,
        detail: dict[str, Any] | None = None,
    ) -> AutomationRun:
        payload = run.model_dump(mode="python")
        payload["_id"] = payload.pop("automation_run_id")
        payload["checkpoint_sequence"] = 1
        checkpoint = AutomationCheckpoint(
            automation_run_id=run.automation_run_id,
            checkpoint_sequence=1,
            phase=phase,
            status=run.status,
            detail=detail or {},
        )
        checkpoint_payload = checkpoint.model_dump(mode="python")
        checkpoint_payload["_id"] = checkpoint_payload.pop("checkpoint_id")

        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                await self._database.automation_runs.insert_one(payload, session=session)
                await self._database.automation_checkpoints.insert_one(
                    checkpoint_payload,
                    session=session,
                )
        return run.model_copy(update={"checkpoint_sequence": 1})

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

    async def list_incomplete_document_ingestion_runs(
        self, document_id: str
    ) -> list[AutomationRun]:
        prefix = re.escape(f"requirement-document:{document_id}:")
        values = await self._database.automation_runs.find(
            {
                "trigger": AutomationTrigger.DOCUMENT_INGESTED,
                "source_event_id": {"$regex": f"^{prefix}"},
                "status": {
                    "$ne": AutomationStatus.COMPLETED
                },
            }
        ).sort("created_at", 1).to_list(length=None)
        runs = []
        for value in values:
            value["automation_run_id"] = str(value.pop("_id"))
            runs.append(AutomationRun.model_validate(value))
        return runs

    async def list_runs(
        self,
        project_id: str,
        limit: int,
        requester_user_id: str | None = None,
    ) -> list[AutomationRun]:
        query = {"project_id": project_id}
        if requester_user_id is not None:
            query["requester_user_id"] = requester_user_id
        values = await self._database.automation_runs.find(query).sort(
            "updated_at", DESCENDING
        ).to_list(length=limit)
        for value in values:
            value["automation_run_id"] = str(value.pop("_id"))
        return [AutomationRun.model_validate(value) for value in values]

    async def list_child_runs(
        self, parent_run_id: str, project_id: str, requester_user_id: str, limit: int
    ) -> list[AutomationRun]:
        values = await self._database.automation_runs.find(
            {
                "project_id": project_id,
                "requester_user_id": requester_user_id,
                "constraints.parent_automation_run_id": parent_run_id,
            }
        ).sort([("created_at", 1), ("_id", 1)]).to_list(length=limit)
        for value in values:
            value["automation_run_id"] = str(value.pop("_id"))
        return [AutomationRun.model_validate(value) for value in values]

    async def transition_with_checkpoint(
        self,
        automation_run_id: str,
        expected_revision: int,
        values: dict,
        *,
        phase: AutomationCheckpointPhase,
        detail: dict,
        state_snapshot=None,
        recovery_lease_expired_before: datetime | None = None,
        legacy_recovery_cutoff: datetime | None = None,
        require_live_worker_lease: bool = False,
    ) -> AutomationRun | None:
        values = {**values, "updated_at": datetime.now(timezone.utc)}
        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                run_filter: dict[str, Any] = {
                    "_id": automation_run_id,
                    "revision": expected_revision,
                }
                if recovery_lease_expired_before is not None:
                    run_filter["status"] = AutomationStatus.RUNNING.value
                    recovery_branches = [
                        {
                            "worker_lease_expires_at": {
                                "$type": "date",
                                "$lte": recovery_lease_expired_before,
                            }
                        }
                    ]
                    if legacy_recovery_cutoff is not None:
                        recovery_branches.append(
                            {
                                "worker_lease_expires_at": None,
                                "updated_at": {"$lte": legacy_recovery_cutoff},
                            }
                        )
                    run_filter["$and"] = [{"$or": recovery_branches}]
                if require_live_worker_lease:
                    run_filter["status"] = AutomationStatus.RUNNING.value
                    run_filter["worker_lease_expires_at"] = {"$gt": values["updated_at"]}
                result = await self._database.automation_runs.find_one_and_update(
                    run_filter,
                    {
                        "$set": values,
                        "$inc": {"revision": 1, "checkpoint_sequence": 1},
                    },
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )
                if not result:
                    return None

                checkpoint = AutomationCheckpoint(
                    automation_run_id=automation_run_id,
                    checkpoint_sequence=int(result.get("checkpoint_sequence") or 1),
                    phase=phase,
                    status=AutomationStatus(result["status"]),
                    detail=detail,
                    state_snapshot=state_snapshot,
                )
                checkpoint_payload = checkpoint.model_dump(mode="python")
                checkpoint_payload["_id"] = checkpoint_payload.pop("checkpoint_id")
                await self._database.automation_checkpoints.insert_one(
                    checkpoint_payload,
                    session=session,
                )

        result["automation_run_id"] = str(result.pop("_id"))
        return AutomationRun.model_validate(result)

    async def recover_interrupted_runs(
        self,
        startup_cutoff: datetime | None = None,
        *,
        include_queued: bool = True,
        include_legacy_running: bool = True,
        after_automation_run_id: str | None = None,
        limit: int = 100,
    ) -> list[AutomationRun]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("automation_recovery_batch_size_invalid")
        now = datetime.now(timezone.utc)
        legacy_cutoff = startup_cutoff or now
        query: dict[str, Any] = {"status": {"$in": [AutomationStatus.RUNNING.value]}}
        recovery_branches = [
            {
                "status": AutomationStatus.RUNNING.value,
                "worker_lease_expires_at": {"$type": "date", "$lte": now},
            }
        ]
        if include_legacy_running:
            recovery_branches.append(
                {
                    "status": AutomationStatus.RUNNING.value,
                    "worker_lease_expires_at": None,
                    "updated_at": {"$lte": legacy_cutoff},
                }
            )
        if include_queued:
            query["status"]["$in"].append(AutomationStatus.QUEUED.value)
            recovery_branches.append(
                {
                    "status": AutomationStatus.QUEUED.value,
                    "created_at": {"$lte": legacy_cutoff},
                }
            )
        query["$or"] = recovery_branches
        if after_automation_run_id:
            query["_id"] = {"$gt": str(after_automation_run_id)}
        values = await self._database.automation_runs.find(query).sort(
            [("_id", 1)]
        ).to_list(length=limit)
        recovered = []
        for value in values:
            if value.get("status") == AutomationStatus.QUEUED.value:
                value["automation_run_id"] = str(value.pop("_id"))
                recovered.append(AutomationRun.model_validate(value))
                continue

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
            stored_retry_count = value.get("automatic_retry_count", 0)
            retry_count = (
                stored_retry_count
                if type(stored_retry_count) is int and stored_retry_count >= 0
                else limits.retries
            )
            can_resume = snapshot is not None and not action_outcome_uncertain
            retry_budget_available = retry_count < limits.retries
            should_resume = can_resume and retry_budget_available
            retry_exhausted = can_resume and not retry_budget_available
            next_status = AutomationStatus.QUEUED if should_resume else AutomationStatus.DEGRADED
            reason_code = (
                "AUTOMATION_ACTION_OUTCOME_UNCERTAIN"
                if action_outcome_uncertain
                else "AUTOMATION_RECOVERY_RETRY_LIMIT_REACHED"
                if retry_exhausted
                else None
                if should_resume
                else "AUTOMATION_INTERRUPTED_WITHOUT_CHECKPOINT"
            )
            run = await self.transition_with_checkpoint(
                str(value["_id"]),
                value["revision"],
                {
                    "status": next_status,
                    "error_code": reason_code,
                    "worker_lease_expires_at": None,
                    "automatic_retry_count": retry_count + 1
                    if should_resume
                    else retry_count,
                },
                phase=(
                    AutomationCheckpointPhase.QUEUED
                    if should_resume
                    else AutomationCheckpointPhase.FINALIZED
                ),
                detail=(
                    {
                        "reason_code": "AUTOMATION_RESUMED_FROM_CHECKPOINT",
                        "resuming_after": snapshot.completed_phase.value,
                    }
                    if can_resume
                    else {
                        "reason_code": reason_code,
                        "retryable": False,
                        "automatic_retry_count": retry_count,
                        "resumable": can_resume,
                        "task_id": latest.detail.get("task_id") if latest else None,
                        "tool_name": latest.detail.get("tool_name") if latest else None,
                    }
                ),
                state_snapshot=snapshot if can_resume else None,
                recovery_lease_expired_before=now,
                legacy_recovery_cutoff=(legacy_cutoff if include_legacy_running else None),
            )
            if run:
                recovered.append(run)
        return recovered

    async def list_retryable_queue_runs(self, retry_cutoff: datetime, limit: int = 100) -> list[AutomationRun]:
        values = await self._database.automation_runs.find(
            {
                "status": AutomationStatus.DEGRADED.value,
                "error_code": {
                    "$in": [
                        "AUTOMATION_QUEUE_UNAVAILABLE",
                        "AUTOMATION_WORKER_RETRYABLE",
                    ]
                },
                "updated_at": {"$lte": retry_cutoff},
                "$or": [
                    {"automatic_retry_count": {"$lt": limits.retries}},
                    {"automatic_retry_count": {"$exists": False}},
                ],
            }
        ).sort([("updated_at", 1), ("_id", 1)]).to_list(length=limit)
        for value in values:
            value["automation_run_id"] = str(value.pop("_id"))
        return [AutomationRun.model_validate(value) for value in values]

    async def claim_stale_queued_runs(
        self,
        stale_before: datetime,
        lease_expires_at: datetime,
        limit: int = 100,
    ) -> list[AutomationRun]:
        now = datetime.now(timezone.utc)
        claimed = []
        query = {
            "status": AutomationStatus.QUEUED.value,
            "updated_at": {"$lte": stale_before},
            "$or": [
                {"queue_dispatch_lease_expires_at": {"$lte": now}},
                {"queue_dispatch_lease_expires_at": None},
                {"queue_dispatch_lease_expires_at": {"$exists": False}},
            ],
        }
        for _ in range(max(0, limit)):
            value = await self._database.automation_runs.find_one_and_update(
                query,
                {"$set": {"queue_dispatch_lease_expires_at": lease_expires_at}},
                sort=[("updated_at", 1), ("_id", 1)],
                return_document=ReturnDocument.AFTER,
            )
            if value is None:
                break
            value["automation_run_id"] = str(value.pop("_id"))
            claimed.append(AutomationRun.model_validate(value))
        return claimed

    async def latest_checkpoint(self, automation_run_id: str) -> AutomationCheckpoint | None:
        value = await self._database.automation_checkpoints.find_one(
            {"automation_run_id": automation_run_id},
            sort=[
                ("checkpoint_sequence", DESCENDING),
                ("created_at", DESCENDING),
                ("_id", DESCENDING),
            ],
        )
        if not value:
            return None
        value["checkpoint_id"] = str(value.pop("_id"))
        return AutomationCheckpoint.model_validate(value)

    async def save_checkpoint(
        self,
        checkpoint: AutomationCheckpoint,
        *,
        expected_worker_revision: int | None = None,
    ) -> bool:
        payload = checkpoint.model_dump(mode="python")
        payload["_id"] = payload.pop("checkpoint_id")
        if expected_worker_revision is None:
            async with await database.mongodb.start_session() as session:
                async with session.start_transaction():
                    active_run = await self._database.automation_runs.find_one_and_update(
                        {"_id": checkpoint.automation_run_id},
                        {"$inc": {"checkpoint_sequence": 1}},
                        return_document=ReturnDocument.AFTER,
                        session=session,
                    )
                    if not active_run:
                        return False
                    payload["checkpoint_sequence"] = int(
                        active_run.get("checkpoint_sequence") or 1
                    )
                    await self._database.automation_checkpoints.insert_one(
                        payload, session=session
                    )
            return True

        now = datetime.now(timezone.utc)
        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                active_run = await self._database.automation_runs.find_one_and_update(
                    {
                        "_id": checkpoint.automation_run_id,
                        "revision": expected_worker_revision,
                        "status": AutomationStatus.RUNNING.value,
                        "worker_lease_expires_at": {"$gt": now},
                    },
                    {
                        "$set": {
                            "worker_lease_expires_at": now + timedelta(
                                seconds=limits.message_ack_timeout_seconds
                            )
                        },
                        "$inc": {"checkpoint_sequence": 1},
                    },
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )
                if not active_run:
                    return False
                payload["checkpoint_sequence"] = int(
                    active_run.get("checkpoint_sequence") or 1
                )
                await self._database.automation_checkpoints.insert_one(
                    payload, session=session
                )
        return True

    async def list_checkpoints(self, automation_run_id: str) -> list[AutomationCheckpoint]:
        values = await self._database.automation_checkpoints.find(
            {"automation_run_id": automation_run_id}
        ).sort(
            [
                ("checkpoint_sequence", 1),
                ("created_at", 1),
                ("_id", 1),
            ]
        ).to_list(length=None)
        for value in values:
            value["checkpoint_id"] = str(value.pop("_id"))
        return [AutomationCheckpoint.model_validate(value) for value in values]

    async def count_retry_checkpoints(self, automation_run_id: str) -> int:
        return await self._database.automation_checkpoints.count_documents(
            {
                "automation_run_id": automation_run_id,
                "detail.reason_code": {
                    "$in": [
                        "AUTOMATION_QUEUE_UNAVAILABLE",
                        "AUTOMATION_WORKER_RETRYABLE",
                    ]
                },
            }
        )

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
        await self.save_source_facts(facts)
        await self.save_receipt(receipt)
        if receipt.testability_blueprint is not None:
            await self.save_project_blueprint(
                receipt.automation_run_id,
                receipt.project_id,
                facts,
                receipt.testability_blueprint.model_dump(mode="json"),
            )
        fact_ids = [fact.source_fact_id for fact in facts]
        await self._database.automation_source_facts.delete_many(
            {
                "automation_run_id": automation_run_id,
                "_id": {"$nin": fact_ids},
            }
        )

    async def save_project_blueprint(
        self,
        automation_run_id: str,
        project_id: str,
        facts: list[SourceFact],
        compilation: dict,
    ) -> ProjectTestabilityBlueprint:
        from src.schemas.inference_requirements import TestabilityBlueprintCompilationOutput

        validated = TestabilityBlueprintCompilationOutput.model_validate(compilation)
        facts_by_reference: dict[str, list[SourceFact]] = {}
        for fact in facts:
            if fact.project_id != project_id or fact.automation_run_id != automation_run_id:
                continue
            quote_digest = hashlib.sha256(fact.quote.encode("utf-8")).hexdigest()
            if fact.quote_sha256 and fact.quote_sha256 != quote_digest:
                raise ValueError("BLUEPRINT_SOURCE_QUOTE_DIGEST_INVALID")
            if fact.source_start is None or fact.source_end is None:
                raise ValueError("BLUEPRINT_SOURCE_POSITION_MISSING")
            reference = fact.artifact_version_id or fact.artifact_id
            if reference in validated.evidence_refs:
                facts_by_reference.setdefault(reference, []).append(fact)

        if set(validated.evidence_refs) - set(facts_by_reference):
            raise ValueError("BLUEPRINT_SOURCE_FACTS_MISSING")

        revisions = []
        for reference in sorted(validated.evidence_refs):
            source_facts = facts_by_reference[reference]
            artifact_ids = {fact.artifact_id for fact in source_facts}
            artifact_types = {fact.artifact_type for fact in source_facts}
            if len(artifact_ids) != 1 or len(artifact_types) != 1:
                raise ValueError("BLUEPRINT_SOURCE_REVISION_AMBIGUOUS")
            revisions.append(
                BlueprintSourceRevision(
                    artifact_type=next(iter(artifact_types)),
                    artifact_id=next(iter(artifact_ids)),
                    artifact_version_id=reference,
                    source_fact_ids=sorted({fact.source_fact_id for fact in source_facts}),
                    quote_sha256=sorted(
                        {
                            hashlib.sha256(fact.quote.encode("utf-8")).hexdigest()
                            for fact in source_facts
                        }
                    ),
                )
            )

        source_fact_ids = sorted(
            {
                fact_id
                for revision in revisions
                for fact_id in revision.source_fact_ids
            }
        )
        digest_input = {
            "project_id": project_id,
            "compilation": validated.model_dump(mode="json"),
            "source_revisions": [
                {
                    "artifact_type": item.artifact_type,
                    "artifact_id": item.artifact_id,
                    "artifact_version_id": item.artifact_version_id,
                    "quote_sha256": item.quote_sha256,
                }
                for item in revisions
            ],
        }
        source_digest = hashlib.sha256(
            json.dumps(digest_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        collection = self._database.automation_project_blueprints

        async def attach_run(existing):
            if not existing:
                return None
            if automation_run_id not in existing.get("automation_run_ids", []):
                await collection.update_one(
                    {"_id": existing["_id"]},
                    {"$addToSet": {"automation_run_ids": automation_run_id}},
                )
                existing = await collection.find_one({"_id": existing["_id"]}) or existing
            return self._parse_project_blueprint(existing)

        existing_run = await collection.find_one(
            {"project_id": project_id, "automation_run_ids": automation_run_id}
        )
        if existing_run:
            if existing_run.get("source_digest") != source_digest:
                raise ValueError("AUTOMATION_RUN_BLUEPRINT_CONFLICT")
            return self._parse_project_blueprint(existing_run)

        existing_digest = await collection.find_one(
            {"project_id": project_id, "source_digest": source_digest}
        )
        if existing_digest:
            return await attach_run(existing_digest)

        for _ in range(5):
            latest = await collection.find_one(
                {"project_id": project_id}, sort=[("version", DESCENDING)]
            )
            version = int((latest or {}).get("version", 0)) + 1
            record = ProjectTestabilityBlueprint(
                project_id=project_id,
                version=version,
                automation_run_ids=[automation_run_id],
                source_fact_ids=source_fact_ids,
                source_revisions=revisions,
                source_digest=source_digest,
                compilation=validated,
            )
            payload = record.model_dump(mode="python")
            payload["_id"] = payload.pop("blueprint_id")
            try:
                await collection.insert_one(payload)
                return record
            except DuplicateKeyError:
                existing_run = await collection.find_one(
                    {"project_id": project_id, "automation_run_ids": automation_run_id}
                )
                if existing_run:
                    if existing_run.get("source_digest") != source_digest:
                        raise ValueError("AUTOMATION_RUN_BLUEPRINT_CONFLICT")
                    return self._parse_project_blueprint(existing_run)
                existing_digest = await collection.find_one(
                    {"project_id": project_id, "source_digest": source_digest}
                )
                if existing_digest:
                    return await attach_run(existing_digest)
        raise RuntimeError("PROJECT_BLUEPRINT_VERSION_CONFLICT")

    @staticmethod
    def _parse_project_blueprint(payload: dict) -> ProjectTestabilityBlueprint:
        value = dict(payload)
        value["blueprint_id"] = str(value.pop("_id"))
        return ProjectTestabilityBlueprint.model_validate(value)

    async def list_project_blueprints(
        self, project_id: str, limit: int = 50
    ) -> list[ProjectTestabilityBlueprint]:
        values = await self._database.automation_project_blueprints.find(
            {"project_id": project_id}
        ).sort([("version", DESCENDING), ("created_at", DESCENDING)]).to_list(length=limit)
        return [self._parse_project_blueprint(value) for value in values]

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
