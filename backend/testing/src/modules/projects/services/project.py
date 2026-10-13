from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.authentication import get_project_creation_policy
from src.core.auth import archive_read_permissions, permissions_for_role, project_permissions
from src.core.common import (
    audit,
    get_project,
    load_user_identities,
    new_id,
    now,
    optimistic_patch,
    resolve_user_reference,
)
from src.repositories.project import project_repository
from src.modules.projects.services.project_progress import task_summaries





def project_access(project, membership, grant):
    
    role_permissions = (
        permissions_for_role(membership["project_role"], project.get("settings"))
        if membership
        else set()
    )
    grant_permissions = set(grant.get("permissions", [])) & project_permissions() if grant else set()
    if project.get("status", "active").lower() == "archived":
        allowed = archive_read_permissions() | {"project.restore"}
        if (project.get("settings") or {}).get("read_after_archive_policy", "ALLOW_READ") == "DENY_READ":
            allowed = {"project.read", "project.restore"}
        role_permissions &= allowed
        grant_permissions &= allowed
    return {
        **project,
        "current_membership": membership,
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
        "settings": project.get("settings", {}),
    }


class ProjectService:
    @staticmethod
    async def create(payload, user):
        
        
        policy = await get_project_creation_policy()
        if policy == 'ADMIN_ONLY' and not user.is_system_admin:
            raise HTTPException(
                status_code=403,
                detail={"code": 'SYSTEM_PERMISSION_DENIED'},
            )
        timestamp = now()
        project = {
            "_id": new_id('PRJ'),
            **payload.model_dump(),
            "created_by": user.id,
            "status": 'active',
            "project_completion_percent": 0,
            "revision": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        membership = {
            "_id": new_id('PM'),
            "project_id": project["_id"],
            "user_id": user.id,
            "project_role": 'QA',
            "status": 'ACTIVE',
            "membership_revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await project_repository.create_with_creator(project, membership)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409, detail={"code": 'PROJECT_KEY_EXISTS'}
            )
        await audit(
            user.id,
            'project_created',
            'Project',
            project["_id"],
            project["_id"],
            {"creator_membership_id": membership["_id"]},
        )
        return {
            **project,
            "task_summary": {"total": 0, "completed": 0, "in_progress": 0, "blocked": 0, "cancelled": 0, "applicable_total": 0, "completion_percent": None},
            "current_membership": membership,
            "current_permissions": sorted(
                permissions_for_role('QA', project["settings"])
            ),
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
        query = {"_id": {"$in": list(set(by_project) | set(by_grant))}}
        if status and status != 'all':
            query["status"] = status
        if query_text:
            query["$or"] = [
                {"name": {"$regex": query_text, "$options": "i"}},
                {"key": {"$regex": query_text, "$options": "i"}},
            ]
        projects = await project_repository.list_projects(query, limit)
        summaries = await task_summaries([project["_id"] for project in projects])
        return [
            {
                **project_access(project, by_project.get(project["_id"]), by_grant.get(project["_id"])),
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
        return {
            **project_access(project, membership, grant),
            "project_completion_percent": int(project.get("project_completion_percent", 0)),
            "task_summary": summaries[project_id],
        }

    @staticmethod
    async def update(project_id, payload, user):
        
        await get_project(project_id, user, 'project.update')
        if payload.settings is not None:
            await get_project(project_id, user, 'project.settings.manage')
        updated = await optimistic_patch(
            "projects", project_id, project_id, payload.expected_revision, payload.model_dump()
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
        changes = payload.model_dump(exclude_none=True)
        changes.pop("expected_revision", None)
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
        await get_project(
            project_id, user, 'project.members.read'
        )
        members = await project_repository.list_members(project_id)
        identities = await load_user_identities(item.get("user_id") for item in members)
        return [
            {
                **member,
                "user": identities.get(member.get("user_id")),
                "user_label": (identities.get(member.get("user_id")) or {}).get("label") or member.get("user_id"),
            }
            for member in members
        ]

    @staticmethod
    async def add_member(project_id, payload, user, invited=False):
        
        
        await get_project(project_id, user, 'project.members.manage')
        member_user_id = await resolve_user_reference(payload.user_id)
        timestamp = now()
        membership = {
            "_id": new_id('PM'),
            "project_id": project_id,
            "user_id": member_user_id,
            "project_role": payload.project_role,
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
        desired_role = changes.get("project_role", previous.get("project_role"))
        desired_status = changes.get("status", previous.get("status"))
        was_active_qa = (
            previous.get("project_role") == 'QA'
            and previous.get("status") == 'ACTIVE'
        )
        remains_active_qa = desired_role == 'QA' and desired_status == 'ACTIVE'
        if was_active_qa and not remains_active_qa:
            qa_count = await project_repository.count_members_by_role_status(
                project_id, 'QA', 'ACTIVE'
            )
            if qa_count <= 1:
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'PROJECT_LAST_QA_REQUIRED'},
                )
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
        remains_active_qa = (
            membership.get("project_role") == 'QA'
            and membership.get("status") == 'ACTIVE'
        )
        if was_active_qa and not remains_active_qa:
            qa_count = await project_repository.count_members_by_role_status(
                project_id, 'QA', 'ACTIVE'
            )
            if qa_count == 0:
                await project_repository.restore_member(membership, previous, now())
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'PROJECT_LAST_QA_REQUIRED'},
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
        if (
            membership.get("project_role") == 'QA'
            and membership.get("status") == 'ACTIVE'
        ):
            qa_count = await project_repository.count_members_by_role_status(
                project_id, 'QA', 'ACTIVE'
            )
            if qa_count <= 1:
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'PROJECT_LAST_QA_REQUIRED'},
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
