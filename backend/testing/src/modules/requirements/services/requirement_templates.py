import hashlib
import json
import re

from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from src.core.ai_assistance import ai_contract_metadata, request_ai_assistance
from src.core.common import audit, get_project, get_project_role, new_id, now, plain_text
from src.modules.requirements.services.requirement_documents import require_document_access
from src.modules.requirements.services.requirement_import import api_operation_identifiers
from src.modules.requirements.services.requirement_import_workflow import create_requirement_preview_from_candidates
from src.modules.requirements.services.requirement_indexing import validate_requirement_api_operations, validate_requirement_sources
from src.modules.requirements.services.requirement_records import validate_requirement_custom_values
from src.modules.requirements.services.requirement_workflow import candidate_quality_issues, serialized_content, text_doc
from src.repositories.requirement_document import requirement_document_repository
from src.repositories.requirement_template import requirement_template_repository
from src.schemas.contracts.requirements import RequirementCreate, RequirementTemplateCreate


def starter_templates():
    return [
        {
            "_id": f"starter:{product_type}",
            "name": name,
            "description": description,
            "product_types": [product_type],
            "version": 1,
            "status": "STARTER",
            "context": {
                "objectives": "",
                "in_scope": "",
                "out_of_scope": "",
                "stakeholders": [],
                "actors_and_systems": [],
                "glossary": [],
                "assumptions": [],
            },
            "requirements": [],
        }
        for product_type, name, description in (
            ("web", "Mẫu yêu cầu ứng dụng web", "Bối cảnh và yêu cầu của ứng dụng web"),
            ("mobile", "Mẫu yêu cầu ứng dụng di động", "Bối cảnh và yêu cầu của ứng dụng di động"),
            ("api", "Mẫu yêu cầu API", "Bối cảnh và yêu cầu của API"),
        )
    ]


def public_view(template):
    value = template.get("public_template") or {}
    return {
        "_id": template["_id"],
        "name": value.get("name", template["name"]),
        "description": value.get("description", ""),
        "product_types": value.get("product_types", []),
        "context": value.get("context", {}),
        "requirements": value.get("requirements", []),
        "version": template["version"],
        "revision": template.get("revision", 1),
        "status": template.get("status", "PUBLISHED"),
        "source_template_ids": [],
        "source_document_ids": [],
    }


def pending_publication_view(template):
    return {
        **public_view(template),
        "project_id": template["project_id"],
        "source_document_ids": template.get("source_document_ids", []),
        "publication_source_document_ids": template.get("publication_source_document_ids", []),
        "consents": template.get("consents", {}),
        "publication_requested_by": template.get("publication_requested_by"),
    }


async def visible_template(template_id, project_id, user):
    if template_id.startswith("starter:"):
        template = next((item for item in starter_templates() if item["_id"] == template_id), None)
        if template:
            return template
        raise HTTPException(status_code=404, detail={"code": "TEMPLATE_NOT_FOUND"})
    template = await requirement_template_repository.find(template_id)
    if not template:
        raise HTTPException(status_code=404, detail={"code": "TEMPLATE_NOT_FOUND"})
    if template["project_id"] == project_id:
        try:
            await template_lineage_documents(project_id, template, user)
        except HTTPException:
            if template.get("status") == "PUBLISHED":
                return public_view(template)
            raise
        if template.get("status") == "PENDING_PUBLICATION":
            return {**template, "publication_source_document_ids": sorted(await template_lineage_documents(project_id, template))}
        return template
    if template.get("status") == "PUBLISHED":
        return public_view(template)
    raise HTTPException(status_code=404, detail={"code": "TEMPLATE_NOT_FOUND"})


async def list_templates(project_id, user):
    await get_project(project_id, user, "requirement.read")
    templates = await requirement_template_repository.list_visible(project_id)
    visible = starter_templates()
    for item in templates:
        if item["project_id"] != project_id:
            visible.append(public_view(item))
            continue
        try:
            await template_lineage_documents(project_id, item, user)
        except HTTPException:
            if item.get("status") == "PUBLISHED":
                visible.append(public_view(item))
                continue
            try:
                required_ids = sorted(await template_lineage_documents(project_id, item))
            except HTTPException:
                continue
            source_documents = await requirement_document_repository.list_by_ids(project_id, required_ids)
            if item.get("status") == "PENDING_PUBLICATION" and (
                await get_project_role(project_id, user.id) == "QA"
                or user.is_system_admin
                or any(document.get("created_by") == user.id for document in source_documents)
            ):
                visible.append(pending_publication_view({**item, "publication_source_document_ids": required_ids}))
            continue
        if item.get("status") == "PENDING_PUBLICATION":
            visible.append({**item, "publication_source_document_ids": sorted(await template_lineage_documents(project_id, item))})
        else:
            visible.append(item)
    return visible


async def list_template_versions(project_id, template_id, user):
    await get_project(project_id, user, "requirement.read")
    template = await requirement_template_repository.find(template_id)
    if not template:
        raise HTTPException(status_code=404, detail={"code": "TEMPLATE_NOT_FOUND"})
    if template.get("project_id") != project_id:
        if template.get("status") != "PUBLISHED":
            raise HTTPException(status_code=404, detail={"code": "TEMPLATE_NOT_FOUND"})
        return [{"template_id": template_id, "version": template["version"], "created_at": template.get("published_at")}]
    try:
        await template_lineage_documents(project_id, template, user)
    except HTTPException:
        if template.get("status") == "PUBLISHED":
            return [{"template_id": template_id, "version": template["version"], "created_at": template.get("published_at")}]
        raise
    return await requirement_template_repository.list_versions(template_id, project_id)


async def get_template_version(project_id, template_id, version, user):
    await get_project(project_id, user, "requirement.read")
    template = await requirement_template_repository.find(template_id)
    if not template:
        raise HTTPException(status_code=404, detail={"code": "TEMPLATE_VERSION_NOT_FOUND"})
    if template["project_id"] != project_id:
        if template.get("status") != "PUBLISHED" or template.get("version") != version:
            raise HTTPException(status_code=404, detail={"code": "TEMPLATE_VERSION_NOT_FOUND"})
        return public_view(template)
    saved = await requirement_template_repository.find_version(template_id, project_id, version)
    if not saved:
        raise HTTPException(status_code=404, detail={"code": "TEMPLATE_VERSION_NOT_FOUND"})
    snapshot = saved["snapshot"]
    try:
        await template_lineage_documents(project_id, snapshot, user)
    except HTTPException:
        if template.get("status") == "PUBLISHED" and template.get("version") == version:
            return public_view(template)
        raise
    return {"_id": template_id, **snapshot}


async def list_custom_fields(project_id, user):
    await get_project(project_id, user, "requirement.read")
    return await requirement_template_repository.list_fields(project_id)


async def create_custom_field(project_id, payload, user):
    await get_project(project_id, user, "project.update")
    if await get_project_role(project_id, user.id) != "QA" and not user.is_system_admin:
        raise HTTPException(status_code=403, detail={"code": "CUSTOM_FIELD_MANAGER_REQUIRED"})
    field = {"_id": new_id("RCF"), "project_id": project_id, **payload.model_dump(), "created_at": now(), "created_by": user.id}
    try:
        await requirement_template_repository.insert_field(field)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail={"code": "CUSTOM_FIELD_EXISTS"}) from error
    return field


async def validate_template_documents(project_id, document_ids, user, ai_required=False):
    documents = await requirement_document_repository.list_by_ids(project_id, list(dict.fromkeys(document_ids)))
    by_id = {item["_id"]: item for item in documents}
    if set(by_id) != set(document_ids):
        raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_MISSING"})
    for document in documents:
        await require_document_access(document, user, "requirement_document.read")
        if ai_required and not document.get("ai_enabled"):
            raise HTTPException(status_code=403, detail={"code": "DOCUMENT_AI_ACCESS_DISABLED", "document_id": document["_id"]})
    return documents


async def template_lineage_documents(project_id, template, user=None, ai_required=False, visited=None):
    if template.get("project_id") != project_id:
        return set()
    seen = visited if visited is not None else set()
    template_identity = (template.get("_id"), template.get("version"))
    if template_identity in seen:
        return set()
    seen.add(template_identity)
    document_ids = set(template.get("source_document_ids", []))
    if user:
        await validate_template_documents(project_id, document_ids, user, ai_required=ai_required)
    else:
        documents = await requirement_document_repository.list_by_ids(project_id, list(document_ids))
        if {document["_id"] for document in documents} != document_ids:
            raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_MISSING"})
    for source_id in template.get("source_template_ids", []):
        if source_id.startswith("starter:"):
            continue
        source = await requirement_template_repository.find(source_id)
        if not source or source.get("project_id") != project_id and source.get("status") != "PUBLISHED":
            raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_MISSING"})
        if source_id in template.get("source_template_public_ids", []):
            if source.get("status") != "PUBLISHED":
                raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_MISSING"})
            continue
        source_versions = template.get("source_template_versions", {}).get(source_id)
        for source_version in source_versions if isinstance(source_versions, list) else [source_versions]:
            source_snapshot = source
            if source_version is not None:
                saved = await requirement_template_repository.find_version(source_id, source["project_id"], source_version)
                if not saved:
                    raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_MISSING"})
                source_snapshot = {"_id": source_id, **saved["snapshot"]}
            document_ids.update(await template_lineage_documents(project_id, source_snapshot, user, ai_required, seen))
    return document_ids


async def validate_template_ai_sources(project_id, template, user, visited=None):
    return await template_lineage_documents(project_id, template, user, ai_required=True, visited=visited)


async def create_template(project_id, payload, user, synthesis=None):
    await get_project(project_id, user, "requirement.create")
    referenced_documents = {
        reference["requirement_document_id"]
        for requirement in payload.requirements
        for reference in requirement.source_refs
        if reference.get("requirement_document_id")
    }
    if referenced_documents - set(payload.source_document_ids):
        raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_NOT_DECLARED"})
    referenced_templates = {
        reference["template_id"]
        for requirement in payload.requirements
        for reference in requirement.source_refs
        if reference.get("template_id")
    }
    if referenced_templates - set(payload.source_template_ids):
        raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_NOT_DECLARED"})
    await validate_template_documents(project_id, payload.source_document_ids, user)
    source_template_versions = {}
    source_template_public_ids = []
    for template_id in payload.source_template_ids:
        source = await visible_template(template_id, project_id, user)
        referenced_versions = {
            reference.get("template_version")
            for requirement in payload.requirements
            for reference in requirement.source_refs
            if reference.get("template_id") == template_id
            and isinstance(reference.get("template_version"), int)
            and not isinstance(reference.get("template_version"), bool)
        }
        source_template_versions[template_id] = sorted(referenced_versions | {source["version"]})
        if template_id.startswith("starter:") or source.get("project_id") != project_id:
            source_template_public_ids.append(template_id)
    for requirement in payload.requirements:
        await validate_requirement_custom_values(project_id, requirement)
        await validate_requirement_sources(project_id, requirement.source_refs, user)
        await validate_requirement_api_operations(project_id, requirement.details, requirement.source_refs, user)
    template = {
        "_id": new_id("RTPL"),
        "project_id": project_id,
        **payload.model_dump(),
        "source_template_versions": source_template_versions,
        "source_template_public_ids": source_template_public_ids,
        "version": 1,
        "revision": 1,
        "status": "DRAFT",
        "consents": {},
        "synthesis": synthesis,
        "created_by": user.id,
        "created_at": now(),
        "updated_at": now(),
    }
    await template_lineage_documents(project_id, template, user)
    await requirement_template_repository.insert(template)
    await audit(user.id, "requirement_template_created", "RequirementTemplate", template["_id"], project_id)
    return template


async def update_template(project_id, template_id, payload, user):
    await get_project(project_id, user, "requirement.update")
    template = await visible_template(template_id, project_id, user)
    if template.get("project_id") != project_id or template.get("status") != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_NOT_EDITABLE"})
    referenced_documents = {
        reference["requirement_document_id"]
        for requirement in payload.requirements
        for reference in requirement.source_refs
        if reference.get("requirement_document_id")
    }
    if referenced_documents - set(payload.source_document_ids):
        raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_NOT_DECLARED"})
    referenced_templates = {
        reference["template_id"]
        for requirement in payload.requirements
        for reference in requirement.source_refs
        if reference.get("template_id")
    }
    if referenced_templates - set(payload.source_template_ids):
        raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_NOT_DECLARED"})
    await validate_template_documents(project_id, payload.source_document_ids, user)
    source_template_versions = {}
    source_template_public_ids = []
    for source_template_id in payload.source_template_ids:
        if source_template_id == template_id:
            raise HTTPException(status_code=422, detail={"code": "TEMPLATE_CIRCULAR_SOURCE"})
        source = await visible_template(source_template_id, project_id, user)
        prior_versions = template.get("source_template_versions", {}).get(source_template_id, [])
        if not isinstance(prior_versions, list):
            prior_versions = [prior_versions]
        referenced_versions = {
            reference.get("template_version")
            for requirement in payload.requirements
            for reference in requirement.source_refs
            if reference.get("template_id") == source_template_id
            and isinstance(reference.get("template_version"), int)
            and not isinstance(reference.get("template_version"), bool)
        }
        source_template_versions[source_template_id] = sorted(
            set(prior_versions) | referenced_versions or {source["version"]}
        )
        if source_template_id.startswith("starter:") or source.get("project_id") != project_id:
            source_template_public_ids.append(source_template_id)
    for requirement in payload.requirements:
        await validate_requirement_custom_values(project_id, requirement)
        await validate_requirement_sources(project_id, requirement.source_refs, user)
        await validate_requirement_api_operations(project_id, requirement.details, requirement.source_refs, user)
    synthesis = template.get("synthesis") or None
    if synthesis and synthesis.get("conflicts"):
        if len(payload.conflict_resolutions) != len(synthesis["conflicts"]) or any(not item.strip() for item in payload.conflict_resolutions):
            raise HTTPException(status_code=422, detail={"code": "TEMPLATE_CONFLICT_RESOLUTION_REQUIRED"})
        titles = set()
        contents = set()
        for requirement in payload.requirements:
            title = requirement.title.casefold().strip()
            content = plain_text(requirement.content_doc).casefold().strip()
            if title in titles or content in contents:
                raise HTTPException(status_code=422, detail={"code": "TEMPLATE_DUPLICATE_REQUIREMENT_UNRESOLVED"})
            titles.add(title)
            contents.add(content)
        for conflict, resolution in zip(synthesis["conflicts"], payload.conflict_resolutions):
            if conflict.get("reason") != "CONTEXT_SOURCE_CONFLICT":
                continue
            selected = payload.context.get(conflict["title"])
            selected_text = "\n".join(str(item) for item in selected) if isinstance(selected, list) else str(selected or "")
            if not selected_text.strip() or resolution.strip() != selected_text.strip():
                raise HTTPException(status_code=422, detail={"code": "TEMPLATE_CONTEXT_CONFLICT_UNRESOLVED", "field": conflict["title"]})
        synthesis = {**synthesis, "conflicts": [], "resolutions": payload.conflict_resolutions, "status": "REVIEWED"}
    changes = {**payload.model_dump(exclude={"expected_version", "conflict_resolutions"}), "source_template_versions": source_template_versions, "source_template_public_ids": source_template_public_ids, "updated_at": now(), "consents": {}, "synthesis": synthesis}
    await template_lineage_documents(project_id, {**template, **changes}, user)
    updated = await requirement_template_repository.update(template_id, payload.expected_version, changes)
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_VERSION_CONFLICT"})
    await audit(user.id, "requirement_template_updated", "RequirementTemplate", template_id, project_id, {"version": updated["version"]})
    return updated


async def preview_template(project_id, template_id, user):
    await get_project(project_id, user, "requirement.create")
    template = await visible_template(template_id, project_id, user)
    if template.get("status") == "STARTER" or not template.get("requirements"):
        raise HTTPException(status_code=422, detail={"code": "TEMPLATE_HAS_NO_REQUIREMENTS"})
    if (template.get("synthesis") or {}).get("conflicts"):
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_CONFLICT_REQUIRES_REVIEW"})
    candidates = []
    for item in template["requirements"]:
        requirement = RequirementCreate(**item)
        await validate_requirement_custom_values(project_id, requirement)
        await validate_requirement_sources(project_id, requirement.source_refs, user)
        await validate_requirement_api_operations(project_id, requirement.details, requirement.source_refs, user)
        source_refs = [
            {key: value for key, value in reference.items() if key != "source_quote"}
            for reference in requirement.source_refs
        ]
        source_refs.append({"template_id": template_id, "template_version": template["version"]})
        candidate = requirement.model_dump()
        candidate["source_refs"] = source_refs
        candidate["quality_issues"] = candidate_quality_issues(candidate)
        if "REQUIREMENT_CONTENT_MISSING" in candidate["quality_issues"]:
            raise HTTPException(status_code=422, detail={"code": "TEMPLATE_REQUIREMENT_INCOMPLETE"})
        candidates.append(candidate)
    return await create_requirement_preview_from_candidates(project_id, template["name"], candidates, user, template_id=template_id, template_version=template["version"], template_public_view=template.get("project_id") != project_id)


async def review_template(project_id, template_id, user):
    await get_project(project_id, user, "requirement.read")
    template = await visible_template(template_id, project_id, user)
    if template.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail={"code": "TEMPLATE_NOT_FOUND"})
    document_ids = await validate_template_ai_sources(project_id, template, user)
    documents = await validate_template_documents(project_id, sorted(document_ids), user, ai_required=True)
    template_evidence = []
    document_evidence = []
    document_text = {}
    template_text = serialized_content({
        "context": template.get("context", {}),
        "requirements": template.get("requirements", []),
    })
    for start in range(0, len(template_text), 3500):
        template_evidence.append({
            "artifact_type": "requirement_template",
            "artifact_version_id": f"{template_id}:{template['version']}:{start}",
            "text": template_text[start:start + 3500],
        })
    for document in documents:
        content = document.get("normalized_content")
        if content is None:
            continue
        text = content if isinstance(content, str) else plain_text(content) or serialized_content(content)
        for start in range(0, len(text), 3500):
            reference = f"{document['_id']}:{start}"
            document_evidence.append({
                "artifact_type": "requirement_document",
                "artifact_version_id": reference,
                "text": text[start:start + 3500],
            })
            document_text[reference] = text[start:start + 3500]
    evidence = template_evidence + document_evidence
    if len(evidence) <= 8:
        batches = [evidence]
    else:
        batches = [template_evidence[start:start + 8] for start in range(0, len(template_evidence), 8)]
        batches.extend(
            [template_evidence[0], *document_evidence[start:start + 7]]
            for start in range(0, len(document_evidence), 7)
        )
    findings = []
    results = []
    for batch in batches:
        result = await request_ai_assistance(
            "requirement_template_review",
            project_id,
            "Rà soát phần mẫu Requirements được cung cấp bằng tiếng Việt  Chỉ nêu mục còn thiếu khi tài liệu chứng minh mục đó áp dụng cho yêu cầu cụ thể và sự thiếu sót cản trở việc nhập  Mục không xuất hiện trong nguồn không mặc nhiên là bắt buộc  Nêu mâu thuẫn và chỉ trích nguyên văn tài liệu được phép cho AI đọc  Viết nhận xét bằng tiếng Việt không dùng tên trường nội bộ  Nếu không có đủ mẫu trong phần này thì không kết luận toàn bộ mẫu đã sẵn sàng  Không tự sửa mẫu",
            batch,
        )
        if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
            raise HTTPException(status_code=503, detail={"code": "TEMPLATE_REVIEW_UNAVAILABLE", "warnings": result.get("warnings", [])})
        if result.get("readiness") not in {"ready_for_import", "needs_information", "conflict"}:
            raise HTTPException(status_code=502, detail={"code": "TEMPLATE_REVIEW_INVALID"})
        allowed = {item["artifact_version_id"] for item in batch}
        for finding in result.get("findings") or []:
            refs = finding.get("evidence_refs") or []
            index = finding.get("requirement_index")
            if not refs or not set(refs) <= allowed or index is not None and not 0 <= index < len(template.get("requirements", [])):
                raise HTTPException(status_code=502, detail={"code": "TEMPLATE_REVIEW_INVALID"})
            quote = finding.get("suggested_source_quote")
            if quote and not any(quote in document_text.get(reference, "") for reference in refs):
                raise HTTPException(status_code=502, detail={"code": "TEMPLATE_REVIEW_UNSUPPORTED_SUGGESTION"})
            findings.append(finding)
        results.append(result)
    readiness = (
        "conflict" if any(item["readiness"] == "conflict" for item in results)
        else "needs_information" if len(batches) > 1 or any(item["readiness"] == "needs_information" for item in results)
        else "ready_for_import"
    )
    if not template.get("requirements") or any(
        "REQUIREMENT_CONTENT_MISSING" in candidate_quality_issues(item)
        for item in template["requirements"]
    ):
        readiness = "needs_information"
    if (template.get("synthesis") or {}).get("conflicts"):
        readiness = "conflict"
    metadata = ai_contract_metadata(results[0])
    metadata["evidence_refs"] = list(dict.fromkeys(reference for item in results for reference in item.get("evidence_refs", [])))
    metadata["warnings"] = list(dict.fromkeys(
        [warning for item in results for warning in item.get("warnings", [])]
        + (["BATCHED_REVIEW_REQUIRES_HUMAN_RECONCILIATION"] if len(batches) > 1 else [])
    ))
    metadata["confidence"] = min(item.get("confidence", 0) for item in results)
    return {"readiness": readiness, "findings": findings, "reviewed_parts": len(batches), **metadata}


async def synthesize_template(project_id, payload, user):
    await get_project(project_id, user, "requirement.create")
    documents = await validate_template_documents(project_id, payload.source_document_ids, user, ai_required=True)
    templates = [await visible_template(item, project_id, user) for item in payload.source_template_ids]
    for template in templates:
        await validate_template_ai_sources(project_id, template, user)
    if not documents and templates and all(not item.get("requirements") for item in templates):
        context = {}
        conflicts = []
        for template in templates:
            for key, value in template.get("context", {}).items():
                if not value:
                    continue
                if key in context and context[key] != value:
                    conflicts.append({"title": key, "reason": "CONTEXT_SOURCE_CONFLICT", "values": [context[key], value]})
                else:
                    context[key] = value
        data = RequirementTemplateCreate(name=payload.name, product_types=payload.product_types, context=context, source_template_ids=payload.source_template_ids)
        return await create_template(project_id, data, user, synthesis={"status": "REVIEW_REQUIRED", "conflicts": conflicts, "warnings": ["SOURCE_TEMPLATES_HAVE_NO_REQUIREMENTS"], "evidence_refs": payload.source_template_ids})
    evidence = []
    evidence_lookup = {}
    total_chunks = 0
    for document in documents:
        content = document.get("normalized_content")
        text = serialized_content(content) if content is not None else ""
        total_chunks += (len(text) + 3499) // 3500
        for start in range(0, len(text), 3500):
            reference = f"{document['_id']}:{start}"
            chunk = text[start:start + 3500]
            evidence.append({"artifact_type": f"requirement_document:{document.get('source_type', 'REFERENCE')}", "artifact_id": reference, "authority": document.get("authority", "PROJECT_REFERENCE"), "text": chunk})
            evidence_lookup[reference] = (document, start, chunk)
    for template in templates:
        serialized = json.dumps({"context": template.get("context"), "requirements": template.get("requirements")}, ensure_ascii=False, default=str)
        total_chunks += (len(serialized) + 3499) // 3500
    if total_chunks > 100:
        raise HTTPException(status_code=413, detail={"code": "TEMPLATE_SOURCE_TOO_LARGE"})
    for template in templates:
        serialized = json.dumps({"context": template.get("context"), "requirements": template.get("requirements")}, ensure_ascii=False, default=str)
        for start in range(0, len(serialized), 3500):
            reference = f"{template['_id']}:{start}"
            evidence.append({"artifact_type": "requirement_template", "artifact_id": reference, "authority": "PROJECT_REFERENCE", "text": serialized[start:start + 3500]})
            evidence_lookup[reference] = (template, None, None)
    if not evidence:
        raise HTTPException(status_code=422, detail={"code": "TEMPLATE_SOURCE_EMPTY"})
    results = []
    for start in range(0, len(evidence), 8):
        result = await request_ai_assistance("requirement_template_synthesis", project_id, payload.instruction or "Tổng hợp mẫu yêu cầu bằng tiếng Việt và nêu rõ thông tin còn thiếu hoặc mâu thuẫn", evidence[start:start + 8])
        if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
            raise HTTPException(status_code=503, detail={"code": "TEMPLATE_SYNTHESIS_UNAVAILABLE", "warnings": result.get("warnings", [])})
        results.append(result)
    requirements = []
    source_field_warnings = []
    api_operation_cache = {}
    conflicts = [item for result in results for item in result.get("conflicts", [])]
    evidence_text_by_ref = {item["artifact_id"]: item["text"] for item in evidence}
    for suggestion in (item for result in results for item in result.get("suggestions", [])):
        refs = []
        if any(reference not in evidence_lookup for reference in suggestion.get("evidence_refs", [])):
            raise HTTPException(status_code=502, detail={"code": "TEMPLATE_EVIDENCE_INVALID"})
        cited_text = "\n".join(evidence_text_by_ref.get(reference, "") for reference in suggestion.get("evidence_refs", []))
        verified_lists = {}
        omitted_sections = set()
        for key in ("acceptance_criteria", "actors", "business_rules", "dependencies"):
            verified_lists[key] = [
                value
                for value in suggestion.get(key, [])
                if str(value).casefold() in cited_text.casefold()
            ]
            if len(verified_lists[key]) != len(suggestion.get(key, [])):
                omitted_sections.add(key)
        details = {}
        for key in ("main_flow", "exception_flow", "data_rules", "integration", "quality_measure"):
            value = suggestion.get(key)
            if value:
                if str(value).casefold() not in cited_text.casefold():
                    omitted_sections.add(key)
                    continue
                details[key] = value
        story = {}
        for key in ("actor", "goal", "value"):
            value = suggestion.get(f"user_story_{key}")
            if value:
                if str(value).casefold() not in cited_text.casefold():
                    omitted_sections.add(f"user_story.{key}")
                    continue
                story[key] = value
        if story:
            if not any(
                evidence_lookup[reference][0].get("source_type") == "USER_STORY"
                or evidence_lookup[reference][0].get("context", {}).get("source_type") == "USER_STORY"
                for reference in suggestion.get("evidence_refs", [])
            ):
                omitted_sections.update(f"user_story.{key}" for key in story)
            else:
                details["user_story"] = story
        api_links = []
        for operation in suggestion.get("api_operations", []):
            reference = operation.get("source_ref")
            if reference not in suggestion.get("evidence_refs", []) or reference not in evidence_lookup:
                raise HTTPException(status_code=502, detail={"code": "TEMPLATE_API_OPERATION_INVALID"})
            source, start, _ = evidence_lookup[reference]
            if start is None or source.get("format") not in ("openapi", "postman"):
                raise HTTPException(status_code=502, detail={"code": "TEMPLATE_API_OPERATION_INVALID"})
            if source["_id"] not in api_operation_cache:
                api_operation_cache[source["_id"]] = api_operation_identifiers(source.get("normalized_content"), source["format"])
            claimed = {key: value for key, value in operation.items() if key != "source_ref" and value is not None}
            claimed["method"] = claimed["method"].upper()
            matches = [
                item for item in api_operation_cache[source["_id"]]
                if all(item.get(key) == value for key, value in claimed.items())
            ]
            if len(matches) != 1:
                raise HTTPException(status_code=502, detail={"code": "TEMPLATE_API_OPERATION_INVALID"})
            link = {"requirement_document_id": source["_id"], **matches[0]}
            if link not in api_links:
                api_links.append(link)
        if api_links:
            details["api_operations"] = api_links
        for reference in suggestion.get("evidence_refs", []):
            if reference not in evidence_lookup:
                raise HTTPException(status_code=502, detail={"code": "TEMPLATE_EVIDENCE_INVALID"})
            source, start, chunk = evidence_lookup[reference]
            if start is None:
                refs.append({"template_id": source["_id"], "template_version": source["version"]})
            else:
                quote = str((suggestion.get("source_quotes") or {}).get(reference) or "").strip()
                if not quote or quote not in chunk:
                    raise HTTPException(status_code=502, detail={"code": "TEMPLATE_SOURCE_QUOTE_INVALID"})
                offset = chunk.index(quote)
                span_start = offset
                span_end = offset + len(quote)
                evidence_values = [suggestion.get("content")]
                evidence_values.extend(value for values in verified_lists.values() for value in values)
                evidence_values.extend(value for value in details.values() if isinstance(value, str))
                evidence_values.extend(story.values())
                for value in evidence_values:
                    if not value:
                        continue
                    match = re.search(re.escape(str(value)), chunk, flags=re.IGNORECASE)
                    if match:
                        span_start = min(span_start, match.start())
                        span_end = max(span_end, match.end())
                quote = chunk[span_start:span_end]
                refs.append({"requirement_document_id": source["_id"], "content_hash": source["content_hash"], "source_version": source.get("source_version"), "source_start": start + span_start, "source_end": start + span_end, "source_text_hash": hashlib.sha256(quote.encode("utf-8")).hexdigest(), "source_quote": quote})
        if not refs:
            raise HTTPException(status_code=502, detail={"code": "TEMPLATE_EVIDENCE_MISSING"})
        try:
            section_states = {key: "missing" for key in suggestion.get("missing_sections", [])}
            section_states.update({key: "not_applicable" for key in suggestion.get("not_applicable_sections", [])})
            section_states.update({key: "missing" for key in omitted_sections})
            section_states.update({key: "provided" for key, values in verified_lists.items() if values})
            section_states.update({key: "provided" for key in details})
            requirements.append(RequirementCreate(title=suggestion["title"], type=suggestion["type"], content_doc=text_doc(suggestion["content"]), acceptance_criteria=[{"key": f"AC-{index + 1}", "content_doc": text_doc(value)} for index, value in enumerate(verified_lists["acceptance_criteria"])], actors=verified_lists["actors"], business_rules=verified_lists["business_rules"], dependencies=verified_lists["dependencies"], details=details, source_refs=refs, section_states=section_states))
            if omitted_sections:
                source_field_warnings.append("Một số mục AI đề xuất không có nguyên văn trong nguồn nên đã bị bỏ qua  Hãy rà soát mẫu")
        except (KeyError, ValidationError) as error:
            raise HTTPException(status_code=502, detail={"code": "TEMPLATE_AI_OUTPUT_INVALID"}) from error
    if not requirements:
        raise HTTPException(status_code=502, detail={"code": "TEMPLATE_AI_NO_REQUIREMENTS"})
    if len(requirements) > 100:
        raise HTTPException(status_code=422, detail={"code": "TEMPLATE_TOO_MANY_REQUIREMENTS"})
    titles = {}
    contents = {}
    for requirement in requirements:
        key = requirement.title.casefold().strip()
        content_key = plain_text(requirement.content_doc).casefold().strip()
        if key in titles:
            conflicts.append({"title": requirement.title, "reason": "DUPLICATE_TITLE_SAME_CONTENT" if plain_text(titles[key].content_doc).casefold().strip() == content_key else "DUPLICATE_TITLE_DIFFERENT_CONTENT"})
        elif content_key in contents:
            conflicts.append({"title": requirement.title, "reason": "DUPLICATE_CONTENT_DIFFERENT_TITLE"})
        titles[key] = requirement
        contents[content_key] = requirement
    context = {}
    context_warnings = []
    all_evidence_text = "\n".join(item["text"] for item in evidence).casefold()
    for result in results:
        for key, value in (result.get("context") or {}).items():
            if (
                key not in starter_templates()[0]["context"]
                or not isinstance(value, (str, list))
                or isinstance(value, list)
                and any(not isinstance(item, str) for item in value)
            ):
                context_warnings.append("TEMPLATE_CONTEXT_FIELD_IGNORED")
                continue
            values = value if isinstance(value, list) else [value]
            if any(str(item).casefold() not in all_evidence_text for item in values if item):
                context_warnings.append("TEMPLATE_CONTEXT_NOT_IN_SOURCE")
                continue
            if key in context and context[key] and value and context[key] != value:
                conflicts.append({"title": key, "reason": "CONTEXT_SOURCE_CONFLICT", "values": [context[key], value]})
            elif value:
                context[key] = value
    data = RequirementTemplateCreate(name=payload.name, product_types=payload.product_types, context=context, requirements=requirements, source_document_ids=payload.source_document_ids, source_template_ids=payload.source_template_ids)
    return await create_template(project_id, data, user, synthesis={"status": "REVIEW_REQUIRED", "conflicts": conflicts, "warnings": list(dict.fromkeys([item for result in results for item in result.get("warnings", [])] + context_warnings + source_field_warnings)), "evidence_refs": list(dict.fromkeys(item for result in results for item in result.get("evidence_refs", [])))})


async def request_publication(project_id, template_id, payload, user):
    await get_project(project_id, user, "requirement.update")
    template = await visible_template(template_id, project_id, user)
    if template.get("project_id") != project_id or template.get("status") != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_NOT_PUBLISHABLE"})
    if payload.expected_version != template["version"]:
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_VERSION_CONFLICT"})
    if payload.public_template.source_document_ids or payload.public_template.source_template_ids:
        raise HTTPException(status_code=422, detail={"code": "PUBLIC_TEMPLATE_CANNOT_REFERENCE_PRIVATE_SOURCES"})
    if not payload.public_template.requirements or any(
        not plain_text(item.content_doc).strip() for item in payload.public_template.requirements
    ):
        raise HTTPException(status_code=422, detail={"code": "PUBLIC_TEMPLATE_INCOMPLETE"})
    public_data = payload.public_template.model_dump()
    for item in public_data["requirements"]:
        if item.get("source_refs") or item.get("owner_id") or item.get("custom_values"):
            raise HTTPException(status_code=422, detail={"code": "PUBLIC_TEMPLATE_PRIVATE_METADATA"})
    required_ids = sorted(await template_lineage_documents(project_id, template))
    updated = await requirement_template_repository.update_state(template_id, template["revision"], {"status": "PENDING_PUBLICATION", "public_template": public_data, "publication_source_document_ids": required_ids, "consents": {}, "publication_requested_by": user.id, "updated_at": now()})
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_VERSION_CONFLICT"})
    await audit(user.id, "requirement_template_publication_requested", "RequirementTemplate", template_id, project_id)
    return updated


async def consent_publication(project_id, template_id, payload, user):
    await get_project(project_id, user, "requirement_document.read")
    template = await requirement_template_repository.find(template_id)
    if not template or template.get("project_id") != project_id or template.get("status") != "PENDING_PUBLICATION":
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_CONSENT_INVALID"})
    required_ids = sorted(await template_lineage_documents(project_id, template))
    if payload.document_id not in required_ids:
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_CONSENT_INVALID"})
    document = await requirement_document_repository.find(payload.document_id, project_id)
    if not document or document.get("created_by") != user.id:
        raise HTTPException(status_code=403, detail={"code": "DOCUMENT_OWNER_REQUIRED"})
    consents = {**template.get("consents", {}), payload.document_id: {"approved": payload.approved, "by": user.id, "at": now()}}
    updated = await requirement_template_repository.update_state(template_id, template["revision"], {"consents": consents, "updated_at": now()})
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_VERSION_CONFLICT"})
    await audit(user.id, "requirement_template_source_consent", "RequirementTemplate", template_id, project_id, {"document_id": payload.document_id, "approved": payload.approved})
    return pending_publication_view({**updated, "publication_source_document_ids": required_ids})


async def approve_publication(project_id, template_id, user):
    await get_project(project_id, user, "project.update")
    if await get_project_role(project_id, user.id) != "QA" and not user.is_system_admin:
        raise HTTPException(status_code=403, detail={"code": "TEMPLATE_APPROVER_REQUIRED"})
    template = await requirement_template_repository.find(template_id)
    if not template or template.get("project_id") != project_id or template.get("status") != "PENDING_PUBLICATION" or template.get("publication_requested_by") == user.id:
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_APPROVAL_INVALID"})
    required_ids = await template_lineage_documents(project_id, template)
    if any(not template.get("consents", {}).get(document_id, {}).get("approved") for document_id in required_ids):
        raise HTTPException(status_code=409, detail={"code": "DOCUMENT_OWNER_CONSENT_REQUIRED"})
    updated = await requirement_template_repository.update_state(template_id, template["revision"], {"status": "PUBLISHED", "published_by": user.id, "published_at": now(), "updated_at": now()})
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "TEMPLATE_VERSION_CONFLICT"})
    await audit(user.id, "requirement_template_published", "RequirementTemplate", template_id, project_id)
    return updated
