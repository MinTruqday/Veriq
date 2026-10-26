from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.core.database import database
from src.repositories.impact_analysis import impact_analysis_repository
from src.modules.quality.services.change_analysis import classify_test_impact, semantic_candidate_score
from src.modules.quality.services.impact_automation import (
    ai_new_test_requirements,
    apply_ai_impact_suggestions,
    request_impact_classification,
)


def impact_test_version_ids(current_tests, direct_targets):
    current_version_ids = [
        item["current_version_id"]
        for item in current_tests
        if item.get("current_version_id")
    ]
    return list(dict.fromkeys([*current_version_ids, *sorted(direct_targets)]))


async def create_impact_analysis_record(
    change_set_id,
    project_id,
    user,
    model_version=None,
    allow_existing=True,
    supersedes=None,
    rerun_input=None,
):
    
    model_version = model_version or 'evidence_impact_analysis'
    change_set = await get_project_entity(
        "requirement_change_sets", change_set_id, user, 'impact.execute'
    )
    if project_id is not None and change_set["project_id"] != project_id:
        raise HTTPException(
            status_code=422, detail={"code": 'PROJECT_MISMATCH'}
        )
    if change_set.get("status") not in ['REVIEWED', 'ANALYZED']:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'CHANGE_SET_REVIEW_REQUIRED',
                "status": change_set.get("status"),
            },
        )
    await get_project(change_set["project_id"], user, 'ai.run_impact')
    existing = await impact_analysis_repository.find_by_change_and_model(
        change_set_id, model_version
    )
    if existing and allow_existing:
        return existing
    criteria = await impact_analysis_repository.list_acceptance_criteria(
        [change_set["from_version_id"], change_set["to_version_id"]],
        10000,
    )
    source_ids = {
        change_set["from_version_id"],
        change_set["to_version_id"],
        *[item["_id"] for item in criteria],
    }
    links = await impact_analysis_repository.list_trace_links(
        change_set["project_id"],
        list(source_ids),
        ['CONFIRMED', 'STALE'],
        50000,
    )
    direct_targets = {link["target_id"] for link in links}
    current_tests = await impact_analysis_repository.list_current_tests(
        change_set["project_id"],
        ['ACTIVE', 'NEEDS_UPDATE'],
        20000,
    )
    versions = await impact_analysis_repository.list_test_versions(
        change_set["project_id"],
        impact_test_version_ids(current_tests, direct_targets),
        20000,
    )
    from_version = await impact_analysis_repository.find_requirement_version(
        change_set["from_version_id"], change_set["project_id"]
    )
    to_version = await impact_analysis_repository.find_requirement_version(
        change_set["to_version_id"], change_set["project_id"]
    )
    requirement_text = " ".join(
        [
            str((from_version or {}).get("plain_text_projection", "")),
            str((to_version or {}).get("plain_text_projection", "")),
        ]
    )
    impacted = []
    for version in versions:
        direct_trace = version["_id"] in direct_targets
        semantic_score = semantic_candidate_score(
            requirement_text, str(version.get("plain_text_projection", ""))
        )
        item = classify_test_impact(version, change_set["changes"], direct_trace)
        if not direct_trace and semantic_score >= 0.2:
            item["classification"] = 'POTENTIALLY_AFFECTED'
            item["confidence"] = max(
                item["confidence"],
                round(
                    min(
                        0.9,
                        0.55
                        + semantic_score * 0.35,
                    ),
                    4,
                ),
            )
            item["reasons"].append(
                'Ứng viên semantic có nội dung giao nhau với Requirement thay đổi'
            )
        item["evidence"].append(
            {
                "artifact_type": 'semantic_candidate',
                "semantic_score": round(semantic_score, 4),
                "direct_trace": direct_trace,
            }
        )
        impacted.append(item)
    ai_result = await request_impact_classification(change_set["project_id"], change_set, versions)
    ai_applied_version_ids = apply_ai_impact_suggestions(impacted, ai_result)
    affected = [
        item
        for item in impacted
        if item["classification"] != 'STILL_VALID'
        or item["test_case_version_id"] in direct_targets
    ]
    new_test_requirements = ai_new_test_requirements(ai_result, change_set["to_version_id"])
    analysis = {
        "_id": new_id('IMP'),
        "project_id": change_set["project_id"],
        "change_set_id": change_set_id,
        "affected_test_cases": affected,
        "new_test_requirements": new_test_requirements,
        "status": 'REVIEW_READY',
        "revision": 1,
        "mode": 'AI_ASSISTED'
        if ai_result.get("status") == 'SUCCESS'
        else 'DEGRADED_AI',
        "model_version": model_version,
        "algorithm_version": (
            rerun_input.algorithm_version if rerun_input else 'impact_pipeline'
        ),
        "knowledge_index_version": rerun_input.knowledge_index_version if rerun_input else None,
        "snapshot_number": (
            int((supersedes or {}).get("snapshot_number", 1))
            + 1
            if supersedes
            else 1
        ),
        "supersedes_analysis_id": (supersedes or {}).get("_id"),
        "rerun_reason": rerun_input.reason if rerun_input else None,
        "pipeline": ['direct_trace', 'semantic_candidate', 'deterministic_check', 'evidence_classification'],
        "ai_result": ai_result,
        "ai_applied_version_ids": ai_applied_version_ids,
        "created_by": user.id,
        "created_at": now(),
    }
    timestamp = now()
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                committed = await impact_analysis_repository.commit_analysis_for_change_set(
                    analysis,
                    change_set_id,
                    change_set["project_id"],
                    change_set.get("revision", 1),
                    change_set["status"],
                    timestamp,
                    session,
                )
                if not committed:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "CHANGE_SET_CHANGED_DURING_IMPACT_ANALYSIS",
                            "message": "Change Set đã thay đổi trong lúc phân tích. Hãy chạy phân tích lại.",
                        },
                    )
                await audit(
                    user.id,
                    'impact_analysis_created',
                    'ImpactAnalysis',
                    analysis["_id"],
                    change_set["project_id"],
                    {"affected_count": len(affected)},
                    session=session,
                )
    except HTTPException:
        raise
    return analysis


async def get_change_set_impact_record(change_set_id, user):
    
    change_set = await get_project_entity(
        "requirement_change_sets", change_set_id, user, 'impact.read'
    )
    analysis = await impact_analysis_repository.find_latest_for_change(
        change_set_id, change_set["project_id"]
    )
    if not analysis:
        raise HTTPException(
            status_code=404, detail={"code": 'ENTITY_NOT_FOUND'}
        )
    return analysis


async def get_impact_analysis_record(analysis_id, user, permission=None):
    return await get_project_entity(
        "impact_analyses",
        analysis_id,
        user,
        permission or 'impact.read',
    )


async def rerun_impact_analysis_record(analysis_id, payload, user):
    
    analysis = await get_impact_analysis_record(
        analysis_id, user, 'impact.execute'
    )
    await get_project(analysis["project_id"], user, 'ai.run_impact')
    if analysis.get("status") not in ['REVIEW_READY', 'REVIEWED']:
        raise HTTPException(
            status_code=409, detail={"code": 'IMPACT_NOT_RERUNNABLE'}
        )
    previous_status = analysis["status"]
    claimed = await impact_analysis_repository.transition_analysis(
        analysis_id,
        analysis["project_id"],
        payload.expected_revision,
        previous_status,
        {
            "status": 'RERUNNING',
            "rerun_requested_by": user.id,
            "rerun_requested_at": now(),
            "updated_at": now(),
        },
    )
    if not claimed:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    snapshot_number = int(
        analysis.get("snapshot_number", 1)
    ) + 1
    try:
        replacement = await create_impact_analysis_record(
            analysis["change_set_id"],
            analysis["project_id"],
            user,
            model_version='evidence_impact_analysis-rerun-{snapshot_number}'.format(
                snapshot_number=snapshot_number
            ),
            allow_existing=False,
            supersedes=analysis,
            rerun_input=payload,
        )
        superseded = await impact_analysis_repository.transition_analysis(
            analysis_id,
            analysis["project_id"],
            claimed["revision"],
            'RERUNNING',
            {
                "status": 'SUPERSEDED',
                "superseded_by_analysis_id": replacement["_id"],
                "superseded_at": now(),
                "superseded_by": user.id,
                "updated_at": now(),
            },
        )
        if not superseded:
            await impact_analysis_repository.delete_analysis(
                replacement["_id"], analysis["project_id"]
            )
            raise HTTPException(
                status_code=409, detail={"code": 'IMPACT_RERUN_CONFLICT'}
            )
    except Exception:
        await impact_analysis_repository.restore_analysis_status(
            analysis_id,
            analysis["project_id"],
            'RERUNNING',
            previous_status,
            now(),
        )
        await impact_analysis_repository.set_change_status(
            analysis["change_set_id"],
            analysis["project_id"],
            'REVIEWED'
            if previous_status == 'REVIEWED'
            else 'ANALYZED',
            now(),
        )
        raise
    await audit(
        user.id,
        'impact_analysis_rerun',
        'ImpactAnalysis',
        replacement["_id"],
        analysis["project_id"],
        {
            "supersedes_analysis_id": analysis_id,
            "reason": payload.reason,
            "algorithm_version": payload.algorithm_version,
            "knowledge_index_version": payload.knowledge_index_version,
        },
    )
    return replacement


async def review_impact_analysis_record(analysis_id, payload, user):
    
    analysis = await get_impact_analysis_record(
        analysis_id, user, 'impact.close'
    )
    await get_project(analysis["project_id"], user, 'impact.review')
    if analysis["status"] == 'REVIEWED':
        return analysis
    if analysis["status"] != 'REVIEW_READY':
        raise HTTPException(
            status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'}
        )
    if analysis["revision"] != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_revision": analysis["revision"],
            },
        )
    if payload.overrides:
        await get_project(analysis["project_id"], user, 'impact.override')
    by_version = {
        item["test_case_version_id"]: dict(item) for item in analysis["affected_test_cases"]
    }
    unknown = [
        item.test_case_version_id
        for item in payload.overrides
        if item.test_case_version_id not in by_version
    ]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={
                "code": 'IMPACT_OVERRIDE_TARGET_INVALID',
                "test_case_version_ids": unknown,
            },
        )
    override_events = []
    for item in payload.overrides:
        target = by_version[item.test_case_version_id]
        override_events.append(
            {
                "test_case_version_id": item.test_case_version_id,
                "from_classification": target["classification"],
                "to_classification": item.classification,
                "reason": item.reason,
                "reviewed_by": user.id,
                "created_at": now(),
            }
        )
        target["classification"] = item.classification
        target["override_reason"] = item.reason
        target["overridden_by"] = user.id
    timestamp = now()
    updated = await impact_analysis_repository.review_analysis(
        analysis_id,
        analysis["project_id"],
        payload.expected_revision,
        'REVIEW_READY',
        {
            "status": 'REVIEWED',
            "reviewed_affected_test_cases": list(by_version.values()),
            "review_overrides": override_events,
            "review_note": payload.review_note,
            "reviewed_by": user.id,
            "reviewed_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    await impact_analysis_repository.set_change_status(
        analysis["change_set_id"],
        analysis["project_id"],
        'REVIEWED',
        timestamp,
    )
    analysis = await impact_analysis_repository.find_analysis(
        analysis_id, analysis["project_id"]
    )
    await audit(
        user.id,
        'impact_analysis_reviewed',
        'ImpactAnalysis',
        analysis_id,
        analysis["project_id"],
        {"override_count": len(override_events), "review_note": payload.review_note},
    )
    return analysis


async def add_impact_review_perspective_record(analysis_id, payload, user):
    
    analysis = await get_impact_analysis_record(
        analysis_id, user, 'impact.review'
    )
    note = str(payload.get("review_note") or "").strip()
    if not 2 <= len(note) <= 5000:
        raise HTTPException(
            status_code=422, detail={"code": 'IMPACT_REVIEW_NOTE_REQUIRED'}
        )
    perspective = {
        "_id": new_id('IMPR'),
        "project_id": analysis["project_id"],
        "impact_analysis_id": analysis_id,
        "review_note": note,
        "reviewed_by": user.id,
        "created_at": now(),
    }
    await impact_analysis_repository.insert_perspective(perspective)
    await audit(
        user.id,
        'impact_review_perspective_added',
        'ImpactAnalysis',
        analysis_id,
        analysis["project_id"],
    )
    return perspective
