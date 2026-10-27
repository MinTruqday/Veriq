import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from loguru import logger

from src.core.infrastructure.configuration import settings
from src.core.security.access import create_access_token, get_password_hash, verify_password
from src.repositories.identity import IdentityRepository as IdentityRepository
from src.schemas.identity import UserCreate, UserInDB
from src.services.email import EmailService


class SessionService:
    @staticmethod
    def refresh_cookie_seconds():
        return settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    @staticmethod
    def access_token_for_user(user_doc: dict, session_id: str):
        return create_access_token(
            data={
                "sub": user_doc["email"],
                "sid": session_id,
                "system_role": user_doc.get("system_role", "USER"),
                "uid": str(user_doc["_id"]),
                "permissions": user_doc.get("permissions", []),
                "full_name": user_doc.get("full_name", ""),
                "slug": user_doc.get("slug", ""),
            }
        )

    @staticmethod
    async def create_platform_user(user_in: UserCreate, client_ip: str):
        if await IdentityRepository.get_auth_credential_by_email(user_in.email):
            raise HTTPException(
                status_code=400, detail="Địa chỉ thư điện tử đã được sử dụng cho một tài khoản khác"
            )
        if await IdentityRepository.get_auth_credential_by_slug(user_in.slug):
            raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại trên hệ thống")

        user_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        auth_cred = {
            **user_in.model_dump(exclude={"password", "agreed_to_terms"}, mode="json"),
            "_id": user_id,
            "email": user_in.email.lower(),
            "slug": user_in.slug.lower(),
            "full_name": user_in.full_name,
            "system_role": "USER",
            "permissions": [],
            "is_active": True,
            "is_verified": False,
            "email_verified": False,
            "password_hash": get_password_hash(user_in.password),
            "passkeys": [],
            "created_at": created_at,
            "updated_at": created_at,
        }
        await IdentityRepository.create_auth_credential(auth_cred)
        await SessionService.issue_email_verification(user_id, user_in.email, client_ip)
        await IdentityRepository.insert_audit_log(
            {
                "action": "REGISTER_USER",
                "actor_email": user_in.email,
                "ip": client_ip,
                "timestamp": datetime.now(timezone.utc),
            }
        )
        logger.info("User account registration process completed")
        return {
            "email": user_in.email.lower(),
            "full_name": user_in.full_name,
            "slug": user_in.slug.lower(),
            "system_role": "USER",
            "id": user_id,
            "created_at": created_at,
        }

    @staticmethod
    async def issue_email_verification(user_id: str, email: str, client_ip: str):
        token = secrets.token_urlsafe(32)
        timestamp = datetime.now(timezone.utc)
        await IdentityRepository.create_email_verification_token(
            {
                "_id": secrets.token_hex(16),
                "user_id": user_id,
                "email": email,
                "token": token,
                "used": False,
                "expires_at": timestamp
                + timedelta(minutes=30),
                "created_at": timestamp,
                "requested_ip": client_ip,
            }
        )
        delivered = True
        try:
            await EmailService.send_email_verification(email, token)
        except Exception:
            delivered = False
            logger.exception("Failed to dispatch email verification notification")
        await IdentityRepository.insert_audit_log(
            {
                "action": "EMAIL_VERIFICATION_REQUESTED",
                "actor_email": email.lower(),
                "target_user_id": user_id,
                "ip": client_ip,
                "delivered": delivered,
                "timestamp": timestamp,
            }
        )
        return {
            "status": "ok",
            "delivered": delivered,
        }

    @staticmethod
    async def verify_email(token: str, client_ip: str):
        token_doc = await IdentityRepository.consume_email_verification_token(token)
        if not token_doc:
            raise HTTPException(
                status_code=400, detail="Mã xác minh thư điện tử không hợp lệ hoặc đã hết hạn"
            )
        account = await IdentityRepository.mark_email_verified(
            str(token_doc["user_id"]), token_doc["email"]
        )
        if not account:
            raise HTTPException(
                status_code=409,
                detail="Địa chỉ thư điện tử của tài khoản đã thay đổi hoặc tài khoản không khả dụng",
            )
        await IdentityRepository.insert_audit_log(
            {
                "action": "EMAIL_VERIFIED",
                "actor_email": token_doc["email"],
                "target_user_id": str(token_doc["user_id"]),
                "ip": client_ip,
                "timestamp": datetime.now(timezone.utc),
            }
        )
        return {"verified": True, "email": token_doc["email"]}

    @staticmethod
    async def login_user(username: str, password: str, client_ip: str):
        is_email = "@" in username
        try:
            if is_email:
                auth_cred = await IdentityRepository.get_auth_credential_by_email(username)
            else:
                auth_cred = await IdentityRepository.get_auth_credential_by_slug(username)
        except Exception:
            auth_cred = None

        if not auth_cred:
            await IdentityRepository.insert_audit_log(
                {
                    "action": "LOGIN_FAILED_UNKNOWN_ACCOUNT",
                    "actor_email": username.lower() if is_email else "",
                    "actor_slug": username.lower() if not is_email else "",
                    "ip": client_ip,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            raise HTTPException(status_code=401, detail="Thông tin đăng nhập không chính xác")

        password_hash = auth_cred.get("password_hash") if auth_cred else "invalid"

        if not verify_password(password, password_hash):
            await IdentityRepository.insert_audit_log(
                {
                    "action": "LOGIN_FAILED_WRONG_PASSWORD",
                    "actor_email": auth_cred.get("email", ""),
                    "ip": client_ip,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            logger.warning("User authentication failed due to invalid credentials provided")
            raise HTTPException(status_code=401, detail="Thông tin đăng nhập không chính xác")

        user_id_str = str(auth_cred["_id"])

        is_active = auth_cred.get("is_active", True)
        if not is_active:
            raise HTTPException(
                status_code=403,
                detail="Tài khoản hiện đang bị khóa hoặc ở trạng thái không hoạt động",
            )

        session_id = str(uuid.uuid4())
        refresh_token = secrets.token_urlsafe(48)
        await IdentityRepository.cache_session(user_id_str, session_id)
        await IdentityRepository.register_session(user_id_str, session_id, client_ip, refresh_token)
        access_token = SessionService.access_token_for_user(auth_cred, session_id)
        await IdentityRepository.insert_audit_log(
            {
                "action": "LOGIN_SUCCESS",
                "actor_email": auth_cred["email"],
                "ip": client_ip,
                "timestamp": datetime.now(timezone.utc),
            }
        )
        logger.info("User authentication process completed")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "_refresh_token": refresh_token,
            "user": {
                "email": auth_cred["email"],
                "has_passkey": len(auth_cred.get("passkeys", [])) > 0,
            },
        }

    @staticmethod
    async def revoke_all_sessions(current_user: UserInDB):
        user_id_str = str(current_user.id)
        await IdentityRepository.revoke_all_sessions(user_id_str)
        logger.info("Revocation of all active user sessions completed")
        return {"message": "Thực hiện đăng xuất khỏi tất cả các thiết bị hoàn tất"}

    @staticmethod
    async def revoke_session(current_user):
        await IdentityRepository.revoke_session(str(current_user.id), current_user.session_id)
        return {"message": "Đăng xuất hoàn tất"}

    @staticmethod
    async def forgot_password(email: str, client_ip: str):
        try:
            user = await IdentityRepository.get_user_by_email(email)
        except Exception:
            user = None
        if user:
            otp_code = "".join(
                str(secrets.randbelow(10)) for _ in range(6)
            )
            await IdentityRepository.create_password_reset_token(
                {
                    "_id": secrets.token_hex(8),
                    "email": email,
                    "token": otp_code,
                    "expires_at": datetime.now(timezone.utc)
                    + timedelta(minutes=1),
                    "used": False,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            await IdentityRepository.insert_audit_log(
                {
                    "action": "FORGOT_PASSWORD_REQUEST",
                    "actor_email": email,
                    "ip": client_ip,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            try:
                await EmailService.send_reset_password_email(email, otp_code)
            except Exception:
                logger.exception("Failed to dispatch password recovery email notification")
        return {
            "status": "ok",
            "message": "Hệ thống đang tiến hành xử lý yêu cầu khôi phục mật khẩu",
        }

    @staticmethod
    async def reset_password(token: str, new_password: str, client_ip: str):
        token_doc = await IdentityRepository.consume_password_reset_token(token)
        if not token_doc:
            raise HTTPException(
                status_code=400, detail="Mã xác minh bảo mật không hợp lệ hoặc đã quá hạn sử dụng"
            )
        auth_cred = await IdentityRepository.get_auth_credential_by_email(token_doc["email"])
        if not auth_cred:
            raise HTTPException(status_code=400, detail="Mã xác minh bảo mật không hợp lệ")
        await IdentityRepository.update_password_hash(
            token_doc["email"], get_password_hash(new_password)
        )
        await IdentityRepository.revoke_all_sessions(str(auth_cred["_id"]))
        await IdentityRepository.insert_audit_log(
            {
                "action": "RESET_PASSWORD_SUCCESS",
                "actor_email": token_doc["email"],
                "ip": client_ip,
                "timestamp": datetime.now(timezone.utc),
            }
        )
        logger.info("User account password modification completed")
        return {"status": "ok", "message": "Thực hiện thay đổi mật khẩu tài khoản hoàn tất"}

    @staticmethod
    async def verify_reset_code(token: str, client_ip: str):
        token_doc = await IdentityRepository.get_valid_password_reset_token(token)
        if not token_doc:
            raise HTTPException(
                status_code=400, detail="Mã xác minh bảo mật không hợp lệ hoặc đã quá hạn sử dụng"
            )
        return {"status": "ok", "message": "Xác thực mã bảo mật hoàn tất"}

    @staticmethod
    async def issue_token_for_user(user_doc: dict, client_ip: str):
        if (
            not user_doc.get("is_active", True)
        ):
            raise HTTPException(
                status_code=403,
                detail="Tài khoản hiện đang bị khóa hoặc ở trạng thái không hoạt động",
            )
        session_id = str(uuid.uuid4())
        refresh_token = secrets.token_urlsafe(48)
        user_id_str = str(user_doc["_id"])
        await IdentityRepository.register_session(user_id_str, session_id, client_ip, refresh_token)
        await IdentityRepository.cache_session(user_id_str, session_id)
        access_token = SessionService.access_token_for_user(user_doc, session_id)
        auth_cred = await IdentityRepository.get_auth_credential_by_id(str(user_doc["_id"]))
        has_passkey = len(auth_cred.get("passkeys", [])) > 0 if auth_cred else False
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "_refresh_token": refresh_token,
            "user": {"email": user_doc["email"], "has_passkey": has_passkey},
        }

    @staticmethod
    async def refresh_session(refresh_token: str, client_ip: str):
        replacement = secrets.token_urlsafe(48)
        session = await IdentityRepository.rotate_refresh_token(
            refresh_token, replacement, client_ip
        )
        if not session:
            raise HTTPException(
                status_code=401, detail="Phiên làm mới không hợp lệ hoặc đã hết hạn"
            )
        user_doc = await IdentityRepository.get_auth_credential_by_id(str(session["user_id"]))
        if not user_doc or not user_doc.get("is_active", True):
            await IdentityRepository.revoke_session(str(session["user_id"]), str(session["_id"]))
            raise HTTPException(status_code=401, detail="Tài khoản không còn khả dụng")
        await IdentityRepository.cache_session(
            str(session["user_id"]), str(session["_id"])
        )
        access_token = SessionService.access_token_for_user(user_doc, str(session["_id"]))
        await IdentityRepository.insert_audit_log(
            {
                "action": "SESSION_REFRESHED",
                "actor_email": user_doc["email"],
                "ip": client_ip,
                "timestamp": datetime.now(timezone.utc),
            }
        )
        return {"access_token": access_token, "token_type": "bearer", "_refresh_token": replacement}
