import hashlib
import re
from dataclasses import dataclass

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.storage import storage_client
from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.repositories.requirement_document import requirement_document_repository
from src.repositories.common import common_repository
from src.clients.project_knowledge import index_artifact, remove_artifact
from src.modules.requirements.services.requirement_import import (
    extract_file_content,
    source_document_text,
    supported_requirement_formats,
)
from src.modules.requirements.services.requirement_workflow import serialized_content




@dataclass(frozen=True)
class RequirementDocumentResult:
    data: dict
    status: str = 'SUCCESS'
    degraded_mode: str | None = None


async def validate_document_recipients(project_id, shared_with):
    recipients = sorted({str(user_id).strip() for user_id in shared_with if str(user_id).strip()})
    for user_id in recipients:
        membership = await common_repository.find_membership(
            project_id, user_id, status="ACTIVE", projection={"_id": 1}
        )
        if not membership:
            raise HTTPException(status_code=422, detail={"code": "DOCUMENT_RECIPIENT_NOT_IN_PROJECT"})
    return recipients


async def require_document_access(document, user, permission):
    await get_project(document["project_id"], user, permission)
    if user.is_system_admin or document.get("created_by") == user.id:
        return document
    visibility = document.get("visibility", "private")
    if visibility == "project" or (
        visibility == "shared" and user.id in set(document.get("shared_with", []))
    ):
        return document
    raise HTTPException(status_code=403, detail={"code": "DOCUMENT_ACCESS_DENIED"})


async def require_document_owner(document, user):
    await get_project(document["project_id"], user, 'requirement_document.read')
    if user.is_system_admin or document.get("created_by") == user.id:
        return document
    raise HTTPException(status_code=403, detail={"code": "DOCUMENT_ACCESS_MANAGEMENT_DENIED"})


async def create_requirement_document_record(project_id, payload, user):
    await get_project(project_id, user, 'requirement_document.upload')
    shared_with = await validate_document_recipients(project_id, payload.shared_with)
    content = serialized_content(payload.content)
    normalized_content = payload.content if payload.format in ("openapi", "postman") else source_document_text(payload.content)
    normalized = serialized_content(normalized_content)
    if len(content.encode("utf-8")) > 26214400:
        raise HTTPException(status_code=413, detail={"code": 'IMPORT_TOO_LARGE'})
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing = await requirement_document_repository.find_by_hash(project_id, content_hash, user.id)
    if existing:
        return await require_document_access(existing, user, 'requirement_document.read')
    timestamp = now()
    document = {
        "_id": new_id('RDOC'),
        "project_id": project_id,
        "filename": payload.filename,
        "format": payload.format,
        "content_hash": content_hash,
        "raw_source": {
            "storage": 'embedded',
            "content": payload.content,
            "sha256": content_hash,
            "size": len(content.encode("utf-8")),
        },
        "normalized_content": normalized_content,
        "normalized_content_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "source_version": '1',
        "source_type": 'API_SPEC' if payload.format in ("openapi", "postman") else payload.source_type,
        "authority": 'PROJECT_REFERENCE',
        "approval_status": 'DRAFT',
        "status": 'READY',
        "index_status": "NOT_REQUESTED",
        "visibility": payload.visibility,
        "shared_with": shared_with,
        "ai_enabled": payload.ai_enabled,
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await requirement_document_repository.insert(document)
    except DuplicateKeyError:
        existing = await requirement_document_repository.find_by_hash(
            project_id, content_hash, user.id
        )
        if existing:
            return await require_document_access(existing, user, 'requirement_document.read')
        raise
    await audit(
        user.id,
        'requirement_document_created',
        'RequirementDocument',
        document["_id"],
        project_id,
        {"content_hash": content_hash, "format": payload.format},
    )
    if document.get("ai_enabled"):
        indexed = await index_requirement_document(document)
        if not indexed:
            await requirement_document_repository.update(
                document["_id"],
                project_id,
                {"ai_enabled": False, "updated_at": now()},
            )
            raise HTTPException(status_code=503, detail={"code": "KNOWLEDGE_INDEX_FAILED"})
        document = await requirement_document_repository.find(document["_id"], project_id)
    return document


async def store_raw_requirement_source(project_id, document_id, filename, content_type, data):
    return await storage_client.store_requirement_source(
        project_id, document_id, filename, content_type, data
    )


async def read_raw_requirement_source(document):
    source = document.get("raw_source") or {}
    if source.get("storage") == 'embedded':
        content = serialized_content(source.get("content"))
        return content.encode("utf-8")
    object_key = source.get("object_key")
    if not object_key:
        raise HTTPException(
            status_code=409,
            detail={"code": 'RAW_SOURCE_UNAVAILABLE'},
        )
    return await storage_client.read_requirement_source(
        document["project_id"], document["_id"], object_key
    )


async def index_requirement_document(document):
    indexed = await index_artifact(
        document["project_id"],
        'requirement_document',
        document["_id"],
        document["_id"],
        document.get("title") or document.get("filename") or document["_id"],
        serialized_content(document.get("normalized_content") or ""),
        document.get("status", 'READY'),
        document.get("authority", 'PROJECT_REFERENCE'),
        document.get("source_version", '1'),
        module=document.get("module") or "",
        component=document.get("component"),
        product_area=document.get("product_area"),
        release_id=document.get("release_id"),
        external_source_id=document.get("external_source_id"),
        approval_status=document.get("approval_status", 'DRAFT'),
        owner_id=document.get("owner_id"),
        created_by=document.get("created_by"),
        visibility=document.get("visibility") or "private",
        shared_with=document.get("shared_with") or [],
        approved_by=document.get("approved_by"),
        approved_at=document.get("approved_at"),
        effective_from=document.get("effective_from"),
        tags=document.get("tags") or [],
    )
    await requirement_document_repository.set_index_result(
        document["_id"],
        document["project_id"],
        'INDEXED'
        if indexed
        else 'FAILED',
        now(),
    )
    return indexed


async def upload_requirement_document_record(
    project_id,
    format,
    filename,
    content_type,
    data,
    user,
    visibility="private",
    shared_with=None,
    ai_enabled=False,
    source_type="REFERENCE",
):
    if format not in supported_requirement_formats():
        raise HTTPException(status_code=422, detail={"code": 'UNSUPPORTED_IMPORT_FORMAT'})
    if not data:
        raise HTTPException(status_code=422, detail={"code": 'EMPTY_IMPORT'})
    if len(data) > 26214400:
        raise HTTPException(status_code=413, detail={"code": 'IMPORT_TOO_LARGE'})
    await get_project(project_id, user, 'requirement_document.upload')
    shared_with = await validate_document_recipients(project_id, shared_with or [])
    resolved_filename = filename or f"{'requirements'}.{format}"
    content_hash = hashlib.sha256(data).hexdigest()
    existing = await requirement_document_repository.find_by_hash(project_id, content_hash, user.id)
    if existing:
        return RequirementDocumentResult(await require_document_access(existing, user, 'requirement_document.read'))
    document_id = new_id('RDOC')
    source = await store_raw_requirement_source(
        project_id,
        document_id,
        resolved_filename,
        content_type,
        data,
    )
    timestamp = now()
    document = {
        "_id": document_id,
        "project_id": project_id,
        "filename": resolved_filename,
        "format": format,
        "content_hash": source["sha256"],
        "raw_source": source,
        "normalized_content": None,
        "source_version": '1',
        "source_type": 'API_SPEC' if format in ("openapi", "postman") else source_type,
        "authority": 'PROJECT_REFERENCE',
        "approval_status": 'DRAFT',
        "status": 'UPLOADED',
        "index_status": "NOT_REQUESTED",
        "visibility": visibility,
        "shared_with": shared_with,
        "ai_enabled": ai_enabled,
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await requirement_document_repository.insert(document)
    except DuplicateKeyError:
        existing = await requirement_document_repository.find_by_hash(
            project_id, content_hash, user.id
        )
        if existing:
            return RequirementDocumentResult(await require_document_access(existing, user, 'requirement_document.read'))
        raise
    await audit(
        user.id,
        'requirement_document_uploaded',
        'RequirementDocument',
        document_id,
        project_id,
        {
            "content_hash": source["sha256"],
            "object_key": source["object_key"],
            "format": format,
        },
    )
    try:
        content = extract_file_content(data, format)
    except Exception as error:
        await requirement_document_repository.update(
            document_id,
            project_id,
            {
                "status": 'PARSE_FAILED',
                "parse_error_type": type(error).__name__,
                "updated_at": now(),
            },
            increment_revision=True,
        )
        document = await requirement_document_repository.find(document_id, project_id)
        await audit(
            user.id,
            'requirement_document_parse_failed',
            'RequirementDocument',
            document_id,
            project_id,
            {"error_type": type(error).__name__},
        )
        return RequirementDocumentResult(
            document, 'DEGRADED', 'PARSER_FAILED'
        )
    normalized = serialized_content(content)
    await requirement_document_repository.update(
        document_id,
        project_id,
        {
            "normalized_content": content,
            "normalized_content_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "status": 'READY',
            "updated_at": now(),
        },
        increment_revision=True,
    )
    document = await requirement_document_repository.find(document_id, project_id)
    if document.get("ai_enabled"):
        await index_requirement_document(document)
        document = await requirement_document_repository.find(document_id, project_id)
    return RequirementDocumentResult(document)


async def list_requirement_document_records(project_id, status, query_text, limit, user):
    await get_project(project_id, user, 'requirement_document.read')
    query = {"project_id": project_id}
    if status:
        query["status"] = status.upper()
    if query_text:
        query["filename"] = {"$regex": re.escape(query_text), "$options": "i"}
    documents = await requirement_document_repository.list(query, limit)
    return [
        document
        for document in documents
        if user.is_system_admin
        or document.get("created_by") == user.id
        or document.get("visibility", "private") == "project"
        or (
            document.get("visibility") == "shared"
            and user.id in set(document.get("shared_with", []))
        )
    ]


async def get_requirement_document_record(document_id, user, permission=None):
    document = await get_project_entity(
        'requirement_documents',
        document_id,
        user,
        permission or 'requirement_document.read',
    )
    return await require_document_access(
        document, user, permission or 'requirement_document.read'
    )


async def update_requirement_document_record(document_id, payload, user):
    document = await get_requirement_document_record(
        document_id, user, 'knowledge.manage'
    )
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    resulting = {**document, **changes}
    if resulting.get("approval_status") == 'APPROVED' and (
        not resulting.get("approved_by") or not resulting.get("approved_at")
    ):
        raise HTTPException(
            status_code=422,
            detail={"code": 'APPROVAL_PROVENANCE_REQUIRED'},
        )
    if changes.get("release_id"):
        if not await requirement_document_repository.release_exists(
            document["project_id"], changes["release_id"]
        ):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_RELEASE'})
    if document.get("ai_enabled"):
        changes["index_status"] = 'PENDING'
    updated = await requirement_document_repository.update_with_revision(
        document_id,
        document["project_id"],
        payload.expected_revision,
        {**changes, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    indexed = True
    if updated.get("ai_enabled"):
        indexed = await index_requirement_document(updated)
    updated = await requirement_document_repository.find(
        document_id, document["project_id"]
    )
    await audit(
        user.id,
        'requirement_document_metadata_updated',
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"fields": sorted(changes)},
    )
    return RequirementDocumentResult(
        updated,
        'SUCCESS' if indexed else 'DEGRADED',
        None if indexed else 'DEGRADED_VECTOR',
    )


async def update_requirement_document_access(document_id, payload, user):
    document = await get_project_entity(
        'requirement_documents',
        document_id,
        user,
        'requirement_document.read',
    )
    await require_document_owner(document, user)
    shared_with = await validate_document_recipients(
        document["project_id"], payload.shared_with
    )
    updated = await requirement_document_repository.update_with_revision(
        document_id,
        document["project_id"],
        payload.expected_revision,
        {
            "visibility": payload.visibility,
            "shared_with": shared_with,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    if updated.get("ai_enabled"):
        await index_requirement_document(updated)
    await audit(
        user.id,
        "requirement_document.access_updated",
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"visibility": payload.visibility, "shared_with": shared_with},
    )
    return RequirementDocumentResult(updated)


async def update_requirement_document_ai_read(document_id, payload, user):
    document = await get_project_entity(
        'requirement_documents',
        document_id,
        user,
        'requirement_document.read',
    )
    await require_document_owner(document, user)
    if document.get("ai_enabled") and not payload.ai_enabled:
        raise HTTPException(status_code=409, detail={"code": "AI_READ_ACCESS_LOCKED"})
    if payload.ai_enabled and not document.get("normalized_content"):
        raise HTTPException(status_code=409, detail={"code": "DOCUMENT_PARSE_REQUIRED"})
    updated = await requirement_document_repository.update_with_revision(
        document_id,
        document["project_id"],
        payload.expected_revision,
        {"ai_enabled": payload.ai_enabled, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    if payload.ai_enabled:
        indexed = await index_requirement_document(updated)
        if not indexed:
            if not document.get("ai_enabled"):
                await requirement_document_repository.update(
                    document_id,
                    document["project_id"],
                    {"ai_enabled": False, "updated_at": now()},
                )
            raise HTTPException(status_code=503, detail={"code": "KNOWLEDGE_INDEX_FAILED"})
    else:
        await remove_artifact(updated["project_id"], updated["_id"])
        await requirement_document_repository.set_index_result(
            updated["_id"], updated["project_id"], "NOT_REQUESTED", now()
        )
    await audit(
        user.id,
        "requirement_document.ai_read_updated",
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"ai_enabled": payload.ai_enabled},
    )
    return RequirementDocumentResult(
        await requirement_document_repository.find(document_id, document["project_id"])
    )


async def reindex_requirement_document_record(document_id, user):
    document = await get_requirement_document_record(
        document_id, user, 'knowledge.manage'
    )
    if document.get("status") == 'ARCHIVED':
        raise HTTPException(
            status_code=409,
            detail={"code": 'DOCUMENT_ARCHIVED'},
        )
    if not document.get("ai_enabled"):
        return RequirementDocumentResult(document)
    indexed = await index_requirement_document(document)
    await requirement_document_repository.update(
        document_id,
        document["project_id"],
        {"updated_at": now()},
        increment_revision=True,
    )
    updated = await requirement_document_repository.find(
        document_id, document["project_id"]
    )
    await audit(
        user.id,
        'requirement_document_reindexed',
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"indexed": indexed},
    )
    return RequirementDocumentResult(
        updated,
        'SUCCESS' if indexed else 'DEGRADED',
        None if indexed else 'DEGRADED_VECTOR',
    )


async def archive_requirement_document_record(document_id, payload, user):
    document = await get_requirement_document_record(
        document_id, user, 'requirement_document.archive'
    )
    if document.get("status") == 'ARCHIVED':
        return document
    timestamp = now()
    updated = await requirement_document_repository.update_with_revision(
        document_id,
        document["project_id"],
        payload.expected_revision,
        {
            "status_before_archive": document.get("status", 'READY'),
            "status": 'ARCHIVED',
            "archived_by": user.id,
            "archived_at": timestamp,
            "archive_reason": payload.reason,
            "updated_at": timestamp,
        },
    )
    if not updated:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT'},
        )
    if updated.get("ai_enabled"):
        await remove_artifact(updated["project_id"], updated["_id"])
    await audit(
        user.id,
        'requirement_document_archived',
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"reason": payload.reason},
    )
    return updated


async def restore_requirement_document_record(document_id, payload, user):
    document = await get_requirement_document_record(
        document_id, user, 'requirement_document.restore'
    )
    if document.get("status") != 'ARCHIVED':
        return document
    timestamp = now()
    updated = await requirement_document_repository.update_with_revision(
        document_id,
        document["project_id"],
        payload.expected_revision,
        {
            "status": document.get("status_before_archive", 'READY'),
            "restored_by": user.id,
            "restored_at": timestamp,
            "restore_reason": payload.reason,
            "updated_at": timestamp,
        },
        status='ARCHIVED',
    )
    if not updated:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT'},
        )
    await audit(
        user.id,
        'requirement_document_restored',
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"reason": payload.reason},
    )
    return updated


async def retry_requirement_document_parse_record(document_id, payload, user):
    document = await get_requirement_document_record(
        document_id, user, 'requirement_document.extract'
    )
    if document.get("status") == 'READY':
        return RequirementDocumentResult(document)
    if document.get("status") != 'PARSE_FAILED':
        raise HTTPException(
            status_code=409,
            detail={"code": 'DOCUMENT_NOT_RETRYABLE', "status": document.get("status")},
        )
    claimed = await requirement_document_repository.claim_status(
        document_id,
        document["project_id"],
        'PARSE_FAILED',
        payload.expected_revision,
        'PARSING',
        now(),
    )
    if claimed.matched_count != 1:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    try:
        data = await read_raw_requirement_source(document)
        content = extract_file_content(data, document["format"])
    except Exception as error:
        await requirement_document_repository.transition_status(
            document_id,
            document["project_id"],
            'PARSING',
            {
                "status": 'PARSE_FAILED',
                "parse_error_type": type(error).__name__,
                "updated_at": now(),
            },
        )
        failed = await requirement_document_repository.find(
            document_id, document["project_id"]
        )
        await audit(
            user.id,
            'requirement_document_parse_retry_failed',
            'RequirementDocument',
            document_id,
            document["project_id"],
            {"error_type": type(error).__name__},
        )
        return RequirementDocumentResult(
            failed, 'DEGRADED', 'PARSER_FAILED'
        )
    normalized = serialized_content(content)
    updated = await requirement_document_repository.transition_status(
        document_id,
        document["project_id"],
        'PARSING',
        {
            "normalized_content": content,
            "normalized_content_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "status": 'READY',
            "parse_error_type": None,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'PARSE_RETRY_CONFLICT'})
    await audit(
        user.id,
        'requirement_document_parse_retry_succeeded',
        'RequirementDocument',
        document_id,
        document["project_id"],
    )
    return RequirementDocumentResult(updated)
