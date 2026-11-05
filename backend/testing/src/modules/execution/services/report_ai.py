import json

from src.core.ai_automation import request_ai_automation
from src.core.common import get_project, new_id, now
from src.core.human_decisions import content_authorship_changes
from src.modules.execution.services.report_document import document_text, resolve_report_fields
from src.modules.execution.services.reporting import fail, fingerprint, report_for_user
from src.repositories.reporting import reporting_repository as repository


async def draft_report(report_id, request, user):
    report = await report_for_user(report_id, user)
    await get_project(report["project_id"], user, "workreport.ai")
    if user.id not in {report["owner_id"], report["reviewer_id"], *report.get("editor_ids", [])}:
        fail("REPORT_AI_ACCESS_DENIED", 403)
    if report["revision"] != request.expected_revision:
        fail("REPORT_REVISION_CONFLICT")
    query = {"report_id": report_id, "requested_by": user.id, "idempotency_key": request.idempotency_key}
    request_hash = fingerprint(request.model_dump())
    existing = await repository.find("report_ai_drafts", query)
    if existing:
        if existing["request_hash"] != request_hash:
            fail("REPORT_IDEMPOTENCY_CONFLICT")
        return existing
    from pymongo.errors import DuplicateKeyError
    proposal_id = new_id("RAI")
    try:
        await repository.insert("report_ai_drafts", {"_id": proposal_id, **query, "project_id": report["project_id"], "request_hash": request_hash, "source_revision": report["revision"], "mode": request.mode, "output_language": request.output_language, "status": "RUNNING", "result": None, "created_at": now(), "updated_at": now()})
    except DuplicateKeyError:
        fail("REPORT_AI_REQUEST_RUNNING")
    records = [{"report_title": report["title"], "project_name": report.get("project_name"), "owner_name": report.get("owner_name"), "snapshot_metrics": report["snapshot"]["metrics"], "period": report["period"], "captured_at": report["snapshot"]["captured_at"], "limitations": report["snapshot"]["limitations"]}, *report["snapshot"]["work_items"], {"current_narrative": document_text(resolve_report_fields(report))}]
    groups, group = [], ""
    for record in records:
        source = json.dumps(record, ensure_ascii=False, default=str)
        for offset in range(0, len(source), 3500):
            text = source[offset:offset + 3500]
            if len(group) + len(text) + 1 > 3900:
                groups.append(group)
                group = ""
            group += text + "\n"
    if group:
        groups.append(group)
    if len(groups) > 100:
        await repository.change("report_ai_drafts", {"_id": proposal_id}, {"$set": {"status": "FAILED", "error_code": "REPORT_AI_SOURCE_TOO_LARGE", "updated_at": now()}})
        fail("REPORT_AI_SOURCE_TOO_LARGE", 422)
    evidence = [{"artifact_type": "work_report", "artifact_id": report_id, "artifact_version_id": f"{report_id}:r{report['revision']}:source{index}", "project_id": report["project_id"], "source": "database", "authority": "PROJECT_REFERENCE", "score": 1, "text": text} for index, text in enumerate(groups)]
    try:
        result = await request_ai_automation("work_report_narrative", report["project_id"], json.dumps({"mode": request.mode, "user_instruction": request.instruction}, ensure_ascii=False), evidence, request_id=request.idempotency_key, output_language=request.output_language)
        current = await report_for_user(report_id, user)
        if current["revision"] != report["revision"]:
            fail("REPORT_AI_PROPOSAL_STALE")
    except Exception as error:
        await repository.change("report_ai_drafts", {"_id": proposal_id, "status": "RUNNING"}, {"$set": {"status": "FAILED", "error_code": type(error).__name__, "updated_at": now()}})
        raise
    value = {"_id": new_id("RAI"), **query, "project_id": report["project_id"], "request_hash": request_hash, "source_revision": report["revision"], "source_hash": fingerprint(report["snapshot"]), "mode": request.mode, "output_language": request.output_language, "result": result, "created_at": now(), "updated_at": now()}
    value["_id"] = proposal_id
    value["status"] = result.get("status", "DEGRADED")
    return await repository.change("report_ai_drafts", {"_id": proposal_id, "status": "RUNNING"}, {"$set": {key: item for key, item in value.items() if key != "_id"}})


async def apply_report_proposal(report_id, payload, user):
    from src.core.common import audit
    from src.core.database import database
    from src.modules.execution.services.report_document import paragraph, validate_report_document

    report = await report_for_user(report_id, user, "write")
    key = {"report_id": report_id, "actor_id": user.id, "idempotency_key": payload.idempotency_key}
    replay = await repository.find("report_actions", key)
    request_hash = fingerprint(payload.model_dump())
    if replay:
        if replay["request_hash"] != request_hash:
            fail("REPORT_IDEMPOTENCY_CONFLICT")
        return replay["result"]
    proposal = await repository.find("report_ai_drafts", {"_id": payload.proposal_id, "report_id": report_id, "project_id": report["project_id"]})
    if not proposal or proposal.get("mode") == "REVIEW" or (proposal.get("result") or {}).get("status") != "SUCCESS":
        fail("REPORT_AI_PROPOSAL_NOT_APPLICABLE")
    if report["status"] != "DRAFT" or report["revision"] != payload.expected_revision or report["revision"] != proposal["source_revision"]:
        fail("REPORT_AI_PROPOSAL_STALE")
    sections = proposal["result"]["suggestions"][0].get("sections", [])
    if any(index >= len(sections) for index in payload.section_indices):
        fail("REPORT_AI_SECTIONS_INVALID", 422)
    content = {"type": "doc", "content": list(report["content_doc"].get("content", []))}
    for index in payload.section_indices:
        section = sections[index]
        content["content"].append(paragraph(section["title"], 2))
        content["content"].extend(paragraph(line) for line in section["text"].split("\n"))
    validate_report_document(content)
    receipt = {"proposal_id": proposal["_id"], "section_indices": payload.section_indices, "source_revision": proposal["source_revision"], "applied_by": user.id, "applied_at": now(), "model": proposal["result"].get("model"), "evidence_refs": proposal["result"].get("evidence_refs", [])}
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            value = await repository.change("work_reports", {"_id": report_id, "revision": payload.expected_revision, "status": "DRAFT"}, {"$set": {**content_authorship_changes(report, user, {"content_doc": content}), "updated_at": now()}, "$inc": {"revision": 1}, "$push": {"ai_application_history": receipt}}, session=session)
            if not value:
                fail("REPORT_REVISION_CONFLICT")
            await repository.insert("report_actions", {"_id": new_id("RACT"), **key, "request_hash": request_hash, "result": value, "created_at": now()}, session=session)
            await audit(user.id, "report_ai_sections_applied", "Report", report_id, report["project_id"], receipt, session=session)
    return value
