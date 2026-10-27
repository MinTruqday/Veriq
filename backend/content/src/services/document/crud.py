import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from loguru import logger

from src.clients.knowledge import knowledge_client
from src.clients.notification import notification_client
from src.repositories.cache import DocumentCacheRepository
from src.repositories.document import DocumentRepository
from src.repositories.document_ingestion_outbox import (
    DocumentIngestionSourceChanged,
    document_ingestion_outbox,
)
from src.schemas.document import DocumentContentUpdate, DocumentCreate, DocumentInDB, DocumentStatus
from src.services.document.base import can_read_full, is_admin, pwd_context, serialize_document


class DocumentCrudService:
    @staticmethod
    async def create_document(doc_in: DocumentCreate, current_user):
        slug = doc_in.slug
        if not slug:
            normalized = (
                unicodedata.normalize("NFKD", doc_in.title)
                .encode("ascii", "ignore")
                .decode("ascii")
                .lower()
            )
            slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "tai-lieu"
        existing_slug = await DocumentRepository.find_one({"slug": slug})
        if existing_slug:
            slug = f"{slug}-{uuid.uuid4().hex[:8]}"

        doc_dict = doc_in.model_dump(exclude={"password"})
        doc_dict["slug"] = slug
        if not doc_dict.get("publisher_name"):
            doc_dict["publisher_name"] = current_user.full_name

        doc_doc = DocumentInDB(**doc_dict, creator_id=str(current_user.id))
        doc_data = doc_doc.model_dump(by_alias=True)
        doc_data["views"] = 0
        doc_data["is_deleted"] = False
        doc_data["created_at"] = datetime.now(timezone.utc)
        doc_data["updated_at"] = datetime.now(timezone.utc)
        if doc_data.get("file_url"):
            doc_data["indexing_status"] = "queued"
            doc_data["is_indexed"] = False

        if doc_in.password:
            doc_data["access_password_hash"] = pwd_context.hash(doc_in.password)
            doc_data["is_password_protected"] = True

        await DocumentRepository.insert_one(doc_data)

        if doc_data.get("file_url"):
            try:
                await document_ingestion_outbox.enqueue(
                    doc_data, user_id=str(current_user.id)
                )
            except Exception:
                logger.exception("Create ingest outbox persistence failed")

        return serialize_document(doc_data)

    @staticmethod
    async def get_my_documents(current_user, q: str = None, cursor: str = None, limit: int = 50):
        user_id = str(current_user.id)
        query = {"creator_id": user_id, "is_deleted": {"$ne": True}}
        if q:
            escaped_query = re.escape(q)
            query["$and"] = [
                {
                    "$or": [
                        {"title": {"$regex": escaped_query, "$options": "i"}},
                        {"description": {"$regex": escaped_query, "$options": "i"}},
                    ]
                }
            ]
        if cursor:
            query["_id"] = {"$lt": cursor}

        cursor_db = DocumentRepository.find(query).sort("_id", -1).limit(limit)
        documents = await cursor_db.to_list(length=limit)
        return [
            {
                "_id": str(document["_id"]),
                "title": document.get("title", ""),
                "slug": document.get("slug", ""),
                "status": document.get("status", "draft"),
                "content_format": document.get("content_format", "veriq"),
                "cover_url": document.get("cover_url"),
                "file_url": document.get("file_url"),
                "artifact_metadata": document.get("artifact_metadata"),
                "is_indexed": document.get("is_indexed", False),
                "indexing_status": document.get("indexing_status", "not_started"),
                "indexing_progress": document.get("indexing_progress"),
                "indexing_error": document.get("indexing_error"),
                "index_report": document.get(
                    "index_report", {"failed_chunks": [], "quarantined_chunks": []}
                ),
                "extraction_method": document.get("extraction_method"),
                "extracted_text_available": bool(document.get("extracted_text")),
                "extracted_text_truncated": bool(document.get("extracted_text_truncated")),
                "chunks_count": document.get("chunks_count", 0),
                "views": document.get("views", 0),
                "created_at": (
                    document["created_at"].isoformat()
                    if isinstance(document.get("created_at"), datetime)
                    else document.get("created_at")
                ),
                "updated_at": (
                    document["updated_at"].isoformat()
                    if isinstance(document.get("updated_at"), datetime)
                    else document.get("updated_at")
                ),
            }
            for document in documents
        ]

    @staticmethod
    async def update_document_content(
        document_id: str, update_data: DocumentContentUpdate, current_user
    ):
        document = await DocumentRepository.find_one({"_id": document_id})
        if not document:
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )

        user_id = str(current_user.id)
        is_creator = document.get("creator_id") == user_id

        if not is_creator and not is_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Bạn không có quyền chỉnh sửa nội dung tài liệu này"
            )

        if update_data.expected_version:
            stored_version = document.get("updated_at")
            if (
                stored_version
                and str(stored_version).split("+")[0]
                != str(update_data.expected_version).split("+")[0]
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Xung đột phiên bản: Tài liệu đã được cập nhật bởi một phiên làm việc khác",
                )

        if document.get("content"):
            await DocumentRepository.insert_revision(
                {
                    "document_id": document_id,
                    "creator_id": user_id,
                    "content": document.get("content"),
                    "content_format": document.get("content_format"),
                    "created_at": datetime.now(timezone.utc),
                    "note": "Auto-saved revision before update",
                }
            )

        new_content = update_data.content
        word_count = len(new_content.split())
        reading_time_min = max(1, word_count // 200)

        update_dict = {
            "content": new_content,
            "content_format": update_data.content_format,
            "reading_time_minutes": reading_time_min,
            "word_count": word_count,
            "updated_at": datetime.now(timezone.utc),
            "last_modified_by": user_id,
        }

        await DocumentRepository.update_one({"_id": document_id}, {"$set": update_dict})

        try:
            await notification_client.send(
                target_user_id=user_id,
                title="Document successfully updated",
                body="The specified document content has been successfully synchronized and updated",
                notification_type="DOCUMENT_UPDATE",
            )
        except Exception:
            logger.exception("Document update notification dispatch failed")

        await DocumentCacheRepository.invalidate_document(document_id, document.get("slug"))

        updated = await DocumentRepository.find_one({"_id": document_id})
        return serialize_document(updated)

    @staticmethod
    async def update_document(document_id: str, doc_update, current_user) -> dict:
        document = await DocumentRepository.find_one({"_id": document_id})
        if not document:
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )

        user_id = str(current_user.id)
        is_creator = document.get("creator_id") == user_id

        if not is_creator and not is_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Bạn không có quyền cập nhật thông tin tài liệu này"
            )

        update_data = (
            doc_update.model_dump(exclude_unset=True)
            if hasattr(doc_update, "model_dump")
            else dict(doc_update)
        )
        expected_version = update_data.pop("expected_version", None)
        if expected_version:
            stored_version = document.get("updated_at")
            if (
                stored_version
                and str(stored_version).split("+")[0] != str(expected_version).split("+")[0]
            ):
                raise HTTPException(
                    status_code=409, detail="Không thể chỉnh sửa do đã có phiên bản mới hơn"
                )

        if "slug" in update_data and update_data["slug"] != document.get("slug"):
            existing = await DocumentRepository.find_one({"slug": update_data["slug"]})
            if existing:
                raise HTTPException(status_code=400, detail="Đường dẫn định tuyến đã được sử dụng")

        update_data["updated_at"] = datetime.now(timezone.utc)

        if "password" in update_data:
            pwd = update_data.pop("password")
            if pwd:
                update_data["access_password_hash"] = pwd_context.hash(pwd)
                update_data["is_password_protected"] = True
            else:
                update_data["access_password_hash"] = None
                update_data["is_password_protected"] = False

        await DocumentRepository.update_one({"_id": document_id}, {"$set": update_data})

        await DocumentCacheRepository.invalidate_document(document_id, document.get("slug"))

        if update_data.get("file_url"):
            await DocumentRepository.update_one(
                {"_id": document_id},
                {
                    "$set": {"indexing_status": "queued", "is_indexed": False},
                    "$unset": {"indexing_error": "", "index_dispatch_event_id": ""},
                },
            )
            try:
                await document_ingestion_outbox.enqueue(
                    {**document, **update_data, "_id": document_id},
                    user_id=str(document.get("creator_id") or ""),
                    force_new=True,
                )
            except Exception:
                await DocumentRepository.update_one(
                    {"_id": document_id},
                    {
                        "$set": {
                            "indexing_status": "queued",
                            "indexing_error": "outbox_persistence_pending",
                        }
                    },
                )
                logger.exception(f"Ingest outbox persistence failed for document_id={document_id}")

        updated = await DocumentRepository.find_one({"_id": document_id})
        return serialize_document(updated)

    @staticmethod
    async def retry_document_indexing(document_id: str, current_user):
        document = await DocumentRepository.find_one(
            {"_id": document_id, "is_deleted": {"$ne": True}}
        )
        if not document:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
        if document.get("creator_id") != str(current_user.id) and not is_admin(current_user):
            raise HTTPException(status_code=403, detail="Không có quyền lập chỉ mục tài liệu")
        if not document.get("file_url"):
            raise HTTPException(status_code=422, detail="Tài liệu chưa có tệp nguồn")
        if (
            document.get("ai_enabled") is False
            or document.get("index_status") == "REVOKE_PENDING"
            or document.get("source_is_current") is False
        ):
            raise HTTPException(
                status_code=409,
                detail="Tài liệu hiện không được phép lập chỉ mục AI",
            )
        try:
            await document_ingestion_outbox.enqueue(
                document,
                user_id=str(document.get("creator_id") or ""),
                superseded_document_id=str(document.get("previous_version_id") or ""),
                force_new=True,
                expected_source_snapshot=document,
            )
        except DocumentIngestionSourceChanged:
            raise HTTPException(
                status_code=409,
                detail="Tài liệu hoặc quyền truy cập đã thay đổi; hãy tải lại trước khi lập chỉ mục",
            )
        except Exception:
            logger.exception(
                "Document reindex dispatch failed document_id={}", document_id
            )
            raise HTTPException(
                status_code=503, detail="Không thể đưa tài liệu vào hàng đợi lập chỉ mục"
            )
        return serialize_document(await DocumentRepository.find_one({"_id": document_id}))

    @staticmethod
    async def list_documents(
        limit: int, cursor: str, q: str, sort_by: str, category: str = None, tag: str = None
    ):
        query = {
            "status": DocumentStatus.PUBLISHED,
            "is_deleted": {"$ne": True},
            "visibility": "public",
        }
        if q:
            query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
            ]
        if category:
            query["category"] = category
        if tag:
            query["tags"] = tag

        sort_mapping = {"latest": ("created_at", -1), "views": ("views", -1)}
        sort_field, sort_dir = sort_mapping.get(sort_by, ("created_at", -1))

        if cursor:
            if sort_field == "created_at":
                query["_id"] = {"$lt": cursor}

        cursor_db = DocumentRepository.find(query).sort(sort_field, sort_dir).limit(limit)
        documents = await cursor_db.to_list(length=limit)
        return [serialize_document(d) for d in documents]

    @staticmethod
    async def get_document_by_id(document_id: str, current_user, password: str = None):
        user_id = str(current_user.id) if current_user else None
        document = await DocumentRepository.find_one({"_id": document_id})
        if not document:
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )

        is_creator = document.get("creator_id") == user_id

        if document.get("is_deleted") is True and not is_creator and not is_admin(current_user):
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )

        if (
            not is_creator
            and document.get("status") != DocumentStatus.PUBLISHED
            and not is_admin(current_user)
        ):
            raise HTTPException(
                status_code=403, detail="Tài liệu hiện đang ở trạng thái nháp và chưa được công bố"
            )

        if document.get("is_password_protected") and not is_creator:
            if not password:
                return {
                    "_id": str(document["_id"]),
                    "title": document.get("title"),
                    "is_password_protected": True,
                }
            attempts = await DocumentCacheRepository.password_attempts(document_id, user_id)
            if attempts >= 5:
                raise HTTPException(
                    status_code=429,
                    detail="Truy cập bị tạm khóa do vi phạm giới hạn thử mật khẩu tài liệu",
                )
            if not pwd_context.verify(password, document.get("access_password_hash")):
                await DocumentCacheRepository.record_password_failure(document_id, user_id)
                raise HTTPException(
                    status_code=403,
                    detail="Thông tin xác thực không chính xác hoặc không khớp với hồ sơ bảo mật",
                )
            await DocumentCacheRepository.clear_password_failures(document_id, user_id)

        can_view_full_content = await can_read_full(document, current_user)
        if not can_view_full_content and document.get("status") == DocumentStatus.PUBLISHED:
            preview_limit = max(
                0,
                int(document.get("preview_pages", 5) or 0),
            )
            document["content"] = (document.get("content") or "")[
                : preview_limit * 1000
            ]

        serialized = serialize_document(document)
        serialized["can_read_full"] = can_view_full_content
        return serialized

    @staticmethod
    async def get_document_by_slug(slug: str, current_user=None):
        document = await DocumentRepository.find_one(
            {
                "slug": slug,
                "status": DocumentStatus.PUBLISHED,
                "is_deleted": {"$ne": True},
                "visibility": "public",
            }
        )
        if not document:
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )
        return await DocumentCrudService.get_document_by_id(str(document["_id"]), current_user)

    @staticmethod
    async def soft_delete_document(document_id: str, current_user) -> dict:
        document = await DocumentRepository.find_one(
            {"_id": document_id, "creator_id": str(current_user.id), "is_deleted": {"$ne": True}}
        )
        if not document:
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )
        await knowledge_client.delete_document(
            document_id, str(current_user.id), is_admin(current_user)
        )
        res = await DocumentRepository.update_one(
            {"_id": document_id, "creator_id": str(current_user.id), "is_deleted": {"$ne": True}},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}},
        )
        if res.modified_count == 0:
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )
        logger.info("Document moved to recycle bin")
        return {"message": "Tài liệu đã được di chuyển vào thùng rác hệ thống"}

    @staticmethod
    async def restore_document(document_id: str, current_user) -> dict:
        res = await DocumentRepository.update_one(
            {"_id": document_id, "creator_id": str(current_user.id), "is_deleted": True},
            {"$set": {"is_deleted": False, "deleted_at": None}},
        )
        if res.modified_count == 0:
            raise HTTPException(
                status_code=404, detail="Hệ thống không tìm thấy tài liệu yêu cầu trong thùng rác"
            )
        restored = await DocumentRepository.find_one(
            {"_id": document_id, "creator_id": str(current_user.id)}
        )
        if restored and restored.get("file_url"):
            await DocumentCrudService.retry_document_indexing(document_id, current_user)
        logger.info("Document restored from recycle bin")
        return {"message": "Tài liệu đã được khôi phục hoàn tất từ thùng rác"}

    @staticmethod
    async def get_trash(current_user) -> list:
        docs = await (
            DocumentRepository.find({"creator_id": str(current_user.id), "is_deleted": True})
            .sort("deleted_at", -1)
            .to_list(length=100)
        )
        return [
            {
                "_id": str(b["_id"]),
                "title": b.get("title", ""),
                "deleted_at": (
                    b["deleted_at"].isoformat()
                    if isinstance(b.get("deleted_at"), datetime)
                    else b.get("deleted_at")
                ),
            }
            for b in docs
        ]

    @staticmethod
    async def toggle_star_document(document_id: str, current_user):
        document = await DocumentRepository.find_one(
            {"_id": document_id, "creator_id": str(current_user.id)}
        )
        if not document:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy tài liệu hoặc thiếu quyền cập nhật"
            )
        starred = not bool(document.get("is_starred", False))
        await DocumentRepository.update_one(
            {"_id": document_id},
            {"$set": {"is_starred": starred, "updated_at": datetime.now(timezone.utc)}},
        )
        return {"starred": starred}

    @staticmethod
    async def set_document_password(document_id: str, password: str, current_user) -> dict:
        doc = await DocumentRepository.find_one(
            {"_id": document_id, "creator_id": str(current_user.id)}
        )
        if not doc:
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )
        hashed = pwd_context.hash(password)
        await DocumentRepository.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "access_password_hash": hashed,
                    "is_password_protected": True,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        logger.info("Document password protection enabled")
        return {"message": "Thiết lập mật khẩu bảo vệ tài liệu hoàn tất"}

    @staticmethod
    async def get_document_preview(slug: str) -> dict:
        doc = await DocumentRepository.find_one(
            {
                "slug": slug,
                "status": DocumentStatus.PUBLISHED,
                "is_deleted": {"$ne": True},
                "visibility": "public",
            }
        )
        if not doc:
            raise HTTPException(
                status_code=404, detail="Hệ thống không thể tìm thấy tài liệu theo yêu cầu của bạn"
            )
        limit = doc.get("preview_pages", 5)
        raw_content = doc.get("content", "")
        preview_content = ""
        try:
            parsed = json.loads(raw_content)
            if "blocks" in parsed:
                parsed["blocks"] = parsed["blocks"][
                    : limit * 5
                ]
                preview_content = json.dumps(parsed)
            else:
                preview_content = raw_content[
                    : limit * 1000
                ]
        except (TypeError, ValueError, json.JSONDecodeError):
            preview_content = raw_content[
                : limit * 1000
            ]

        return {
            "title": doc.get("title"),
            "description": doc.get("description"),
            "cover_url": doc.get("cover_url"),
            "creator_id": doc.get("creator_id"),
            "preview_content": preview_content,
        }
