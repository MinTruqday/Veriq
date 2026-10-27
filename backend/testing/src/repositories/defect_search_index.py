from datetime import timedelta
from uuid import uuid4

from pymongo import ReturnDocument

from src.core.common import now
from src.core.database import database


class DefectSearchIndexRepository:
    @property
    def entries(self):
        return database.value.defect_search_index_outbox

    def entry_id(self, project_id, defect_id, revision):
        return f"defect-search:{project_id}:{defect_id}:{revision}"

    async def enqueue(self, defect, session=None):
        timestamp = now()
        revision = int(defect.get("revision") or 1)
        event_id = self.entry_id(defect["project_id"], defect["_id"], revision)
        await self.entries.update_one(
            {"_id": event_id},
            {
                "$setOnInsert": {
                    "project_id": defect["project_id"],
                    "defect_id": defect["_id"],
                    "requested_revision": revision,
                    "status": "PENDING",
                    "attempts": 0,
                    "next_attempt_at": timestamp,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            },
            upsert=True,
            **({"session": session} if session is not None else {}),
        )
        return event_id

    async def claim_next(self, lease_seconds):
        timestamp = now()
        token = uuid4().hex
        entry = await self.entries.find_one_and_update(
            {
                "$or": [
                    {
                        "status": "PENDING",
                        "next_attempt_at": {"$lte": timestamp},
                    },
                    {
                        "status": "PROCESSING",
                        "lease_expires_at": {"$lte": timestamp},
                    },
                ]
            },
            {
                "$set": {
                    "status": "PROCESSING",
                    "lease_token": token,
                    "lease_expires_at": timestamp + timedelta(seconds=lease_seconds),
                    "updated_at": timestamp,
                }
            },
            sort=[("next_attempt_at", 1), ("created_at", 1), ("_id", 1)],
            return_document=ReturnDocument.AFTER,
        )
        return entry

    async def complete(self, entry, indexed_revision, status="COMPLETED"):
        result = await self.entries.update_one(
            {
                "_id": entry["_id"],
                "status": "PROCESSING",
                "lease_token": entry["lease_token"],
            },
            {
                "$set": {
                    "status": status,
                    "indexed_revision": indexed_revision,
                    "completed_at": now(),
                    "updated_at": now(),
                },
                "$unset": {"lease_token": "", "lease_expires_at": "", "last_error": ""},
            },
        )
        return result.modified_count == 1

    async def defer(self, entry, error_code):
        attempts = int(entry.get("attempts") or 0) + 1
        delay_seconds = min(3600, 5 * (2 ** min(attempts - 1, 9)))
        result = await self.entries.update_one(
            {
                "_id": entry["_id"],
                "status": "PROCESSING",
                "lease_token": entry["lease_token"],
            },
            {
                "$set": {
                    "status": "PENDING",
                    "attempts": attempts,
                    "next_attempt_at": now() + timedelta(seconds=delay_seconds),
                    "last_error": error_code,
                    "updated_at": now(),
                },
                "$unset": {"lease_token": "", "lease_expires_at": ""},
            },
        )
        return result.modified_count == 1


defect_search_index_repository = DefectSearchIndexRepository()
