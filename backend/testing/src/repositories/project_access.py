from datetime import datetime, timezone

from src.core.database import database
from src.schemas.project_access import ProjectAccessControl, ProjectRoleGrant


class ProjectAccessRepository:
    @staticmethod
    def _correct_build_role_grants(document):
        access = ProjectAccessControl.model_validate(document)
        build_write = {"build.create", "build.manage"}
        grants = {grant.role: set(grant.permissions) for grant in access.role_grants}
        grants.setdefault("QA", set()).difference_update(build_write)
        grants.setdefault("TESTER", set()).difference_update(build_write)
        grants.setdefault("DEVELOPER", set()).update(build_write)
        roles = {grant.role for grant in access.role_grants}
        if all(
            grants[grant.role] == set(grant.permissions)
            for grant in access.role_grants
        ) and "DEVELOPER" in roles:
            return document
        updated = access.model_copy(
            update={
                "revision": access.revision + 1,
                "role_grants": [
                    grant.model_copy(update={"permissions": sorted(grants[grant.role])})
                    for grant in access.role_grants
                ]
                + (
                    [
                        ProjectRoleGrant(
                            role="DEVELOPER",
                            permissions=sorted(grants["DEVELOPER"]),
                        )
                    ]
                    if "DEVELOPER" not in roles
                    else []
                ),
            }
        )
        return ProjectAccessControl.model_validate(updated.model_dump()).model_dump()

    async def _apply_build_role_correction(self, document):
        while True:
            corrected = self._correct_build_role_grants(document)
            if corrected is document:
                return document
            timestamp = datetime.now(timezone.utc)
            from_revision = document["revision"]
            to_revision = corrected["revision"]
            event_id = f"MIG-project-access-v{to_revision}-build-role"
            replacement = {
                **document,
                **corrected,
                "updated_at": timestamp,
            }
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    result = await database.value.project_access_control.replace_one(
                        {"_id": "active", "revision": from_revision},
                        replacement,
                        session=session,
                    )
                    if result.modified_count == 1:
                        await database.value.audit_events.update_one(
                            {"_id": event_id},
                            {
                                "$setOnInsert": {
                                    "actor_id": "SYSTEM_MIGRATION",
                                    "action": "project_access_role_grants_corrected",
                                    "entity_type": "ProjectAccessControl",
                                    "entity_id": "active",
                                    "project_id": None,
                                    "created_at": timestamp,
                                    "details": {
                                        "from_revision": from_revision,
                                        "to_revision": to_revision,
                                        "permissions": [
                                            "build.create",
                                            "build.manage",
                                        ],
                                        "removed_from": ["QA", "TESTER"],
                                        "granted_to": "DEVELOPER",
                                        "legacy_policy_retained": True,
                                    },
                                }
                            },
                            upsert=True,
                            session=session,
                        )
                        return replacement
            document = await database.value.project_access_control.find_one(
                {"_id": "active"}
            )
            if not document:
                raise RuntimeError("PROJECT_ACCESS_POLICY_MISSING_AFTER_MIGRATION")

    async def migrate_legacy(self):
        existing = await database.value.project_access_control.find_one({"_id": "active"})
        if not existing:
            legacy = await database.value.runtime_policies.find_one({"_id": "access_control"})
            if not legacy or not isinstance(legacy.get("values"), dict):
                raise RuntimeError("PROJECT_ACCESS_MIGRATION_SOURCE_MISSING")
            access = ProjectAccessControl.from_legacy(legacy["values"])
            timestamp = datetime.now(timezone.utc)
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    await database.value.project_access_control.update_one(
                        {"_id": "active"},
                        {
                            "$setOnInsert": {
                                **access.model_dump(),
                                "migrated_at": timestamp,
                                "migration_source": "runtime_policies/access_control",
                            }
                        },
                        upsert=True,
                        session=session,
                    )
                    await database.value.audit_events.update_one(
                        {"_id": "MIG-project-access-control-v1"},
                        {
                            "$setOnInsert": {
                                "actor_id": "SYSTEM_MIGRATION",
                                "action": "project_access_migrated",
                                "entity_type": "ProjectAccessControl",
                                "entity_id": "active",
                                "project_id": None,
                                "created_at": timestamp,
                                "details": {
                                    "source_retained": True,
                                    "capability_count": len(access.capabilities),
                                    "role_count": len(access.role_grants),
                                },
                            }
                        },
                        upsert=True,
                        session=session,
                    )
            existing = await database.value.project_access_control.find_one(
                {"_id": "active"}
            )
        ProjectAccessControl.model_validate(existing)
        corrected = await self._apply_build_role_correction(existing)
        status = "MIGRATED" if corrected is not existing else "ALREADY_MIGRATED"
        return {"status": status, "revision": corrected["revision"]}


project_access_repository = ProjectAccessRepository()
