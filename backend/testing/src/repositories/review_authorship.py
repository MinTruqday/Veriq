import hashlib
import json
from datetime import datetime, timezone

from src.core.database import database


ARTIFACT_AUDIT_SOURCES = {
    "requirement_versions": ("Requirement", {"requirement_draft_updated"}),
    "test_plans": ("TestPlan", {"test_plan_updated"}),
    "test_case_drafts": ("TestCaseDraft", {"test_case_draft_updated"}),
    "test_scenarios": ("TestScenario", {"test_scenario_updated"}),
    "work_reports": ("Report", {"report_updated", "report_ai_sections_applied"}),
    "test_status_reports": ("TestStatusReport", {"test_status_report_updated", "test_status_report_evidence_attached"}),
    "test_completion_reports": ("TestCompletionReport", {"test_completion_report_updated"}),
}


def recovered_authorship(record, events, allowed_actions):
    authors = set(record.get("content_author_ids") or [])
    if record.get("created_by"):
        authors.add(record["created_by"])
    evidence = []
    unresolved_actor = False
    for event in events:
        if event.get("action") not in allowed_actions:
            continue
        details = event.get("details") or {}
        actor = details.get("initiated_by") if details.get("actor_type") == "AI_AUTOMATION" else event.get("actor_id")
        evidence.append(event["_id"])
        if actor:
            authors.add(actor)
        else:
            unresolved_actor = True
    verified = bool(record.get("created_by")) and not unresolved_actor and (
        (record.get("revision") == 1 and not evidence) or record.get("content_authorship_status") == "VERIFIED"
    )
    value = {
        "content_author_ids": sorted(authors),
        "content_authorship_status": "VERIFIED" if verified else "INCOMPLETE",
        "source_revision": record.get("revision"),
        "audit_event_ids": sorted(set(evidence)),
    }
    value["evidence_hash"] = hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return value


class ReviewAuthorshipRepository:
    async def preview(self, project_id=None):
        items = []
        for collection, (entity_type, actions) in ARTIFACT_AUDIT_SOURCES.items():
            query = {"status": {"$in": ["DRAFT", "IN_REVIEW", "draft", "in_review"]}}
            if project_id:
                query["project_id"] = project_id
            async for record in database.value[collection].find(query):
                audit_query = {
                    "project_id": record["project_id"],
                    "entity_type": entity_type,
                    "entity_id": record.get("requirement_id") if collection == "requirement_versions" else record["_id"],
                    "action": {"$in": sorted(actions)},
                }
                if collection == "requirement_versions":
                    current = await database.value.requirements.find_one({
                        "_id": record.get("requirement_id"),
                        "project_id": record["project_id"],
                        "current_version_id": record["_id"],
                    })
                    if not current or not record.get("created_at"):
                        events = []
                    else:
                        audit_query["created_at"] = {"$gte": record["created_at"]}
                        events = await database.value.audit_events.find(audit_query).to_list(None)
                else:
                    events = await database.value.audit_events.find(audit_query).to_list(None)
                recovered = recovered_authorship(record, events, actions)
                previous = record.get("review_authorship_recovery") or {}
                items.append({
                    "collection": collection,
                    "entity_id": record["_id"],
                    "project_id": record["project_id"],
                    "expected_revision": record.get("revision"),
                    "already_applied": previous.get("evidence_hash") == recovered["evidence_hash"],
                    **recovered,
                })
        return items

    async def apply(self, actor_id, project_id=None):
        if not actor_id:
            raise ValueError("REVIEW_AUTHORSHIP_MIGRATION_ACTOR_REQUIRED")
        results = []
        for item in await self.preview(project_id):
            if item["content_authorship_status"] == "INCOMPLETE":
                results.append({"entity_id": item["entity_id"], "status": "REISSUE_REQUIRED", "content_author_ids": item["content_author_ids"], "audit_event_ids": item["audit_event_ids"]})
                continue
            if item["already_applied"]:
                results.append({"entity_id": item["entity_id"], "status": "UNCHANGED"})
                continue
            timestamp = datetime.now(timezone.utc)
            recovery = {key: item[key] for key in ("source_revision", "audit_event_ids", "evidence_hash")}
            recovery["checked_at"] = timestamp
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    updated = await database.value[item["collection"]].update_one(
                        {"_id": item["entity_id"], "project_id": item["project_id"], "revision": item["expected_revision"]},
                        {"$set": {
                            "content_author_ids": item["content_author_ids"],
                            "content_authorship_status": item["content_authorship_status"],
                            "review_authorship_recovery": recovery,
                        }},
                        session=session,
                    )
                    if updated.matched_count:
                        event_id = f"MIG-review-authorship:{item['collection']}:{item['entity_id']}:{item['evidence_hash']}"
                        await database.value.audit_events.update_one(
                            {"_id": event_id},
                            {"$setOnInsert": {
                                "project_id": item["project_id"], "actor_id": actor_id,
                                "action": "review_authorship_recovered", "entity_type": item["collection"],
                                "entity_id": item["entity_id"], "created_at": timestamp,
                                "details": {"content_authorship_status": item["content_authorship_status"], **recovery},
                            }}, upsert=True, session=session,
                        )
            results.append({"entity_id": item["entity_id"], "status": "APPLIED" if updated.matched_count else "REVISION_CHANGED"})
        return results


review_authorship_repository = ReviewAuthorshipRepository()
