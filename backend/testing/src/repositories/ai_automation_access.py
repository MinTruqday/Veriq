import asyncio
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from src.core.database import database


class AIAutomationAccessRepository:
    LEASE_TTL_SECONDS = 90

    @property
    def leases(self):
        return database.value.ai_automation_access_leases

    async def acquire(self, scope_key: str, lease_id: str) -> bool:
        """Atomically admit a request unless revocation already fenced its scope."""
        timestamp = datetime.now(timezone.utc)
        expires_at = timestamp + timedelta(seconds=self.LEASE_TTL_SECONDS)
        try:
            result = await self.leases.update_one(
                {"_id": scope_key, "revoked": {"$ne": True}},
                {
                    "$setOnInsert": {"revoked": False, "created_at": timestamp},
                    "$addToSet": {"active_lease_ids": lease_id},
                    "$set": {
                        f"lease_expirations.{lease_id}": expires_at,
                        "updated_at": timestamp,
                    },
                },
                upsert=True,
            )
        except DuplicateKeyError:
            existing = await self.leases.find_one(
                {"_id": scope_key}, {"revoked": 1}
            )
            if not existing or existing.get("revoked") is True:
                return False
            retry = await self.leases.update_one(
                {"_id": scope_key, "revoked": {"$ne": True}},
                {
                    "$addToSet": {"active_lease_ids": lease_id},
                    "$set": {
                        f"lease_expirations.{lease_id}": expires_at,
                        "updated_at": timestamp,
                    },
                },
            )
            return retry.matched_count == 1
        return bool(result.matched_count or result.upserted_id)

    async def release(self, scope_key: str, lease_id: str) -> None:
        await self.leases.update_one(
            {"_id": scope_key},
            {
                "$pull": {"active_lease_ids": lease_id},
                "$unset": {f"lease_expirations.{lease_id}": ""},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )

    async def heartbeat(self, scope_key: str, lease_id: str) -> bool:
        """Extend an admitted request lease; a released/fenced lease is not recreated."""
        timestamp = datetime.now(timezone.utc)
        result = await self.leases.update_one(
            {"_id": scope_key, "active_lease_ids": lease_id},
            {
                "$set": {
                    f"lease_expirations.{lease_id}": timestamp
                    + timedelta(seconds=self.LEASE_TTL_SECONDS),
                    "updated_at": timestamp,
                }
            },
        )
        return result.matched_count == 1

    async def _prune_expired_leases(self, scope_key: str) -> None:
        state = await self.leases.find_one(
            {"_id": scope_key},
            {"active_lease_ids": 1, "lease_expirations": 1},
        )
        if not state:
            return
        now = datetime.now(timezone.utc)
        expirations = state.get("lease_expirations") or {}
        for lease_id in state.get("active_lease_ids") or []:
            expires_at = expirations.get(lease_id)
            if not isinstance(expires_at, datetime) or expires_at > now:
                continue
            await self.leases.update_one(
                {
                    "_id": scope_key,
                    "active_lease_ids": lease_id,
                    f"lease_expirations.{lease_id}": expires_at,
                },
                {
                    "$pull": {"active_lease_ids": lease_id},
                    "$unset": {f"lease_expirations.{lease_id}": ""},
                    "$set": {"updated_at": now},
                },
            )

    async def revoke_and_wait(self, scope_key: str, timeout_seconds: float = 20) -> bool:
        """Fence new requests, then wait for already-admitted API writes to finish."""
        timestamp = datetime.now(timezone.utc)
        await self.leases.update_one(
            {"_id": scope_key},
            {
                "$set": {
                    "revoked": True,
                    "revoked_at": timestamp,
                    "updated_at": timestamp,
                },
                "$setOnInsert": {"active_lease_ids": []},
                "$inc": {"revocation_epoch": 1},
            },
            upsert=True,
        )

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while True:
            await self._prune_expired_leases(scope_key)
            state = await self.leases.find_one(
                {"_id": scope_key}, {"active_lease_ids": 1}
            )
            if not state or not state.get("active_lease_ids"):
                return True
            if loop.time() >= deadline:
                return False
            await asyncio.sleep(0.05)

    async def allow_source(self, scope_key: str) -> bool:
        """Reopen a source scope only after all requests from its revoked epoch drained."""
        await self._prune_expired_leases(scope_key)
        state = await self.leases.find_one(
            {"_id": scope_key},
            {"revoked": 1, "active_lease_ids": 1, "revocation_epoch": 1},
        )
        if not state:
            return True
        if state.get("revoked") is not True:
            return True
        if state.get("active_lease_ids"):
            return False
        expected_epoch = state.get("revocation_epoch")
        reopen_filter = {
            "_id": scope_key,
            "revoked": True,
            "active_lease_ids": [],
        }
        if expected_epoch is None:
            reopen_filter["revocation_epoch"] = {"$exists": False}
        else:
            reopen_filter["revocation_epoch"] = expected_epoch
        result = await self.leases.update_one(
            reopen_filter,
            {
                "$set": {
                    "revoked": False,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$unset": {"revoked_at": ""},
            },
        )
        if result.matched_count:
            return True
        latest = await self.leases.find_one(
            {"_id": scope_key},
            {"revoked": 1, "active_lease_ids": 1, "revocation_epoch": 1},
        )
        return bool(
            latest
            and latest.get("revoked") is not True
            and not latest.get("active_lease_ids")
        )


ai_automation_access_repository = AIAutomationAccessRepository()
