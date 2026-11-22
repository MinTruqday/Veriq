import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import DESCENDING, ReturnDocument, UpdateOne
from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.runtime.limits import limits
from src.schemas.ai_runs import (
    AIRunCheckpoint,
    AIRunPhase,
    AIRun,
    AIRunStatus,
    DerivationReceipt,
    SourceFact,
)


class AIRunRepository:
    @property
    def _database(self):
        return database.mongodb[settings.AI_DB_NAME]

    async def create_run_with_checkpoint(
        self,
        run: AIRun,
        *,
        phase: AIRunPhase,
        detail: dict[str, Any] | None = None,
    ) -> AIRun:
        payload = run.model_dump(mode="python")
        payload["_id"] = payload.pop("ai_run_id")
        payload["checkpoint_sequence"] = 1
        checkpoint = AIRunCheckpoint(
            ai_run_id=run.ai_run_id,
            checkpoint_sequence=1,
            phase=phase,
            status=run.status,
            detail=detail or {},
        )
        checkpoint_payload = checkpoint.model_dump(mode="python")
        checkpoint_payload["_id"] = checkpoint_payload.pop("checkpoint_id")

        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                await self._database.ai_runs.insert_one(payload, session=session)
                await self._database.ai_run_checkpoints.insert_one(
                    checkpoint_payload,
                    session=session,
                )
        return run.model_copy(update={"checkpoint_sequence": 1})

    async def get_run(self, ai_run_id: str) -> AIRun | None:
        payload = await self._database.ai_runs.find_one({"_id": ai_run_id})
        if not payload:
            return None
        payload["ai_run_id"] = str(payload.pop("_id"))
        return AIRun.model_validate(payload)

    async def find_event_run(self, project_id: str, source_event_id: str) -> AIRun | None:
        payload = await self._database.ai_runs.find_one(
            {"project_id": project_id, "source_event_id": source_event_id}
        )
        if not payload:
            return None
        payload["ai_run_id"] = str(payload.pop("_id"))
        return AIRun.model_validate(payload)

    async def list_incomplete_document_ingestion_runs(
        self, document_id: str
    ) -> list[AIRun]:
        values = await self._database.ai_runs.find(
            {
                "intent": "process_ingested_requirement_document",
                "target_artifact_ids": document_id,
                "status": {
                    "$nin": [AIRunStatus.COMPLETED, AIRunStatus.CANCELLED]
                },
            }
        ).sort("created_at", 1).to_list(length=None)
        runs = []
        for value in values:
            value["ai_run_id"] = str(value.pop("_id"))
            runs.append(AIRun.model_validate(value))
        return runs

    async def list_runs(
        self,
        project_id: str,
        limit: int,
        requester_user_id: str | None = None,
    ) -> list[AIRun]:
        query = {"project_id": project_id, "constraints.user_requested": True}
        if requester_user_id is not None:
            query["requester_user_id"] = requester_user_id
        values = await self._database.ai_runs.find(query).sort(
            "updated_at", DESCENDING
        ).to_list(length=limit)
        for value in values:
            value["ai_run_id"] = str(value.pop("_id"))
        return [AIRun.model_validate(value) for value in values]

    async def transition_with_checkpoint(
        self,
        ai_run_id: str,
        expected_revision: int,
        values: dict,
        *,
        phase: AIRunPhase,
        detail: dict,
        state_snapshot=None,
        recovery_lease_expired_before: datetime | None = None,
        require_live_worker_lease: bool = False,
    ) -> AIRun | None:
        values = {**values, "updated_at": datetime.now(timezone.utc)}
        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                run_filter: dict[str, Any] = {
                    "_id": ai_run_id,
                    "revision": expected_revision,
                }
                if recovery_lease_expired_before is not None:
                    run_filter["status"] = AIRunStatus.RUNNING.value
                    run_filter["worker_lease_expires_at"] = {
                        "$type": "date",
                        "$lte": recovery_lease_expired_before,
                    }
                if require_live_worker_lease:
                    run_filter["status"] = AIRunStatus.RUNNING.value
                    run_filter["worker_lease_expires_at"] = {"$gt": values["updated_at"]}
                result = await self._database.ai_runs.find_one_and_update(
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

                checkpoint = AIRunCheckpoint(
                    ai_run_id=ai_run_id,
                    checkpoint_sequence=int(result.get("checkpoint_sequence") or 1),
                    phase=phase,
                    status=AIRunStatus(result["status"]),
                    detail=detail,
                    state_snapshot=state_snapshot,
                )
                checkpoint_payload = checkpoint.model_dump(mode="python")
                checkpoint_payload["_id"] = checkpoint_payload.pop("checkpoint_id")
                await self._database.ai_run_checkpoints.insert_one(
                    checkpoint_payload,
                    session=session,
                )

        result["ai_run_id"] = str(result.pop("_id"))
        return AIRun.model_validate(result)

    async def recover_interrupted_runs(
        self,
        startup_cutoff: datetime | None = None,
        *,
        include_queued: bool = True,
        after_ai_run_id: str | None = None,
        limit: int = 100,
    ) -> list[AIRun]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("run_recovery_batch_size_invalid")
        now = datetime.now(timezone.utc)
        recovery_cutoff = startup_cutoff or now
        query: dict[str, Any] = {"status": {"$in": [AIRunStatus.RUNNING.value]}}
        recovery_branches = [
            {
                "status": AIRunStatus.RUNNING.value,
                "worker_lease_expires_at": {"$type": "date", "$lte": now},
            }
        ]
        if include_queued:
            query["status"]["$in"].append(AIRunStatus.QUEUED.value)
            recovery_branches.append(
                {
                    "status": AIRunStatus.QUEUED.value,
                    "created_at": {"$lte": recovery_cutoff},
                }
            )
        query["$or"] = recovery_branches
        if after_ai_run_id:
            query["_id"] = {"$gt": str(after_ai_run_id)}
        values = await self._database.ai_runs.find(query).sort(
            [("_id", 1)]
        ).to_list(length=limit)
        recovered = []
        for value in values:
            if value.get("status") == AIRunStatus.QUEUED.value:
                value["ai_run_id"] = str(value.pop("_id"))
                recovered.append(AIRun.model_validate(value))
                continue

            latest = await self.latest_checkpoint(str(value["_id"]))
            snapshot = latest.state_snapshot if latest else None
            action_outcome_uncertain = bool(
                latest
                and latest.phase == AIRunPhase.ACTION_STARTED
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
            next_status = AIRunStatus.QUEUED if should_resume else AIRunStatus.DEGRADED
            reason_code = (
                "AI_RUN_ACTION_OUTCOME_UNCERTAIN"
                if action_outcome_uncertain
                else "AI_RUN_RECOVERY_RETRY_LIMIT_REACHED"
                if retry_exhausted
                else None
                if should_resume
                else "AI_RUN_INTERRUPTED_WITHOUT_CHECKPOINT"
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
                    AIRunPhase.QUEUED
                    if should_resume
                    else AIRunPhase.FINALIZED
                ),
                detail=(
                    {
                        "reason_code": "AI_RUN_RESUMED_FROM_CHECKPOINT",
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
            )
            if run:
                recovered.append(run)
        return recovered

    async def list_retryable_queue_runs(self, retry_cutoff: datetime, limit: int = 100) -> list[AIRun]:
        values = await self._database.ai_runs.find(
            {
                "status": AIRunStatus.DEGRADED.value,
                "error_code": {
                    "$in": [
                        "AI_RUN_QUEUE_UNAVAILABLE",
                        "AI_RUN_WORKER_RETRYABLE",
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
            value["ai_run_id"] = str(value.pop("_id"))
        return [AIRun.model_validate(value) for value in values]

    async def claim_stale_queued_runs(
        self,
        stale_before: datetime,
        lease_expires_at: datetime,
        limit: int = 100,
    ) -> list[AIRun]:
        now = datetime.now(timezone.utc)
        claimed = []
        query = {
            "status": AIRunStatus.QUEUED.value,
            "updated_at": {"$lte": stale_before},
            "$or": [
                {"queue_dispatch_lease_expires_at": {"$lte": now}},
                {"queue_dispatch_lease_expires_at": None},
                {"queue_dispatch_lease_expires_at": {"$exists": False}},
            ],
        }
        for _ in range(max(0, limit)):
            value = await self._database.ai_runs.find_one_and_update(
                query,
                {"$set": {"queue_dispatch_lease_expires_at": lease_expires_at}},
                sort=[("updated_at", 1), ("_id", 1)],
                return_document=ReturnDocument.AFTER,
            )
            if value is None:
                break
            value["ai_run_id"] = str(value.pop("_id"))
            claimed.append(AIRun.model_validate(value))
        return claimed

    async def latest_checkpoint(self, ai_run_id: str) -> AIRunCheckpoint | None:
        value = await self._database.ai_run_checkpoints.find_one(
            {"ai_run_id": ai_run_id},
            sort=[
                ("checkpoint_sequence", DESCENDING),
                ("created_at", DESCENDING),
                ("_id", DESCENDING),
            ],
        )
        if not value:
            return None
        value["checkpoint_id"] = str(value.pop("_id"))
        return AIRunCheckpoint.model_validate(value)

    async def latest_checkpoint_with_evidence(
        self, ai_run_id: str
    ) -> AIRunCheckpoint | None:
        value = await self._database.ai_run_checkpoints.find_one(
            {
                "ai_run_id": ai_run_id,
                "state_snapshot.evidence.0": {"$exists": True},
            },
            sort=[
                ("checkpoint_sequence", DESCENDING),
                ("created_at", DESCENDING),
                ("_id", DESCENDING),
            ],
        )
        if not value:
            return None
        value["checkpoint_id"] = str(value.pop("_id"))
        return AIRunCheckpoint.model_validate(value)

    async def save_checkpoint(
        self,
        checkpoint: AIRunCheckpoint,
        *,
        expected_worker_revision: int | None = None,
    ) -> bool:
        payload = checkpoint.model_dump(mode="python")
        payload["_id"] = payload.pop("checkpoint_id")
        if expected_worker_revision is None:
            async with await database.mongodb.start_session() as session:
                async with session.start_transaction():
                    active_run = await self._database.ai_runs.find_one_and_update(
                        {"_id": checkpoint.ai_run_id},
                        {"$inc": {"checkpoint_sequence": 1}},
                        return_document=ReturnDocument.AFTER,
                        session=session,
                    )
                    if not active_run:
                        return False
                    payload["checkpoint_sequence"] = int(
                        active_run.get("checkpoint_sequence") or 1
                    )
                    await self._database.ai_run_checkpoints.insert_one(
                        payload, session=session
                    )
            return True

        now = datetime.now(timezone.utc)
        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                active_run = await self._database.ai_runs.find_one_and_update(
                    {
                        "_id": checkpoint.ai_run_id,
                        "revision": expected_worker_revision,
                        "status": AIRunStatus.RUNNING.value,
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
                await self._database.ai_run_checkpoints.insert_one(
                    payload, session=session
                )
        return True

    async def list_checkpoints(self, ai_run_id: str) -> list[AIRunCheckpoint]:
        values = await self._database.ai_run_checkpoints.find(
            {"ai_run_id": ai_run_id}
        ).sort(
            [
                ("checkpoint_sequence", 1),
                ("created_at", 1),
                ("_id", 1),
            ]
        ).to_list(length=None)
        for value in values:
            value["checkpoint_id"] = str(value.pop("_id"))
        return [AIRunCheckpoint.model_validate(value) for value in values]

    async def count_retry_checkpoints(self, ai_run_id: str) -> int:
        return await self._database.ai_run_checkpoints.count_documents(
            {
                "ai_run_id": ai_run_id,
                "detail.reason_code": {
                    "$in": [
                        "AI_RUN_QUEUE_UNAVAILABLE",
                        "AI_RUN_WORKER_RETRYABLE",
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
        await self._database.ai_run_source_facts.bulk_write(operations, ordered=True)

    async def replace_provenance(
        self,
        ai_run_id: str,
        facts: list[SourceFact],
        receipt: DerivationReceipt,
    ) -> None:
        await self.save_source_facts(facts)
        await self.save_receipt(receipt)
        fact_ids = [fact.source_fact_id for fact in facts]
        await self._database.ai_run_source_facts.delete_many(
            {
                "ai_run_id": ai_run_id,
                "_id": {"$nin": fact_ids},
            }
        )

    async def save_receipt(self, receipt: DerivationReceipt) -> None:
        payload = receipt.model_dump(mode="python")
        payload["_id"] = payload.pop("receipt_id")
        receipt_id = payload.pop("_id")
        await self._database.ai_run_derivation_receipts.update_one(
            {"ai_run_id": receipt.ai_run_id},
            {"$set": payload, "$setOnInsert": {"_id": receipt_id}},
            upsert=True,
        )

    async def get_receipt(self, ai_run_id: str) -> DerivationReceipt | None:
        payload = await self._database.ai_run_derivation_receipts.find_one(
            {"ai_run_id": ai_run_id}
        )
        if not payload:
            return None
        payload["receipt_id"] = str(payload.pop("_id"))
        return DerivationReceipt.model_validate(payload)

    async def list_source_facts(self, ai_run_id: str) -> list[SourceFact]:
        values = await self._database.ai_run_source_facts.find(
            {"ai_run_id": ai_run_id}
        ).sort("created_at", 1).to_list(length=None)
        for value in values:
            value["source_fact_id"] = str(value.pop("_id"))
        return [SourceFact.model_validate(value) for value in values]


ai_run_repository = AIRunRepository()
