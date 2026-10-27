from copy import deepcopy
import hashlib
import json

from fastapi import HTTPException
from pydantic import ValidationError

from src.core.common import get_project, get_project_entity, now, plain_text
from src.core.database import database
from src.core.human_decisions import require_automation_publication_authority
from src.modules.design.services.linters import duplicate_score, lint_test_case
from src.modules.design.services.test_evidence import requirement_test_evidence_text
from src.repositories.analysis import analysis_repository
from src.repositories.analysis import ActiveTestCaseVersionIntegrityError
from src.repositories.common import common_repository
from src.repositories.test_design import test_design_repository
from src.repositories.test_case_review import test_case_review_repository
from src.schemas.contracts.design import TestCaseDraftCreate, TestCaseDraftPatch, TestStep


async def list_acceptance_criteria_in_session(version_id, session):
    """Read every criterion in a stable order inside the caller's transaction."""
    return await common_repository.list_all_acceptance_criteria(version_id, session)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def validate_merge_replay(
    decision,
    draft,
    *,
    decision_id,
    draft_id,
    project_id,
    actor_id,
    expected_revision,
    request_hash,
):
    """Return a replay receipt only when audit and persisted draft agree."""
    details = decision.get("details") if isinstance(decision, dict) else None
    base_revision = details.get("base_revision") if isinstance(details, dict) else None
    result_revision = details.get("result_revision") if isinstance(details, dict) else None
    merged_ids = draft.get("merge_decision_ids", []) if isinstance(draft, dict) else []
    if (
        not isinstance(decision, dict)
        or decision.get("_id") != decision_id
        or decision.get("project_id") != project_id
        or decision.get("actor_id") != actor_id
        or decision.get("action") != "test_case_merge_saved"
        or decision.get("entity_type") != "TestCaseDraft"
        or decision.get("entity_id") != draft_id
        or not isinstance(details, dict)
        or details.get("request_hash") != request_hash
        or isinstance(base_revision, bool)
        or not isinstance(base_revision, int)
        or base_revision != expected_revision
        or isinstance(result_revision, bool)
        or not isinstance(result_revision, int)
        or result_revision != base_revision + 1
        or not isinstance(draft, dict)
        or draft.get("_id") != draft_id
        or draft.get("project_id") != project_id
        or isinstance(draft.get("revision"), bool)
        or not isinstance(draft.get("revision"), int)
        or draft["revision"] < result_revision
        or not isinstance(merged_ids, list)
        or decision_id not in merged_ids
    ):
        raise HTTPException(409, detail={"code": "TEST_CASE_MERGE_INCOMPLETE"})
    return {"draft": draft, "applied_revision": result_revision, "idempotent": True}


def proposal_snapshot(draft):
    """Capture once at generation, never relabel an edited legacy draft as AI's original."""
    return deepcopy({key: value for key, value in draft.items() if key in TestCaseDraftCreate.model_fields})


def validate_merge_choices(choices, result, original, proposal):
    """Reject audit claims that say a value came from a source but differs from it."""
    scoped_step_choices = {
        choice.get("step_id")
        if isinstance(choice, dict)
        else getattr(choice, "step_id", None)
        for choice in choices
        if str(
            choice.get("field")
            if isinstance(choice, dict)
            else getattr(choice, "field", "")
        ).startswith("steps.")
        and (
            choice.get("step_id")
            if isinstance(choice, dict)
            else getattr(choice, "step_id", None)
        )
    }
    identities = set()
    for choice in choices:
        get = choice.get if isinstance(choice, dict) else lambda key, default=None: getattr(choice, key, default)
        source_name = get("source")
        field = get("field")
        step_id = get("step_id")
        identity = (field, step_id)
        if identity in identities:
            raise HTTPException(422, detail={"code": "MERGE_CHOICE_DUPLICATE", "field": field})
        identities.add(identity)
        if field == "steps" and not step_id and scoped_step_choices:
            continue
        if source_name == "MANUAL":
            continue
        source = proposal if source_name == "AI" else original
        if source is None:
            raise HTTPException(422, detail={"code": "MERGE_SOURCE_UNAVAILABLE"})
        if field == "steps":
            source_steps = source.get("steps") or []
            if step_id:
                source_value = next((step for step in source_steps if step.get("id") == step_id), None)
                result_value = next((step for step in result.get("steps") or [] if step.get("id") == step_id), None)
            else:
                source_value = source_steps
                result_value = result.get("steps") or []
        elif field.startswith("steps."):
            source_step = next((step for step in source.get("steps") or [] if step.get("id") == step_id), None)
            result_step = next((step for step in result.get("steps") or [] if step.get("id") == step_id), None)
            field_name = field.split(".", 1)[1]
            source_present = source_step is not None and field_name in source_step
            source_value = (
                source_step.get(field_name)
                if source_present
                else TestStep.model_fields[field_name].get_default(
                    call_default_factory=True
                )
            )
            result_value = result_step.get(field_name) if result_step else None
            source_present = source_step is not None
        else:
            source_present = field in source
            source_value = (
                source.get(field)
                if source_present
                else TestCaseDraftCreate.model_fields[field].get_default(
                    call_default_factory=True
                )
            )
            result_value = result.get(field)
            source_present = True
        if field == "steps":
            source_present = True
        if not source_present or result_value != source_value:
            raise HTTPException(422, detail={"code": "MERGE_CHOICE_VALUE_MISMATCH", "field": field})


def merge_invalidates_coverage(changed_fields):
    return bool(
        set(changed_fields)
        & {
            "title",
            "objective_doc",
            "preconditions_doc",
            "steps",
            "test_data",
            "expected_result_doc",
            "postconditions_doc",
            "requirement_version_ids",
            "acceptance_criterion_ids",
            "coverage_item_ids",
            "test_condition_ids",
            "bdd",
        }
    )


def ensure_unique_step_ids(test_case):
    steps = test_case.get("steps") or []
    ids = [step.get("id") for step in steps if isinstance(step, dict)]
    if (
        len(ids) != len(steps)
        or any(
            not isinstance(step_id, str)
            or not step_id
            or step_id != step_id.strip()
            for step_id in ids
        )
        or len(ids) != len(set(ids))
    ):
        raise HTTPException(
            409,
            detail={"code": "TEST_CASE_STEP_IDENTITY_CONFLICT"},
        )


async def assert_sources_current_in_session(draft, session):
    """Recheck source/version invariants in the same Mongo transaction as a write."""
    db = database.value
    version_ids = list(dict.fromkeys(draft.get("requirement_version_ids") or []))
    stale = []
    observed_criterion_ids = set()
    expected_source_text = {}
    for version_id in version_ids:
        version = await db.requirement_versions.find_one(
            {"_id": version_id, "project_id": draft["project_id"]}, session=session
        )
        if not version:
            stale.append("REQUIREMENT_VERSION_MISSING")
            continue
        requirement = await db.requirements.find_one(
            {"_id": version.get("requirement_id"), "project_id": draft["project_id"]},
            {"current_version_id": 1},
            session=session,
        )
        if not requirement or requirement.get("current_version_id") != version_id or version.get("status") != "BASELINED":
            stale.append("REQUIREMENT_VERSION_CHANGED")
        criteria = await list_acceptance_criteria_in_session(version_id, session)
        observed_criterion_ids.update(criterion["_id"] for criterion in criteria)
        expected_source_text[version_id] = requirement_test_evidence_text(version)
        expected_source_text.update(
            {
                criterion["_id"]: criterion.get("plain_text")
                or plain_text(criterion.get("content_doc", {}))
                for criterion in criteria
            }
        )
    proposal = draft.get("ai_proposal_snapshot") or {}
    for evidence in proposal.get("source_evidence", []):
        artifact_id = evidence.get("artifact_version_id")
        if expected_source_text.get(artifact_id) != evidence.get("text"):
            stale.append("SOURCE_EVIDENCE_CHANGED")
    snapshot_ids = draft.get("review_acceptance_criteria_snapshot_ids")
    if snapshot_ids is not None and set(snapshot_ids) != observed_criterion_ids:
        stale.append("ACCEPTANCE_CRITERIA_CHANGED")
    parent_id = draft.get("parent_version_id")
    if parent_id:
        parent = await db.test_case_versions.find_one(
            {"_id": parent_id, "project_id": draft["project_id"]},
            {"test_case_id": 1}, session=session,
        )
        case = await db.test_cases.find_one(
            {"_id": parent.get("test_case_id"), "project_id": draft["project_id"]},
            {"current_version_id": 1}, session=session,
        ) if parent else None
        if not parent or not case or case.get("current_version_id") != parent_id:
            stale.append("TEST_CASE_BASE_VERSION_CHANGED")
    if stale:
        from fastapi import HTTPException

        raise HTTPException(409, detail={"code": "TEST_CASE_COMPARISON_STALE", "reasons": sorted(set(stale))})


async def validate_test_case_publication_uniqueness(draft, threshold, session):
    """Serialize publication per project and recheck duplicates inside its transaction.

    The project write is a transaction fence: concurrent approval transactions conflict
    and retry against the newly committed active versions instead of both publishing a
    semantic duplicate from stale preflight comparisons.
    """
    db = database.value
    project_update = await db.projects.update_one(
        {"_id": draft["project_id"]},
        {"$inc": {"test_case_publication_revision": 1}},
        session=session,
    )
    if project_update.matched_count != 1:
        raise HTTPException(404, detail={"code": "PROJECT_NOT_FOUND"})
    project = await db.projects.find_one(
        {"_id": draft["project_id"]},
        {"settings": 1},
        session=session,
    )
    if not project:
        raise HTTPException(404, detail={"code": "PROJECT_NOT_FOUND"})
    threshold = (project.get("settings") or {}).get(
        "testcase_duplicate_threshold", threshold
    )

    parent_case_id = None
    parent_version_id = draft.get("parent_version_id")
    if parent_version_id:
        parent = await db.test_case_versions.find_one(
            {"_id": parent_version_id, "project_id": draft["project_id"]},
            {"test_case_id": 1},
            session=session,
        )
        if not parent:
            raise HTTPException(409, detail={"code": "TEST_CASE_BASE_VERSION_CHANGED"})
        parent_case_id = parent.get("test_case_id")

    duplicates = []
    last_case_id = None
    while True:
        query = {
            "project_id": draft["project_id"],
            "status": "ACTIVE",
            "current_version_id": {"$ne": None},
        }
        if last_case_id is not None:
            query["_id"] = {"$gt": last_case_id}
        active_cases = await db.test_cases.find(
            query,
            {"_id": 1, "current_version_id": 1, "test_case_key": 1},
            session=session,
        ).sort("_id", 1).to_list(500)
        if not active_cases:
            break
        version_ids = [case["current_version_id"] for case in active_cases]
        versions = await db.test_case_versions.find(
            {
                "_id": {"$in": version_ids},
                "project_id": draft["project_id"],
            },
            session=session,
        ).to_list(len(version_ids))
        versions_by_id = {version["_id"]: version for version in versions}
        for case in active_cases:
            version = versions_by_id.get(case["current_version_id"])
            if not version or version.get("test_case_id") != case["_id"]:
                raise HTTPException(
                    409,
                    detail={
                        "code": "TEST_CASE_CURRENT_VERSION_MISSING",
                        "test_case_id": case["_id"],
                    },
                )
            if version.get("test_case_id") == parent_case_id:
                continue
            score, reasons = duplicate_score(draft, version, threshold)
            if score >= threshold:
                duplicates.append({
                    "test_case_id": version.get("test_case_id"),
                    "version_id": version.get("_id"),
                    "test_case_key": case.get("test_case_key"),
                    "title": version.get("title"),
                    "version": version.get("version"),
                    "score": score,
                    "reasons": reasons,
                })
        last_case_id = active_cases[-1]["_id"]
        if len(active_cases) < 500:
            break
    if duplicates and not str(draft.get("duplicate_reason") or "").strip():
        raise HTTPException(
            409,
            detail={
                "code": "TEST_CASE_DUPLICATE_REVIEW_REQUIRED",
                "matches": sorted(duplicates, key=lambda item: (-item["score"], item.get("test_case_key") or "")),
                "message": "Ca này gần trùng với ca đang hiệu lực; QA cần ghi lý do xác nhận vẫn giữ riêng trước khi duyệt.",
            },
        )


async def comparison_sources(draft):
    project_id = draft["project_id"]
    version_ids = list(dict.fromkeys(draft.get("requirement_version_ids") or []))
    versions = await analysis_repository.list_requirement_versions(project_id, version_ids, len(version_ids)) if version_ids else []
    reasons = []
    if len(versions) != len(version_ids):
        reasons.append("REQUIREMENT_VERSION_MISSING")
    current_sources = []
    expected = {}
    criterion_ids = []
    for version in versions:
        current = await test_design_repository.find_current_requirement(project_id, version["requirement_id"])
        if not current or current.get("current_version_id") != version["_id"] or version.get("status") != "BASELINED":
            reasons.append("REQUIREMENT_VERSION_CHANGED")
        text = requirement_test_evidence_text(version)
        expected[version["_id"]] = text
        criteria = await analysis_repository.list_acceptance_criteria(version["_id"], None)
        criterion_ids.extend(item["_id"] for item in criteria)
        for criterion in criteria:
            expected[criterion["_id"]] = criterion.get("plain_text") or plain_text(criterion.get("content_doc", {}))
        current_sources.append({"version_id": version["_id"], "revision": version.get("revision"), "text_hash": fingerprint(text), "current_version_id": (current or {}).get("current_version_id"), "criteria": [{"id": item["_id"], "revision": item.get("revision"), "text_hash": fingerprint(expected[item["_id"]])} for item in sorted(criteria, key=lambda item: item["_id"])]})
    original = draft.get("ai_proposal_snapshot")
    if original:
        for evidence in original.get("source_evidence", []):
            if expected.get(evidence.get("artifact_version_id")) != evidence.get("text"):
                reasons.append("SOURCE_EVIDENCE_CHANGED")
        snapshot_ids = draft.get("review_acceptance_criteria_snapshot_ids")
        if snapshot_ids is not None and set(snapshot_ids) != set(criterion_ids):
            reasons.append("ACCEPTANCE_CRITERIA_CHANGED")
    parent = None
    parent_id = draft.get("parent_version_id")
    if parent_id:
        parent = await test_design_repository.find_case_version(parent_id, project_id)
        case = await test_design_repository.find_case(parent["test_case_id"], project_id) if parent else None
        if not parent or not case or case.get("current_version_id") != parent_id:
            reasons.append("TEST_CASE_BASE_VERSION_CHANGED")
    return {"sources": sorted(current_sources, key=lambda item: item["version_id"]), "parent": parent, "stale_reasons": sorted(set(reasons))}


async def review_context(draft_id, user, permission="testcase.read"):
    draft = await get_project_entity("test_case_drafts", draft_id, user, permission)
    draft = {"test_level": None, "test_kind": None, "expected_impact": "unassessed", "assessment_reason": "", **draft}
    sources = await comparison_sources(draft)
    settings = await test_design_repository.find_project_settings(draft["project_id"])
    custom_fields = await test_design_repository.list_all_test_case_custom_fields(
        draft["project_id"]
    )
    threshold = settings.get("testcase_duplicate_threshold", 0.72)
    duplicates = []
    parent_case_id = (sources["parent"] or {}).get("test_case_id")
    try:
        async for active_versions in analysis_repository.iter_active_test_case_version_pages(
            draft["project_id"], "ACTIVE"
        ):
            for candidate in active_versions:
                if candidate.get("test_case_id") == parent_case_id:
                    continue
                score, reasons = duplicate_score(draft, candidate, threshold)
                if score >= threshold:
                    duplicates.append({"test_case_id": candidate.get("test_case_id"), "version_id": candidate.get("_id"), "test_case_key": candidate.get("test_case_key"), "title": candidate.get("title"), "version": candidate.get("version"), "score": score, "reasons": reasons})
    except ActiveTestCaseVersionIntegrityError as error:
        raise HTTPException(
            409,
            detail={"code": "TEST_CASE_CURRENT_VERSION_MISSING"},
        ) from error
    token = fingerprint(
        {
            "draft_id": draft_id,
            "revision": draft["revision"],
            "user_id": user.id,
            "sources": sources["sources"],
            "parent_version_id": (sources["parent"] or {}).get("_id"),
            "proposal": draft.get("ai_proposal_snapshot"),
            "custom_fields": custom_fields,
        }
    )
    return {
        "draft": draft, "original": sources["parent"], "proposal": draft.get("ai_proposal_snapshot"),
        "proposal_available": bool(draft.get("ai_proposal_snapshot")),
        "source_evidence": draft.get("source_evidence", []),
        "custom_fields": custom_fields,
        "comparison_token": token, "stale_reasons": sources["stale_reasons"],
        "is_new": not bool(draft.get("parent_version_id")),
        "duplicates": sorted(duplicates, key=lambda item: (-item["score"], item.get("test_case_key") or "")),
        "findings": lint_test_case(draft),
    }


async def save_merged_test_case(draft_id, payload, user):
    require_automation_publication_authority(user)
    context = await review_context(draft_id, user, "testcase.update")
    draft = context["draft"]
    decision_id = "TCMERGE-" + fingerprint([draft_id, payload.operation_id])
    request_hash = fingerprint(payload.model_dump())
    previous = await test_case_review_repository.find_decision(decision_id)
    if previous:
        details = previous.get("details") or {}
        if (
            previous.get("actor_id") != user.id
            or details.get("request_hash") != request_hash
        ):
            raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        return validate_merge_replay(
            previous,
            draft,
            decision_id=decision_id,
            draft_id=draft_id,
            project_id=draft["project_id"],
            actor_id=user.id,
            expected_revision=payload.expected_revision,
            request_hash=request_hash,
        )
    if draft["revision"] != payload.expected_revision:
        raise HTTPException(409, detail={"code": "REVISION_CONFLICT", "current_revision": draft["revision"]})
    if context["stale_reasons"] or context["comparison_token"] != payload.comparison_token:
        raise HTTPException(409, detail={"code": "TEST_CASE_COMPARISON_STALE", "reasons": context["stale_reasons"]})
    if draft.get("status") not in {"DRAFT", "IN_REVIEW"}:
        raise HTTPException(409, detail={"code": "IMMUTABLE_TEST_CASE_DRAFT"})
    ensure_unique_step_ids(draft)
    ensure_unique_step_ids(payload.result.model_dump())
    if context["original"]:
        ensure_unique_step_ids(context["original"])
    if context["proposal"]:
        ensure_unique_step_ids(context["proposal"])
    allowed = set(TestCaseDraftPatch.model_fields) - {"expected_revision"}
    step_fields = {"steps." + key for key in TestStep.model_fields}
    step_fields.add("steps")
    step_ids = {step.get("id") for step in draft.get("steps", [])}
    step_ids.update(step.get("id") for step in (draft.get("ai_proposal_snapshot") or {}).get("steps", []))
    step_ids.update(step.get("id") for step in (context.get("original") or {}).get("steps", []))
    for choice in payload.choices:
        if choice.field not in allowed | step_fields:
            raise HTTPException(422, detail={"code": "INVALID_MERGE_FIELD"})
        if (
            choice.field.startswith("steps.") or choice.field == "steps"
        ) and choice.step_id and choice.step_id not in step_ids:
            raise HTTPException(422, detail={"code": "INVALID_MERGE_STEP"})
        if choice.field.startswith("steps.") and not choice.step_id:
            raise HTTPException(422, detail={"code": "INVALID_MERGE_STEP"})
        if choice.source == "AI" and not context["proposal_available"]:
            raise HTTPException(422, detail={"code": "AI_PROPOSAL_SNAPSHOT_UNAVAILABLE"})
        if choice.source == "ORIGINAL" and not context["original"]:
            raise HTTPException(422, detail={"code": "ORIGINAL_TEST_CASE_UNAVAILABLE"})
    values = payload.result.model_dump()
    validate_merge_choices(payload.choices, values, context["original"], context["proposal"])
    changes = {key: values[key] for key in allowed if values[key] != draft.get(key)}
    from src.modules.design.services.test_case_records import validate_test_case_owner
    if "owner_id" in changes:
        await get_project(draft["project_id"], user, "project.members.read")
        values["owner_id"] = await validate_test_case_owner(
            draft["project_id"], changes["owner_id"]
        )
        changes["owner_id"] = values["owner_id"]
    if "attachments" in changes:
        await get_project(draft["project_id"], user, "attachment.manage")
    from src.modules.design.services.test_case_records import validate_design_sources, validate_data_set_versions, validate_test_design_structure, validate_coverage_items
    from src.modules.design.services.test_case_custom_fields import validate_test_case_custom_values
    await validate_design_sources(draft["project_id"], values["requirement_version_ids"], values["acceptance_criterion_ids"], values["scenario_id"], values["test_condition_ids"])
    await validate_data_set_versions(draft["project_id"], values["data_set_version_ids"])
    await validate_test_design_structure(draft["project_id"], values["repository_node_id"], payload.result.bdd)
    await validate_coverage_items(draft["project_id"], values["requirement_version_ids"], values["coverage_item_ids"])
    await validate_test_case_custom_values(draft["project_id"], values["custom_values"])
    merged = {**draft, **changes}
    proposal = draft.get("ai_proposal_snapshot")
    if proposal and not merged.get("evidence_refs"):
        for key in ("evidence_refs", "evidence_quotes", "source_evidence"):
            changes[key] = deepcopy(proposal.get(key, []))
            merged[key] = changes[key]
    if merge_invalidates_coverage(changes):
        merged["coverage_obligations"] = []
        merged["challenge_hypotheses"] = []
        changes.update({"coverage_obligations": [], "challenge_hypotheses": []})
    try:
        TestCaseDraftCreate.model_validate(merged)
    except ValidationError as error:
        raise HTTPException(422, detail={"code": "TEST_CASE_MERGE_INVALID", "message": "Bản ghép chưa hợp lệ; kiểm tra các trường, bước và nguồn dẫn."}) from error
    final_sources = await comparison_sources(merged)
    if final_sources["stale_reasons"]:
        raise HTTPException(409, detail={"code": "TEST_CASE_COMPARISON_STALE", "reasons": final_sources["stale_reasons"]})
    timestamp = now()
    changes.update({"status": "DRAFT", "updated_at": timestamp, "last_merge_decision_id": decision_id})
    decision = {"_id": decision_id, "project_id": draft["project_id"], "actor_id": user.id, "action": "test_case_merge_saved", "entity_type": "TestCaseDraft", "entity_id": draft_id, "created_at": timestamp, "details": {"request_hash": request_hash, "base_revision": draft["revision"], "result_revision": draft["revision"] + 1, "choices": [item.model_dump() for item in payload.choices], "changed_fields": sorted(changes), "previous_values": {key: draft.get(key) for key in changes if key not in {"updated_at"}}, "new_values": {key: value for key, value in changes.items() if key != "updated_at"}, "comparison_token": payload.comparison_token}}
    result = await test_case_review_repository.merge(draft, changes, decision)
    result["findings"] = lint_test_case(result["draft"])
    return result


async def validate_review_sources_before_approval(draft):
    try:
        TestCaseDraftCreate.model_validate(draft)
    except ValidationError as error:
        raise HTTPException(422, detail={"code": "TEST_CASE_MERGE_INVALID"}) from error
    ensure_unique_step_ids(draft)
    if draft.get("expected_impact", "unassessed") != "unassessed" and not str(draft.get("assessment_reason") or "").strip():
        raise HTTPException(409, detail={"code": "TEST_CASE_IMPACT_REASON_REQUIRED", "message": "Cần ghi lý do đánh giá ảnh hưởng trước khi duyệt."})
    state = await comparison_sources(draft)
    if state["stale_reasons"]:
        raise HTTPException(409, detail={"code": "TEST_CASE_COMPARISON_STALE", "reasons": state["stale_reasons"]})
