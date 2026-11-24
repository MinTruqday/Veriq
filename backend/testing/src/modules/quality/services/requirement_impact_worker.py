"""Durable, read-only impact analysis for approved requirement revisions."""
import asyncio
import logging
import json
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from pymongo import ReturnDocument

from src.clients.authentication import load_accounts
from src.core.ai_capabilities import request_ai_capability
from src.core.auth import CurrentUser, SystemRole
from src.core.common import get_project, now
from src.core.database import database
from src.modules.quality.services.requirement_version_diff import compare_requirement_versions

logger = logging.getLogger(__name__)
_worker = None


def validated_suggestion(suggestion, before_text, after_text, case_text):
    """Keep only conclusions whose available source excerpts match exactly."""
    if not isinstance(suggestion, dict):
        return {}
    for field, source in (
        ("requirement_before_quote", before_text),
        ("requirement_after_quote", after_text),
        ("test_case_quote", case_text),
    ):
        quote = suggestion.get(field)
        if not source:
            if quote not in (None, ""):
                return {}
            continue
        if not isinstance(quote, str) or len(quote.strip()) < 2 or quote not in source:
            return {}
    if suggestion.get("classification") not in {
        "STILL_VALID", "POTENTIALLY_AFFECTED", "NEEDS_UPDATE", "OBSOLETE",
        "INSUFFICIENT_EVIDENCE",
    }:
        return {}
    return suggestion


async def _authorize(job):
    account = (await load_accounts([job["requested_by"]])).get(job["requested_by"], {})
    if account.get("is_active") is not True:
        raise HTTPException(403, detail={"code": "IMPACT_REQUESTER_UNAVAILABLE"})
    user = CurrentUser(_id=job["requested_by"], email="", system_role=SystemRole(account.get("system_role", "USER")))
    for permission in ("requirement.read", "testcase.read", "ai.run_impact"):
        await get_project(job["project_id"], user, permission)
    return account.get("locale")


async def _analyze(job):
    user_locale = await _authorize(job)
    project_id = job["project_id"]
    project = await database.value.projects.find_one({"_id": project_id}, {"locale": 1})
    output_language = user_locale or (project or {}).get("locale") or "auto"
    old = await database.value.requirement_versions.find_one({"_id": job["from_version_id"], "project_id": project_id, "status": "BASELINED"})
    new = await database.value.requirement_versions.find_one({"_id": job["to_version_id"], "project_id": project_id, "status": "BASELINED"})
    if not old or not new:
        raise ValueError("REQUIREMENT_VERSION_UNAVAILABLE")
    criteria = await database.value.acceptance_criteria.find({"project_id": project_id, "requirement_version_id": {"$in": [old["_id"], new["_id"]]}}).to_list(10001)
    if len(criteria) > 10000:
        raise ValueError("IMPACT_SOURCE_LIMIT_EXCEEDED")
    comparison = compare_requirement_versions(old, new, [c for c in criteria if c["requirement_version_id"] == old["_id"]], [c for c in criteria if c["requirement_version_id"] == new["_id"]])
    if not comparison["has_content_changes"]:
        return {"status": "NO_CONTENT_CHANGE", "comparison": comparison, "cases": [], "limitations": []}
    criterion_ids = [c["_id"] for c in criteria if c["requirement_version_id"] == old["_id"]]
    links = await database.value.trace_links.find({"project_id": project_id, "source_id": {"$in": [old["_id"], *criterion_ids]}, "target_type": "test_case_version", "status": "CONFIRMED"}, {"target_id": 1}).to_list(10001)
    if len(links) > 10000:
        raise ValueError("IMPACT_SOURCE_LIMIT_EXCEEDED")
    target_ids = [link["target_id"] for link in links if link.get("target_id")]
    # A plan can be the only bridge between a Requirement and its Test Cases.
    # Read those snapshots before resolving versions so plan-only coverage is
    # not silently omitted from the impact analysis.
    requirement_plans = await database.value.test_plans.find(
        {"project_id": project_id, "requirement_version_ids": old["_id"]},
        {"name": 1, "status": 1, "requirement_version_ids": 1,
         "test_case_version_ids": 1, "test_suite_snapshots": 1},
    ).to_list(10001)
    if len(requirement_plans) > 10000:
        raise ValueError("IMPACT_SOURCE_LIMIT_EXCEEDED")
    plan_case_version_ids = []
    for plan in requirement_plans:
        plan_case_version_ids.extend(plan.get("test_case_version_ids") or [])
        for snapshot in plan.get("test_suite_snapshots") or []:
            if isinstance(snapshot, dict):
                plan_case_version_ids.extend(snapshot.get("test_case_version_ids") or [])
    related_version_ids = list(dict.fromkeys([*target_ids, *plan_case_version_ids]))
    versions = await database.value.test_case_versions.find({"project_id": project_id, "$or": [{"requirement_version_ids": old["_id"]}, {"acceptance_criterion_ids": {"$in": criterion_ids}}, {"_id": {"$in": related_version_ids}}]}).to_list(10001)
    if len(versions) > 10000:
        raise ValueError("IMPACT_SOURCE_LIMIT_EXCEEDED")
    owners = await database.value.test_cases.find({"project_id": project_id, "current_version_id": {"$in": [v["_id"] for v in versions]}}, {"current_version_id": 1, "test_case_key": 1, "status": 1}).to_list(10001)
    current = {case["current_version_id"]: case for case in owners if case.get("status") in ("ACTIVE", "NEEDS_UPDATE")}
    versions = [version for version in versions if version["_id"] in current]
    case_ids = [version["_id"] for version in versions]
    plans = await database.value.test_plans.find({"project_id": project_id, "$or": [{"requirement_version_ids": old["_id"]}, {"test_case_version_ids": {"$in": case_ids}}, {"test_suite_snapshots.test_case_version_ids": {"$in": case_ids}}]}).to_list(10001)
    if len(plans) > 10000:
        raise ValueError("IMPACT_SOURCE_LIMIT_EXCEEDED")
    runs = await database.value.test_runs.find({"project_id": project_id, "$or": [{"test_case_version_ids": {"$in": case_ids}}, {"test_plan_id": {"$in": [p["_id"] for p in plans]}}]}, {"name": 1, "status": 1}).to_list(10001)
    if len(runs) > 10000:
        raise ValueError("IMPACT_SOURCE_LIMIT_EXCEEDED")
    before_text = "\n".join(item["before"] for item in comparison["changes"] if item["before"])
    after_text = "\n".join(item["after"] for item in comparison["changes"] if item["after"])
    results, limitations, new_candidates = [], [], []
    plan_results = []
    account = (await load_accounts([job["requested_by"]])).get(job["requested_by"], {})
    requester = CurrentUser(_id=job["requested_by"], email="", system_role=SystemRole(account.get("system_role", "USER")))
    try:
        await get_project(project_id, requester, "testplan.read")
        can_read_plans = True
    except HTTPException as error:
        if error.status_code != 403:
            raise
        can_read_plans = False
    fields = ("objective", "scope_in", "scope_out", "test_types", "test_techniques", "test_level", "test_approach", "environment", "environment_notes", "test_data_notes", "entry_criteria", "exit_criteria", "schedule", "estimation", "risk_register")
    if can_read_plans:
        for plan in plans:
            content = json.dumps({key: plan[key] for key in fields if plan.get(key)}, ensure_ascii=False, sort_keys=True, default=str)
            suggestion = {}
            if content != "{}" and len(content) <= 4000 and max(len(before_text), len(after_text)) <= 4000:
                evidence = []
                for kind, version, value in (("requirement_before", old, before_text), ("requirement_after", new, after_text)):
                    if value:
                        evidence.append({"artifact_type": kind, "artifact_id": version["_id"], "artifact_version_id": version["_id"], "text": value})
                evidence.append({"artifact_type": "test_plan", "artifact_id": plan["_id"], "artifact_version_id": plan["_id"], "text": content})
                ai = await request_ai_capability("impact_analysis", project_id, "Analyze the supplied Test Plan against the Requirement change. Return a plan_suggestion with exact source quotations; do not assess Test Cases or invent information.", evidence, output_language=output_language)
                if ai.get("status") == "SUCCESS" and not ai.get("degraded_mode"):
                    suggestion = next((item for item in ai.get("plan_suggestions", []) if item.get("plan_id") == plan["_id"]), {})
                else:
                    limitations.append("AI_UNAVAILABLE")
            def valid_quote(field, source):
                quote = suggestion.get(field)
                return (not source and not quote) or (isinstance(quote, str) and len(quote.strip()) >= 2 and quote in source)
            if not (suggestion.get("classification") in {"STILL_VALID", "POTENTIALLY_AFFECTED", "INSUFFICIENT_EVIDENCE"} and valid_quote("requirement_before_quote", before_text) and valid_quote("requirement_after_quote", after_text) and valid_quote("plan_quote", content)):
                suggestion = {}
            plan_results.append({"_id": plan["_id"], "name": plan.get("name"), "status": plan.get("status"), "revision": plan.get("revision"), "classification": suggestion.get("classification", "INSUFFICIENT_EVIDENCE"), "reason": suggestion.get("reason", "Chưa đủ căn cứ để phân tích tự động."), "suggestion": suggestion.get("suggestion", ""), "evidence": {key: suggestion.get(key) for key in ("requirement_before_quote", "requirement_after_quote", "plan_quote")}})
    if not versions:
        limitations.append("NO_LINKED_CASES")
    if len(before_text) > 4000 or len(after_text) > 4000:
        limitations.append("REQUIREMENT_CHANGE_TOO_LONG")
    for start in range(0, len(versions), 15):
        batch = versions[start:start + 15]
        suitable = [v for v in batch if 0 < len(str(v.get("plain_text_projection") or "")) <= 4000]
        suggestions = {}
        if suitable and (before_text or after_text) and len(before_text) <= 4000 and len(after_text) <= 4000:
            await _authorize(job)
            evidence = []
            if before_text:
                evidence.append({"artifact_type": "requirement_before", "artifact_id": old["_id"], "artifact_version_id": old["_id"], "text": before_text})
            if after_text:
                evidence.append({"artifact_type": "requirement_after", "artifact_id": new["_id"], "artifact_version_id": new["_id"], "text": after_text})
            evidence.extend({"artifact_type": "test_case_version", "artifact_id": v.get("test_case_id"), "artifact_version_id": v["_id"], "text": v["plain_text_projection"]} for v in suitable)
            instruction = (
                "Analyze each Test Case against the Requirement change. Use STILL_VALID or POTENTIALLY_AFFECTED "
                "only when a concrete step, data value, or expected result supports the conclusion. If a case has "
                "only a generic title, lacks steps or expected results, or cannot be tied to the changed behavior, "
                "use INSUFFICIENT_EVIDENCE; do not infer impact from a shared feature area. Quote verbatim from "
                "available sources. If the old or new version has no corresponding changed text, leave that side's "
                "quote empty and explain the absence in the reason; never invent a quotation or unsupported condition."
            )
            if not after_text:
                instruction += (
                    " The changed text was removed from the new version. If a Test Case verifies the removed rule, "
                    "do not classify it as STILL_VALID. Use POTENTIALLY_AFFECTED if the evidence does not show where "
                    "the rule moved; use OBSOLETE only when supplied evidence confirms the behavior was retired."
                )
            if not before_text:
                instruction += (
                    " This is newly added content. Classify STILL_VALID only if existing steps and expected results "
                    "clearly verify it; otherwise use INSUFFICIENT_EVIDENCE. If the new behavior is concrete and "
                    "testable and none of the supplied cases demonstrates coverage, propose one minimal new Test Case. "
                    "Quote the new Requirement exactly and leave the old-version quote empty."
                )
            ai = await request_ai_capability(
                "impact_analysis",
                project_id,
                instruction,
                evidence,
                output_language=output_language,
            )
            if ai.get("status") != "SUCCESS" or ai.get("degraded_mode"):
                limitations.append("AI_UNAVAILABLE")
            else:
                suggestions = {item.get("test_case_version_id"): item for item in ai.get("suggestions", []) if isinstance(item, dict)}
                for candidate in ai.get("new_test_candidates", []):
                    if not isinstance(candidate, dict):
                        continue
                    before_quote = candidate.get("requirement_before_quote")
                    after_quote = candidate.get("requirement_after_quote")
                    if (
                        (
                            (not before_text and before_quote in (None, ""))
                            or (bool(before_text) and isinstance(before_quote, str) and len(before_quote.strip()) >= 2 and before_quote in before_text)
                        )
                        and (
                            (not after_text and after_quote in (None, ""))
                            or (bool(after_text) and isinstance(after_quote, str) and len(after_quote.strip()) >= 2 and after_quote in after_text)
                        )
                        and isinstance(candidate.get("patch"), dict)
                    ):
                        new_candidates.append({
                            **{key: value for key, value in candidate.items() if key != "confidence"},
                            "requirement_before_absent": not bool(before_text),
                            "requirement_after_absent": not bool(after_text),
                        })
        for version in batch:
            suggestion = validated_suggestion(suggestions.get(version["_id"]), before_text, after_text, str(version.get("plain_text_projection") or ""))
            results.append({"version_id": version["_id"], "case_id": current[version["_id"]]["_id"], "case_key": current[version["_id"]].get("test_case_key"), "title": version.get("title"), "classification": suggestion.get("classification", "INSUFFICIENT_EVIDENCE"), "reason": suggestion.get("reason", "Chưa đủ căn cứ để phân tích tự động."), "proposed_patch": suggestion.get("maintenance_patch"), "evidence": {**{field: suggestion[field] for field in ("requirement_before_quote", "requirement_after_quote", "test_case_quote") if field in suggestion}, "requirement_before_absent": not bool(before_text), "requirement_after_absent": not bool(after_text)}})
    await _authorize(job)
    latest = await database.value.requirements.find_one({"_id": job["requirement_id"], "project_id": project_id}, {"current_version_id": 1})
    if not latest or latest.get("current_version_id") != new["_id"]:
        return {"status": "STALE", "comparison": comparison, "cases": [], "limitations": ["REQUIREMENT_CHANGED"]}
    latest_cases = await database.value.test_cases.find(
        {"project_id": project_id, "_id": {"$in": [case["_id"] for case in current.values()]}},
        {"current_version_id": 1, "status": 1},
    ).to_list(10001)
    latest_versions = {case.get("current_version_id") for case in latest_cases if case.get("status") in ("ACTIVE", "NEEDS_UPDATE")}
    if set(case_ids) != latest_versions:
        return {"status": "STALE", "comparison": comparison, "cases": [], "limitations": ["TEST_CASE_CHANGED"]}
    if can_read_plans:
        latest_plans = await database.value.test_plans.find({"project_id": project_id, "_id": {"$in": [p["_id"] for p in plans]}}, {"revision": 1}).to_list(10001)
        if {p["_id"]: p.get("revision") for p in latest_plans} != {p["_id"]: p.get("revision") for p in plans}:
            return {"status": "STALE", "comparison": comparison, "cases": [], "limitations": ["TEST_PLAN_CHANGED"]}
    return {"status": "PARTIAL" if limitations or any(c["classification"] == "INSUFFICIENT_EVIDENCE" for c in results + plan_results) else "COMPLETED", "comparison": comparison, "cases": results, "new_candidates": new_candidates, "plans": plan_results, "runs": runs, "limitations": list(set(limitations))}


async def process_next_requirement_impact():
    timestamp = now()
    token = str(uuid4())
    job = await database.value.requirement_impact_jobs.find_one_and_update({"$or": [{"status": "PENDING"}, {"status": "RUNNING", "lease_until": {"$lt": timestamp}}]}, {"$set": {"status": "RUNNING", "lease_token": token, "lease_until": timestamp + timedelta(hours=2), "updated_at": timestamp}}, sort=[("created_at", 1)], return_document=ReturnDocument.AFTER)
    if not job:
        return False
    try:
        result = await _analyze(job)
    except HTTPException as error:
        result = {"status": "FAILED", "error_code": (error.detail or {}).get("code", "IMPACT_ACCESS_UNAVAILABLE") if isinstance(error.detail, dict) else "IMPACT_ACCESS_UNAVAILABLE"}
    except Exception:
        logger.exception("Requirement impact analysis failed")
        result = {"status": "FAILED", "error_code": "IMPACT_ANALYSIS_FAILED"}
    await database.value.requirement_impact_jobs.update_one({"_id": job["_id"], "status": "RUNNING", "lease_token": token}, {"$set": {**result, "updated_at": now()}, "$unset": {"lease_token": "", "lease_until": ""}})
    return True


async def _poll():
    while True:
        try:
            if await process_next_requirement_impact():
                continue
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Requirement impact worker failed")
        await asyncio.sleep(5)


async def start_requirement_impact_worker():
    global _worker
    if _worker is None or _worker.done():
        _worker = asyncio.create_task(_poll())


async def stop_requirement_impact_worker():
    global _worker
    if _worker:
        _worker.cancel()
        try:
            await _worker
        except asyncio.CancelledError:
            pass
        _worker = None
