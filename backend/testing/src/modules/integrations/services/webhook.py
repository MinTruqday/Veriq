import hmac
import hashlib
import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_entity, new_id, now, optimistic_patch
from src.core.configuration import settings
from src.core.database import database
from src.repositories.webhook import webhook_repository


def _replay_request_hash(payload, delivery_id):
    request = payload.model_dump(mode="json", exclude={"idempotency_key"})
    request["delivery_id"] = delivery_id
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_replay(existing, delivery_id, payload, user):
    if existing.get("requested_by") != user.id:
        raise HTTPException(status_code=403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
    request_hash = existing.get("idempotency_request_hash")
    if not request_hash:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
    if request_hash != _replay_request_hash(payload, delivery_id):
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})


def public_subscription(value):
    result = dict(value)
    result["endpoint_reference"] = "Đã cấu hình" if value.get("endpoint_reference") else None
    result["secret_reference"] = "Đã cấu hình" if value.get("secret_reference") else None
    return result


def public_delivery(value):
    allowed = set(['_id',
 'project_id',
 'subscription_id',
 'event_type',
 'status',
 'attempt',
 'response_status',
 'error_code',
 'payload_hash',
 'duration_ms',
 'operation_id',
 'created_at',
 'updated_at',
 'completed_at'])
    return {key: item for key, item in value.items() if key in allowed}


def public_replay_job(value):
    private_fields = set(['endpoint_reference', 'secret_reference'])
    return {
        key: item
        for key, item in value.items()
        if key not in private_fields
    }


class WebhookService:
    @staticmethod
    async def list_subscriptions(project_id, include_disabled, user):
        
        await get_project(project_id, user, "webhook.project.read")
        query = {"project_id": project_id}
        if not include_disabled:
            query["enabled"] = True
        items = await webhook_repository.list_subscriptions(
            query, 500
        )
        return [public_subscription(item) for item in items]

    @staticmethod
    async def create_subscription(project_id, payload, user):
        
        await get_project(project_id, user, "webhook.project.manage")
        timestamp = now()
        value = {
            "_id": new_id('WHSUB'),
            "project_id": project_id,
            **payload.model_dump(),
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await webhook_repository.insert_subscription(value)
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail={"code": 'WEBHOOK_NAME_EXISTS'})
        await audit(
            user.id,
            "webhook_subscription_created",
            "WebhookSubscription",
            value["_id"],
            project_id,
            {"events": value["events"]},
        )
        return public_subscription(value)

    @staticmethod
    async def update_subscription(project_id, subscription_id, payload, user):
        
        subscription = await get_project_entity(
            "webhook_subscriptions", subscription_id, user, "webhook.project.manage"
        )
        if subscription["project_id"] != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        try:
            updated = await optimistic_patch(
                "webhook_subscriptions",
                subscription_id,
                project_id,
                payload.expected_revision,
                payload.model_dump(exclude_unset=True),
            )
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail={"code": 'WEBHOOK_NAME_EXISTS'})
        await audit(
            user.id,
            "webhook_subscription_updated",
            "WebhookSubscription",
            subscription_id,
            project_id,
            {"enabled": updated.get("enabled")},
        )
        return public_subscription(updated)

    @staticmethod
    async def list_deliveries(project_id, status, user):
        
        await get_project(project_id, user, "webhook.project.read")
        query = {"project_id": project_id}
        if status:
            if status not in ['QUEUED', 'DELIVERED', 'FAILED']:
                raise HTTPException(
                    status_code=422, detail={"code": 'WEBHOOK_STATUS_INVALID'}
                )
            query["status"] = status
        items = await webhook_repository.list_deliveries(
            query, 1000
        )
        return [public_delivery(item) for item in items]

    @staticmethod
    async def replay_delivery(project_id, delivery_id, payload, user):
        
        await get_project(project_id, user, "webhook.project.replay")
        existing_job = await webhook_repository.find_replay_job(
            project_id, payload.idempotency_key
        )
        if existing_job:
            if existing_job.get("delivery_id") != delivery_id:
                raise HTTPException(
                    status_code=409, detail={"code": 'IDEMPOTENCY_KEY_REUSED'}
                )
            _verify_replay(existing_job, delivery_id, payload, user)
            return public_replay_job(existing_job)
        delivery = await webhook_repository.find_delivery(delivery_id, project_id)
        if not delivery:
            raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
        if delivery.get("status") != 'FAILED':
            raise HTTPException(
                status_code=409,
                detail={"code": 'WEBHOOK_DELIVERY_NOT_REPLAYABLE'},
            )
        subscription = await webhook_repository.find_subscription(
            delivery["subscription_id"], project_id, True
        )
        if not subscription:
            raise HTTPException(
                status_code=409,
                detail={"code": 'WEBHOOK_SUBSCRIPTION_INACTIVE'},
            )
        timestamp = now()
        job = {
            "_id": new_id('WHOP'),
            "project_id": project_id,
            "delivery_id": delivery_id,
            "subscription_id": delivery["subscription_id"],
            "endpoint_reference": subscription["endpoint_reference"],
            "secret_reference": subscription["secret_reference"],
            "event_type": delivery["event_type"],
            "payload_hash": delivery["payload_hash"],
            "status": 'QUEUED',
            "reason": payload.reason,
            "idempotency_key": payload.idempotency_key,
            "idempotency_request_hash": _replay_request_hash(payload, delivery_id),
            "requested_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    await webhook_repository.insert_replay_job(job, session=session)
                    queued = await webhook_repository.queue_replay(
                        delivery_id,
                        project_id,
                        'FAILED',
                        'QUEUED',
                        job["_id"],
                        timestamp,
                        session=session,
                    )
                    if queued.matched_count != 1:
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "WEBHOOK_DELIVERY_REPLAY_CONFLICT"},
                        )
                    await audit(
                        user.id,
                        "webhook_delivery_replay_queued",
                        "WebhookDelivery",
                        delivery_id,
                        project_id,
                        {"operation_id": job["_id"], "reason": payload.reason},
                        session=session,
                    )
        except DuplicateKeyError:
            existing_job = await webhook_repository.find_replay_job(
                project_id, payload.idempotency_key
            )
            if existing_job:
                if existing_job.get("delivery_id") != delivery_id:
                    raise HTTPException(
                        status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"}
                    )
                _verify_replay(existing_job, delivery_id, payload, user)
                return public_replay_job(existing_job)
            raise
        return public_replay_job(job)

    @staticmethod
    async def record_delivery(payload, internal_token):
        
        if not hmac.compare_digest(internal_token, settings.SECRET_KEY):
            raise HTTPException(
                status_code=403, detail={"code": 'INVALID_INTERNAL_TOKEN'}
            )
        subscription = await webhook_repository.find_subscription(
            payload.subscription_id, payload.project_id
        )
        if not subscription:
            raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
        timestamp = now()
        value = {
            "_id": payload.delivery_id,
            **payload.model_dump(exclude={"delivery_id"}),
            "completed_at": timestamp,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        await webhook_repository.upsert_delivery(
            payload.delivery_id, payload.project_id, value
        )
        return public_delivery(value)
