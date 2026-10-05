import hashlib
import re
from dataclasses import dataclass

from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now, require_action_policy
from src.repositories.requirement_document import requirement_document_repository
from src.clients.project_knowledge import index_artifact





@dataclass(frozen=True)
class RequirementSourceResult:
    data: dict
    indexed: bool

    @property
    def status(self):
        return (
            'SUCCESS'
            if self.indexed
            else 'DEGRADED'
        )

    @property
    def degraded_mode(self):
        return None if self.indexed else 'DEGRADED_VECTOR'


async def create_requirement_source(project_id, payload, user):
    await get_project(project_id, user, 'knowledge.manage')
    content_hash = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
    existing = await requirement_document_repository.find_by_hash(project_id, content_hash, user.id)
    if existing:
        return RequirementSourceResult(
            existing, existing.get("index_status") == 'INDEXED'
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
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await requirement_document_repository.insert(document)
    indexed = await index_artifact(
        project_id,
        "requirement_document",
        document["_id"],
        document["_id"],
        payload.title,
        payload.content,
        document["status"],
        payload.authority,
        payload.source_version,
        module=payload.module or "",
        component=payload.component,
        product_area=payload.product_area,
        release_id=payload.release_id,
        external_source_id=payload.external_source_id,
        approval_status=payload.approval_status,
        owner_id=payload.owner_id,
        approved_by=payload.approved_by,
        approved_at=payload.approved_at,
        effective_from=payload.effective_from,
        tags=payload.tags,
    )
    document["index_status"] = (
        'INDEXED' if indexed else 'FAILED'
    )
    document["indexed_at"] = now()
    await requirement_document_repository.set_index_result(
        document["_id"], project_id, document["index_status"], document["indexed_at"]
    )
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
    await get_project(project_id, user, 'knowledge.read')
    query = {"project_id": project_id}
    if not include_archived:
        query["status"] = {"$ne": 'ARCHIVED'}
    documents = await requirement_document_repository.list(query, 1000)
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
    document = await get_project_entity(
        'requirement_documents',
        document_id,
        user,
        'knowledge.manage',
    )
    if document.get("status") == 'ARCHIVED':
        raise HTTPException(
            status_code=409, detail={"code": 'KNOWLEDGE_SOURCE_ARCHIVED'}
        )
    content = str((document.get("raw_source") or {}).get("content") or "")
    indexed = await index_artifact(
        document["project_id"],
        "requirement_document",
        document["_id"],
        document["_id"],
        document.get("title") or document.get("filename") or "",
        content,
        document.get("status", 'READY'),
        document.get("authority"),
        document.get("source_version"),
        module=document.get("module") or "",
        component=document.get("component"),
        product_area=document.get("product_area"),
        release_id=document.get("release_id"),
        external_source_id=document.get("external_source_id"),
        approval_status=document.get("approval_status"),
        owner_id=document.get("owner_id"),
        approved_by=document.get("approved_by"),
        approved_at=document.get("approved_at"),
        effective_from=document.get("effective_from"),
        tags=document.get("tags", []),
    )
    timestamp = now()
    await requirement_document_repository.set_index_result(
        document_id,
        document["project_id"],
        'INDEXED'
        if indexed
        else 'FAILED',
        timestamp,
    )
    await requirement_document_repository.update(
        document_id,
        document["project_id"],
        {"updated_at": timestamp},
        increment_revision=True,
    )
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
    document = await get_project_entity(
        'requirement_documents', document_id, user, 'knowledge.manage'
    )
    await require_action_policy(
        document["project_id"],
        user,
        'knowledge.archive',
        set(['QA', 'BA']),
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
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    await audit(
        user.id,
        'knowledge_source_archived',
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"reason": payload.reason},
    )
    return updated
