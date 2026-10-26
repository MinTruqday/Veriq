from src.core.infrastructure.configuration import settings


class DatabaseInfrastructure:
    def __init__(self):
        self.mongodb = None


database = DatabaseInfrastructure()


async def init_db():
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is required")
    from motor.motor_asyncio import AsyncIOMotorClient

    database.mongodb = AsyncIOMotorClient(settings.MONGODB_URI)
    await database.mongodb.admin.command("ping")
    jobs = database.mongodb[settings.WORKER_DB_NAME].worker_jobs
    await jobs.create_index([("document_id", 1), ("created_at", -1)])
    await jobs.create_index("expire_at", expireAfterSeconds=0)
    await jobs.create_index([("status", 1), ("execution_lease_until", 1)])
    outbox = database.mongodb[settings.WORKER_DB_NAME].worker_job_outbox
    await outbox.create_index([("status", 1), ("next_attempt_at", 1)])
    await outbox.create_index([("status", 1), ("lease_until", 1)])
    await outbox.create_index([("job_id", 1), ("dispatch_generation", 1)], unique=True)
    await outbox.create_index("expire_at", expireAfterSeconds=0)


async def close_db():
    if database.mongodb:
        database.mongodb.close()
        database.mongodb = None
