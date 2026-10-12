import shutil
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import HTTPException

from src.core.storage import upload_file
from src.core.infrastructure.configuration import settings
from src.services.file import FileService
from src.services.upload import UploadService


class ChunkService:
    @staticmethod
    async def save_chunk(
        upload_id: str,
        chunk_index: int,
        total_chunks: int,
        filename: str,
        content: bytes,
        content_type: str,
        user_id: str,
    ) -> dict:
        try:
            normalized_id = str(UUID(upload_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Mã phiên tải lên không hợp lệ")

        if (
            total_chunks < 1
            or total_chunks > 1000
            or chunk_index < 0
            or chunk_index >= total_chunks
        ):
            raise HTTPException(status_code=400, detail="Thông tin phân đoạn không hợp lệ")

        chunk_dir = Path("storage/chunks") / user_id / normalized_id
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_path = chunk_dir / f"chunk_{chunk_index}"

        async with aiofiles.open(chunk_path, "wb") as stream:
            await stream.write(content)

        parts = [chunk_dir / f"chunk_{index}" for index in range(total_chunks)]
        if not all(part.is_file() for part in parts):
            return {"is_complete": False, "uploaded": chunk_index}

        total_size = sum(part.stat().st_size for part in parts)
        if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
            shutil.rmtree(chunk_dir)
            raise HTTPException(status_code=413, detail="Tệp tải lên vượt quá kích thước cho phép")

        quota = await FileService.get_storage_quota(user_id)
        if total_size > quota["storage_available"]:
            shutil.rmtree(chunk_dir)
            raise HTTPException(status_code=413, detail="Dung lượng lưu trữ không đủ")

        combined = bytearray()
        for part in parts:
            async with aiofiles.open(part, "rb") as stream:
                combined.extend(await stream.read())

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        path = UploadService.object_path(ext, content_type, user_id, False, False)
        try:
            await upload_file(bytes(combined), path, content_type)
        finally:
            shutil.rmtree(chunk_dir, ignore_errors=True)

        return {
            "is_complete": True,
            "url": path,
            "filename": filename,
            "size": total_size,
            "content_type": content_type,
        }
