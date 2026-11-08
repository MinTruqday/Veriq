import hmac
import json
from contextvars import ContextVar
from enum import Enum
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pymongo import MongoClient

from src.clients.authentication import session_is_valid
from src.core.configuration import settings
from src.schemas.contracts.common import CurrentUser, SystemRole
from src.schemas.project_access import ProjectAccessControl

ai_automation_context = ContextVar("ai_automation_context", default=None)
_access_policy_context = ContextVar("project_access_policy", default=None)


class ProjectRole(str, Enum):
    QA = "QA"
    TESTER = "TESTER"
    BA = "BA"
    DEVELOPER = "DEVELOPER"
    VIEWER = "VIEWER"


ROLE_NEUTRAL_PERMISSIONS = {
    "attachment.delete_own_unreferenced",
    "attachment.manage",
    "attachment.moderate",
    "attachment.upload",
    "comment.create",
    "comment.delete_own",
    "comment.moderate",
    "comment.update_own",
    "notification.mark_read",
    "notification.preferences.manage",
    "notification.watch.manage",
    "report.export",
    "requirement_document.download",
}


@lru_cache(maxsize=1)
def _access_client():
    return MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)


@lru_cache(maxsize=8)
def _validated_access_policy(serialized):
    return ProjectAccessControl.model_validate_json(serialized).permission_values()


def access_policy():
    cached = _access_policy_context.get()
    if cached is not None:
        return cached
    document = _access_client()[settings.TESTING_DB_NAME].project_access_control.find_one({"_id": "active"})
    if not isinstance(document, dict):
        raise RuntimeError("Thiếu dữ liệu phân quyền dự án đã chuyển đổi")
    fields = {key: document[key] for key in ProjectAccessControl.model_fields if key in document}
    values = _validated_access_policy(json.dumps(fields, sort_keys=True))
    _access_policy_context.set(values)
    return values


def refresh_access_policy():
    _access_policy_context.set(None)


def clear_access_policy():
    refresh_access_policy()
    _validated_access_policy.cache_clear()


access_policy.cache_clear = clear_access_policy


def project_permissions():
    return set(access_policy().get("project_permissions", []))


def archive_read_permissions():
    return set(access_policy().get("read_only_permissions", [])) | {"testdata.read"}


ASSIGNED_DRAFT_PERMISSIONS = frozenset({
    "testcase.create", "testcase.update", "testcase.submit_review",
    "testcase.lint", "testscenario.update",
})
ASSIGNED_OWNER_PERMISSIONS = ASSIGNED_DRAFT_PERMISSIONS | frozenset({
    "attachment.manage", "defect.update", "defect.trace.manage",
    "defect.transition.developer", "testmonitor.control.update",
})


def required_business_role(permission: str) -> set[str]:
    return {
        str(role).strip().upper()
        for role in access_policy().get("business_role_permissions", {}).get(permission, [])
        if str(role).strip()
    }


def business_role_allows(permission: str, roles: set[str]) -> bool:
    required = required_business_role(permission)
    normalized_roles = {str(role).strip().upper() for role in roles if str(role).strip()}
    return not required or bool(required.intersection(normalized_roles))


def permissions_for_role(role: ProjectRole | str, settings_value: dict | None = None):
    normalized = str(getattr(role, "value", role) or "").strip().upper()
    if not normalized:
        return set()
    values = access_policy()
    permissions = set(values.get("role_permissions", {}).get(normalized, []))
    project_settings = settings_value or {}
    for key, rule in values.get("policy_permissions", {}).items():
        if (
            isinstance(rule, dict)
            and rule.get("role") == normalized
            and project_settings.get(key) is True
        ):
            permissions.update(rule.get("permissions", []))
    for rule in values.get("conditional_permissions", []):
        if (
            isinstance(rule, dict)
            and rule.get("role") == normalized
            and project_settings.get(rule.get("setting")) is rule.get("enabled")
        ):
            permissions.update(rule.get("permissions", []))
    denied = set()
    for rule in values.get("conditional_denials", []):
        if (
            isinstance(rule, dict)
            and rule.get("role") == normalized
            and project_settings.get(rule.get("setting")) is rule.get("enabled")
        ):
            denied.update(rule.get("permissions", []))
    overrides = project_settings.get("permission_overrides", {}).get(normalized, {})
    known_permissions = project_permissions()
    permissions.update(item for item in overrides.get("allow", []) if item in known_permissions)
    permissions.difference_update(denied | set(overrides.get("deny", [])))
    return {item for item in permissions if business_role_allows(item, {normalized})}


def roles_for_membership(membership: dict | None) -> set[str]:
    if not membership:
        return set()
    primary = membership.get("project_role")
    if primary:
        normalized = str(primary).strip().upper()
        return {normalized} if normalized else set()
    roles = membership.get("project_roles")
    if not isinstance(roles, list):
        roles = []
    legacy_roles = {str(role).strip().upper() for role in roles if str(role).strip()}
    return legacy_roles if len(legacy_roles) == 1 else set()


def permission_explicitly_denied(permission, roles, settings_value=None):
    project_settings = settings_value or {}
    for role in roles:
        if permission in project_settings.get("permission_overrides", {}).get(role, {}).get("deny", []):
            return True
        for rule in access_policy().get("conditional_denials", []):
            if rule.get("role") == role and project_settings.get(rule.get("setting")) is rule.get("enabled") and permission in rule.get("permissions", []):
                return True
    return False


def responsibility_allows(permission, user_id, settings_value=None):
    responsibility = access_policy().get("responsibility_permissions", {}).get(permission)
    if not responsibility:
        return True
    return ((settings_value or {}).get("responsibilities") or {}).get(responsibility) == user_id


def permissions_for_membership(membership: dict | None, settings_value: dict | None = None):
    if not membership:
        return set()
    if membership.get("status") != "ACTIVE":
        return set()
    permissions = set().union(
        *(permissions_for_role(role, settings_value) for role in roles_for_membership(membership))
    )
    responsibilities = (settings_value or {}).get("responsibilities") or {}
    for permission, responsibility in access_policy().get("responsibility_permissions", {}).items():
        if responsibilities.get(responsibility) != membership.get("user_id"):
            permissions.discard(permission)
    return permissions


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/xac-thuc/dang-nhap", auto_error=False)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    ai_automation_run_id: str | None = Header(default=None, alias="X-AI-Automation-Run"),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
):
    ai_automation_context.set(None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "AUTH_REQUIRED"}
        )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("uid") or payload.get("sub")
        email = payload.get("email") or payload.get("sub", "")
        if not user_id:
            raise ValueError
        role_value = payload.get("system_role", "USER")
        session_id = payload.get("sid")
        if session_id and not await session_is_valid(str(session_id), str(user_id)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "SESSION_REVOKED"}
            )
        user = CurrentUser(
            _id=str(user_id), email=str(email), system_role=SystemRole(str(role_value).upper())
        )
        user._access_token = token
        token_run_id = str(payload.get("ai_automation_run_id") or "")
        if token_run_id:
            if (
                not ai_automation_run_id
                or ai_automation_run_id != token_run_id
                or not x_internal_token
                or not hmac.compare_digest(x_internal_token, settings.SECRET_KEY)
            ):
                raise HTTPException(
                    status_code=403, detail={"code": "AI_AUTOMATION_IDENTITY_INVALID"}
                )
            try:
                from src.clients.ai_automation import automation_run_is_active

                worker_revision = payload.get("ai_automation_worker_revision")
                if worker_revision is not None and (
                    isinstance(worker_revision, bool)
                    or not isinstance(worker_revision, int)
                    or worker_revision < 1
                ):
                    raise HTTPException(
                        status_code=403,
                        detail={"code": "AI_AUTOMATION_WORKER_REVISION_INVALID"},
                    )
                if worker_revision is None and request.method not in {"GET", "HEAD"}:
                    raise HTTPException(
                        status_code=403,
                        detail={"code": "AI_AUTOMATION_WORKER_FENCE_REQUIRED"},
                    )
                run_is_active = await automation_run_is_active(
                    token_run_id, worker_revision
                )
            except HTTPException:
                raise
            except Exception as error:
                raise HTTPException(
                    status_code=503, detail={"code": "AI_AUTOMATION_STATUS_UNAVAILABLE"}
                ) from error
            if not run_is_active:
                raise HTTPException(
                    status_code=409, detail={"code": "AI_AUTOMATION_RUN_NOT_ACTIVE"}
                )
            from uuid import uuid4

            from src.repositories.ai_automation_access import ai_automation_access_repository

            source_document_ids = payload.get("ai_automation_source_document_ids")
            if (
                not isinstance(source_document_ids, list)
                or len(source_document_ids) > 100
                or any(
                    not isinstance(value, str) or not value or len(value) > 200
                    for value in source_document_ids
                )
                or len(source_document_ids) != len(set(source_document_ids))
            ):
                raise HTTPException(
                    status_code=403, detail={"code": "AI_AUTOMATION_SOURCE_SCOPE_INVALID"}
                )
            lease_scopes = [f"run:{token_run_id}"] + [
                f"source:{document_id}" for document_id in source_document_ids
            ]
            acquired_leases = []
            try:
                for scope_key in lease_scopes:
                    lease_id = str(uuid4())
                    admitted = await ai_automation_access_repository.acquire(scope_key, lease_id)
                    if not admitted:
                        for acquired_scope, acquired_id in acquired_leases:
                            await ai_automation_access_repository.release(
                                acquired_scope, acquired_id
                            )
                        raise HTTPException(
                            status_code=409, detail={"code": "AI_AUTOMATION_RUN_ACCESS_REVOKED"}
                        )
                    acquired_leases.append((scope_key, lease_id))
            except Exception as error:
                if isinstance(error, HTTPException):
                    raise
                for acquired_scope, acquired_id in acquired_leases:
                    try:
                        await ai_automation_access_repository.release(acquired_scope, acquired_id)
                    except Exception:
                        pass
                raise HTTPException(
                    status_code=503, detail={"code": "AI_AUTOMATION_ACCESS_LEASE_UNAVAILABLE"}
                ) from error
            request.state.ai_automation_leases = acquired_leases
            user._ai_automation_run_id = token_run_id
            user._ai_automation_trigger = str(payload.get("ai_automation_trigger") or "")
            user._ai_automation_source_event_id = str(
                payload.get("ai_automation_source_event_id") or ""
            )
            user._ai_automation_initiator_id = str(payload.get("ai_automation_initiator_id") or "")
            user._ai_automation_definition_id = str(
                payload.get("ai_automation_definition_id") or ""
            )
            publication_project_id = str(payload.get("ai_automation_publication_project_id") or "")
            publication_permissions = payload.get("ai_automation_publication_permissions")
            allowed_publication_permissions = {
                "requirement.submit_review",
                "requirement.approve",
                "testcase.submit_review",
                "testcase.approve",
                "proposal.approve",
                "testplan.approve",
                "release.close",
                "testmonitor.snapshot.create",
                "testcompletion.create",
                "testadequacy.execution_feedback.record",
            }
            if publication_project_id and isinstance(publication_permissions, list):
                user._ai_automation_publication_permissions = sorted(
                    set(map(str, publication_permissions)) & allowed_publication_permissions
                )
            ai_automation_context.set(
                {
                    "run_id": token_run_id,
                    "source_event_id": user._ai_automation_source_event_id,
                    "initiator_id": user._ai_automation_initiator_id,
                    "definition_id": user._ai_automation_definition_id,
                    "principal_id": user.id,
                    "publication_project_id": publication_project_id,
                    "publication_permissions": user._ai_automation_publication_permissions,
                }
            )
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "TOKEN_EXPIRED"}
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "TOKEN_INVALID"}
        )


def require_authenticated(user: CurrentUser = Depends(get_current_user)):
    return user
