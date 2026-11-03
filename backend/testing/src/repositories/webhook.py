from src.core.database import database


class WebhookRepository:
    async def list_subscriptions(self, query, limit):
        return await database.value.webhook_subscriptions.find(query).sort(
            "updated_at", -1
        ).to_list(limit)

    async def insert_subscription(self, value):
        await database.value.webhook_subscriptions.insert_one(value)
        return value

    async def list_deliveries(self, query, limit):
        return await database.value.webhook_deliveries.find(query).sort(
            "created_at", -1
        ).to_list(limit)

    async def find_replay_job(self, project_id, idempotency_key):
        return await database.value.webhook_replay_jobs.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_delivery(self, delivery_id, project_id):
        return await database.value.webhook_deliveries.find_one(
            {"_id": delivery_id, "project_id": project_id}
        )

    async def find_subscription(self, subscription_id, project_id, enabled=None):
        query = {"_id": subscription_id, "project_id": project_id}
        if enabled is not None:
            query["enabled"] = enabled
        return await database.value.webhook_subscriptions.find_one(query)

    async def insert_replay_job(self, value, session=None):
        await database.value.webhook_replay_jobs.insert_one(value, session=session)
        return value

    async def queue_replay(
        self, delivery_id, project_id, failed_status, queued_status, operation_id, updated_at, session=None
    ):
        return await database.value.webhook_deliveries.update_one(
            {"_id": delivery_id, "project_id": project_id, "status": failed_status},
            {
                "$set": {
                    "status": queued_status,
                    "operation_id": operation_id,
                    "updated_at": updated_at,
                },
                "$inc": {"attempt": 1},
            },
            session=session,
        )

    async def upsert_delivery(self, delivery_id, project_id, value):
        await database.value.webhook_deliveries.update_one(
            {"_id": delivery_id, "project_id": project_id},
            {"$set": value},
            upsert=True,
        )
        return value


webhook_repository = WebhookRepository()
