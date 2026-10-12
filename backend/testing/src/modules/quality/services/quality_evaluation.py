from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.repositories.quality import quality_repository
from src.modules.execution.services.test_monitoring import effective_snapshot


def system_recommendation(gate_status, critical_risks):
    if gate_status == 'FAIL':
        return 'NO_GO'
    if gate_status in ['INSUFFICIENT_DATA', 'MANUAL_REQUIRED', 'NOT_CONFIGURED', None]:
        return 'INSUFFICIENT_DATA'
    if gate_status == 'WARN':
        return 'MORE_TESTING_REQUIRED'
    return (
        'GO_WITH_RISK'
        if critical_risks
        else 'GO'
    )


def evaluate_quality_objectives(objectives, snapshots):
    measurements = {}
    for snapshot in sorted(
        snapshots,
        key=lambda item: str(item.get("measured_at") or item.get("created_at") or ""),
        reverse=True,
    ):
        measurements.setdefault(snapshot.get("measurement_key"), snapshot)
    results = []
    for objective in objectives:
        key = objective.get("key") or objective.get("metric")
        target = objective.get("target")
        snapshot = measurements.get(key)
        actual = snapshot.get("value") if snapshot else None
        if (
            not isinstance(actual, (int, float))
            or isinstance(actual, bool)
            or not isinstance(target, (int, float))
            or isinstance(target, bool)
        ):
            status = 'INSUFFICIENT_DATA'
        elif key in ['BLOCKED_RATE', 'DEFECT_REOPEN_RATE', 'CRITICAL_DEFECT_AGING', 'MEAN_TIME_TO_RETEST', 'STALE_TEST_RATIO', 'REQUIREMENT_VOLATILITY', 'ESCAPED_DEFECT_RATE']:
            status = 'PASS' if actual <= target else 'FAIL'
        else:
            status = 'PASS' if actual >= target else 'FAIL'
        results.append(
            {
                **objective,
                "measurement_snapshot_id": snapshot.get("_id") if snapshot else None,
                "actual": actual,
                "status": status,
            }
        )
    return results


def rationale_document(value):
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": value}]}],
    }


async def get_evaluation(evaluation_id, user, permission=None):
    value = await quality_repository.find_evaluation(evaluation_id)
    if not value:
        raise HTTPException(
            status_code=404, detail={"code": 'ENTITY_NOT_FOUND'}
        )
    await get_project(
        value["project_id"], user, permission or 'qualityevaluation.read'
    )
    return value


async def list_evaluations(project_id, release_id, user):
    await get_project(project_id, user, 'qualityevaluation.read')
    query = {"project_id": project_id}
    if release_id:
        query["release_id"] = release_id
    items = await quality_repository.list_evaluations(
        query, 500
    )
    return {"items": items, "total": len(items)}


async def create_evaluation(project_id, payload, user):
    await get_project(project_id, user, 'qualityevaluation.create')
    if payload.idempotency_key:
        existing = await quality_repository.find_evaluation_by_idempotency_key(
            project_id, payload.idempotency_key
        )
        if existing:
            if (
                existing.get("release_id") != payload.release_id
                or existing.get("build_id") != payload.build_id
            ):
                raise HTTPException(
                    status_code=409, detail={"code": 'IDEMPOTENCY_KEY_REUSED'}
                )
            return existing
    release = await quality_repository.find_release(payload.release_id, project_id)
    build = await quality_repository.find_build(payload.build_id, project_id)
    monitoring = await quality_repository.find_monitoring_snapshot(
        payload.monitoring_snapshot_id, project_id, payload.release_id
    )
    snapshots = await quality_repository.list_measurement_snapshots(
        payload.measurement_snapshot_refs, project_id, 1000
    )
    if (
        not release
        or not build
        or not monitoring
        or len(snapshots) != len(set(payload.measurement_snapshot_refs))
    ):
        raise HTTPException(
            status_code=422, detail={"code": 'QUALITY_EVALUATION_SOURCE_NOT_IN_PROJECT'}
        )
    if any(item.get("release_id") not in {None, payload.release_id} for item in snapshots):
        raise HTTPException(
            status_code=422, detail={"code": 'MEASUREMENT_RELEASE_MISMATCH'}
        )
    monitoring = await effective_snapshot(monitoring)
    plan = await quality_repository.find_test_plan(
        monitoring["test_plan_id"], project_id
    )
    strategy = await quality_repository.find_strategy(
        (plan or {}).get("strategy_version_id"), project_id
    )
    gate = await quality_repository.find_gate_for_project(
        monitoring["_id"], project_id
    )
    if not plan or not strategy or not gate:
        raise HTTPException(
            status_code=422, detail={"code": 'QUALITY_EVALUATION_SOURCE_INCOMPLETE'}
        )
    unresolved = await quality_repository.list_unresolved_defects(
        project_id,
        payload.release_id,
        ['CLOSED', 'REJECTED'],
        5000,
    )
    gate_status = monitoring.get(
        "effective_quality_gate_status", monitoring.get("quality_gate_status")
    )
    recommendation = system_recommendation(gate_status, payload.critical_risks)
    if payload.recommendation and payload.recommendation != recommendation:
        raise HTTPException(
            status_code=422,
            detail={"code": 'SYSTEM_RECOMMENDATION_MISMATCH', "expected": recommendation},
        )
    human_decision = await quality_repository.find_latest_decision(
        monitoring["_id"], project_id
    )
    timestamp = now()
    value = {
        "_id": new_id('PQE'),
        "project_id": project_id,
        **payload.model_dump(exclude={"recommendation"}),
        "snapshot_id": monitoring["_id"],
        "strategy_version_id": strategy["_id"],
        "gate_evaluation_id": gate["_id"],
        "measurement_snapshots": snapshots,
        "quality_objective_results": evaluate_quality_objectives(
            strategy.get("quality_objectives", []), snapshots
        ),
        "exit_criteria_results": monitoring.get("effective_exit_criteria_evaluation", []),
        "exit_criteria_snapshot": monitoring.get("effective_exit_criteria_evaluation", []),
        "quality_gate_status": gate_status,
        "system_recommendation": recommendation,
        "recommendation": recommendation,
        "rationale_doc": rationale_document(payload.rationale),
        "human_decision": human_decision,
        "quality_decision_id": human_decision.get("_id") if human_decision else None,
        "unresolved_defects": unresolved,
        "waivers": [],
        "reviewed_by": [],
        "approved_by": None,
        "status": 'DRAFT',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await quality_repository.insert_evaluation(value)
    except DuplicateKeyError:
        if payload.idempotency_key:
            return await quality_repository.find_evaluation_by_idempotency_key(
                project_id, payload.idempotency_key
            )
        raise
    await audit(
        user.id,
        'quality_evaluation_created',
        'ProductQualityEvaluation',
        value["_id"],
        project_id,
        {
            "release_id": payload.release_id,
            "recommendation": recommendation,
            "measurement_snapshot_refs": payload.measurement_snapshot_refs,
        },
    )
    return value


async def update_evaluation(evaluation_id, payload, user):
    value = await get_evaluation(evaluation_id, user, 'qualityevaluation.create')
    if value["status"] != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'QUALITY_EVALUATION_IMMUTABLE'})
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "recommendation" in changes and changes["recommendation"] != value.get(
        "system_recommendation", value.get("recommendation")
    ):
        raise HTTPException(
            status_code=409, detail={"code": 'SYSTEM_RECOMMENDATION_IMMUTABLE'}
        )
    changes.pop("recommendation", None)
    if "rationale" in changes:
        changes["rationale_doc"] = rationale_document(changes["rationale"])
    changes["updated_at"] = now()
    updated = await quality_repository.update_evaluation(
        {
            "_id": evaluation_id,
            "revision": payload.expected_revision,
            "status": 'DRAFT',
        },
        {"$set": changes, "$inc": {"revision": 1}},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'quality_evaluation_updated',
        'ProductQualityEvaluation',
        evaluation_id,
        value["project_id"],
        {"fields": sorted(changes)},
    )
    return updated


async def submit_evaluation(evaluation_id, payload, user):
    value = await get_evaluation(evaluation_id, user, 'qualityevaluation.review')
    if value["status"] != 'DRAFT':
        raise HTTPException(
            status_code=409, detail={"code": 'INVALID_QUALITY_EVALUATION_TRANSITION'}
        )
    updated = await quality_repository.update_evaluation(
        {
            "_id": evaluation_id,
            "revision": payload.expected_revision,
            "status": 'DRAFT',
        },
        {
            "$set": {
                "status": 'IN_REVIEW',
                "submitted_by": user.id,
                "submitted_at": now(),
                "submission_note": payload.note,
                "updated_at": now(),
            },
            "$inc": {"revision": 1},
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'quality_evaluation_submitted',
        'ProductQualityEvaluation',
        evaluation_id,
        value["project_id"],
        {"note": payload.note},
    )
    return updated


async def review_evaluation(evaluation_id, payload, user):
    value = await get_evaluation(evaluation_id, user, 'qualityevaluation.review')
    if value["status"] != 'IN_REVIEW':
        raise HTTPException(status_code=409, detail={"code": 'QUALITY_EVALUATION_NOT_IN_REVIEW'})
    history = [
        *value.get("reviewed_by", []),
        {"actor_id": user.id, "decision": payload.decision, "note": payload.note, "at": now()},
    ]
    changes = {"reviewed_by": history, "updated_at": now()}
    if payload.decision == 'REQUEST_CHANGES':
        changes["status"] = 'DRAFT'
    updated = await quality_repository.update_evaluation(
        {
            "_id": evaluation_id,
            "revision": payload.expected_revision,
            "status": 'IN_REVIEW',
        },
        {"$set": changes, "$inc": {"revision": 1}},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'quality_evaluation_reviewed',
        'ProductQualityEvaluation',
        evaluation_id,
        value["project_id"],
        {"decision": payload.decision},
    )
    return updated


async def add_waiver(evaluation_id, payload, user):
    value = await get_evaluation(evaluation_id, user, 'qualityevaluation.create')
    if value["status"] not in ['DRAFT', 'IN_REVIEW']:
        raise HTTPException(status_code=409, detail={"code": 'QUALITY_EVALUATION_IMMUTABLE'})
    if payload.expiry_at <= now():
        raise HTTPException(status_code=422, detail={"code": 'WAIVER_EXPIRY_MUST_BE_FUTURE'})
    if not await quality_repository.find_active_member(
        value["project_id"], payload.owner_id, 'ACTIVE'
    ):
        raise HTTPException(
            status_code=422, detail={"code": 'WAIVER_OWNER_NOT_PROJECT_MEMBER'}
        )
    expected_revision = payload.expected_revision or value["revision"]
    waiver = {
        "waiver_id": new_id('WVR'),
        **payload.model_dump(exclude={"expected_revision"}),
        "status": 'PENDING',
        "approved_by": None,
        "created_by": user.id,
        "created_at": now(),
    }
    updated = await quality_repository.update_evaluation(
        {
            "_id": evaluation_id,
            "revision": expected_revision,
            "status": {"$in": ['DRAFT', 'IN_REVIEW']},
        },
        {"$push": {"waivers": waiver}, "$set": {"updated_at": now()}, "$inc": {"revision": 1}},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'STALE_REVISION'})
    await audit(
        user.id,
        'quality_waiver_created',
        'ProductQualityEvaluation',
        evaluation_id,
        value["project_id"],
        {"waiver_id": waiver["waiver_id"], "risk": waiver["risk"]},
    )
    return updated


async def decide_waiver(evaluation_id, waiver_id, payload, user):
    value = await get_evaluation(
        evaluation_id, user, 'qualityevaluation.waiver.approve'
    )
    waiver = next(
        (item for item in value.get("waivers", []) if item["waiver_id"] == waiver_id), None
    )
    if not waiver:
        raise HTTPException(status_code=404, detail={"code": 'WAIVER_NOT_FOUND'})
    if waiver["status"] != 'PENDING':
        raise HTTPException(
            status_code=409, detail={"code": 'WAIVER_ALREADY_DECIDED'}
        )
    waivers = [
        {
            **item,
            "status": 'APPROVED'
            if payload.decision == 'APPROVE'
            else 'REJECTED',
            "approved_by": user.id,
            "approved_at": now(),
            "decision_note": payload.note,
        }
        if item["waiver_id"] == waiver_id
        else item
        for item in value["waivers"]
    ]
    updated = await quality_repository.update_evaluation(
        {
            "_id": evaluation_id,
            "revision": payload.expected_revision,
            "waivers.waiver_id": waiver_id,
        },
        {"$set": {"waivers": waivers, "updated_at": now()}, "$inc": {"revision": 1}},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'quality_waiver_decided',
        'ProductQualityEvaluation',
        evaluation_id,
        value["project_id"],
        {"waiver_id": waiver_id, "decision": payload.decision},
    )
    return updated


async def approve_evaluation(evaluation_id, payload, user):
    value = await get_evaluation(evaluation_id, user, 'qualityevaluation.approve')
    if value["status"] != 'IN_REVIEW':
        raise HTTPException(status_code=409, detail={"code": 'QUALITY_EVALUATION_NOT_IN_REVIEW'})
    if not any(
        item.get("decision") == 'ENDORSE'
        for item in value.get("reviewed_by", [])
    ):
        raise HTTPException(
            status_code=409, detail={"code": 'QUALITY_EVALUATION_ENDORSEMENT_REQUIRED'}
        )
    if any(
        item.get("status") == 'PENDING' for item in value.get("waivers", [])
    ):
        raise HTTPException(status_code=409, detail={"code": 'PENDING_QUALITY_WAIVER'})
    recommendation = value.get("system_recommendation", value.get("recommendation"))
    if (
        value.get("quality_gate_status") == 'FAIL'
        and recommendation in ['GO', 'GO_WITH_RISK']
        and not any(
            item.get("status") == 'APPROVED'
            for item in value.get("waivers", [])
        )
    ):
        raise HTTPException(
            status_code=409, detail={"code": 'FAILED_GATE_REQUIRES_APPROVED_WAIVER'}
        )
    human_decision = await quality_repository.find_latest_decision(
        value["snapshot_id"], value["project_id"]
    )
    timestamp = now()
    updated = await quality_repository.update_evaluation(
        {
            "_id": evaluation_id,
            "revision": payload.expected_revision,
            "status": 'IN_REVIEW',
        },
        {
            "$set": {
                "status": 'APPROVED',
                "approved_by": user.id,
                "approved_at": timestamp,
                "approval_note": payload.note,
                "human_decision": human_decision,
                "quality_decision_id": human_decision.get("_id") if human_decision else None,
                "updated_at": timestamp,
            },
            "$inc": {"revision": 1},
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'product_quality_evaluation_approved',
        'ProductQualityEvaluation',
        evaluation_id,
        value["project_id"],
        {
            "recommendation": recommendation,
            "quality_decision_id": human_decision.get("_id") if human_decision else None,
        },
    )
    return updated


class QualityEvaluationService:
    @staticmethod
    async def list(project_id, release_id, user):
        return await list_evaluations(project_id, release_id, user)

    @staticmethod
    async def create(project_id, payload, user):
        return await create_evaluation(project_id, payload, user)

    @staticmethod
    async def get(evaluation_id, user):
        return await get_evaluation(evaluation_id, user)

    @staticmethod
    async def update(evaluation_id, payload, user):
        return await update_evaluation(evaluation_id, payload, user)

    @staticmethod
    async def submit(evaluation_id, payload, user):
        return await submit_evaluation(evaluation_id, payload, user)

    @staticmethod
    async def review(evaluation_id, payload, user):
        return await review_evaluation(evaluation_id, payload, user)

    @staticmethod
    async def add_waiver(evaluation_id, payload, user):
        return await add_waiver(evaluation_id, payload, user)

    @staticmethod
    async def decide_waiver(evaluation_id, waiver_id, payload, user):
        return await decide_waiver(evaluation_id, waiver_id, payload, user)

    @staticmethod
    async def approve(evaluation_id, payload, user):
        return await approve_evaluation(evaluation_id, payload, user)
