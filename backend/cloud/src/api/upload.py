import shutil
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, Response

from src.core.dependency import (
    CurrentUser,
    SystemRole,
    get_current_user,
    get_db,
    require_system_admin,
)
from src.core.response import APIResponse
from src.core.storage import download_file
from src.schemas.upload import ConfirmUploadRequest, PresignedUrlRequest
from src.services.upload import UploadService

router = APIRouter(prefix="/tai-len")


@router.post("/hinh-anh", response_model=APIResponse[Any], status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_system_admin),
    db=Depends(get_db),
) -> Any:
    await UploadService.validate_svg(file)
    result = await UploadService.upload_image(file, owner_id=current_user.id, is_system=True)
    return APIResponse(data=result, message="Truyền tải hình ảnh hoàn tất", status=201)


@router.post("/tai-lieu", response_model=APIResponse[Any], status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_system_admin),
    db=Depends(get_db),
) -> Any:
    result = await UploadService.upload_document(file, owner_id=current_user.id, is_system=True)
    return APIResponse(data=result, message="Truyền tải và lưu trữ tài liệu hoàn tất", status=201)


@router.post("/tap-tin", response_model=APIResponse[Any], status_code=201)
async def upload_asset(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
) -> Any:
    size = await UploadService.file_size(file)
    await UploadService.enforce_quota(current_user.id, size)
    result = await UploadService.upload_document(file, owner_id=current_user.id)
    item = await UploadService.register_item(result, current_user.id)
    return APIResponse(
        data={**result, "item_id": item.id}, message="Truyền tải tệp tin hoàn tất", status=201
    )


@router.post("/duong-dan-ky-truoc", response_model=APIResponse[Any])
async def get_presigned_url_for_upload(
    req: PresignedUrlRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
) -> Any:
    if req.is_system and current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Không có quyền tải tệp hệ thống")
    is_temporary = req.is_message_attachment
    if not req.is_system and not is_temporary:
        await UploadService.enforce_quota(current_user.id, req.size)
    result = await UploadService.get_presigned_upload_url(
        req.filename,
        req.content_type,
        current_user.id,
        req.is_system,
        req.is_message_attachment,
        is_temporary,
    )
    reservation = {
        "owner_id": current_user.id,
        "filename": req.filename,
        "size": req.size,
        "content_type": req.content_type,
        "is_system": req.is_system,
        "is_message_attachment": req.is_message_attachment,
    }
    await UploadService.reserve(result["file_path"], reservation)
    return APIResponse(
        data=result, message="Khởi tạo đường dẫn truyền tải bảo mật hoàn tất", status=200
    )


@router.post("/xac-nhan", response_model=APIResponse[Any], status_code=201)
async def confirm_upload(
    req: ConfirmUploadRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
) -> Any:
    if req.is_system and current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Không có quyền tải tệp hệ thống")
    expected = {
        "owner_id": current_user.id,
        "filename": req.filename,
        "size": req.size,
        "content_type": req.content_type,
        "is_system": req.is_system,
        "is_message_attachment": req.is_message_attachment,
    }
    await UploadService.confirm_reservation(req.file_path, expected)
    await UploadService.verify_stored_object(req.file_path, req.size, req.content_type)
    result = {
        "url": req.file_path,
        "filename": req.filename,
        "size": req.size,
        "content_type": req.content_type,
    }
    if req.is_system:
        return APIResponse(data=result, message="Xác thực tải lên hệ thống hoàn tất", status=201)
    is_temporary = req.is_message_attachment
    if is_temporary:
        await UploadService.record_temporary_file(
            current_user.id, req.file_path, req.filename
        )
        result["expires_in_days"] = 14
    else:
        await UploadService.enforce_quota(current_user.id, req.size)
        item = await UploadService.register_item(result, current_user.id)
        result["item_id"] = item.id
    return APIResponse(data=result, message="Xác thực truyền tải tệp hoàn tất", status=201)


@router.get("/luu-tru/xem-truoc/{file_path:path}", response_model=APIResponse[Any])
async def get_presigned_preview_url(
    file_path: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    if not await UploadService.can_download(
        file_path, current_user.id, current_user.system_role == SystemRole.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Không có quyền xem trước tệp này")
    url_data = await UploadService.get_presigned_url(file_path)
    return APIResponse(
        data={"preview_url": url_data["download_url"]}, message="Tạo liên kết xem trước hoàn tất"
    )


@router.get("/luu-tru/{file_path:path}")
async def get_presigned_download_url(
    file_path: str,
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    if not await UploadService.can_download(
        file_path, current_user.id, current_user.system_role == SystemRole.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Không có quyền tải xuống tệp này")
    url_data = await UploadService.get_presigned_url(file_path)
    return RedirectResponse(url=url_data["download_url"], status_code=302)


@router.get("/noi-dung/{file_path:path}")
async def get_message_attachment_content(
    file_path: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    if not await UploadService.can_download(
        file_path, current_user.id, current_user.system_role == SystemRole.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Không có quyền tải xuống tệp này")
    content, content_type = await download_file(file_path)
    return Response(content=content, media_type=content_type)


@router.post("/phan-doan", response_model=APIResponse[Any], status_code=201)
async def upload_chunk(
    file: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...),
    current_user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
) -> Any:
    try:
        normalized_id = str(UUID(upload_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Mã phiên tải lên không hợp lệ")
    UploadService.validate_filename(filename, file.content_type or "application/octet-stream")
    if total_chunks < 1 or total_chunks > 1000 or chunk_index < 0 or chunk_index >= total_chunks:
        raise HTTPException(status_code=400, detail="Thông tin phân đoạn không hợp lệ")
    chunk = await UploadService.read_limited(file)
    chunk_dir = Path("storage/chunks") / current_user.id / normalized_id
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = chunk_dir / f"chunk_{chunk_index}"
    async with aiofiles.open(chunk_path, "wb") as stream:
        await stream.write(chunk)
    parts = [chunk_dir / f"chunk_{index}" for index in range(total_chunks)]
    if not all(part.is_file() for part in parts):
        return APIResponse(
            data={"uploaded": chunk_index}, message="Truyền tải phân đoạn hoàn tất", status=200
        )
    total_size = sum(part.stat().st_size for part in parts)
    try:
        UploadService.validate_size(total_size)
    except HTTPException:
        shutil.rmtree(chunk_dir)
        raise
    await UploadService.enforce_quota(current_user.id, total_size)
    content = bytearray()
    for part in parts:
        async with aiofiles.open(part, "rb") as stream:
            content.extend(await stream.read())
    from src.core.storage import upload_file

    ext = filename.rsplit(".", 1)[-1].lower()
    content_type = file.content_type or "application/octet-stream"
    path = UploadService.object_path(ext, content_type, current_user.id, False, False)
    try:
        await upload_file(bytes(content), path, content_type)
        result = {
            "url": path,
            "filename": filename,
            "size": total_size,
            "content_type": content_type,
        }
        item = await UploadService.register_item(result, current_user.id)
        result["item_id"] = item.id
    finally:
        shutil.rmtree(chunk_dir, ignore_errors=True)
    return APIResponse(data=result, message="Truyền tải tệp tin hoàn tất", status=201)


@router.post("/yeu-cau/{token}", response_model=APIResponse[Any], status_code=201)
async def upload_via_request(
    token: str,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    db=Depends(get_db),
) -> Any:
    from src.services.file_request import FileRequestService

    req_info = await FileRequestService.validate_request(token, password)
    if not req_info or "error" in req_info:
        raise HTTPException(
            status_code=403, detail="Liên kết không hợp lệ, hết hạn hoặc sai mật khẩu"
        )

    size = await UploadService.file_size(file)
    owner_id = req_info["owner_id"]
    target_folder_id = req_info["target_folder_id"]

    await UploadService.enforce_quota(owner_id, size)
    result = await UploadService.upload_document(file, owner_id=owner_id)

    item = await UploadService.register_item(result, owner_id, target_folder_id)
    result["item_id"] = item.id
    return APIResponse(data=result, message="Truyền tải tệp tin qua yêu cầu hoàn tất", status=201)
