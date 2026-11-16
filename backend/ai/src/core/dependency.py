import hmac
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from loguru import logger

from src.clients.authentication import AuthenticationClient
from src.core.infrastructure.configuration import settings
from src.core.infrastructure.redis import redis
from src.schemas.auth import CurrentUser, SystemRole

ALGORITHM = "HS256"
SECRET_KEY = settings.SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/xac-thuc/dang-nhap")

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    x_ai_capability_run: str | None = Header(default=None, alias="X-AI-Run-ID"),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "authentication_required"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        ai_run_id = payload.get("ai_capability_run_id")
        if ai_run_id:
            path_parts = request.url.path.strip("/").split("/")
            path_is_project_knowledge_search = (
                request.method == "POST"
                and len(path_parts) == 4
                and path_parts[0] == "tri-thuc"
                and path_parts[1] == "du-an"
                and path_parts[3] == "tim-kiem"
            )
            if (
                not path_is_project_knowledge_search
                or not x_ai_capability_run
                or not hmac.compare_digest(str(ai_run_id), x_ai_capability_run)
                or not settings.SECRET_KEY
                or not x_internal_token
                or not hmac.compare_digest(x_internal_token, settings.SECRET_KEY)
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "AI_RUN_IDENTITY_INVALID"},
                )

            user_id = payload.get("uid")
            subject = payload.get("sub")
            worker_revision = payload.get("ai_capability_worker_revision")
            if (
                not user_id
                or str(subject or "") != str(user_id)
                or isinstance(worker_revision, bool)
                or not isinstance(worker_revision, int)
                or worker_revision < 1
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "AI_RUN_IDENTITY_INVALID"},
                )

            requested_project_id = path_parts[2]
            try:
                from src.repositories.ai_runs import ai_run_repository
                from src.schemas.ai_runs import AIRunStatus

                run = await ai_run_repository.get_run(str(ai_run_id))
            except Exception as error:
                logger.exception("AI run identity verification unavailable")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "AI_RUN_STATUS_UNAVAILABLE"},
                ) from error

            if (
                not run
                or run.status != AIRunStatus.RUNNING
                or run.revision != worker_revision
                or str(run.execution_user_id or "") != str(user_id)
                or run.project_id != requested_project_id
                or "knowledge.read" not in run.execution_permissions
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "AI_RUN_SCOPE_INVALID"},
                )

            return CurrentUser(
                _id=str(user_id),
                email="",
                system_role="USER",
                permissions=run.execution_permissions,
                is_active=True,
                session_id=f"ai-run:{ai_run_id}:{worker_revision}",
            )

        email: str = payload.get("sub")
        session_id: str = payload.get("sid")
        if email is None or session_id is None:
            logger.warning("Token verification failed due to missing identity claims")
            raise credentials_exception
    except jwt.PyJWTError:
        logger.warning("Rejected request with an invalid or expired access token")
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
    request: Request,
    token: Optional[str] = Depends(
        OAuth2PasswordBearer(tokenUrl="/xac-thuc/dang-nhap", auto_error=False)
    ),
    x_ai_capability_run: str | None = Header(default=None, alias="X-AI-Run-ID"),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> Optional[CurrentUser]:
    if not token:
        return None
    try:
        return await get_current_user(
            request=request,
            token=token,
            x_ai_capability_run=x_ai_capability_run,
            x_internal_token=x_internal_token,
        )
    except HTTPException:
        return None

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

async def verify_internal_token(x_internal_token: str = Header(default="")) -> None:
    if not settings.SECRET_KEY or not hmac.compare_digest(x_internal_token, settings.SECRET_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden invalid internal token"
        )
