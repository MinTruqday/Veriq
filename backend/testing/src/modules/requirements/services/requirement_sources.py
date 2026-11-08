import hashlib
import re
from dataclasses import dataclass

from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.repositories.requirement_document import requirement_document_repository


@dataclass(frozen=True)
class RequirementSourceResult:
    data: dict
    indexed: bool

    @property
    def status(self):
        return (
            'SUCCESS'
            if self.indexed
            and self.data.get("ai_enabled") is True
            and self.data.get("status") == 'READY'
            and self.data.get("index_status") == 'INDEXED'
            else 'DEGRADED'
        )

    @property
    def degraded_mode(self):
        index_status = self.data.get("index_status")
        if self.data.get("ai_enabled") is not True:
            return 'AI_READ_NOT_ENABLED'
        if self.data.get("status") != 'READY':
            return 'DOCUMENT_NOT_READY'
        if self.indexed and index_status == 'INDEXED':
            return None
        if index_status == 'DEGRADED':
            if self.data.get("index_cleanup_pending"):
                return 'KNOWLEDGE_CLEANUP_PENDING'
            return 'PARTIAL_SOURCE_EXTRACTION'
        if index_status == 'FAILED':
            return 'DEGRADED_VECTOR'
        if index_status == 'NOT_REQUESTED':
            return 'AI_READ_NOT_ENABLED'
        if index_status == 'PENDING':
            return 'KNOWLEDGE_INDEX_PENDING'
        return 'UNKNOWN_INDEX_STATUS'


async def create_requirement_source(project_id, payload, user):
    await get_project(project_id, user, 'knowledge.manage')
    content_hash = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
    existing = await requirement_document_repository.find_embedded_knowledge_source_by_hash(
        project_id, content_hash, user.id, payload.source_type
    )
    if existing:
        indexed = False
        needs_migration = existing.get("ai_enabled") is None
        if needs_migration:
            migrated = await requirement_document_repository.update_with_revision(
                existing["_id"],
                project_id,
                existing.get("revision"),
                {
                    "ai_enabled": True,
                    "visibility": "project",
                    "shared_with": [],
                    "record_kind": "KNOWLEDGE_SOURCE",
                    "index_status": "PENDING",
                    "indexed_at": None,
                    "index_cleanup_pending": [],
                    "updated_at": now(),
                },
                unset_fields=["index_contract_version"],
            )
            existing = migrated or await requirement_document_repository.find(
                existing["_id"], project_id
            )
            if existing and existing.get("ai_enabled") is True:
                from src.modules.requirements.services.requirement_documents import (
                    index_requirement_document,
                )

                indexed = await index_requirement_document(existing)
                existing = await requirement_document_repository.find(
                    existing["_id"], project_id
                )
        if not existing:
            raise HTTPException(
                status_code=409,
                detail={"code": "KNOWLEDGE_SOURCE_CHANGED_DURING_REUSE"},
            )
        is_indexed = bool(
            existing.get("ai_enabled") is True
            and existing.get("status") == 'READY'
            and existing.get("index_status") in {'INDEXED', 'DEGRADED'}
            and (not needs_migration or indexed)
        )
        return RequirementSourceResult(
            existing,
            is_indexed,
        )
    timestamp = now()
    safe_name = (
        re.sub(
            '[^A-Za-z0-9_-]+',
            '-',
            payload.title,
        ).strip('-')
        or 'knowledge-source'
    )
    document = {
        "_id": new_id('KSRC'),
        "project_id": project_id,
        "record_kind": "KNOWLEDGE_SOURCE",
        "filename": f"{safe_name}{'.md'}",
        "format": 'md',
        "content_hash": content_hash,
        "raw_source": {
            "storage": 'embedded',
            "content": payload.content,
            "sha256": content_hash,
            "size": len(payload.content.encode("utf-8")),
            "source_url": payload.source_url,
        },
        "normalized_content": payload.content,
        "normalized_content_hash": content_hash,
        "source_version": payload.source_version,
        "title": payload.title,
        "source_type": payload.source_type,
        "authority": payload.authority,
        "source_url": payload.source_url,
        "owner_id": payload.owner_id,
        "created_by": user.id,
        "visibility": "project",
        "shared_with": [],
        "ai_enabled": True,
        "module": payload.module,
        "component": payload.component,
        "product_area": payload.product_area,
        "release_id": payload.release_id,
        "external_source_id": payload.external_source_id,
        "approval_status": payload.approval_status,
        "approved_by": payload.approved_by,
        "approved_at": payload.approved_at,
        "effective_from": payload.effective_from,
        "tags": payload.tags,
        "status": 'READY',
        "index_status": 'PENDING',
        "revision": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await requirement_document_repository.insert(document)
    from src.modules.requirements.services.requirement_documents import index_requirement_document

    indexed = await index_requirement_document(document)
    document = await requirement_document_repository.find(
        document["_id"], project_id
    ) or {
        **document,
        "index_status": "INDEXED" if indexed else "FAILED",
    }
    await audit(
        user.id,
        'knowledge_source_created',
        'RequirementDocument',
        document["_id"],
        project_id,
        {"source_type": payload.source_type, "authority": payload.authority},
    )
    return RequirementSourceResult(document, indexed)


async def list_requirement_sources(project_id, include_archived, user):
    from src.modules.requirements.services.requirement_documents import (
        list_requirement_document_records,
    )

    documents = await list_requirement_document_records(project_id, "", "", 1000, user)
    if not include_archived:
        documents = [item for item in documents if item.get("status") != "ARCHIVED"]
    project = await requirement_document_repository.project_authority_order(project_id)
    order = (project or {}).get("settings", {}).get(
        "knowledge_authority_order", ['APPROVED_SOURCE', 'CONTROLLED_SOURCE', 'PROJECT_REFERENCE', 'SUPPLEMENTAL', 'DRAFT', 'UNVERIFIED']
    )
    ranks = {value: index for index, value in enumerate(order)}
    documents.sort(
        key=lambda item: (ranks.get(item.get("authority"), len(ranks)), item.get("updated_at"))
    )
    return documents


async def reindex_requirement_source(document_id, user):
    from src.modules.requirements.services.requirement_documents import (
        finish_requirement_document_ai_revocation,
        index_requirement_document,
        open_requirement_document_source_if_current,
        require_document_access,
    )

    document = await get_project_entity(
        'requirement_documents',
        document_id,
        user,
        'knowledge.manage',
    )
    await require_document_access(document, user, 'knowledge.manage')
    if document.get("status") == 'ARCHIVED':
        raise HTTPException(
            status_code=409, detail={"code": 'KNOWLEDGE_SOURCE_ARCHIVED'}
        )
    if document.get("ai_enabled") is not True:
        raise HTTPException(
            status_code=409, detail={"code": "AI_READ_PERMISSION_REQUIRED"}
        )
    if document.get("index_status") == "REVOKE_PENDING":
        if not await finish_requirement_document_ai_revocation(document):
            raise HTTPException(
                status_code=503,
                detail={"code": "KNOWLEDGE_REVOCATION_PENDING"},
            )
        raise HTTPException(
            status_code=409,
            detail={"code": "AI_READ_PERMISSION_REQUIRED"},
        )
    indexed = await index_requirement_document(document)
    updated_document = await requirement_document_repository.find(
        document_id, document["project_id"]
    )
    index_status = (updated_document or {}).get("index_status", "FAILED")
    indexed = indexed and index_status in {"INDEXED", "DEGRADED"}
    if indexed:
        source_opened, updated_document = await open_requirement_document_source_if_current(
            document_id, document["project_id"]
        )
        indexed = source_opened
    updated = await requirement_document_repository.find(
        document_id, document["project_id"]
    )
    await audit(
        user.id,
        'knowledge_source_reindexed',
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"indexed": indexed},
    )
    return RequirementSourceResult(updated, indexed)


async def archive_requirement_source(document_id, payload, user):
    from src.modules.requirements.services.requirement_documents import (
        begin_requirement_document_archive_cleanup,
        finish_requirement_document_archive_cleanup,
        require_document_access,
    )

    document = await get_project_entity(
        'requirement_documents', document_id, user, 'knowledge.manage'
    )
    await require_document_access(document, user, 'knowledge.manage')
    timestamp = now()
    archived, newly_archived = await begin_requirement_document_archive_cleanup(
        document,
        expected_revision=payload.expected_revision,
        archive_changes={
            "status_before_archive": document.get("status", 'READY'),
            "archived_by": user.id,
            "archived_at": timestamp,
            "archive_reason": payload.reason,
        },
    )
    if newly_archived:
        await audit(
            user.id,
            'knowledge_source_archived',
            'RequirementDocument',
            document_id,
            document["project_id"],
            {"reason": payload.reason},
        )
    return await finish_requirement_document_archive_cleanup(archived)
