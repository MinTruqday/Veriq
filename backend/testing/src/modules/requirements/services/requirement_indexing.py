import hashlib

from fastapi import HTTPException

from src.core.common import now
from src.repositories.requirement_document import requirement_document_repository
from src.repositories.requirement_template import requirement_template_repository
from src.clients.project_knowledge import index_artifact
from src.modules.requirements.services.requirement_import import source_document_text





async def validate_requirement_sources(project_id, source_refs, user):
    from src.modules.requirements.services.requirement_documents import require_document_access
    from src.modules.requirements.services.requirement_templates import get_template_version

    template_references = [item for item in source_refs or [] if item.get("template_id")]
    for reference in template_references:
        template_id = reference["template_id"]
        version = reference.get("template_version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_TEMPLATE_VERSION_INVALID"})
        template = await requirement_template_repository.find(template_id)
        if not template or (template.get("project_id") != project_id and template.get("status") != "PUBLISHED"):
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_TEMPLATE_SOURCE_UNAVAILABLE"})
        if not await requirement_template_repository.find_version(template_id, template["project_id"], version):
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_TEMPLATE_VERSION_MISSING"})
        await get_template_version(project_id, template_id, version, user)
    references = [item for item in source_refs or [] if item.get("requirement_document_id")]
    if not references:
        return
    document_ids = list(dict.fromkeys(item["requirement_document_id"] for item in references))
    documents = await requirement_document_repository.list_by_ids(project_id, document_ids)
    by_id = {item["_id"]: item for item in documents}
    if set(by_id) != set(document_ids):
        raise HTTPException(
            status_code=422,
            detail={"code": 'CROSS_PROJECT_OR_MISSING_REQUIREMENT_DOCUMENT'},
        )
    for reference in references:
        document = by_id[reference["requirement_document_id"]]
        await require_document_access(document, user, "requirement_document.read")
        if reference.get("source_quote") is not None and not reference.get("source_text_hash"):
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_SOURCE_QUOTE_MISMATCH"})
        expected_hash = reference.get("content_hash")
        if expected_hash and expected_hash != document.get("content_hash"):
            raise HTTPException(
                status_code=422,
                detail={"code": 'REQUIREMENT_SOURCE_HASH_MISMATCH'},
            )
        if reference.get("source_version") and reference["source_version"] != document.get("source_version"):
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_SOURCE_VERSION_MISMATCH"})
        if reference.get("source_text_hash"):
            content = document.get("normalized_content")
            if content is None:
                raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_SOURCE_SPAN_UNAVAILABLE"})
            content = source_document_text(content)
            start = reference.get("source_start")
            end = reference.get("source_end")
            if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end > len(content) or start >= end:
                raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_SOURCE_SPAN_INVALID"})
            if hashlib.sha256(content[start:end].encode("utf-8")).hexdigest() != reference["source_text_hash"]:
                raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_SOURCE_TEXT_MISMATCH"})
            if reference.get("source_quote") is not None and reference["source_quote"] != content[start:end]:
                raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_SOURCE_QUOTE_MISMATCH"})


async def validate_requirement_api_operations(project_id, details, source_refs, user):
    from src.modules.requirements.services.requirement_documents import require_document_access
    from src.modules.requirements.services.requirement_import import api_operation_identifiers

    links = details.get("api_operations", []) if isinstance(details, dict) else []
    if not links:
        return
    if not isinstance(links, list) or len(links) > 50:
        raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_API_OPERATION_INVALID"})
    document_ids = {item.get("requirement_document_id") for item in source_refs or [] if isinstance(item, dict)}
    cache = {}
    for link in links:
        if not isinstance(link, dict) or not isinstance(link.get("method"), str):
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_API_OPERATION_INVALID"})
        document_id = link.get("requirement_document_id")
        if not isinstance(document_id, str) or document_id not in document_ids:
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_API_OPERATION_SOURCE_MISSING"})
        if document_id not in cache:
            document = await requirement_document_repository.find(document_id, project_id)
            if not document or document.get("format") not in ("openapi", "postman"):
                raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_API_OPERATION_SOURCE_INVALID"})
            await require_document_access(document, user, "requirement_document.read")
            cache[document_id] = api_operation_identifiers(document.get("normalized_content"), document["format"])
        identity = {key: value for key, value in link.items() if key != "requirement_document_id"}
        if not (isinstance(identity.get("path"), str) or isinstance(identity.get("url_template"), str)):
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_API_OPERATION_INVALID"})
        if not any(identity == operation for operation in cache[document_id]):
            raise HTTPException(status_code=422, detail={"code": "REQUIREMENT_API_OPERATION_NOT_IN_SOURCE"})


async def index_requirement_version(version):
    criteria = await requirement_document_repository.list_acceptance_criterion_ids(
        version["project_id"], version["_id"]
    )
    source_document_ids = list(
        dict.fromkeys(
            item.get("requirement_document_id")
            for item in version.get("source_refs", [])
            if item.get("requirement_document_id")
        )
    )
    indexed = await index_artifact(
        version["project_id"],
        'requirement_version',
        version["requirement_id"],
        version["_id"],
        version["title"],
        version.get("plain_text_projection", ""),
        version.get("status", 'DRAFT'),
        'APPROVED_SOURCE'
        if version.get("status") == 'BASELINED'
        else 'DRAFT',
        version.get("version"),
        acceptance_criterion_ids=[item["_id"] for item in criteria],
        source_document_ids=source_document_ids,
    )
    await requirement_document_repository.set_requirement_version_index_result(
        version["_id"],
        'READY'
        if indexed
        else 'FAILED',
        None if indexed else 'KNOWLEDGE_INDEX_FAILED',
        now(),
    )
    return indexed
