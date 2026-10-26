from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database


class WorkerJobRepository:
    @property
    def collection(self):
        return database.mongodb[settings.WORKER_DB_NAME].worker_jobs

    @property
    def outbox(self):
        return database.mongodb[settings.WORKER_DB_NAME].worker_job_outbox

    async def create_job_with_outbox(self, job_id, job_values, insert, outbox):
        now = datetime.now(timezone.utc)
        job = {
            "_id": job_id,
            "created_at": now,
            "updated_at": now,
            **insert,
            **job_values,
        }
        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                await self.collection.insert_one(job, session=session)
                await self.outbox.insert_one(outbox, session=session)

    async def ensure_queued_job_outbox(self, job):
        """Repair a legacy queued job whose DB write preceded its broker publish."""
        if job.get("status") != "queued":
            return
        generation = int(job.get("dispatch_generation", 0))
        now = datetime.now(timezone.utc)
        try:
            await self.outbox.update_one(
                {"_id": f"{job['_id']}:{generation}"},
                {
                    "$setOnInsert": {
                        "job_id": job["_id"],
                        "dispatch_generation": generation,
                        "payload": job.get("request"),
                        "status": "pending",
                        "attempt_count": 0,
                        "next_attempt_at": now,
                        "created_at": now,
                        "updated_at": now,
                    }
                },
                upsert=True,
            )
        except DuplicateKeyError:
            return

    async def claim_next_outbox(self, lease_token, now, lease_until):
        return await self.outbox.find_one_and_update(
            {
                "$or": [
                    {"status": "pending", "next_attempt_at": {"$lte": now}},
                    {"status": "dispatching", "lease_until": {"$lte": now}},
                ]
            },
            {
                "$set": {
                    "status": "dispatching",
                    "lease_token": lease_token,
                    "lease_until": lease_until,
                    "updated_at": now,
                },
                "$inc": {"attempt_count": 1},
            },
            sort=[("next_attempt_at", 1), ("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )

    async def mark_outbox_published(self, outbox_id, lease_token, now):
        return await self.outbox.update_one(
            {"_id": outbox_id, "status": "dispatching", "lease_token": lease_token},
            {
                "$set": {
                    "status": "published",
                    "published_at": now,
                    "updated_at": now,
                    "expire_at": now + timedelta(days=settings.WORKER_OUTBOX_RETENTION_DAYS),
                },
                "$unset": {"lease_token": "", "lease_until": "", "last_error": ""},
            },
        )

    async def reschedule_outbox(self, outbox_id, lease_token, now, next_attempt_at, error):
        return await self.outbox.update_one(
            {"_id": outbox_id, "status": "dispatching", "lease_token": lease_token},
            {
                "$set": {
                    "status": "pending",
                    "next_attempt_at": next_attempt_at,
                    "last_error": str(error)[-1000:],
                    "updated_at": now,
                },
                "$unset": {"lease_token": "", "lease_until": ""},
            },
        )

    async def claim_retry_with_outbox(self, job_id, max_manual_retries):
        now = datetime.now(timezone.utc)
        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                job = await self.collection.find_one_and_update(
                    {
                        "_id": job_id,
                        "status": "failed",
                        "$or": [
                            {"manual_retry_count": {"$lt": max_manual_retries}},
                            {"manual_retry_count": {"$exists": False}},
                        ],
                    },
                    {
                        "$set": {
                            "status": "queued",
                            "error": None,
                            "error_code": None,
                            "updated_at": now,
                        },
                        "$inc": {"manual_retry_count": 1, "dispatch_generation": 1},
                    },
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )
                if not job:
                    return None
                generation = int(job["dispatch_generation"])
                request = job.get("request")
                if not isinstance(request, dict):
                    raise ValueError("Worker job payload is unavailable for retry")
                await self.outbox.insert_one(
                    {
                        "_id": f"{job_id}:{generation}",
                        "job_id": job_id,
                        "dispatch_generation": generation,
                        "payload": request,
                        "status": "pending",
                        "attempt_count": 0,
                        "next_attempt_at": now,
                        "created_at": now,
                        "updated_at": now,
                    },
                    session=session,
                )
                return job

    async def claim_execution(self, job_id, lease_token, now, lease_until):
        return await self.collection.find_one_and_update(
            {"_id": job_id, "status": "queued"},
            {
                "$set": {
                    "status": "running",
                    "attempt_started_at": now,
                    "execution_lease_token": lease_token,
                    "execution_lease_until": lease_until,
                    "updated_at": now,
                },
                "$inc": {"delivery_count": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def renew_execution_lease(self, job_id, lease_token, now, lease_until):
        return await self.collection.update_one(
            {
                "_id": job_id,
                "status": "running",
                "execution_lease_token": lease_token,
            },
            {
                "$set": {
                    "execution_lease_until": lease_until,
                    "updated_at": now,
                }
            },
        )

    async def finalize_execution(self, job_id, lease_token, values):
        now = datetime.now(timezone.utc)
        return await self.collection.update_one(
            {
                "_id": job_id,
                "status": "running",
                "execution_lease_token": lease_token,
            },
            {
                "$set": {**values, "updated_at": now},
                "$unset": {"execution_lease_token": "", "execution_lease_until": ""},
            },
        )

    async def mark_expired_executions_for_reconciliation(self, now):
        """Never replay a possibly side-effecting task after its owner disappears."""
        return await self.collection.update_many(
            {
                "status": "running",
                "execution_lease_until": {"$lte": now},
            },
            {
                "$set": {
                    "status": "reconciliation_required",
                    "error_code": "worker_execution_lease_expired",
                    "error": "Worker lease expired; execution outcome must be reconciled before retry.",
                    "reconciliation_required_at": now,
                    "updated_at": now,
                },
                "$unset": {"execution_lease_token": "", "execution_lease_until": ""},
            },
        )

    async def fail_execution(self, job_id, lease_token, values):
        return await self.finalize_execution(job_id, lease_token, values)

    async def cancel_queued(self, job_id, timestamp):
        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                job = await self.collection.find_one_and_update(
                    {"_id": job_id, "status": "queued"},
                    {
                        "$set": {
                            "status": "canceled",
                            "canceled_at": timestamp,
                            "updated_at": timestamp,
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )
                if not job:
                    return None
                await self.outbox.update_many(
                    {
                        "job_id": job_id,
                        "status": "pending",
                        "dispatch_generation": int(job.get("dispatch_generation", 0)),
                    },
                    {
                        "$set": {
                            "status": "canceled",
                            "updated_at": timestamp,
                            "expire_at": timestamp
                            + timedelta(days=settings.WORKER_OUTBOX_RETENTION_DAYS),
                        },
                    },
                    session=session,
                )
                return job

    async def record(self, job_id, values, insert=None):
        now = datetime.now(timezone.utc)
        update = {"$set": {**values, "updated_at": now}}
        if insert is not None:
            update["$setOnInsert"] = {"_id": job_id, "created_at": now, **insert}
        await self.collection.update_one({"_id": job_id}, update, upsert=insert is not None)

    async def find_one(self, query, projection=None):
        return await self.collection.find_one(query, projection)

    async def list(self, query, limit):
        return await self.collection.find(
            query,
            {"request.internal_token": 0, "execution_lease_token": 0},
        ).sort(
            "updated_at", -1
        ).limit(limit).to_list(limit)

    async def count(self, query):
        return await self.collection.count_documents(query)

    async def overview(self, query):
        return await self.collection.aggregate(
            [{"$match": query}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        ).to_list(100)

    async def discard(self, job_id, values):
        return await self.collection.find_one_and_update(
            {"_id": job_id, "status": "failed"},
            {"$set": values},
            return_document=ReturnDocument.AFTER,
        )

worker_job_repository = WorkerJobRepository()
