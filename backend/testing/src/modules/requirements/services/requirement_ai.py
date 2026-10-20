import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_entity, new_id, now, plain_text, validate_doc
from src.repositories.requirement_ai import requirement_ai_repository
from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.modules.design.services.linters import requirement_findings
from src.modules.requirements.services.requirement_records import persist_acceptance_criteria
from src.modules.requirements.services.requirement_workflow import (
    prepare_requirement_ai_suggestion,
    requirement_suggestion_changes,
    text_doc,
)


async def analyze_requirement_quality(version_id, payload, user):
    
    version = await get_project_entity("requirement_versions", version_id, user, "ai.run_lint")
    query = {
        "project_id": version["project_id"],
        "artifact_id": version_id,
        "result_type": 'REQUIREMENT_QUALITY_ANALYSIS',
        "idempotency_key": payload.idempotency_key,
    }
    existing = await requirement_ai_repository.find_finding(query)
    if existing:
        return existing
    acceptance_criteria = await requirement_ai_repository.list_acceptance_criteria(
        version_id, 200
    )
    deterministic_findings = [
        {
            **item,
            "origin": 'RULE',
            "evidence_refs": [version_id],
            "reason_codes": [item["rule_id"]],
        }
        for item in requirement_findings(version, acceptance_criteria)
    ]
    evidence = [
        {
            "artifact_type": "requirement_version",
            "artifact_id": version.get("requirement_id"),
            "artifact_version_id": version_id,
            "authority": 'PROJECT_BASELINE'
            if version.get("status") == 'BASELINED'
            else 'DRAFT',
            "text": json.dumps(
                {
                    "title": version.get("title"),
                    "content": version.get("plain_text_projection")
                    or plain_text(version.get("content_doc", {})),
                    "actors": version.get("actors", []),
                    "business_rules": version.get("business_rules", []),
                    "acceptance_criteria": [
                        str(item.get("plain_text") or "").strip()
                        for item in acceptance_criteria
                        if str(item.get("plain_text") or "").strip()
                    ],
                    "dependencies": version.get("dependencies", []),
                    "tags": version.get("tags", []),
                },
                ensure_ascii=False,
            ),
        }
    ]
    instruction = json.dumps({"user_instruction": payload.instruction}, ensure_ascii=False)
    ai_result = await request_ai_automation(
        "requirement_quality_analysis", version["project_id"], instruction, evidence
    )
    ai_findings = [
        {
            **item,
            "rule_id": item.get(
                "reason_codes", [item.get("category", 'AI_FINDING')]
            )[0],
            "origin": 'AI',
            "span": None,
        }
        for item in ai_result.get("findings", [])
    ]
    aggregate = {"patch": {}, "target_fields": [], "evidence_refs": [], "reason_codes": []}
    for candidate in ai_result.get("suggestions", []):
        ai_suggestion = prepare_requirement_ai_suggestion(candidate, acceptance_criteria)
        if not requirement_suggestion_changes(version, ai_suggestion, acceptance_criteria):
            continue
        for field in ("revised_title", "revised_content", "rationale"):
            if ai_suggestion.get(field):
                aggregate[field] = ai_suggestion[field]
        if isinstance(ai_suggestion.get("patch"), dict):
            aggregate["patch"].update(ai_suggestion["patch"])
        for field in ("target_fields", "evidence_refs", "reason_codes"):
            aggregate[field] = list(
                dict.fromkeys([*aggregate[field], *ai_suggestion.get(field, [])])
            )
    aggregate["origin"] = 'AI'
    suggestions = []
    if requirement_suggestion_changes(version, aggregate, acceptance_criteria):
        suggestions.append(
            {
                **aggregate,
                "suggestion_id": 'REQ-SUG-1',
                "status": 'CANDIDATE',
                "candidate_only": True,
            }
        )
    findings = deterministic_findings + ai_findings
    result = {
        "_id": new_id('AIF'),
        "project_id": version["project_id"],
        "artifact_type": 'requirement_version',
        "artifact_id": version_id,
        "result_type": 'REQUIREMENT_QUALITY_ANALYSIS',
        "requirement_version_id": version_id,
        "findings": findings,
        "suggestions": suggestions,
        "valid": ai_result.get("status") == 'SUCCESS'
        and not ai_result.get("degraded_mode")
        and not any(item["severity"] == 'error' for item in findings),
        **ai_contract_metadata(ai_result),
        "idempotency_key": payload.idempotency_key,
        "human_confirmation_required": True,
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        await requirement_ai_repository.insert_finding(result)
    except DuplicateKeyError:
        existing = await requirement_ai_repository.find_finding(query)
        if existing:
            return existing
        raise
    await audit(
        user.id,
        "requirement_quality_analyzed",
        "AIResult",
        result["_id"],
        version["project_id"],
        {"requirement_version_id": version_id, "status": result["status"]},
    )
    return result


async def apply_requirement_quality_suggestion(version_id, payload, user):
    
    version = await get_project_entity(
        "requirement_versions", version_id, user, "requirement.update"
    )
    if version.get("status") != 'DRAFT':
        raise HTTPException(status_code=409, detail={"code": 'IMMUTABLE_REQUIREMENT_VERSION'})
    if version.get("revision") != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_revision": version.get("revision")},
        )
    ai_result = await requirement_ai_repository.find_finding(
        {
            "_id": payload.ai_result_id,
            "project_id": version["project_id"],
            "artifact_id": version_id,
            "result_type": 'REQUIREMENT_QUALITY_ANALYSIS',
        }
    )
    if not ai_result:
        raise HTTPException(status_code=404, detail={"code": 'AI_SUGGESTION_NOT_FOUND'})
    suggestion = next(
        (
            item
            for item in ai_result.get("suggestions", [])
            if item.get("suggestion_id") == payload.suggestion_id
        ),
        None,
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail={"code": 'AI_SUGGESTION_NOT_FOUND'})
    if ai_result.get("status") != 'SUCCESS' or ai_result.get("degraded_mode"):
        raise HTTPException(status_code=409, detail={"code": 'AI_SUGGESTION_NOT_APPLICABLE'})
    acceptance_criteria = await requirement_ai_repository.list_acceptance_criteria(
        version_id, 200
    )
    if not requirement_suggestion_changes(version, suggestion, acceptance_criteria):
        raise HTTPException(status_code=422, detail={"code": 'AI_SUGGESTION_NO_CHANGE'})
    changes = {"updated_at": now()}
    revised_title = str(suggestion.get("revised_title") or "").strip()
    revised_content = str(suggestion.get("revised_content") or "").strip()
    if revised_title and revised_title != str(version.get("title") or "").strip():
        changes["title"] = revised_title
    current_content = str(
        version.get("plain_text_projection") or plain_text(version.get("content_doc", {})) or ""
    ).strip()
    if revised_content and revised_content != current_content:
        changes["content_doc"] = text_doc(revised_content)
        changes["plain_text_projection"] = revised_content
    patch = suggestion.get("patch") if isinstance(suggestion.get("patch"), dict) else {}
    if "business_rules" in patch:
        await get_project(version["project_id"], user, "business_rule.manage")
    if "dependencies" in patch:
        await get_project(version["project_id"], user, "requirement_dependency.manage")
    for field in ("actors", "business_rules", "dependencies"):
        if field in patch:
            changes[field] = patch[field]
    proposed_criteria = patch.get("acceptance_criteria")
    if proposed_criteria is not None:
        await get_project(version["project_id"], user, "acceptance_criteria.manage")
        keys = [item.get("key") for item in proposed_criteria]
        if len(keys) != len(set(keys)) or any(not key for key in keys):
            raise HTTPException(
                status_code=422,
                detail={"code": 'INVALID_ACCEPTANCE_CRITERION_PATCH'},
            )
        for item in proposed_criteria:
            validate_doc(item.get("content_doc", {}))
    updated = await requirement_ai_repository.update_requirement(
        {
            "_id": version_id,
            "project_id": version["project_id"],
            "status": 'DRAFT',
            "revision": payload.expected_revision,
        },
        changes,
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    if proposed_criteria is not None:
        previous_criteria = acceptance_criteria
        await requirement_ai_repository.delete_acceptance_criteria(version_id)
        try:
            await persist_acceptance_criteria(updated, proposed_criteria)
        except Exception:
            await requirement_ai_repository.delete_acceptance_criteria(version_id)
            if previous_criteria:
                await requirement_ai_repository.insert_acceptance_criteria(previous_criteria)
            rollback_values = {
                field: version[field]
                for field in changes
                if field in version and field != "revision"
            }
            rollback_values.update(
                {
                    "acceptance_criterion_ids": [item["_id"] for item in previous_criteria],
                    "revision": payload.expected_revision,
                }
            )
            missing_fields = [
                field for field in changes if field not in version and field != "revision"
            ]
            await requirement_ai_repository.rollback_requirement(
                {
                    "_id": version_id,
                    "project_id": version["project_id"],
                    "status": 'DRAFT',
                    "revision": payload.expected_revision + 1,
                },
                rollback_values,
                missing_fields,
            )
            raise
        updated = await requirement_ai_repository.find_requirement_version(version_id)
    await requirement_ai_repository.mark_suggestion_applied(
        ai_result["_id"], version["project_id"], payload.suggestion_id, now()
    )
    await audit(
        user.id,
        "requirement_ai_suggestion_applied",
        "RequirementVersion",
        version_id,
        version["project_id"],
        {
            "ai_result_id": ai_result["_id"],
            "suggestion_id": payload.suggestion_id,
            "reason_codes": suggestion.get("reason_codes", []),
            "evidence_refs": suggestion.get("evidence_refs", []),
        },
    )
    return updated
