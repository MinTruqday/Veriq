from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from src.repositories.storage import storage_repository
from src.schemas.storage import StorageItemCreate, StorageItemInDB, StorageItemUpdate
from src.services.storage_analytics import get_storage_quota
from src.services.storage_paths import object_prefixes


class FileService:
    @staticmethod
    async def create_file_record(item: StorageItemCreate, owner_id: str) -> StorageItemInDB:
        if item.parent_id:
            parent = await storage_repository.find_one(
                {
                    "_id": item.parent_id,
                    "owner_id": owner_id,
                    "is_folder": True,
                    "is_trashed": {"$ne": True},
                }
            )
            if not parent:
                raise HTTPException(status_code=400, detail="Thư mục cha không hợp lệ")

        if not item.url or not item.url.startswith(object_prefixes(owner_id)):
            raise HTTPException(status_code=400, detail="Đường dẫn tệp không thuộc chủ sở hữu")

        existing = await storage_repository.find_one(
            {"owner_id": owner_id, "url": item.url}, {"_id": 1}
        )
        if existing:
            raise HTTPException(status_code=409, detail="Tệp đã được đăng ký trong kho lưu trữ")

        db_item = StorageItemInDB(**item.model_dump(), owner_id=owner_id)
        await storage_repository.insert(
            db_item.model_dump(by_alias=True)
        )
        return db_item

    @staticmethod
    async def get_file_by_id(file_id: str, owner_id: str) -> StorageItemInDB:
        doc = await storage_repository.find_one(
            {"_id": file_id, "owner_id": owner_id}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
        return StorageItemInDB(**doc)

    @staticmethod
    async def update_file_metadata(
        file_id: str, update_data: StorageItemUpdate, owner_id: str
    ) -> StorageItemInDB:
        payload = update_data.model_dump(exclude_unset=True)
        payload["updated_at"] = datetime.now(timezone.utc)
        res = await storage_repository.find_one_and_update(
            {"_id": file_id, "owner_id": owner_id}, {"$set": payload}
        )
        if not res:
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin cần cập nhật")
        return StorageItemInDB(**res)

    @staticmethod
    async def rename_file(file_id: str, new_name: str, owner_id: str) -> dict:
        res = await storage_repository.update_one(
            {"_id": file_id, "owner_id": owner_id, "is_folder": False},
            {"$set": {"name": new_name, "updated_at": datetime.now(timezone.utc)}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
        return {"status": "success", "file_id": file_id, "name": new_name}

    @staticmethod
    async def move_file(file_id: str, new_parent_id: Optional[str], owner_id: str) -> dict:
        if new_parent_id:
            parent = await storage_repository.find_one(
                {
                    "_id": new_parent_id,
                    "owner_id": owner_id,
                    "is_folder": True,
                    "is_trashed": {"$ne": True},
                }
            )
            if not parent:
                raise HTTPException(status_code=400, detail="Thư mục đích không tồn tại")
        res = await storage_repository.update_one(
            {"_id": file_id, "owner_id": owner_id, "is_folder": False},
            {"$set": {"parent_id": new_parent_id, "updated_at": datetime.now(timezone.utc)}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
        return {"status": "success", "file_id": file_id, "parent_id": new_parent_id}

    @staticmethod
    async def get_storage_quota(owner_id: str) -> dict:
        quota = await get_storage_quota(owner_id)
        limit = quota["limit"]
        used = quota["used"]
        return {
            "storage_limit": limit,
            "storage_used": used,
            "storage_available": max(0, limit - used),
            "percentage_used": round((used / limit) * 100, 2) if limit > 0 else 0,
        }
