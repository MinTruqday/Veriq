from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    next_key,
    now,
    page_payload,
    plain_text,
    sort_spec,
    validate_doc,
)
from src.repositories.requirement import requirement_repository
from src.repositories.requirement_template import requirement_template_repository
from src.schemas.contracts.requirements import RequirementCreate
from src.modules.requirements.services.requirement_indexing import (
    index_requirement_version,
    validate_requirement_api_operations,
    validate_requirement_sources,
)



async def persist_acceptance_criteria(version, values):
    criteria = []
    keys = [value.key if hasattr(value, "key") else value.get("key") for value in values]
    if len(keys) != len(set(keys)):
        raise HTTPException(
            status_code=422, detail={"code": 'DUPLICATE_ACCEPTANCE_CRITERION_KEY'}
        )
    for value in values:
        item = value.model_dump() if hasattr(value, "model_dump") else dict(value)
        if (
            version.get("status") == 'DRAFT'
            and item.get("status") != 'obsolete'
        ):
            item["status"] = 'draft'
        validate_doc(item["content_doc"])
        criterion = {
            "_id": new_id('AC'),
            "project_id": version["project_id"],
            "requirement_version_id": version["_id"],
            **item,
            "plain_text": plain_text(item["content_doc"]),
            "created_at": now(),
        }
        criteria.append(criterion)
    criterion_ids = [item["_id"] for item in criteria]
    await requirement_repository.insert_acceptance_criteria(criteria)
    await requirement_repository.set_acceptance_criterion_ids(version["_id"], criterion_ids)
    version["acceptance_criterion_ids"] = criterion_ids
    version["acceptance_criteria"] = criteria
    return version


async def validate_requirement_custom_values(project_id, requirement):
    values = requirement.custom_values or {}
    fields = await requirement_template_repository.list_fields(project_id)
    definitions = {field["key"]: field for field in fields}
    if set(values) - set(definitions):
        raise HTTPException(status_code=422, detail={"code": "UNKNOWN_CUSTOM_FIELD"})
    for field in fields:
        if field.get("requirement_types") and requirement.type not in field["requirement_types"]:
            if field["key"] in values:
                raise HTTPException(status_code=422, detail={"code": "CUSTOM_FIELD_NOT_APPLICABLE", "field": field["key"]})
            continue
        value = values.get(field["key"])
        if field["required"] and value in (None, ""):
            raise HTTPException(status_code=422, detail={"code": "CUSTOM_FIELD_REQUIRED", "field": field["key"]})
        if value is None:
            continue
        valid = (
            field["value_type"] in ("text", "date") and isinstance(value, str)
            or field["value_type"] == "number" and isinstance(value, (int, float)) and not isinstance(value, bool)
            or field["value_type"] == "boolean" and isinstance(value, bool)
            or field["value_type"] == "choice" and isinstance(value, str) and value in field["choices"]
        )
        if not valid:
            raise HTTPException(status_code=422, detail={"code": "CUSTOM_FIELD_INVALID", "field": field["key"]})


async def create_requirement_record(project_id, payload, user, origin="manual"):
    await get_project(project_id, user, "requirement.create")
    await validate_requirement_custom_values(project_id, payload)
    await validate_requirement_sources(project_id, payload.source_refs, user)
    await validate_requirement_api_operations(project_id, payload.details, payload.source_refs, user)
    validate_doc(payload.content_doc)
    requirement_key = payload.requirement_key or await next_key(
        project_id, 'requirement', 'REQ'
    )
    timestamp = now()
    requirement_id = new_id('REQ')
    version = {
        "_id": new_id('REQV'),
        "project_id": project_id,
        "requirement_id": requirement_id,
        "requirement_key": requirement_key,
        "version": 1,
        "title": payload.title,
        "type": payload.type,
        "priority": payload.priority,
        "risk": payload.risk,
        "content_doc": payload.content_doc,
        "plain_text_projection": plain_text(payload.content_doc),
        "business_rules": payload.business_rules,
        "actors": payload.actors,
        "dependencies": payload.dependencies,
        "source_refs": payload.source_refs,
        "tags": payload.tags,
        "owner_id": payload.owner_id or user.id,
        "details": payload.details,
        "section_states": payload.section_states,
        "custom_values": payload.custom_values,
        "acceptance_criterion_ids": [],
        "parent_version_id": None,
        "change_reason": 'Khởi tạo Requirement',
        "status": 'DRAFT',
        "revision": 1,
        "origin": origin,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    requirement = {
        "_id": requirement_id,
        "project_id": project_id,
        "requirement_key": requirement_key,
        "current_version_id": version["_id"],
        "status": 'DRAFT',
        "owner_id": payload.owner_id or user.id,
        "tags": payload.tags,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await requirement_repository.insert_requirement(requirement)
        await requirement_repository.insert_version(version)
    except DuplicateKeyError:
        await requirement_repository.delete_requirement(requirement_id)
        raise HTTPException(status_code=409, detail={"code": 'REQUIREMENT_KEY_EXISTS'})
    try:
        await persist_acceptance_criteria(version, payload.acceptance_criteria)
    except Exception:
        await requirement_repository.delete_acceptance_criteria(version["_id"])
        await requirement_repository.delete_version(version["_id"], project_id)
        await requirement_repository.delete_requirement(requirement_id, project_id)
        raise
    await index_requirement_version(version)
    await audit(user.id, "requirement_created", "Requirement", requirement_id, project_id)
    return {**requirement, "current_version": version}


async def list_requirement_records(
    project_id,
    user,
    q="",
    key="",
    title="",
    status="",
    owner="",
    tag="",
    coverage="",
    source_type="",
    has_pending_impact=None,
    page=1,
    page_size=50,
    sort="-updated_at",
):
    await get_project(project_id, user, "requirement.read")
    requirements = await requirement_repository.list_requirements(
        project_id, status, 20000
    )
    version_ids = [
        item.get("current_version_id") for item in requirements if item.get("current_version_id")
    ]
    versions = await requirement_repository.list_versions_by_ids(
        project_id, version_ids, 20000
    )
    by_id = {item["_id"]: item for item in versions}
    items = [
        {**item, "current_version": by_id.get(item.get("current_version_id"))}
        for item in requirements
    ]
    confirmed_links = await requirement_repository.list_confirmed_trace_sources(
        project_id,
        version_ids,
        'CONFIRMED',
        'requirement_version',
        50000,
    )
    covered_ids = {item["source_id"] for item in confirmed_links}
    change_sets = await requirement_repository.list_pending_change_targets(
        project_id,
        version_ids,
        ['REVIEWED', 'CLOSED', 'REJECTED'],
        20000,
    )
    pending_ids = {item["to_version_id"] for item in change_sets}
    for item in items:
        version = item.get("current_version") or {}
        item["owner_id"] = item.get("owner_id") or version.get("owner_id")
        item["tags"] = sorted(set(item.get("tags", [])) | set(version.get("tags", [])))
        item["covered"] = item.get("current_version_id") in covered_ids
        item["has_pending_impact"] = item.get("current_version_id") in pending_ids
        item["source_types"] = sorted(
            {
                str(ref.get("source_type") or ref.get("type") or "manual")
                for ref in version.get("source_refs", [])
            }
        )
    terms = [value.strip().lower() for value in (q, key, title) if value.strip()]
    if terms:
        items = [
            item
            for item in items
            if all(
                value
                in f"{item.get('requirement_key', '')} {(item.get('current_version') or {}).get('title', '')}".lower()
                for value in terms
            )
        ]
    if owner:
        items = [item for item in items if item.get("owner_id") == owner]
    if tag:
        items = [item for item in items if tag in item.get("tags", [])]
    if coverage:
        normalized = coverage.lower()
        if normalized not in {"covered", "uncovered"}:
            raise HTTPException(
                status_code=422, detail={"code": 'INVALID_COVERAGE_FILTER'}
            )
        items = [item for item in items if item.get("covered") is (normalized == "covered")]
    if source_type:
        items = [item for item in items if source_type in item.get("source_types", [])]
    if has_pending_impact is not None:
        items = [item for item in items if item.get("has_pending_impact") is has_pending_impact]
    sort_field, direction = sort_spec(
        sort, {"requirement_key", "status", "updated_at", "created_at", "title", "owner_id"}
    )
    items.sort(
        key=lambda item: str(
            (item.get("current_version") or {}).get(sort_field, item.get(sort_field, "")) or ""
        ).lower(),
        reverse=direction < 0,
    )
    total = len(items)
    start = (page - 1) * page_size
    return page_payload(items[start : start + page_size], page, page_size, total)


async def get_requirement_record(requirement_id, user):
    requirement = await get_project_entity("requirements", requirement_id, user, "requirement.read")
    version = await requirement_repository.find_version(requirement["current_version_id"])
    criteria = await requirement_repository.list_acceptance_criteria(
        version["_id"], 500
    )
    return {**requirement, "current_version": {**version, "acceptance_criteria": criteria}}


async def update_requirement_draft_record(project_id, requirement_id, payload, user):
    requirement = await get_project_entity(
        "requirements", requirement_id, user, "requirement.update"
    )
    if requirement["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    version = await requirement_repository.find_version(
        requirement["current_version_id"], project_id
    )
    if not version or version.get("status") != 'DRAFT':
        raise HTTPException(
            status_code=409, detail={"code": 'IMMUTABLE_REQUIREMENT_VERSION'}
        )
    if version.get("revision") != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_revision": version.get("revision"),
            },
        )
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "acceptance_criteria" in changes:
        await get_project(project_id, user, "acceptance_criteria.manage")
    if "business_rules" in changes:
        await get_project(project_id, user, "business_rule.manage")
    if "dependencies" in changes:
        await get_project(project_id, user, "requirement_dependency.manage")
    if "attachments" in changes:
        await get_project(project_id, user, "attachment.manage")
    criteria = changes.pop("acceptance_criteria", None)
    if criteria is not None:
        keys = [item.get("key") for item in criteria]
        if len(keys) != len(set(keys)):
            raise HTTPException(
                status_code=422,
                detail={"code": 'DUPLICATE_ACCEPTANCE_CRITERION_KEY'},
            )
        for item in criteria:
            validate_doc(item["content_doc"])
    if "source_refs" in changes:
        await validate_requirement_sources(project_id, changes["source_refs"], user)
    if any(key in changes for key in ("custom_values", "type", "details", "section_states")):
        await validate_requirement_custom_values(
            project_id,
            RequirementCreate(**{
                **version,
                **changes,
                "acceptance_criteria": [],
            }),
        )
    content_doc = changes.get("content_doc")
    if content_doc is not None:
        validate_doc(content_doc)
        changes["plain_text_projection"] = plain_text(content_doc)
    if "requirement_key" in changes and changes["requirement_key"] != requirement.get(
        "requirement_key"
    ):
        duplicate = await requirement_repository.find_duplicate_key(
            project_id, requirement_id, changes["requirement_key"]
        )
        if duplicate:
            raise HTTPException(
                status_code=409, detail={"code": 'REQUIREMENT_KEY_EXISTS'}
            )
    updated_version = await requirement_repository.update_draft(
        version["_id"],
        project_id,
        payload.expected_revision,
        'DRAFT',
        {**changes, "updated_at": now()},
    )
    if not updated_version:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    identity_changes = {key: changes[key] for key in ("owner_id", "tags") if key in changes}
    if identity_changes:
        await requirement_repository.update_requirement_identity(
            requirement_id,
            project_id,
            {**identity_changes, "updated_at": now()},
            version["_id"],
        )
    if criteria is not None:
        previous_criteria = await requirement_repository.list_acceptance_criteria(
            version["_id"], 500
        )
        await requirement_repository.delete_acceptance_criteria(version["_id"])
        try:
            await persist_acceptance_criteria(updated_version, criteria)
        except Exception:
            await requirement_repository.replace_acceptance_criteria(
                version["_id"],
                previous_criteria,
                [item["_id"] for item in previous_criteria],
            )
            raise
        updated_version = await requirement_repository.find_version(version["_id"])
        current_criteria = await requirement_repository.list_acceptance_criteria(
            version["_id"], 500
        )
        updated_version = {**updated_version, "acceptance_criteria": current_criteria}
    parent_changes = {key: changes[key] for key in ("requirement_key",) if key in changes}
    if parent_changes:
        await requirement_repository.update_requirement_identity(
            requirement_id, project_id, {**parent_changes, "updated_at": now()}
        )
    await audit(user.id, "requirement_draft_updated", "Requirement", requirement_id, project_id)
    return {**requirement, **parent_changes, "current_version": updated_version}


async def create_requirement_version_record(requirement_id, payload, user):
    requirement = await get_project_entity(
        "requirements", requirement_id, user, "requirement.version.create"
    )
    if requirement["current_version_id"] != payload.expected_current_version_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_version_id": requirement["current_version_id"],
            },
        )
    await validate_requirement_sources(requirement["project_id"], payload.source_refs, user)
    await validate_requirement_api_operations(requirement["project_id"], payload.details, payload.source_refs, user)
    await validate_requirement_custom_values(requirement["project_id"], payload)
    parent = await requirement_repository.find_version(requirement["current_version_id"])
    latest = await requirement_repository.find_latest_version(requirement_id)
    timestamp = now()
    version = {
        "_id": new_id('REQV'),
        "project_id": requirement["project_id"],
        "requirement_id": requirement_id,
        "requirement_key": requirement["requirement_key"],
        "version": int(latest.get("version", 0)) + 1,
        "title": payload.title,
        "type": payload.type,
        "priority": payload.priority,
        "risk": payload.risk,
        "content_doc": validate_doc(payload.content_doc),
        "plain_text_projection": plain_text(payload.content_doc),
        "business_rules": payload.business_rules,
        "actors": payload.actors,
        "dependencies": payload.dependencies,
        "source_refs": payload.source_refs,
        "tags": payload.tags,
        "owner_id": payload.owner_id or requirement.get("owner_id"),
        "details": payload.details,
        "section_states": payload.section_states,
        "custom_values": payload.custom_values,
        "acceptance_criterion_ids": [],
        "parent_version_id": parent["_id"],
        "change_reason": payload.change_reason,
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await requirement_repository.insert_version(version)
    try:
        await persist_acceptance_criteria(version, payload.acceptance_criteria)
    except Exception:
        await requirement_repository.delete_acceptance_criteria(version["_id"])
        await requirement_repository.delete_version(version["_id"], requirement["project_id"])
        raise
    activated = await requirement_repository.activate_version(
        requirement_id,
        version["_id"],
        'CHANGED',
        payload.tags,
        payload.owner_id or requirement.get("owner_id"),
        timestamp,
        payload.expected_current_version_id,
    )
    if not activated:
        await requirement_repository.delete_acceptance_criteria(version["_id"])
        await requirement_repository.delete_version(version["_id"], requirement["project_id"])
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await index_requirement_version(version)
    await audit(
        user.id,
        "requirement_version_created",
        "RequirementVersion",
        version["_id"],
        requirement["project_id"],
        {"parent_version_id": parent["_id"]},
    )
    return version


async def list_requirement_version_records(requirement_id, user):
    await get_project_entity("requirements", requirement_id, user, "requirement.version.read")
    return await requirement_repository.list_versions(
        requirement_id, 500
    )
