from datetime import datetime, timezone

from src.core.database import database
from src.schemas.project_access import ProjectAccessControl


LEGACY_PERMISSION_RENAMES = {
    "defect.transition.developer": "defect.transition.resolve"
}


def _canonicalize_legacy_permissions(access):
    capabilities = []
    capability_names = set()
    renamed_capabilities = 0
    for item in sorted(
        access.capabilities,
        key=lambda value: value.name in LEGACY_PERMISSION_RENAMES,
    ):
        target = LEGACY_PERMISSION_RENAMES.get(item.name, item.name)
        renamed_capabilities += target != item.name
        if target in capability_names:
            continue
        capability_names.add(target)
        capabilities.append(
            item.model_copy(update={"name": target}) if target != item.name else item
        )
    role_grants = [
        grant.model_copy(update={
            "permissions": sorted({
                LEGACY_PERMISSION_RENAMES.get(value, value)
                for value in grant.permissions
            })
        })
        for grant in access.role_grants
    ]
    setting_grants = [
        grant.model_copy(update={
            "permissions": sorted({
                LEGACY_PERMISSION_RENAMES.get(value, value)
                for value in grant.permissions
            })
        })
        for grant in access.setting_grants
    ]
    changed = bool(
        renamed_capabilities
        or any(
            grant.permissions != original.permissions
            for grant, original in zip(role_grants, access.role_grants)
        )
        or any(
            grant.permissions != original.permissions
            for grant, original in zip(setting_grants, access.setting_grants)
        )
    )
    return access.model_copy(update={
        "capabilities": capabilities,
        "role_grants": role_grants,
        "setting_grants": setting_grants,
    }), renamed_capabilities, changed


class ProjectAccessRepository:
    async def migrate_legacy_permission_names(self):
        from src.core.auth import access_policy

        while True:
            document = await database.value.project_access_control.find_one({"_id": "active"})
            access = ProjectAccessControl.model_validate(document)
            canonical, renamed_capabilities, changed = _canonicalize_legacy_permissions(access)
            if not changed:
                access_policy.cache_clear()
                return
            updated = canonical.model_copy(update={
                "revision": access.revision + 1,
            })
            timestamp = datetime.now(timezone.utc)
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    result = await database.value.project_access_control.replace_one(
                        {"_id": "active", "revision": access.revision},
                        {**document, **updated.model_dump(), "updated_at": timestamp},
                        session=session,
                    )
                    if result.modified_count:
                        await database.value.audit_events.update_one(
                            {"_id": f"MIG-canonical-project-permissions-{updated.revision}"},
                            {"$setOnInsert": {
                                "actor_id": "SYSTEM_MIGRATION",
                                "action": "project_permission_names_canonicalized",
                                "entity_type": "ProjectAccessControl",
                                "entity_id": "active",
                                "project_id": None,
                                "created_at": timestamp,
                                "details": {
                                    "revision": updated.revision,
                                    "legacy_capabilities_renamed": renamed_capabilities,
                                },
                            }},
                            upsert=True,
                            session=session,
                        )
                        access_policy.cache_clear()
                        return

    async def ensure_private_defect_capability(self):
        from src.core.auth import ROLE_NEUTRAL_PERMISSIONS, access_policy
        from src.schemas.project_access import ProjectCapability

        while True:
            document = await database.value.project_access_control.find_one({"_id": "active"})
            access = ProjectAccessControl.model_validate(document)
            capability_names = {item.name for item in access.capabilities}
            grants = {grant.role: set(grant.permissions) for grant in access.role_grants}
            writable_permissions = {
                item.name
                for item in access.capabilities
                if not item.read_only and item.name not in ROLE_NEUTRAL_PERMISSIONS
            }
            private_read_roles = {
                role
                for role, permissions in grants.items()
                if "defect.read" in permissions and permissions & writable_permissions
            }
            updated_grants = {
                role: permissions | {"defect.private.read"}
                if role in private_read_roles
                else permissions
                for role, permissions in grants.items()
            }
            changed = (
                "defect.private.read" not in capability_names
                or any(updated_grants[role] != grants[role] for role in grants)
            )
            if not changed:
                access_policy.cache_clear()
                return
            updated = access.model_copy(update={
                "revision": access.revision + 1,
                "capabilities": access.capabilities + (
                    [ProjectCapability(name="defect.private.read", read_only=True)]
                    if "defect.private.read" not in capability_names
                    else []
                ),
                "role_grants": [
                    grant.model_copy(update={"permissions": sorted(updated_grants[grant.role])})
                    for grant in access.role_grants
                ],
            })
            timestamp = datetime.now(timezone.utc)
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    result = await database.value.project_access_control.replace_one(
                        {"_id": "active", "revision": access.revision},
                        {**document, **updated.model_dump(), "updated_at": timestamp},
                        session=session,
                    )
                    if result.modified_count:
                        await database.value.audit_events.update_one(
                            {"_id": f"MIG-defect-private-read-{updated.revision}"},
                            {"$setOnInsert": {
                                "actor_id": "SYSTEM_MIGRATION",
                                "action": "defect_private_read_capability_added",
                                "entity_type": "ProjectAccessControl",
                                "entity_id": "active",
                                "project_id": None,
                                "created_at": timestamp,
                                "details": {
                                    "permission": "defect.private.read",
                                    "granted_roles": sorted(private_read_roles),
                                    "previous_revision": access.revision,
                                },
                            }},
                            upsert=True,
                            session=session,
                        )
                        access_policy.cache_clear()
                        return

    async def ensure_reporting_capabilities(self):
        from src.core.auth import access_policy
        from src.schemas.project_access import ProjectCapability

        names = {
            "workreport.read",
            "workreport.write",
            "workreport.ai",
            "workreport.manage",
            "workreport.review",
            "workreport.publish",
        }
        while True:
            document = await database.value.project_access_control.find_one({"_id": "active"})
            access = ProjectAccessControl.model_validate(document)
            known = {item.name for item in access.capabilities}
            missing = names - known
            if not missing:
                access_policy.cache_clear()
                return
            updated = access.model_copy(update={
                "revision": access.revision + 1,
                "capabilities": access.capabilities + [ProjectCapability(name=name, read_only=name.endswith(".read")) for name in sorted(missing)],
            })
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    result = await database.value.project_access_control.replace_one(
                        {"_id": "active", "revision": access.revision},
                        {**document, **updated.model_dump(), "updated_at": datetime.now(timezone.utc)}, session=session,
                    )
                    if result.modified_count:
                        await database.value.audit_events.insert_one({
                            "_id": f"MIG-reporting-capabilities-{updated.revision}",
                            "actor_id": "SYSTEM_MIGRATION", "action": "reporting_capabilities_added",
                            "entity_type": "ProjectAccessControl", "entity_id": "active", "project_id": None,
                            "created_at": datetime.now(timezone.utc), "details": {"added": sorted(missing), "previous_revision": access.revision},
                        }, session=session)
                        access_policy.cache_clear()
                        return

    async def ensure_read_only_comment_capabilities(self):
        from src.core.auth import ROLE_NEUTRAL_PERMISSIONS, access_policy
        from src.schemas.project_access import ProjectCapability

        permissions = {"comment.read", "comment.create"}
        while True:
            document = await database.value.project_access_control.find_one({"_id": "active"})
            access = ProjectAccessControl.model_validate(document)
            known = {item.name for item in access.capabilities}
            missing = permissions - known
            grants = {grant.role: set(grant.permissions) for grant in access.role_grants}
            read_only = {
                item.name for item in access.capabilities if item.read_only
            }
            writable = {
                item.name for item in access.capabilities if not item.read_only
            } - ROLE_NEUTRAL_PERMISSIONS
            comment_roles = {
                role
                for role, role_permissions in grants.items()
                if role_permissions & read_only and not role_permissions & writable
            }
            updated_grants = {
                role: role_permissions | permissions
                if role in comment_roles
                else role_permissions
                for role, role_permissions in grants.items()
            }
            changed = bool(
                missing
                or any(updated_grants[role] != grants[role] for role in grants)
            )
            if not changed:
                access_policy.cache_clear()
                return
            updated = access.model_copy(update={
                "revision": access.revision + 1,
                "capabilities": access.capabilities + [
                    ProjectCapability(name=name, read_only=name.endswith(".read"))
                    for name in sorted(missing)
                ],
                "role_grants": [
                    grant.model_copy(update={"permissions": sorted(updated_grants[grant.role])})
                    for grant in access.role_grants
                ],
            })
            timestamp = datetime.now(timezone.utc)
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    result = await database.value.project_access_control.replace_one(
                        {"_id": "active", "revision": access.revision},
                        {**document, **updated.model_dump(), "updated_at": timestamp},
                        session=session,
                    )
                    if result.modified_count:
                        await database.value.audit_events.update_one(
                            {"_id": f"MIG-read-only-comments-{updated.revision}"},
                            {"$setOnInsert": {
                                "actor_id": "SYSTEM_MIGRATION",
                                "action": "read_only_comment_capability_added",
                                "entity_type": "ProjectAccessControl",
                                "entity_id": "active",
                                "project_id": None,
                                "created_at": timestamp,
                                "details": {
                                    "permissions": sorted(permissions),
                                    "roles": sorted(comment_roles),
                                    "previous_revision": access.revision,
                                },
                            }},
                            upsert=True,
                            session=session,
                        )
                        access_policy.cache_clear()
                        return

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
        access = ProjectAccessControl.model_validate(existing)
        return {"status": "READY", "revision": access.revision}


project_access_repository = ProjectAccessRepository()
