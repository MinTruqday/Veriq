from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.authentication import get_project_creation_policy
from src.core.auth import (
    access_policy,
    archive_read_permissions,
    business_role_allows,
    permissions_for_membership,
    permissions_for_role,
    project_permissions,
    responsibility_allows,
    roles_for_membership,
)
from src.core.common import (
    audit,
    build_audit_event,
    get_project,
    load_user_identities,
    new_id,
    now,
    optimistic_patch,
    resolve_user_reference,
)
from src.modules.projects.services.project_progress import task_summaries
from src.modules.projects.services.project_responsibilities import (
    assignable_responsibilities,
    validate_project_responsibilities,
)
from src.repositories.project import project_repository


def _validate_project_dates(planned_start_at, planned_end_at):
    if planned_start_at and planned_end_at:
        try:
            valid_range = planned_end_at > planned_start_at
        except TypeError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "PROJECT_SCHEDULE_TIMEZONE_MISMATCH"},
            ) from exc
        if not valid_range:
            raise HTTPException(
                status_code=422, detail={"code": "PROJECT_SCHEDULE_INVALID"}
            )


def project_access(project, membership, grant):
    policy = access_policy()
    available_project_roles = sorted(policy.get("role_permissions", {}))
    configurable_role_settings = {}
    setting_rules = [
        *(
            {"setting": setting, "enabled": True, "effect": "ALLOW", **rule}
            for setting, rule in policy.get("policy_permissions", {}).items()
        ),
        *(
            {**rule, "effect": "ALLOW"}
            for rule in policy.get("conditional_permissions", [])
        ),
        *(
            {**rule, "effect": "DENY"}
            for rule in policy.get("conditional_denials", [])
        ),
    ]
    for rule in setting_rules:
        setting = str(rule.get("setting") or "").strip()
        role = str(rule.get("role") or "").strip().upper()
        permissions = sorted(set(rule.get("permissions", [])) & project_permissions())
        if not setting or role not in available_project_roles or not permissions:
            continue
        configurable_role_settings.setdefault(setting, []).append({
            "role": role,
            "enabled": bool(rule.get("enabled")),
            "effect": rule["effect"],
            "permissions": permissions,
        })
    role_permissions = permissions_for_membership(membership, project.get("settings"))
    grant_permissions = set(grant.get("permissions", [])) & project_permissions() if grant else set()
    active_roles = roles_for_membership(membership) if membership and membership.get("status") == "ACTIVE" else set()
    effective_roles = roles_for_membership(membership)
    public_membership = (
        {
            **membership,
            "project_role": next(iter(effective_roles)) if len(effective_roles) == 1 else None,
            "project_roles": sorted(effective_roles),
        }
        if membership
        else None
    )
    grant_permissions = {item for item in grant_permissions if business_role_allows(item, active_roles) and responsibility_allows(item, membership.get("user_id") if membership else None, project.get("settings"))}
    if project.get("status", "active").lower() == "archived":
        allowed = archive_read_permissions() | {"project.restore"}
        if (project.get("settings") or {}).get("read_after_archive_policy", "ALLOW_READ") == "DENY_READ":
            allowed = {"project.read", "project.restore"}
        role_permissions &= allowed
        grant_permissions &= allowed
    return {
        **project,
        "available_project_roles": available_project_roles,
        "configurable_role_settings": [
            {"key": key, "rules": rules}
            for key, rules in sorted(configurable_role_settings.items())
        ],
        "current_membership": public_membership,
        "current_permissions": sorted(role_permissions | grant_permissions),
        "access_context": (
            {
                "mode": 'BREAK_GLASS',
                "grant_id": grant["_id"],
                "permissions": sorted(grant_permissions),
                "expires_at": grant["expires_at"],
                "reason": grant.get("reason"),
            }
            if grant and not grant_permissions.issubset(role_permissions)
            else None
        ),
    }


def project_settings(project):
    return {
        "project_id": project["_id"],
        "name": project.get("name"),
        "description": project.get("description", ""),
        "project_type": project.get("project_type"),
        "locale": project.get("locale"),
        "timezone": project.get("timezone"),
        "automation_framework": project.get("automation_framework"),
        "automation_language": project.get("automation_language"),
        "settings": project.get("settings", {}),
    }


class ProjectService:
    @staticmethod
    def _project_setup_permissions():
        return {
            "project.read",
            "project.update",
            "project.settings.manage",
            "project.members.read",
            "project.members.manage",
        }

    @staticmethod
    def _project_setup_role():
        required_permissions = ProjectService._project_setup_permissions()
        role_permissions = access_policy().get("role_permissions", {})
        candidates = [
            role
            for role in role_permissions
            if required_permissions.issubset(permissions_for_role(role))
        ]
        if not candidates:
            raise HTTPException(
                status_code=503,
                detail={"code": "PROJECT_SETUP_CAPABILITIES_UNAVAILABLE"},
            )
        return min(
            candidates,
            key=lambda role: (len(permissions_for_role(role)), role),
        )

    @staticmethod
    async def can_create_project(user):
        policy = await get_project_creation_policy()
        if user.is_system_admin:
            return True
        if policy == 'ADMIN_ONLY':
            return False
        memberships = await project_repository.list_active_memberships(
            user.id, "ACTIVE"
        )
        if not memberships:
            return True
        project_ids = {item["project_id"] for item in memberships}
        projects = await project_repository.list_projects(
            {"_id": {"$in": list(project_ids)}}, len(project_ids)
        )
        settings_by_project = {
            project["_id"]: project.get("settings") or {}
            for project in projects
        }
        required_permissions = ProjectService._project_setup_permissions()
        return any(
            required_permissions.issubset(
                permissions_for_membership(
                    membership,
                    settings_by_project.get(membership["project_id"]),
                )
            )
            for membership in memberships
        )

    @staticmethod
    async def create(payload, user):
        if not await ProjectService.can_create_project(user):
            raise HTTPException(
                status_code=403,
                detail={"code": 'SYSTEM_PERMISSION_DENIED'},
            )
        timestamp = now()
        _validate_project_dates(payload.planned_start_at, payload.planned_end_at)
        setup_role = ProjectService._project_setup_role()
        await validate_project_responsibilities(
            payload.settings,
            initial_members={
                user.id: {
                    "status": "ACTIVE",
                    "project_role": setup_role,
                    "project_roles": [setup_role],
                }
            },
        )
        project = {
            "_id": new_id('PRJ'),
            **payload.model_dump(),
            "project_lead_user_id": None,
            "created_by": user.id,
            "status": 'active',
            "project_completion_percent": 0,
            "revision": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        creator_membership = {
            "_id": new_id('PM'),
            "project_id": project["_id"],
            "user_id": user.id,
            "project_role": setup_role,
            "project_roles": [setup_role],
            "status": 'ACTIVE',
            "membership_revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            memberships = [creator_membership]
            project_created_event = build_audit_event(
                user.id,
                'project_created',
                'Project',
                project["_id"],
                project["_id"],
                {
                    "creator_membership_id": creator_membership["_id"],
                    "creator_setup_role": setup_role,
                },
            )
            await project_repository.create_with_memberships(
                project, memberships, project_created_event
            )
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409, detail={"code": 'PROJECT_KEY_EXISTS'}
            )
        return {
            **project,
            "task_summary": {"total": 0, "completed": 0, "in_progress": 0, "blocked": 0, "cancelled": 0, "applicable_total": 0, "completion_percent": None},
            "current_membership": creator_membership,
            "current_permissions": sorted(permissions_for_membership(creator_membership, project["settings"])),
        }

    @staticmethod
    async def list(query_text, status, limit, user):
        
        
        memberships = await project_repository.list_active_memberships(
            user.id, 'ACTIVE'
        )
        by_project = {item["project_id"]: item for item in memberships}
        grants = await project_repository.list_active_grants(
            user.id, 'ACTIVE', now()
        )
        by_grant = {item["project_id"]: item for item in grants}
        query = {"_id": {"$in": list(by_project)}}
        if status and status != 'all':
            query["status"] = status
        if query_text:
            query["$or"] = [
                {"name": {"$regex": query_text, "$options": "i"}},
                {"key": {"$regex": query_text, "$options": "i"}},
            ]
        projects = await project_repository.list_projects(query, limit)
        summaries = await task_summaries([project["_id"] for project in projects])
        lead_ids = [project.get("project_lead_user_id") for project in projects]
        lead_identities = await load_user_identities(item for item in lead_ids if item)
        return [
            {
                **project_access(project, by_project.get(project["_id"]), by_grant.get(project["_id"])),
                "project_lead_label": (
                    (lead_identities.get(project["project_lead_user_id"]) or {}).get("label")
                    or (lead_identities.get(project["project_lead_user_id"]) or {}).get("email")
                    if project.get("project_lead_user_id")
                    else None
                ),
                "project_completion_percent": int(project.get("project_completion_percent", 0)),
                "task_summary": summaries.get(project["_id"]),
            }
            for project in projects
        ]

    @staticmethod
    async def list_invitations(user):
        invitations = await project_repository.list_invitations(
            user.id, 'INVITED'
        )
        project_ids = {item["project_id"] for item in invitations}
        projects = await project_repository.list_project_summaries(project_ids)
        projects_by_id = {item["_id"]: item for item in projects}
        return [
            {**invitation, "project": projects_by_id.get(invitation["project_id"])}
            for invitation in invitations
            if invitation["project_id"] in projects_by_id
        ]

    @staticmethod
    async def get(project_id, user):
        
        project = await get_project(project_id, user, 'project.read')
        membership = await project_repository.find_member(
            project_id, user.id, status='ACTIVE'
        )
        grant = await project_repository.find_active_grant(
            project_id, user.id, 'ACTIVE', now()
        )
        summaries = await task_summaries([project_id])
        lead_identity = (
            await load_user_identities([project["project_lead_user_id"]])
            if project.get("project_lead_user_id")
            else {}
        ).get(project.get("project_lead_user_id"), {})
        return {
            **project_access(project, membership, grant),
            "project_lead_label": lead_identity.get("label") or lead_identity.get("email"),
            "project_completion_percent": int(project.get("project_completion_percent", 0)),
            "task_summary": summaries[project_id],
        }

    @staticmethod
    async def update(project_id, payload, user):
        current = await get_project(project_id, user, 'project.update')
        if payload.settings is not None:
            await get_project(project_id, user, 'project.settings.manage')
            await validate_project_responsibilities(payload.settings, project_id)
        changes = payload.model_dump(exclude_unset=True)
        changes.pop("expected_revision", None)
        await ProjectService._validate_project_lead(project_id, changes)
        if {"planned_start_at", "planned_end_at"} & set(changes):
            _validate_project_dates(
                changes.get("planned_start_at", current.get("planned_start_at")),
                changes.get("planned_end_at", current.get("planned_end_at")),
            )
        updated = await optimistic_patch(
            "projects", project_id, project_id, payload.expected_revision, changes
        )
        await audit(
            user.id,
            'project_updated',
            'Project',
            project_id,
            project_id,
        )
        return updated

    @staticmethod
    async def get_settings(project_id, user):
        
        project = await get_project(
            project_id, user, 'project.settings.manage'
        )
        return project_settings(project), project.get("revision", 1)

    @staticmethod
    async def update_settings(project_id, payload, user):
        
        await get_project(project_id, user, 'project.settings.manage')
        if payload.settings is not None:
            await validate_project_responsibilities(payload.settings, project_id)
        changes = payload.model_dump(exclude_unset=True)
        changes.pop("expected_revision", None)
        await ProjectService._validate_project_lead(project_id, changes)
        if not changes:
            raise HTTPException(
                status_code=422, detail={"code": 'SETTINGS_EMPTY'}
            )
        updated = await optimistic_patch(
            "projects", project_id, project_id, payload.expected_revision, changes
        )
        await audit(
            user.id,
            'project_settings_updated',
            'ProjectSettings',
            project_id,
            project_id,
        )
        return project_settings(updated), updated["revision"]

    @staticmethod
    async def _validate_project_lead(project_id, changes):
        lead_user_id = changes.get("project_lead_user_id")
        if "project_lead_user_id" not in changes or lead_user_id is None:
            return
        membership = await project_repository.find_member(
            project_id, lead_user_id, status="ACTIVE"
        )
        if not membership:
            raise HTTPException(
                status_code=422,
                detail={"code": "PROJECT_LEAD_MUST_BE_ACTIVE_MEMBER"},
            )

    @staticmethod
    async def archive(project_id, payload, user):
        
        await get_project(project_id, user, 'project.archive')
        updated = await optimistic_patch(
            "projects",
            project_id,
            project_id,
            payload.expected_revision,
            {
                "status": 'archived',
                "archived_by": user.id,
                "archived_at": now(),
                "archive_reason": payload.reason,
            },
        )
        await audit(
            user.id,
            'project_archived',
            'Project',
            project_id,
            project_id,
            {"reason": payload.reason},
        )
        return updated

    @staticmethod
    async def restore(project_id, payload, user):
        
        project = await get_project(project_id, user, 'project.restore')
        if project.get("status") == 'active':
            return project
        updated = await optimistic_patch(
            "projects",
            project_id,
            project_id,
            payload.expected_revision,
            {
                "status": 'active',
                "restored_by": user.id,
                "restored_at": now(),
                "restore_reason": payload.reason,
            },
        )
        await audit(
            user.id,
            'project_restored',
            'Project',
            project_id,
            project_id,
            {"reason": payload.reason},
        )
        return updated

    @staticmethod
    async def list_members(project_id, user):
        project = await get_project(
            project_id, user, 'project.members.read'
        )
        members = await project_repository.list_members(project_id)
        identities = await load_user_identities(item.get("user_id") for item in members)
        return [
            {
                **member,
                "project_role": next(iter(roles_for_membership(member)))
                if len(roles_for_membership(member)) == 1
                else None,
                "project_roles": sorted(roles_for_membership(member)),
                "permissions": sorted(
                    permissions_for_membership(member, project.get("settings"))
                ),
                "assignable_responsibilities": assignable_responsibilities(member),
                "user": identities.get(member.get("user_id")),
                "user_label": (identities.get(member.get("user_id")) or {}).get("label") or member.get("user_id"),
            }
            for member in members
        ]

    @staticmethod
    async def add_member(project_id, payload, user, invited=False):
        await get_project(project_id, user, 'project.members.manage')
        if payload.project_role not in access_policy().get("role_permissions", {}):
            raise HTTPException(422, detail={"code": "PROJECT_ROLE_UNAVAILABLE"})
        member_user_id = await resolve_user_reference(payload.user_id)
        timestamp = now()
        membership = {
            "_id": new_id('PM'),
            "project_id": project_id,
            "user_id": member_user_id,
            "project_role": payload.project_role,
            "project_roles": [payload.project_role],
            "status": 'INVITED' if invited else 'ACTIVE',
            "membership_revision": 1,
            **({"invited_by": user.id, "invited_at": timestamp} if invited else {}),
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await project_repository.add_member(membership)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409,
                detail={"code": 'PROJECT_MEMBERSHIP_EXISTS'},
            )
        await audit(
            user.id,
            'project_member_invited'
            if invited
            else 'project_member_added',
            'ProjectMember',
            membership["_id"],
            project_id,
            {"user_id": member_user_id, "project_role": payload.project_role},
        )
        return membership

    @staticmethod
    async def accept_invitation(invitation_id, user):
        
        
        timestamp = now()
        membership = await project_repository.transition_invitation(
            invitation_id,
            user.id,
            'INVITED',
            {"status": 'ACTIVE', "accepted_at": timestamp, "updated_at": timestamp},
        )
        if not membership:
            raise HTTPException(
                status_code=404,
                detail={"code": 'INVITATION_NOT_FOUND'},
            )
        await audit(
            user.id,
            'project_invitation_accepted',
            'ProjectMember',
            membership["_id"],
            membership["project_id"],
        )
        return membership

    @classmethod
    async def accept_project_invitation(cls, project_id, member_user_id, user):
        
        if user.id != member_user_id:
            raise HTTPException(
                status_code=403,
                detail={"code": 'INVITATION_OWNER_REQUIRED'},
            )
        membership = await project_repository.find_member(
            project_id,
            user.id,
            status='INVITED',
            projection={"_id": 1},
        )
        if not membership:
            raise HTTPException(
                status_code=404,
                detail={"code": 'INVITATION_NOT_FOUND'},
            )
        return await cls.accept_invitation(membership["_id"], user)

    @staticmethod
    async def decline_invitation(invitation_id, user):
        
        
        timestamp = now()
        membership = await project_repository.transition_invitation(
            invitation_id,
            user.id,
            'INVITED',
            {"status": 'DECLINED', "declined_at": timestamp, "updated_at": timestamp},
        )
        if not membership:
            raise HTTPException(
                status_code=404,
                detail={"code": 'INVITATION_NOT_FOUND'},
            )
        await audit(
            user.id,
            'project_invitation_declined',
            'ProjectMember',
            membership["_id"],
            membership["project_id"],
        )
        return membership

    @staticmethod
    async def leave(project_id, user):
        
        
        timestamp = now()
        membership = await project_repository.transition_membership(
            project_id,
            user.id,
            'ACTIVE',
            {"status": 'LEFT', "left_at": timestamp, "updated_at": timestamp},
        )
        if not membership:
            raise HTTPException(
                status_code=404,
                detail={"code": 'PROJECT_MEMBERSHIP_NOT_FOUND'},
            )
        await audit(
            user.id,
            'project_member_left',
            'ProjectMember',
            membership["_id"],
            project_id,
        )
        return membership

    @staticmethod
    async def resend_invitation(project_id, member_user_id, user):
        
        await get_project(project_id, user, 'project.members.manage')
        timestamp = now()
        membership = await project_repository.update_invitation(
            project_id,
            member_user_id,
            'INVITED',
            {"invited_by": user.id, "invited_at": timestamp, "updated_at": timestamp},
            {"invite_send_count": 1},
        )
        if not membership:
            raise HTTPException(
                status_code=409,
                detail={"code": 'INVITATION_NOT_PENDING'},
            )
        await audit(
            user.id,
            'project_invitation_resent',
            'ProjectMember',
            membership["_id"],
            project_id,
        )
        return membership

    @staticmethod
    async def cancel_invitation(project_id, member_user_id, user):
        
        await get_project(project_id, user, 'project.members.manage')
        timestamp = now()
        membership = await project_repository.update_invitation(
            project_id,
            member_user_id,
            'INVITED',
            {
                "status": 'CANCELLED',
                "cancelled_by": user.id,
                "cancelled_at": timestamp,
                "updated_at": timestamp,
            },
        )
        if not membership:
            raise HTTPException(
                status_code=409,
                detail={"code": 'INVITATION_NOT_PENDING'},
            )
        await audit(
            user.id,
            'project_invitation_cancelled',
            'ProjectMember',
            membership["_id"],
            project_id,
        )
        return membership

    @staticmethod
    async def update_member(project_id, member_user_id, payload, user):
        await get_project(project_id, user, 'project.members.manage')
        if (
            payload.project_role is not None
            and payload.project_role not in access_policy().get("role_permissions", {})
        ):
            raise HTTPException(422, detail={"code": "PROJECT_ROLE_UNAVAILABLE"})
        previous = await project_repository.find_member(project_id, member_user_id)
        if not previous:
            raise HTTPException(
                status_code=404, detail={"code": 'ENTITY_NOT_FOUND'}
            )
        if previous.get("membership_revision") != payload.expected_revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": 'REVISION_CONFLICT',
                    "current_revision": previous.get("membership_revision"),
                },
            )
        changes = {key: value for key, value in payload.model_dump().items() if value is not None and key != "expected_revision"}
        if "project_role" in changes and "project_roles" not in changes:
            changes["project_roles"] = [changes["project_role"]]
        changes["updated_at"] = now()
        membership = await project_repository.update_member(
            project_id, member_user_id, payload.expected_revision, changes
        )
        if not membership:
            existing = await project_repository.find_member(project_id, member_user_id)
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail={"code": 'ENTITY_NOT_FOUND'},
                )
            raise HTTPException(
                status_code=409,
                detail={
                    "code": 'REVISION_CONFLICT',
                    "current_revision": existing["membership_revision"],
                },
            )
        await audit(
            user.id,
            'project_member_updated',
            'ProjectMember',
            membership["_id"],
            project_id,
            {"user_id": member_user_id, **changes},
        )
        return membership

    @staticmethod
    async def remove_member(project_id, member_user_id, user):
        
        
        
        await get_project(project_id, user, 'project.members.manage')
        membership = await project_repository.find_member(project_id, member_user_id)
        if not membership:
            raise HTTPException(
                status_code=404, detail={"code": 'ENTITY_NOT_FOUND'}
            )
        await project_repository.remove_member(project_id, member_user_id)
        await audit(
            user.id,
            'project_member_removed',
            'ProjectMember',
            membership["_id"],
            project_id,
            {"user_id": member_user_id},
        )
        return {"removed": True, "user_id": member_user_id}
