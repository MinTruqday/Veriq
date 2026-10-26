from fastapi import HTTPException

from src.core.common import get_project
from src.repositories.causal_analysis import causal_analysis_repository


async def validate_member(project_id, user_id):
    
    if not await causal_analysis_repository.find_active_member(
        project_id, user_id, 'ACTIVE'
    ):
        raise HTTPException(
            status_code=422, detail={"code": 'ACTION_OWNER_NOT_PROJECT_MEMBER'}
        )


async def get_analysis(analysis_id, user, permission=None):
    
    value = await causal_analysis_repository.find_analysis(analysis_id)
    if not value:
        raise HTTPException(
            status_code=404, detail={"code": 'ENTITY_NOT_FOUND'}
        )
    await get_project(value["project_id"], user, permission or 'causalanalysis.read')
    return value


async def list_analyses(project_id, user):
    
    await get_project(project_id, user, "causalanalysis.read")
    items = await causal_analysis_repository.list_analyses(
        {"project_id": project_id}, 1000
    )
    return {"items": items, "total": len(items)}


async def latest_hypothesis_result(analysis_id, user):
    analysis = await get_analysis(analysis_id, user, "causalanalysis.read")
    return await causal_analysis_repository.find_latest_ai_result(
        analysis["project_id"],
        analysis_id,
        "CAUSAL_ANALYSIS_HYPOTHESES",
        {
            "_id": 1,
            "suggestions": 1,
            "candidate_only": 1,
            "human_confirmation_required": 1,
            "created_at": 1,
            "model": 1,
            "confidence": 1,
            "status": 1,
            "reason_codes": 1,
        },
    )


async def suggest_candidates(project_id, user):
    project = await get_project(project_id, user, "causalanalysis.read")
    project_settings = project.get("settings") or {}
    
    reopen_threshold = max(
        int(
            project_settings.get(
                "rca_reopen_threshold", 2
            )
        ),
        1,
    )
    duplicate_threshold = max(
        int(
            project_settings.get(
                "rca_duplicate_threshold", 3
            )
        ),
        2,
    )
    defects = await causal_analysis_repository.list_defects(
        {"project_id": project_id}, 2000
    )
    existing = await causal_analysis_repository.list_analyses(
        {"project_id": project_id, "status": {"$ne": 'CLOSED'}},
        1000,
        {"defect_ids": 1},
    )
    linked = {defect_id for analysis in existing for defect_id in analysis.get("defect_ids", [])}
    duplicate_counts = {}
    root_cause_counts = {}
    for defect in defects:
        duplicate_key = defect.get("duplicate_cluster_id") or defect.get("duplicate_of")
        if duplicate_key:
            duplicate_counts[duplicate_key] = duplicate_counts.get(duplicate_key, 0) + 1
        category = defect.get("root_cause_category")
        if category and category != 'UNKNOWN':
            root_cause_counts[category] = root_cause_counts.get(category, 0) + 1
    items = []
    for defect in defects:
        if defect["_id"] in linked:
            continue
        reason_codes = []
        if str(defect.get("severity", "")).upper() in set(['BLOCKER', 'CRITICAL']):
            reason_codes.append('SEVERITY_TRIGGER')
        if (
            int(defect.get("reopen_count", 0) or 0) >= reopen_threshold
            or defect.get("status") == 'REOPENED'
        ):
            reason_codes.append('REOPEN_TRIGGER')
        duplicate_key = defect.get("duplicate_cluster_id") or defect.get("duplicate_of")
        if duplicate_key and duplicate_counts.get(duplicate_key, 0) >= duplicate_threshold:
            reason_codes.append('DUPLICATE_CLUSTER_TRIGGER')
        category = defect.get("root_cause_category")
        if (
            category
            and category != 'UNKNOWN'
            and root_cause_counts.get(category, 0) >= duplicate_threshold
        ):
            reason_codes.append('REPEATED_ROOT_CAUSE_TRIGGER')
        if reason_codes:
            items.append(
                {
                    "candidate_id": f"{'RCA-CANDIDATE-'}{defect['_id']}",
                    "defect_ids": [defect["_id"]],
                    "problem_statement": defect.get("title")
                    or defect.get("summary")
                    or defect["_id"],
                    "reason_codes": reason_codes,
                    "evidence_refs": [defect["_id"]],
                }
            )
    return {
        "items": items,
        "total": len(items),
        "thresholds": {"reopen_count": reopen_threshold, "duplicate_cluster": duplicate_threshold},
    }
