import re
from hashlib import sha256

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, PyMongoError
from src.core.common import audit, get_project_entity, new_id, now, plain_text
from src.core.database import database
from src.core.human_decisions import (
    require_automation_publication_authority,
    require_independent_review,
)
from src.modules.design.services.linters import requirement_findings
from src.repositories.requirement import requirement_repository
from src.repositories.requirement_clarification import requirement_clarification_repository


async def list_clarifications(requirement_version_id, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "requirement.read")
    return await requirement_clarification_repository.list_for_requirement(
        version["project_id"], version["requirement_id"]
    )


async def _create(
    project_id,
    requirement_id,
    version_id,
    payload,
    user,
    finding_key=None,
    session=None,
    clarification_id=None,
    expected_version_revision=None,
):
    value = {
        "_id": clarification_id or new_id("RCL"),
        "project_id": project_id,
        "requirement_id": requirement_id,
        "requirement_version_id": version_id,
        "coverage_item_id": payload.get("coverage_item_id"),
        "source_ref": payload.get("source_ref"),
        "source_quote": payload.get("source_quote"),
        "unlocks_obligation_keys": list(dict.fromkeys(payload.get("unlocks_obligation_keys") or [])),
        "unlocks_source_quotes": list(dict.fromkeys(payload.get("unlocks_source_quotes") or [])),
        "unlocks_coverage_item_ids": list(dict.fromkeys(payload.get("unlocks_coverage_item_ids") or [])),
        "question": payload["question"],
        "reason": payload["reason"],
        "finding_key": finding_key,
        "status": "OPEN",
        "revision": 1,
        "created_by": user.id,
        "created_at": now(),
        "updated_at": now(),
    }
    async def persist(active_session):
        if expected_version_revision is not None:
            current_version = await database.value.requirement_versions.find_one(
                {
                    "_id": version_id,
                    "project_id": project_id,
                    "requirement_id": requirement_id,
                    "revision": expected_version_revision,
                },
                session=active_session,
            )
            if not current_version:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "REQUIREMENT_VERSION_CHANGED"},
                )
        await requirement_clarification_repository.insert(value, session=active_session)
        if not await requirement_repository.bump_clarification_gate_revision(
            version_id,
            project_id,
            session=active_session,
            expected_revision=expected_version_revision,
        ):
            raise HTTPException(status_code=409, detail={"code": "REQUIREMENT_VERSION_CHANGED"})
        await audit(
            user.id,
            "requirement_clarification_created",
            "RequirementClarification",
            value["_id"],
            project_id,
            {"requirement_version_id": version_id},
            session=active_session,
        )

    if session is not None:
        await persist(session)
    else:
        async with await database.client.start_session() as active_session:
            await active_session.with_transaction(persist)
    return value


async def _replace_and_audit(
    clarification, payload, changes, user, action, details=None,
    requirement_current_version_id=None,
    requirement_version_revision=None,
    requirement_gate_version_id=None,
):
    async def commit(session):
        if requirement_current_version_id is not None:
            requirement_update = await database.value.requirements.update_one(
                {
                    "_id": clarification["requirement_id"],
                    "project_id": clarification["project_id"],
                    "current_version_id": requirement_current_version_id,
                },
                {"$set": {"updated_at": changes.get("updated_at") or now()}},
                session=session,
            )
            if requirement_update.matched_count != 1:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "RESOLUTION_VERSION_NOT_CURRENT"},
                )
        updated = await requirement_clarification_repository.replace(
            clarification["_id"],
            clarification["project_id"],
            payload.expected_revision,
            changes,
            session=session,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        if not await requirement_repository.bump_clarification_gate_revision(
            requirement_gate_version_id or clarification["requirement_version_id"],
            clarification["project_id"],
            session=session,
            expected_revision=requirement_version_revision,
        ):
            raise HTTPException(status_code=409, detail={"code": "REQUIREMENT_VERSION_CHANGED"})
        await audit(
            user.id,
            action,
            "RequirementClarification",
            clarification["_id"],
            clarification["project_id"],
            details,
            session=session,
        )
        return updated

    async with await database.client.start_session() as session:
        return await session.with_transaction(commit)


async def create_clarification(requirement_version_id, payload, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "requirement.review")
    return await _create(
        version["project_id"],
        version["requirement_id"],
        version["_id"],
        payload.model_dump(),
        user,
        expected_version_revision=version["revision"],
    )


async def generate_clarifications(requirement_version_id, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "requirement.review")
    criteria = await requirement_repository.list_acceptance_criteria(version["_id"], None)
    findings = [
        finding
        for finding in requirement_findings(version, criteria)
        if finding.get("severity") == "error"
    ]
    if not findings:
        return []
    for attempt in range(3):
        async def create_in_transaction(session):
            created = []
            for finding in findings:
                identity = "|".join(
                    str(finding.get(name) or "")
                    for name in ("rule_id", "criterion_id", "target_field")
                )
                finding_key = sha256(f"{version['_id']}|{identity}".encode()).hexdigest()
                if await requirement_clarification_repository.find_finding(
                    version["project_id"], version["_id"], finding_key, session=session
                ):
                    continue
                created.append(await _create(
                    version["project_id"],
                    version["requirement_id"],
                    version["_id"],
                    {
                        "question": finding["suggestion"],
                        "reason": finding["message"],
                        "source_ref": finding.get("criterion_key") or finding.get("target_field"),
                        "source_quote": None,
                    },
                    user,
                    finding_key,
                    session=session,
                    clarification_id=f"RCL-{finding_key}",
                    expected_version_revision=version["revision"],
                ))
            return created

        try:
            async with await database.client.start_session() as session:
                return await session.with_transaction(create_in_transaction)
        except PyMongoError as exc:
            retryable_conflict = isinstance(exc, DuplicateKeyError) or exc.has_error_label(
                "TransientTransactionError"
            )
            if not retryable_conflict or attempt == 2:
                raise
    return []


async def answer_clarification(clarification_id, payload, user):
    clarification = await requirement_clarification_repository.find(clarification_id)
    if not clarification:
        raise HTTPException(status_code=404, detail={"code": "CLARIFICATION_NOT_FOUND"})
    requirement = await get_project_entity(
        "requirements", clarification["requirement_id"], user, "requirement.update"
    )
    version = await requirement_repository.find_version(
        clarification["requirement_version_id"],
        clarification["project_id"],
        clarification["requirement_id"],
    )
    if (
        not version
        or requirement.get("current_version_id") != version["_id"]
        or version.get("status") == "SUPERSEDED"
    ):
        raise HTTPException(status_code=409, detail={"code": "CLARIFICATION_VERSION_NOT_CURRENT"})
    if clarification["status"] not in {"OPEN", "ANSWERED"}:
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    timestamp = now()
    return await _replace_and_audit(
        clarification,
        payload,
        {
            "status": "ANSWERED",
            "answer": payload.answer,
            "answered_by": user.id,
            "answered_at": timestamp,
            "answered_requirement_version_revision": version.get("revision"),
            "updated_at": timestamp,
        },
        user,
        "requirement_clarification_answered",
        requirement_current_version_id=version["_id"],
        requirement_version_revision=version.get("revision"),
    )


def _normalized_evidence(value):
    return " ".join(str(value or "").casefold().split())


def _criterion_reference_matches(reference, criterion):
    normalized_reference = _normalized_evidence(reference)
    normalized_key = _normalized_evidence(criterion.get("key"))
    if normalized_reference in {
        normalized_key,
        _normalized_evidence(criterion.get("_id")),
    }:
        return True
    reference_match = re.fullmatch(r"ac[-_ ]?0*(\d+)", normalized_reference)
    key_match = re.fullmatch(r"ac[-_ ]?0*(\d+)", normalized_key)
    return bool(reference_match and key_match and reference_match.group(1) == key_match.group(1))


def _clarification_source_evidence(version, criteria, clarification):
    reference = str(clarification.get("source_ref") or "").strip()
    normalized_reference = _normalized_evidence(reference).replace(" ", "_")
    if normalized_reference in {"content", "requirement_content"}:
        return plain_text(version.get("content_doc", {}))
    if normalized_reference in {"title", "requirement_title"}:
        return str(version.get("title") or "")
    if normalized_reference == "actors":
        return "\n".join(str(value) for value in version.get("actors") or [])
    if normalized_reference in {"business_rules", "business_rule"}:
        return "\n".join(str(value) for value in version.get("business_rules") or [])
    business_rule = re.fullmatch(r"business_rules?:?[_ ]?(\d+)", normalized_reference)
    if business_rule:
        index = int(business_rule.group(1)) - 1
        values = version.get("business_rules") or []
        return str(values[index]) if 0 <= index < len(values) else ""
    version_id = _normalized_evidence(version.get("_id"))
    if normalized_reference in {"requirement_version", version_id}:
        return str(
            version.get("plain_text_projection")
            or plain_text(version.get("content_doc", {}))
            or version.get("title")
            or ""
        )
    api_operations = (version.get("details") or {}).get("api_operations", [])
    for operation in api_operations:
        if not isinstance(operation, dict):
            continue
        method = str(operation.get("method") or "").strip().upper()
        path = str(operation.get("path") or operation.get("url_template") or "").strip()
        if method and path and _normalized_evidence(f"{method} {path}") == _normalized_evidence(reference):
            return f"{method} {path}"
    if normalized_reference in {"acceptance_criteria", "acceptance_criterion"}:
        selected = criteria
    else:
        selected = [
            item for item in criteria if _criterion_reference_matches(reference, item)
        ]
    return "\n".join(
        str(item.get("plain_text") or plain_text(item.get("content_doc", {})))
        for item in selected
    )


async def request_clarification_changes(clarification_id, payload, user):
    clarification = await requirement_clarification_repository.find(clarification_id)
    if not clarification:
        raise HTTPException(status_code=404, detail={"code": "CLARIFICATION_NOT_FOUND"})
    requirement = await get_project_entity(
        "requirements", clarification["requirement_id"], user, "requirement.review"
    )
    source_version = await requirement_repository.find_version(
        clarification["requirement_version_id"],
        clarification["project_id"],
        clarification["requirement_id"],
    )
    version = await requirement_repository.find_version(
        requirement.get("current_version_id"),
        clarification["project_id"],
        clarification["requirement_id"],
    )
    if (
        not source_version
        or not version
        or version.get("status") not in {"DRAFT", "IN_REVIEW"}
    ):
        raise HTTPException(status_code=409, detail={"code": "CLARIFICATION_VERSION_NOT_EDITABLE"})
    if clarification.get("status") != "ANSWERED":
        raise HTTPException(status_code=409, detail={"code": "CLARIFICATION_ANSWER_REQUIRED"})
    if clarification.get("revision") != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    if version.get("revision") != payload.expected_requirement_revision:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    if version.get("status") == "IN_REVIEW":
        require_independent_review(version, user, "REQUIREMENT_SELF_REVIEW_FORBIDDEN")
    timestamp = now()
    requirement_revision_after_request = version["revision"] + int(version["status"] == "IN_REVIEW")

    async def commit(session):
        if not await requirement_repository.bump_clarification_gate_revision(
            version["_id"],
            version["project_id"],
            session=session,
            expected_revision=version["revision"],
        ):
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        if version.get("status") == "IN_REVIEW":
            transitioned = await requirement_repository.transition_version(
                version["_id"],
                version["project_id"],
                version["revision"],
                "IN_REVIEW",
                "DRAFT",
                {
                    "review_note": payload.review_note,
                    "changes_requested_by": user.id,
                    "changes_requested_at": timestamp,
                    "updated_at": timestamp,
                },
                session=session,
            )
            if not transitioned:
                raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
            await audit(
                user.id,
                "requirement_changes_requested",
                "RequirementVersion",
                version["_id"],
                version["project_id"],
                {"review_note": payload.review_note, "clarification_id": clarification_id},
                session=session,
            )
        if not await requirement_repository.set_requirement_status(
            clarification["requirement_id"],
            clarification["project_id"],
            version["_id"],
            "DRAFT",
            timestamp,
            session=session,
        ):
            raise HTTPException(status_code=409, detail={"code": "REQUIREMENT_STATUS_CONFLICT"})
        updated = await requirement_clarification_repository.replace(
            clarification_id,
            clarification["project_id"],
            payload.expected_revision,
            {
                "change_requested_requirement_revision": requirement_revision_after_request,
                "change_requested_requirement_version_id": version["_id"],
                "change_request_note": payload.review_note,
                "change_requested_by": user.id,
                "change_requested_at": timestamp,
                "updated_at": timestamp,
            },
            session=session,
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
        await audit(
            user.id,
            "requirement_clarification_change_requested",
            "RequirementClarification",
            clarification_id,
            clarification["project_id"],
            {
                "requirement_version_id": version["_id"],
                "requirement_revision": requirement_revision_after_request,
            },
            session=session,
        )
        return updated

    async with await database.client.start_session() as session:
        updated = await session.with_transaction(commit)
    latest_version = await requirement_repository.find_version(
        version["_id"], version["project_id"]
    )
    return {"clarification": updated, "requirement_version": latest_version}


async def resolve_clarification(clarification_id, payload, user):
    require_automation_publication_authority(user, "requirement.approve")
    clarification = await requirement_clarification_repository.find(clarification_id)
    if not clarification:
        raise HTTPException(status_code=404, detail={"code": "CLARIFICATION_NOT_FOUND"})
    requirement = await get_project_entity("requirements", clarification["requirement_id"], user, "requirement.review")
    if clarification["status"] != "ANSWERED":
        raise HTTPException(status_code=409, detail={"code": "CLARIFICATION_ANSWER_REQUIRED"})
    version = await requirement_repository.find_version(payload.requirement_version_id, clarification["project_id"], clarification["requirement_id"])
    if not version:
        raise HTTPException(status_code=422, detail={"code": "RESOLUTION_VERSION_INVALID"})
    if requirement.get("current_version_id") != version["_id"]:
        raise HTTPException(status_code=409, detail={"code": "RESOLUTION_VERSION_NOT_CURRENT"})
    change_requested_version_id = clarification.get(
        "change_requested_requirement_version_id"
    ) or clarification["requirement_version_id"]
    if change_requested_version_id != version["_id"]:
        raise HTTPException(
            status_code=409,
            detail={"code": "CLARIFICATION_UPDATE_REQUEST_REQUIRED"},
        )
    required_revision = clarification.get("change_requested_requirement_revision")
    if required_revision is None or version.get("revision", 0) <= required_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": "CLARIFICATION_REQUIRES_UPDATED_REQUIREMENT"},
        )
    criteria = await requirement_repository.list_acceptance_criteria(version["_id"], None)
    source_evidence = _clarification_source_evidence(version, criteria, clarification)
    if (
        not source_evidence
        or _normalized_evidence(payload.evidence_quote)
        not in _normalized_evidence(source_evidence)
    ):
        raise HTTPException(status_code=422, detail={"code": "RESOLUTION_EVIDENCE_NOT_FOUND"})
    timestamp = now()
    return await _replace_and_audit(
        clarification,
        payload,
        {
            "status": "RESOLVED",
            "resolved_requirement_version_id": version["_id"],
            "resolution_evidence_quote": payload.evidence_quote,
            "resolved_by": user.id,
            "resolved_at": timestamp,
            "updated_at": timestamp,
        },
        user,
        "requirement_clarification_resolved",
        {"requirement_version_id": version["_id"]},
        requirement_current_version_id=version["_id"],
        requirement_version_revision=version.get("revision"),
        requirement_gate_version_id=version["_id"],
    )


async def decide_clarification(clarification_id, payload, user):
    require_automation_publication_authority(user)
    clarification = await requirement_clarification_repository.find(clarification_id)
    if not clarification:
        raise HTTPException(status_code=404, detail={"code": "CLARIFICATION_NOT_FOUND"})
    requirement = await get_project_entity(
        "requirements",
        clarification["requirement_id"],
        user,
        "requirement.review",
    )
    if clarification["status"] not in {"OPEN", "ANSWERED"}:
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    version = await requirement_repository.find_version(
        clarification["requirement_version_id"],
        clarification["project_id"],
        clarification["requirement_id"],
    )
    if (
        not version
        or requirement.get("current_version_id") != version["_id"]
        or version.get("status") == "SUPERSEDED"
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "CLARIFICATION_VERSION_NOT_CURRENT"},
        )
    timestamp = now()
    return await _replace_and_audit(
        clarification,
        payload,
        {
            "status": payload.status,
            "decision": {
                "reason": payload.reason,
                "decided_by": user.id,
                "decided_at": timestamp,
            },
            "updated_at": timestamp,
        },
        user,
        "requirement_clarification_decided",
        {"status": payload.status},
        requirement_current_version_id=version["_id"],
        requirement_version_revision=version.get("revision"),
    )


async def supersede_requirement_clarifications(
    project_id, requirement_id, requirement_version_id, session=None
):
    await requirement_clarification_repository.supersede_for_requirement(
        project_id, requirement_id, requirement_version_id, now(), session=session
    )
