from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5

from pymongo import ReturnDocument

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.schemas.document_ingestion_outbox import (
    DocumentIngestionDispatch,
    DocumentIngestionDispatchStatus,
)


class DocumentIngestionOutboxRepository:
    COLLECTION = "document_ingestion_outbox"
    LEASE_SECONDS = 120

    @classmethod
    def _collection(cls):
        if database.mongodb is None:
            raise RuntimeError("content_database_not_initialized")
        return database.mongodb[settings.CONTENT_DB_NAME][cls.COLLECTION]

    @classmethod
    async def enqueue(
        cls,
        document: dict,
        user_id: str = "",
        superseded_document_id: str = "",
        force_new: bool = False,
    ) -> str:
        now = datetime.now(timezone.utc)
        document_id = str(document.get("_id") or document.get("document_id") or "")
        if not document_id:
            raise ValueError("document_ingestion_outbox_requires_document_id")
        source_identity = ":".join(
            [
                document_id,
                str(document.get("source_revision") or ""),
                str(document.get("content_hash") or ""),
                str(document.get("file_url") or ""),
            ]
        )
        event_id = (
            str(uuid4())
            if force_new
            else str(uuid5(NAMESPACE_URL, f"veriq-document-ingestion:{source_identity}"))
        )
        event = DocumentIngestionDispatch(
            event_id=event_id,
            document_id=document_id,
            user_id=str(user_id or ""),
            superseded_document_id=str(superseded_document_id or ""),
            available_at=now,
            created_at=now,
            updated_at=now,
        )
        row = event.model_dump()
        row["_id"] = event_id
        row["status"] = event.status.value
        async with await database.mongodb.start_session() as session:
            async with session.start_transaction():
                await cls._collection().update_one(
                    {"_id": event_id},
                    {"$setOnInsert": row},
                    upsert=True,
                    session=session,
                )
                result = await database.mongodb[settings.CONTENT_DB_NAME][
                    "documents"
                ].update_one(
                    {
                        "_id": document.get("_id") or document_id,
                        "is_deleted": {"$ne": True},
                    },
                    {
                        "$set": {
                            "index_dispatch_event_id": event_id,
                            "indexing_status": "queued",
                            "is_indexed": False,
                            "updated_at": now,
                        },
                        "$unset": {"indexing_error": ""},
                    },
                    session=session,
                )
                if result.matched_count != 1:
                    raise RuntimeError("document_ingestion_source_unavailable")
        return event_id

    @classmethod
    async def claim(cls, lease_token: str) -> dict | None:
        now = datetime.now(timezone.utc)
        return await cls._collection().find_one_and_update(
            {
                "$or": [
                    {"status": "pending", "available_at": {"$lte": now}},
                    {"status": "processing", "lease_until": {"$lte": now}},
                ]
            },
            {
                "$set": {
                    "status": DocumentIngestionDispatchStatus.PROCESSING.value,
                    "lease_token": lease_token,
                    "lease_until": now + timedelta(seconds=cls.LEASE_SECONDS),
                    "updated_at": now,
                },
                "$inc": {"attempts": 1},
            },
            sort=[("available_at", 1), ("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )

    @classmethod
    async def complete(cls, event_id: str, lease_token: str) -> bool:
        now = datetime.now(timezone.utc)
        result = await cls._collection().update_one(
            {
                "_id": event_id,
                "status": "processing",
                "lease_token": lease_token,
                "lease_until": {"$gt": now},
            },
            {
                "$set": {
                    "status": DocumentIngestionDispatchStatus.COMPLETED.value,
                    "updated_at": now,
                    "completed_at": now,
                },
                "$unset": {"lease_token": "", "lease_until": "", "last_error": ""},
            },
        )
        return result.modified_count == 1

    @classmethod
    async def retry(cls, event: dict, lease_token: str, error: Exception) -> bool:
        now = datetime.now(timezone.utc)
        attempts = max(1, int(event.get("attempts") or 1))
        delay_seconds = min(15 * (2 ** min(attempts - 1, 6)), 900)
        result = await cls._collection().update_one(
            {
                "_id": str(event.get("_id") or event.get("event_id") or ""),
                "status": "processing",
                "lease_token": lease_token,
                "lease_until": {"$gt": now},
            },
            {
                "$set": {
                    "status": DocumentIngestionDispatchStatus.PENDING.value,
                    "available_at": now + timedelta(seconds=delay_seconds),
                    "updated_at": now,
                    "last_error": type(error).__name__,
                },
                "$unset": {"lease_token": "", "lease_until": ""},
            },
        )
        return result.modified_count == 1

    @classmethod
    async def list_documents_requiring_dispatch(cls, limit: int = 100) -> list[dict]:
        query = {
            "file_url": {"$type": "string", "$ne": ""},
            "is_deleted": {"$ne": True},
            "source_is_current": {"$ne": False},
            "indexing_status": {"$in": [None, "not_started", "queued"]},
            "$or": [
                {"index_dispatch_event_id": {"$exists": False}},
                {"index_dispatch_event_id": None},
            ],
        }
        cursor = cls._collection().database["documents"].find(query).limit(limit)
        return await cursor.to_list(length=limit)

    @classmethod
    async def recover_expired_indexing_claims(cls, limit: int = 100) -> int:
        now = datetime.now(timezone.utc)
        documents = cls._collection().database["documents"]
        query = {
            "indexing_status": "indexing",
            "$or": [
                {"indexing_lease_until": {"$lte": now}},
                {"indexing_lease_until": None},
                {"indexing_lease_until": {"$exists": False}},
            ],
            "file_url": {"$type": "string", "$ne": ""},
            "is_deleted": {"$ne": True},
            "source_is_current": {"$ne": False},
            "ai_enabled": {"$ne": False},
            "index_status": {"$ne": "REVOKE_PENDING"},
        }
        rows = await documents.find(query, {"_id": 1}).sort(
            [("indexing_lease_until", 1), ("_id", 1)]
        ).limit(limit).to_list(length=limit)
        recovered = 0
        for row in rows:
            result = await documents.update_one(
                {
                    "_id": row["_id"],
                    "indexing_status": "indexing",
                    "$or": [
                        {"indexing_lease_until": {"$lte": now}},
                        {"indexing_lease_until": None},
                        {"indexing_lease_until": {"$exists": False}},
                    ],
                    "is_deleted": {"$ne": True},
                    "source_is_current": {"$ne": False},
                    "ai_enabled": {"$ne": False},
                    "index_status": {"$ne": "REVOKE_PENDING"},
                },
                {
                    "$set": {
                        "indexing_status": "queued",
                        "is_indexed": False,
                        "updated_at": now,
                    },
                    "$unset": {
                        "indexing_attempt_id": "",
                        "indexing_lease_token": "",
                        "indexing_lease_until": "",
                        "indexing_progress": "",
                        "index_dispatch_event_id": "",
                        "indexing_error": "",
                    },
                },
            )
            recovered += int(result.modified_count == 1)

        await documents.update_many(
            {
                "indexing_status": {"$in": ["indexed", "degraded"]},
                "indexing_lease_until": {"$lte": now},
            },
            {
                "$unset": {
                    "indexing_attempt_id": "",
                    "indexing_lease_token": "",
                    "indexing_lease_until": "",
                    "indexing_progress": "",
                }
            },
        )
        return recovered


document_ingestion_outbox = DocumentIngestionOutboxRepository
