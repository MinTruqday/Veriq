import hashlib
import json

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

IMPACT_SCOPE_LIMITS = {
    "acceptance_criteria": 10000,
    "trace_links": 50000,
    "test_scenarios": 20000,
    "test_cases": 20000,
    "test_case_versions": 20000,
    "test_plans": 20000,
    "test_runs": 20000,
}


def _bounded_scope_records(records, scope_name, limitations):
    limit = IMPACT_SCOPE_LIMITS[scope_name]
    if len(records) > limit:
        limitations.append(f"SCOPE_TRUNCATED_{scope_name.upper()}")
        return records[:limit]
    return records


def _plan_case_version_ids(plan):
    version_ids = list(plan.get("test_case_version_ids") or [])
    for suite in plan.get("test_suite_snapshots") or []:
        version_ids.extend(suite.get("test_case_version_ids") or [])
    return list(dict.fromkeys(str(item) for item in version_ids if item))


def _impact_snapshot(kind, item, reasons, related_case_version_ids=None):
    snapshot = {
        "artifact_type": kind,
        "artifact_id": str(item.get("_id") or ""),
        "_id": str(item.get("_id") or ""),
        "key": item.get("scenario_key") or item.get("test_plan_key") or item.get("run_key"),
        "name": item.get("name") or item.get("title") or item.get("scenario_key") or "",
        "status": item.get("status") or "UNKNOWN",
        "revision": item.get("revision"),
        "reasons": list(dict.fromkeys(reasons)),
        "related_test_case_version_ids": list(related_case_version_ids or []),
        "requirement_version_ids": list(item.get("requirement_version_ids") or []),
        "snapshot_only": kind == "test_run",
    }
    if kind == "test_scenario":
        snapshot["acceptance_criterion_ids"] = list(item.get("acceptance_criterion_ids") or [])
        snapshot["test_condition_ids"] = list(item.get("test_condition_ids") or [])
    elif kind == "test_plan":
        snapshot["test_suite_ids"] = list(item.get("test_suite_ids") or [])
        snapshot["approved_snapshot_hash"] = item.get("approved_snapshot_hash") or item.get("baseline_hash")
    elif kind == "test_run":
        snapshot["test_plan_id"] = item.get("test_plan_id")
        snapshot["test_plan_snapshot_hash"] = item.get("test_plan_snapshot_hash")
        snapshot["test_case_version_ids"] = list(item.get("test_case_version_ids") or [])
        snapshot["execution_status"] = item.get("status") or "UNKNOWN"
    return snapshot


def impact_test_version_ids(current_tests, direct_targets):
    current_version_ids = {
        item["current_version_id"]
        for item in current_tests
        if item.get("current_version_id")
    }
    return sorted(current_version_ids | set(direct_targets))


def _impact_source_fingerprint(
    change_set,
    criteria,
    links,
    source_scenarios,
    scenario_links,
    current_tests,
    versions,
    from_version,
    to_version,
    plan_candidates,
    run_candidates,
):
    source = {
        "change_set": {
            key: change_set.get(key)
            for key in ("_id", "project_id", "from_version_id", "to_version_id", "changes")
        },
        "acceptance_criteria": criteria,
        "trace_links": links,
        "source_scenarios": source_scenarios,
        "scenario_trace_links": scenario_links,
        "current_test_cases": current_tests,
        "test_case_versions": versions,
        "from_requirement_version": from_version,
        "to_requirement_version": to_version,
        "test_plans": plan_candidates,
        "test_runs": run_candidates,
    }
    serialized = json.dumps(source, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def _current_impact_source_fingerprint(change_set, analysis):
    scope_limitations = []
    requirement_version_ids = [change_set["from_version_id"], change_set["to_version_id"]]
    criteria = await impact_analysis_repository.list_acceptance_criteria(
        requirement_version_ids, IMPACT_SCOPE_LIMITS["acceptance_criteria"]
    )
    criteria = _bounded_scope_records(criteria, "acceptance_criteria", scope_limitations)
    source_ids = { *requirement_version_ids, *[item["_id"] for item in criteria] }
    links = await impact_analysis_repository.list_trace_links(
        change_set["project_id"], list(source_ids), ["CONFIRMED", "STALE"],
        IMPACT_SCOPE_LIMITS["trace_links"],
    )
    links = _bounded_scope_records(links, "trace_links", scope_limitations)
    source_scenarios = await impact_analysis_repository.list_scenarios_for_sources(
        change_set["project_id"], list(source_ids), IMPACT_SCOPE_LIMITS["test_scenarios"]
    )
    source_scenarios = _bounded_scope_records(
        source_scenarios, "test_scenarios", scope_limitations
    )
    scenario_ids = [str(item["_id"]) for item in source_scenarios if item.get("_id")]
    scenario_links = await impact_analysis_repository.list_trace_links(
        change_set["project_id"], scenario_ids, ["CONFIRMED", "STALE"],
        IMPACT_SCOPE_LIMITS["trace_links"],
    )
    scenario_links = _bounded_scope_records(
        scenario_links, "trace_links", scope_limitations
    )
    direct_targets = {
        link["target_id"] for link in [*links, *scenario_links] if link.get("target_id")
    }
    current_tests = await impact_analysis_repository.list_current_tests(
        change_set["project_id"], ["ACTIVE", "NEEDS_UPDATE"],
        IMPACT_SCOPE_LIMITS["test_cases"],
    )
    current_tests = _bounded_scope_records(current_tests, "test_cases", scope_limitations)
    candidate_version_ids = impact_test_version_ids(current_tests, direct_targets)
    if len(candidate_version_ids) > IMPACT_SCOPE_LIMITS["test_case_versions"]:
        candidate_version_ids = candidate_version_ids[: IMPACT_SCOPE_LIMITS["test_case_versions"]]
    versions = await impact_analysis_repository.list_test_versions(
        change_set["project_id"], candidate_version_ids,
        IMPACT_SCOPE_LIMITS["test_case_versions"],
    )
    versions = _bounded_scope_records(
        versions, "test_case_versions", scope_limitations
    )
    from_version = await impact_analysis_repository.find_requirement_version(
        change_set["from_version_id"], change_set["project_id"]
    )
    to_version = await impact_analysis_repository.find_requirement_version(
        change_set["to_version_id"], change_set["project_id"]
    )
    affected_case_ids = list(dict.fromkeys(
        item.get("test_case_version_id")
        for item in analysis.get("affected_test_cases", [])
        if item.get("test_case_version_id")
    ))
    plan_candidates = await impact_analysis_repository.list_plans_for_impact(
        change_set["project_id"], [change_set["from_version_id"]], affected_case_ids,
        IMPACT_SCOPE_LIMITS["test_plans"],
    )
    plan_candidates = _bounded_scope_records(
        plan_candidates, "test_plans", scope_limitations
    )
    plan_ids = [
        item.get("artifact_id")
        for item in analysis.get("affected_test_plans", [])
        if item.get("artifact_id")
    ]
    run_candidates = await impact_analysis_repository.list_runs_for_impact(
        change_set["project_id"], [change_set["from_version_id"]], affected_case_ids,
        plan_ids, IMPACT_SCOPE_LIMITS["test_runs"],
    )
    run_candidates = _bounded_scope_records(
        run_candidates, "test_runs", scope_limitations
    )
    return _impact_source_fingerprint(
        change_set, criteria, links, source_scenarios, scenario_links, current_tests,
        versions, from_version, to_version, plan_candidates, run_candidates,
    )


async def require_current_impact_source(analysis, user, permission="impact.review"):
    change_set_id = analysis.get("change_set_id")
    if not change_set_id or not analysis.get("source_snapshot_hash"):
        raise HTTPException(status_code=409, detail={"code": "IMPACT_SOURCE_CHANGED"})
    change_set = await get_project_entity(
        "requirement_change_sets", change_set_id, user, permission
    )
    if change_set.get("status") not in {"ANALYZED", "REVIEWED"}:
        raise HTTPException(status_code=409, detail={"code": "IMPACT_SOURCE_CHANGED"})
    current_hash = await _current_impact_source_fingerprint(change_set, analysis)
    if (
        current_hash != analysis["source_snapshot_hash"]
        or int(change_set.get("revision", 1)) != analysis.get("source_change_set_revision")
    ):
        raise HTTPException(status_code=409, detail={"code": "IMPACT_SOURCE_CHANGED"})
    return change_set


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
        existing_source_hash = await _current_impact_source_fingerprint(
            change_set, existing
        )
        if (
            not existing.get("source_snapshot_hash")
            or existing_source_hash != existing["source_snapshot_hash"]
            or int(change_set.get("revision", 1))
            != existing.get("source_change_set_revision")
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "IMPACT_SOURCE_CHANGED",
                    "message": "Nguồn hoặc liên kết đã thay đổi sau khi phân tích. Hãy chạy lại phân tích trước khi tiếp tục.",
                },
            )
        return existing
    scope_limitations = []
    criteria = await impact_analysis_repository.list_acceptance_criteria(
        [change_set["from_version_id"], change_set["to_version_id"]],
        IMPACT_SCOPE_LIMITS["acceptance_criteria"],
    )
    criteria = _bounded_scope_records(criteria, "acceptance_criteria", scope_limitations)
    source_ids = {
        change_set["from_version_id"],
        change_set["to_version_id"],
        *[item["_id"] for item in criteria],
    }
    links = await impact_analysis_repository.list_trace_links(
        change_set["project_id"],
        list(source_ids),
        ['CONFIRMED', 'STALE'],
        IMPACT_SCOPE_LIMITS["trace_links"],
    )
    links = _bounded_scope_records(links, "trace_links", scope_limitations)
    source_scenarios = await impact_analysis_repository.list_scenarios_for_sources(
        change_set["project_id"],
        list(source_ids),
        IMPACT_SCOPE_LIMITS["test_scenarios"],
    )
    source_scenarios = _bounded_scope_records(
        source_scenarios, "test_scenarios", scope_limitations
    )
    scenario_ids = [str(item["_id"]) for item in source_scenarios if item.get("_id")]
    scenario_links = await impact_analysis_repository.list_trace_links(
        change_set["project_id"],
        scenario_ids,
        ['CONFIRMED', 'STALE'],
        IMPACT_SCOPE_LIMITS["trace_links"],
    )
    scenario_links = _bounded_scope_records(
        scenario_links, "trace_links", scope_limitations
    )
    direct_targets = {
        link["target_id"] for link in [*links, *scenario_links] if link.get("target_id")
    }
    current_tests = await impact_analysis_repository.list_current_tests(
        change_set["project_id"],
        ['ACTIVE', 'NEEDS_UPDATE'],
        IMPACT_SCOPE_LIMITS["test_cases"],
    )
    current_tests = _bounded_scope_records(
        current_tests, "test_cases", scope_limitations
    )
    candidate_version_ids = impact_test_version_ids(current_tests, direct_targets)
    if len(candidate_version_ids) > IMPACT_SCOPE_LIMITS["test_case_versions"]:
        scope_limitations.append("SCOPE_TRUNCATED_TEST_CASE_VERSION_IDS")
        candidate_version_ids = candidate_version_ids[: IMPACT_SCOPE_LIMITS["test_case_versions"]]
    versions = await impact_analysis_repository.list_test_versions(
        change_set["project_id"],
        candidate_version_ids,
        IMPACT_SCOPE_LIMITS["test_case_versions"],
    )
    versions = _bounded_scope_records(
        versions, "test_case_versions", scope_limitations
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
        item = classify_test_impact(version, direct_trace)
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
    affected_case_version_ids = list(
        dict.fromkeys(item["test_case_version_id"] for item in affected)
    )
    scenario_case_versions = {}
    for link in scenario_links:
        scenario_case_versions.setdefault(link.get("source_id"), []).append(link.get("target_id"))
    affected_scenarios = []
    for scenario in source_scenarios:
        linked_requirement_ids = set(scenario.get("requirement_version_ids") or [])
        linked_criteria_ids = set(scenario.get("acceptance_criterion_ids") or [])
        scenario_reasons = []
        if linked_requirement_ids.intersection(
            {change_set["from_version_id"], change_set["to_version_id"]}
        ):
            scenario_reasons.append("SCENARIO_LINKED_TO_CHANGED_REQUIREMENT")
        if linked_criteria_ids.intersection({item["_id"] for item in criteria}):
            scenario_reasons.append("SCENARIO_LINKED_TO_CHANGED_ACCEPTANCE_CRITERION")
        linked_cases = list(
            dict.fromkeys(scenario_case_versions.get(str(scenario.get("_id")), []))
        )
        if scenario_reasons:
            affected_scenarios.append(
                _impact_snapshot("test_scenario", scenario, scenario_reasons, linked_cases)
            )
    case_ids_for_scope = set(affected_case_version_ids)
    plan_candidates = await impact_analysis_repository.list_plans_for_impact(
        change_set["project_id"],
        [change_set["from_version_id"]],
        list(case_ids_for_scope),
        IMPACT_SCOPE_LIMITS["test_plans"],
    )
    plan_candidates = _bounded_scope_records(
        plan_candidates, "test_plans", scope_limitations
    )
    affected_plans = []
    for plan in plan_candidates:
        plan_case_ids = set(_plan_case_version_ids(plan))
        plan_requirement_ids = set(plan.get("requirement_version_ids") or [])
        plan_reasons = []
        if change_set["from_version_id"] in plan_requirement_ids:
            plan_reasons.append("PLAN_INCLUDES_CHANGED_REQUIREMENT_VERSION")
        if plan_case_ids.intersection(case_ids_for_scope):
            plan_reasons.append("PLAN_INCLUDES_AFFECTED_TEST_CASE_VERSION")
        if plan_reasons:
            affected_plans.append(
                _impact_snapshot(
                    "test_plan", plan, plan_reasons, sorted(plan_case_ids.intersection(case_ids_for_scope))
                )
            )
    plan_ids = [item["artifact_id"] for item in affected_plans if item.get("artifact_id")]
    run_candidates = await impact_analysis_repository.list_runs_for_impact(
        change_set["project_id"],
        [change_set["from_version_id"]],
        list(case_ids_for_scope),
        plan_ids,
        IMPACT_SCOPE_LIMITS["test_runs"],
    )
    run_candidates = _bounded_scope_records(
        run_candidates, "test_runs", scope_limitations
    )
    source_snapshot_hash = _impact_source_fingerprint(
        change_set,
        criteria,
        links,
        source_scenarios,
        scenario_links,
        current_tests,
        versions,
        from_version,
        to_version,
        plan_candidates,
        run_candidates,
    )
    affected_runs = []
    for run in run_candidates:
        run_case_ids = set(run.get("test_case_version_ids") or [])
        run_requirement_ids = set(run.get("requirement_version_ids") or [])
        run_reasons = []
        if change_set["from_version_id"] in run_requirement_ids:
            run_reasons.append("RUN_SNAPSHOT_INCLUDES_CHANGED_REQUIREMENT_VERSION")
        if run_case_ids.intersection(case_ids_for_scope):
            run_reasons.append("RUN_SNAPSHOT_INCLUDES_AFFECTED_TEST_CASE_VERSION")
        if run.get("test_plan_id") in plan_ids:
            run_reasons.append("RUN_USES_AFFECTED_TEST_PLAN")
        if run_reasons:
            affected_runs.append(
                _impact_snapshot(
                    "test_run", run, run_reasons, sorted(run_case_ids.intersection(case_ids_for_scope))
                )
            )
    impact_limitations = list(dict.fromkeys(scope_limitations))
    if not links and not scenario_links:
        impact_limitations.append("NO_CONFIRMED_TRACE_LINKS_FOUND")
    if any(item.get("status") == "STALE" for item in [*links, *scenario_links]):
        impact_limitations.append("STALE_TRACE_LINKS_REQUIRE_REVIEW")
    analysis = {
        "_id": new_id('IMP'),
        "project_id": change_set["project_id"],
        "change_set_id": change_set_id,
        "source_change_set_revision": int(change_set.get("revision", 1)) + 1,
        "source_snapshot_hash": source_snapshot_hash,
        "affected_test_cases": affected,
        "affected_test_scenarios": affected_scenarios,
        "affected_test_plans": affected_plans,
        "affected_test_runs": affected_runs,
        "impact_limitations": impact_limitations,
        "scope_complete": not scope_limitations,
        "scope_summary": {
            "trace_link_count": len(links) + len(scenario_links),
            "affected_test_scenario_count": len(affected_scenarios),
            "affected_test_case_count": len(affected),
            "affected_test_plan_count": len(affected_plans),
            "affected_test_run_count": len(affected_runs),
            "processed_acceptance_criterion_count": len(criteria),
            "processed_source_scenario_count": len(source_scenarios),
            "processed_current_test_case_count": len(current_tests),
            "processed_test_case_version_count": len(versions),
            "processed_test_plan_count": len(plan_candidates),
            "processed_test_run_count": len(run_candidates),
        },
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
    await require_current_impact_source(analysis, user, "impact.review")
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
    try:
        await require_current_impact_source(analysis, user, "impact.review")
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") != "IMPACT_SOURCE_CHANGED":
            raise
        current = await impact_analysis_repository.find_analysis(
            analysis_id, analysis["project_id"]
        )
        if current and current.get("status") == "REVIEWED":
            rolled_back = await impact_analysis_repository.transition_analysis(
                analysis_id,
                analysis["project_id"],
                current["revision"],
                "REVIEWED",
                {"status": "REVIEW_READY", "updated_at": now()},
                unset=[
                    "reviewed_affected_test_cases",
                    "review_overrides",
                    "review_note",
                    "reviewed_by",
                    "reviewed_at",
                ],
            )
            if not rolled_back:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "IMPACT_REVIEW_RECONCILIATION_REQUIRED"},
                ) from exc
        raise
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
