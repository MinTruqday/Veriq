from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.services.auth_cookie import set_refresh_cookie
from src.core.dependency import CurrentUser, RateLimiting, get_current_user
from src.core.response import APIResponse
from src.schemas.identity import PasskeyFinishRequest, PasskeyRequest
from src.services.passkey import PasskeyService

router = APIRouter(prefix="/xac-thuc/khoa-bao-mat", tags=["Khóa bảo mật"])


@router.post(
    "/dang-nhap/bat-dau",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=5, period=60))],
)
async def passkey_login_begin(payload: PasskeyRequest):
    return APIResponse(
        data=await PasskeyService.login_begin(payload.email),
        message="Khởi tạo quy trình xác thực bằng mã bảo mật hoàn tất",
        status=200,
    )


@router.post(
    "/dang-nhap/hoan-tat",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=5, period=60))],
)
async def passkey_login_finish(payload: PasskeyFinishRequest, request: Request, response: Response):
    token_data = await PasskeyService.login_finish(payload.email, payload.credential)
    return APIResponse(
        data=set_refresh_cookie(response, request, token_data),
        message="Xác thực thông tin thông qua mã bảo mật hoàn tất",
        status=200,
    )


@router.post("/dang-ky/bat-dau", response_model=APIResponse[Any])
async def passkey_register_begin(
    payload: PasskeyRequest, current_user: CurrentUser = Depends(get_current_user)
):
    if payload.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=403, detail="Không thể đăng ký mã bảo mật cho tài khoản khác"
        )
    return APIResponse(
        data=await PasskeyService.register_begin(payload.email),
        message="Khởi tạo quy trình đăng ký mã bảo mật hoàn tất",
        status=200,
    )


@router.post("/dang-ky/hoan-tat", response_model=APIResponse[Any])
async def passkey_register_finish(
    payload: PasskeyFinishRequest, current_user: CurrentUser = Depends(get_current_user)
):
    if payload.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=403, detail="Không thể đăng ký mã bảo mật cho tài khoản khác"
        )
    return APIResponse(
        data=await PasskeyService.register_finish(payload.email, payload.credential),
        message="Thực hiện đăng ký mã bảo mật hoàn tất",
        status=200,
    )
