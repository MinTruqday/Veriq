from hashlib import sha256

from fastapi import HTTPException

from src.core.common import audit, get_project_entity, get_project_role, new_id, now, plain_text
from src.modules.design.services.linters import requirement_findings
from src.repositories.requirement import requirement_repository
from src.repositories.requirement_clarification import requirement_clarification_repository


async def _require_role(project_id, user, role):
    if await get_project_role(project_id, user.id) != role:
        raise HTTPException(status_code=403, detail={"code": f"{role}_ROLE_REQUIRED"})


async def list_clarifications(requirement_version_id, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "requirement.read")
    return await requirement_clarification_repository.list_for_version(version["project_id"], version["_id"])


async def _create(project_id, requirement_id, version_id, payload, user, finding_key=None):
    value = {
        "_id": new_id("RCL"),
        "project_id": project_id,
        "requirement_id": requirement_id,
        "requirement_version_id": version_id,
        "coverage_item_id": payload.get("coverage_item_id"),
        "source_ref": payload.get("source_ref"),
        "source_quote": payload.get("source_quote"),
        "question": payload["question"],
        "reason": payload["reason"],
        "finding_key": finding_key,
        "status": "OPEN",
        "revision": 1,
        "created_by": user.id,
        "created_at": now(),
        "updated_at": now(),
    }
    await requirement_clarification_repository.insert(value)
    await audit(user.id, "requirement_clarification_created", "RequirementClarification", value["_id"], project_id, {"requirement_version_id": version_id})
    return value


async def create_clarification(requirement_version_id, payload, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "requirement.review")
    await _require_role(version["project_id"], user, "QA")
    return await _create(version["project_id"], version["requirement_id"], version["_id"], payload.model_dump(), user)


async def generate_clarifications(requirement_version_id, user):
    version = await get_project_entity("requirement_versions", requirement_version_id, user, "requirement.review")
    await _require_role(version["project_id"], user, "QA")
    criteria = await requirement_repository.list_acceptance_criteria(version["_id"], 500)
    created = []
    for finding in requirement_findings(version, criteria):
        identity = "|".join(str(finding.get(name) or "") for name in ("rule_id", "criterion_id", "target_field"))
        finding_key = sha256(f"{version['_id']}|{identity}".encode()).hexdigest()
        if await requirement_clarification_repository.find_active_finding(version["project_id"], version["_id"], finding_key):
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
        ))
    return created


async def answer_clarification(clarification_id, payload, user):
    clarification = await requirement_clarification_repository.find(clarification_id)
    if not clarification:
        raise HTTPException(status_code=404, detail={"code": "CLARIFICATION_NOT_FOUND"})
    await get_project_entity("requirements", clarification["requirement_id"], user, "requirement.update")
    await _require_role(clarification["project_id"], user, "BA")
    if clarification["status"] not in {"OPEN", "ANSWERED"}:
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    updated = await requirement_clarification_repository.replace(
        clarification_id,
        clarification["project_id"],
        payload.expected_revision,
        {"status": "ANSWERED", "answer": payload.answer, "answered_by": user.id, "answered_at": now(), "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "requirement_clarification_answered", "RequirementClarification", clarification_id, clarification["project_id"])
    return updated


def _version_evidence(version, criteria):
    return "\n".join(
        [
            plain_text(version.get("content_doc", {})),
            *[str(value) for value in version.get("business_rules") or []],
            *[str(item.get("plain_text") or plain_text(item.get("content_doc", {}))) for item in criteria],
        ]
    ).casefold()


async def resolve_clarification(clarification_id, payload, user):
    clarification = await requirement_clarification_repository.find(clarification_id)
    if not clarification:
        raise HTTPException(status_code=404, detail={"code": "CLARIFICATION_NOT_FOUND"})
    await get_project_entity("requirements", clarification["requirement_id"], user, "requirement.review")
    await _require_role(clarification["project_id"], user, "QA")
    if clarification["status"] != "ANSWERED":
        raise HTTPException(status_code=409, detail={"code": "CLARIFICATION_ANSWER_REQUIRED"})
    version = await requirement_repository.find_version(payload.requirement_version_id, clarification["project_id"], clarification["requirement_id"])
    if not version:
        raise HTTPException(status_code=422, detail={"code": "RESOLUTION_VERSION_INVALID"})
    criteria = await requirement_repository.list_acceptance_criteria(version["_id"], 500)
    if payload.evidence_quote.casefold() not in _version_evidence(version, criteria):
        raise HTTPException(status_code=422, detail={"code": "RESOLUTION_EVIDENCE_NOT_FOUND"})
    updated = await requirement_clarification_repository.replace(
        clarification_id,
        clarification["project_id"],
        payload.expected_revision,
        {"status": "RESOLVED", "resolved_requirement_version_id": version["_id"], "resolution_evidence_quote": payload.evidence_quote, "resolved_by": user.id, "resolved_at": now(), "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "requirement_clarification_resolved", "RequirementClarification", clarification_id, clarification["project_id"], {"requirement_version_id": version["_id"]})
    return updated


async def decide_clarification(clarification_id, payload, user):
    clarification = await requirement_clarification_repository.find(clarification_id)
    if not clarification:
        raise HTTPException(status_code=404, detail={"code": "CLARIFICATION_NOT_FOUND"})
    await get_project_entity("requirements", clarification["requirement_id"], user, "requirement.review")
    await _require_role(clarification["project_id"], user, "QA")
    if clarification["status"] not in {"OPEN", "ANSWERED"}:
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE_TRANSITION"})
    updated = await requirement_clarification_repository.replace(
        clarification_id,
        clarification["project_id"],
        payload.expected_revision,
        {"status": payload.status, "decision": {"reason": payload.reason, "decided_by": user.id, "decided_at": now()}, "updated_at": now()},
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "requirement_clarification_decided", "RequirementClarification", clarification_id, clarification["project_id"], {"status": payload.status})
    return updated


async def supersede_requirement_clarifications(project_id, requirement_id, requirement_version_id):
    await requirement_clarification_repository.supersede_for_requirement(project_id, requirement_id, requirement_version_id, now())
