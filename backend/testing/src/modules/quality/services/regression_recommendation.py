from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.repositories.regression_recommendation import regression_recommendation_repository
from src.modules.quality.services.impact_analysis import require_current_impact_source





async def recent_failure_versions(project_id):
    
    runs = await regression_recommendation_repository.list_recent_runs(
        project_id, 20
    )
    results = await regression_recommendation_repository.list_results_by_status(
        [item["_id"] for item in runs],
        'FAIL',
        10000,
    )
    return {item["test_case_version_id"] for item in results}


async def create_regression_recommendation_record(change_set_id, user):
    
    change_set = await get_project_entity(
        'requirement_change_sets', change_set_id, user, 'regression.generate'
    )
    await get_project(change_set["project_id"], user, 'ai.generate_regression')
    analysis = await regression_recommendation_repository.find_latest_impact_analysis(
        change_set_id
    )
    if not analysis:
        raise HTTPException(status_code=409, detail={"code": 'IMPACT_ANALYSIS_REQUIRED'})
    if analysis.get("status") != 'REVIEWED':
        raise HTTPException(status_code=409, detail={"code": 'IMPACT_REVIEW_REQUIRED'})
    await require_current_impact_source(analysis, user, "regression.generate")
    existing = await regression_recommendation_repository.find_by_change_set(
        change_set_id, change_set["project_id"]
    )
    if existing:
        if existing.get("impact_analysis_id") != analysis.get("_id"):
            raise HTTPException(status_code=409, detail={"code": 'IMPACT_SOURCE_CHANGED'})
        return existing
    recent_failures = await recent_failure_versions(change_set["project_id"])
    items = []
    for impact in analysis.get("reviewed_affected_test_cases", analysis["affected_test_cases"]):
        test_case = await regression_recommendation_repository.find_test_case(
            impact["test_case_id"], change_set["project_id"]
        )
        current_version_id = (
            test_case.get("current_version_id") if test_case else impact["test_case_version_id"]
        )
        direct_trace = any(item.get("direct_trace") for item in impact.get("evidence", []))
        level = (
            'MUST_RUN'
            if direct_trace
            or impact["classification"] == 'NEEDS_UPDATE'
            or current_version_id in recent_failures
            else 'SHOULD_RUN'
            if impact["classification"] == 'POTENTIALLY_AFFECTED'
            else 'OPTIONAL'
        )
        reasons = list(impact["reasons"])
        if current_version_id in recent_failures:
            reasons.append('Test Case có kết quả FAIL gần đây')
        items.append(
            {
                "test_case_id": impact["test_case_id"],
                "test_case_version_id": current_version_id,
                "test_case_key": impact.get("test_case_key"),
                "level": level,
                "reasons": reasons,
                "evidence": impact["evidence"],
            }
        )
    recommendation = {
        "_id": new_id('REG'),
        "project_id": change_set["project_id"],
        "change_set_id": change_set_id,
        "impact_analysis_id": analysis["_id"],
        "items": items,
        "status": 'PENDING_APPROVAL',
        "revision": 1,
        "model_version": 'risk_scoring',
        "created_by": user.id,
        "created_at": now(),
        "updated_at": now(),
    }
    await regression_recommendation_repository.insert_recommendation(recommendation)
    await audit(
        user.id,
        'regression_recommendation_created',
        'RegressionRecommendation',
        recommendation["_id"],
        change_set["project_id"],
    )
    return recommendation


async def get_change_set_regression_record(change_set_id, user):
    change_set = await get_project_entity(
        'requirement_change_sets',
        change_set_id,
        user,
        'regression.read',
    )
    recommendation = await regression_recommendation_repository.find_by_change_set(
        change_set_id, change_set["project_id"]
    )
    if not recommendation:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    return recommendation


async def get_regression_recommendation_record(
    recommendation_id, user, permission=None
):
    return await get_project_entity(
        'regression_recommendations',
        recommendation_id,
        user,
        permission or 'regression.read',
    )


async def edit_regression_recommendation_record(recommendation_id, payload, user):
    
    recommendation = await get_regression_recommendation_record(
        recommendation_id, user, 'regression.generate'
    )
    if recommendation.get("status") != 'PENDING_APPROVAL':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    analysis = await get_project_entity(
        "impact_analyses",
        recommendation["impact_analysis_id"],
        user,
        "regression.generate",
    )
    if analysis.get("status") != 'REVIEWED':
        raise HTTPException(status_code=409, detail={"code": 'IMPACT_REVIEW_REQUIRED'})
    await require_current_impact_source(analysis, user, "regression.generate")
    selected = payload.selected_test_case_version_ids
    items = recommendation.get("items", [])
    if selected is not None:
        by_id = {item["test_case_version_id"]: item for item in items}
        unknown = set(selected) - set(by_id)
        if unknown:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": 'INVALID_REGRESSION_SCOPE',
                    "test_case_version_ids": sorted(unknown),
                },
            )
        items = [by_id[item] for item in selected]
    timestamp = now()
    updated = await regression_recommendation_repository.update_recommendation(
        {
            "_id": recommendation_id,
            "project_id": recommendation["project_id"],
            "status": 'PENDING_APPROVAL',
            "revision": payload.expected_revision,
        },
        {
            "items": items,
            "name": payload.name or recommendation.get("name"),
            "review_note": payload.review_note,
            "candidate_edited_by": user.id,
            "candidate_edited_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'regression_recommendation_edited',
        'RegressionRecommendation',
        recommendation_id,
        recommendation["project_id"],
    )
    return updated


async def approve_regression_recommendation_record(recommendation_id, payload, user):
    
    recommendation = await get_regression_recommendation_record(
        recommendation_id, user, 'regression.approve'
    )
    if recommendation.get("status") == 'APPROVED' and recommendation.get(
        "test_suite_id"
    ):
        suite = await regression_recommendation_repository.find_suite(
            recommendation["test_suite_id"], recommendation["project_id"]
        )
        return {"recommendation": recommendation, "test_suite": suite}
    if recommendation.get("status") != 'PENDING_APPROVAL':
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    if recommendation["revision"] != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_revision": recommendation["revision"]},
        )
    analysis = await get_project_entity(
        "impact_analyses",
        recommendation["impact_analysis_id"],
        user,
        "regression.approve",
    )
    if analysis.get("status") != 'REVIEWED':
        raise HTTPException(status_code=409, detail={"code": 'IMPACT_REVIEW_REQUIRED'})
    await require_current_impact_source(analysis, user, "regression.approve")
    recommended_ids = {item["test_case_version_id"] for item in recommendation["items"]}
    selected_ids = payload.selected_test_case_version_ids
    if selected_ids is None:
        selected_ids = [
            item["test_case_version_id"]
            for item in recommendation["items"]
            if item["level"] in ['MUST_RUN', 'SHOULD_RUN']
        ]
    selected_ids = list(dict.fromkeys(selected_ids))
    if not selected_ids or not set(selected_ids) <= recommended_ids:
        raise HTTPException(status_code=422, detail={"code": 'REGRESSION_SELECTION_INVALID'})
    test_cases = await regression_recommendation_repository.list_active_test_cases(
        recommendation["project_id"],
        selected_ids,
        'ACTIVE',
        len(selected_ids),
    )
    if {item["current_version_id"] for item in test_cases} != set(selected_ids):
        raise HTTPException(status_code=409, detail={"code": 'REGRESSION_RECOMMENDATION_STALE'})
    timestamp = now()
    suite = {
        "_id": new_id('TSU'),
        "project_id": recommendation["project_id"],
        "name": payload.name
        or 'Regression {change_set_id}'.format(
            change_set_id=recommendation["change_set_id"]
        ),
        "suite_type": 'regression',
        "test_case_version_ids": selected_ids,
        "source_regression_recommendation_id": recommendation_id,
        "status": 'APPROVED',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await regression_recommendation_repository.insert_suite(suite)
    recommendation = await regression_recommendation_repository.update_recommendation(
        {
            "_id": recommendation_id,
            "project_id": recommendation["project_id"],
            "revision": payload.expected_revision,
            "status": 'PENDING_APPROVAL',
        },
        {
            "status": 'APPROVED',
            "test_suite_id": suite["_id"],
            "review_note": payload.review_note,
            "approved_by": user.id,
            "approved_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not recommendation:
        await regression_recommendation_repository.delete_suite(
            suite["_id"], suite["project_id"]
        )
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'regression_approved',
        'RegressionRecommendation',
        recommendation_id,
        recommendation["project_id"],
        {"test_suite_id": suite["_id"], "test_count": len(selected_ids)},
    )
    await audit(
        user.id,
        'test_suite_created',
        'TestSuite',
        suite["_id"],
        recommendation["project_id"],
        {"source_regression_recommendation_id": recommendation_id},
    )
    return {"recommendation": recommendation, "test_suite": suite}
