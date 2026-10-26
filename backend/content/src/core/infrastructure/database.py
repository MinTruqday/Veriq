import asyncio

from loguru import logger

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.redis import redis


class DatabaseInfrastructure:
    def __init__(self):
        self.mongodb = None


database = DatabaseInfrastructure()


async def init_db():
    mongo_uri = settings.MONGODB_URI

    if not mongo_uri:
        logger.error("Failed to initialize database connection due to missing MongoDB URI")
        import sys

        sys.exit(1)

    from motor.motor_asyncio import AsyncIOMotorClient

    database.mongodb = AsyncIOMotorClient(mongo_uri)
    await database.mongodb.admin.command("ping")

    from src.core.infrastructure.mq import mq

    max_retries = 5
    for i in range(max_retries):
        try:
            if await mq.health_check():
                logger.info("RabbitMQ connection established")
                break
            else:
                raise Exception("MQ health check failed")
        except Exception:
            if i == max_retries - 1:
                logger.exception("RabbitMQ connection error")
                raise
            logger.warning("Attempting to reconnect to RabbitMQ")
            await asyncio.sleep(5)

    await setup_indexes()


async def setup_indexes():
    try:
        db = database.mongodb[settings.CONTENT_DB_NAME]

        await db["documents"].create_index(
            [("title", "text"), ("description", "text"), ("author", "text")], background=True
        )
        await db["documents"].create_index([("creator_id", 1)], background=True)
        await db["documents"].create_index([("source_url", 1)], background=True)
        await db["documents"].create_index([("content_hash", 1)], background=True)
        await db["documents"].create_index(
            [("indexing_status", 1), ("is_deleted", 1), ("source_is_current", 1)],
            background=True,
        )
        await db["documents"].create_index(
            [("indexing_status", 1), ("indexing_lease_until", 1), ("is_deleted", 1)],
            background=True,
        )
        await db["documents"].create_index(
            [("source_url", 1), ("source_is_current", 1)], background=True
        )
        await db["documents"].create_index(
            [("source_url", 1), ("content_hash", 1)],
            unique=True,
            partialFilterExpression={
                "source_url": {"$type": "string"},
                "content_hash": {"$type": "string"},
            },
            background=True,
        )
        await db["documents"].create_index([("creator_id", 1), ("created_at", -1)], background=True)
        await db["documents"].create_index(
            [("status", 1), ("is_deleted", 1), ("created_at", -1)], background=True
        )
        await db["documents"].create_index(
            [("status", 1), ("is_deleted", 1), ("views", -1)], background=True
        )
        await db["documents"].create_index(
            [("status", 1), ("is_deleted", 1), ("categories", 1), ("created_at", -1)],
            background=True,
        )
        await db["documents"].create_index(
            [("status", 1), ("is_deleted", 1), ("tags", 1), ("created_at", -1)], background=True
        )
        await db["documents"].create_index([("slug", 1)], unique=True, background=True)

        await db["comments"].create_index([("item_id", 1), ("item_type", 1)], background=True)
        await db["comments"].create_index([("path", 1)], background=True)

        await db["editor_comments"].create_index(
            [("document_id", 1), ("block_id", 1)], background=True
        )

        await db["document_versions"].create_index(
            [("document_id", 1), ("created_at", -1)], background=True
        )
        await db["document_ingestion_outbox"].create_index(
            [("status", 1), ("available_at", 1), ("created_at", 1)],
            background=True,
        )
        await db["document_ingestion_outbox"].create_index(
            [("status", 1), ("lease_until", 1)],
            background=True,
        )
        await db["workspace_folders"].create_index([("creator_id", 1), ("parent_id", 1)])
        logger.info("MongoDB indexing initialized")
    except Exception:
        logger.exception("MongoDB indexing error")
        raise


async def close_db():
    if database.mongodb:
        database.mongodb.close()
        database.mongodb = None
    from src.core.infrastructure.mq import mq

    await mq.aclose()
    await redis.aclose()
