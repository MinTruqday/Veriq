import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from loguru import logger

from src.core.infrastructure.configuration import settings
from src.core.storage import generate_presigned_url, get_bucket, get_storage_client, upload_file
from src.repositories.storage import (
    storage_repository,
    temporary_file_repository,
    upload_reservation_repository,
)
from src.schemas.storage import StorageItemCreate
from src.services.storage import StorageService
from src.services.storage_paths import object_prefixes


class UploadService:
    allowed_extensions = {
        "pdf",
        "docx",
        "doc",
        "xlsx",
        "xls",
        "pptx",
        "ppt",
        "txt",
        "zip",
        "csv",
        "json",
        "md",
        "png",
        "jpg",
        "jpeg",
        "webp",
        "webm",
        "veriq",
        "veriqx",
        "mp4",
        "mov",
        "m4v",
        "mp3",
        "wav",
        "ogg",
        "oga",
        "m4a",
        "aac",
        "flac",
    }
    image_extensions = {"png", "jpg", "jpeg", "webp"}
    video_extensions = {"webm", "mp4", "mov", "m4v"}
    audio_extensions = {"mp3", "wav", "ogg", "oga", "m4a", "aac", "flac"}

    @staticmethod
    def validate_filename(filename: str, content_type: str, image_only: bool = False) -> str:
        if not filename or filename != os.path.basename(filename) or filename in {".", ".."}:
            raise HTTPException(status_code=400, detail="Tên tệp không hợp lệ")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed = UploadService.image_extensions if image_only else UploadService.allowed_extensions
        if ext not in allowed or ext == "svg" or "svg" in content_type.lower():
            raise HTTPException(status_code=400, detail="Định dạng tệp tin không được hỗ trợ")
        if image_only and not content_type.lower().startswith("image/"):
            raise HTTPException(status_code=400, detail="Định dạng hình ảnh không hợp lệ")
        if ext in UploadService.image_extensions and not content_type.lower().startswith("image/"):
            raise HTTPException(status_code=400, detail="Kiểu nội dung hình ảnh không hợp lệ")
        if ext in UploadService.video_extensions and not content_type.lower().startswith("video/"):
            raise HTTPException(status_code=400, detail="Kiểu nội dung video không hợp lệ")
        if ext in UploadService.audio_extensions and not content_type.lower().startswith("audio/"):
            raise HTTPException(status_code=400, detail="Kiểu nội dung âm thanh không hợp lệ")
        return ext

    @staticmethod
    async def read_limited(file) -> bytes:
        content = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
        if not content:
            raise HTTPException(status_code=400, detail="Tệp tải lên không được để trống")
        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Tệp tải lên vượt quá kích thước cho phép")
        return content

    @staticmethod
    def object_path(
        ext: str,
        content_type: str,
        owner_id: str | None,
        is_system: bool,
        is_message_attachment: bool,
        is_temporary: bool = False,
    ) -> str:
        normalized_type = content_type.lower()
        if normalized_type.startswith("image/"):
            kind = "images"
        elif normalized_type.startswith("video/"):
            kind = "videos"
        elif normalized_type.startswith("audio/"):
            kind = "audio"
        else:
            kind = "documents"
        if is_system:
            return f"system/{kind}/{uuid.uuid4().hex}.{ext}"
        if owner_id and is_temporary:
            return f"temp/{owner_id}/{uuid.uuid4().hex}.{ext}"
        if owner_id:
            folder = "message_attachments" if is_message_attachment else kind
            return f"users/{owner_id}/{folder}/{uuid.uuid4().hex}.{ext}"
        return f"public/{kind}/{uuid.uuid4().hex}.{ext}"

    @staticmethod
    async def upload_image(file, owner_id: str | None = None, is_system: bool = False):
        content_type = file.content_type or "application/octet-stream"
        ext = UploadService.validate_filename(file.filename, content_type, True)
        content = await UploadService.read_limited(file)
        path = UploadService.object_path(ext, content_type, owner_id, is_system, False)
        try:
            await upload_file(content, path, content_type)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Image storage operation failed")
            raise HTTPException(status_code=500, detail="Không thể lưu trữ tệp hình ảnh")
        return {
            "url": path,
            "filename": file.filename,
            "size": len(content),
            "content_type": content_type,
        }

    @staticmethod
    async def upload_document(
        file,
        owner_id: str | None = None,
        is_system: bool = False,
        is_message_attachment: bool = False,
        is_temporary: bool = False,
    ):
        content_type = file.content_type or "application/octet-stream"
        ext = UploadService.validate_filename(file.filename, content_type)
        content = await UploadService.read_limited(file)
        path = UploadService.object_path(
            ext, content_type, owner_id, is_system, is_message_attachment, is_temporary
        )
        try:
            await upload_file(content, path, content_type)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Document storage operation failed")
            raise HTTPException(status_code=500, detail="Không thể lưu trữ tài liệu")
        return {
            "url": path,
            "filename": file.filename,
            "extension": ext,
            "size": len(content),
            "content_type": content_type,
        }

    @staticmethod
    async def get_presigned_url(file_path: str):
        if ".." in file_path or file_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Đường dẫn tệp tin không hợp lệ")
        try:
            return {"download_url": await generate_presigned_url(file_path, 3600)}
        except Exception:
            logger.exception("Failed to generate presigned download URL")
            raise HTTPException(status_code=500, detail="Không thể khởi tạo liên kết tải xuống")

    @staticmethod
    async def get_presigned_upload_url(
        filename: str,
        content_type: str,
        owner_id: str,
        is_system: bool = False,
        is_message_attachment: bool = False,
        is_temporary: bool = False,
    ):
        from src.core.storage import generate_presigned_put_url

        ext = UploadService.validate_filename(filename, content_type)
        path = UploadService.object_path(
            ext, content_type, owner_id, is_system, is_message_attachment, is_temporary
        )
        try:
            url = await generate_presigned_put_url(path, content_type, 3600)
            return {"upload_url": url, "file_path": path}
        except Exception:
            logger.exception("Failed to generate presigned upload URL")
            raise HTTPException(status_code=500, detail="Không thể khởi tạo liên kết tải lên")

    @staticmethod
    async def validate_svg(file):
        if file.filename and file.filename.lower().endswith(".svg"):
            content = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
            text = content.decode("utf-8", errors="ignore")
            if re.search("<!ENTITY", text, re.IGNORECASE) or re.search(
                "<!DOCTYPE", text, re.IGNORECASE
            ):
                raise HTTPException(status_code=400, detail="Tệp đồ họa vector không an toàn")
            await file.seek(0)

    @staticmethod
    async def file_size(file):
        await file.seek(0)
        file.file.seek(0, 2)
        size = file.file.tell()
        await file.seek(0)
        UploadService.validate_size(size)
        return size

    @staticmethod
    def validate_size(size: int):
        if size < settings.MIN_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="Tệp tải lên không được để trống")
        if size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Tệp tải lên vượt quá kích thước cho phép")

    @staticmethod
    async def enforce_quota(user_id: str, additional_size: int):
        quota = await StorageService.get_storage_quota(user_id)
        if quota["used"] + additional_size > quota["limit"]:
            raise HTTPException(status_code=400, detail="Dung lượng lưu trữ đã đầy")

    @staticmethod
    async def register_item(result: dict, user_id: str, parent_id: str | None = None):
        return await StorageService.create_item(
            StorageItemCreate(
                name=result["filename"],
                is_folder=False,
                url=result["url"],
                size=result["size"],
                mime_type=result["content_type"],
                parent_id=parent_id,
            ),
            user_id,
        )

    @staticmethod
    async def can_download(file_path: str, user_id: str, is_system_admin: bool):
        if ".." in file_path or file_path.startswith("/"):
            return False
        if file_path.startswith("public/"):
            return True
        if file_path.startswith(object_prefixes(user_id)):
            return True
        if file_path.startswith(f"temp/{user_id}/"):
            return True
        item = await storage_repository.find_one(
            {
                "url": file_path,
                "is_trashed": False,
                "$or": [{"owner_id": user_id}, {"shared_with.user_id": user_id}],
            },
            {"_id": 1},
        )
        return bool(item) or bool(is_system_admin and file_path.startswith("system/"))

    @staticmethod
    async def reserve(file_path: str, reservation: dict):
        await upload_reservation_repository.reserve(file_path, 3600, reservation)

    @staticmethod
    async def confirm_reservation(file_path: str, expected: dict):
        raw = await upload_reservation_repository.consume(file_path)
        if not raw:
            raise HTTPException(
                status_code=409, detail="Yêu cầu tải lên không tồn tại hoặc đã được xác nhận"
            )
        if json.loads(raw) != expected:
            raise HTTPException(status_code=400, detail="Thông tin xác nhận tải lên không hợp lệ")

    @staticmethod
    async def verify_stored_object(file_path: str, size: int, content_type: str):
        storage = await get_storage_client()
        try:
            metadata = await storage.head_object(Bucket=get_bucket(file_path), Key=file_path)
        except Exception as error:
            raise HTTPException(status_code=400, detail="Không tìm thấy tệp đã tải lên") from error
        actual_type = (metadata.get("ContentType") or "").split(";", 1)[0].lower()
        if metadata.get("ContentLength") != size or actual_type != content_type.lower():
            await storage.delete_object(Bucket=get_bucket(file_path), Key=file_path)
            raise HTTPException(status_code=400, detail="Nội dung tải lên không khớp yêu cầu")

    @staticmethod
    async def record_temporary_file(owner_id: str, file_path: str, filename: str):
        now = datetime.now(timezone.utc)
        await temporary_file_repository.insert(
            {
                "owner_id": owner_id,
                "url": file_path,
                "original_filename": filename,
                "created_at": now,
                "expires_at": now + timedelta(days=14),
            }
        )
