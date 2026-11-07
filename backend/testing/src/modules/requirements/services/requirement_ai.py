import hashlib
import json
from datetime import timedelta

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.ai_automation import queue_requirement_changed
from src.core.common import audit, get_project, get_project_entity, new_id, now, plain_text, validate_doc
from src.core.database import database
from src.repositories.requirement_ai import requirement_ai_repository
from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.modules.design.services.linters import requirement_findings
from src.modules.requirements.services.requirement_records import persist_acceptance_criteria
from src.modules.requirements.services.requirement_workflow import (
    prepare_requirement_ai_suggestion,
    requirement_suggestion_changes,
    text_doc,
)


async def get_latest_requirement_quality_analysis(version_id, user):
    version = await get_project_entity(
        "requirement_versions", version_id, user, "requirement.read"
    )
    result = await requirement_ai_repository.find_latest_quality_analysis(
        version["project_id"], version_id
    )
    if not result:
        return None
    return {
        **result,
        "artifact_revision": result.get("artifact_revision"),
        "is_stale": result.get("artifact_revision") != version.get("revision"),
    }


async def analyze_requirement_quality(version_id, payload, user):
    version = await get_project_entity("requirement_versions", version_id, user, "ai.run_lint")
    idempotency_query = {
        "project_id": version["project_id"],
        "artifact_id": version_id,
        "idempotency_key": payload.idempotency_key,
    }
    acceptance_criteria = await requirement_ai_repository.list_acceptance_criteria(
        version_id, 200
    )
    source_text = json.dumps(
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
    )
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    request_fingerprint = hashlib.sha256(
        json.dumps(
            {
                "actor_id": user.id,
                "requirement_version_id": version_id,
                "revision": version.get("revision"),
                "status": version.get("status"),
                "source_hash": source_hash,
                "instruction": payload.instruction,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    timestamp = now()
    claim_token = new_id("RQAI")
    lease_expires_at = timestamp + timedelta(minutes=5)
    existing = await requirement_ai_repository.find_quality_analysis_request(
        idempotency_query
    )
    if existing:
        if not existing.get("request_fingerprint"):
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
        if existing.get("created_by") != user.id:
            raise HTTPException(status_code=403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
        if existing["request_fingerprint"] != request_fingerprint:
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
        if existing.get("result_type") == "REQUIREMENT_QUALITY_ANALYSIS":
            return existing
        claim = await requirement_ai_repository.reclaim_quality_analysis_claim(
            existing["_id"],
            request_fingerprint,
            timestamp,
            claim_token,
            lease_expires_at,
        )
        if not claim:
            raise HTTPException(
                status_code=409,
                detail={"code": "REQUIREMENT_QUALITY_ANALYSIS_IN_PROGRESS", "retryable": True},
            )
        claim_id = claim["_id"]
    else:
        claim_id = new_id("AIF")
        claim = {
            "_id": claim_id,
            **idempotency_query,
            "artifact_type": "requirement_version",
            "result_type": "REQUIREMENT_QUALITY_ANALYSIS_PENDING",
            "request_fingerprint": request_fingerprint,
            "source_hash": source_hash,
            "artifact_revision": version.get("revision"),
            "created_by": user.id,
            "created_at": timestamp,
            "claimed_at": timestamp,
            "lease_expires_at": lease_expires_at,
            "claim_token": claim_token,
            "attempt": 1,
        }
        try:
            await requirement_ai_repository.insert_quality_analysis_claim(claim)
        except DuplicateKeyError:
            existing = await requirement_ai_repository.find_quality_analysis_request(
                idempotency_query
            )
            if existing:
                if not existing.get("request_fingerprint"):
                    raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_REPLAY_UNVERIFIABLE"})
                if existing.get("created_by") != user.id:
                    raise HTTPException(status_code=403, detail={"code": "IDEMPOTENCY_REPLAY_ACTOR_MISMATCH"})
                if existing["request_fingerprint"] != request_fingerprint:
                    raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
            if existing and existing.get("result_type") == "REQUIREMENT_QUALITY_ANALYSIS":
                return existing
            if existing:
                claim = await requirement_ai_repository.reclaim_quality_analysis_claim(
                    existing["_id"],
                    request_fingerprint,
                    timestamp,
                    claim_token,
                    lease_expires_at,
                )
                if claim:
                    claim_id = claim["_id"]
                else:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "REQUIREMENT_QUALITY_ANALYSIS_IN_PROGRESS", "retryable": True},
                    )
            else:
                raise
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
            "text": source_text,
        }
    ]
    instruction = json.dumps({"user_instruction": payload.instruction}, ensure_ascii=False)
    try:
        ai_result = await request_ai_automation(
            "requirement_quality_analysis", version["project_id"], instruction, evidence
        )
        current_version = await get_project_entity(
            "requirement_versions", version_id, user, "ai.run_lint"
        )
        current_criteria = await requirement_ai_repository.list_acceptance_criteria(
            version_id, 200
        )
        current_source_text = json.dumps(
            {
                "title": (current_version or {}).get("title"),
                "content": (current_version or {}).get("plain_text_projection")
                or plain_text((current_version or {}).get("content_doc", {})),
                "actors": (current_version or {}).get("actors", []),
                "business_rules": (current_version or {}).get("business_rules", []),
                "acceptance_criteria": [
                    str(item.get("plain_text") or "").strip()
                    for item in current_criteria
                    if str(item.get("plain_text") or "").strip()
                ],
                "dependencies": (current_version or {}).get("dependencies", []),
                "tags": (current_version or {}).get("tags", []),
            },
            ensure_ascii=False,
        )
        current_source_hash = hashlib.sha256(current_source_text.encode("utf-8")).hexdigest()
        if (
            not current_version
            or current_version.get("project_id") != version["project_id"]
            or current_version.get("revision") != version.get("revision")
            or current_version.get("status") != version.get("status")
            or current_source_hash != source_hash
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "REQUIREMENT_QUALITY_ANALYSIS_SOURCE_CHANGED", "retryable": True},
            )
        ai_recommendations = [
            {
                **item,
                "recommendation_id": f"REQ-REC-{index:02d}",
                "origin": 'AI',
                "status": 'CANDIDATE',
            }
            for index, item in enumerate(ai_result.get("recommendations", []), 1)
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
        findings = deterministic_findings
        contract_metadata = ai_contract_metadata(ai_result)
        if contract_metadata.get("degraded_mode") is None:
            contract_metadata["degraded_mode"] = False
        result = {
            "_id": claim_id,
            "project_id": version["project_id"],
            "artifact_type": 'requirement_version',
            "artifact_id": version_id,
            "result_type": 'REQUIREMENT_QUALITY_ANALYSIS',
            "requirement_version_id": version_id,
            "artifact_revision": version.get("revision"),
            "source_hash": source_hash,
            "request_fingerprint": request_fingerprint,
            "findings": findings,
            "recommendations": ai_recommendations,
            "suggestions": suggestions,
            "valid": ai_result.get("status") == 'SUCCESS'
            and not ai_result.get("degraded_mode")
            and not any(item["severity"] == 'error' for item in deterministic_findings),
            **contract_metadata,
            "idempotency_key": payload.idempotency_key,
            "human_confirmation_required": True,
            "created_by": user.id,
            "created_at": timestamp,
        }
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                replaced = await requirement_ai_repository.replace_quality_analysis_claim(
                    claim_id, claim_token, result, session=session
                )
                if not replaced:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "REQUIREMENT_QUALITY_ANALYSIS_CLAIM_LOST", "retryable": True},
                    )
                await audit(
                    user.id,
                    "requirement_quality_analyzed",
                    "AIResult",
                    result["_id"],
                    version["project_id"],
                    {"requirement_version_id": version_id, "status": result["status"]},
                    session=session,
                )
    except Exception:
        await requirement_ai_repository.release_quality_analysis_claim(
            claim_id, claim_token
        )
        raise
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
    if ai_result.get("artifact_revision") != version.get("revision"):
        raise HTTPException(status_code=409, detail={"code": "AI_SUGGESTION_STALE"})
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
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            current_version = await requirement_ai_repository.find_requirement_version(
                version_id, session=session
            )
            if (
                not current_version
                or current_version.get("project_id") != version["project_id"]
                or current_version.get("status") != "DRAFT"
                or current_version.get("revision") != payload.expected_revision
            ):
                raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
            current_result = await requirement_ai_repository.find_finding(
                {
                    "_id": payload.ai_result_id,
                    "project_id": version["project_id"],
                    "artifact_id": version_id,
                    "result_type": "REQUIREMENT_QUALITY_ANALYSIS",
                },
                session=session,
            )
            if (
                not current_result
                or current_result.get("status") != "SUCCESS"
                or current_result.get("degraded_mode")
                or payload.suggestion_id in current_result.get("applied_suggestion_ids", [])
            ):
                raise HTTPException(
                    status_code=409, detail={"code": "AI_SUGGESTION_NOT_APPLICABLE"}
                )
            if current_result.get("artifact_revision") != current_version.get("revision"):
                raise HTTPException(status_code=409, detail={"code": "AI_SUGGESTION_STALE"})
            current_suggestion = next(
                (
                    item
                    for item in current_result.get("suggestions", [])
                    if item.get("suggestion_id") == payload.suggestion_id
                ),
                None,
            )
            if current_suggestion != suggestion:
                raise HTTPException(
                    status_code=409, detail={"code": "AI_SUGGESTION_CHANGED"}
                )
            current_criteria = await requirement_ai_repository.list_acceptance_criteria(
                version_id, 200, session=session
            )
            if not requirement_suggestion_changes(
                current_version, current_suggestion, current_criteria
            ):
                raise HTTPException(
                    status_code=422, detail={"code": "AI_SUGGESTION_NO_CHANGE"}
                )
            updated = await requirement_ai_repository.update_requirement(
                {
                    "_id": version_id,
                    "project_id": version["project_id"],
                    "status": "DRAFT",
                    "revision": payload.expected_revision,
                },
                {**changes, "updated_at": now()},
                session=session,
            )
            if not updated:
                raise HTTPException(
                    status_code=409, detail={"code": "REVISION_CONFLICT"}
                )
            if proposed_criteria is not None:
                await requirement_ai_repository.delete_acceptance_criteria(
                    version_id, session=session
                )
                updated = await persist_acceptance_criteria(
                    updated, proposed_criteria, session=session
                )
            marked = await requirement_ai_repository.mark_suggestion_applied(
                current_result["_id"],
                version["project_id"],
                payload.suggestion_id,
                now(),
                session=session,
            )
            if not marked:
                raise HTTPException(
                    status_code=409, detail={"code": "AI_SUGGESTION_CHANGED"}
                )
            await queue_requirement_changed(updated, user, session)
            await audit(
                user.id,
                "requirement_ai_suggestion_applied",
                "RequirementVersion",
                version_id,
                version["project_id"],
                {
                    "ai_result_id": current_result["_id"],
                    "suggestion_id": payload.suggestion_id,
                    "reason_codes": suggestion.get("reason_codes", []),
                    "evidence_refs": suggestion.get("evidence_refs", []),
                },
                session=session,
            )
    return updated
