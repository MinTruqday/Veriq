from datetime import datetime, timezone

from src.core.database import database
from src.schemas.project_access import ProjectAccessControl


class ProjectAccessRepository:
    async def migrate_legacy(self):
        """Atomic, repeatable cutover. Keep the original document for recovery."""
        existing = await database.value.project_access_control.find_one({"_id": "active"})
        if existing:
            ProjectAccessControl.model_validate(existing)
            return {"status": "ALREADY_MIGRATED", "revision": existing["revision"]}
        legacy = await database.value.runtime_policies.find_one({"_id": "access_control"})
        if not legacy or not isinstance(legacy.get("values"), dict):
            raise RuntimeError("PROJECT_ACCESS_MIGRATION_SOURCE_MISSING")
        access = ProjectAccessControl.from_legacy(legacy["values"])
        timestamp = datetime.now(timezone.utc)
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                await database.value.project_access_control.update_one(
                    {"_id": "active"},
                    {"$setOnInsert": {**access.model_dump(), "migrated_at": timestamp, "migration_source": "runtime_policies/access_control"}},
                    upsert=True, session=session,
                )
                await database.value.audit_events.update_one(
                    {"_id": "MIG-project-access-control-v1"},
                    {"$setOnInsert": {"actor_id": "SYSTEM_MIGRATION", "action": "project_access_migrated", "entity_type": "ProjectAccessControl", "entity_id": "active", "project_id": None, "created_at": timestamp, "details": {"source_retained": True, "capability_count": len(access.capabilities), "role_count": len(access.role_grants)}}},
                    upsert=True, session=session,
                )
        return {"status": "MIGRATED", "revision": access.revision}


project_access_repository = ProjectAccessRepository()
