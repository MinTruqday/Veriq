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

    async def correct_member_management_role(self):
        from src.core.auth import access_policy

        permission = "project.members.manage"
        while True:
            document = await database.value.project_access_control.find_one({"_id": "active"})
            access = ProjectAccessControl.model_validate(document)
            grants = {grant.role: set(grant.permissions) for grant in access.role_grants}
            if permission in grants.get("BA", set()) and permission not in grants.get("QA", set()):
                return
            grants.setdefault("BA", set()).add(permission)
            grants.setdefault("QA", set()).discard(permission)
            updated = access.model_copy(update={"revision": access.revision + 1, "role_grants": [grant.model_copy(update={"permissions": sorted(grants[grant.role])}) for grant in access.role_grants]})
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    result = await database.value.project_access_control.replace_one(
                        {"_id": "active", "revision": access.revision}, {**document, **updated.model_dump(), "updated_at": datetime.now(timezone.utc)}, session=session,
                    )
                    if result.modified_count:
                        await database.value.audit_events.insert_one({
                            "_id": f"MIG-member-management-role-{updated.revision}", "actor_id": "SYSTEM_MIGRATION",
                            "action": "project_member_management_role_corrected", "entity_type": "ProjectAccessControl", "entity_id": "active", "project_id": None,
                            "created_at": datetime.now(timezone.utc), "details": {"permission": permission, "removed_from": "QA", "granted_to": "BA", "previous_revision": access.revision},
                        }, session=session)
                        access_policy.cache_clear()
                        return

    async def ensure_reporting_capabilities(self):
        from src.schemas.project_access import ProjectCapability
        from src.core.auth import access_policy

        allowed = {
            "workreport.read": {"BA", "QA", "TESTER", "DEVELOPER", "VIEWER"},
            "workreport.write": {"BA", "QA", "TESTER", "DEVELOPER"},
            "workreport.ai": {"BA", "QA", "TESTER", "DEVELOPER"},
            "workreport.manage": {"BA"},
            "workreport.review": {"BA", "QA"},
            "workreport.publish": {"BA", "QA"},
        }
        while True:
            document = await database.value.project_access_control.find_one({"_id": "active"})
            access = ProjectAccessControl.model_validate(document)
            known = {item.name for item in access.capabilities}
            missing = set(allowed) - known
            if not missing:
                access_policy.cache_clear()
                return
            updated = access.model_copy(update={
                "revision": access.revision + 1,
                "capabilities": access.capabilities + [ProjectCapability(name=name, read_only=name.endswith(".read")) for name in sorted(missing)],
                "role_grants": [grant.model_copy(update={"permissions": sorted(set(grant.permissions) | {name for name in missing if grant.role in allowed[name]})}) for grant in access.role_grants],
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

    async def ensure_viewer_comment_capability(self):
        from src.core.auth import access_policy
        from src.schemas.project_access import ProjectCapability

        permissions = {"comment.read", "comment.create"}
        while True:
            document = await database.value.project_access_control.find_one({"_id": "active"})
            access = ProjectAccessControl.model_validate(document)
            known = {item.name for item in access.capabilities}
            missing = permissions - known
            grants = {grant.role: set(grant.permissions) for grant in access.role_grants}
            roles = {grant.role for grant in access.role_grants}
            current_viewer = grants.get("VIEWER", set())
            updated_viewer = current_viewer | permissions
            changed = bool(missing or updated_viewer != current_viewer or "VIEWER" not in roles)
            if not changed:
                access_policy.cache_clear()
                return
            grants["VIEWER"] = updated_viewer
            updated = access.model_copy(update={
                "revision": access.revision + 1,
                "capabilities": access.capabilities + [
                    ProjectCapability(name=name, read_only=name.endswith(".read"))
                    for name in sorted(missing)
                ],
                "role_grants": [
                    grant.model_copy(update={"permissions": sorted(grants[grant.role])})
                    for grant in access.role_grants
                ] + ([ProjectRoleGrant(role="VIEWER", permissions=sorted(grants["VIEWER"]))] if "VIEWER" not in roles else []),
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
                            {"_id": f"MIG-viewer-comments-{updated.revision}"},
                            {"$setOnInsert": {
                                "actor_id": "SYSTEM_MIGRATION",
                                "action": "viewer_comment_capability_added",
                                "entity_type": "ProjectAccessControl",
                                "entity_id": "active",
                                "project_id": None,
                                "created_at": timestamp,
                                "details": {"permissions": sorted(permissions), "previous_revision": access.revision},
                            }},
                            upsert=True,
                            session=session,
                        )
                        access_policy.cache_clear()
                        return

    @staticmethod
    def business_policy_preview(document):
        from src.core.auth import ProjectRole, ROLE_NEUTRAL_PERMISSIONS
        from src.repositories.legacy_business_roles import legacy_required_business_role

        access = ProjectAccessControl.model_validate(document)
        capabilities = []
        for capability in access.capabilities:
            required = legacy_required_business_role(capability.name)
            roles = required if isinstance(required, set) else {required} if required else set()
            if not roles and (capability.read_only or capability.name.endswith(".read") or capability.name in ROLE_NEUTRAL_PERMISSIONS):
                roles = set(ProjectRole)
            role_names = sorted(role.value for role in roles)
            responsibility = None
            if capability.name == "requirement.approve":
                role_names = ["BA"]
                responsibility = "business_confirmation"
            if capability.name in {"release.close", "qualitygate.decide", "qualitygate.accept_risk", "qualitygate.override"}:
                role_names = ["BA", "QA"]
                responsibility = "release_decision"
            capabilities.append(capability.model_copy(update={
                "business_roles": role_names, "responsibility": responsibility,
            }))
        grants = []
        for grant in access.role_grants:
            permissions = set(grant.permissions)
            if grant.role == "QA":
                permissions.discard("requirement.approve")
            if grant.role == "BA":
                permissions.add("requirement.approve")
            if grant.role in {"BA", "QA"}:
                permissions.update(item.name for item in capabilities if item.responsibility == "release_decision")
            grants.append(grant.model_copy(update={"permissions": sorted(permissions)}))
        return access.model_copy(update={"revision": access.revision + 1, "capabilities": capabilities, "role_grants": grants})

    async def ensure_business_policy(self):
        from src.core.auth import access_policy

        while True:
            document = await database.value.project_access_control.find_one({"_id": "active"})
            if document.get("business_policy_initialized"):
                return
            updated = self.business_policy_preview(document)
            timestamp = datetime.now(timezone.utc)
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    result = await database.value.project_access_control.replace_one(
                        {"_id": "active", "revision": document["revision"]},
                        {**document, **updated.model_dump(), "business_policy_initialized": True, "updated_at": timestamp},
                        session=session,
                    )
                    if result.modified_count:
                        await database.value.audit_events.insert_one({
                            "_id": f"MIG-business-responsibilities-{updated.revision}",
                            "actor_id": "SYSTEM_MIGRATION", "action": "business_policy_initialized",
                            "entity_type": "ProjectAccessControl", "entity_id": "active", "project_id": None,
                            "created_at": timestamp,
                            "details": {"previous_policy": document, "new_revision": updated.revision},
                        }, session=session)
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
        ProjectAccessControl.model_validate(existing)
        corrected = await self._apply_build_role_correction(existing)
        status = "MIGRATED" if corrected is not existing else "ALREADY_MIGRATED"
        return {"status": status, "revision": corrected["revision"]}


project_access_repository = ProjectAccessRepository()
