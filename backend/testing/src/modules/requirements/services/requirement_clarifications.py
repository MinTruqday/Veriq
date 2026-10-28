from hashlib import sha256

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, PyMongoError
from src.core.human_decisions import require_automation_publication_authority

from src.core.common import audit, get_project_entity, get_project_roles, new_id, now, plain_text
from src.core.database import database
from src.modules.design.services.linters import requirement_findings
from src.repositories.requirement import requirement_repository
from src.repositories.requirement_clarification import requirement_clarification_repository


async def _require_role(project_id, user, role):
    if role not in await get_project_roles(project_id, user.id):
        raise HTTPException(status_code=403, detail={"code": f"{role}_ROLE_REQUIRED"})


async def _require_question_author(project_id, user):
    roles = await get_project_roles(project_id, user.id)
    if "QA" in roles or (getattr(user, "_ai_automation_run_id", None) and "BA" in roles):
        return
    raise HTTPException(status_code=403, detail={"code": "QA_ROLE_REQUIRED"})


async def list_clarifications(requirement_version_id, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "requirement.read")
    return await requirement_clarification_repository.list_for_version(version["project_id"], version["_id"])


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
            clarification["requirement_version_id"],
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
    await _require_question_author(version["project_id"], user)
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
    await _require_question_author(version["project_id"], user)
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
    await _require_role(clarification["project_id"], user, "BA")
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
            "updated_at": timestamp,
        },
        user,
        "requirement_clarification_answered",
        requirement_current_version_id=version["_id"],
        requirement_version_revision=version.get("revision"),
    )


def _version_evidence(version, criteria):
    return "\n".join(
        [
            plain_text(version.get("content_doc", {})),
            *[str(value) for value in version.get("business_rules") or []],
            *[str(item.get("plain_text") or plain_text(item.get("content_doc", {}))) for item in criteria],
        ]
    ).casefold()


async def resolve_clarification(clarification_id, payload, user):
    require_automation_publication_authority(user, "requirement.approve")
    clarification = await requirement_clarification_repository.find(clarification_id)
    if not clarification:
        raise HTTPException(status_code=404, detail={"code": "CLARIFICATION_NOT_FOUND"})
    requirement = await get_project_entity("requirements", clarification["requirement_id"], user, "requirement.review")
    await _require_role(clarification["project_id"], user, "QA")
    if clarification["status"] != "ANSWERED":
        raise HTTPException(status_code=409, detail={"code": "CLARIFICATION_ANSWER_REQUIRED"})
    version = await requirement_repository.find_version(payload.requirement_version_id, clarification["project_id"], clarification["requirement_id"])
    if not version:
        raise HTTPException(status_code=422, detail={"code": "RESOLUTION_VERSION_INVALID"})
    if requirement.get("current_version_id") != version["_id"]:
        raise HTTPException(status_code=409, detail={"code": "RESOLUTION_VERSION_NOT_CURRENT"})
    clarification_version = (
        version
        if clarification["requirement_version_id"] == version["_id"]
        else await requirement_repository.find_version(
            clarification["requirement_version_id"],
            clarification["project_id"],
            clarification["requirement_id"],
        )
    )
    if not clarification_version:
        raise HTTPException(status_code=409, detail={"code": "REQUIREMENT_VERSION_CHANGED"})
    criteria = await requirement_repository.list_acceptance_criteria(version["_id"], None)
    if payload.evidence_quote.casefold() not in _version_evidence(version, criteria):
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
        requirement_version_revision=clarification_version.get("revision"),
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
    await _require_role(clarification["project_id"], user, "QA")
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
