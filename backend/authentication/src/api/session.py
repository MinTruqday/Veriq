from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.core.dependency import CurrentUser, RateLimiting, get_current_user
from src.core.response import APIResponse
from src.schemas.identity import (
    AccountDeactivate,
    EmailChange,
    EmailVerificationInput,
    ForgotPasswordRequest,
    NotificationSettingsUpdate,
    PasswordChange,
    ProfileUpdate,
    ResetPasswordRequest,
    SettingsUpdate,
    UserResponse,
    VerifyCodeRequest,
)
from src.services.account import AccountService
from src.services.auth_cookie import set_refresh_cookie
from src.services.session import SessionService

router = APIRouter(prefix="/xac-thuc", tags=["Xác thực và phiên đăng nhập"])


@router.get("/ca-nhan", response_model=APIResponse[UserResponse])
async def read_users_me(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await AccountService.profile(current_user),
        message="Trích xuất thông tin cá nhân hoàn tất",
        status=status.HTTP_200_OK,
    )


@router.patch("/ca-nhan", response_model=APIResponse[Any])
async def update_users_me(
    payload: ProfileUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await AccountService.update_profile(current_user, payload.model_dump()),
        message="Cập nhật hồ sơ cá nhân hoàn tất",
    )


@router.post("/doi-thu-dien-tu", response_model=APIResponse[Any])
async def change_email(payload: EmailChange, current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await AccountService.change_email(
            current_user, payload.current_password, str(payload.new_email)
        ),
        message="Đổi email hoàn tất, vui lòng đăng nhập lại",
    )


@router.post(
    "/xac-minh-thu-dien-tu/gui-lai",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=3, period=300))],
)
async def resend_email_verification(
    request: Request, current_user: CurrentUser = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else "unknown"
    return APIResponse(
        data=await AccountService.resend_verification(current_user, client_ip),
        message="Khởi tạo lại yêu cầu xác minh thư điện tử hoàn tất",
    )


@router.post(
    "/xac-minh-thu-dien-tu",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=5, period=300))],
)
async def verify_email(payload: EmailVerificationInput, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    return APIResponse(
        data=await SessionService.verify_email(payload.token, client_ip),
        message="Xác minh địa chỉ thư điện tử hoàn tất",
    )


@router.get("/cai-dat", response_model=APIResponse[Any])
async def read_settings(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await AccountService.preferences(current_user.id),
        message="Tải cài đặt cá nhân hoàn tất",
    )


@router.patch("/cai-dat", response_model=APIResponse[Any])
async def update_settings(
    payload: SettingsUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await AccountService.update_preferences(current_user, payload.model_dump()),
        message="Cập nhật cài đặt cá nhân hoàn tất",
    )


@router.patch("/thong-bao", response_model=APIResponse[Any])
async def update_notifications(
    payload: NotificationSettingsUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await AccountService.update_notifications(current_user, payload.model_dump()),
        message="Cập nhật thông báo cá nhân hoàn tất",
    )


@router.post("/vo-hieu-hoa", response_model=APIResponse[Any])
async def deactivate_account(
    payload: AccountDeactivate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await AccountService.deactivate(current_user, payload.current_password),
        message="Vô hiệu hóa tài khoản hoàn tất",
    )


@router.post("/doi-mat-khau", response_model=APIResponse[Any])
async def change_password(
    payload: PasswordChange, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await AccountService.change_password(
            current_user, payload.current_password, payload.new_password
        ),
        message="Đổi mật khẩu và thu hồi các phiên khác hoàn tất",
    )


@router.get("/phien", response_model=APIResponse[Any])
async def list_my_sessions(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await AccountService.sessions(current_user),
        message="Tải danh sách phiên đăng nhập hoàn tất",
    )


@router.delete("/phien/{session_id}", response_model=APIResponse[Any])
async def revoke_my_session(session_id: str, current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await AccountService.revoke_session(current_user, session_id),
        message="Thu hồi phiên đăng nhập hoàn tất",
    )


@router.post(
    "/dang-nhap",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=5, period=60))],
)
async def login(
    request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    client_ip = request.client.host if request.client else "unknown"
    token_data = await SessionService.login_user(form_data.username, form_data.password, client_ip)
    return APIResponse(
        data=set_refresh_cookie(response, request, token_data),
        message="Xác thực thông tin và cấp quyền truy cập hệ thống hoàn tất",
        status=status.HTTP_200_OK,
    )


@router.post(
    "/quen-mat-khau",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=3, period=300))],
)
async def forgot_password(payload: ForgotPasswordRequest, request: Request) -> Any:
    client_ip = request.client.host if request.client else "unknown"
    return APIResponse(
        data=await SessionService.forgot_password(payload.email, client_ip),
        message="Thực hiện truyền tải yêu cầu đặt lại mật khẩu hoàn tất",
        status=status.HTTP_200_OK,
    )


@router.post(
    "/dat-lai-mat-khau",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=5, period=300))],
)
async def reset_password(payload: ResetPasswordRequest, request: Request) -> Any:
    client_ip = request.client.host if request.client else "unknown"
    return APIResponse(
        data=await SessionService.reset_password(payload.token, payload.new_password, client_ip),
        message="Thực hiện thay đổi mật khẩu tài khoản hoàn tất",
        status=status.HTTP_200_OK,
    )


@router.post(
    "/xac-nhan-ma",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=5, period=300))],
)
async def verify_code(payload: VerifyCodeRequest, request: Request) -> Any:
    client_ip = request.client.host if request.client else "unknown"
    return APIResponse(
        data=await SessionService.verify_reset_code(payload.token, client_ip),
        message="Xác thực mã bảo mật hoàn tất",
        status=status.HTTP_200_OK,
    )


@router.post("/dang-xuat", response_model=APIResponse[Any])
async def logout(response: Response, current_user: CurrentUser = Depends(get_current_user)):
    response.delete_cookie("veriq_refresh_token", path="/")
    return APIResponse(
        data=await SessionService.revoke_session(current_user), message="Đăng xuất hoàn tất"
    )


@router.post("/dang-xuat-tat-ca", response_model=APIResponse[Any])
async def logout_all(response: Response, current_user: CurrentUser = Depends(get_current_user)):
    response.delete_cookie("veriq_refresh_token", path="/")
    return APIResponse(
        data=await SessionService.revoke_all_sessions(current_user),
        message="Đăng xuất khỏi tất cả thiết bị hoàn tất",
    )


@router.post(
    "/lam-moi-phien",
    response_model=APIResponse[Any],
    dependencies=[Depends(RateLimiting(calls=20, period=60))],
)
async def refresh_session(
    request: Request, response: Response, veriq_refresh_token: str | None = Cookie(default=None)
):
    if not veriq_refresh_token:
        raise HTTPException(status_code=401, detail="Không tìm thấy phiên làm mới")
    client_ip = request.client.host if request.client else "unknown"
    token_data = await SessionService.refresh_session(veriq_refresh_token, client_ip)
    return APIResponse(
        data=set_refresh_cookie(response, request, token_data),
        message="Làm mới phiên đăng nhập hoàn tất",
        status=status.HTTP_200_OK,
    )
