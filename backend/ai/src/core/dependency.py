import hmac
from typing import List, Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from loguru import logger

from src.clients.authentication import AuthenticationClient
from src.core.infrastructure.configuration import settings
from src.core.infrastructure.mongo import mongo
from src.core.infrastructure.redis import redis
from src.schemas.auth import CurrentUser, SystemRole

ALGORITHM = "HS256"
SECRET_KEY = settings.SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/xac-thuc/dang-nhap")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "authentication_required"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        session_id: str = payload.get("sid")
        if email is None or session_id is None:
            logger.warning("Token verification failed due to missing identity claims")
            raise credentials_exception
    except jwt.PyJWTError:
        logger.exception("Authentication decoding failed due to invalid token payload")
        raise credentials_exception

    uid = payload.get("uid")
    if not uid:
        logger.warning("Missing user identifier (UID) in authentication token")
        raise credentials_exception

    is_valid_session = await AuthenticationClient.session_is_valid(str(uid), str(session_id))
    if not is_valid_session:
        logger.warning("Attempted to use an invalidated or revoked session token")
        raise credentials_exception

    user_doc = {
        "_id": uid,
        "email": email,
        "system_role": payload.get("system_role", "USER"),
        "permissions": payload.get("permissions", []),
        "session_id": session_id,
        "full_name": payload.get("full_name", ""),
        "slug": payload.get("slug", ""),
        "is_active": True,
    }
    return CurrentUser(**user_doc)


async def get_current_user_optional(
    token: Optional[str] = Depends(
        OAuth2PasswordBearer(tokenUrl="/xac-thuc/dang-nhap", auto_error=False)
    ),
) -> Optional[CurrentUser]:
    if not token:
        return None
    try:
        return await get_current_user(token)
    except HTTPException:
        return None


async def get_current_user_token_param(token: str) -> CurrentUser:
    return await get_current_user(token)


async def require_system_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "system_admin_required"},
        )
    return current_user


class RateLimiting:
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"rate_limit:{client_ip}:{path}"
        current = await redis.get(key)
        if current is not None and int(current) >= self.calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "rate_limit_exceeded"},
            )
        await redis.pipeline_incr_expire(key, self.period)
        return True


def require_permissions(required_permissions: List[str]):
    async def permission_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        user_perms = current_user.permissions or []
        if current_user.system_role == SystemRole.ADMIN:
            return current_user
        missing = [p for p in required_permissions if p not in user_perms]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail={"code": "privileged_access_required"}
            )
        return current_user

    return permission_checker


async def get_db():
    return mongo.get_db()


async def verify_internal_token(x_internal_token: str = Header(default="")) -> None:
    if not settings.SECRET_KEY or not hmac.compare_digest(x_internal_token, settings.SECRET_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden invalid internal token"
        )
