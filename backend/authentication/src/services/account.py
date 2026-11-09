from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from src.core.security.access import get_password_hash, verify_password
from src.repositories.identity import IdentityRepository
from src.schemas.identity import SystemRole
from src.services.session import SessionService


class AccountService:
    @staticmethod
    async def profile(current_user: Any):
        account = await IdentityRepository.get_auth_credential_by_id(str(current_user.id))
        if not account:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy thông tin tài khoản người dùng"
            )
        result = dict(account)
        result["_id"] = str(account["_id"])
        result.pop("password_hash", None)
        result.pop("passkeys", None)
        result.update(
            {
                "email": account.get("email", current_user.email),
                "full_name": account.get("full_name")
                or current_user.full_name
                or current_user.email,
                "slug": account.get("slug")
                or str(account.get("email", current_user.email)).split("@", 1)[0],
                "system_role": account.get("system_role", SystemRole.USER.value),
                "permissions": account.get("permissions") or [],
                "created_at": account.get("created_at") or datetime.now(timezone.utc),
            }
        )
        return result

    @staticmethod
    async def update_profile(current_user: Any, values: dict):
        changes = {key: value for key, value in values.items() if value is not None}
        if not changes:
            raise HTTPException(
                status_code=422, detail="Không có dữ liệu cần cập nhật"
            )
        changes["updated_at"] = datetime.now(timezone.utc)
        account = await IdentityRepository.find_and_update_auth_credential(
            {"_id": current_user.id}, {"$set": changes}
        )
        if not account:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
        await AccountService._audit(
            current_user, "ACCOUNT_PROFILE_UPDATED", changes=sorted(changes)
        )
        account["_id"] = str(account["_id"])
        account.pop("password_hash", None)
        account.pop("passkeys", None)
        return account

    @staticmethod
    async def change_email(current_user: Any, current_password: str, requested_email: str):
        await AccountService._verified_account(current_user, current_password)
        new_email = requested_email.lower()
        if new_email == current_user.email.lower():
            raise HTTPException(
                status_code=422, detail="Email mới phải khác email hiện tại"
            )
        duplicate = await IdentityRepository.find_auth_credential({"email": new_email})
        if duplicate:
            raise HTTPException(status_code=409, detail="Email mới đã được sử dụng")
        await IdentityRepository.update_auth_credential(
            {"_id": current_user.id},
            {
                "$set": {
                    "email": new_email,
                    "is_verified": False,
                    "email_verified": False,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        await SessionService.issue_email_verification(
            current_user.id, new_email, "authenticated"
        )
        await IdentityRepository.revoke_all_sessions(current_user.id)
        await AccountService._audit(
            current_user, "ACCOUNT_EMAIL_CHANGED", new_email=new_email
        )
        return {"email": new_email, "reauth_required": True}

    @staticmethod
    async def resend_verification(current_user: Any, client_ip: str):
        account = await IdentityRepository.get_auth_credential_by_id(current_user.id)
        if not account:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
        if account.get("is_verified") or account.get("email_verified"):
            return {"verified": True}
        return await SessionService.issue_email_verification(
            current_user.id, account["email"], client_ip
        )

    @staticmethod
    async def preferences(user_id: str):
        account = await IdentityRepository.get_auth_credential_by_id(user_id)
        return account.get("preferences", {}) if account else {}

    @staticmethod
    async def update_preferences(current_user: Any, values: dict):
        changes = {key: value for key, value in values.items() if value is not None}
        await IdentityRepository.update_auth_credential(
            {"_id": current_user.id},
            {"$set": {f"preferences.{key}": value for key, value in changes.items()}},
        )
        await AccountService._audit(
            current_user, "ACCOUNT_PREFERENCES_UPDATED", changes=sorted(changes)
        )
        return changes

    @staticmethod
    async def update_notifications(current_user: Any, values: dict):
        await IdentityRepository.update_auth_credential(
            {"_id": current_user.id},
            {"$set": {f"notification_settings.{key}": value for key, value in values.items()}},
        )
        await AccountService._audit(
            current_user, "ACCOUNT_NOTIFICATIONS_UPDATED", changes=sorted(values)
        )
        return values

    @staticmethod
    async def deactivate(current_user: Any, current_password: str):
        await AccountService._verified_account(current_user, current_password)
        await IdentityRepository.update_auth_credential(
            {"_id": current_user.id},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        await IdentityRepository.revoke_all_sessions(current_user.id)
        await AccountService._audit(current_user, "ACCOUNT_DEACTIVATED")
        return {"deactivated": True}

    @staticmethod
    async def change_password(current_user: Any, current_password: str, new_password: str):
        account = await AccountService._verified_account(current_user, current_password)
        if verify_password(new_password, account.get("password_hash", "")):
            raise HTTPException(
                status_code=422, detail="Mật khẩu mới phải khác mật khẩu hiện tại"
            )
        timestamp = datetime.now(timezone.utc)
        await IdentityRepository.update_auth_credential(
            {"_id": current_user.id},
            {
                "$set": {
                    "password_hash": get_password_hash(new_password),
                    "last_password_change": timestamp,
                    "updated_at": timestamp,
                }
            },
        )
        await IdentityRepository.revoke_other_sessions(
            current_user.id, current_user.session_id, timestamp
        )
        await IdentityRepository.retain_session_cache(current_user.id, current_user.session_id)
        await AccountService._audit(
            current_user, "ACCOUNT_PASSWORD_CHANGED", timestamp=timestamp
        )
        return {"other_sessions_revoked": True}

    @staticmethod
    async def sessions(current_user: Any):
        sessions = await IdentityRepository.list_active_sessions(current_user.id)
        for session in sessions:
            session["is_current"] = session.get("_id") == current_user.session_id
        return sessions

    @staticmethod
    async def revoke_session(current_user: Any, session_id: str):
        session = await IdentityRepository.get_session(current_user.id, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên đăng nhập")
        await IdentityRepository.revoke_session(current_user.id, session_id)
        await AccountService._audit(
            current_user, "ACCOUNT_SESSION_REVOKED", session_id=session_id
        )
        return {"revoked": True, "session_id": session_id}

    @staticmethod
    async def _verified_account(current_user: Any, password: str):
        account = await IdentityRepository.get_auth_credential_by_id(current_user.id)
        if not account or not verify_password(password, account.get("password_hash", "")):
            raise HTTPException(
                status_code=403, detail="Mật khẩu hiện tại không chính xác"
            )
        return account

    @staticmethod
    async def _audit(current_user: Any, action: str, timestamp=None, **values):
        await IdentityRepository.insert_audit_log(
            {
                "action": action,
                "actor_email": current_user.email,
                "target_user_id": current_user.id,
                "timestamp": timestamp or datetime.now(timezone.utc),
                **values,
            }
        )
