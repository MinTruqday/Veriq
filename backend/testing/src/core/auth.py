import hmac
from contextvars import ContextVar
from enum import Enum
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo import MongoClient

from src.clients.authentication import session_is_valid
from src.core.configuration import settings
from src.schemas.contracts.common import CurrentUser, SystemRole


ai_automation_context = ContextVar("ai_automation_context", default=None)


class ProjectRole(str, Enum):
    QA = "QA"
    TESTER = "TESTER"
    BA = "BA"
    DEVELOPER = "DEVELOPER"
    VIEWER = "VIEWER"


@lru_cache(maxsize=1)
def access_policy():
    client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        document = client[settings.TESTING_DB_NAME].runtime_policies.find_one(
            {"_id": "access_control"}, {"_id": 0, "values": 1}
        )
    finally:
        client.close()
    if not isinstance(document, dict) or not isinstance(document.get("values"), dict):
        raise RuntimeError("Thiếu chính sách phân quyền dự án")
    return document["values"]


def project_permissions():
    return set(access_policy().get("project_permissions", []))


def archive_read_permissions():
    return set(access_policy().get("read_only_permissions", [])) | {"testdata.read"}


def permissions_for_role(role: ProjectRole | str, settings_value: dict | None = None):
    try:
        normalized = role if isinstance(role, ProjectRole) else ProjectRole(str(role).upper())
    except ValueError:
        return set()
    values = access_policy()
    permissions = set(values.get("role_permissions", {}).get(normalized.value, []))
    project_settings = settings_value or {}
    for key, rule in values.get("policy_permissions", {}).items():
        if (
            isinstance(rule, dict)
            and rule.get("role") == normalized.value
            and project_settings.get(key) is True
        ):
            permissions.update(rule.get("permissions", []))
    for rule in values.get("conditional_permissions", []):
        if (
            isinstance(rule, dict)
            and rule.get("role") == normalized.value
            and project_settings.get(rule.get("setting")) is rule.get("enabled")
        ):
            permissions.update(rule.get("permissions", []))
    for rule in values.get("conditional_denials", []):
        if (
            isinstance(rule, dict)
            and rule.get("role") == normalized.value
            and project_settings.get(rule.get("setting")) is rule.get("enabled")
        ):
            permissions.difference_update(rule.get("permissions", []))
    overrides = project_settings.get("permission_overrides", {}).get(normalized.value, {})
    known_permissions = project_permissions()
    permissions.update(item for item in overrides.get("allow", []) if item in known_permissions)
    permissions.difference_update(overrides.get("deny", []))
    return permissions


def roles_for_membership(membership: dict | None) -> set[str]:
    if not membership:
        return set()
    roles = membership.get("project_roles")
    if not isinstance(roles, list):
        roles = []
    primary = membership.get("project_role")
    return {str(role).upper() for role in [*roles, primary] if role}


def permissions_for_membership(membership: dict | None, settings_value: dict | None = None):
    if not membership:
        return set()
    return set().union(
        *(permissions_for_role(role, settings_value) for role in roles_for_membership(membership))
    )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/xac-thuc/dang-nhap", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    ai_automation_run_id: str | None = Header(default=None, alias="X-AI-Automation-Run"),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "AUTH_REQUIRED"})
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("uid") or payload.get("sub")
        email = payload.get("email") or payload.get("sub", "")
        if not user_id:
            raise ValueError
        role_value = payload.get("system_role", "USER")
        session_id = payload.get("sid")
        if session_id and not await session_is_valid(str(session_id), str(user_id)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "SESSION_REVOKED"})
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
                raise HTTPException(status_code=403, detail={"code": "AI_AUTOMATION_IDENTITY_INVALID"})
            user._ai_automation_run_id = token_run_id
            user._ai_automation_initiator_id = str(payload.get("ai_automation_initiator_id") or "")
            user._ai_automation_definition_id = str(payload.get("ai_automation_definition_id") or "")
            ai_automation_context.set(
                {
                    "run_id": token_run_id,
                    "initiator_id": user._ai_automation_initiator_id,
                    "definition_id": user._ai_automation_definition_id,
                    "principal_id": user.id,
                }
            )
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "TOKEN_EXPIRED"})
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "TOKEN_INVALID"})


def require_authenticated(user: CurrentUser = Depends(get_current_user)):
    return user
