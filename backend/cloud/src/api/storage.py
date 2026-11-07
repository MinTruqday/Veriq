import secrets
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger

from src.core.dependency import CurrentUser, get_current_user, get_db
from src.core.response import APIResponse
from src.schemas.storage import (
    BulkActionRequest,
    FileVersionResponse,
    InternalShareRequest,
    ItemActivityResponse,
    QuotaAnalyticsResponse,
    StarredUpdateRequest,
    StorageItemCreate,
    StorageItemResponse,
    StorageItemUpdate,
    TagColorUpdateRequest,
)
from src.services.activity import ActivityService
from src.services.storage import StorageService

router = APIRouter(prefix="/luu-tru")


@router.post("/thu-muc", response_model=APIResponse[StorageItemResponse], status_code=201)
async def create_folder(
    data: StorageItemCreate = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    data.is_folder = True
    item = await StorageService.create_item(data, current_user.id)
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Khởi tạo thư mục lưu trữ mới hoàn tất",
        status=201,
    )


@router.post("/tap-tin", response_model=APIResponse[StorageItemResponse], status_code=201)
async def create_file(
    data: StorageItemCreate = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    data.is_folder = False
    quota = await StorageService.get_storage_quota(current_user.id)
    if (quota["used"] + data.size) > quota["limit"]:
        raise HTTPException(
            status_code=413, detail="Dung lượng lưu trữ của bạn đã vượt quá giới hạn cho phép"
        )
    item = await StorageService.create_item(data, current_user.id)
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Khởi tạo dữ liệu tệp tin lưu trữ mới hoàn tất",
        status=201,
    )


@router.get("/danh-sach", response_model=APIResponse[List[StorageItemResponse]])
async def list_items(
    parent_id: Optional[str] = None,
    is_trashed: bool = False,
    is_starred: Optional[bool] = None,
    tag: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    items = await StorageService.get_items_by_parent(
        parent_id, current_user.id, is_trashed, is_starred, tag
    )
    response_items = [StorageItemResponse(**item.dict()) for item in items]
    return APIResponse(
        data=response_items, message="Trích xuất nội dung thư mục lưu trữ hoàn tất", status=200
    )


@router.get("/tim-kiem", response_model=APIResponse[List[StorageItemResponse]])
async def search_items(
    q: str,
    type: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    items = await StorageService.search_items(q, current_user.id, type)
    return APIResponse(
        data=[StorageItemResponse(**item.dict()) for item in items],
        message="Trích xuất kết quả tìm kiếm dữ liệu lưu trữ hoàn tất",
        status=200,
    )


@router.get("/gan-day", response_model=APIResponse[List[StorageItemResponse]])
async def get_recent_items(
    limit: int = Query(default=20, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    items = await StorageService.get_recent_items(current_user.id, limit)
    return APIResponse(
        data=[StorageItemResponse(**item.dict()) for item in items],
        message="Trích xuất danh sách tệp truy cập gần đây hoàn tất",
        status=200,
    )


@router.get("/han-muc", response_model=APIResponse[Any])
async def get_storage_quota(
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    data = await StorageService.get_storage_quota(current_user.id)
    return APIResponse(
        data=data, message="Trích xuất thông tin hạn mức lưu trữ hoàn tất", status=200
    )


@router.post(
    "/tap-tin/{item_id}/loi-tat", response_model=APIResponse[StorageItemResponse], status_code=201
)
async def create_shortcut(
    item_id: str,
    target_parent_id: Optional[str] = Body(None, embed=True),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.create_shortcut(item_id, target_parent_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin gốc để tạo lối tắt")
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Khởi tạo lối tắt tệp tin lưu trữ hoàn tất",
        status=201,
    )


@router.get("/tai-xuong-zip")
async def download_zip(
    ids: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    import io
    import zipfile

    from fastapi.responses import StreamingResponse

    from src.core.storage import download_file

    item_ids = list(dict.fromkeys(i.strip() for i in ids.split(",") if i.strip()))
    if not item_ids or len(item_ids) > 50:
        raise HTTPException(status_code=400, detail="Số lượng tệp yêu cầu không hợp lệ")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        total_size = 0
        used_names = set()
        for i_id in item_ids:
            item = await StorageService.get_accessible_item(i_id, current_user.id)
            if not item or item.is_folder or not item.url:
                raise HTTPException(
                    status_code=404, detail="Không tìm thấy tệp hoặc thiếu quyền truy cập"
                )
            total_size += item.size
            if total_size > 500 * 1024 * 1024:
                raise HTTPException(
                    status_code=413, detail="Tổng dung lượng bản nén vượt quá giới hạn"
                )
            safe_name = item.name.replace("\\", "_").replace("/", "_")
            if safe_name in used_names:
                safe_name = f"{item.id}_{safe_name}"
            used_names.add(safe_name)
            try:
                file_data, _ = await download_file(item.url)
                zip_file.writestr(safe_name, file_data)
            except HTTPException:
                raise
            except Exception:
                logger.exception("Failed to add file to zip archive")
                raise HTTPException(status_code=502, detail="Không thể đọc tệp từ kho đối tượng")
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=storage_download.zip"},
    )


@router.put("/tap-tin/{item_id}", response_model=APIResponse[StorageItemResponse])
async def update_item(
    item_id: str,
    data: StorageItemUpdate = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    if data.is_public and data.is_public is True:
        current_item = await StorageService.get_item(item_id, current_user.id)
        if current_item and (not current_item.share_token):
            update_data_dict = data.model_dump(exclude_unset=True)
            update_data_dict["share_token"] = f"share_{secrets.token_urlsafe(32)}"
            item = await StorageService.update_item(
                item_id, current_user.id, StorageItemUpdate(**update_data_dict)
            )
        else:
            item = await StorageService.update_item(item_id, current_user.id, data)
    else:
        item = await StorageService.update_item(item_id, current_user.id, data)
    if not item:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy dữ liệu tệp tin hoặc thư mục yêu cầu"
        )
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Cập nhật dữ liệu tệp tin lưu trữ hoàn tất",
        status=200,
    )


@router.delete("/tap-tin/{item_id}", response_model=APIResponse[Any])
async def delete_item(
    item_id: str,
    hard_delete: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    if hard_delete:
        success = await StorageService.delete_item(item_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy dữ liệu tệp tin hoặc thư mục yêu cầu"
            )
        return APIResponse(
            data=None, message="Hủy bỏ vĩnh viễn dữ liệu lưu trữ hoàn tất", status=200
        )
    else:
        item = await StorageService.update_item(
            item_id, current_user.id, StorageItemUpdate(is_trashed=True)
        )
        if not item:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy dữ liệu tệp tin hoặc thư mục yêu cầu"
            )
        return APIResponse(
            data=None, message="Di chuyển dữ liệu vào khu vực lưu trữ tạm hoàn tất", status=200
        )


@router.post(
    "/tap-tin/{item_id}/sao-chep", response_model=APIResponse[StorageItemResponse], status_code=201
)
async def copy_item(
    item_id: str,
    target_parent_id: Optional[str] = Body(None, embed=True),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.copy_item(item_id, current_user.id, target_parent_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu tệp tin yêu cầu")
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Khởi tạo bản sao dữ liệu tệp tin hoàn tất",
        status=201,
    )


@router.post("/tap-tin/{item_id}/phien-ban", response_model=APIResponse[StorageItemResponse])
async def add_version(
    item_id: str,
    url: str = Body(..., embed=True),
    size: int = Body(..., embed=True),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.add_version(item_id, current_user.id, url, size)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu tệp tin yêu cầu")
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Cập nhật phiên bản dữ liệu lưu trữ mới hoàn tất",
        status=200,
    )


@router.post("/tap-tin/{item_id}/chia-se", response_model=APIResponse[Any])
async def share_archive(
    item_id: str,
    email: str = Body(..., embed=True),
    role: str = Body("viewer", embed=True),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    res = await StorageService.share_item(item_id, email, role, current_user.id)
    return APIResponse(data=None, message=res["message"], status=200)


@router.get("/chia-se/{share_token}", response_model=APIResponse[Any])
async def get_public_item(share_token: str, db=Depends(get_db)):
    item = await StorageService.get_public_item(share_token)
    if not item:
        raise HTTPException(
            status_code=404, detail="Liên kết chia sẻ dữ liệu không hợp lệ hoặc đã hết hạn"
        )
    data = StorageItemResponse(**item.model_dump()).model_dump(by_alias=True)
    if not item.is_folder and item.url:
        from src.services.upload import UploadService

        data.update(await UploadService.get_presigned_url(item.url))
    return APIResponse(data=data, message="Trích xuất thông tin chia sẻ hoàn tất", status=200)


@router.post("/thao-tac-hang-loat", response_model=APIResponse[Any])
async def bulk_action(
    req: BulkActionRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await StorageService.bulk_action(
        action=req.action,
        item_ids=req.item_ids,
        target_parent_id=req.target_parent_id,
        owner_id=current_user.id,
    )
    return APIResponse(data=result, message=f"Thao tác {req.action} hàng loạt hoàn tất", status=200)


@router.post("/tap-tin/{item_id}/khoa", response_model=APIResponse[StorageItemResponse])
async def lock_item(
    item_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.lock_item(item_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
    return APIResponse(
        data=StorageItemResponse(**item.dict()), message="Khóa tệp tin hoàn tất", status=200
    )


@router.post("/tap-tin/{item_id}/mo-khoa", response_model=APIResponse[StorageItemResponse])
async def unlock_item(
    item_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.unlock_item(item_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
    return APIResponse(
        data=StorageItemResponse(**item.dict()), message="Mở khóa tệp tin hoàn tất", status=200
    )


@router.get("/tap-tin/{item_id}/xem-truoc", response_model=APIResponse[Any])
async def get_preview_url(
    item_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.get_accessible_item(item_id, current_user.id)
    if not item or item.is_folder or not item.url:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy tệp tin hoặc không hỗ trợ xem trước"
        )

    from src.core.storage import get_bucket, get_storage_client

    try:
        client = await get_storage_client()
        url = await client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": get_bucket(item.url),
                "Key": item.url,
                "ResponseContentDisposition": "inline",
            },
            ExpiresIn=3600,
        )
        return APIResponse(
            data={"preview_url": url}, message="Tạo liên kết xem trước hoàn tất", status=200
        )
    except Exception as e:
        logger.error(f"Error generating preview url: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi tạo liên kết xem trước")


@router.get("/tap-tin/{item_id}/nhat-ky", response_model=APIResponse[List[ItemActivityResponse]])
async def get_item_activities(
    item_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.get_accessible_item(item_id, current_user.id)
    if not item:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy tệp tin hoặc không có quyền truy cập"
        )

    activities = await ActivityService.get_item_activities(item_id)
    return APIResponse(
        data=activities, message="Trích xuất nhật ký hoạt động của tệp tin hoàn tất", status=200
    )


@router.get("/tap-tin/{item_id}/phien-ban", response_model=APIResponse[List[FileVersionResponse]])
async def get_file_versions(
    item_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    versions = await StorageService.get_versions(item_id, current_user.id)
    return APIResponse(
        data=[FileVersionResponse(**v) for v in versions],
        message="Trích xuất lịch sử phiên bản tệp tin hoàn tất",
        status=200,
    )


@router.post(
    "/tap-tin/{item_id}/phien-ban/{version_id}/khoi-phuc",
    response_model=APIResponse[StorageItemResponse],
)
async def rollback_file_version(
    item_id: str,
    version_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.rollback_version(item_id, version_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Khôi phục phiên bản tệp tin hoàn tất",
        status=200,
    )


@router.patch("/tap-tin/{item_id}/yeu-thich", response_model=APIResponse[StorageItemResponse])
async def toggle_starred(
    item_id: str,
    req: StarredUpdateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.set_starred(item_id, req.is_starred, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Cập nhật trạng thái yêu thích hoàn tất",
        status=200,
    )


@router.patch("/tap-tin/{item_id}/nhan-dan", response_model=APIResponse[StorageItemResponse])
async def update_tags_and_color(
    item_id: str,
    req: TagColorUpdateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.set_tags_and_color(item_id, req.tags, req.color, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Cập nhật thẻ phân loại và nhãn màu hoàn tất",
        status=200,
    )


@router.get("/thung-rac", response_model=APIResponse[List[StorageItemResponse]])
async def get_trashed_items(
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    items = await StorageService.get_trashed_items(current_user.id)
    return APIResponse(
        data=[StorageItemResponse(**item.dict()) for item in items],
        message="Trích xuất danh sách thùng rác hoàn tất",
        status=200,
    )


@router.post("/thung-rac/{item_id}/khoi-phuc", response_model=APIResponse[StorageItemResponse])
async def restore_trash_item(
    item_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    item = await StorageService.restore_from_trash(item_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp trong thùng rác")
    return APIResponse(
        data=StorageItemResponse(**item.dict()),
        message="Khôi phục tệp từ thùng rác hoàn tất",
        status=200,
    )


@router.delete("/thung-rac/don-sach", response_model=APIResponse[Any])
async def empty_trash(
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await StorageService.empty_trash(current_user.id)
    return APIResponse(data=result, message="Dọn sạch thùng rác hoàn tất", status=200)


@router.get("/dung-luong/phan-tich", response_model=APIResponse[QuotaAnalyticsResponse])
async def get_quota_analytics(
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    data = await StorageService.get_quota_analytics(current_user.id)
    return APIResponse(
        data=QuotaAnalyticsResponse(**data),
        message="Trích xuất báo cáo phân tích dung lượng hoàn tất",
        status=200,
    )


@router.post("/tap-tin/{item_id}/chia-se-noi-bo", response_model=APIResponse[Any])
async def share_internal(
    item_id: str,
    req: InternalShareRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    res = await StorageService.share_internal(item_id, req.email, req.role, current_user.id)
    return APIResponse(data=None, message=res["message"], status=200)


@router.delete(
    "/tap-tin/{item_id}/chia-se-noi-bo/{target_user_id}", response_model=APIResponse[Any]
)
async def revoke_internal_share(
    item_id: str,
    target_user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    success = await StorageService.revoke_internal_share(item_id, target_user_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy quyền chia sẻ để thu hồi")
    return APIResponse(data=None, message="Thu hồi quyền chia sẻ hoàn tất", status=200)


@router.get("/duoc-chia-se-voi-toi", response_model=APIResponse[List[StorageItemResponse]])
async def get_shared_with_me(
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    items = await StorageService.get_shared_with_me_items(current_user.id)
    return APIResponse(
        data=[StorageItemResponse(**item.dict()) for item in items],
        message="Trích xuất danh sách tệp được chia sẻ hoàn tất",
        status=200,
    )
