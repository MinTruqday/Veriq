from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.core.configuration import settings
from src.modules.design.services.linters import requirement_duplicate_score
from src.modules.quality.services.change_analysis import semantic_changes
from src.repositories.requirement_analysis import requirement_analysis_repository





async def compare_requirement_versions(requirement_id, from_version_id, to_version_id, user):
    await get_project_entity("requirements", requirement_id, user, "requirement.diff.read")
    versions = await requirement_analysis_repository.list_versions(
        {
            "requirement_id": requirement_id,
            "_id": {"$in": [from_version_id, to_version_id]},
        },
        2,
    )
    by_id = {item["_id"]: item for item in versions}
    if set(by_id) != {from_version_id, to_version_id}:
        raise HTTPException(status_code=404, detail="Không tìm thấy đủ hai phiên bản")
    before = by_id[from_version_id]
    after = by_id[to_version_id]
    before["acceptance_criteria"] = await requirement_analysis_repository.list_acceptance_criteria(
        {"requirement_version_id": from_version_id}
    )
    after["acceptance_criteria"] = await requirement_analysis_repository.list_acceptance_criteria(
        {"requirement_version_id": to_version_id}
    )
    return {
        "from_version": by_id[from_version_id],
        "to_version": by_id[to_version_id],
        "changes": semantic_changes(before, after),
        "comparison_algorithm_version": 'semantic_diff',
    }


async def find_requirement_duplicates(project_id, payload, user):
    await get_project(project_id, user, "requirement.duplicate_check")
    query = {
        "project_id": project_id,
        "status": {
            "$nin": ['OBSOLETE', 'ARCHIVED']
        },
    }
    selected_ids = list(dict.fromkeys(payload.requirement_ids))
    if selected_ids:
        query["_id"] = {"$in": selected_ids}
    requirement_limit = settings.REQUIREMENT_DUPLICATE_SCAN_MAX_ITEMS
    requirements = await requirement_analysis_repository.list_requirements(
        query, requirement_limit + 1
    )
    if len(requirements) > requirement_limit:
        raise HTTPException(
            status_code=422,
            detail={"code": "REQUIREMENT_DUPLICATE_SCAN_LIMIT_EXCEEDED"},
        )
    if selected_ids and {item["_id"] for item in requirements} != set(selected_ids):
        raise HTTPException(
            status_code=404,
            detail={"code": 'REQUIREMENT_SELECTION_NOT_FOUND'},
        )
    current_version_ids = [item.get("current_version_id") for item in requirements]
    if any(not version_id for version_id in current_version_ids):
        raise HTTPException(
            status_code=409,
            detail={"code": "REQUIREMENT_DUPLICATE_SCAN_VERSION_SNAPSHOT_INCOMPLETE"},
        )
    versions = await requirement_analysis_repository.list_versions(
        {
            "project_id": project_id,
            "_id": {"$in": current_version_ids},
        },
        requirement_limit + 1,
    )
    if {item["_id"] for item in versions} != set(current_version_ids):
        raise HTTPException(
            status_code=409,
            detail={"code": "REQUIREMENT_DUPLICATE_SCAN_VERSION_SNAPSHOT_INCOMPLETE"},
        )
    version_by_id = {item["_id"]: item for item in versions}
    if any(
        version_by_id[requirement["current_version_id"]].get("requirement_id")
        != requirement["_id"]
        for requirement in requirements
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "REQUIREMENT_DUPLICATE_SCAN_VERSION_SNAPSHOT_INCOMPLETE"},
        )
    criteria = await requirement_analysis_repository.list_acceptance_criteria(
        {
            "project_id": project_id,
            "requirement_version_id": {"$in": [item["_id"] for item in versions]},
        },
        settings.REQUIREMENT_DUPLICATE_SCAN_MAX_CRITERIA + 1,
    )
    if len(criteria) > settings.REQUIREMENT_DUPLICATE_SCAN_MAX_CRITERIA:
        raise HTTPException(
            status_code=422,
            detail={"code": "REQUIREMENT_DUPLICATE_SCAN_CRITERIA_LIMIT_EXCEEDED"},
        )
    criteria_by_version = {}
    for criterion in criteria:
        criteria_by_version.setdefault(criterion["requirement_version_id"], []).append(criterion)
    version_by_id = {
        item["_id"]: {**item, "acceptance_criteria": criteria_by_version.get(item["_id"], [])}
        for item in versions
    }
    candidates = []
    ordered = sorted(requirements, key=lambda item: item["_id"])
    for index, left in enumerate(ordered):
        left_version = version_by_id.get(left["current_version_id"])
        if not left_version:
            continue
        for right in ordered[index + 1 :]:
            right_version = version_by_id.get(right["current_version_id"])
            if not right_version:
                continue
            score, reasons = requirement_duplicate_score(left_version, right_version)
            if score < payload.threshold:
                continue
            candidates.append(
                {
                    "left_requirement_id": left["_id"],
                    "left_requirement_label": left.get("requirement_key")
                    or left_version.get("title")
                    or left["_id"],
                    "left_version_id": left_version["_id"],
                    "right_requirement_id": right["_id"],
                    "right_requirement_label": right.get("requirement_key")
                    or right_version.get("title")
                    or right["_id"],
                    "right_version_id": right_version["_id"],
                    "score": score,
                    "match_type": 'EXACT'
                    if score == 1
                    else 'SEMANTIC',
                    "reasons": reasons,
                    "status": 'CANDIDATE',
                }
            )
    candidates.sort(
        key=lambda item: (-item["score"], item["left_requirement_id"], item["right_requirement_id"])
    )
    candidates = candidates[: payload.limit]
    scan = {
        "_id": new_id('RDS'),
        "project_id": project_id,
        "requirement_ids": selected_ids,
        "threshold": payload.threshold,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "algorithm": {
            "name": "requirement_duplicate",
            "version": "1",
            "score_signals": [
                "content_similarity",
                "business_rule_similarity",
                "acceptance_criteria_similarity",
            ],
            "aggregation": "arithmetic_mean_of_available_signals",
            "explanation_only_signals": ["actor_similarity"],
        },
        "status": 'COMPLETED',
        "created_by": user.id,
        "created_at": now(),
    }
    await requirement_analysis_repository.insert_duplicate_scan(scan)
    await audit(
        user.id,
        "requirement_duplicate_scan_completed",
        "RequirementDuplicateScan",
        scan["_id"],
        project_id,
        {"candidate_count": len(candidates), "threshold": payload.threshold},
    )
    return scan
