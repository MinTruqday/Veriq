from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from src.repositories.storage import storage_repository
from src.schemas.storage import StorageItemCreate, StorageItemInDB, StorageItemUpdate
from src.services.storage_analytics import get_quota_analytics, get_storage_quota
from src.services.storage_paths import object_prefixes
from src.services.storage_sharing import (
    get_public_item,
    get_recent_items,
    get_shared_with_me_items,
    revoke_internal_share,
    share_internal,
    share_item,
)
from src.services.storage_trash import (
    delete_item,
    empty_trash,
    get_trashed_items,
    restore_from_trash,
)
from src.services.storage_versions import (
    add_version,
    get_versions,
    lock_item,
    rollback_version,
    unlock_item,
)


class StorageService:
    @staticmethod
    async def create_item(item: StorageItemCreate, owner_id: str) -> StorageItemInDB:
        if item.parent_id:
            parent = await StorageService.get_item(item.parent_id, owner_id)
            if not parent or not parent.is_folder or parent.is_trashed:
                raise HTTPException(status_code=400, detail="Thư mục cha không hợp lệ")
        if not item.is_folder:
            if not item.url or not item.url.startswith(object_prefixes(owner_id)):
                raise HTTPException(status_code=400, detail="Đường dẫn tệp không thuộc chủ sở hữu")
            existing = await storage_repository.find_one(
                {"owner_id": owner_id, "url": item.url}, {"_id": 1}
            )
            if existing:
                raise HTTPException(status_code=409, detail="Tệp đã được đăng ký trong kho lưu trữ")
            from src.core.storage import get_bucket, get_storage_client, original_content_length

            try:
                client = await get_storage_client()
                metadata = await client.head_object(Bucket=get_bucket(item.url), Key=item.url)
            except Exception:
                raise HTTPException(
                    status_code=400, detail="Không tìm thấy dữ liệu tệp trong kho đối tượng"
                )
            if original_content_length(metadata) != item.size:
                raise HTTPException(
                    status_code=400, detail="Kích thước tệp không khớp dữ liệu lưu trữ"
                )
        db_item = StorageItemInDB(**item.model_dump(), owner_id=owner_id)
        await storage_repository.insert(
            db_item.model_dump(by_alias=True)
        )
        return db_item

    get_storage_quota = staticmethod(get_storage_quota)

    @staticmethod
    async def create_shortcut(
        item_id: str, parent_id: Optional[str], owner_id: str
    ) -> Optional[StorageItemInDB]:
        target = await StorageService.get_accessible_item(item_id, owner_id)
        if not target:
            return None
        if parent_id:
            parent = await StorageService.get_item(parent_id, owner_id)
            if not parent or not parent.is_folder:
                return None
        shortcut = StorageItemInDB(
            name=f"Shortcut to {target.name}",
            parent_id=parent_id,
            owner_id=owner_id,
            is_folder=False,
            is_shortcut=True,
            target_id=item_id,
        )
        await storage_repository.insert(
            shortcut.model_dump(by_alias=True)
        )
        return shortcut

    @staticmethod
    async def get_items_by_parent(
        parent_id: Optional[str],
        owner_id: str,
        is_trashed: bool = False,
        is_starred: Optional[bool] = None,
        tag: Optional[str] = None,
    ) -> List[StorageItemInDB]:
        access_query = {"$or": [{"owner_id": owner_id}, {"shared_with.user_id": owner_id}]}
        if parent_id:
            parent = await StorageService.get_accessible_item(parent_id, owner_id)
            if not parent:
                return []
            access_query = {"owner_id": parent.owner_id}
        query = {**access_query, "parent_id": parent_id, "is_trashed": is_trashed}
        if is_starred is not None:
            query["is_starred"] = is_starred
        if tag:
            query["tags"] = tag
        items = await storage_repository.find_many(
            query,
            sort=[("is_folder", -1), ("name", 1)],
        )
        return [StorageItemInDB(**item) for item in items]

    @staticmethod
    async def search_items(
        query_str: str, owner_id: str, type_filter: Optional[str] = None
    ) -> List[StorageItemInDB]:
        query = {
            "$or": [{"owner_id": owner_id}, {"shared_with.user_id": owner_id}],
            "is_trashed": False,
            "name": {"$regex": query_str, "$options": "i"},
        }
        if type_filter == "folder":
            query["is_folder"] = True
        elif type_filter == "file":
            query["is_folder"] = False
        items = await storage_repository.find_many(query, sort=[("created_at", -1)])
        return [StorageItemInDB(**item) for item in items]

    @staticmethod
    async def get_item(item_id: str, owner_id: str = None) -> Optional[StorageItemInDB]:
        query = {"_id": item_id}
        if owner_id:
            query["owner_id"] = owner_id
        item = await storage_repository.find_one(query)
        if item:
            return StorageItemInDB(**item)
        return None

    @staticmethod
    async def get_accessible_item(item_id: str, user_id: str) -> Optional[StorageItemInDB]:
        item = await storage_repository.find_one(
            {
                "_id": item_id,
                "is_trashed": False,
                "$or": [{"owner_id": user_id}, {"shared_with.user_id": user_id}],
            }
        )
        return StorageItemInDB(**item) if item else None

    @staticmethod
    async def update_item(
        item_id: str, owner_id: str, update_data: StorageItemUpdate
    ) -> Optional[StorageItemInDB]:
        item = await StorageService.get_item(item_id, owner_id)
        if not item:
            return None

        if item.is_locked and item.locked_by != owner_id:
            raise HTTPException(status_code=403, detail="Tệp đang bị khóa bởi người dùng khác")

        update_dict = update_data.model_dump(exclude_unset=True)
        if "parent_id" in update_dict and update_dict["parent_id"]:
            if update_dict["parent_id"] == item_id:
                return None
            parent = await StorageService.get_item(update_dict["parent_id"], owner_id)
            if not parent or not parent.is_folder or parent.is_trashed:
                return None
            ancestor = parent
            while ancestor.parent_id:
                if ancestor.parent_id == item_id:
                    return None
                ancestor = await StorageService.get_item(ancestor.parent_id, owner_id)
                if not ancestor:
                    return None
        if not update_dict:
            return await StorageService.get_item(item_id, owner_id)
        update_dict["updated_at"] = datetime.now(timezone.utc)
        result = await storage_repository.find_one_and_update(
            {"_id": item_id, "owner_id": owner_id}, {"$set": update_dict}
        )
        if result:
            if item.is_folder and "is_trashed" in update_dict:
                pending = [item_id]
                descendant_ids = []
                while pending:
                    children = await storage_repository.find_many(
                        {"owner_id": owner_id, "parent_id": {"$in": pending}},
                        {"_id": 1},
                    )
                    pending = [child["_id"] for child in children]
                    descendant_ids.extend(pending)
                if descendant_ids:
                    await storage_repository.update_many(
                        {"_id": {"$in": descendant_ids}, "owner_id": owner_id},
                        {
                            "$set": {
                                "is_trashed": update_dict["is_trashed"],
                                "updated_at": datetime.now(timezone.utc),
                            }
                        },
                    )
            return StorageItemInDB(**result)
        return None

    delete_item = staticmethod(delete_item)

    @staticmethod
    async def _copy_children(source_parent_id: str, new_parent_id: str, owner_id: str):
        children = await storage_repository.find_many(
            {"owner_id": owner_id, "parent_id": source_parent_id, "is_trashed": False}
        )
        for child in children:
            child_dict = StorageItemInDB(**child).model_dump()
            child_id_old = child_dict.pop("id", None)
            child_dict["parent_id"] = new_parent_id
            new_child = StorageItemInDB(**child_dict)
            await storage_repository.insert(
                new_child.model_dump(by_alias=True)
            )
            if new_child.is_folder:
                await StorageService._copy_children(str(child_id_old), str(new_child.id), owner_id)

    @staticmethod
    async def copy_item(
        item_id: str, owner_id: str, target_parent_id: Optional[str] = None
    ) -> Optional[StorageItemInDB]:
        item = await StorageService.get_item(item_id, owner_id)
        if not item:
            return None
        if target_parent_id:
            parent = await StorageService.get_item(target_parent_id, owner_id)
            if not parent or not parent.is_folder or parent.is_trashed:
                return None
        new_item_dict = item.model_dump()
        new_item_dict["name"] = f"{item.name} (Copy)"
        if target_parent_id is not None:
            new_item_dict["parent_id"] = target_parent_id
        new_item_dict.pop("id", None)
        new_item = StorageItemInDB(**new_item_dict)
        await storage_repository.insert(
            new_item.model_dump(by_alias=True)
        )
        if item.is_folder:
            await StorageService._copy_children(item_id, str(new_item.id), owner_id)
        return new_item

    add_version = staticmethod(add_version)

    get_public_item = staticmethod(get_public_item)
    share_item = staticmethod(share_item)
    get_recent_items = staticmethod(get_recent_items)

    lock_item = staticmethod(lock_item)
    unlock_item = staticmethod(unlock_item)

    @staticmethod
    async def bulk_action(
        action: str, item_ids: List[str], target_parent_id: Optional[str], owner_id: str
    ) -> dict:
        success_count = 0
        failed_count = 0
        for i_id in item_ids:
            try:
                if action == "delete":
                    res = await StorageService.update_item(
                        i_id, owner_id, StorageItemUpdate(is_trashed=True)
                    )
                    if res:
                        success_count += 1
                    else:
                        failed_count += 1
                elif action == "move":
                    res = await StorageService.update_item(
                        i_id, owner_id, StorageItemUpdate(parent_id=target_parent_id)
                    )
                    if res:
                        success_count += 1
                    else:
                        failed_count += 1
                elif action == "copy":
                    res = await StorageService.copy_item(i_id, owner_id, target_parent_id)
                    if res:
                        success_count += 1
                    else:
                        failed_count += 1
            except Exception:
                failed_count += 1
        return {"success": success_count, "failed": failed_count}

    get_versions = staticmethod(get_versions)
    rollback_version = staticmethod(rollback_version)

    @staticmethod
    async def set_starred(
        item_id: str, is_starred: bool, owner_id: str
    ) -> Optional[StorageItemInDB]:
        item = await StorageService.get_item(item_id, owner_id)
        if not item:
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp hoặc thư mục")

        result = await storage_repository.find_one_and_update(
            {"_id": item_id, "owner_id": owner_id},
            {"$set": {"is_starred": is_starred, "updated_at": datetime.now(timezone.utc)}},
        )
        from src.services.activity import ActivityService

        await ActivityService.log_activity(item_id, owner_id, "STAR" if is_starred else "UNSTAR")
        return StorageItemInDB(**result) if result else None

    @staticmethod
    async def set_tags_and_color(
        item_id: str, tags: Optional[List[str]], color: Optional[str], owner_id: str
    ) -> Optional[StorageItemInDB]:
        item = await StorageService.get_item(item_id, owner_id)
        if not item:
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp hoặc thư mục")

        update_set = {"updated_at": datetime.now(timezone.utc)}
        if tags is not None:
            update_set["tags"] = tags
        if color is not None:
            update_set["color"] = color

        result = await storage_repository.find_one_and_update(
            {"_id": item_id, "owner_id": owner_id}, {"$set": update_set}
        )
        from src.services.activity import ActivityService

        if tags is not None:
            await ActivityService.log_activity(item_id, owner_id, "TAG")
        if color is not None:
            await ActivityService.log_activity(item_id, owner_id, "COLOR")
        return StorageItemInDB(**result) if result else None

    get_trashed_items = staticmethod(get_trashed_items)
    restore_from_trash = staticmethod(restore_from_trash)
    empty_trash = staticmethod(empty_trash)

    get_quota_analytics = staticmethod(get_quota_analytics)

    share_internal = staticmethod(share_internal)
    revoke_internal_share = staticmethod(revoke_internal_share)
    get_shared_with_me_items = staticmethod(get_shared_with_me_items)
