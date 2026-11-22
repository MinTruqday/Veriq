from typing import List, Optional

from fastapi import HTTPException

from src.clients.accounts import AccountClient
from src.repositories.storage import storage_repository
from src.schemas.storage import StorageItemInDB
from src.services.activity import ActivityService


async def get_public_item(share_token: str) -> Optional[StorageItemInDB]:
    item = await storage_repository.find_one(
        {"share_token": share_token, "is_public": True}
    )
    return StorageItemInDB(**item) if item else None


async def share_item(item_id: str, email: str, role: str, owner_id: str) -> dict:
    if role != "editor":
        raise HTTPException(status_code=422, detail="Vai trò chia sẻ không hợp lệ")
    target_user = await AccountClient.get_by_email(email)
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản người dùng tương ứng với email",
        )
    target_user_id = str(target_user["_id"])
    if target_user_id == owner_id:
        raise HTTPException(
            status_code=400, detail="Không thể tự chia sẻ tài liệu cho chính mình"
        )
    item = await storage_repository.find_one({"_id": item_id, "owner_id": owner_id})
    if not item:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy dữ liệu hoặc thiếu quyền chia sẻ"
        )
    result = await storage_repository.update_one(
        {"_id": item_id, "owner_id": owner_id, "shared_with.user_id": {"$ne": target_user_id}},
        {"$addToSet": {"shared_with": {"user_id": target_user_id, "role": role}}},
    )
    if result.modified_count == 0:
        return {"message": "Tệp tin đã được chia sẻ"}
    return {"message": "Chia sẻ tệp hoàn tất"}


async def get_recent_items(owner_id: str, limit: int = 20) -> List[StorageItemInDB]:
    items = await storage_repository.find_many(
        {
            "$or": [{"owner_id": owner_id}, {"shared_with": {"$elemMatch": {"user_id": owner_id, "role": "editor"}}}],
            "is_trashed": False,
            "is_folder": False,
        },
        sort=[("updated_at", -1)],
        limit=limit,
    )
    return [StorageItemInDB(**item) for item in items]


async def share_internal(item_id: str, email: str, role: str, owner_id: str) -> dict:
    return await share_item(item_id, email, role, owner_id)


async def revoke_internal_share(item_id: str, target_user_id: str, owner_id: str) -> bool:
    item = await storage_repository.find_one({"_id": item_id, "owner_id": owner_id})
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp hoặc thiếu quyền")
    result = await storage_repository.update_one(
        {"_id": item_id, "owner_id": owner_id},
        {"$pull": {"shared_with": {"user_id": target_user_id}}},
    )
    await ActivityService.log_activity(item_id, owner_id, "REVOKE_SHARE")
    return result.modified_count > 0


async def get_shared_with_me_items(user_id: str) -> List[StorageItemInDB]:
    items = await storage_repository.find_many(
        {"shared_with": {"$elemMatch": {"user_id": user_id, "role": "editor"}}, "is_trashed": False},
        sort=[("updated_at", -1)],
    )
    return [StorageItemInDB(**item) for item in items]
