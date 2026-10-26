from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.modules.quality.services.causal_analysis_automation import generate_hypotheses
from src.modules.quality.services.causal_analysis_query import (
    get_analysis,
    latest_hypothesis_result,
    list_analyses,
    suggest_candidates,
    validate_member,
)
from src.repositories.causal_analysis import causal_analysis_repository


async def create_analysis(project_id, payload, user):
    await get_project(project_id, user, "causalanalysis.create")
    defect_ids = list(dict.fromkeys(payload.defect_ids))
    if defect_ids:
        defects = await causal_analysis_repository.list_defects(
            {"_id": {"$in": defect_ids}, "project_id": project_id}, 1000
        )
        if len(defects) != len(defect_ids):
            raise HTTPException(status_code=422, detail={"code": "DEFECT_NOT_IN_PROJECT"})
    source_event = payload.source_event_id is not None
    source_automation_run_id = None
    if source_event:
        source_automation_run_id = getattr(user, "_ai_automation_run_id", None)
        if (
            not source_automation_run_id
            or getattr(user, "_ai_automation_trigger", None) != payload.source_event_trigger
            or getattr(user, "_ai_automation_source_event_id", None) != payload.source_event_id
            or len(defect_ids) != 1
        ):
            raise HTTPException(status_code=403, detail={"code": "VERIFIED_DEFECT_EVENT_REQUIRED"})
        expected_event_id = f"defect:{defect_ids[0]}:{payload.source_event_revision}"
        if payload.source_event_id != expected_event_id:
            raise HTTPException(status_code=409, detail={"code": "DEFECT_EVENT_IDENTITY_MISMATCH"})
        current_defect = await causal_analysis_repository.list_defects(
            {"_id": defect_ids[0], "project_id": project_id}, 1
        )
        if not current_defect or current_defect[0].get("revision") != payload.source_event_revision:
            raise HTTPException(status_code=409, detail={"code": "DEFECT_EVENT_SUPERSEDED"})
    await validate_member(project_id, payload.owner_id)
    if payload.idempotency_key:
        existing = await causal_analysis_repository.find_analysis_by_idempotency(
            project_id, payload.idempotency_key
        )
        if existing:
            if (
                set(existing.get("defect_ids", [])) != set(defect_ids)
                or existing.get("source_event_id") != payload.source_event_id
                or existing.get("source_event_revision") != payload.source_event_revision
                or existing.get("source_event_trigger") != payload.source_event_trigger
                or existing.get("source_automation_run_id") != source_automation_run_id
            ):
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            return existing
    timestamp = now()
    identifier = new_id("RCA")
    data = payload.model_dump(exclude={"evidence"})
    value = {
        "_id": identifier,
        "analysis_key": identifier,
        "project_id": project_id,
        **data,
        "source_automation_run_id": source_automation_run_id,
        "defect_ids": defect_ids,
        "root_causes": [],
        "contributing_factors": [],
        "five_whys": [],
        "corrective_actions": [],
        "preventive_actions": [],
        "approved_by": None,
        "effectiveness_reviews": [],
        "status": "DRAFT",
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        await causal_analysis_repository.insert_analysis(value)
    except DuplicateKeyError:
        if payload.idempotency_key:
            return await causal_analysis_repository.find_analysis_by_idempotency(
                project_id, payload.idempotency_key
            )
        raise
    await audit(
        user.id,
        "causal_analysis_created",
        "CausalAnalysis",
        value["_id"],
        project_id,
        {"defect_ids": defect_ids},
    )
    return value


async def update_analysis(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.update")
    if value["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_NOT_DRAFT"})
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if "owner_id" in changes:
        await validate_member(value["project_id"], changes["owner_id"])
    changes["updated_at"] = now()
    updated = await causal_analysis_repository.update_analysis(
        {"_id": analysis_id, "revision": payload.expected_revision, "status": "DRAFT"}, changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        "causal_analysis_updated",
        "CausalAnalysis",
        analysis_id,
        value["project_id"],
        {"fields": sorted(changes)},
    )
    return updated


async def link_defects(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.update")
    if value["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_NOT_DRAFT"})
    defect_ids = list(dict.fromkeys(payload.defect_ids))
    defects = await causal_analysis_repository.list_defects(
        {"_id": {"$in": defect_ids}, "project_id": value["project_id"]}, 1000
    )
    if len(defects) != len(defect_ids):
        raise HTTPException(status_code=422, detail={"code": "DEFECT_NOT_IN_PROJECT"})
    linked = list(dict.fromkeys([*value.get("defect_ids", []), *defect_ids]))
    updated = await causal_analysis_repository.update_analysis(
        {"_id": analysis_id, "revision": payload.expected_revision, "status": "DRAFT"},
        {"defect_ids": linked, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        "causal_analysis_defects_linked",
        "CausalAnalysis",
        analysis_id,
        value["project_id"],
        {"defect_ids": defect_ids},
    )
    return updated


async def add_five_why(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.update")
    if value["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_NOT_DRAFT"})
    five_whys = list(value.get("five_whys", []))
    if len(five_whys) >= 5:
        raise HTTPException(status_code=409, detail={"code": "FIVE_WHYS_LIMIT_REACHED"})
    five_whys.append(payload.why)
    updated = await causal_analysis_repository.update_analysis(
        {"_id": analysis_id, "revision": payload.expected_revision, "status": "DRAFT"},
        {"five_whys": five_whys, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        "causal_analysis_five_why_added",
        "CausalAnalysis",
        analysis_id,
        value["project_id"],
        {"sequence": len(five_whys)},
    )
    return updated


async def record_root_cause(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.update")
    if value["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_NOT_DRAFT"})
    root_cause = {
        "category": payload.category,
        "detail": payload.detail,
        "evidence_refs": payload.evidence_refs,
        "recorded_by": user.id,
        "recorded_at": now(),
    }
    updated = await causal_analysis_repository.update_analysis(
        {"_id": analysis_id, "revision": payload.expected_revision, "status": "DRAFT"},
        {
            "root_causes": [root_cause],
            "contributing_factors": payload.contributing_factors,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        "causal_analysis_root_cause_recorded",
        "CausalAnalysis",
        analysis_id,
        value["project_id"],
        {"category": payload.category},
    )
    return updated


async def create_action(analysis_id, payload, user, action_type):
    value = await get_analysis(analysis_id, user, "preventionaction.manage")
    if value["status"] not in {"APPROVED", "ACTION_IN_PROGRESS"}:
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_NOT_APPROVED"})
    if value["status"] == "CLOSED":
        raise HTTPException(status_code=409, detail={"code": "CLOSED_CAUSAL_ANALYSIS_IMMUTABLE"})
    timestamp = now()
    action = {
        "_id": new_id("CAPA"),
        "causal_analysis_id": analysis_id,
        "project_id": value["project_id"],
        **payload.model_dump(),
        "action_type": action_type,
        "owner_id": None,
        "status": "OPEN",
        "result": "",
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await causal_analysis_repository.insert_action(action)
    field = "corrective_actions" if action_type == "CORRECTIVE" else "preventive_actions"
    analysis = await causal_analysis_repository.update_analysis(
        {
            "_id": analysis_id,
            "revision": value["revision"],
            "status": {"$in": ["APPROVED", "ACTION_IN_PROGRESS"]},
        },
        {"status": "ACTION_IN_PROGRESS", "updated_at": timestamp},
        {field: action["_id"]},
    )
    if not analysis:
        await causal_analysis_repository.delete_action(action["_id"])
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        "capa_action_created",
        "PreventionAction",
        action["_id"],
        value["project_id"],
        {"causal_analysis_id": analysis_id, "type": action_type},
    )
    return action


async def assign_action(action_id, payload, user):
    action = await causal_analysis_repository.find_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    await get_project(action["project_id"], user, "preventionaction.manage")
    await validate_member(action["project_id"], payload.owner_id)
    if action["status"] == "CLOSED":
        raise HTTPException(status_code=409, detail={"code": "CAPA_ACTION_CLOSED"})
    timestamp = now()
    updated = await causal_analysis_repository.update_action(
        {"_id": action_id, "revision": payload.expected_revision, "status": {"$ne": "CLOSED"}},
        {
            "owner_id": payload.owner_id,
            "assigned_by": user.id,
            "assigned_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        "capa_action_assigned",
        "PreventionAction",
        action_id,
        action["project_id"],
        {"owner_id": payload.owner_id},
    )
    return updated


async def update_action(action_id, payload, user):
    action = await causal_analysis_repository.find_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    await get_project(action["project_id"], user, "preventionaction.manage")
    if payload.status != "OPEN" and not action.get("owner_id"):
        raise HTTPException(status_code=409, detail={"code": "CAPA_ACTION_OWNER_REQUIRED"})

    if ["OPEN", "IN_PROGRESS", "IMPLEMENTED", "EFFECTIVENESS_REVIEW", "CLOSED"].index(
        payload.status
    ) < ["OPEN", "IN_PROGRESS", "IMPLEMENTED", "EFFECTIVENESS_REVIEW", "CLOSED"].index(
        action["status"]
    ) or ["OPEN", "IN_PROGRESS", "IMPLEMENTED", "EFFECTIVENESS_REVIEW", "CLOSED"].index(
        payload.status
    ) > ["OPEN", "IN_PROGRESS", "IMPLEMENTED", "EFFECTIVENESS_REVIEW", "CLOSED"].index(
        action["status"]
    ) + 1:
        raise HTTPException(status_code=409, detail={"code": "INVALID_CAPA_TRANSITION"})
    changes = {"status": payload.status, "result": payload.result, "updated_at": now()}
    if payload.evidence_refs is not None:
        changes["evidence_refs"] = payload.evidence_refs
    updated = await causal_analysis_repository.update_action(
        {"_id": action_id, "revision": payload.expected_revision, "status": action["status"]},
        changes,
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    event = "preventive_action_closed" if payload.status == "CLOSED" else "capa_action_updated"
    await audit(
        user.id,
        event,
        "PreventionAction",
        action_id,
        action["project_id"],
        {"from": action["status"], "to": payload.status},
    )
    return updated


async def submit_review(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.update")
    if not value.get("defect_ids"):
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_DEFECT_REQUIRED"})
    if not value.get("five_whys"):
        raise HTTPException(status_code=409, detail={"code": "FIVE_WHYS_REQUIRED"})
    if not value.get("root_causes"):
        raise HTTPException(status_code=409, detail={"code": "ROOT_CAUSE_REQUIRED"})
    timestamp = now()
    updated = await causal_analysis_repository.update_analysis(
        {"_id": analysis_id, "revision": payload.expected_revision, "status": "DRAFT"},
        {
            "status": "IN_REVIEW",
            "submitted_by": user.id,
            "submitted_at": timestamp,
            "review_note": payload.note,
            "updated_at": timestamp,
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_SUBMIT_CONFLICT"})
    await audit(
        user.id,
        "causal_analysis_submitted",
        "CausalAnalysis",
        analysis_id,
        value["project_id"],
        {"note": payload.note},
    )
    return updated


async def approve_analysis(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.approve")
    target = "APPROVED" if payload.decision == "APPROVE" else "DRAFT"
    timestamp = now()
    changes = {
        "status": target,
        "approval_note": payload.note,
        "reviewed_by": user.id,
        "reviewed_at": timestamp,
        "updated_at": timestamp,
    }
    if target == "APPROVED":
        changes.update({"approved_by": user.id, "approved_at": timestamp})
    else:
        changes.update({"approved_by": None, "approved_at": None})
    updated = await causal_analysis_repository.update_analysis(
        {"_id": analysis_id, "revision": payload.expected_revision, "status": "IN_REVIEW"}, changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_REVIEW_CONFLICT"})
    event = "causal_analysis_approved" if target == "APPROVED" else "causal_analysis_reviewed"
    await audit(
        user.id,
        event,
        "CausalAnalysis",
        analysis_id,
        value["project_id"],
        {"decision": payload.decision},
    )
    return updated


async def review_effectiveness(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.update")
    if value["status"] != "ACTION_IN_PROGRESS":
        raise HTTPException(
            status_code=409, detail={"code": "CAUSAL_ANALYSIS_ACTIONS_NOT_IN_PROGRESS"}
        )
    actions = await causal_analysis_repository.list_actions(analysis_id, 1000)
    if not actions or any(
        item["status"] not in ["IMPLEMENTED", "EFFECTIVENESS_REVIEW", "CLOSED"] for item in actions
    ):
        raise HTTPException(status_code=409, detail={"code": "CAPA_ACTIONS_NOT_IMPLEMENTED"})
    review = {
        "decision": payload.decision,
        "result": payload.result,
        "evidence_refs": payload.evidence_refs,
        "reviewed_at": payload.reviewed_at,
        "reviewed_by": user.id,
    }
    reviews = [*value.get("effectiveness_reviews", []), review]
    target = "EFFECTIVENESS_REVIEW" if payload.decision == "EFFECTIVE" else "ACTION_IN_PROGRESS"
    updated = await causal_analysis_repository.update_analysis(
        {"_id": analysis_id, "revision": payload.expected_revision, "status": "ACTION_IN_PROGRESS"},
        {
            "status": target,
            "effectiveness_reviews": reviews,
            "effectiveness_review_at": payload.reviewed_at,
            "updated_at": now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        "causal_analysis_effectiveness_reviewed",
        "CausalAnalysis",
        analysis_id,
        value["project_id"],
        {"decision": payload.decision, "evidence_refs": payload.evidence_refs},
    )
    return updated


async def close_analysis(analysis_id, payload, user):
    value = await get_analysis(analysis_id, user, "causalanalysis.approve")
    actions = await causal_analysis_repository.list_actions(analysis_id, 1000)
    if not actions or any(item["status"] != "CLOSED" for item in actions):
        raise HTTPException(status_code=409, detail={"code": "CAPA_ACTIONS_NOT_CLOSED"})
    if (
        not value.get("effectiveness_reviews")
        or value["effectiveness_reviews"][-1].get("decision") != "EFFECTIVE"
    ):
        raise HTTPException(status_code=409, detail={"code": "EFFECTIVENESS_APPROVAL_REQUIRED"})
    timestamp = now()
    updated = await causal_analysis_repository.update_analysis(
        {
            "_id": analysis_id,
            "revision": payload.expected_revision,
            "status": "EFFECTIVENESS_REVIEW",
        },
        {
            "status": "CLOSED",
            "closed_by": user.id,
            "closed_at": timestamp,
            "close_note": payload.note,
            "updated_at": timestamp,
        },
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "CAUSAL_ANALYSIS_CLOSE_CONFLICT"})
    await audit(
        user.id,
        "causal_analysis_closed",
        "CausalAnalysis",
        analysis_id,
        value["project_id"],
        {"note": payload.note},
    )
    return updated


class CausalAnalysisService:
    @staticmethod
    async def list(project_id, user):
        return await list_analyses(project_id, user)

    @staticmethod
    async def candidates(project_id, user):
        return await suggest_candidates(project_id, user)

    @staticmethod
    async def create(project_id, payload, user):
        return await create_analysis(project_id, payload, user)

    @staticmethod
    async def get(analysis_id, user):
        value = await get_analysis(analysis_id, user)
        value["actions"] = await causal_analysis_repository.list_actions(analysis_id, 1000)
        return value

    @staticmethod
    async def update(analysis_id, payload, user):
        return await update_analysis(analysis_id, payload, user)

    @staticmethod
    async def link_defects(analysis_id, payload, user):
        return await link_defects(analysis_id, payload, user)

    @staticmethod
    async def add_five_why(analysis_id, payload, user):
        return await add_five_why(analysis_id, payload, user)

    @staticmethod
    async def record_root_cause(analysis_id, payload, user):
        return await record_root_cause(analysis_id, payload, user)

    @staticmethod
    async def create_action(analysis_id, payload, user, action_type):
        return await create_action(analysis_id, payload, user, action_type)

    @staticmethod
    async def assign_action(action_id, payload, user):
        return await assign_action(action_id, payload, user)

    @staticmethod
    async def update_action(action_id, payload, user):
        return await update_action(action_id, payload, user)

    @staticmethod
    async def submit_review(analysis_id, payload, user):
        return await submit_review(analysis_id, payload, user)

    @staticmethod
    async def approve(analysis_id, payload, user):
        return await approve_analysis(analysis_id, payload, user)

    @staticmethod
    async def review_effectiveness(analysis_id, payload, user):
        return await review_effectiveness(analysis_id, payload, user)

    @staticmethod
    async def close(analysis_id, payload, user):
        return await close_analysis(analysis_id, payload, user)

    @staticmethod
    async def generate_hypotheses(analysis_id, payload, user):
        return await generate_hypotheses(analysis_id, payload, user)

    @staticmethod
    async def latest_hypothesis_result(analysis_id, user):
        return await latest_hypothesis_result(analysis_id, user)
