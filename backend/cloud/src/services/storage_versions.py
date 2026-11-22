from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException

from src.core.storage import get_bucket, get_storage_client, original_content_length
from src.repositories.storage import storage_repository
from src.schemas.storage import FileVersion, StorageItemInDB
from src.services.activity import ActivityService
from src.services.storage_analytics import get_storage_quota
from src.services.storage_paths import object_prefixes


async def _owned_item(item_id: str, owner_id: str) -> Optional[StorageItemInDB]:
    item = await storage_repository.find_one(
        {"_id": item_id, "owner_id": owner_id}
    )
    return StorageItemInDB(**item) if item else None


async def _accessible_item(item_id: str, user_id: str) -> Optional[StorageItemInDB]:
    item = await storage_repository.find_one(
        {
            "_id": item_id,
            "is_trashed": False,
            "$or": [{"owner_id": user_id}, {"shared_with": {"$elemMatch": {"user_id": user_id, "role": "editor"}}}],
        }
    )
    return StorageItemInDB(**item) if item else None


async def add_version(
    item_id: str, owner_id: str, url: str, size: int
) -> Optional[StorageItemInDB]:
    item = await _owned_item(item_id, owner_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
    if item.is_folder:
        raise HTTPException(status_code=400, detail="Thư mục không hỗ trợ lịch sử phiên bản")
    if not url.startswith(object_prefixes(owner_id)):
        raise HTTPException(
            status_code=400, detail="Đường dẫn phiên bản không thuộc người dùng hiện tại"
        )
    try:
        client = await get_storage_client()
        metadata = await client.head_object(Bucket=get_bucket(url), Key=url)
    except Exception:
        raise HTTPException(status_code=503, detail="Dịch vụ lưu trữ tạm thời không khả dụng")
    if original_content_length(metadata) != size:
        raise HTTPException(
            status_code=409, detail="Kích thước phiên bản không khớp với dữ liệu đã tải lên"
        )
    quota = await get_storage_quota(owner_id)
    registered = await storage_repository.find_one(
        {"owner_id": owner_id, "$or": [{"url": url}, {"versions.url": url}]},
        {"_id": 1},
    )
    projected_usage = quota["used"] if registered else quota["used"] + size
    if projected_usage > quota["limit"]:
        raise HTTPException(status_code=413, detail="Dung lượng lưu trữ còn lại không đủ")
    update = {
        "$set": {"url": url, "size": size, "updated_at": datetime.now(timezone.utc)}
    }
    if item.url:
        old_version = FileVersion(url=item.url, size=item.size, created_at=item.updated_at)
        update["$push"] = {
            "versions": {
                "$each": [old_version.model_dump()],
                "$slice": -10,
            }
        }
    await storage_repository.replace_version(
        item_id,
        owner_id,
        update,
        registered.get("_id") if registered else None,
    )
    return await _owned_item(item_id, owner_id)


async def lock_item(item_id: str, owner_id: str) -> Optional[StorageItemInDB]:
    item = await _owned_item(item_id, owner_id)
    if not item or item.is_folder:
        raise HTTPException(
            status_code=400, detail="Chỉ có thể khóa tệp tin, không áp dụng cho thư mục"
        )
    if item.is_locked:
        raise HTTPException(status_code=400, detail="Tệp tin đã bị khóa")
    result = await storage_repository.find_one_and_update(
        {"_id": item_id, "owner_id": owner_id},
        {
            "$set": {
                "is_locked": True,
                "locked_by": owner_id,
                "locked_at": datetime.now(timezone.utc),
            }
        },
    )
    return StorageItemInDB(**result) if result else None


async def unlock_item(item_id: str, owner_id: str) -> Optional[StorageItemInDB]:
    item = await _owned_item(item_id, owner_id)
    if not item or item.is_folder:
        raise HTTPException(status_code=400, detail="Không tìm thấy tệp tin")
    if not item.is_locked:
        return item
    if item.locked_by != owner_id:
        raise HTTPException(
            status_code=403, detail="Chỉ người đã khóa tệp mới có quyền mở khóa"
        )
    result = await storage_repository.find_one_and_update(
        {"_id": item_id, "owner_id": owner_id},
        {"$set": {"is_locked": False, "locked_by": None, "locked_at": None}},
    )
    return StorageItemInDB(**result) if result else None


async def get_versions(item_id: str, user_id: str) -> List[dict]:
    item = await _accessible_item(item_id, user_id)
    if not item or item.is_folder:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tệp tin hoặc thư mục không hỗ trợ phiên bản",
        )
    results = [
        {
            "version_id": "current",
            "url": item.url,
            "size": item.size,
            "created_at": item.updated_at or item.created_at,
            "is_active": True,
        }
    ]
    results.extend(
        {
            "version_id": version.version_id,
            "url": version.url,
            "size": version.size,
            "created_at": version.created_at,
            "is_active": False,
        }
        for version in item.versions or []
    )
    return results


async def rollback_version(
    item_id: str, version_id: str, owner_id: str
) -> Optional[StorageItemInDB]:
    item = await _owned_item(item_id, owner_id)
    if not item or item.is_folder:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tin")
    if item.is_locked and item.locked_by != owner_id:
        raise HTTPException(status_code=403, detail="Tệp đang bị khóa bởi người dùng khác")
    target_version = None
    remaining_versions = []
    for version in item.versions or []:
        if version.version_id == version_id:
            target_version = version
        else:
            remaining_versions.append(version)
    if not target_version:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy phiên bản yêu cầu khôi phục"
        )
    remaining_versions.insert(
        0,
        FileVersion(
            url=item.url,
            size=item.size,
            created_at=item.updated_at or item.created_at,
        ),
    )
    result = await storage_repository.find_one_and_update(
        {"_id": item_id, "owner_id": owner_id},
        {
            "$set": {
                "url": target_version.url,
                "size": target_version.size,
                "versions": [
                    version.model_dump()
                    for version in remaining_versions[
                        : 10
                    ]
                ],
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    await ActivityService.log_activity(item_id, owner_id, "ROLLBACK_VERSION")
    return StorageItemInDB(**result) if result else None
