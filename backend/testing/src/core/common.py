from datetime import datetime, timezone
from math import ceil
from uuid import uuid4

from fastapi import HTTPException

from src.clients.authentication import load_accounts, resolve_account
from src.core.auth import CurrentUser, ai_automation_context, archive_read_permissions, permissions_for_membership, permissions_for_role, project_permissions, roles_for_membership
from src.repositories.common import common_repository


RETRYABLE_ERROR_CODES = frozenset(['WORKER_UNAVAILABLE',
 'KNOWLEDGE_UNAVAILABLE',
 'KNOWLEDGE_INDEX_FAILED',
 'AI_PROVIDER_UNAVAILABLE',
 'PROPOSAL_APPLY_PARTIAL',
 'WORKER_JOB_FAILED'])
VIEWER_DEFECT_FIELDS = frozenset(['_id',
 'project_id',
 'defect_key',
 'title',
 'severity',
 'priority',
 'status',
 'assignee',
 'release',
 'release_id',
 'build',
 'build_id',
 'environment',
 'environment_id',
 'root_cause_category',
 'prevention_candidate',
 'revision',
 'created_at',
 'updated_at'])


def new_id(prefix: str):
    return f"{prefix}-{uuid4().hex}"


def now():
    return datetime.now(timezone.utc)


async def get_project_role(project_id, user_id):
    
    membership = await common_repository.find_membership(
        project_id,
        user_id,
        status='ACTIVE',
        projection={"project_role": 1, "project_roles": 1},
    )
    return (membership or {}).get("project_role")


async def get_project_roles(project_id, user_id):
    membership = await common_repository.find_membership(
        project_id,
        user_id,
        status='ACTIVE',
        projection={"project_role": 1, "project_roles": 1},
    )
    return roles_for_membership(membership)


def visible_defect(defect, role):
    if role != 'VIEWER':
        return defect
    return {key: value for key, value in defect.items() if key in VIEWER_DEFECT_FIELDS}


async def load_user_identities(user_ids):
    identifiers = sorted({str(value) for value in user_ids if value})
    return await load_accounts(identifiers)


async def resolve_user_reference(value):
    reference = str(value or "").strip()
    if not reference:
        return reference
    return await resolve_account(reference)


def envelope(
    data=None,
    revision=None,
    trace_id=None,
    operation_id=None,
    status='SUCCESS',
    error_code=None,
    retryable=False,
    state_after_failure=None,
    user_action_required=False,
    degraded_mode=None,
):
    meta = {"trace_id": trace_id or new_id('TRC')}
    if revision is not None:
        meta["revision"] = revision
    if operation_id is not None:
        meta["operation_id"] = operation_id
    operation = {
        "status": status,
        "error_code": error_code,
        "retryable": retryable,
        "state_after_failure": state_after_failure,
        "user_action_required": user_action_required,
    }
    if degraded_mode:
        operation["degraded_mode"] = degraded_mode
    meta["operation"] = operation
    return {"data": data, "meta": meta, **operation}


def page_payload(items, page, page_size, total):
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": ceil(total / page_size) if total else 0,
    }


def sort_spec(value, allowed, default="-updated_at"):
    selected = value or default
    descending = selected.startswith("-")
    field = selected[1:] if descending else selected
    if field not in allowed:
        raise HTTPException(
            status_code=422,
            detail={
                "code": 'INVALID_SORT_FIELD',
                "allowed": sorted(allowed),
            },
        )
    return field, -1 if descending else 1


def failure_metadata(code, status_code=500, detail=None):
    detail = detail if isinstance(detail, dict) else {}
    retryable = detail.get(
        "retryable",
        code in RETRYABLE_ERROR_CODES
        or status_code in [502, 503, 504],
    )
    state_after_failure = detail.get("state_after_failure") or (
        'UNCHANGED'
        if status_code < 500
        else 'RETRYABLE_FAILURE'
    )
    user_action_required = detail.get(
        "user_action_required", status_code in {409, 422, 403} or not retryable
    )
    return {
        "status": 'FAILED',
        "error_code": code,
        "retryable": retryable,
        "state_after_failure": state_after_failure,
        "user_action_required": user_action_required,
    }


async def audit(
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    project_id: str | None,
    details: dict | None = None,
):
    automation = ai_automation_context.get()
    event_details = details or {}
    if automation and automation.get("principal_id") == user_id:
        event_details = {
            **event_details,
            "actor_type": "AI_AUTOMATION",
            "initiated_by": automation.get("initiator_id"),
            "automation_definition_id": automation.get("definition_id"),
        }
    event = {
        "_id": new_id('AUD'),
        "project_id": project_id,
        "actor_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": event_details,
        "created_at": now(),
    }
    if automation and automation.get("principal_id") == user_id:
        event["automation_run_id"] = automation.get("run_id")
    return await common_repository.insert_audit_event(event)


async def get_project(
    project_id: str,
    user: CurrentUser,
    permission: str = 'project.read',
    assigned_role: str | None = None,
    assigned_user_id: str | None = None,
):
    
    
    project = await common_repository.find_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    membership = await common_repository.find_membership(project_id, user.id)
    grant = await common_repository.find_active_grant(
        project_id, user.id, 'ACTIVE', now()
    )
    grant_permissions = set(grant.get("permissions", [])) & project_permissions() if grant else set()
    if not membership and permission not in grant_permissions:
        await audit(
            user.id,
            'project_membership_required',
            'Project',
            project_id,
            project_id,
            {"permission": permission, "system_role": user.system_role.value},
        )
        raise HTTPException(status_code=403, detail={"code": 'PROJECT_MEMBERSHIP_REQUIRED'})
    if membership and membership.get("status") != 'ACTIVE' and permission not in grant_permissions:
        raise HTTPException(status_code=403, detail={"code": 'PROJECT_MEMBERSHIP_INACTIVE'})
    if project.get("administrative_status", 'ACTIVE') != 'ACTIVE':
        raise HTTPException(status_code=423, detail={"code": 'PROJECT_ADMINISTRATIVELY_SUSPENDED'})
    memberships_roles = roles_for_membership(membership)
    permissions = permissions_for_membership(membership, project.get("settings")) if (
        membership and membership.get("status") == 'ACTIVE'
    ) else set()
    assigned_access = (
        assigned_role is not None
        and membership is not None
        and assigned_role in memberships_roles
        and assigned_user_id == user.id
    )
    if (
        permission not in permissions
        and permission not in grant_permissions
        and not assigned_access
    ):
        await audit(
            user.id,
            'project_permission_denied',
            'Project',
            project_id,
            project_id,
            {
                "permission": permission,
                "project_role": membership.get("project_role") if membership else None,
            },
        )
        raise HTTPException(
            status_code=403, detail={"code": 'PROJECT_PERMISSION_DENIED', "permission": permission}
        )
    if (
        project.get("status", 'active').lower() == 'archived'
        and permission not in archive_read_permissions()
        and permission != 'project.restore'
    ):
        raise HTTPException(status_code=409, detail={"code": 'PROJECT_ARCHIVED'})
    if (
        project.get("status", 'active').lower() == 'archived'
        and permission in archive_read_permissions()
        and permission != 'project.read'
        and (project.get("settings") or {}).get("read_after_archive_policy", 'ALLOW_READ')
        == 'DENY_READ'
    ):
        raise HTTPException(status_code=403, detail={"code": 'PROJECT_ARCHIVED_READ_DENIED'})
    if permission in grant_permissions and permission not in permissions:
        return {
            **project,
            "access_context": {
                "mode": 'BREAK_GLASS',
                "grant_id": grant["_id"],
                "permissions": sorted(grant_permissions),
                "expires_at": grant["expires_at"],
                "reason": grant.get("reason"),
            },
        }
    return project


async def require_action_policy(
    project_id: str, user: CurrentUser, action: str, default_roles: set[str]
):
    
    project = await common_repository.find_project(project_id, {"settings": 1})
    membership = await common_repository.find_membership(
        project_id,
        user.id,
        status='ACTIVE',
        projection={"project_role": 1, "project_roles": 1},
    )
    if not project or not membership:
        raise HTTPException(
            status_code=403, detail={"code": 'PROJECT_MEMBERSHIP_REQUIRED'}
        )
    configured = (project.get("settings") or {}).get("action_policies", {}).get(action)
    allowed_roles = set(configured) if isinstance(configured, list) else default_roles
    if not roles_for_membership(membership).intersection(allowed_roles):
        raise HTTPException(
            status_code=403,
            detail={"code": 'PROJECT_ACTION_POLICY_DENIED', "action": action},
        )
    return project


async def get_project_entity(
    collection: str,
    entity_id: str,
    user: CurrentUser,
    permission: str,
    assigned_role: str | None = None,
    assigned_user_field: str | None = None,
):
    projection = {"_id": 1, "project_id": 1}
    if assigned_user_field:
        projection[assigned_user_field] = 1
    identity = await common_repository.find_entity_identity(
        collection, entity_id, projection
    )
    if not identity:
        raise HTTPException(
            status_code=404,
            detail={"code": 'ARTIFACT_NOT_FOUND'},
        )
    await get_project(
        identity["project_id"],
        user,
        permission,
        assigned_role=assigned_role,
        assigned_user_id=identity.get(assigned_user_field) if assigned_user_field else None,
    )
    entity = await common_repository.find_project_entity(
        collection, entity_id, identity["project_id"]
    )
    if not entity:
        raise HTTPException(
            status_code=404,
            detail={"code": 'ARTIFACT_NOT_FOUND'},
        )
    return entity


async def optimistic_patch(
    collection: str, entity_id: str, project_id: str, expected_revision: int, changes: dict
):
    cleaned = {
        key: value
        for key, value in changes.items()
        if value is not None and key != "expected_revision"
    }
    cleaned["updated_at"] = now()
    entity = await common_repository.optimistic_patch(
        collection,
        entity_id,
        project_id,
        expected_revision,
        cleaned,
        include_project_scope=collection != "projects",
    )
    if entity:
        return entity
    existing = await common_repository.find_entity(collection, entity_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu")
    raise HTTPException(
        status_code=409,
        detail={
            "code": 'REVISION_CONFLICT',
            "current_revision": existing.get("revision"),
        },
    )


async def next_key(project_id: str, sequence: str, prefix: str):
    value = await common_repository.next_counter(f"{project_id}:{sequence}")
    return f"{prefix}-{int(value['value']):04d}"


def plain_text(document):
    values = []

    def visit(node):
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                values.append(node["text"])
            for child in node.get("content", []):
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(document)
    return " ".join(values).strip()


def validate_doc(value):
    if (
        not isinstance(value, dict)
        or value.get("type") != "doc"
        or not isinstance(value.get("content", []), list)
    ):
        raise HTTPException(status_code=422, detail="Tiptap JSON không hợp lệ")
    return value
