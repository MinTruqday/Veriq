from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from src.core.dependency import CurrentUser, SystemRole, get_current_user
from src.core.response import APIResponse
from src.schemas.platform import (
    AccountUpdate,
    ActionReason,
    ConfigUpdate,
    ModelRegistryEntry,
    ProfileUpdate,
    ProjectPolicyUpdate,
    ProjectQuotaUpdate,
    ProjectStatusUpdate,
    ProviderUpdate,
    SystemRoleUpdate,
    UserCreateRequest,
)
from src.services.platform import (
    get_platform_config,
    require_system_admin,
    update_platform_config,
)
from src.services.platform_accounts import PlatformAccountService
from src.services.platform_ai import PlatformAiService
from src.services.platform_operations import PlatformOperationsService
from src.services.platform_projects import PlatformProjectService


router = APIRouter(tags=["Quản trị hệ thống"], dependencies=[Depends(require_system_admin)])


@router.post("/quan-tri/tai-khoan", response_model=APIResponse[Any], status_code=201)
async def create_account(
    payload: UserCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformAccountService.create(
            payload, request.client.host if request.client else "admin", current_user
        ),
        message="Tạo tài khoản và khởi tạo lời mời đặt mật khẩu hoàn tất",
    )


@router.get("/quan-tri/tai-khoan", response_model=APIResponse[Any])
async def list_accounts(
    search: str | None = None,
    system_role: SystemRole | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformAccountService.list(search, system_role, is_active, limit),
        message="Tải danh sách tài khoản hoàn tất",
    )


@router.patch("/quan-tri/tai-khoan/{user_id}", response_model=APIResponse[Any])
async def update_account(
    user_id: str, payload: AccountUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.update(user_id, payload, current_user),
        message="Cập nhật tài khoản và thu hồi phiên hoàn tất",
    )


@router.get("/quan-tri/tai-khoan/{user_id}", response_model=APIResponse[Any])
async def account_detail(user_id: str, current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformAccountService.detail(user_id),
        message="Tải chi tiết tài khoản hoàn tất",
    )


@router.patch("/quan-tri/tai-khoan/{user_id}/ho-so", response_model=APIResponse[Any])
async def update_account_profile(
    user_id: str, payload: ProfileUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.update_profile(user_id, payload, current_user),
        message="Cập nhật hồ sơ tài khoản hoàn tất",
    )


@router.post("/quan-tri/tai-khoan/{user_id}/kich-hoat", response_model=APIResponse[Any])
async def enable_account(
    user_id: str, payload: ActionReason, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.activate(user_id, payload, current_user),
        message="Cập nhật trạng thái tài khoản hoàn tất",
    )


@router.post("/quan-tri/tai-khoan/{user_id}/vo-hieu-hoa", response_model=APIResponse[Any])
async def disable_account(
    user_id: str, payload: ActionReason, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.disable(user_id, payload, current_user),
        message="Cập nhật trạng thái tài khoản hoàn tất",
    )


@router.post("/quan-tri/tai-khoan/{user_id}/khoa", response_model=APIResponse[Any])
async def lock_account(
    user_id: str, payload: ActionReason, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.lock(user_id, payload, current_user),
        message="Cập nhật trạng thái tài khoản hoàn tất",
    )


@router.post("/quan-tri/tai-khoan/{user_id}/mo-khoa", response_model=APIResponse[Any])
async def unlock_account(
    user_id: str, payload: ActionReason, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.unlock(user_id, payload, current_user),
        message="Cập nhật trạng thái tài khoản hoàn tất",
    )


@router.post("/quan-tri/tai-khoan/{user_id}/bat-buoc-doi-mat-khau", response_model=APIResponse[Any])
async def force_password_reset(
    user_id: str,
    payload: ActionReason,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformAccountService.force_password_reset(
            user_id,
            payload,
            request.client.host if request.client else "unknown",
            current_user,
        ),
        message="Khởi tạo quy trình đặt lại mật khẩu hoàn tất",
    )


@router.get("/quan-tri/tai-khoan/{user_id}/phien", response_model=APIResponse[Any])
async def list_user_sessions(user_id: str, current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformAccountService.sessions(user_id, current_user),
        message="Tải danh sách phiên đăng nhập hoàn tất",
    )


@router.delete("/quan-tri/tai-khoan/{user_id}/phien/{session_id}", response_model=APIResponse[Any])
async def revoke_user_session(
    user_id: str, session_id: str, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.revoke_session(user_id, session_id, current_user),
        message="Thu hồi phiên hoàn tất",
    )


@router.delete("/quan-tri/tai-khoan/{user_id}/phien", response_model=APIResponse[Any])
async def revoke_all_user_sessions(
    user_id: str, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.revoke_all_sessions(user_id, current_user),
        message="Thu hồi toàn bộ phiên hoàn tất",
    )


@router.patch("/quan-tri/tai-khoan/{user_id}/vai-tro-he-thong", response_model=APIResponse[Any])
async def update_system_role(
    user_id: str, payload: SystemRoleUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.update_system_role(user_id, payload, current_user),
        message="Cập nhật vai trò hệ thống hoàn tất",
    )


@router.get("/quan-tri/tai-khoan/{user_id}/vai-tro-du-an", response_model=APIResponse[Any])
async def list_user_memberships(
    user_id: str, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAccountService.memberships(user_id, current_user),
        message="Tải siêu dữ liệu thành viên dự án hoàn tất",
    )


@router.get("/quan-tri/tai-khoan/{user_id}/nhat-ky", response_model=APIResponse[Any])
async def list_user_audit(
    user_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformAccountService.audit(user_id, limit),
        message="Tải nhật ký bảo mật tài khoản hoàn tất",
    )


@router.get("/quan-tri/du-an", response_model=APIResponse[Any])
async def list_project_metadata(
    search: str = Query(default="", max_length=200),
    status: str = Query(default="", max_length=30),
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformProjectService.list(search, status, limit, current_user),
        message="Tải siêu dữ liệu dự án hoàn tất",
    )


@router.get("/quan-tri/du-an/{project_id}", response_model=APIResponse[Any])
async def project_metadata_detail(
    project_id: str, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformProjectService.detail(project_id, current_user),
        message="Tải siêu dữ liệu dự án hoàn tất",
    )


@router.patch("/quan-tri/du-an/{project_id}/trang-thai", response_model=APIResponse[Any])
async def update_project_status(
    project_id: str,
    payload: ProjectStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformProjectService.update_status(project_id, payload, current_user),
        message="Cập nhật trạng thái quản trị dự án hoàn tất",
    )


@router.patch("/quan-tri/du-an/{project_id}/han-muc", response_model=APIResponse[Any])
async def update_project_quota(
    project_id: str,
    payload: ProjectQuotaUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformProjectService.update_quota(project_id, payload, current_user),
        message="Cập nhật hạn mức dự án hoàn tất",
    )


@router.get("/quan-tri/nen-tang/chinh-sach-du-an", response_model=APIResponse[Any])
async def get_project_policy(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformProjectService.policy(),
        message="Tải chính sách tạo dự án hoàn tất",
    )


@router.patch("/quan-tri/nen-tang/chinh-sach-du-an", response_model=APIResponse[Any])
async def update_project_policy(
    payload: ProjectPolicyUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformProjectService.update_policy(payload, current_user),
        message="Cập nhật chính sách tạo dự án hoàn tất",
    )


@router.get("/quan-tri/ai/nha-cung-cap", response_model=APIResponse[Any])
async def list_ai_providers(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformAiService.providers(),
        message="Tải cấu hình nhà cung cấp AI hoàn tất",
    )


@router.patch("/quan-tri/ai/nha-cung-cap/{provider_id}", response_model=APIResponse[Any])
async def update_ai_provider(
    provider_id: str, payload: ProviderUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAiService.update_provider(provider_id, payload, current_user),
        message="Cập nhật cấu hình AI hoàn tất",
    )


@router.post("/quan-tri/ai/nha-cung-cap/{provider_id}/kiem-tra", response_model=APIResponse[Any])
async def test_ai_provider(provider_id: str, current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformAiService.test_provider(provider_id, current_user),
        message="Kiểm tra kết nối AI hoàn tất",
    )


@router.get("/quan-tri/van-hanh/tac-vu", response_model=APIResponse[Any])
async def list_operations_jobs(
    status: str = Query(default="", max_length=30),
    kind: str = Query(default="", max_length=100),
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformOperationsService.jobs(status, kind, limit, current_user),
        message="Tải danh sách tác vụ nền hoàn tất",
    )


@router.post(
    "/quan-tri/van-hanh/tac-vu/{job_id}/thu-lai", response_model=APIResponse[Any], status_code=202
)
async def retry_operations_job(job_id: str, current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformOperationsService.retry_job(job_id, current_user),
        message="Đưa tác vụ vào hàng đợi chạy lại hoàn tất",
    )


@router.post("/quan-tri/van-hanh/tac-vu/{job_id}/huy", response_model=APIResponse[Any])
async def cancel_operations_job(job_id: str, current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformOperationsService.cancel_job(job_id, current_user),
        message="Hủy tác vụ nền hoàn tất",
    )


@router.get("/quan-tri/van-hanh/dlq", response_model=APIResponse[Any])
async def list_dead_letter_jobs(
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformOperationsService.dead_letter_jobs(limit),
        message="Tải danh sách tác vụ lỗi hoàn tất",
    )


@router.post("/quan-tri/van-hanh/dlq/{job_id}/loai-bo", response_model=APIResponse[Any])
async def discard_dead_letter_job(
    job_id: str, payload: ActionReason, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformOperationsService.discard_job(job_id, payload, current_user),
        message="Loại bỏ tác vụ lỗi hoàn tất",
    )


@router.get("/quan-tri/suc-khoe", response_model=APIResponse[Any])
async def platform_health(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformOperationsService.platform_health(current_user),
        message="Tải trạng thái vận hành nền tảng hoàn tất",
    )


@router.get("/quan-tri/nhat-ky", response_model=APIResponse[Any])
async def list_auth_audit(
    action: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: CurrentUser = Depends(get_current_user),
):
    return APIResponse(
        data=await PlatformOperationsService.audit(action, limit),
        message="Tải nhật ký xác thực hoàn tất",
    )


@router.get("/quan-tri/bao-mat/chinh-sach-xac-thuc", response_model=APIResponse[Any])
async def get_auth_policy(current_user: CurrentUser = Depends(get_current_user)):
    return await get_platform_config("security_auth_policy", current_user)


@router.patch("/quan-tri/bao-mat/chinh-sach-xac-thuc", response_model=APIResponse[Any])
async def update_auth_policy(
    payload: ConfigUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return await update_platform_config("security_auth_policy", payload, current_user)


@router.get("/quan-tri/tich-hop", response_model=APIResponse[Any])
async def get_integrations(current_user: CurrentUser = Depends(get_current_user)):
    return await get_platform_config("integrations", current_user)


@router.patch("/quan-tri/tich-hop", response_model=APIResponse[Any])
async def update_integrations(
    payload: ConfigUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return await update_platform_config("integrations", payload, current_user)


@router.get("/quan-tri/luu-tru", response_model=APIResponse[Any])
async def get_storage_config(current_user: CurrentUser = Depends(get_current_user)):
    return await get_platform_config("storage", current_user)


@router.patch("/quan-tri/luu-tru", response_model=APIResponse[Any])
async def update_storage_config(
    payload: ConfigUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return await update_platform_config("storage", payload, current_user)


@router.get("/quan-tri/cau-hinh", response_model=APIResponse[Any])
async def get_system_config(current_user: CurrentUser = Depends(get_current_user)):
    return await get_platform_config("system", current_user)


@router.patch("/quan-tri/cau-hinh", response_model=APIResponse[Any])
async def update_system_config(
    payload: ConfigUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return await update_platform_config("system", payload, current_user)


@router.get("/quan-tri/ai/mo-hinh", response_model=APIResponse[Any])
async def list_ai_models(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformAiService.models(),
        message="Tải danh mục mô hình AI hoàn tất",
    )


@router.post("/quan-tri/ai/mo-hinh", response_model=APIResponse[Any], status_code=201)
async def register_ai_model(
    payload: ModelRegistryEntry, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAiService.register_model(payload, current_user),
        message="Đăng ký mô hình AI hoàn tất",
        status=201,
    )


@router.patch("/quan-tri/ai/mo-hinh/{model_id}", response_model=APIResponse[Any])
async def update_ai_model(
    model_id: str, payload: ConfigUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return APIResponse(
        data=await PlatformAiService.update_model(model_id, payload, current_user),
        message="Cập nhật mô hình AI hoàn tất",
    )


@router.get("/quan-tri/ai/mac-dinh", response_model=APIResponse[Any])
async def get_ai_defaults(current_user: CurrentUser = Depends(get_current_user)):
    return await PlatformAiService.defaults(current_user)


@router.patch("/quan-tri/ai/mac-dinh", response_model=APIResponse[Any])
async def update_ai_defaults(
    payload: ConfigUpdate, current_user: CurrentUser = Depends(get_current_user)
):
    return await PlatformAiService.update_defaults(payload, current_user)


@router.get("/quan-tri/ai/phien-ban", response_model=APIResponse[Any])
async def get_ai_versions(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformAiService.versions(),
        message="Tải phiên bản AI đang hoạt động hoàn tất",
    )


@router.post("/quan-tri/luu-tru/kiem-tra", response_model=APIResponse[Any])
async def test_storage(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformOperationsService.test_storage(current_user),
        message="Kiểm tra kho lưu trữ hoàn tất",
    )


@router.get("/quan-tri/tich-hop/suc-khoe", response_model=APIResponse[Any])
async def integration_health(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformOperationsService.integration_health(),
        message="Tải trạng thái tích hợp hoàn tất",
    )


@router.get("/quan-tri/van-hanh/so-lieu", response_model=APIResponse[Any])
async def operations_metrics(current_user: CurrentUser = Depends(get_current_user)):
    return APIResponse(
        data=await PlatformOperationsService.metrics(),
        message="Tải số liệu vận hành hoàn tất",
    )


@router.get("/quan-tri/nhat-ky/xuat")
async def export_global_audit(current_user: CurrentUser = Depends(get_current_user)):
    return StreamingResponse(
        iter([await PlatformOperationsService.export_audit(current_user)]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=veriq-global-audit.csv"},
    )
