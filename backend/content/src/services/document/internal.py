import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from loguru import logger

from src.clients.knowledge import knowledge_client
from src.core.infrastructure.configuration import settings
from src.core.dependency import SystemRole
from src.repositories.document import DocumentRepository
from src.repositories.document_ingestion_outbox import document_ingestion_outbox
from src.schemas.document import (
    DocumentIndexingClaimRequest,
    DocumentIndexingClaimResponse,
    DocumentIndexingLeaseRequest,
    DocumentIndexingProgressUpdate,
)
from src.services.document.base import can_read_full


INDEX_SOURCE_SNAPSHOT_FIELDS = frozenset(
    {
        "file_url",
        "revision",
        "content_hash",
        "source_hash",
        "content_sha256",
        "title",
        "author",
        "author_name",
        "visibility",
        "owner_id",
        "creator_id",
        "shared_with",
        "ai_enabled",
        "source",
        "content_source",
        "source_name",
        "source_url",
        "source_type",
        "authority",
        "content_format",
        "version",
        "source_version",
        "publisher",
        "publisher_name",
        "book_title",
        "collector_version",
        "project_id",
        "artifact_type",
        "artifact_id",
        "artifact_version_id",
        "module",
        "status",
        "content_type",
        "conflict_key",
        "claim_value",
        "ocr_language",
        "artifact_metadata",
    }
)


def serialize_internal(value: Any):
    if isinstance(value, dict):
        return {key: serialize_internal(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_internal(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def indexing_status_from_report(index_report: dict) -> str:
    """Do not label a partial index as complete when any source material was skipped."""
    incomplete_sections = (
        "failed_chunks",
        "quarantined_chunks",
        "unprocessed_blocks",
        "index_cleanup_pending",
    )
    if any(index_report.get(section) for section in incomplete_sections):
        return "degraded"
    return "indexed"


async def internal_document_data(req: dict):
    operation = str(req.get("operation", ""))
    query = DocumentRepository.normalize_query(req.get("query") or {})
    projection = req.get("projection")
    documents = DocumentRepository
    if operation == "find_one":
        document = await documents.find_one(query, projection)
        return {"data": serialize_internal(document)}
    if operation == "find_many":
        limit = min(max(int(req.get("limit") or 100), 1), 200)
        cursor = documents.find(query, projection)
        sort = req.get("sort") or []
        if sort:
            cursor = cursor.sort([(str(field), int(direction)) for field, direction in sort])
        rows = await cursor.limit(limit).to_list(length=limit)
        return {"data": serialize_internal(rows)}
    if operation == "update_one":
        result = await documents.update_one(
            query, req.get("update") or {}, upsert=bool(req.get("upsert", False))
        )
        return {
            "data": {
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "upserted_id": str(result.upserted_id) if result.upserted_id else None,
            }
        }
    if operation == "taxonomy":
        rows = await documents.aggregate(
            [
                {
                    "$match": {
                        "status": "published",
                        "visibility": "public",
                        "is_deleted": {"$ne": True},
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "categories": {"$addToSet": "$category"},
                        "tags": {"$push": "$tags"},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "categories": 1,
                        "tags": {
                            "$reduce": {
                                "input": "$tags",
                                "initialValue": [],
                                "in": {"$setUnion": ["$$value", {"$ifNull": ["$$this", []]}]},
                            }
                        },
                    }
                },
            ]
        ).to_list(length=1)
        data = rows[0] if rows else {"categories": [], "tags": []}
        data["categories"] = sorted(value for value in data.get("categories", []) if value)
        data["tags"] = sorted(value for value in data.get("tags", []) if value)
        return {"data": data}
    raise HTTPException(status_code=422, detail="Thao tác dữ liệu nội bộ không hợp lệ")


async def get_internal_document(req: dict):
    document_id = str(req.get("document_id", ""))
    user_id = str(req.get("user_id", ""))
    edit = bool(req.get("edit", False))
    is_admin = bool(req.get("is_admin", False))
    document = await DocumentRepository.find_one(
        {"_id": document_id, "is_deleted": {"$ne": True}}
    )
    if document and edit and not is_admin:
        can_edit = user_id == document.get("creator_id")
        if not can_edit:
            document = None
    elif document and not edit:
        from types import SimpleNamespace

        current_user = SimpleNamespace(
            id=user_id,
            system_role=SystemRole.ADMIN if is_admin else SystemRole.USER,
        )
        if not await can_read_full(document, current_user):
            document = None
    if not document:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy tài liệu hoặc thiếu quyền truy cập"
        )
    return {"data": serialize_internal(document)}


async def get_internal_document_stats(req: dict):
    documents = DocumentRepository
    source_ids = [str(value) for value in req.get("source_ids", [])]
    source_names = [str(value) for value in req.get("source_names", [])]
    total_documents = await documents.count_documents({"is_deleted": {"$ne": True}})
    result = {"total_documents": total_documents}
    if source_ids or source_names:
        collected_filter = {"$or": []}
        if source_ids:
            collected_filter["$or"].append({"creator_id": {"$in": source_ids}})
        if source_names:
            collected_filter["$or"].append({"source_name": {"$in": source_names}})
        result["total_assets"] = await documents.count_documents(
            {"$or": [{"file_url": {"$type": "string"}}, {"pdf_url": {"$type": "string"}}]}
        )
        result["total_collected"] = await documents.count_documents(collected_filter)
        recent = (
            await documents.find(collected_filter, {"created_at": 1})
            .sort("created_at", -1)
            .limit(1)
            .to_list(length=1)
        )
        result["last_run"] = recent[0].get("created_at") if recent else None
    return {"data": result}


async def exchange_internal_document(req: dict):
    action = str(req.get("action", ""))
    document_id = str(req.get("document_id", ""))
    documents = DocumentRepository
    if action == "get_document":
        document = await documents.find_one({"_id": document_id, "is_deleted": {"$ne": True}})
        if not document:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
        document["_id"] = str(document["_id"])
        document.pop("password", None)
        document.pop("access_password_hash", None)
        return {"data": document}
    if action == "get_accessible_document":
        user_id = str(req.get("user_id", ""))
        is_admin = bool(req.get("is_admin", False))
        edit = bool(req.get("edit", False))
        allow_deleted = bool(req.get("allow_deleted", False))
        access = [{"creator_id": user_id}]
        if not edit:
            access.append({"visibility": "public", "status": "published"})
        query = {"_id": document_id}
        if not allow_deleted:
            query["is_deleted"] = {"$ne": True}
        if not is_admin:
            query["$or"] = access
        document = await documents.find_one(query)
        if not document:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy tài liệu hoặc thiếu quyền truy cập"
            )
        document["_id"] = str(document["_id"])
        document.pop("password", None)
        document.pop("access_password_hash", None)
        return {"data": document}
    if action == "get_accessible_documents":
        document_ids = list(dict.fromkeys(
            str(value).strip()
            for value in req.get("document_ids", [])
            if str(value).strip()
        ))
        if not document_ids or len(document_ids) > 100:
            raise HTTPException(status_code=422, detail="Danh sách tài liệu không hợp lệ")
        query = {
            "_id": {"$in": document_ids},
            "is_deleted": {"$ne": True},
            "is_indexed": {"$ne": False},
            "ai_enabled": {"$ne": False},
            "index_status": {"$ne": "REVOKE_PENDING"},
        }
        if not bool(req.get("is_admin", False)):
            user_id = str(req.get("user_id") or "")
            query["$or"] = [
                {"creator_id": user_id},
                {
                    "status": "published",
                    "$or": [
                        {"visibility": "public"},
                        {"visibility": {"$exists": False}},
                    ],
                },
            ]
        rows = await documents.find(
            query, {"_id": 1, "active_index_generation": 1}
        ).to_list(length=len(document_ids))
        return {
            "data": {
                "documents": [
                    {
                        "_id": str(row["_id"]),
                        "active_index_generation": row.get("active_index_generation"),
                    }
                    for row in rows
                    if row.get("_id")
                ]
            }
        }
    if action == "update_indexing_progress":
        try:
            progress = DocumentIndexingProgressUpdate.model_validate(
                {
                    key: req[key]
                    for key in (
                        "indexing_attempt_id",
                        "indexing_lease_token",
                        "phase",
                        "processed_pages",
                        "total_pages",
                        "unprocessed_pages",
                    )
                    if key in req
                }
            )
        except Exception as error:
            raise HTTPException(
                status_code=422, detail="Tiến độ xử lý tài liệu không hợp lệ"
            ) from error
        result = await documents.update_one(
            {
                "_id": document_id,
                "is_deleted": {"$ne": True},
                "ai_enabled": {"$ne": False},
                "index_status": {"$ne": "REVOKE_PENDING"},
                "indexing_attempt_id": progress.indexing_attempt_id,
                "indexing_lease_token": progress.indexing_lease_token,
                "indexing_lease_until": {"$gt": datetime.now(timezone.utc)},
                "indexing_status": "indexing",
            },
            {
                "$set": {
                    "indexing_progress": progress.model_dump(
                        exclude={"indexing_lease_token"}
                    ),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return {"data": {"updated": result.matched_count == 1}}
    if action == "update_index":
        index_report = dict(req.get("index_report") or {})
        indexing_status = indexing_status_from_report(index_report)
        indexing_attempt_id = str(req.get("indexing_attempt_id") or "")
        indexing_lease_token = str(req.get("indexing_lease_token") or "")
        index_generation = str(req.get("index_generation") or "")
        source_snapshot = req.get("source_snapshot")
        if not indexing_attempt_id or not indexing_lease_token:
            raise HTTPException(status_code=422, detail="Thiếu mã lượt lập chỉ mục")
        if (
            not isinstance(source_snapshot, dict)
            or set(source_snapshot) != INDEX_SOURCE_SNAPSHOT_FIELDS
        ):
            raise HTTPException(status_code=422, detail="Ảnh chụp nguồn lập chỉ mục không hợp lệ")
        if len(index_generation) != 64 or any(
            character not in "0123456789abcdef" for character in index_generation
        ):
            raise HTTPException(status_code=422, detail="Mã thế hệ chỉ mục không hợp lệ")
        query = {
            "_id": document_id,
            "is_deleted": {"$ne": True},
            "ai_enabled": {"$ne": False},
            "index_status": {"$ne": "REVOKE_PENDING"},
        }
        query["indexing_attempt_id"] = indexing_attempt_id
        query["indexing_lease_token"] = indexing_lease_token
        query["indexing_status"] = "indexing"
        query["indexing_lease_until"] = {"$gt": datetime.now(timezone.utc)}
        query.update(source_snapshot)
        result = await documents.update_one(
            query,
            {
                "$set": {
                    "indexing_status": indexing_status,
                    "active_index_generation": index_generation,
                    "is_indexed": True,
                    "chunks_count": int(req.get("indexed_chunks", 0)),
                    "indexed_chunks": int(req.get("indexed_chunks", 0)),
                    "extraction_method": str(req.get("extraction_method", "")),
                    "index_report": index_report,
                    "extracted_text": str(req.get("extracted_text") or "")[:200000],
                    "extracted_text_truncated": bool(req.get("extracted_text_truncated", False)),
                    "updated_at": datetime.now(timezone.utc),
                },
                "$unset": {"indexing_progress": ""},
            },
        )
        return {
            "data": {
                "updated": result.matched_count == 1,
                "indexing_status": indexing_status,
            }
        }
    if action == "mark_indexing":
        try:
            claim = DocumentIndexingClaimRequest.model_validate(
                {
                    key: req[key]
                    for key in (
                        "indexing_attempt_id",
                        "indexing_lease_token",
                        "dispatch_event_id",
                    )
                    if key in req
                }
            )
        except Exception as error:
            raise HTTPException(
                status_code=422, detail="Yêu cầu nhận lượt lập chỉ mục không hợp lệ"
            ) from error
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=settings.DOCUMENT_INDEXING_LEASE_SECONDS)
        query = {
            "_id": document_id,
            "is_deleted": {"$ne": True},
            "ai_enabled": {"$ne": False},
            "index_status": {"$ne": "REVOKE_PENDING"},
            "$or": [
                {"indexing_status": {"$in": [None, "not_started", "queued", "failed"]}},
                {
                    "indexing_status": "degraded",
                    "$or": [
                        {"index_report.failed_chunks": {"$exists": True, "$ne": []}},
                        {"index_report.unprocessed_blocks": {"$exists": True, "$ne": []}},
                        {"index_report.index_cleanup_pending": {"$exists": True, "$ne": []}},
                    ],
                },
                {
                    "indexing_status": "indexing",
                    "$or": [
                        {"indexing_lease_until": {"$exists": False}},
                        {"indexing_lease_until": None},
                        {"indexing_lease_until": {"$lte": now}},
                    ],
                },
            ],
        }
        if claim.dispatch_event_id:
            query["index_dispatch_event_id"] = claim.dispatch_event_id
        updated = await documents.find_one_and_update(
            query,
            {
                "$set": {
                    "indexing_status": "indexing",
                    "indexing_attempt_id": claim.indexing_attempt_id,
                    "indexing_lease_token": claim.indexing_lease_token,
                    "indexing_lease_until": lease_until,
                    "updated_at": now,
                },
                "$unset": {"indexing_error": "", "indexing_progress": ""},
            },
        )
        if updated:
            response = DocumentIndexingClaimResponse(
                status="claimed", updated=True, lease_until=lease_until
            )
            return {"data": response.model_dump(mode="json")}

        current = await documents.find_one(
            {"_id": document_id, "is_deleted": {"$ne": True}}
        )
        current_lease_until = current.get("indexing_lease_until") if current else None
        if (
            isinstance(current_lease_until, datetime)
            and current_lease_until.tzinfo is None
        ):
            current_lease_until = current_lease_until.replace(tzinfo=timezone.utc)
        if (
            not current
            or (
                claim.dispatch_event_id
                and current.get("index_dispatch_event_id") != claim.dispatch_event_id
            )
        ):
            status = "superseded"
        elif current.get("indexing_status") in {"indexed", "degraded"}:
            status = "already_indexed"
        elif (
            current.get("indexing_status") == "indexing"
            and isinstance(current_lease_until, datetime)
            and current_lease_until > now
        ):
            status = "busy"
        else:
            status = "not_claimable"
        response = DocumentIndexingClaimResponse(
            status=status,
            updated=False,
            lease_until=current_lease_until,
        )
        return {"data": response.model_dump(mode="json")}
    if action == "renew_indexing_lease":
        try:
            lease = DocumentIndexingLeaseRequest.model_validate(
                {
                    key: req[key]
                    for key in ("indexing_attempt_id", "indexing_lease_token")
                    if key in req
                }
            )
        except Exception as error:
            raise HTTPException(
                status_code=422, detail="Yêu cầu gia hạn lượt lập chỉ mục không hợp lệ"
            ) from error
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=settings.DOCUMENT_INDEXING_LEASE_SECONDS)
        result = await documents.update_one(
            {
                "_id": document_id,
                "is_deleted": {"$ne": True},
                "ai_enabled": {"$ne": False},
                "index_status": {"$ne": "REVOKE_PENDING"},
                "indexing_status": "indexing",
                "indexing_attempt_id": lease.indexing_attempt_id,
                "indexing_lease_token": lease.indexing_lease_token,
                "indexing_lease_until": {"$gt": now},
            },
            {"$set": {"indexing_lease_until": lease_until, "updated_at": now}},
        )
        return {
            "data": {
                "updated": result.matched_count == 1,
                "lease_until": lease_until.isoformat(),
            }
        }
    if action == "mark_index_failed":
        indexing_attempt_id = str(req.get("indexing_attempt_id") or "")
        indexing_lease_token = str(req.get("indexing_lease_token") or "")
        if not indexing_attempt_id or not indexing_lease_token:
            raise HTTPException(status_code=422, detail="Thiếu mã lượt lập chỉ mục")
        query = {
            "_id": document_id,
            "is_deleted": {"$ne": True},
            "ai_enabled": {"$ne": False},
            "index_status": {"$ne": "REVOKE_PENDING"},
            "indexing_status": "indexing",
            "indexing_lease_until": {"$gt": datetime.now(timezone.utc)},
        }
        query["indexing_attempt_id"] = indexing_attempt_id
        query["indexing_lease_token"] = indexing_lease_token
        result = await documents.update_one(
            query,
            {
                "$set": {
                    "indexing_status": "failed",
                    "indexing_error": str(req.get("error_code") or "unknown"),
                    "updated_at": datetime.now(timezone.utc),
                },
                "$unset": {
                    "indexing_attempt_id": "",
                    "indexing_lease_token": "",
                    "indexing_lease_until": "",
                    "indexing_progress": "",
                },
            },
        )
        return {"data": {"updated": result.matched_count == 1}}
    if action == "complete_indexing":
        indexing_attempt_id = str(req.get("indexing_attempt_id") or "")
        indexing_lease_token = str(req.get("indexing_lease_token") or "")
        if not indexing_attempt_id or not indexing_lease_token:
            raise HTTPException(status_code=422, detail="Thiếu mã lượt lập chỉ mục")
        now = datetime.now(timezone.utc)
        result = await documents.update_one(
            {
                "_id": document_id,
                "is_deleted": {"$ne": True},
                "ai_enabled": {"$ne": False},
                "index_status": {"$ne": "REVOKE_PENDING"},
                "indexing_attempt_id": indexing_attempt_id,
                "indexing_lease_token": indexing_lease_token,
                "indexing_lease_until": {"$gt": now},
                "indexing_status": {"$in": ["indexed", "degraded"]},
            },
            {
                "$unset": {
                    "indexing_attempt_id": "",
                    "indexing_lease_token": "",
                    "indexing_lease_until": "",
                    "indexing_progress": "",
                }
            },
        )
        return {"data": {"updated": result.matched_count == 1}}
    if action == "mark_unindexed":
        result = await documents.update_one(
            {"_id": document_id, "is_deleted": {"$ne": True}},
            {
                "$set": {
                    "chunks_count": 0,
                    "indexed_chunks": 0,
                    "is_indexed": False,
                    "indexing_status": "not_started",
                    "updated_at": datetime.now(timezone.utc),
                },
                "$unset": {
                    "indexing_attempt_id": "",
                    "indexing_lease_token": "",
                    "indexing_lease_until": "",
                    "indexing_progress": "",
                },
            },
        )
        return {"data": {"updated": result.matched_count == 1}}
    if action == "mark_source_obsolete":
        result = await documents.update_one(
            {"_id": document_id, "is_deleted": {"$ne": True}},
            {
                "$set": {
                    "source_is_current": False,
                    "collection_status": "obsolete",
                    "obsolete_reason": str(req.get("reason") or ""),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return {"data": {"updated": result.matched_count == 1}}
    if action == "upsert_collected":
        payload = dict(req.get("document") or {})
        identity = payload.get("source_url") or payload.get("file_url")
        if not identity:
            raise HTTPException(status_code=422, detail="Tài liệu thu thập thiếu định danh nguồn")
        now = datetime.now(timezone.utc)
        payload.setdefault("_id", str(uuid.uuid4()))
        payload.setdefault("created_at", now)
        payload["updated_at"] = now
        identity_field = "source_url" if payload.get("source_url") else "file_url"
        identity_query = {identity_field: identity}
        content_hash = str(payload.get("content_hash") or "")
        if content_hash:
            exact_query = {**identity_query, "content_hash": content_hash}
            row = await documents.find_one(exact_query)
            if not row:
                previous = await documents.find_one(
                    identity_query, sort=[("source_revision", -1), ("created_at", -1)]
                )
                payload["source_revision"] = (
                    int(previous.get("source_revision", 1)) + 1 if previous else 1
                )
                payload["previous_version_id"] = str(previous["_id"]) if previous else None
                payload["source_is_current"] = True
                if previous:
                    payload["slug"] = (
                        f"{str(payload.get('slug') or 'tai-lieu')[:130]}-{content_hash[:10]}"
                    )
                inserted = await documents.insert_one_if_unique(payload)
                if inserted:
                    row = payload
                else:
                    row = await documents.find_one(exact_query)
                    if not row:
                        raise RuntimeError("Không thể xác định tài liệu sau xung đột định danh")
                if previous and str(row["_id"]) == str(payload["_id"]):
                    await documents.update_one(
                        {"_id": previous["_id"]},
                        {
                            "$set": {
                                "source_is_current": False,
                                "superseded_by_document_id": str(row["_id"]),
                                "collection_status": "superseded",
                                "updated_at": now,
                            }
                        },
                    )
        else:
            row = await documents.find_one_and_update(
                identity_query,
                {"$setOnInsert": payload},
                upsert=True,
            )
        collected_doc_id = str(row["_id"])
        superseded_document_id = str(row.get("previous_version_id") or "")
        indexing_status = str(row.get("indexing_status") or "not_started")
        if payload.get("file_url") and indexing_status not in {"indexed", "degraded"}:
            await documents.update_one(
                {"_id": row["_id"]},
                {
                    "$set": {
                        "indexing_status": "queued",
                        "is_indexed": False,
                        "updated_at": now,
                    },
                    "$unset": {"indexing_error": "", "index_dispatch_event_id": ""},
                },
            )
            await document_ingestion_outbox.enqueue(
                {**row, "_id": collected_doc_id},
                user_id="",
                superseded_document_id=superseded_document_id,
                force_new=indexing_status == "failed",
            )
            indexing_status = "queued"
        return {"data": {"document_id": collected_doc_id, "indexing_status": indexing_status}}
    if action == "update_collected":
        result = await documents.update_one(
            {"_id": document_id},
            {"$set": {**dict(req.get("values") or {}), "updated_at": datetime.now(timezone.utc)}},
        )
        return {"data": {"updated": result.modified_count == 1}}
    if action == "auto_save_draft":
        result = await documents.update_one(
            {"_id": document_id, "is_deleted": {"$ne": True}},
            {
                "$set": {
                    "draft_content": dict(req.get("content") or {}),
                    "toc": list(req.get("toc") or []),
                    "reading_time_minutes": max(1, int(req.get("reading_time_minutes", 1))),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return {"data": {"updated": result.matched_count == 1}}
    if action == "submit_for_review":
        result = await documents.update_one(
            {
                "_id": document_id,
                "status": {"$nin": ["pending_review", "published"]},
                "is_deleted": {"$ne": True},
            },
            {"$set": {"status": "pending_review", "updated_at": datetime.now(timezone.utc)}},
        )
        return {"data": {"updated": result.modified_count == 1}}
    if action == "global_find_replace":
        current = await documents.find_one(
            {"_id": document_id, "is_deleted": {"$ne": True}}, {"_id": 1}
        )
        if not current:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
        now = datetime.now(timezone.utc)
        await DocumentRepository.insert_version(
            {
                "_id": str(uuid.uuid4()),
                "document_id": document_id,
                "creator_id": str(req.get("creator_id", "")),
                "note": "Tìm và thay thế",
                "snapshot": dict(req.get("snapshot") or {}),
                "created_at": now,
            }
        )
        values = dict(req.get("update") or {})
        values["updated_at"] = now
        await documents.update_one({"_id": document_id}, {"$set": values})
        return {"data": {"updated": True}}
    if action == "get_versions":
        version_ids = [str(value) for value in req.get("version_ids", [])]
        identifiers = DocumentRepository.identifiers(version_ids)
        rows = await (
            DocumentRepository.find_versions(
                {"document_id": document_id, "_id": {"$in": identifiers}}
            )
            .limit(len(version_ids))
            .to_list(length=len(version_ids))
        )
        for row in rows:
            row["_id"] = str(row["_id"])
        return {"data": rows}
    if action == "search_documents":
        text = str(req.get("query", "")).strip()
        search_filter = {"status": "published", "is_deleted": {"$ne": True}}
        if text:
            search_filter["$or"] = [
                {"title": {"$regex": text, "$options": "i"}},
                {"description": {"$regex": text, "$options": "i"}},
                {"tags": {"$regex": text, "$options": "i"}},
            ]
        rows = await documents.find(search_filter).limit(3).to_list(length=3)
        if not rows and text:
            rows = (
                await documents.find({"status": "published", "is_deleted": {"$ne": True}})
                .limit(3)
                .to_list(length=3)
            )
        result = []
        for row in rows:
            result.append(
                {
                    "id": str(row["_id"]),
                    "title": row.get("title", ""),
                    "slug": row.get("slug", ""),
                    "summary": row.get("summary") or row.get("description") or "",
                }
            )
        return {"data": result}
    raise HTTPException(status_code=422, detail="Tác vụ trao đổi tài liệu không hợp lệ")
