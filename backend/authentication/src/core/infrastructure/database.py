from loguru import logger

from src.core.infrastructure.configuration import settings


class DatabaseInfrastructure:
    def __init__(self):
        self.mongodb = None


database = DatabaseInfrastructure()


async def init_db():
    if not settings.MONGODB_URI:
        raise RuntimeError("MongoDB URI is required")
    from motor.motor_asyncio import AsyncIOMotorClient

    database.mongodb = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    await database.mongodb.admin.command("ping")
    await setup_indexes()


async def setup_indexes():
    db = database.mongodb[settings.AUTHENTICATION_DB_NAME]
    await db["auth_credentials"].create_index("email", unique=True)
    await db["auth_credentials"].create_index(
        "slug", unique=True, partialFilterExpression={"slug": {"$type": "string"}}
    )
    await db["sessions"].create_index([("user_id", 1), ("revoked_at", 1)])
    await db["sessions"].create_index(
        "refresh_token_hash",
        unique=True,
        partialFilterExpression={"refresh_token_hash": {"$type": "string"}},
    )
    await db["sessions"].create_index("expires_at", expireAfterSeconds=0)
    await db["password_reset_tokens"].create_index(
        "token_hash", unique=True, partialFilterExpression={"token_hash": {"$type": "string"}}
    )
    await db["password_reset_tokens"].create_index("expires_at", expireAfterSeconds=0)
    await db["email_verification_tokens"].create_index("token_hash", unique=True)
    await db["email_verification_tokens"].create_index([("user_id", 1), ("used", 1)])
    await db["email_verification_tokens"].create_index("expires_at", expireAfterSeconds=0)
    await db["passkey_challenges"].create_index("expires_at", expireAfterSeconds=0)
    await db["audit_logs"].create_index([("actor_email", 1), ("timestamp", -1)])
    logger.info("Authentication database indexes initialized")


async def close_db():
    if database.mongodb:
        database.mongodb.close()
        database.mongodb = None
