import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.repositories.jobs import worker_job_repository
from src.schemas import DiscardJobRequest, TestingJobRequest


class WorkerJobService:
    @staticmethod
    async def enqueue(payload: TestingJobRequest):
        event = payload.event.value
        request_payload = payload.model_dump(mode="json")
        canonical_request = json.dumps(
            request_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        request_fingerprint = hashlib.sha256(canonical_request.encode()).hexdigest()
        identity = ":".join(
            [
                payload.project_id,
                payload.artifact_version_id,
                event,
                payload.model_version,
                payload.requester_id,
                request_fingerprint,
            ]
        )
        job_id = f"qa-{hashlib.sha256(identity.encode()).hexdigest()[:40]}"
        if existing := await worker_job_repository.find_one({"_id": job_id}):
            await worker_job_repository.ensure_queued_job_outbox(existing)
            return {"job_id": job_id, "status": existing["status"]}

        legacy_identity = ":".join(
            [payload.project_id, payload.artifact_version_id, event, payload.model_version]
        )
        legacy_job_id = f"qa-{hashlib.sha256(legacy_identity.encode()).hexdigest()[:40]}"
        if existing := await worker_job_repository.find_one({"_id": legacy_job_id}):
            legacy_request = existing.get("request")
            if isinstance(legacy_request, dict):
                legacy_request.pop("job_id", None)
            if legacy_request == request_payload:
                await worker_job_repository.ensure_queued_job_outbox(existing)
                return {"job_id": legacy_job_id, "status": existing["status"]}

        task_payload = {"job_id": job_id, **request_payload}
        now = datetime.now(timezone.utc)
        try:
            await worker_job_repository.create_job_with_outbox(
                job_id,
                {"status": "queued", "dispatch_generation": 0},
                {
                    "kind": event,
                    "project_id": payload.project_id,
                    "requester_id": payload.requester_id,
                    "request": task_payload,
                },
                {
                    "_id": f"{job_id}:0",
                    "job_id": job_id,
                    "dispatch_generation": 0,
                    "payload": task_payload,
                    "status": "pending",
                    "attempt_count": 0,
                    "next_attempt_at": now,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        except DuplicateKeyError:
            existing = await worker_job_repository.find_one({"_id": job_id})
            if not existing:
                raise
            await worker_job_repository.ensure_queued_job_outbox(existing)
            return {"job_id": job_id, "status": existing["status"]}
        return {"job_id": job_id, "status": "queued"}

    @staticmethod
    async def retry(job_id: str):
        WorkerJobService._validate_id(job_id)
        job = await worker_job_repository.find_one(
            {"_id": job_id},
            {"execution_lease_token": 0},
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.get("status") != "failed":
            raise HTTPException(status_code=409, detail="Only failed jobs can be retried")
        request = job.get("request")
        if not isinstance(request, dict):
            raise HTTPException(status_code=422, detail="Job payload is unavailable for retry")
        claimed = await worker_job_repository.claim_retry_with_outbox(job_id, 9)
        if not claimed:
            latest = await worker_job_repository.find_one({"_id": job_id})
            if not latest:
                raise HTTPException(status_code=404, detail="Job not found")
            retry_count = int(latest.get("manual_retry_count", 0))
            if retry_count >= 9:
                raise HTTPException(status_code=409, detail="Manual retry limit reached")
            raise HTTPException(status_code=409, detail="Job retry is already in progress")
        retry_count = int(claimed.get("manual_retry_count", 0))
        return {
            "job_id": job_id,
            "status": "queued",
            "manual_retry_count": retry_count,
        }

    @staticmethod
    async def cancel(job_id: str):
        WorkerJobService._validate_id(job_id)
        job = await worker_job_repository.find_one({"_id": job_id})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.get("status") == "canceled":
            return {"job_id": job_id, "status": "canceled"}
        if job.get("status") != "queued":
            raise HTTPException(status_code=409, detail="Only queued jobs can be canceled")
        canceled = await worker_job_repository.cancel_queued(
            job_id, datetime.now(timezone.utc)
        )
        if not canceled:
            latest = await worker_job_repository.find_one({"_id": job_id})
            if latest and latest.get("status") == "canceled":
                return {"job_id": job_id, "status": "canceled"}
            raise HTTPException(status_code=409, detail="Worker job state changed; reload before canceling")
        return {"job_id": job_id, "status": "canceled"}

    @staticmethod
    async def get(job_id: str):
        WorkerJobService._validate_id(job_id)
        job = await worker_job_repository.find_one(
            {"_id": job_id},
            {"execution_lease_token": 0},
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        for field in ["created_at", "updated_at", "attempt_started_at", "expire_at"]:
            if value := job.get(field):
                job[field] = value.isoformat()
        return job

    @staticmethod
    async def list(project_id: str, status: str, kind: str, limit: int):
        query = {}
        if project_id:
            query["project_id"] = project_id
        if status:
            query["status"] = status.lower()
        if kind:
            query["kind"] = kind
        items = await worker_job_repository.list(query, limit)
        return {"items": items, "total": await worker_job_repository.count(query)}

    @staticmethod
    async def overview(project_id: str):
        match = {"project_id": project_id} if project_id else {}
        rows = await worker_job_repository.overview(match)
        return {
            "jobs_by_status": {row["_id"]: row["count"] for row in rows},
            "total": sum(row["count"] for row in rows),
        }

    @staticmethod
    async def discard(job_id: str, payload: DiscardJobRequest):
        WorkerJobService._validate_id(job_id)
        job = await worker_job_repository.discard(job_id, {
            "status": "discarded",
            "discard_reason": payload.reason,
            "discarded_by": payload.actor_id,
            "discarded_at": datetime.now(timezone.utc),
        })
        if not job:
            raise HTTPException(status_code=409, detail="Only failed jobs can be discarded")
        return job

    @staticmethod
    def _validate_id(job_id: str):
        if len(job_id) > 128:
            raise HTTPException(status_code=422, detail="Invalid job identifier")
