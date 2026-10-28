import asyncio
import base64
import hashlib
import hmac
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.ai_automation import (
    cancel_document_ingestion_runs,
    cancel_pending_document_ingestion,
    emit_document_ingested,
)
from src.clients.document_conversion import (
    clear_requirement_conversion_checkpoints,
    convert_requirement_source,
)
from src.clients.project_knowledge import index_artifact, remove_artifact
from src.clients.storage import storage_client
from src.core.auth import ai_automation_context
from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.core.configuration import settings
from src.core.database import database
from src.modules.requirements.services.requirement_import import (
    extract_file_content,
    source_document_text,
    supported_requirement_formats,
)
from src.modules.requirements.services.requirement_workflow import serialized_content
from src.repositories.ai_automation_access import ai_automation_access_repository
from src.repositories.common import common_repository
from src.repositories.requirement_document import requirement_document_repository
from src.repositories.requirement_source_block import requirement_source_block_repository
from src.repositories.requirement import requirement_repository
from src.repositories.test_design import test_design_repository

logger = logging.getLogger(__name__)
REQUIREMENT_DOCUMENT_INDEX_CONTRACT_VERSION = 2


@dataclass(frozen=True)
class RequirementDocumentResult:
    data: dict
    status: str = 'SUCCESS'
    degraded_mode: str | None = None


@dataclass(frozen=True)
class ParseRequirementDocumentCommand:
    expected_revision: int


async def queue_document_ingestion(document, user):
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            await audit(
                user.id,
                "requirement_document_ai_ingestion_queued",
                "RequirementDocument",
                document["_id"],
                document["project_id"],
                {"source_version": document.get("source_version"), "revision": document.get("revision")},
                session=session,
            )
            await emit_document_ingested(document, user, session=session)


async def recover_document_ingestion(document, user):
    if document.get("index_status") == "REVOKE_PENDING":
        try:
            source_drained = await ai_automation_access_repository.revoke_and_wait(
                f"source:{document['_id']}"
            )
            if not source_drained:
                return False
            await cancel_pending_document_ingestion(
                document["_id"], "AI_READ_PERMISSION_REVOKED"
            )
            await cancel_document_ingestion_runs(document["_id"])
        except Exception:
            logger.exception(
                "Failed to retry document automation cancellation document=%s",
                document["_id"],
            )
            return False
        removed = await remove_artifact(document["project_id"], document["_id"])
        if not removed:
            return False
        result = await requirement_document_repository.set_index_result(
            document["_id"],
            document["project_id"],
            "NOT_REQUESTED",
            now(),
            expected_revision=document.get("revision"),
        )
        if result.matched_count:
            return True
        latest = await requirement_document_repository.find(
            document["_id"], document["project_id"]
        )
        if (
            latest
            and latest.get("ai_enabled")
            and latest.get("status") != "ARCHIVED"
        ):
            return await index_requirement_document(latest)
        return False
    if document.get("status") != "READY" or document.get("ai_enabled") is not True:
        return True
    if (
        document.get("index_status") not in {"INDEXED", "DEGRADED"}
        or document.get("index_contract_version")
        != REQUIREMENT_DOCUMENT_INDEX_CONTRACT_VERSION
    ):
        indexed = await index_requirement_document(document)
        document = await requirement_document_repository.find(
            document["_id"], document["project_id"]
        )
        if not indexed or not document or not document.get("ai_enabled"):
            return False
    if document.get("index_status") in {"INDEXED", "DEGRADED"}:
        source_opened = await ai_automation_access_repository.allow_source(
            f"source:{document['_id']}"
        )
        if not source_opened:
            return False
        await queue_document_ingestion(document, user)
        return True
    return False


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
    if not can_read_requirement_document(document, user):
        raise HTTPException(status_code=403, detail={"code": "DOCUMENT_ACCESS_DENIED"})
    return document


def can_read_requirement_document(document, user):
    if user.is_system_admin or document.get("created_by") == user.id:
        return True
    automation = ai_automation_context.get()
    if (
        automation
        and automation.get("principal_id") == user.id
        and automation.get("initiator_id") == document.get("created_by")
        and document.get("ai_enabled") is True
    ):
        return True
    visibility = document.get("visibility", "private")
    if visibility == "project" or (
        visibility == "shared" and user.id in set(document.get("shared_with", []))
    ):
        return True
    return False


async def require_document_owner(document, user):
    await get_project(document["project_id"], user, 'requirement_document.read')
    if user.is_system_admin or document.get("created_by") == user.id:
        return document
    raise HTTPException(status_code=403, detail={"code": "DOCUMENT_ACCESS_MANAGEMENT_DENIED"})


async def find_reusable_document_duplicate(
    project_id,
    content_hash,
    format,
    visibility,
    shared_with,
    ai_enabled,
    source_type,
    user,
    ocr_language=None,
):
    document = await requirement_document_repository.find_reusable_duplicate(
        project_id,
        content_hash,
        format,
        visibility,
        shared_with,
        ai_enabled,
        source_type,
        user.id,
        ocr_language,
    )
    if not document:
        return None
    return await require_document_access(document, user, "requirement_document.read")


async def reuse_ready_requirement_document(document, user):
    if document.get("status") == "ARCHIVED":
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_SOURCE_ARCHIVED"},
        )
    if document.get("status") != "READY":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DUPLICATE_SOURCE_NOT_READY",
                "status": document.get("status"),
            },
        )
    if not await recover_document_ingestion(document, user):
        raise HTTPException(
            status_code=503, detail={"code": "DUPLICATE_SOURCE_RECOVERY_PENDING"}
        )
    latest = await requirement_document_repository.find(
        document["_id"], document["project_id"]
    )
    if not latest or latest.get("status") != "READY":
        raise HTTPException(
            status_code=503, detail={"code": "DUPLICATE_SOURCE_RECOVERY_PENDING"}
        )
    return latest


async def reuse_uploaded_requirement_document(document, user):
    status = document.get("status")
    if status == "READY":
        return await reuse_ready_requirement_document(document, user)
    if status == "ARCHIVED":
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_SOURCE_ARCHIVED"},
        )
    if status not in {"UPLOADED", "PARSING", "PARSE_FAILED"}:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_SOURCE_NOT_REUSABLE", "status": status},
        )
    return await require_document_access(document, user, "requirement_document.read")


def ensure_duplicate_settings_match(
    document, *, format, visibility, shared_with, ai_enabled, source_type, ocr_language=None
):
    matches = (
        document.get("format") == format
        and document.get("visibility", "private") == visibility
        and sorted(document.get("shared_with") or []) == sorted(shared_with or [])
        and document.get("ai_enabled", False) == ai_enabled
        and document.get("source_type") == source_type
        and document.get("ocr_language") == ocr_language
    )
    if not matches:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_SOURCE_SETTINGS_CONFLICT"},
        )
    return document


async def resolve_source_successor(
    project_id,
    supersedes_document_id,
    user,
    *,
    content_hash,
    format,
    visibility,
    shared_with,
    ai_enabled,
    source_type,
    ocr_language=None,
):
    if not supersedes_document_id:
        return None
    previous = await get_requirement_document_record(
        supersedes_document_id, user, "requirement_document.read"
    )
    if previous.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail={"code": "SOURCE_VERSION_PARENT_NOT_FOUND"})
    await require_document_owner(previous, user)
    if previous.get("status") == "ARCHIVED":
        raise HTTPException(status_code=409, detail={"code": "SOURCE_VERSION_PARENT_ARCHIVED"})
    ensure_duplicate_settings_match(
        previous,
        format=format,
        visibility=visibility,
        shared_with=shared_with,
        ai_enabled=ai_enabled,
        source_type=source_type,
        ocr_language=ocr_language,
    )
    series_id = str(previous.get("source_series_id") or previous["_id"])
    latest = await requirement_document_repository.latest_in_source_series(project_id, series_id)
    if latest and latest.get("_id") != previous.get("_id"):
        raise HTTPException(
            status_code=409,
            detail={"code": "SOURCE_VERSION_PARENT_STALE", "latest_document_id": latest["_id"]},
        )
    if previous.get("content_hash") == content_hash:
        raise HTTPException(status_code=409, detail={"code": "SOURCE_VERSION_CONTENT_UNCHANGED"})
    sequence = int(previous.get("source_version_sequence") or 1) + 1
    return {
        "source_series_id": series_id,
        "source_version_sequence": sequence,
        "source_version": str(sequence),
        "previous_source_version_id": str(previous["_id"]),
    }


async def raise_source_version_insert_conflict(project_id, lineage):
    if lineage:
        latest = await requirement_document_repository.latest_in_source_series(
            project_id, lineage["source_series_id"]
        )
        if latest and int(latest.get("source_version_sequence") or 1) >= int(
            lineage["source_version_sequence"]
        ):
            code = "SOURCE_VERSION_PARENT_STALE"
            latest_id = latest.get("_id")
        else:
            code = "SOURCE_VERSION_CONTENT_ALREADY_EXISTS"
            latest_id = None
        raise HTTPException(
            status_code=409,
            detail={
                "code": code,
                "latest_document_id": latest_id,
            },
        )


def normalize_ocr_language(source_format, ocr_language):
    language = str(ocr_language or "").strip()
    if not language:
        return None
    if source_format != "pdf":
        raise HTTPException(
            status_code=422,
            detail={"code": "OCR_LANGUAGE_REQUIRES_PDF"},
        )
    return language


def requirement_document_deduplication_key(
    project_id,
    content_hash,
    format,
    visibility,
    shared_with,
    ai_enabled,
    source_type,
    ocr_language,
    created_by,
):
    format_value = getattr(format, "value", format)
    source_type_value = getattr(source_type, "value", source_type)
    scope = {
        "project_id": str(project_id),
        "content_hash": str(content_hash),
        "format": str(format_value),
        "visibility": str(visibility),
        "shared_with": sorted(set(map(str, shared_with or [])))
        if visibility == "shared"
        else [],
        "ai_enabled": bool(ai_enabled),
        "source_type": str(source_type_value),
        "ocr_language": str(ocr_language or ""),
        "owner_id": str(created_by) if visibility == "private" else None,
    }
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


async def create_requirement_document_record(project_id, payload, user):
    ocr_language = normalize_ocr_language(payload.format, payload.ocr_language)
    await get_project(project_id, user, 'requirement_document.upload')
    shared_with = await validate_document_recipients(project_id, payload.shared_with)
    content = serialized_content(payload.content)
    normalized_content = payload.content if payload.format in ("openapi", "postman") else source_document_text(payload.content)
    normalized = serialized_content(normalized_content)
    if len(content.encode("utf-8")) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail={"code": 'IMPORT_TOO_LARGE'})
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source_type = 'API_SPEC' if payload.format in ("openapi", "postman") else payload.source_type
    deduplication_key = requirement_document_deduplication_key(
        project_id,
        content_hash,
        payload.format,
        payload.visibility,
        shared_with,
        payload.ai_enabled,
        source_type,
        ocr_language,
        user.id,
    )
    lineage = await resolve_source_successor(
        project_id,
        payload.supersedes_document_id,
        user,
        content_hash=content_hash,
        format=payload.format,
        visibility=payload.visibility,
        shared_with=shared_with,
        ai_enabled=payload.ai_enabled,
        source_type=source_type,
        ocr_language=ocr_language,
    )
    scoped_duplicate = await requirement_document_repository.find_by_deduplication_key(
        project_id, deduplication_key
    )
    if scoped_duplicate:
        if lineage and not (
            scoped_duplicate.get("source_series_id") == lineage["source_series_id"]
            and scoped_duplicate.get("source_version_sequence")
            == lineage["source_version_sequence"]
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "SOURCE_VERSION_CONTENT_ALREADY_EXISTS"},
            )
        scoped_duplicate = await require_document_access(
            scoped_duplicate, user, "requirement_document.read"
        )
        return await reuse_ready_requirement_document(scoped_duplicate, user)
    existing = await requirement_document_repository.find_by_hash(project_id, content_hash, user.id)
    if existing:
        ensure_duplicate_settings_match(
            existing,
            format=payload.format,
            visibility=payload.visibility,
            shared_with=shared_with,
            ai_enabled=payload.ai_enabled,
            source_type=source_type,
            ocr_language=ocr_language,
        )
        if lineage and existing.get("source_series_id") == lineage["source_series_id"] and existing.get("source_version_sequence") == lineage["source_version_sequence"]:
            existing = await require_document_access(existing, user, 'requirement_document.read')
            return await reuse_ready_requirement_document(existing, user)
        if lineage:
            raise HTTPException(status_code=409, detail={"code": "SOURCE_VERSION_CONTENT_ALREADY_EXISTS"})
        existing = await require_document_access(existing, user, 'requirement_document.read')
        return await reuse_ready_requirement_document(existing, user)
    existing = await find_reusable_document_duplicate(
        project_id,
        content_hash,
        payload.format,
        payload.visibility,
        shared_with,
        payload.ai_enabled,
        source_type,
        user,
        ocr_language,
    )
    if existing:
        if lineage and not (
            existing.get("source_series_id") == lineage["source_series_id"]
            and existing.get("source_version_sequence") == lineage["source_version_sequence"]
        ):
            raise HTTPException(status_code=409, detail={"code": "SOURCE_VERSION_CONTENT_ALREADY_EXISTS"})
        return await reuse_ready_requirement_document(existing, user)
    timestamp = now()
    document_id = new_id('RDOC')
    document = {
        "_id": document_id,
        "project_id": project_id,
        "filename": payload.filename,
        "format": payload.format,
        "content_hash": content_hash,
        "deduplication_key": deduplication_key,
        "raw_source": {
            "storage": 'embedded',
            "content": payload.content,
            "sha256": content_hash,
            "size": len(content.encode("utf-8")),
        },
        "normalized_content": normalized_content,
        "normalized_content_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "parse_report": {"unprocessed_blocks": []},
        "source_version": lineage["source_version"] if lineage else '1',
        "source_series_id": lineage["source_series_id"] if lineage else document_id,
        "source_version_sequence": lineage["source_version_sequence"] if lineage else 1,
        "previous_source_version_id": lineage["previous_source_version_id"] if lineage else None,
        "source_type": source_type,
        "ocr_language": ocr_language,
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
        if lineage:
            await raise_source_version_insert_conflict(project_id, lineage)
        scoped_duplicate = await requirement_document_repository.find_by_deduplication_key(
            project_id, deduplication_key
        )
        if scoped_duplicate:
            scoped_duplicate = await require_document_access(
                scoped_duplicate, user, "requirement_document.read"
            )
            return await reuse_ready_requirement_document(scoped_duplicate, user)
        existing = await requirement_document_repository.find_by_hash(
            project_id, content_hash, user.id
        )
        if existing:
            ensure_duplicate_settings_match(
                existing,
                format=payload.format,
                visibility=payload.visibility,
                shared_with=shared_with,
                ai_enabled=payload.ai_enabled,
                source_type=source_type,
                ocr_language=ocr_language,
            )
            existing = await require_document_access(existing, user, 'requirement_document.read')
            if not await recover_document_ingestion(existing, user):
                raise HTTPException(status_code=503, detail={"code": "KNOWLEDGE_INDEX_FAILED"})
            return existing
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
            raise HTTPException(status_code=503, detail={"code": "KNOWLEDGE_INDEX_FAILED"})
        document = await requirement_document_repository.find(document["_id"], project_id)
        await queue_document_ingestion(document, user)
    return document


async def store_raw_requirement_source(project_id, document_id, filename, content_type, data):
    return await storage_client.store_requirement_source(
        project_id, document_id, filename, content_type, data
    )


async def remove_unclaimed_raw_requirement_source(project_id, document_id, source):
    object_key = (source or {}).get("object_key")
    if not object_key:
        return
    try:
        document = await requirement_document_repository.find(document_id, project_id)
        claimed_object_key = ((document or {}).get("raw_source") or {}).get("object_key")
        if claimed_object_key == object_key:
            return
        await storage_client.delete_requirement_source(
            project_id, document_id, object_key
        )
    except Exception:
        logger.exception(
            "Unable to confirm or remove unclaimed requirement source; "
            "project_id=%s document_id=%s",
            project_id,
            document_id,
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


async def parse_requirement_source(data, source_format, filename, ocr_language=None):
    if source_format in {"pdf", "docx"}:
        parsed = await convert_requirement_source(
            data, filename, ocr_language=ocr_language
        )
        return parsed.markdown, {
            "source_structure": [block.model_dump() for block in parsed.structure],
            "parse_report": {
                "parser": parsed.parser,
                "parser_version": parsed.parser_version,
                "page_count": parsed.page_count,
                "ocr_enabled": parsed.ocr_enabled,
                "ocr_language": parsed.ocr_language,
                "unprocessed_blocks": parsed.unprocessed_blocks,
                "extraction_warnings": parsed.extraction_warnings,
                "structure_available": bool(parsed.structure),
            },
        }
    content = await asyncio.to_thread(extract_file_content, data, source_format)
    return content, {
        "source_structure": [],
        "parse_report": {
            "parser": "veriq_source_reader",
            "page_count": None,
            "structure_available": False,
            "unprocessed_blocks": [],
        },
    }


async def read_and_parse_requirement_source(document, attempt_id):
    data = await read_raw_requirement_source(document)
    if document["format"] == "pdf":
        parsed = await convert_requirement_source(
            data,
            document["filename"],
            document_id=document["_id"],
            project_id=document["project_id"],
            owner_id=str(document.get("created_by") or ""),
            ocr_language=document.get("ocr_language"),
        )
        expected_source_hash = hashlib.sha256(data).hexdigest()
        if parsed.source_hash != expected_source_hash:
            try:
                await clear_requirement_conversion_checkpoints(
                    document["_id"],
                    document["project_id"],
                    str(document.get("created_by") or ""),
                    expected_source_hash,
                )
            except Exception as error:
                logger.warning(
                    "Mismatched requirement checkpoints retained for TTL document_id=%s error=%s",
                    document["_id"],
                    type(error).__name__,
                )
            raise RuntimeError("requirement_source_hash_mismatch")
        current = await requirement_document_repository.find(
            document["_id"], document["project_id"]
        )
        same_source = bool(
            current and current.get("content_hash") == parsed.source_hash
        )
        current_attempt_active = bool(
            current
            and current.get("status") == "PARSING"
            and current.get("parse_attempt_id")
            and current.get("content_hash") == parsed.source_hash
        )
        if not current or current.get("status") != "PARSING" or not same_source:
            if not current_attempt_active:
                try:
                    await clear_requirement_conversion_checkpoints(
                        document["_id"],
                        document["project_id"],
                        str(document.get("created_by") or ""),
                        parsed.source_hash,
                    )
                except Exception as error:
                    logger.warning(
                        "Obsolete requirement checkpoints retained for TTL document_id=%s error=%s",
                        document["_id"],
                        type(error).__name__,
                    )
            raise RuntimeError("requirement_parse_attempt_superseded")
        if current.get("parse_attempt_id") != attempt_id:
            raise RuntimeError("requirement_parse_attempt_superseded")
        return parsed.markdown, {
            "source_structure": [block.model_dump() for block in parsed.structure],
            "parse_report": {
                "parser": parsed.parser,
                "parser_version": parsed.parser_version,
                "page_count": parsed.page_count,
                "ocr_enabled": parsed.ocr_enabled,
                "ocr_language": parsed.ocr_language,
                "unprocessed_blocks": parsed.unprocessed_blocks,
                "extraction_warnings": parsed.extraction_warnings,
                "structure_available": bool(parsed.structure),
            },
        }
    return await parse_requirement_source(
        data,
        document["format"],
        document["filename"],
        document.get("ocr_language"),
    )


async def index_requirement_document(document, _stale_retries=0):
    source_structure = document.get("source_structure") or []
    extraction = dict(document.get("parse_report") or {})
    if (document.get("raw_source") or {}).get("storage") == "embedded":
        extraction.setdefault("extraction_method", "USER_PROVIDED")
        extraction.setdefault("unprocessed_blocks", [])
    source_structure_hash = str(
        document.get("source_structure_source_hash") or document.get("content_hash") or ""
    )
    if document.get("source_structure_store") == "blocks":
        source_structure = await requirement_source_block_repository.list_version(
            document["project_id"], document["_id"], source_structure_hash
        )
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
        ai_enabled=document.get("ai_enabled") is True,
        approved_by=document.get("approved_by"),
        approved_at=document.get("approved_at"),
        effective_from=document.get("effective_from"),
        tags=document.get("tags") or [],
        source_structure=source_structure,
        document_id=document["_id"],
        content_format=document.get("format"),
        source_type=document.get("source_type"),
        source_version=document.get("source_version"),
        source_hash=document.get("content_hash"),
        extraction=extraction,
    )
    index_status = requirement_document_index_status(
        indexed, extraction
    )
    result = await requirement_document_repository.set_index_result(
        document["_id"],
        document["project_id"],
        index_status,
        now(),
        expected_revision=document.get("revision"),
        index_contract_version=(
            REQUIREMENT_DOCUMENT_INDEX_CONTRACT_VERSION if indexed else None
        ),
    )
    if result.matched_count:
        return indexed

    latest = await requirement_document_repository.find(
        document["_id"], document["project_id"]
    )
    if (
        _stale_retries < 1
        and latest
        and latest.get("ai_enabled")
        and latest.get("status") != "ARCHIVED"
    ):
        return await index_requirement_document(latest, _stale_retries + 1)
    if not latest or not latest.get("ai_enabled") or latest.get("status") == "ARCHIVED":
        removed = await remove_artifact(document["project_id"], document["_id"])
        if removed and latest:
            await requirement_document_repository.set_index_result(
                latest["_id"],
                latest["project_id"],
                "NOT_REQUESTED",
                now(),
                expected_revision=latest.get("revision"),
            )
    return False


def requirement_document_index_status(indexed: bool, parse_report: dict) -> str:
    if not indexed:
        return 'FAILED'
    unprocessed_blocks = parse_report.get("unprocessed_blocks")
    if not isinstance(unprocessed_blocks, list) or unprocessed_blocks:
        return 'DEGRADED'
    return 'INDEXED'


def ai_safe_parse_report(document: dict) -> dict:
    report = document.get("parse_report")
    if not isinstance(report, dict):
        report = {}
    unprocessed = report.get("unprocessed_blocks")
    has_unprocessed_report = isinstance(unprocessed, list)
    if not has_unprocessed_report:
        unprocessed = []
    bounded = []
    for block in unprocessed[:100]:
        if not isinstance(block, dict):
            continue
        diagnostic = {}
        for key in ("page_no", "block_id", "type", "reason_code", "unmapped_token_count"):
            value = block.get(key)
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                diagnostic[key] = value[:160] if isinstance(value, str) else value
        confidence = block.get("ocr_page_confidence")
        if (
            isinstance(confidence, (int, float))
            and not isinstance(confidence, bool)
            and 0 <= confidence <= 1
        ):
            diagnostic["ocr_page_confidence"] = float(confidence)
        bounded.append(diagnostic)
    warnings = []
    for block in report.get("extraction_warnings", [])[:100] if isinstance(report.get("extraction_warnings"), list) else []:
        if not isinstance(block, dict):
            continue
        diagnostic = {}
        for key in ("page_no", "block_id", "type", "reason_code"):
            value = block.get(key)
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                diagnostic[key] = value[:160] if isinstance(value, str) else value
        confidence = block.get("ocr_page_confidence")
        if (
            isinstance(confidence, (int, float))
            and not isinstance(confidence, bool)
            and 0 <= confidence <= 1
        ):
            diagnostic["ocr_page_confidence"] = float(confidence)
        warnings.append(diagnostic)
    return {
        "parser": report.get("parser") if isinstance(report.get("parser"), str) else None,
        "parser_version": report.get("parser_version") if isinstance(report.get("parser_version"), str) else None,
        "page_count": report.get("page_count") if isinstance(report.get("page_count"), int) else None,
        "ocr_enabled": report.get("ocr_enabled") if isinstance(report.get("ocr_enabled"), bool) else None,
        "structure_available": report.get("structure_available") if isinstance(report.get("structure_available"), bool) else None,
        "unprocessed_blocks_reported": has_unprocessed_report,
        "unprocessed_block_count": len(unprocessed) if has_unprocessed_report else None,
        "unprocessed_blocks": bounded,
        "unprocessed_blocks_truncated": len(unprocessed) > len(bounded),
        "extraction_warnings": warnings,
        "extraction_warnings_truncated": len(report.get("extraction_warnings", [])) > len(warnings)
        if isinstance(report.get("extraction_warnings"), list)
        else False,
    }


def can_retry_requirement_document_parse(document):
    status = document.get("status")
    if status in {"UPLOADED", "PARSE_FAILED"}:
        return True
    if status != "PARSING":
        return False
    updated_at = document.get("updated_at")
    if not isinstance(updated_at, datetime):
        return False
    return updated_at <= now() - timedelta(
        seconds=settings.DOCUMENT_PARSE_LEASE_SECONDS
    )


async def maintain_requirement_parse_lease(document_id, project_id, attempt_id):
    interval = max(1, settings.DOCUMENT_PARSE_LEASE_SECONDS / 3)
    while True:
        await asyncio.sleep(interval)
        try:
            heartbeat = await requirement_document_repository.heartbeat_parse_attempt(
                document_id, project_id, attempt_id, now()
            )
        except Exception:
            logger.exception(
                "Unable to renew requirement parse lease document=%s", document_id
            )
            continue
        if heartbeat.matched_count != 1:
            return


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
    ocr_language=None,
    supersedes_document_id=None,
):
    if format not in supported_requirement_formats():
        raise HTTPException(status_code=422, detail={"code": 'UNSUPPORTED_IMPORT_FORMAT'})
    ocr_language = normalize_ocr_language(format, ocr_language)
    if not data:
        raise HTTPException(status_code=422, detail={"code": 'EMPTY_IMPORT'})
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail={"code": 'IMPORT_TOO_LARGE'})
    await get_project(project_id, user, 'requirement_document.upload')
    shared_with = await validate_document_recipients(project_id, shared_with or [])
    resolved_filename = filename or f"{'requirements'}.{format}"
    content_hash = hashlib.sha256(data).hexdigest()
    resolved_source_type = 'API_SPEC' if format in ("openapi", "postman") else source_type
    deduplication_key = requirement_document_deduplication_key(
        project_id,
        content_hash,
        format,
        visibility,
        shared_with,
        ai_enabled,
        resolved_source_type,
        ocr_language,
        user.id,
    )
    lineage = await resolve_source_successor(
        project_id,
        supersedes_document_id,
        user,
        content_hash=content_hash,
        format=format,
        visibility=visibility,
        shared_with=shared_with,
        ai_enabled=ai_enabled,
        source_type=resolved_source_type,
        ocr_language=ocr_language,
    )
    scoped_duplicate = await requirement_document_repository.find_by_deduplication_key(
        project_id, deduplication_key
    )
    if scoped_duplicate:
        if lineage and not (
            scoped_duplicate.get("source_series_id") == lineage["source_series_id"]
            and scoped_duplicate.get("source_version_sequence")
            == lineage["source_version_sequence"]
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "SOURCE_VERSION_CONTENT_ALREADY_EXISTS"},
            )
        scoped_duplicate = await require_document_access(
            scoped_duplicate, user, "requirement_document.read"
        )
        scoped_duplicate = await reuse_uploaded_requirement_document(
            scoped_duplicate, user
        )
        return RequirementDocumentResult(scoped_duplicate)
    existing = await requirement_document_repository.find_by_hash(project_id, content_hash, user.id)
    if existing:
        ensure_duplicate_settings_match(
            existing,
            format=format,
            visibility=visibility,
            shared_with=shared_with,
            ai_enabled=ai_enabled,
            source_type=resolved_source_type,
            ocr_language=ocr_language,
        )
        if lineage and existing.get("source_series_id") == lineage["source_series_id"] and existing.get("source_version_sequence") == lineage["source_version_sequence"]:
            existing = await require_document_access(existing, user, 'requirement_document.read')
            existing = await reuse_uploaded_requirement_document(existing, user)
            return RequirementDocumentResult(existing)
        if lineage:
            raise HTTPException(status_code=409, detail={"code": "SOURCE_VERSION_CONTENT_ALREADY_EXISTS"})
        existing = await require_document_access(existing, user, 'requirement_document.read')
        existing = await reuse_uploaded_requirement_document(existing, user)
        return RequirementDocumentResult(existing)
    existing = await find_reusable_document_duplicate(
        project_id,
        content_hash,
        format,
        visibility,
        shared_with,
        ai_enabled,
        resolved_source_type,
        user,
        ocr_language,
    )
    if existing:
        if lineage and not (
            existing.get("source_series_id") == lineage["source_series_id"]
            and existing.get("source_version_sequence") == lineage["source_version_sequence"]
        ):
            raise HTTPException(status_code=409, detail={"code": "SOURCE_VERSION_CONTENT_ALREADY_EXISTS"})
        existing = await reuse_uploaded_requirement_document(existing, user)
        return RequirementDocumentResult(existing)
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
        "deduplication_key": deduplication_key,
        "raw_source": source,
        "normalized_content": None,
        "source_version": lineage["source_version"] if lineage else '1',
        "source_series_id": lineage["source_series_id"] if lineage else document_id,
        "source_version_sequence": lineage["source_version_sequence"] if lineage else 1,
        "previous_source_version_id": lineage["previous_source_version_id"] if lineage else None,
        "source_type": resolved_source_type,
        "ocr_language": ocr_language,
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
        await remove_unclaimed_raw_requirement_source(
            project_id, document_id, source
        )
        if lineage:
            await raise_source_version_insert_conflict(project_id, lineage)
        scoped_duplicate = await requirement_document_repository.find_by_deduplication_key(
            project_id, deduplication_key
        )
        if scoped_duplicate:
            scoped_duplicate = await require_document_access(
                scoped_duplicate, user, "requirement_document.read"
            )
            scoped_duplicate = await reuse_uploaded_requirement_document(
                scoped_duplicate, user
            )
            return RequirementDocumentResult(scoped_duplicate)
        existing = await requirement_document_repository.find_by_hash(
            project_id, content_hash, user.id
        )
        if existing:
            ensure_duplicate_settings_match(
                existing,
                format=format,
                visibility=visibility,
                shared_with=shared_with,
                ai_enabled=ai_enabled,
                source_type=resolved_source_type,
                ocr_language=ocr_language,
            )
            existing = await require_document_access(existing, user, 'requirement_document.read')
            existing = await reuse_uploaded_requirement_document(existing, user)
            return RequirementDocumentResult(existing)
        raise
    except Exception:
        await remove_unclaimed_raw_requirement_source(
            project_id, document_id, source
        )
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
    return RequirementDocumentResult(document, "QUEUED")


async def list_requirement_document_records(project_id, status, query_text, limit, user):
    await get_project(project_id, user, 'requirement_document.read')
    query = {"project_id": project_id}
    if status:
        query["status"] = status.upper()
    if query_text:
        query["filename"] = {"$regex": re.escape(query_text), "$options": "i"}
    documents = await requirement_document_repository.list(query, limit)
    return [
        {**document, "can_retry_parse": can_retry_requirement_document_parse(document)}
        for document in documents
        if can_read_requirement_document(document, user)
    ]


def encode_ai_document_cursor(project_id, document_id):
    cursor_value = f"{project_id}\0{document_id}"
    payload = base64.urlsafe_b64encode(cursor_value.encode("utf-8")).decode("ascii").rstrip("=")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"), payload.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{signature}"


def decode_ai_document_cursor(cursor, project_id):
    if not cursor:
        return None
    try:
        payload, signature = str(cursor).split(".", 1)
        expected = hmac.new(
            settings.SECRET_KEY.encode("utf-8"), payload.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        encoded = payload + "=" * (-len(payload) % 4)
        cursor_value = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
        cursor_project_id, separator, document_id = cursor_value.partition("\0")
        if (
            separator != "\0"
            or cursor_project_id != str(project_id)
            or not document_id
            or len(document_id) > 200
        ):
            raise ValueError("invalid document cursor")
        return document_id
    except (ValueError, UnicodeDecodeError, base64.binascii.Error) as error:
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_CURSOR_INVALID"}) from error


async def list_ai_requirement_document_page(project_id, cursor, limit, user):
    await get_project(project_id, user, "requirement_document.read")
    after_id = decode_ai_document_cursor(cursor, project_id)
    documents = await requirement_document_repository.list_ai_scope_page(
        project_id, after_id, limit
    )
    readable = [
        document for document in documents if can_read_requirement_document(document, user)
    ]
    last_id = str(documents[-1]["_id"]) if len(documents) == limit else None
    return {
        "items": [
            {
                key: document.get(key)
                for key in (
                    "_id",
                    "project_id",
                    "status",
                    "ai_enabled",
                    "revision",
                    "index_status",
                    "source_version",
                    "source_version_sequence",
                    "source_series_id",
                    "previous_source_version_id",
                    "authority",
                    "normalized_content",
                    "content_hash",
                )
            } | {"parse_report": ai_safe_parse_report(document)}
            for document in readable
        ],
        "next_cursor": encode_ai_document_cursor(project_id, last_id) if last_id else None,
    }


async def list_requirement_source_structure_page(
    document_id, offset, limit, user, permission="requirement_document.read"
):
    document = await get_requirement_document_record(document_id, user, permission)
    source_hash = str(
        document.get("source_structure_source_hash") or document.get("content_hash") or ""
    )
    if document.get("source_structure_store") == "blocks":
        rows = await requirement_source_block_repository.page_version(
            document["project_id"], document_id, source_hash, offset, limit
        )
        has_more = len(rows) > limit
        selected = rows[:limit]
        items = []
        for row in selected:
            block = dict(row.get("block", {}))
            image_metadata = block.get("image_metadata")
            if isinstance(image_metadata, dict):
                block["image_metadata"] = {
                    key: value for key, value in image_metadata.items() if key != "asset_key"
                }
            text = str(block.pop("text", "") or "")
            block.update(
                {
                    "text_preview": text[:2000],
                    "text_length": len(text),
                    "text_truncated": len(text) > 2000,
                    "block_index": row["block_index"],
                }
            )
            items.append(block)
        next_offset = offset + len(selected) if has_more else None
    else:
        source_structure = document.get("source_structure") or []
        items = []
        for index, raw_block in enumerate(source_structure[offset : offset + limit], start=offset):
            if not isinstance(raw_block, dict):
                continue
            block = dict(raw_block)
            image_metadata = block.get("image_metadata")
            if isinstance(image_metadata, dict):
                block["image_metadata"] = {
                    key: value for key, value in image_metadata.items() if key != "asset_key"
                }
            text = str(block.pop("text", "") or "")
            block.update(
                {
                    "text_preview": text[:2000],
                    "text_length": len(text),
                    "text_truncated": len(text) > 2000,
                    "block_index": index,
                }
            )
            items.append(block)
        next_offset = offset + len(items) if offset + limit < len(source_structure) else None
    report = ai_safe_parse_report(document)
    return {
        "document_id": document_id,
        "project_id": document["project_id"],
        "source_hash": source_hash or None,
        "source_structure_available": bool(items) or report.get("structure_available") is True,
        "source_structure_count": document.get(
            "source_structure_count", len(document.get("source_structure") or [])
        ),
        "items": items,
        "next_offset": next_offset,
        "parse_report": report,
    }


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


async def get_requirement_source_impact(document_id, user):
    document = await get_requirement_document_record(document_id, user)
    project_id = document["project_id"]
    await get_project(project_id, user, "requirement.read")
    series_id = str(document.get("source_series_id") or document_id)
    versions = await requirement_document_repository.list_source_series(
        project_id, series_id
    )
    if not versions:
        versions = [document]
    for item in versions:
        await require_document_access(item, user, "requirement_document.read")
    for index, item in enumerate(versions):
        expected_sequence = index + 1
        expected_parent = str(versions[index - 1]["_id"]) if index else None
        if (
            int(item.get("source_version_sequence") or 1) != expected_sequence
            or str(item.get("source_version") or expected_sequence)
            != str(expected_sequence)
            or str(item.get("source_series_id") or item["_id"]) != series_id
            or item.get("previous_source_version_id") != expected_parent
            or not item.get("content_hash")
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "SOURCE_VERSION_LINEAGE_INVALID"},
            )
    source_document_ids = [str(item["_id"]) for item in versions]
    requirement_versions = await requirement_repository.list_versions_by_source_documents(
        project_id, source_document_ids
    )
    requirement_version_ids = list(
        dict.fromkeys(str(item["_id"]) for item in requirement_versions)
    )
    cases = await test_design_repository.list_cases_linked_to_requirement(
        project_id, requirement_version_ids
    )
    case_versions = await test_design_repository.list_case_versions_linked_to_requirements(
        project_id, requirement_version_ids
    )
    case_ids = list(
        dict.fromkeys(
            str(item.get("test_case_id") or "")
            for item in case_versions
            if item.get("test_case_id")
        )
    )
    case_records = await test_design_repository.list_cases_by_ids(project_id, case_ids)
    cases_by_id = {str(item["_id"]): item for item in case_records}
    requirements = []
    seen_requirements = set()
    for item in requirement_versions:
        requirement_id = str(item.get("requirement_id") or "")
        if not requirement_id or requirement_id in seen_requirements:
            continue
        seen_requirements.add(requirement_id)
        requirements.append(
            {
                "requirement_id": requirement_id,
                "requirement_version_ids": [
                    str(version["_id"])
                    for version in requirement_versions
                    if str(version.get("requirement_id") or "") == requirement_id
                ],
            }
        )
    latest = versions[-1]
    source_versions = []
    for item in versions:
        previous_id = item.get("previous_source_version_id")
        previous = next(
            (candidate for candidate in versions if candidate.get("_id") == previous_id),
            None,
        )
        source_versions.append(
            {
                "document_id": str(item["_id"]),
                "source_version": str(item.get("source_version") or "1"),
                "source_version_sequence": int(item.get("source_version_sequence") or 1),
                "previous_source_version_id": previous_id,
                "content_hash": item.get("content_hash"),
                "status": item.get("status"),
                "is_latest": str(item["_id"]) == str(latest["_id"]),
                "content_changed_from_previous": bool(
                    previous and previous.get("content_hash") != item.get("content_hash")
                ),
            }
        )
    return {
        "source_series_id": series_id,
        "requested_document_id": str(document["_id"]),
        "latest_document_id": str(latest["_id"]),
        "source_versions": source_versions,
        "affected_requirement_versions": [
            {
                "requirement_version_id": str(item["_id"]),
                "requirement_id": str(item.get("requirement_id") or ""),
                "version": item.get("version"),
                "status": item.get("status"),
            }
            for item in requirement_versions
        ],
        "affected_requirements": requirements,
        "affected_test_cases": [
            {
                "test_case_id": str(item["_id"]),
                "test_case_key": item.get("test_case_key"),
                "current_version_id": item.get("current_version_id"),
                "requirement_version_ids": item.get("current_version", {}).get(
                    "requirement_version_ids", []
                ),
            }
            for item in cases
        ],
        "affected_test_case_versions": [
            {
                "test_case_id": str(item.get("test_case_id") or ""),
                "test_case_key": cases_by_id.get(
                    str(item.get("test_case_id") or ""), {}
                ).get("test_case_key"),
                "test_case_version_id": str(item["_id"]),
                "version": item.get("version"),
                "status": item.get("status"),
                "is_current": str(
                    cases_by_id.get(str(item.get("test_case_id") or ""), {}).get(
                        "current_version_id"
                    )
                    or ""
                ) == str(item["_id"]),
                "requirement_version_ids": item.get("requirement_version_ids", []),
            }
            for item in case_versions
        ],
        "impact_status": "HAS_DOWNSTREAM_ARTIFACTS"
        if requirement_versions or cases
        else "NO_DOWNSTREAM_ARTIFACTS",
    }


async def update_requirement_document_record(document_id, payload, user):
    document = await get_requirement_document_record(
        document_id, user, 'knowledge.manage'
    )
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if (
        "source_version" in changes
        and document.get("source_series_id")
        and str(changes["source_version"])
        != str(document.get("source_version_sequence") or 1)
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "SOURCE_VERSION_IS_LINEAGE_MANAGED"},
        )
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
    if payload.ai_enabled and document.get("index_status") == "REVOKE_PENDING":
        raise HTTPException(
            status_code=409,
            detail={"code": "AI_READ_REVOCATION_IN_PROGRESS"},
        )
    if payload.ai_enabled and not document.get("normalized_content"):
        raise HTTPException(status_code=409, detail={"code": "DOCUMENT_PARSE_REQUIRED"})
    updated = await requirement_document_repository.update_with_revision(
        document_id,
        document["project_id"],
        payload.expected_revision,
        {
            "ai_enabled": payload.ai_enabled,
            "index_status": "PENDING" if payload.ai_enabled else "REVOKE_PENDING",
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    if payload.ai_enabled:
        indexed = await index_requirement_document(updated)
        if not indexed:
            raise HTTPException(status_code=503, detail={"code": "KNOWLEDGE_INDEX_FAILED"})
        source_opened = await ai_automation_access_repository.allow_source(
            f"source:{updated['_id']}"
        )
        if not source_opened:
            raise HTTPException(
                status_code=503,
                detail={"code": "AI_READ_ACCESS_DRAIN_PENDING"},
            )
        latest = await requirement_document_repository.find(
            document_id, updated["project_id"]
        )
        if not latest or latest.get("index_status") not in {"INDEXED", "DEGRADED"}:
            raise HTTPException(
                status_code=503,
                detail={"code": "KNOWLEDGE_INDEX_FAILED"},
            )
        updated = latest
        await queue_document_ingestion(updated, user)
    else:
        cancellation_failed = False
        run_access_fence_failed = False
        cancelled_runs = 0
        source_drained = await ai_automation_access_repository.revoke_and_wait(
            f"source:{updated['_id']}"
        )
        if not source_drained:
            await audit(
                user.id,
                "requirement_document.ai_read_event_cancellation_pending",
                "RequirementDocument",
                document_id,
                document["project_id"],
                {"revision": updated["revision"], "reason": "SOURCE_REQUESTS_STILL_ACTIVE"},
            )
            raise HTTPException(
                status_code=503,
                detail={"code": "AI_AUTOMATION_REQUESTS_STILL_ACTIVE"},
            )
        try:
            cancelled_events = await cancel_pending_document_ingestion(
                updated["_id"], "AI_READ_PERMISSION_REVOKED"
            )
        except Exception:
            logger.exception(
                "Failed to cancel queued document ingestion document=%s",
                updated["_id"],
            )
            cancelled_events = 0
            cancellation_failed = True
        try:
            cancelled_runs = await cancel_document_ingestion_runs(updated["_id"])
        except Exception:
            logger.exception(
                "Failed to cancel dispatched AI document runs document=%s",
                updated["_id"],
            )
            cancellation_failed = True
            run_access_fence_failed = True
        if run_access_fence_failed:
            await audit(
                user.id,
                "requirement_document.ai_read_event_cancellation_pending",
                "RequirementDocument",
                document_id,
                document["project_id"],
                {
                    "revision": updated["revision"],
                    "cancelled_pending_events": cancelled_events,
                    "cancelled_dispatched_runs": cancelled_runs,
                },
            )
            raise HTTPException(
                status_code=503,
                detail={"code": "AI_INGESTION_CANCELLATION_PENDING"},
            )
        removed = await remove_artifact(updated["project_id"], updated["_id"])
        if not removed:
            await audit(
                user.id,
                "requirement_document.ai_read_revocation_pending",
                "RequirementDocument",
                document_id,
                document["project_id"],
                {
                    "revision": updated["revision"],
                    "cancelled_pending_events": cancelled_events,
                    "cancelled_dispatched_runs": cancelled_runs,
                },
            )
            raise HTTPException(
                status_code=503,
                detail={"code": "KNOWLEDGE_REVOCATION_PENDING"},
            )
        if cancellation_failed:
            await audit(
                user.id,
                "requirement_document.ai_read_event_cancellation_pending",
                "RequirementDocument",
                document_id,
                document["project_id"],
                {
                    "revision": updated["revision"],
                    "cancelled_pending_events": cancelled_events,
                    "cancelled_dispatched_runs": cancelled_runs,
                },
            )
            raise HTTPException(
                status_code=503,
                detail={"code": "AI_INGESTION_CANCELLATION_PENDING"},
            )
        result = await requirement_document_repository.set_index_result(
            updated["_id"],
            updated["project_id"],
            "NOT_REQUESTED",
            now(),
            expected_revision=updated.get("revision"),
        )
        if not result.matched_count:
            latest = await requirement_document_repository.find(
                updated["_id"], updated["project_id"]
            )
            if (
                latest
                and latest.get("ai_enabled")
                and latest.get("status") != "ARCHIVED"
            ):
                await index_requirement_document(latest)
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        updated = await requirement_document_repository.find(
            updated["_id"], updated["project_id"]
        )
    await audit(
        user.id,
        "requirement_document.ai_read_updated",
        'RequirementDocument',
        document_id,
        document["project_id"],
        {
            "ai_enabled": payload.ai_enabled,
            "cancelled_pending_events": (
                cancelled_events if not payload.ai_enabled else 0
            ),
            "cancelled_dispatched_runs": (
                cancelled_runs if not payload.ai_enabled else 0
            ),
        },
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
    )
    updated = await requirement_document_repository.find(
        document_id, document["project_id"]
    )
    if indexed and updated.get("ai_enabled"):
        await queue_document_ingestion(updated, user)
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
    if document.get("ai_enabled") is True:
        source_drained = await ai_automation_access_repository.revoke_and_wait(
            f"source:{document_id}"
        )
        if not source_drained:
            raise HTTPException(
                status_code=503,
                detail={"code": "AI_AUTOMATION_REQUESTS_STILL_ACTIVE"},
            )
        try:
            await cancel_pending_document_ingestion(
                document_id, "REQUIREMENT_DOCUMENT_ARCHIVED"
            )
            await cancel_document_ingestion_runs(document_id)
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "DOCUMENT_AUTOMATION_CANCELLATION_PENDING"},
            ) from error
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
        unset_fields=["deduplication_key"],
    )
    if not updated:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT'},
        )
    if updated.get("ai_enabled"):
        removed = await remove_artifact(updated["project_id"], updated["_id"])
        if not removed:
            raise HTTPException(
                status_code=503,
                detail={"code": "KNOWLEDGE_REVOCATION_PENDING"},
            )
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
        if document.get("status") == "READY" and document.get("ai_enabled") is True:
            recovered = await recover_document_ingestion(document, user)
            latest = await requirement_document_repository.find(
                document_id, document["project_id"]
            )
            if (
                not recovered
                or not latest
                or latest.get("index_status") not in {"INDEXED", "DEGRADED"}
            ):
                raise HTTPException(
                    status_code=503,
                    detail={"code": "DOCUMENT_RESTORE_RECOVERY_PENDING"},
                )
            return latest
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
    if updated.get("ai_enabled") is True:
        indexed = await index_requirement_document(updated)
        if not indexed:
            raise HTTPException(
                status_code=503,
                detail={"code": "KNOWLEDGE_INDEX_FAILED"},
            )
        source_opened = await ai_automation_access_repository.allow_source(
            f"source:{document_id}"
        )
        if not source_opened:
            raise HTTPException(
                status_code=503,
                detail={"code": "AI_READ_ACCESS_DRAIN_PENDING"},
            )
        latest = await requirement_document_repository.find(
            document_id, updated["project_id"]
        )
        if not latest or latest.get("index_status") not in {"INDEXED", "DEGRADED"}:
            raise HTTPException(
                status_code=503,
                detail={"code": "DOCUMENT_RESTORE_RECOVERY_PENDING"},
            )
        updated = latest
        await queue_document_ingestion(updated, user)
    await audit(
        user.id,
        'requirement_document_restored',
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"reason": payload.reason},
    )
    return updated


async def retry_requirement_document_parse_record(
    document_id, payload, user, *, _document=None
):
    if _document is None:
        document = await get_requirement_document_record(
            document_id, user, 'requirement_document.extract'
        )
    else:
        document = _document
        if document.get("_id") != document_id or document.get("created_by") != user.id:
            raise HTTPException(status_code=404, detail={"code": "DOCUMENT_NOT_FOUND"})
    if document.get("status") == 'READY':
        recovered = await recover_document_ingestion(document, user)
        latest = await requirement_document_repository.find(
            document_id, document["project_id"]
        )
        return RequirementDocumentResult(
            latest or document,
            "SUCCESS" if recovered else "DEGRADED",
            None if recovered else "DOCUMENT_INGESTION_RECOVERY_FAILED",
        )
    retryable_status = document.get("status")
    attempt_id = new_id("PARSE")
    if retryable_status in {'UPLOADED', 'PARSE_FAILED'}:
        claimed = await requirement_document_repository.claim_status(
            document_id,
            document["project_id"],
            retryable_status,
            payload.expected_revision,
            'PARSING',
            now(),
            attempt_id=attempt_id,
        )
    elif retryable_status == "PARSING" and can_retry_requirement_document_parse(document):
        stale_before = now() - timedelta(
            seconds=settings.DOCUMENT_PARSE_LEASE_SECONDS
        )
        claimed = await requirement_document_repository.claim_stale_parse(
            document_id,
            document["project_id"],
            payload.expected_revision,
            stale_before,
            now(),
            attempt_id,
        )
    else:
        raise HTTPException(
            status_code=409,
            detail={"code": 'DOCUMENT_NOT_RETRYABLE', "status": document.get("status")},
        )
    if claimed.matched_count != 1:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    lease_task = asyncio.create_task(
        maintain_requirement_parse_lease(
            document_id, document["project_id"], attempt_id
        )
    )
    try:
        content, source_details = await asyncio.wait_for(
            read_and_parse_requirement_source(document, attempt_id),
            timeout=settings.DOCUMENT_PARSE_TIMEOUT_SECONDS,
        )
        await get_project(
            document["project_id"], user, "requirement_document.extract"
        )
    except Exception as error:
        if (
            isinstance(error, HTTPException)
            and error.status_code in {403, 404}
            and document.get("format") == "pdf"
        ):
            try:
                await clear_requirement_conversion_checkpoints(
                    document_id,
                    document["project_id"],
                    str(document.get("created_by") or ""),
                    str(document.get("content_hash") or ""),
                )
            except Exception as cleanup_error:
                logger.warning(
                    "Revoked requirement parse checkpoints retained for TTL document_id=%s error=%s",
                    document_id,
                    type(cleanup_error).__name__,
                )
        failed = await requirement_document_repository.transition_status(
            document_id,
            document["project_id"],
            'PARSING',
            {
                "status": 'PARSE_FAILED',
                "parse_error_type": type(error).__name__,
                "updated_at": now(),
            },
            attempt_id=attempt_id,
        )
        if not failed:
            failed = await requirement_document_repository.find(
                document_id, document["project_id"]
            )
            return RequirementDocumentResult(
                failed or document, 'DEGRADED', 'PARSE_RETRY_SUPERSEDED'
            )
        await audit(
            user.id,
            'requirement_document_parse_failed',
            'RequirementDocument',
            document_id,
            document["project_id"],
            {"error_type": type(error).__name__},
        )
        failure_code = (
            "PARSER_TIMEOUT"
            if isinstance(error, asyncio.TimeoutError)
            else "DOCUMENT_ACCESS_REVOKED"
            if isinstance(error, HTTPException) and error.status_code in {403, 404}
            else "PARSER_FAILED"
        )
        return RequirementDocumentResult(
            failed, 'DEGRADED', failure_code
        )
    finally:
        lease_task.cancel()
        await asyncio.gather(lease_task, return_exceptions=True)
    normalized = serialized_content(content)
    source_blocks = source_details.pop("source_structure", [])
    source_structure_hash = str(document.get("content_hash") or "")
    await requirement_source_block_repository.replace_version(
        document["project_id"], document_id, source_structure_hash, source_blocks
    )
    source_details.update(
        {
            "source_structure_store": "blocks",
            "source_structure_source_hash": source_structure_hash,
            "source_structure_count": len(source_blocks),
        }
    )
    updated = await requirement_document_repository.transition_status(
        document_id,
        document["project_id"],
        'PARSING',
        {
            "normalized_content": content,
            **source_details,
            "normalized_content_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "status": 'READY',
            "parse_error_type": None,
            "updated_at": now(),
        },
        attempt_id=attempt_id,
        unset_fields=["source_structure"],
    )
    if not updated:
        latest = await requirement_document_repository.find(
            document_id, document["project_id"]
        )
        if (
            not latest
            or latest.get("source_structure_source_hash") != source_structure_hash
        ):
            try:
                await requirement_source_block_repository.delete_version(
                    document["project_id"], document_id, source_structure_hash
                )
            except Exception as error:
                logger.warning(
                    "Unpublished requirement source blocks retained document_id=%s error=%s",
                    document_id,
                    type(error).__name__,
                )
        raise HTTPException(status_code=409, detail={"code": 'PARSE_RETRY_CONFLICT'})
    try:
        await requirement_source_block_repository.delete_obsolete_versions(
            document["project_id"], document_id, source_structure_hash
        )
    except Exception as error:
        logger.warning(
            "Obsolete requirement source blocks retained document_id=%s error=%s",
            document_id,
            type(error).__name__,
        )
    if document.get("format") == "pdf":
        try:
            await clear_requirement_conversion_checkpoints(
                document_id,
                document["project_id"],
                str(document.get("created_by") or ""),
                str(document.get("content_hash") or ""),
            )
        except Exception as error:
            logger.warning(
                "Requirement conversion checkpoint cleanup deferred document_id=%s error=%s",
                document_id,
                type(error).__name__,
            )
    await audit(
        user.id,
        'requirement_document_parse_succeeded',
        'RequirementDocument',
        document_id,
        document["project_id"],
    )
    if updated.get("ai_enabled") is True:
        indexed = await index_requirement_document(updated)
        latest = await requirement_document_repository.find(
            document_id, updated["project_id"]
        )
        if not indexed or not latest or latest.get("index_status") not in {"INDEXED", "DEGRADED"}:
            return RequirementDocumentResult(
                latest or updated, 'DEGRADED', 'KNOWLEDGE_INDEX_FAILED'
            )
        source_opened = await ai_automation_access_repository.allow_source(
            f"source:{document_id}"
        )
        if not source_opened:
            return RequirementDocumentResult(
                latest, 'DEGRADED', 'AI_READ_ACCESS_DRAIN_PENDING'
            )
        await queue_document_ingestion(latest, user)
        updated = latest
    return RequirementDocumentResult(updated)
