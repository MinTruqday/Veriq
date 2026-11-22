from datetime import datetime, timezone

from src.core.database import database
from src.core.auth import requires_project_approval
from src.schemas.project_access import (
    ProjectAccessControl,
    ProjectCapability,
    ProjectRoleGrant,
)


LEGACY_PERMISSION_RENAMES = {
    "defect.transition.developer": "defect.transition.resolve"
}

PROJECT_ROLE_MIGRATION = {
    "BA": "BA",
    "QA": "QA",
    "QC": "TESTER",
    "DEVELOPER": "DEVELOPER",
    "SYSTEM_ADMIN": None,
}

ROLE_PERMISSION_PREFIXES = {
    "BA": ("requirement.", "requirement_document.", "acceptance_criteria.", "business_rule.", "requirement_dependency."),
    "QA": ("testanalysis.", "testplan.", "teststrategy.", "testcompletion.", "teststatusreport.", "testmonitor.", "risk.", "measurement.", "impact.", "processimprovement.", "qualityevaluation.", "statisticalquality.", "reviewsession."),
    "QC": ("testscenario.", "testcase.", "testcondition.", "testdata.", "testsuite.", "automation.", "regression.", "apiartifact.", "testrun.", "testresult.", "defect."),
    "DEVELOPER": ("build.", "environmentincident.", "causalanalysis."),
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
    async def migrate_project_roles(self):
        from src.clients.authentication import load_accounts
        db = database.value
        document = await db.project_access_control.find_one({"_id": "active"})
        policy_version = int(document.get("project_role_policy_version", 0))
        if policy_version >= 2:
            return
        active_access = ProjectAccessControl.model_validate(document)
        source_document = document
        if policy_version == 1:
            source_document = await db.project_access_control.find_one(
                {"_id": "before_project_role_policy_v1"}
            )
            if not source_document:
                raise RuntimeError("Cannot restore the project role policy source")
        access = ProjectAccessControl.model_validate(source_document)
        projects = await db.projects.find(
            {}, {"created_by": 1, "project_owner_user_id": 1, "settings": 1}
        ).to_list(length=None)
        members = await db.project_members.find(
            {}, {"user_id": 1, "project_id": 1, "project_role": 1, "project_roles": 1, "status": 1}
        ).to_list(length=None)
        creator_ids = sorted({project["created_by"] for project in projects if project.get("created_by")})
        account_ids = sorted(
            set(creator_ids)
            | {member["user_id"] for member in members if member.get("user_id")}
            | {project["project_owner_user_id"] for project in projects if project.get("project_owner_user_id")}
        )
        accounts = {}
        for offset in range(0, len(account_ids), 100):
            accounts.update(await load_accounts(account_ids[offset:offset + 100]))
        if any("system_role" not in account or "is_active" not in account for account in accounts.values()):
            raise RuntimeError("Authentication must expose account status before migrating project owners")
        capabilities = [
            *access.capabilities,
            *[
                ProjectCapability(name=name)
                for name in (
                    "testscenario.approve",
                    "testscenario.review",
                    "testadequacy.approve",
                    "testadequacy.review",
                    "workreport.approve",
                )
                if name not in {capability.name for capability in access.capabilities}
            ],
        ]
        read_only_permissions = {
            capability.name for capability in access.capabilities if capability.read_only
        }
        previous_roles = {grant.role: set(grant.permissions) for grant in access.role_grants}
        grants = []
        for role, source_role in PROJECT_ROLE_MIGRATION.items():
            permissions = previous_roles.get(source_role, set()) if source_role else set()
            permissions = {
                permission for permission in permissions
                if not requires_project_approval(permission)
                and self._role_permission_allowed(
                    role, permission, permission in read_only_permissions
                )
            }
            if role == "QA":
                permissions.update({
                    permission for permission in ("testscenario.review", "testadequacy.review")
                    if permission in {capability.name for capability in capabilities}
                })
            grants.append(ProjectRoleGrant(
                role=role,
                permissions=sorted(permissions),
            ))
        setting_grants = []
        role_mapping = {source: target for target, source in PROJECT_ROLE_MIGRATION.items() if source}
        for grant in access.setting_grants:
            role = role_mapping.get(grant.role)
            if not role:
                continue
            permissions = [
                permission for permission in grant.permissions
                if not requires_project_approval(permission)
                and self._role_permission_allowed(
                    role, permission, permission in read_only_permissions
                )
            ]
            if permissions:
                setting_grants.append(grant.model_copy(update={"role": role, "permissions": permissions}))
        policy = access.model_copy(update={
            "role_grants": grants, "setting_grants": setting_grants, "capabilities": capabilities,
            "revision": active_access.revision + 1,
        })
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                result = await db.project_access_control.replace_one(
                    {"_id": "active", "revision": active_access.revision},
                    {**document, **policy.model_dump(), "project_role_policy_version": 2},
                    session=session,
                )
                if result.modified_count != 1:
                    raise RuntimeError("Project access policy changed during migration")
                if not await db.project_access_control.find_one(
                    {"_id": "before_project_role_policy_v2"}, session=session
                ):
                    await db.project_access_control.insert_one(
                        {**document, "_id": "before_project_role_policy_v2"}, session=session,
                    )
                for project in projects:
                    creator_id = project.get("created_by")
                    creator = accounts.get(creator_id, {})
                    candidate_ids = [
                        project.get("project_owner_user_id"),
                        creator_id,
                    ]
                    owner_id = None
                    for candidate_id in candidate_ids:
                        candidate = accounts.get(candidate_id, {})
                        member = await db.project_members.find_one({
                            "project_id": project["_id"],
                            "user_id": candidate_id,
                            "status": "ACTIVE",
                        }, session=session)
                        if (
                            candidate_id
                            and member
                            and candidate.get("is_active")
                            and candidate.get("system_role") == "USER"
                        ):
                            owner_id = candidate_id
                            break
                    changes = {}
                    if owner_id != project.get("project_owner_user_id"):
                        changes["project_owner_user_id"] = owner_id
                    settings = project.get("settings") or {}
                    overrides = settings.get("permission_overrides") or {}
                    migrated_overrides = self._migrated_permission_overrides(overrides)
                    if migrated_overrides != overrides:
                        changes["settings.permission_overrides"] = migrated_overrides
                    if changes:
                        await db.audit_events.insert_one({
                            "_id": f"MIG-project-role-v2-project-{project['_id']}",
                            "action": "project_role_settings_migrated",
                            "actor_id": "SYSTEM_MIGRATION",
                            "entity_type": "Project",
                            "entity_id": project["_id"],
                            "project_id": project["_id"],
                            "created_at": datetime.now(timezone.utc),
                            "details": {
                                "previous_owner_user_id": project.get("project_owner_user_id"),
                                "project_owner_user_id": owner_id,
                                "previous_permission_overrides": overrides,
                                "permission_overrides": migrated_overrides,
                            },
                        }, session=session)
                        await db.projects.update_one(
                            {"_id": project["_id"]},
                            {"$set": changes},
                            session=session,
                        )
                async for member in db.project_members.find({}, session=session):
                    previous = {member.get("project_role"), *(member.get("project_roles") or [])}
                    roles = self._migrated_roles(previous)
                    account = accounts.get(member.get("user_id"), {})
                    if account.get("system_role") == "ADMIN":
                        roles = ["SYSTEM_ADMIN"]
                    owner = await db.projects.find_one({
                        "_id": member["project_id"], "project_owner_user_id": member["user_id"],
                    }, projection={"_id": 1}, session=session)
                    status = member.get("status")
                    if not roles and not owner:
                        status = "CANCELLED" if status == "INVITED" else "INACTIVE"
                    previous_roles = sorted(previous - {None})
                    if roles == previous_roles and status == member.get("status"):
                        continue
                    await db.audit_events.insert_one({
                        "_id": f"MIG-project-role-v2-{member['_id']}",
                        "action": "project_membership_role_migrated",
                        "actor_id": "SYSTEM_MIGRATION",
                        "entity_type": "ProjectMember",
                        "entity_id": member["_id"],
                        "project_id": member["project_id"],
                        "created_at": datetime.now(timezone.utc),
                        "details": {"previous_roles": previous_roles, "roles": roles,
                                    "system_role": account.get("system_role"),
                                    "previous_status": member.get("status"), "status": status},
                    }, session=session)
                    await db.project_members.update_one(
                        {"_id": member["_id"]},
                        {"$set": {"project_roles": roles, "status": status,
                                  "project_role": roles[0] if len(roles) == 1 else None},
                         "$inc": {"membership_revision": 1, "assignment_fence_revision": 1}},
                        session=session,
                    )
                for collection, field in (
                    (db.project_notification_rules, "target_roles"),
                    (db.planning_workflows, "transitions.allowed_roles"),
                    (db.measurement_definitions, "owner_role"),
                ):
                    async for record in collection.find(
                        {field: {"$in": ["VIEWER", "TESTER"]}}, session=session,
                    ):
                        if field == "transitions.allowed_roles":
                            changes = {"transitions": [
                                {**transition, "allowed_roles": self._migrated_roles(transition["allowed_roles"])}
                                for transition in record["transitions"]
                            ]}
                        elif field == "owner_role":
                            changes = {field: "QC" if record[field] == "TESTER" else None}
                        else:
                            changes = {field: self._migrated_roles(record[field])}
                            if not changes[field]:
                                changes["enabled_events"] = []
                        await db.audit_events.insert_one({
                            "_id": f"MIG-project-role-v2-{collection.name}-{record['_id']}",
                            "action": "project_role_reference_migrated",
                            "actor_id": "SYSTEM_MIGRATION",
                            "entity_type": collection.name,
                            "entity_id": record["_id"],
                            "project_id": record.get("project_id"),
                            "created_at": datetime.now(timezone.utc),
                            "details": {key: record.get(key) for key in changes},
                        }, session=session)
                        await collection.update_one(
                            {"_id": record["_id"]},
                            {"$set": changes, "$inc": {"revision": 1}},
                            session=session,
                        )
        from src.core.auth import access_policy

        access_policy.cache_clear()

    @staticmethod
    def _role_permission_allowed(role, permission, read_only=False):
        if read_only:
            return True
        permission = str(permission)
        for owner, prefixes in ROLE_PERMISSION_PREFIXES.items():
            if permission.startswith(prefixes):
                if permission.endswith(".review") and owner == "QC":
                    return role == "QA"
                return role == owner
        return True

    @staticmethod
    def _migrated_roles(roles):
        role_mapping = {
            **{role: role for role in PROJECT_ROLE_MIGRATION},
            **{source: target for target, source in PROJECT_ROLE_MIGRATION.items() if source},
        }
        return sorted({role_mapping[role] for role in roles if role in role_mapping})

    @staticmethod
    def _migrated_permission_overrides(overrides):
        values = {role: dict(value) for role, value in overrides.items()}
        values.pop("VIEWER", None)
        tester = values.pop("TESTER", None)
        if tester:
            qc = values.setdefault("QC", {})
            for key in ("allow", "deny"):
                qc[key] = sorted(set(qc.get(key, [])) | set(tester.get(key, [])))
        return values

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
