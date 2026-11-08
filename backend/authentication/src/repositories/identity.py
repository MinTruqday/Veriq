import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.mongo import mongo
from src.core.infrastructure.redis import redis


class IdentityRepository:
    @staticmethod
    def _token_hash(token: str) -> str:
        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    @staticmethod
    async def get_system_config_by_type(config_type: str, projection: dict | None = None):
        return await mongo.find_one("system_configs", {"type": config_type}, projection)

    @staticmethod
    async def get_auth_credential_by_id(user_id: str):
        return await mongo.find_one("auth_credentials", {"_id": user_id})

    @staticmethod
    async def get_auth_credential_by_email(email: str):
        return await mongo.find_one("auth_credentials", {"email": email.lower()})

    @staticmethod
    async def get_user_by_email(email: str):
        return await IdentityRepository.get_auth_credential_by_email(email)

    @staticmethod
    async def get_auth_credential_by_slug(slug: str):
        return await mongo.find_one("auth_credentials", {"slug": slug.lower()})

    @staticmethod
    async def find_auth_credential(query: dict, projection: dict | None = None):
        return await mongo.find_one("auth_credentials", query, projection)

    @staticmethod
    async def find_auth_credentials(
        query: dict, projection: dict | None = None, limit: int = 500
    ):
        return await mongo.find("auth_credentials", query, projection).to_list(limit)

    @staticmethod
    async def list_auth_credentials(
        query: dict,
        projection: dict | None = None,
        sort=None,
        limit: int | None = None,
    ):
        cursor = mongo.find("auth_credentials", query, projection, sort=sort)
        if limit is not None:
            cursor = cursor.limit(limit)
        return await cursor.to_list(length=limit)

    @staticmethod
    async def update_auth_credential(query: dict, update: dict):
        return await mongo.update_one("auth_credentials", query, update)

    @staticmethod
    async def update_auth_credentials(query: dict, update: dict):
        return await mongo.update_many("auth_credentials", query, update)

    @staticmethod
    async def count_auth_credentials(query: dict):
        return await mongo.count_documents("auth_credentials", query)

    @staticmethod
    async def find_and_update_auth_credential(query: dict, update: dict):
        return await mongo.get_db()["auth_credentials"].find_one_and_update(
            query, update, return_document=ReturnDocument.AFTER
        )

    @staticmethod
    async def update_system_config(config_type: str, update: dict, upsert: bool = False):
        return await mongo.update_one(
            "system_configs", {"type": config_type}, update, upsert=upsert
        )

    @staticmethod
    async def create_auth_credential(credential: dict):
        credential["email"] = credential["email"].lower()
        if credential.get("slug"):
            credential["slug"] = credential["slug"].lower()
        return await mongo.insert_one("auth_credentials", credential)

    @staticmethod
    async def update_password_hash(email: str, password_hash: str):
        return await mongo.update_one(
            "auth_credentials",
            {"email": email.lower()},
            {
                "$set": {
                    "password_hash": password_hash,
                    "last_password_change": datetime.now(timezone.utc),
                }
            },
        )

    @staticmethod
    async def insert_audit_log(log_data: dict):
        return await mongo.insert_one("audit_logs", log_data)

    @staticmethod
    async def register_session(user_id: str, session_id: str, ip: str, refresh_token: str):
        now = datetime.now(timezone.utc)
        return await mongo.insert_one(
            "sessions",
            {
                "_id": session_id,
                "user_id": user_id,
                "ip": ip,
                "refresh_token_hash": IdentityRepository._token_hash(refresh_token),
                "created_at": now,
                "last_refreshed_at": now,
                "expires_at": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                "revoked_at": None,
            },
        )

    @staticmethod
    async def rotate_refresh_token(refresh_token: str, replacement: str, ip: str):
        now = datetime.now(timezone.utc)
        return await mongo.get_db()["sessions"].find_one_and_update(
            {
                "refresh_token_hash": IdentityRepository._token_hash(refresh_token),
                "revoked_at": None,
                "expires_at": {"$gt": now},
            },
            {
                "$set": {
                    "refresh_token_hash": IdentityRepository._token_hash(replacement),
                    "last_refreshed_at": now,
                    "last_ip": ip,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    @staticmethod
    async def revoke_session(user_id: str, session_id: str):
        await redis.get_client().srem(f"user_sessions:{user_id}", session_id)
        return await mongo.update_one(
            "sessions",
            {"_id": session_id, "user_id": user_id},
            {"$set": {"revoked_at": datetime.now(timezone.utc)}},
        )

    @staticmethod
    async def revoke_all_sessions(user_id: str):
        await redis.delete(f"user_sessions:{user_id}")
        return await mongo.update_many(
            "sessions",
            {"user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(timezone.utc)}},
        )

    @staticmethod
    async def revoke_every_session(timestamp: datetime):
        return await mongo.update_many(
            "sessions", {"revoked_at": None}, {"$set": {"revoked_at": timestamp}}
        )

    @staticmethod
    async def clear_every_session_cache():
        async for key in redis.get_client().scan_iter(match="user_sessions:*"):
            await redis.delete(key)

    @staticmethod
    async def revoke_other_sessions(user_id: str, session_id: str, timestamp: datetime):
        return await mongo.update_many(
            "sessions",
            {"user_id": user_id, "_id": {"$ne": session_id}, "revoked_at": None},
            {"$set": {"revoked_at": timestamp}},
        )

    @staticmethod
    async def list_active_sessions(user_id: str):
        return (
            await mongo.find(
                "sessions",
                {
                    "user_id": user_id,
                    "revoked_at": None,
                    "expires_at": {"$gt": datetime.now(timezone.utc)},
                },
                {"refresh_token_hash": 0},
            )
            .sort("created_at", -1)
            .to_list(500)
        )

    @staticmethod
    async def get_session(user_id: str, session_id: str, projection: dict | None = None):
        return await mongo.find_one(
            "sessions", {"_id": session_id, "user_id": user_id}, projection
        )

    @staticmethod
    async def count_sessions(query: dict):
        return await mongo.count_documents("sessions", query)

    @staticmethod
    async def list_sessions(query: dict, projection: dict | None = None):
        return await mongo.find("sessions", query, projection).sort(
            "created_at", -1
        ).to_list(length=None)

    @staticmethod
    async def retain_session_cache(user_id: str, session_id: str):
        cache_key = f"user_sessions:{user_id}"
        await redis.delete(cache_key)
        return await IdentityRepository.cache_session(user_id, session_id)

    @staticmethod
    async def cache_session(user_id: str, session_id: str):
        cache_key = f"user_sessions:{user_id}"
        await redis.sadd(cache_key, session_id)
        return await redis.get_client().expire(
            cache_key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )

    @staticmethod
    async def has_cached_session(user_id: str, session_id: str):
        return await redis.sismember(f"user_sessions:{user_id}", session_id)

    @staticmethod
    async def create_password_reset_token(document: dict):
        token = document.pop("token")
        document["token_hash"] = IdentityRepository._token_hash(token)
        await mongo.update_many(
            "password_reset_tokens",
            {"email": document["email"].lower(), "used": False},
            {"$set": {"used": True}},
        )
        document["email"] = document["email"].lower()
        return await mongo.insert_one("password_reset_tokens", document)

    @staticmethod
    async def get_valid_password_reset_token(token: str):
        return await mongo.find_one(
            "password_reset_tokens",
            {
                "$or": [{"token_hash": IdentityRepository._token_hash(token)}, {"token": token}],
                "used": False,
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            },
        )

    @staticmethod
    async def consume_password_reset_token(token: str):
        return await mongo.get_db()["password_reset_tokens"].find_one_and_update(
            {
                "$or": [{"token_hash": IdentityRepository._token_hash(token)}, {"token": token}],
                "used": False,
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            },
            {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.BEFORE,
        )

    @staticmethod
    async def create_email_verification_token(document: dict):
        token = document.pop("token")
        document["token_hash"] = IdentityRepository._token_hash(token)
        document["email"] = document["email"].lower()
        await mongo.update_many(
            "email_verification_tokens",
            {"user_id": document["user_id"], "used": False},
            {"$set": {"used": True, "invalidated_at": datetime.now(timezone.utc)}},
        )
        return await mongo.insert_one("email_verification_tokens", document)

    @staticmethod
    async def consume_email_verification_token(token: str):
        return await mongo.get_db()["email_verification_tokens"].find_one_and_update(
            {
                "token_hash": IdentityRepository._token_hash(token),
                "used": False,
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            },
            {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.BEFORE,
        )

    @staticmethod
    async def mark_email_verified(user_id: str, email: str):
        timestamp = datetime.now(timezone.utc)
        return await mongo.get_db()["auth_credentials"].find_one_and_update(
            {"_id": user_id, "email": email.lower(), "is_active": True},
            {
                "$set": {
                    "is_verified": True,
                    "email_verified": True,
                    "email_verified_at": timestamp,
                    "updated_at": timestamp,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    @staticmethod
    async def set_redis_passkey_challenge(email: str, challenge: bytes):
        await redis.setex(
            f"passkey_challenge:{email.lower()}",
            300,
            base64.b64encode(challenge).decode("ascii"),
        )

    @staticmethod
    async def upsert_passkey_challenge(email: str, challenge: bytes):
        now = datetime.now(timezone.utc)
        return await mongo.update_one(
            "passkey_challenges",
            {"_id": email.lower()},
            {
                "$set": {
                    "challenge": challenge,
                    "created_at": now,
                    "expires_at": now
                    + timedelta(seconds=300),
                }
            },
            upsert=True,
        )

    @staticmethod
    async def consume_passkey_challenge(email: str):
        document = await mongo.get_db()["passkey_challenges"].find_one_and_delete(
            {"_id": email.lower(), "expires_at": {"$gt": datetime.now(timezone.utc)}}
        )
        await redis.delete(f"passkey_challenge:{email.lower()}")
        return document.get("challenge") if document else None

    @staticmethod
    async def update_passkey_sign_count(user_id: str, credential_id: str, sign_count: int):
        return await mongo.update_one(
            "auth_credentials",
            {"_id": user_id, "passkeys.credential_id": credential_id},
            {"$set": {"passkeys.$.sign_count": sign_count}},
        )

    @staticmethod
    async def add_passkey(user_id: str, passkey: dict):
        return await mongo.update_one(
            "auth_credentials",
            {"_id": user_id, "passkeys.credential_id": {"$ne": passkey["credential_id"]}},
            {"$push": {"passkeys": passkey}},
        )
