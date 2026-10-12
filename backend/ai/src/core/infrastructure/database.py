import asyncio

from loguru import logger

from src.core.infrastructure.configuration import settings


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

    from src.core.infrastructure.mq import mq

    max_retries = 5
    for i in range(max_retries):
        try:
            if await mq.health_check():
                logger.info("RabbitMQ connection is stable")
                break
            else:
                raise Exception("MQ health check failed")
        except Exception as e:
            if i == max_retries - 1:
                logger.exception("RabbitMQ connection failed")
                raise e
            logger.exception("Retrying RabbitMQ connection")
            await asyncio.sleep(5)

    await setup_indexes()


async def setup_indexes():
    try:
        db = database.mongodb[settings.AI_DB_NAME]
        from pymongo import ASCENDING, DESCENDING, IndexModel

        index_sets = {
            "agent_traces": [
                IndexModel([("session_id", ASCENDING), ("started_at", DESCENDING)]),
                IndexModel([("status", ASCENDING), ("started_at", DESCENDING)]),
            ],
            "ai_sessions": [
                IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("document_id", ASCENDING)]),
            ],
            "ai_messages": [
                IndexModel([("session_id", ASCENDING), ("created_at", ASCENDING)]),
                IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            ],
            "retrieval_audit": [
                IndexModel([("requester_id", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("document_ids", ASCENDING), ("created_at", DESCENDING)]),
            ],
            "ai_workspaces": [
                IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
            ],
            "agent_runs": [
                IndexModel([("project_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),
            ],
            "long_term_memory": [
                IndexModel([("project_id", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("project_id", ASCENDING), ("trusted", ASCENDING)]),
                IndexModel(
                    [
                        ("project_id", ASCENDING),
                        ("owner_id", ASCENDING),
                        ("trusted", ASCENDING),
                        ("created_at", DESCENDING),
                    ]
                ),
                IndexModel([("run_id", ASCENDING)], unique=True),
            ],
        }
        for collection_name, indexes in index_sets.items():
            await db[collection_name].create_indexes(indexes)
        logger.info("MongoDB index creation completed")
    except Exception:
        logger.exception("MongoDB index creation failed")
        raise


async def close_db():
    if database.mongodb:
        database.mongodb.close()
