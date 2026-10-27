import secrets
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import HTTPException, status
from loguru import logger

from src.clients.google import (
    GoogleAuthorizationRejected,
    GoogleProviderUnavailable,
    google_client,
)
from src.core.infrastructure.configuration import settings
from src.repositories.cache import CacheRepository
from src.repositories.identity import IdentityRepository


class GoogleService:
    @staticmethod
    async def get_google_auth_url():
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Hệ thống chưa được cấu hình dịch vụ xác thực liên kết",
            )
        state = secrets.token_urlsafe(32)
        await CacheRepository.store_google_oauth_state(state)
        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
            }
        )
        return f"{settings.GOOGLE_AUTH_URL}?{query}"

    @staticmethod
    async def handle_google_callback(code: str, state: str, client_ip: str):
        from src.services.session import SessionService

        if not code or not state:
            raise HTTPException(status_code=400, detail="Yêu cầu xác thực liên kết không hợp lệ")
        stored_state = await CacheRepository.consume_google_oauth_state(state)
        if not stored_state:
            raise HTTPException(
                status_code=400, detail="Phiên xác thực liên kết không hợp lệ hoặc đã hết hạn"
            )
        if not all(
            [settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET, settings.GOOGLE_REDIRECT_URI]
        ):
            raise HTTPException(
                status_code=503, detail="Dịch vụ xác thực liên kết chưa được cấu hình"
            )

        try:
            google_user = await google_client.load_user(code)
        except GoogleAuthorizationRejected:
            raise HTTPException(
                status_code=400, detail="Nhà cung cấp đã từ chối yêu cầu xác thực"
            )
        except GoogleProviderUnavailable:
            logger.exception("Federated identity provider request failed")
            raise HTTPException(
                status_code=502, detail="Không thể xác minh tài khoản với nhà cung cấp"
            )

        email = str(google_user.get("email", "")).strip().lower()
        if not email or google_user.get("email_verified") is not True:
            raise HTTPException(
                status_code=400, detail="Địa chỉ thư điện tử liên kết chưa được xác minh"
            )

        user_doc = await IdentityRepository.get_auth_credential_by_email(email)
        if not user_doc:
            raise HTTPException(
                status_code=403,
                detail="Tài khoản chưa được quản trị viên cấp quyền đăng nhập",
            )

        return await SessionService.issue_token_for_user(user_doc, client_ip)
