import re
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from src.clients.service_gateway import internal_request
from src.core.dependency import CurrentUser
from src.repositories.identity import IdentityRepository
from src.repositories.platform import PlatformRepository
from src.schemas.identity import SystemRole, UserCreate
from src.schemas.platform import (
    AccountUpdate,
    ActionReason,
    ProfileUpdate,
    SystemRoleUpdate,
    UserCreateRequest,
)
from src.services.platform import account_or_404, account_view, protect_last_admin, record_audit
from src.services.session import SessionService


class PlatformAccountService:
    @staticmethod
    async def create(
        payload: UserCreateRequest, client_ip: str, current_user: CurrentUser
    ):
        user = await SessionService.create_platform_user(
            UserCreate(
                email=payload.email,
                full_name=payload.full_name,
                slug=payload.slug,
                password=secrets.token_urlsafe(48),
                agreed_to_terms=True,
            ),
            client_ip,
        )
        await SessionService.forgot_password(str(payload.email), client_ip)
        await record_audit(
            current_user,
            "ADMIN_USER_CREATED",
            user["id"],
            payload.reason,
            {"invite_flow": "PASSWORD_RESET"},
        )
        return account_view(await account_or_404(user["id"]))

    @staticmethod
    async def list(
        search: str | None,
        system_role: SystemRole | None,
        is_active: bool | None,
        limit: int,
    ):
        query: dict[str, Any] = {}
        if search:
            pattern = re.escape(search.strip())
            query["$or"] = [
                {"email": {"$regex": pattern, "$options": "i"}},
                {"slug": {"$regex": pattern, "$options": "i"}},
                {"full_name": {"$regex": pattern, "$options": "i"}},
            ]
        if system_role is not None:
            query["system_role"] = system_role.value
        if is_active is not None:
            query["is_active"] = is_active
        accounts = await IdentityRepository.list_auth_credentials(
            query, sort=[("created_at", -1)], limit=limit
        )
        return [account_view(account) for account in accounts]

    @staticmethod
    async def update(user_id: str, payload: AccountUpdate, current_user: CurrentUser):
        if user_id == current_user.id and (
            payload.is_active is False
            or payload.system_role not in {None, SystemRole.ADMIN}
        ):
            raise HTTPException(
                status_code=422, detail="Không thể tự khóa hoặc hạ quyền tài khoản quản trị hiện tại"
            )
        account_before = await account_or_404(user_id)
        desired_role = payload.system_role.value if payload.system_role is not None else None
        await protect_last_admin(account_before, desired_role, payload.is_active)
        changes = {
            key: value.value if isinstance(value, SystemRole) else value
            for key, value in payload.model_dump(exclude={"reason"}).items()
            if value is not None
        }
        changes["updated_at"] = datetime.now(timezone.utc)
        account = await IdentityRepository.find_and_update_auth_credential(
            {"_id": user_id}, {"$set": changes}
        )
        if not account:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
        await IdentityRepository.revoke_all_sessions(user_id)
        await IdentityRepository.insert_audit_log(
            {
                "action": "ADMIN_ACCOUNT_UPDATED",
                "actor_email": current_user.email,
                "target_user_id": user_id,
                "changes": changes,
                "reason": payload.reason,
                "timestamp": changes["updated_at"],
            }
        )
        return account_view(account)

    @staticmethod
    async def detail(user_id: str):
        account = await account_or_404(user_id)
        session_count = await IdentityRepository.count_sessions(
            {"user_id": user_id, "revoked_at": None}
        )
        return {
            **account_view(account),
            "account_status": account.get(
                "account_status",
                "ACTIVE"
                if account.get("is_active", True)
                else "DISABLED",
            ),
            "active_session_count": session_count,
            "passkey_count": len(account.get("passkeys", [])),
            "is_verified": account.get("is_verified", False),
            "last_password_change": account.get("last_password_change"),
        }

    @staticmethod
    async def update_profile(
        user_id: str, payload: ProfileUpdate, current_user: CurrentUser
    ):
        await account_or_404(user_id)
        changes = {
            key: value
            for key, value in payload.model_dump(exclude={"reason"}).items()
            if value is not None
        }
        if not changes:
            raise HTTPException(status_code=422, detail="Không có dữ liệu cần cập nhật")
        changes["updated_at"] = datetime.now(timezone.utc)
        account = await IdentityRepository.find_and_update_auth_credential(
            {"_id": user_id}, {"$set": changes}
        )
        await record_audit(
            current_user, "ADMIN_USER_PROFILE_UPDATED", user_id, payload.reason, changes
        )
        return account_view(account)

    @staticmethod
    async def change_status(
        user_id: str,
        desired_status: str,
        payload: ActionReason,
        current_user: CurrentUser,
    ):
        account = await account_or_404(user_id)
        active = desired_status == "ACTIVE"
        await protect_last_admin(account, desired_active=active)
        if user_id == current_user.id and not active:
            raise HTTPException(status_code=422, detail="Không thể tự vô hiệu hóa tài khoản hiện tại")
        account = await IdentityRepository.find_and_update_auth_credential(
            {"_id": user_id},
            {
                "$set": {
                    "is_active": active,
                    "account_status": desired_status,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        if not active:
            await IdentityRepository.revoke_all_sessions(user_id)
        await record_audit(
            current_user, f"ADMIN_USER_{desired_status}", user_id, payload.reason
        )
        return account_view(account)

    @staticmethod
    async def activate(user_id: str, payload: ActionReason, current_user: CurrentUser):
        return await PlatformAccountService.change_status(
            user_id, "ACTIVE", payload, current_user
        )

    @staticmethod
    async def disable(user_id: str, payload: ActionReason, current_user: CurrentUser):
        return await PlatformAccountService.change_status(
            user_id, "DISABLED", payload, current_user
        )

    @staticmethod
    async def lock(user_id: str, payload: ActionReason, current_user: CurrentUser):
        return await PlatformAccountService.change_status(
            user_id, "LOCKED", payload, current_user
        )

    @staticmethod
    async def unlock(user_id: str, payload: ActionReason, current_user: CurrentUser):
        return await PlatformAccountService.change_status(
            user_id, "ACTIVE", payload, current_user
        )

    @staticmethod
    async def force_password_reset(
        user_id: str, payload: ActionReason, client_ip: str, current_user: CurrentUser
    ):
        account = await account_or_404(user_id)
        result = await SessionService.forgot_password(account["email"], client_ip)
        await IdentityRepository.revoke_all_sessions(user_id)
        await record_audit(
            current_user, "ADMIN_FORCE_PASSWORD_RESET", user_id, payload.reason
        )
        return result

    @staticmethod
    async def sessions(user_id: str, current_user: CurrentUser):
        await account_or_404(user_id)
        sessions = await IdentityRepository.list_sessions(
            {"user_id": user_id}, {"refresh_token_hash": 0}
        )
        await record_audit(
            current_user, "ADMIN_USER_SESSIONS_VIEWED", user_id, "security review"
        )
        return sessions

    @staticmethod
    async def revoke_session(user_id: str, session_id: str, current_user: CurrentUser):
        await account_or_404(user_id)
        await IdentityRepository.revoke_session(user_id, session_id)
        await record_audit(
            current_user,
            "ADMIN_USER_SESSION_REVOKED",
            user_id,
            "security action",
            {"session_id": session_id},
        )
        return {"revoked": True, "session_id": session_id}

    @staticmethod
    async def revoke_all_sessions(user_id: str, current_user: CurrentUser):
        await account_or_404(user_id)
        await IdentityRepository.revoke_all_sessions(user_id)
        await record_audit(
            current_user, "ADMIN_USER_SESSIONS_REVOKED", user_id, "security action"
        )
        return {"revoked": True}

    @staticmethod
    async def reset_passkeys(
        user_id: str, payload: ActionReason, current_user: CurrentUser
    ):
        await account_or_404(user_id)
        await IdentityRepository.update_auth_credential(
            {"_id": user_id},
            {"$set": {"passkeys": [], "updated_at": datetime.now(timezone.utc)}},
        )
        await IdentityRepository.revoke_all_sessions(user_id)
        await record_audit(
            current_user, "ADMIN_USER_PASSKEYS_RESET", user_id, payload.reason
        )
        return {"reset": True}

    @staticmethod
    async def update_system_role(
        user_id: str, payload: SystemRoleUpdate, current_user: CurrentUser
    ):
        account = await account_or_404(user_id)
        await protect_last_admin(account, desired_role=payload.system_role.value)
        if user_id == current_user.id and payload.system_role != SystemRole.ADMIN:
            raise HTTPException(status_code=422, detail="Không thể tự hạ quyền quản trị hiện tại")
        account = await IdentityRepository.find_and_update_auth_credential(
            {"_id": user_id},
            {
                "$set": {
                    "system_role": payload.system_role.value,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        await IdentityRepository.revoke_all_sessions(user_id)
        await record_audit(
            current_user,
            "ADMIN_SYSTEM_ROLE_UPDATED",
            user_id,
            payload.reason,
            {"system_role": payload.system_role.value},
        )
        return account_view(account)

    @staticmethod
    async def memberships(user_id: str, current_user: CurrentUser):
        await account_or_404(user_id)
        response = await internal_request(
            "GET", "testing", f"/kiem-thu/noi-bo/quan-tri/nguoi-dung/{user_id}/thanh-vien"
        )
        response.raise_for_status()
        await record_audit(
            current_user, "ADMIN_USER_MEMBERSHIPS_VIEWED", user_id, "support metadata"
        )
        return response.json()

    @staticmethod
    async def audit(user_id: str, limit: int):
        account = await account_or_404(user_id)
        events = await PlatformRepository.list_audit_logs(
            {"$or": [{"target_user_id": user_id}, {"actor_email": account.get("email")}]},
            limit,
        )
        return [{**event, "_id": str(event["_id"])} for event in events]
