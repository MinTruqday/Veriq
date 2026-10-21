from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now, sort_spec
from src.clients.project_knowledge import index_artifact
from src.repositories.analysis import analysis_repository
from src.modules.quality.services.change_analysis import semantic_changes


async def enrich_change_set_records(items, project_id):
    
    requirement_ids = sorted(
        {item.get("requirement_id") for item in items if item.get("requirement_id")}
    )
    version_ids = sorted(
        {
            version_id
            for item in items
            for version_id in (item.get("from_version_id"), item.get("to_version_id"))
            if version_id
        }
    )
    requirements = await analysis_repository.list_requirements_by_ids(
        project_id, requirement_ids, len(requirement_ids)
    )
    versions = await analysis_repository.list_requirement_version_labels(
        project_id, version_ids, len(version_ids)
    )
    requirements_by_id = {item["_id"]: item for item in requirements}
    versions_by_id = {item["_id"]: item for item in versions}
    enriched = []
    for item in items:
        requirement = requirements_by_id.get(item.get("requirement_id"), {})
        from_version = versions_by_id.get(item.get("from_version_id"), {})
        to_version = versions_by_id.get(item.get("to_version_id"), {})
        enriched.append(
            {
                **item,
                "requirement_label": requirement.get("requirement_key")
                or requirement.get("title")
                or item.get("requirement_id"),
                "from_version_label": (
                    f"{'v'}{from_version['version']}"
                    if from_version.get("version") is not None
                    else None
                ),
                "to_version_label": (
                    f"{'v'}{to_version['version']}"
                    if to_version.get("version") is not None
                    else None
                ),
            }
        )
    return enriched


async def mark_previous_traces_stale(change_set):
    criteria = await analysis_repository.list_acceptance_criteria(
        change_set["from_version_id"], 10000
    )
    affected_ids = [change_set["from_version_id"]]
    for change in change_set.get("changes", []):
        before_criteria = change.get("before", {}).get("fields", {}).get("acceptance_criteria") or []
        after_criteria = change.get("after", {}).get("fields", {}).get("acceptance_criteria") or []
        if not before_criteria and not after_criteria:
            continue
        before_by_key = {
            item.get("key"): (item.get("text"), item.get("source_span"))
            for item in before_criteria
        }
        after_by_key = {
            item.get("key"): (item.get("text"), item.get("source_span"))
            for item in after_criteria
        }
        affected_keys = {
            key for key in before_by_key.keys() | after_by_key.keys()
            if before_by_key.get(key) != after_by_key.get(key)
        }
        affected_ids.extend(item["_id"] for item in criteria if item.get("key") in affected_keys)
    await analysis_repository.mark_traces_stale(
        change_set["project_id"],
        affected_ids,
        'CONFIRMED',
        'STALE',
        now(),
    )


async def create_change_set_record(requirement_id, payload, user):
    
    requirement = await get_project_entity("requirements", requirement_id, user, "changeset.create")
    version_ids = [payload.from_version_id, payload.to_version_id]
    versions = await analysis_repository.list_change_pair_versions(requirement_id, version_ids)
    by_id = {item["_id"]: item for item in versions}
    if set(by_id) != {payload.from_version_id, payload.to_version_id}:
        raise HTTPException(status_code=422, detail={"code": 'INVALID_REQUIREMENT_VERSION_PAIR'})
    if by_id[payload.to_version_id].get("status") != 'BASELINED':
        raise HTTPException(status_code=409, detail={"code": 'TARGET_VERSION_NOT_BASELINED'})
    existing = await analysis_repository.find_change_set_for_target(
        requirement_id, payload.to_version_id
    )
    if existing and existing.get("changes"):
        return existing
    before = by_id[payload.from_version_id]
    after = by_id[payload.to_version_id]
    before["acceptance_criteria"] = await analysis_repository.list_acceptance_criteria(
        payload.from_version_id, 10000
    )
    after["acceptance_criteria"] = await analysis_repository.list_acceptance_criteria(
        payload.to_version_id, 10000
    )
    changes = semantic_changes(before, after)
    if existing:
        if not changes:
            return existing
        refreshed = await analysis_repository.refresh_empty_change_set(
            existing["_id"], requirement["project_id"], existing.get("revision", 1), changes
        )
        if not refreshed:
            latest = await analysis_repository.find_change_set_for_target(
                requirement_id, payload.to_version_id
            )
            return latest or existing
        await mark_previous_traces_stale(refreshed)
        await audit(
            user.id,
            "requirement_change_set_repaired",
            "RequirementChangeSet",
            refreshed["_id"],
            requirement["project_id"],
            {"change_count": len(changes)},
        )
        return refreshed
    change_set = {
        "_id": new_id('CHG'),
        "project_id": requirement["project_id"],
        "requirement_id": requirement_id,
        "from_version_id": payload.from_version_id,
        "to_version_id": payload.to_version_id,
        "changes": changes,
        "model_version": 'semantic_diff',
        "status": 'READY',
        "revision": 1,
        "created_by": user.id,
        "created_at": now(),
    }
    await analysis_repository.insert_change_set(change_set)
    if changes:
        await mark_previous_traces_stale(change_set)
    await audit(
        user.id,
        "requirement_change_set_created",
        "RequirementChangeSet",
        change_set["_id"],
        requirement["project_id"],
        {"change_count": len(changes)},
    )
    await index_artifact(
        requirement["project_id"],
        "change",
        change_set["_id"],
        change_set["_id"],
        change_set["_id"],
        " ".join(
            [
                change_set["_id"],
                *[str(item.get("subject") or item.get("type") or "") for item in changes],
            ]
        ),
        change_set["status"],
        'PROJECT_REFERENCE',
        change_set["revision"],
        requirement_version_ids=[payload.from_version_id, payload.to_version_id],
    )
    return change_set


async def list_change_set_records(
    project_id,
    user,
    requirement_id="",
    status="",
    sort="-created_at",
    limit=100,
):
    
    await get_project(project_id, user, "changeset.read")
    query = {"project_id": project_id}
    for field, value in {"requirement_id": requirement_id, "status": status}.items():
        if value:
            query[field] = value
    sort_field, direction = sort_spec(
        sort, set(['requirement_id', 'status', 'created_at', 'updated_at']), '-created_at'
    )
    items = await analysis_repository.list_change_sets(
        query, sort_field, direction, limit
    )
    return await enrich_change_set_records(items, project_id)


async def get_change_set_record(change_set_id, user):
    item = await get_project_entity(
        "requirement_change_sets", change_set_id, user, "changeset.read"
    )
    return (await enrich_change_set_records([item], item["project_id"]))[0]


async def review_change_set_record(change_set_id, payload, user):
    
    change_set = await get_project_entity(
        "requirement_change_sets", change_set_id, user, "changeset.review"
    )
    if change_set.get("status") == 'REVIEWED':
        return change_set
    if change_set.get("status") != 'READY':
        raise HTTPException(status_code=409, detail={"code": 'CHANGE_SET_NOT_REVIEWABLE'})
    updated = await analysis_repository.review_change_set(
        change_set_id,
        change_set["project_id"],
        payload.expected_revision,
        'READY',
        {
            "changes": payload.changes,
            "status": 'REVIEWED',
            "review_note": payload.review_note,
            "reviewed_by": user.id,
            "reviewed_at": now(),
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        "requirement_change_set_reviewed",
        "RequirementChangeSet",
        change_set_id,
        change_set["project_id"],
        {"review_note": payload.review_note, "change_count": len(payload.changes)},
    )
    return updated
