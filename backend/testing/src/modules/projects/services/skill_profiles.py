import asyncio
import hashlib
import heapq
import logging
import re
import unicodedata
from datetime import date, timedelta
from itertools import chain

import httpx
from fastapi import HTTPException, UploadFile
from pymongo.errors import DuplicateKeyError

from src.clients.ai_automation import ai_automation_client
from src.clients.document_conversion import convert_requirement_source
from src.core.auth import roles_for_membership
from src.core.common import audit, get_project, get_project_entity, load_user_identities, now
from src.core.configuration import settings
from src.core.database import database
from src.repositories.project import project_repository
from src.repositories.skill_profile import skill_profile_repository
from src.repositories.test_run import test_run_repository

CV_SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".txt"})
CV_MAX_EXTRACTED_CHARACTERS = 100_000
CV_MAX_SOURCE_BLOCKS = 500
CV_SOURCE_BLOCK_CHARACTERS = 3_000
logger = logging.getLogger(__name__)


def _cv_source_blocks(conversion):
    structure = conversion.structure or []

    def extracted_candidates():
        for item in structure:
            if item.extraction_status == "EXTRACTED" and item.text.strip():
                yield item

    candidate_iterator = iter(extracted_candidates())
    first_candidate = next(candidate_iterator, None)
    if first_candidate is not None:
        candidates = chain((first_candidate,), candidate_iterator)
    elif conversion.markdown.strip():
        candidates = (
            {
                "block_id": f"markdown:{index}",
                "page_no": None,
                "text": match.group(1).strip(),
            }
            for index, match in enumerate(
                re.finditer(
                    r"(?s)(?:^|\n\n)(.*?)(?=\n\n|$)",
                    conversion.markdown,
                )
            )
            if match.group(1).strip()
        )
    else:
        candidates = ()

    blocks = []
    total_characters = 0
    truncated = False
    for item in candidates:
        if isinstance(item, dict):
            block_id_value = item.get("block_id")
            page_no = item.get("page_no")
            text = str(item.get("text") or "").strip()
        else:
            block_id_value = item.block_id
            page_no = item.page_no
            text = item.text.strip()
        for offset in range(0, len(text), CV_SOURCE_BLOCK_CHARACTERS):
            if len(blocks) >= CV_MAX_SOURCE_BLOCKS:
                truncated = True
                break
            piece = text[offset : offset + CV_SOURCE_BLOCK_CHARACTERS]
            if total_characters + len(piece) > CV_MAX_EXTRACTED_CHARACTERS:
                truncated = True
                break
            block_id = str(block_id_value or f"source:{len(blocks)}")
            if len(text) > CV_SOURCE_BLOCK_CHARACTERS:
                block_id = f"{block_id}:part:{offset // CV_SOURCE_BLOCK_CHARACTERS + 1}"
            blocks.append({"block_id": block_id, "page_no": page_no, "text": piece})
            total_characters += len(piece)
        if truncated:
            break
    return blocks, total_characters, truncated


def _validate_cv_candidate_evidence(source_blocks, extracted):
    if not isinstance(extracted, dict):
        return False
    blocks_by_id = {item["block_id"]: item for item in source_blocks}
    if len(blocks_by_id) != len(source_blocks):
        return False
    for category in ("skills", "experiences"):
        candidates = extracted.get(category) or []
        if not isinstance(candidates, list):
            return False
        for candidate in candidates:
            if not isinstance(candidate, dict):
                return False
            source = blocks_by_id.get(candidate.get("source_block_id"))
            quote = candidate.get("evidence_quote")
            if (
                not source
                or not isinstance(quote, str)
                or not quote
                or quote not in source["text"]
                or candidate.get("page_no") != source["page_no"]
            ):
                return False
            claims = (
                [candidate.get("name")]
                if category == "skills"
                else [
                    candidate.get("title"),
                    candidate.get("period"),
                    candidate.get("domain"),
                    *(candidate.get("technologies") or []),
                    candidate.get("responsibilities"),
                ]
            )
            required_claims = [str(value).strip() for value in claims if str(value or "").strip()]
            if not required_claims or any(
                not _cv_claim_is_present(value, quote)
                for value in required_claims
            ):
                return False
            citation_anchor = candidate.get("name") if category == "skills" else candidate.get("title")
            if not isinstance(citation_anchor, str) or not citation_anchor.strip():
                return False
            if not _cv_claim_is_present(citation_anchor, quote):
                return False
    return True


def _cv_profile_entries(extracted, source_sha256):
    skills = []
    seen_skills = set()
    for candidate in extracted.get("skills") or []:
        name = " ".join(str(candidate.get("name") or "").split())
        key = _normalized(name)
        if not key or key in seen_skills:
            continue
        seen_skills.add(key)
        skills.append({
            "name": name,
            "level": "",
            "evidence": candidate["evidence_quote"],
            "source_block_id": candidate["source_block_id"],
            "source_page_no": candidate.get("page_no"),
            "source_sha256": source_sha256,
            "source_kind": "CV_EXTRACTED",
            "confirmed": False,
        })
    experiences = []
    seen_experiences = set()
    for candidate in extracted.get("experiences") or []:
        key = (
            _normalized(candidate.get("title")),
            _normalized(candidate.get("period")),
            _normalized(candidate.get("domain")),
        )
        if key in seen_experiences:
            continue
        seen_experiences.add(key)
        experiences.append({
            "title": candidate["title"],
            "period": candidate.get("period", ""),
            "domain": candidate.get("domain", ""),
            "technologies": candidate.get("technologies") or [],
            "responsibilities": candidate.get("responsibilities", ""),
            "evidence": candidate["evidence_quote"],
            "source_block_id": candidate["source_block_id"],
            "source_page_no": candidate.get("page_no"),
            "source_sha256": source_sha256,
            "source_kind": "CV_EXTRACTED",
            "confirmed": False,
        })
    return skills, experiences


async def _persist_cv_profile(project_id, user, extracted, source_sha256):
    existing = await skill_profile_repository.find(project_id, user.id)
    current_skills = list((existing or {}).get("skills") or [])
    current_experiences = list((existing or {}).get("experiences") or [])
    declared_skills = [item for item in current_skills if item.get("source_kind") != "CV_EXTRACTED"]
    declared_experiences = [item for item in current_experiences if item.get("source_kind") != "CV_EXTRACTED"]
    extracted_skills, extracted_experiences = _cv_profile_entries(extracted, source_sha256)
    has_old_cv_facts = len(declared_skills) != len(current_skills) or len(declared_experiences) != len(current_experiences)
    if not extracted_skills and not extracted_experiences and not has_old_cv_facts:
        return existing or {
            "project_id": project_id,
            "user_id": user.id,
            "skills": [],
            "experiences": [],
            "availability": "AVAILABLE",
            "revision": 0,
        }, False
    declared_skill_keys = {_normalized(item.get("name")) for item in declared_skills}
    extracted_skills = [item for item in extracted_skills if _normalized(item["name"]) not in declared_skill_keys]
    experience_keys = {
        (_normalized(item.get("title")), _normalized(item.get("period")), _normalized(item.get("domain")))
        for item in declared_experiences
    }
    merged_experiences = declared_experiences + [
        item for item in extracted_experiences
        if (_normalized(item["title"]), _normalized(item["period"]), _normalized(item["domain"])) not in experience_keys
    ]
    merged_skills = declared_skills + extracted_skills
    changes = {
        "skills": merged_skills,
        "experiences": merged_experiences,
        "availability": (existing or {}).get("availability", "AVAILABLE"),
    }
    if existing and all(existing.get(key) == value for key, value in changes.items()):
        return existing, False
    expected_revision = (existing or {}).get("revision", 0)
    timestamp = now()
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                updated = await skill_profile_repository.upsert(
                    project_id,
                    user.id,
                    expected_revision,
                    changes,
                    timestamp,
                    session=session,
                )
                if not updated:
                    raise HTTPException(status_code=409, detail={"code": "SKILL_PROFILE_REVISION_CONFLICT"})
                await audit(
                    user.id,
                    "member_skill_profile_cv_extracted",
                    "MemberSkillProfile",
                    user.id,
                    project_id,
                    session=session,
                )
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail={"code": "SKILL_PROFILE_REVISION_CONFLICT"}) from exc
    return updated, True


def _cv_claim_is_present(claim, evidence):
    normalized_claim = " ".join(unicodedata.normalize("NFC", str(claim)).casefold().split())
    normalized_evidence = " ".join(unicodedata.normalize("NFC", str(evidence)).casefold().split())
    if not normalized_claim:
        return True
    pattern = rf"(?<!\w){re.escape(normalized_claim)}(?!\w)"
    return re.search(pattern, normalized_evidence, flags=re.UNICODE) is not None


async def extract_own_skill_profile_from_cv(project_id, file: UploadFile, user):
    try:
        await get_project(project_id, user, "project.read")
        filename = str(file.filename or "").strip()
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in CV_SUPPORTED_SUFFIXES:
            raise HTTPException(status_code=422, detail={"code": "CV_FORMAT_UNSUPPORTED"})
        content = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
        if not content:
            raise HTTPException(status_code=422, detail={"code": "CV_FILE_EMPTY"})
        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail={"code": "CV_FILE_TOO_LARGE"})
        source_sha256 = hashlib.sha256(content).hexdigest()
        try:
            conversion = await convert_requirement_source(content, filename)
        except Exception as error:
            raise HTTPException(status_code=422, detail={"code": "CV_CONVERSION_FAILED"}) from error
    finally:
        await file.close()

    source_blocks, extracted_characters, source_truncated = _cv_source_blocks(conversion)
    if not source_blocks:
        raise HTTPException(status_code=422, detail={"code": "CV_TEXT_NOT_EXTRACTED"})
    try:
        for attempt in range(2):
            try:
                extracted = await ai_automation_client.extract_skill_profile(
                    project_id, source_blocks
                )
                break
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if attempt:
                    raise
                await asyncio.sleep(0.5)
    except httpx.HTTPStatusError as error:
        response_code = None
        try:
            payload = error.response.json()
            detail = payload.get("detail") if isinstance(payload, dict) else None
            response_code = detail.get("code") if isinstance(detail, dict) else None
        except (ValueError, TypeError):
            pass
        logger.warning(
            "CV AI extraction rejected status=%s code=%s",
            error.response.status_code,
            response_code or "unavailable",
        )
        if error.response.status_code == 413 and response_code == "CV_TEXT_LIMIT_EXCEEDED":
            raise HTTPException(
                status_code=413, detail={"code": "CV_TEXT_LIMIT_EXCEEDED"}
            ) from error
        if error.response.status_code == 422 and response_code == "CV_CONTENT_UNSAFE":
            raise HTTPException(
                status_code=422, detail={"code": "CV_CONTENT_UNSAFE"}
            ) from error
        if response_code in {
            "CV_EVIDENCE_NOT_FOUND",
            "CV_PAGE_REFERENCE_MISMATCH",
            "CV_CLAIM_NOT_GROUNDED",
        }:
            raise HTTPException(
                status_code=502, detail={"code": "CV_AI_EVIDENCE_INVALID"}
            ) from error
        raise HTTPException(
            status_code=502, detail={"code": "CV_AI_EXTRACTION_UNAVAILABLE"}
        ) from error
    except Exception as error:
        logger.warning(
            "CV AI extraction request failed error_type=%s",
            type(error).__name__,
        )
        raise HTTPException(status_code=502, detail={"code": "CV_AI_EXTRACTION_UNAVAILABLE"}) from error
    if not _validate_cv_candidate_evidence(source_blocks, extracted):
        raise HTTPException(status_code=502, detail={"code": "CV_AI_EVIDENCE_INVALID"})

    profile, profile_changed = await _persist_cv_profile(
        project_id, user, extracted, source_sha256
    )

    warnings = list(extracted.get("warnings") or [])
    if conversion.unprocessed_blocks:
        warnings.append("CV_HAS_UNPROCESSED_SOURCE_BLOCKS")
    if source_truncated:
        warnings.append("CV_EXTRACTION_INPUT_LIMIT_REACHED")
    return {
        "project_id": project_id,
        "skills": extracted.get("skills") or [],
        "experiences": extracted.get("experiences") or [],
        "profile": _public_profile(profile),
        "warnings": list(dict.fromkeys(warnings)),
        "parser": conversion.parser,
        "parser_version": conversion.parser_version,
        "page_count": conversion.page_count,
        "source_block_count": len(source_blocks),
        "extracted_characters": extracted_characters,
        "source_sha256": source_sha256,
        "cv_persisted": False,
        "profile_facts_persisted": any(
            item.get("source_kind") == "CV_EXTRACTED" and item.get("source_sha256") == source_sha256
            for item in [*(profile.get("skills") or []), *(profile.get("experiences") or [])]
        ),
        "profile_changed": profile_changed,
        "profile_revision": profile.get("revision", 0),
        "indexed_in_project_knowledge": False,
    }


def _public_profile(profile):
    return {
        "project_id": profile["project_id"],
        "user_id": profile["user_id"],
        "skills": profile.get("skills", []),
        "experiences": profile.get("experiences", []),
        "availability": profile.get("availability", "AVAILABLE"),
        "revision": profile.get("revision", 1),
        "updated_at": profile.get("updated_at"),
    }


def _matches_cv_skill_source(submitted, stored):
    return (
        stored.get("source_kind") == "CV_EXTRACTED"
        and bool(stored.get("source_sha256"))
        and all(
            submitted.get(field) == stored.get(field)
            for field in (
                "name",
                "evidence",
                "source_block_id",
                "source_page_no",
                "source_sha256",
            )
        )
    )


def _matches_cv_experience_source(submitted, stored):
    return (
        stored.get("source_kind") == "CV_EXTRACTED"
        and bool(stored.get("source_sha256"))
        and all(
            submitted.get(field) == stored.get(field)
            for field in (
                "title",
                "period",
                "domain",
                "technologies",
                "responsibilities",
                "evidence",
                "source_block_id",
                "source_page_no",
                "source_sha256",
            )
        )
    )


def _profile_patch_with_trusted_sources(changes, existing):
    stored_skills = {
        _normalized(item.get("name")): item
        for item in (existing or {}).get("skills", [])
        if item.get("source_kind") == "CV_EXTRACTED"
    }
    stored_experiences = {
        (
            _normalized(item.get("title")),
            _normalized(item.get("period")),
            _normalized(item.get("domain")),
        ): item
        for item in (existing or {}).get("experiences", [])
        if item.get("source_kind") == "CV_EXTRACTED"
    }

    for skill in changes.get("skills", []):
        stored = stored_skills.get(_normalized(skill.get("name")))
        if stored and _matches_cv_skill_source(skill, stored):
            skill["source_kind"] = "CV_EXTRACTED"
        else:
            skill["source_kind"] = "MEMBER_DECLARED"
            skill["source_block_id"] = None
            skill["source_page_no"] = None
            skill["source_sha256"] = None

    for experience in changes.get("experiences", []):
        key = (
            _normalized(experience.get("title")),
            _normalized(experience.get("period")),
            _normalized(experience.get("domain")),
        )
        stored = stored_experiences.get(key)
        if stored and _matches_cv_experience_source(experience, stored):
            experience["source_kind"] = "CV_EXTRACTED"
        else:
            experience["source_kind"] = "MEMBER_DECLARED"
            experience["source_block_id"] = None
            experience["source_page_no"] = None
            experience["source_sha256"] = None
    return changes


async def get_own_skill_profile(project_id, user):
    await get_project(project_id, user, "project.read")
    profile = await skill_profile_repository.find(project_id, user.id)
    if not profile:
        return {
            "project_id": project_id,
            "user_id": user.id,
            "skills": [],
            "experiences": [],
            "availability": "AVAILABLE",
            "revision": 0,
        }
    return _public_profile(profile)


async def update_own_skill_profile(project_id, payload, user):
    await get_project(project_id, user, "project.read")
    changes = payload.model_dump(exclude={"expected_revision"})
    existing = await skill_profile_repository.find(project_id, user.id)
    changes = _profile_patch_with_trusted_sources(changes, existing)
    timestamp = now()
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                updated = await skill_profile_repository.upsert(
                    project_id,
                    user.id,
                    payload.expected_revision,
                    changes,
                    timestamp,
                    session=session,
                )
                if not updated:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "SKILL_PROFILE_REVISION_CONFLICT"},
                    )
                await audit(
                    user.id,
                    "member_skill_profile_updated",
                    "MemberSkillProfile",
                    user.id,
                    project_id,
                    session=session,
                )
    except DuplicateKeyError as exc:
        if payload.expected_revision == 0:
            raise HTTPException(
                status_code=409,
                detail={"code": "SKILL_PROFILE_REVISION_CONFLICT"},
            ) from exc
        raise
    return _public_profile(updated)


def _normalized(value):
    return " ".join(str(value).strip().casefold().split())


def _skill_key(value):
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(normalized.split())


def _availability_rank(value):
    return {"AVAILABLE": 0, "LIMITED": 1}.get(value, 2)


async def _project_capacity_limits(
    user_ids,
    period_start=None,
    period_end=None,
    *,
    session=None,
    fence_periods=False,
):
    if not user_ids:
        return "CAPACITY_NOT_DECLARED", {}
    start = str(period_start or now().date().isoformat())[:10]
    end = str(period_end or start)[:10]
    periods = await database.value.resource_capacity_periods.find(
        {"period_start": {"$lte": end}, "period_end": {"$gte": start}},
        session=session,
    ).to_list(100)
    if fence_periods and session is not None:
        for period in sorted(periods, key=lambda item: item["_id"]):
            fenced = await database.value.resource_capacity_periods.update_one(
                {"_id": period["_id"], "revision": period.get("revision", 1)},
                {"$inc": {"assignment_fence_revision": 1}},
                session=session,
            )
            if fenced.matched_count != 1:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "RESOURCE_CAPACITY_CHANGED_RETRY_ASSIGNMENT"},
                )
    if not periods:
        if await database.value.resource_capacity_periods.count_documents(
            {}, session=session
        ):
            return "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE", {}
        return "CAPACITY_NOT_DECLARED", {}
    periods.sort(key=lambda item: (item.get("period_start", ""), item.get("period_end", "")))
    requested_start = date.fromisoformat(start)
    requested_end = date.fromisoformat(end)
    first_start = date.fromisoformat(periods[0]["period_start"])
    covered_until = date.fromisoformat(periods[0]["period_end"])
    if first_start > requested_start or covered_until < requested_start:
        return "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE", {}
    for period in periods[1:]:
        period_start = date.fromisoformat(period["period_start"])
        period_end = date.fromisoformat(period["period_end"])
        if period_start <= covered_until:
            return "AMBIGUOUS_CAPACITY_PERIOD", {}
        if period_start > covered_until + timedelta(days=1):
            return "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE", {}
        covered_until = max(covered_until, period_end)
    if covered_until < requested_end:
        return "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE", {}
    limits_by_period = [
        {
            item.get("user_id"): item["max_concurrent_projects"]
            for item in period.get("entries") or []
            if item.get("user_id") and item.get("max_concurrent_projects") is not None
        }
        for period in periods
    ]
    user_ids_with_limits = set().union(*(set(item) for item in limits_by_period))
    limits = {
        user_id: min(period_limits[user_id] for period_limits in limits_by_period)
        for user_id in user_ids_with_limits
        if all(user_id in period_limits for period_limits in limits_by_period)
    }
    return "PROJECT_LIMITS_PARTIALLY_DECLARED" if limits else "PROJECT_LIMIT_NOT_DECLARED", limits


async def _check_test_run_assignment_capacity(
    project_id,
    run,
    user_ids,
    *,
    session,
    existing_run_user_ids=(),
):
    user_ids = set(user_ids)
    if not user_ids:
        return
    schedule = run.get("test_plan_schedule_snapshot") or {}
    capacity_status, limits = await _project_capacity_limits(
        sorted(user_ids),
        schedule.get("planned_start_at"),
        schedule.get("planned_end_at"),
        session=session,
        fence_periods=True,
    )
    if not limits:
        return
    project_workload = await _member_project_workload(
        user_ids,
        schedule,
        session=session,
        exclude_run_id=run.get("_id"),
    )
    for user_id in set(existing_run_user_ids).intersection(user_ids):
        project_workload[user_id].add(project_id)
    exceeded = {
        user_id: {
            "active_project_count": len(projects),
            "max_concurrent_projects": limits[user_id],
        }
        for user_id, projects in project_workload.items()
        if user_id in limits
        and project_id not in projects
        and len(projects) >= limits[user_id]
    }
    if exceeded:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MAX_CONCURRENT_PROJECTS_REACHED",
                "users": exceeded,
                "capacity_status": capacity_status,
            },
        )


async def _member_project_workload(
    user_ids,
    schedule,
    *,
    session=None,
    exclude_run_id=None,
    exclude_plan_id=None,
):
    user_ids = set(user_ids)
    workload = {user_id: set() for user_id in user_ids}
    start_value = str(schedule.get("planned_start_at") or now().date().isoformat())[:10]
    end_value = str(schedule.get("planned_end_at") or start_value)[:10]
    async for active_run in skill_profile_repository.iter_active_runs_for_members(
        sorted(user_ids),
        session=session,
        exclude_run_id=exclude_run_id,
        include_drafts=True,
    ):
        run_schedule = active_run.get("test_plan_schedule_snapshot") or {}
        run_start = str(run_schedule.get("planned_start_at") or "")[:10]
        run_end = str(run_schedule.get("planned_end_at") or "")[:10]
        if (
            run_start
            and run_end
            and (run_start > end_value or run_end < start_value)
        ):
            continue
        assigned = set((active_run.get("test_case_assignments") or {}).values())
        if active_run.get("assignee_id"):
            assigned.add(active_run["assignee_id"])
        project_id = active_run.get("project_id")
        if project_id:
            for user_id in assigned.intersection(user_ids):
                workload[user_id].add(project_id)

    plan_query = {
        "status": {"$in": ["IN_REVIEW", "APPROVED"]},
        "schedule.planned_start_at": {"$lte": f"{end_value}T23:59:59.999999"},
        "schedule.planned_end_at": {"$gte": start_value},
    }
    if exclude_plan_id:
        plan_query["_id"] = {"$ne": exclude_plan_id}
    plans = database.value.test_plans.find(
        plan_query,
        {
            "project_id": 1,
            "schedule.planned_start_at": 1,
            "schedule.planned_end_at": 1,
            "estimation.effort_allocations": 1,
        },
        session=session,
    )
    async for plan in plans:
        other_schedule = plan.get("schedule") or {}
        other_start = str(other_schedule.get("planned_start_at") or "")[:10]
        other_end = str(other_schedule.get("planned_end_at") or "")[:10]
        if not other_start or not other_end or other_start > end_value or other_end < start_value:
            continue
        project_id = plan.get("project_id")
        if not project_id:
            continue
        for allocation in (plan.get("estimation") or {}).get("effort_allocations") or []:
            user_id = allocation.get("user_id")
            if user_id in user_ids:
                workload[user_id].add(project_id)
    return workload


async def _check_test_plan_assignment_capacity(
    project_id,
    schedule,
    user_ids,
    *,
    session,
    exclude_plan_id=None,
):
    user_ids = set(user_ids)
    if not user_ids:
        return
    start = (schedule or {}).get("planned_start_at")
    end = (schedule or {}).get("planned_end_at")
    if not start or not end:
        return
    capacity_status, limits = await _project_capacity_limits(
        sorted(user_ids), start, end, session=session, fence_periods=True
    )
    if not limits:
        return
    workload = await _member_project_workload(
        user_ids,
        schedule,
        session=session,
        exclude_plan_id=exclude_plan_id,
    )
    exceeded = {
        user_id: {
            "active_project_count": len(projects),
            "max_concurrent_projects": limits[user_id],
        }
        for user_id, projects in workload.items()
        if user_id in limits
        and project_id not in projects
        and len(projects) >= limits[user_id]
    }
    if exceeded:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MAX_CONCURRENT_PROJECTS_REACHED",
                "users": exceeded,
                "capacity_status": capacity_status,
            },
        )


def _owner_decision_context(candidates, profiles, project_workload):
    results = {}
    for member_id, candidate in candidates.items():
        profile = profiles.get(member_id) or {}
        factors = {
            "skill_evidence": [
                {
                    "required_skill": item.get("required_skill"),
                    "profile_skill": item.get("name"),
                    "reported_level": item.get("level", ""),
                    "evidence_status": item.get("evidence_status", "DECLARED"),
                    "independently_assessed": item.get("independently_assessed") is True,
                }
                for item in candidate["matched_skill_evidence"]
            ],
            "availability": candidate["availability"],
            "workload": {
                "active_cases": candidate["active_case_count"],
                "active_runs": candidate["active_run_count"],
                "active_projects": len(project_workload.get(member_id, set())),
            },
        }
        experiences = [item for item in profile.get("experiences", []) if item.get("confirmed") is True]
        factors["experience_evidence"] = [
            {
                "title": item.get("title"),
                "domain": item.get("domain"),
                "technologies": item.get("technologies") or [],
                "source_kind": item.get("source_kind", "MEMBER_DECLARED"),
                        "independently_assessed": False,
            }
            for item in experiences
        ]
        results[member_id] = {
            "context": factors,
            "context_status": {
                "skill_evidence": "PROFILE_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED",
                "experience_evidence": "PROFILE_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED" if experiences else "NO_CONFIRMED_EXPERIENCE_EVIDENCE",
            },
        }
    return results


def _confirmed_skills(profile):
    confirmed = {}
    for skill in profile.get("skills", []):
        if skill.get("confirmed") is not True:
            continue
        key = _skill_key(skill.get("name"))
        if key:
            confirmed.setdefault(key, skill)
    return confirmed


def _assignment_skills(profile):
    return _confirmed_skills(profile)


def rank_skill_candidates(
    memberships, profiles, workloads, required_skills, *, case_workloads=None
):
    required_by_key = {}
    for value in required_skills:
        key = _skill_key(value)
        if key:
            required_by_key.setdefault(key, str(value).strip())
    required_keys = list(required_by_key)
    case_workloads = case_workloads or {}
    profile_by_user = {item["user_id"]: item for item in profiles}
    candidates = []
    for member in memberships:
        member_id = member["user_id"]
        profile = profile_by_user.get(member_id, {})
        availability = profile.get("availability", "AVAILABLE")
        if availability == "UNAVAILABLE":
            continue
        usable = _assignment_skills(profile)
        matched = [skill for skill in required_keys if skill in usable]
        candidates.append(
            {
                "user_id": member_id,
                "matched_skills": [usable[key].get("name") for key in matched],
                "matched_required_skills": [required_by_key[key] for key in matched],
                "confirmed_skills": [item.get("name") for item in usable.values() if item.get("name")],
                "matched_skill_evidence": [
                    {
                        "required_skill": required_by_key[key],
                        "name": usable[key].get("name"),
                        "level": usable[key].get("level", ""),
                        "source_kind": usable[key].get("source_kind", "MEMBER_DECLARED"),
                        "evidence_status": (
                            "DOCUMENT_SUPPORTED"
                            if usable[key].get("source_kind") == "CV_EXTRACTED"
                            and str(usable[key].get("evidence") or "").strip()
                            else "DECLARED"
                        ),
                        "independently_assessed": False,
                        "confirmed": usable[key].get("confirmed") is True,
                    }
                    for key in matched
                ],
                "unmatched_skills": [required_by_key[key] for key in required_keys if key not in usable],
                "availability": profile.get("availability", "PROFILE_NOT_SET"),
                "active_run_count": workloads.get(member_id, 0),
                "active_case_count": case_workloads.get(member_id, 0),
                "profile_exists": bool(profile),
                "skill_match_count": len(matched),
                "matched_skill_count": len(matched),
            }
        )
    return list(required_by_key.values()), candidates


def _minimum_cost_case_assignment(case_ids, options_by_case, base_workloads):
    candidate_ids = sorted({candidate_id for options in options_by_case.values() for candidate_id in options})
    if not case_ids or not candidate_ids:
        return {}

    source = 0
    case_offset = 1
    candidate_offset = case_offset + len(case_ids)
    sink = candidate_offset + len(candidate_ids)
    graph = [[] for _ in range(sink + 1)]

    def add_edge(start, end, capacity, cost):
        forward = [end, len(graph[end]), capacity, cost]
        reverse = [start, len(graph[start]), 0, -cost]
        graph[start].append(forward)
        graph[end].append(reverse)
        return forward

    candidate_index = {candidate_id: candidate_offset + index for index, candidate_id in enumerate(candidate_ids)}
    assignment_edges = {}
    for index, case_id in enumerate(case_ids):
        case_node = case_offset + index
        add_edge(source, case_node, 1, 0)
        options = options_by_case.get(case_id, {})
        if not options:
            continue
        for candidate_id in options:
            assignment_edges[(case_id, candidate_id)] = add_edge(
                case_node,
                candidate_index[candidate_id],
                1,
                0,
            )
    for candidate_id in candidate_ids:
        candidate_node = candidate_index[candidate_id]
        base_load = max(0, int(base_workloads.get(candidate_id, 0)))
        for slot in range(len(case_ids)):
            current_load = base_load + slot
            add_edge(candidate_node, sink, 1, (current_load + 1) ** 2 - current_load**2)

    node_count = len(graph)
    potentials = [0] * node_count
    while True:
        distances = [float("inf")] * node_count
        previous = [None] * node_count
        distances[source] = 0
        queue = [(0, source)]
        while queue:
            distance, node = heapq.heappop(queue)
            if distance != distances[node]:
                continue
            for edge_index, edge in enumerate(graph[node]):
                target, _, capacity, cost = edge
                if capacity <= 0:
                    continue
                next_distance = distance + cost + potentials[node] - potentials[target]
                if next_distance < distances[target]:
                    distances[target] = next_distance
                    previous[target] = (node, edge_index)
                    heapq.heappush(queue, (next_distance, target))
        if previous[sink] is None:
            break
        for node, distance in enumerate(distances):
            if distance < float("inf"):
                potentials[node] += distance
        node = sink
        while node != source:
            parent, edge_index = previous[node]
            edge = graph[parent][edge_index]
            edge[2] -= 1
            graph[node][edge[1]][2] += 1
            node = parent

    result = {}
    for (case_id, candidate_id), edge in assignment_edges.items():
        if edge[2] == 0:
            result[case_id] = candidate_id
    return result


def _opaque_staffing_candidate_refs(user_ids):
    return {
        f"candidate-{index + 1}": user_id
        for index, user_id in enumerate(user_ids)
    }


def _map_staffing_recommendations(recommendations, candidate_ref_to_user):
    recommendation_ids = [
        item.get("candidate_id")
        for item in recommendations
        if isinstance(item, dict)
    ]
    if (
        len(recommendation_ids) != len(recommendations)
        or any(not isinstance(item, str) or not item for item in recommendation_ids)
        or len(recommendation_ids) != len(set(recommendation_ids))
        or set(recommendation_ids) != set(candidate_ref_to_user)
    ):
        raise HTTPException(
            status_code=502,
            detail={"code": "AI_OWNER_RECOMMENDATION_CANDIDATES_INVALID"},
        )
    return {
        candidate_ref_to_user[item["candidate_id"]]: item
        for item in recommendations
    }


async def automatically_assign_test_cases(
    project_id,
    versions,
    session=None,
    existing_case_assignments=None,
    existing_assignee_id=None,
    exclude_run_id=None,
    schedule=None,
):
    memberships = await project_repository.list_members(project_id, session=session)
    eligible = [
        item for item in memberships
        if item.get("status") == "ACTIVE" and "TESTER" in roles_for_membership(item)
    ]
    eligible_ids = [item["user_id"] for item in eligible]
    profiles = await skill_profile_repository.list_for_members(
        project_id, eligible_ids, session=session
    )
    profiles_by_user = {item["user_id"]: item for item in profiles}
    case_load = {member_id: 0 for member_id in eligible_ids}
    run_load = {member_id: 0 for member_id in eligible_ids}
    schedule = schedule or {}
    project_workload = await _member_project_workload(
        eligible_ids,
        schedule,
        session=session,
        exclude_run_id=exclude_run_id,
    )
    _, project_limits = await _project_capacity_limits(
        eligible_ids,
        schedule.get("planned_start_at"),
        schedule.get("planned_end_at"),
        session=session,
        fence_periods=session is not None,
    )
    async for active_run in skill_profile_repository.iter_active_runs_for_members(
        eligible_ids, session=session, exclude_run_id=exclude_run_id
    ):
        case_assignments = list((active_run.get("test_case_assignments") or {}).values())
        case_assignees = set(case_assignments)
        assigned = set(case_assignees)
        if active_run.get("assignee_id"):
            assigned.add(active_run["assignee_id"])
        for member_id in assigned:
            if member_id in case_load:
                run_load[member_id] += 1
        for member_id in case_assignments:
            if member_id in case_load:
                case_load[member_id] += 1

    existing_case_assignments = existing_case_assignments or {}
    existing_run_assignees = set(existing_case_assignments.values())
    if existing_assignee_id:
        existing_run_assignees.add(existing_assignee_id)
    for member_id in existing_run_assignees:
        if member_id in run_load:
            run_load[member_id] += 1
            project_workload[member_id].add(project_id)
    for member_id in existing_case_assignments.values():
        if member_id in case_load:
            case_load[member_id] += 1

    candidate_map = {}
    candidate_reason_by_version = {}
    for version in versions:
        required = {
            _normalized(skill)
            for skill in version.get("required_skills", [])
            if _normalized(skill)
        }
        candidates = []
        has_usable_skill = False
        has_available_profile = False
        has_skill_match = False
        has_capacity_eligible_profile = False
        for member_id in eligible_ids:
            profile = profiles_by_user.get(member_id)
            if not profile:
                continue
            usable_skills = set(_assignment_skills(profile))
            has_usable_skill = has_usable_skill or bool(usable_skills)
            availability = profile.get("availability")
            if availability == "UNAVAILABLE":
                continue
            if availability not in {"AVAILABLE", "LIMITED"}:
                continue
            has_available_profile = True
            if required and not required.issubset(usable_skills):
                continue
            has_skill_match = True
            limit = project_limits.get(member_id)
            if (
                limit is not None
                and project_id not in project_workload[member_id]
                and len(project_workload[member_id]) >= limit
            ):
                continue
            has_capacity_eligible_profile = True
            candidates.append(member_id)
        candidate_map[version["_id"]] = candidates
        candidate_reason_by_version[version["_id"]] = (
            "NO_ELIGIBLE_TESTER"
            if not eligible_ids
            else "PROFILE_NOT_CONFIRMED"
            if not has_usable_skill
            else "NO_AVAILABLE_TESTER"
            if not has_available_profile
            else "NO_FULL_SKILL_MATCH"
            if required and not has_skill_match
            else "MAX_CONCURRENT_PROJECTS_REACHED"
            if has_skill_match and not has_capacity_eligible_profile
            else "NO_ELIGIBLE_TESTER"
        )
    ordered = sorted(
        versions,
        key=lambda version: (
            len(candidate_map[version["_id"]]) or len(eligible_ids) + 1,
            -len(version.get("required_skills", [])),
            version["_id"],
        ),
    )
    assignments = {}
    decisions = {}
    unresolved = []
    assigned_run_members = set(existing_run_assignees)
    for version in ordered:
        candidates = candidate_map[version["_id"]]
        if not candidates:
            unresolved.append({
                "test_case_version_id": version["_id"],
                "reason": candidate_reason_by_version[version["_id"]],
            })
            continue
        assignee = min(
            candidates,
            key=lambda member_id: (
                _availability_rank(
                    profiles_by_user.get(member_id, {}).get("availability", "AVAILABLE")
                ),
                case_load[member_id],
                run_load[member_id],
                member_id,
            ),
        )
        profile = profiles_by_user.get(assignee, {})
        usable_skills = _assignment_skills(profile)
        required_names = [
            str(skill).strip()
            for skill in (version.get("required_skills") or [])
            if _normalized(skill)
        ]
        decisions[version["_id"]] = {
            "assignee_id": assignee,
            "required_skills": required_names,
            "matched_skills": [
                usable_skills[name].get("name")
                for name in dict.fromkeys(_normalized(skill) for skill in required_names)
                if name in usable_skills
            ],
            "matched_skill_evidence": [
                {
                    "name": usable_skills[name].get("name"),
                    "level": usable_skills[name].get("level", ""),
                    "source_kind": usable_skills[name].get("source_kind", "MEMBER_DECLARED"),
                    "confirmed": usable_skills[name].get("confirmed") is True,
                }
                for name in dict.fromkeys(_normalized(skill) for skill in required_names)
                if name in usable_skills
            ],
            "skill_profile_revision": profile.get("revision", 0),
            "availability_at_assignment": profile.get("availability", "PROFILE_NOT_SET"),
            "active_case_count_before_assignment": case_load[assignee],
            "active_run_count_before_assignment": run_load[assignee],
            "reason": (
                "SOURCE_EVIDENCE_THEN_AVAILABILITY_AND_LOWEST_ACTIVE_CASE_AND_RUN_LOAD"
                if required_names
                else "AVAILABILITY_AND_LOWEST_ACTIVE_CASE_AND_RUN_LOAD"
            ),
        }
        assignments[version["_id"]] = assignee
        case_load[assignee] += 1
        project_workload[assignee].add(project_id)
        if assignee not in assigned_run_members:
            assigned_run_members.add(assignee)
            run_load[assignee] += 1
    return assignments, unresolved, decisions


async def recommend_test_run_assignments(project_id, run_id, payload, user):
    run = await get_project_entity("test_runs", run_id, user, "testrun.assign")
    if run.get("project_id") != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    if (
        payload.expected_run_revision is not None
        and run.get("revision") != payload.expected_run_revision
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "TEST_RUN_CHANGED_RECOMMEND_AGAIN"},
        )
    plan_staffing = []
    plan_schedule = {}
    if run.get("test_plan_id"):
        plan = await database.value.test_plans.find_one(
            {"_id": run["test_plan_id"], "project_id": project_id}
        )
        if plan:
            plan_source = (plan.get("approved_snapshot") or plan) if plan.get("status") == "APPROVED" else plan
            plan_staffing = (plan_source.get("estimation") or {}).get("effort_allocations") or []
            plan_schedule = plan_source.get("schedule") or {}
    planned_tester_ids = {
        item.get("user_id") for item in plan_staffing if item.get("user_id")
    }
    memberships = await project_repository.list_members(project_id)
    eligible = [
        item for item in memberships
        if item.get("status") == "ACTIVE"
        and "TESTER" in roles_for_membership(item)
        and (not plan_staffing or item.get("user_id") in planned_tester_ids)
    ]
    eligible_ids = [item["user_id"] for item in eligible]
    profiles = await skill_profile_repository.list_for_members(project_id, eligible_ids)
    by_user = {item["user_id"]: item for item in profiles}
    workload = {member_id: 0 for member_id in eligible_ids}
    case_workload = {member_id: 0 for member_id in eligible_ids}
    project_workload = await _member_project_workload(eligible_ids, plan_schedule, exclude_run_id=run_id)
    capacity_status, project_limits = await _project_capacity_limits(
        eligible_ids,
        plan_schedule.get("planned_start_at"),
        plan_schedule.get("planned_end_at"),
    )
    async for active_run in skill_profile_repository.iter_active_runs_for_members(
        eligible_ids, exclude_run_id=run_id
    ):
        case_assignments = list((active_run.get("test_case_assignments") or {}).values())
        case_assignees = set(case_assignments)
        assigned = set()
        if active_run.get("assignee_id"):
            assigned.add(active_run["assignee_id"])
        assigned.update(case_assignees)
        for member_id in assigned:
            if member_id in workload:
                workload[member_id] += 1
        for member_id in case_assignments:
            if member_id in case_workload:
                case_workload[member_id] += 1
    identities = await load_user_identities(eligible_ids)
    required, candidates = rank_skill_candidates(
        eligible,
        profiles,
        workload,
        payload.required_skills,
        case_workloads=case_workload,
    )
    for candidate in candidates:
        member_id = candidate["user_id"]
        candidate["user_label"] = (identities.get(member_id) or {}).get("label") or member_id
        limit = project_limits.get(member_id)
        candidate["active_project_count"] = len(project_workload[member_id])
        candidate["max_concurrent_projects"] = limit
        candidate["project_limit_reached"] = bool(
            limit is not None
            and project_id not in project_workload[member_id]
            and len(project_workload[member_id]) >= limit
        )

    versions = await test_run_repository.list_versions(
        list(dict.fromkeys(run.get("test_case_version_ids", []))),
        len(run.get("test_case_version_ids", [])),
    )
    versions_by_id = {item["_id"]: item for item in versions}
    proposed_workload = dict(case_workload)
    proposed_projects = {member_id: set(projects) for member_id, projects in project_workload.items()}
    existing_assignments = run.get("test_case_assignments") or {}
    existing_run_members = set(existing_assignments.values())
    if run.get("assignee_id"):
        existing_run_members.add(run["assignee_id"])
    for member_id in existing_run_members:
        if member_id in workload:
            workload[member_id] += 1
            project_workload[member_id].add(project_id)
    case_recommendations_by_id = {}
    assignment_options = {}
    assignment_candidates = {}
    unresolved_cases = []
    for version_id in run.get("test_case_version_ids", []):
        version = versions_by_id.get(version_id)
        if not version or version.get("project_id") != project_id:
            unresolved_cases.append({"test_case_version_id": version_id, "reason": "VERSION_UNAVAILABLE"})
            continue
        if existing_assignments.get(version_id):
            case_recommendations_by_id[version_id] = {
                "test_case_version_id": version_id,
                "required_skills": version.get("required_skills", []),
                "assignee_id": existing_assignments[version_id],
                "status": "EXISTING_ASSIGNMENT_PRESERVED",
                "candidates": [],
                "near_matches": [],
            }
            continue
        case_required_by_key = {}
        for value in (version.get("required_skills") or payload.required_skills):
            key = _skill_key(value)
            if key:
                case_required_by_key.setdefault(key, str(value).strip())
        case_required = list(case_required_by_key.values())
        _, ranked = rank_skill_candidates(
            eligible,
            profiles,
            workload,
            case_required,
            case_workloads=proposed_workload,
        )
        for candidate in ranked:
            member_id = candidate["user_id"]
            limit = project_limits.get(member_id)
            candidate["active_project_count"] = len(proposed_projects[member_id])
            candidate["max_concurrent_projects"] = limit
            candidate["project_limit_reached"] = bool(
                limit is not None
                and project_id not in proposed_projects[member_id]
                and len(proposed_projects[member_id]) >= limit
            )
        near_matches = [
            candidate
            for candidate in ranked
            if candidate["profile_exists"]
            and candidate["availability"] in {"AVAILABLE", "LIMITED"}
            and not candidate["project_limit_reached"]
            and candidate["matched_skill_count"] < len(case_required)
        ]
        for candidate in near_matches:
            member_id = candidate["user_id"]
            candidate["user_label"] = (identities.get(member_id) or {}).get("label") or member_id
        skill_matches = [
            candidate
            for candidate in ranked
            if candidate["profile_exists"]
            and candidate["availability"] in {"AVAILABLE", "LIMITED"}
            and candidate["matched_skill_count"] == len(case_required)
        ]
        suitable = [
            candidate
            for candidate in skill_matches
            if not candidate["project_limit_reached"]
        ]
        for candidate in suitable:
            member_id = candidate["user_id"]
            candidate["user_label"] = (identities.get(member_id) or {}).get("label") or member_id
        case_candidate_options = {
            candidate["user_id"]: 0
            for candidate in suitable
        }
        if case_candidate_options:
            assignment_options[version_id] = case_candidate_options
            assignment_candidates[version_id] = suitable
        else:
            unresolved_reason = (
                "MAX_CONCURRENT_PROJECTS_REACHED"
                if skill_matches
                else "NO_FULL_SKILL_MATCH"
                if case_required
                else "NO_ELIGIBLE_TESTER"
            )
            case_recommendations_by_id[version_id] = {
                "test_case_version_id": version_id,
                "required_skills": case_required,
                "assignee_id": None,
                "status": unresolved_reason,
                "candidates": ranked,
                "near_matches": near_matches,
            }

    base_workloads = {
        member_id: case_workload.get(member_id, 0)
        for member_id in eligible_ids
    }
    optimized_assignments = _minimum_cost_case_assignment(
        list(assignment_options), assignment_options, base_workloads
    )
    for version_id, candidate_options in assignment_candidates.items():
        chosen_id = optimized_assignments.get(version_id)
        candidates_for_case = candidate_options
        if chosen_id:
            chosen = next(item for item in candidates_for_case if item["user_id"] == chosen_id)
            proposed_workload[chosen_id] = proposed_workload.get(chosen_id, 0) + 1
            proposed_projects[chosen_id].add(project_id)
            case_recommendations_by_id[version_id] = {
                "test_case_version_id": version_id,
                "required_skills": chosen["matched_required_skills"],
                "assignee_id": chosen_id,
                "assignee_label": chosen["user_label"],
                "matched_skill_evidence": chosen["matched_skill_evidence"],
                "status": "PROPOSED",
                "assignment_method": "GLOBAL_MIN_COST_SKILL_AND_WORKLOAD_OPTIMIZATION",
                "candidates": candidates_for_case,
                "near_matches": near_matches,
            }
        else:
            case_recommendations_by_id[version_id] = {
                "test_case_version_id": version_id,
                "required_skills": [],
                "assignee_id": None,
                "status": "NO_ELIGIBLE_TESTER",
                "candidates": candidates_for_case,
                "near_matches": near_matches,
            }
    case_recommendations = [
        case_recommendations_by_id[version_id]
        for version_id in run.get("test_case_version_ids", [])
        if version_id in case_recommendations_by_id
    ]
    return {
        "test_run_id": run_id,
        "run_revision": run.get("revision", 1),
        "skill_profile_revisions": {
            member_id: by_user.get(member_id, {}).get("revision", 0)
            for member_id in eligible_ids
        },
        "required_skills": required,
        "recommendations": candidates,
        "status": (
            "CANDIDATES_FOUND"
            if any(not item["project_limit_reached"] for item in candidates)
            else "PROJECT_LIMIT_REACHED"
            if candidates
            else "NO_MATCHING_SKILL_EVIDENCE"
        ),
        "method": "GLOBAL_ASSIGNMENT_OPTIMIZATION_WITH_SOURCE_EVIDENCE_AND_ACTIVE_LOAD",
        "active_project_count_basis": "OPEN_TEST_RUNS_OR_OVERLAPPING_REVIEWED_TEST_PLANS",
        "project_capacity_status": capacity_status,
        "staffing_source": "TEST_PLAN_EFFORT_ALLOCATION" if plan_staffing else "ACTIVE_PROJECT_TESTERS",
        "test_plan_staffing": plan_staffing,
        "applies_automatically": False,
        "case_recommendations": case_recommendations,
        "unresolved_cases": unresolved_cases,
        "assignment_plan_status": (
            "READY" if not unresolved_cases and all(item["status"] not in {"NO_FULL_SKILL_MATCH", "NO_ELIGIBLE_TESTER", "MAX_CONCURRENT_PROJECTS_REACHED"} for item in case_recommendations)
            else "PARTIAL"
        ),
    }


async def recommend_test_case_owner(project_id, payload, user, *, output_language=None):
    if payload.draft_id:
        draft = await get_project_entity(
            "test_case_drafts", payload.draft_id, user, "testcase.update"
        )
        if draft.get("project_id") != project_id:
            raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
        if draft.get("status") != "DRAFT":
            raise HTTPException(status_code=409, detail={"code": "IMMUTABLE_TEST_CASE_DRAFT"})
    else:
        await get_project(project_id, user, "testcase.create")
    await get_project(project_id, user, "project.members.read")

    project = await database.value.projects.find_one(
        {"_id": project_id}, {"locale": 1}
    )
    output_language = output_language or (project or {}).get("locale")
    if not output_language:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_OUTPUT_LOCALE_REQUIRED"})

    memberships = await project_repository.list_members(project_id)
    eligible = [
        item
        for item in memberships
        if item.get("status") == "ACTIVE" and roles_for_membership(item).intersection({"QA", "TESTER"})
    ]
    eligible_ids = [item["user_id"] for item in eligible]
    profiles = await skill_profile_repository.list_for_members(project_id, eligible_ids)
    profiles_by_user = {item["user_id"]: item for item in profiles}
    case_workload = {member_id: 0 for member_id in eligible_ids}
    run_workload = {member_id: 0 for member_id in eligible_ids}
    staffing_schedule = {
        "planned_start_at": now().date().isoformat(),
        "planned_end_at": now().date().isoformat(),
    }
    project_workload = await _member_project_workload(eligible_ids, staffing_schedule)
    project_capacity_status, project_limits = await _project_capacity_limits(
        eligible_ids,
        staffing_schedule["planned_start_at"],
        staffing_schedule["planned_end_at"],
    )
    if eligible_ids:
        async for active_run in skill_profile_repository.iter_active_runs_for_members(eligible_ids):
            assigned_cases = list((active_run.get("test_case_assignments") or {}).values())
            assigned_members = set(assigned_cases)
            if active_run.get("assignee_id"):
                assigned_members.add(active_run["assignee_id"])
            for member_id in assigned_members:
                if member_id in run_workload:
                    run_workload[member_id] += 1
            for member_id in assigned_cases:
                if member_id in case_workload:
                    case_workload[member_id] += 1

    required, ranked = rank_skill_candidates(
        eligible,
        profiles,
        run_workload,
        payload.required_skills,
        case_workloads=case_workload,
    )
    identities = await load_user_identities(eligible_ids)
    recommendation_pool = []
    excluded_by_project_limit = 0
    for candidate in ranked:
        member_id = candidate["user_id"]
        profile = profiles_by_user.get(member_id)
        if not profile or profile.get("availability") not in {"AVAILABLE", "LIMITED"}:
            continue
        project_limit = project_limits.get(member_id)
        if (
            project_limit is not None
            and project_id not in project_workload[member_id]
            and len(project_workload[member_id]) >= project_limit
        ):
            excluded_by_project_limit += 1
            continue
        recommendation_pool.append(
            {
                **candidate,
                "user_label": (identities.get(member_id) or {}).get("label") or member_id,
                "skill_profile_revision": profile.get("revision", 0),
                "active_project_count": len(project_workload[member_id]),
                "max_concurrent_projects": project_limit,
                "project_limit_reached": False,
            }
        )
    recommendation_pool.sort(key=lambda item: item["user_id"])

    candidates_by_user = {item["user_id"]: item for item in recommendation_pool}
    if not candidates_by_user:
        return {
            "project_id": project_id,
            "draft_id": payload.draft_id,
            "required_skills": required,
            "candidates": [],
            "near_matches": [],
            "recommended_user_id": None,
            "recommended_user_label": None,
            "status": "PROJECT_LIMIT_REACHED" if excluded_by_project_limit else "NO_ELIGIBLE_TESTER",
            "method": "AI_RANKED_ELIGIBLE_CANDIDATES_WITH_SKILL_GAP_ANALYSIS",
            "active_project_count_basis": "OPEN_TEST_RUNS_OR_OVERLAPPING_REVIEWED_TEST_PLANS",
            "project_capacity_status": project_capacity_status,
            "excluded_by_project_limit_count": excluded_by_project_limit,
            "recommendation_engine": "AI",
            "applies_automatically": False,
        }
    candidate_ref_to_user = _opaque_staffing_candidate_refs(
        list(candidates_by_user)
    )
    candidate_ref_by_user = {
        user_id: candidate_ref
        for candidate_ref, user_id in candidate_ref_to_user.items()
    }
    ai_candidate_inputs = []
    facts_by_user = {}
    skill_evidence_by_user = {}
    for candidate in recommendation_pool:
        member_id = candidate["user_id"]
        profile = profiles_by_user.get(member_id) or {}
        facts = []
        skill_evidence_by_user[member_id] = {}
        confirmed_skills = list(_confirmed_skills(profile).values())
        required_keys = {_skill_key(value) for value in required}
        for index, skill in enumerate(confirmed_skills):
            match_state = (
                "Tên kỹ năng khớp yêu cầu"
                if _skill_key(skill.get("name")) in required_keys
                else "Tên kỹ năng chưa khớp trực tiếp yêu cầu"
            )
            skill_description = f"Kỹ năng trong hồ sơ: {skill['name']}"
            if skill.get("level"):
                skill_description = f"{skill_description} ({skill['level']})"
            facts.append({
                "fact_id": f"skill-{index + 1}",
                "description": f"{skill_description}; nguồn {skill.get('source_kind', 'MEMBER_DECLARED')}; người dùng đã xác nhận trong hồ sơ; chưa có xác minh độc lập; {match_state}",
            })
            skill_evidence_by_user[member_id][f"skill-{index + 1}"] = {
                "name": skill["name"],
                "level": skill.get("level", ""),
                "source_kind": skill.get("source_kind", "MEMBER_DECLARED"),
                "evidence_status": (
                    "DOCUMENT_SUPPORTED"
                    if skill.get("source_kind") == "CV_EXTRACTED" and str(skill.get("evidence") or "").strip()
                    else "DECLARED"
                ),
                "independently_assessed": False,
                "confirmed": skill.get("confirmed") is True,
            }
        for index, experience in enumerate(profile.get("experiences") or []):
            if experience.get("confirmed") is not True:
                continue
            description = ", ".join(
                value for value in (
                    experience.get("title"),
                    experience.get("domain"),
                    ", ".join(experience.get("technologies") or []),
                    experience.get("period"),
                ) if value
            )
            if description:
                facts.append({
                    "fact_id": f"experience-{index + 1}",
                    "description": f"Kinh nghiệm đã xác nhận: {description[:240]}",
                })
        for fact_id, description in (
            ("availability", f"Khả dụng: {candidate['availability']}"),
            (
                "active-projects",
                f"Dự án có Test Run mở hoặc Test Plan được duyệt trùng lịch: {len(project_workload[member_id])}",
            ),
            ("active-cases", f"Số ca đang được giao: {candidate['active_case_count']}"),
            ("active-runs", f"Số đợt chạy đang tham gia: {candidate['active_run_count']}"),
        ):
            facts.append({"fact_id": fact_id, "description": description})
        facts_by_user[member_id] = facts
        ai_candidate_inputs.append({
            "candidate_id": candidate_ref_by_user[member_id],
            "confirmed_skills": candidate["confirmed_skills"],
            "relevant_experience": [
                fact["description"] for fact in facts if fact["fact_id"].startswith("experience-")
            ],
            "evidence_facts": facts,
            "availability": candidate["availability"],
            "active_project_count": len(project_workload[member_id]),
            "active_case_count": candidate["active_case_count"],
            "active_run_count": candidate["active_run_count"],
        })
    ai_result = await ai_automation_client.recommend_test_case_owners(
        project_id, output_language, required, ai_candidate_inputs
    ) if ai_candidate_inputs else {"recommendations": [], "warnings": []}
    recommendation_by_user = _map_staffing_recommendations(
        ai_result.get("recommendations") or [], candidate_ref_to_user
    )

    ai_rank_by_user = {
        candidate_ref_to_user[item["candidate_id"]]: rank
        for rank, item in enumerate(ai_result.get("recommendations") or [], start=1)
    }
    exact_required_by_key = {_skill_key(value): value for value in required}
    for member_id, candidate in candidates_by_user.items():
        recommendation = recommendation_by_user[member_id]
        validated_skill_matches = []
        matched_keys = set()
        evidence_keys = set()
        for match in recommendation.get("skill_matches") or []:
            required_skill = str(match.get("required_skill") or "").strip()
            required_key = _skill_key(required_skill)
            evidence_id = match.get("evidence_fact_id")
            evidence = skill_evidence_by_user[member_id].get(evidence_id)
            match_type = match.get("match_type")
            if (
                required_key not in exact_required_by_key
                or required_key in matched_keys
                or not evidence
                or evidence_id in evidence_keys
                or match_type not in {"EXACT", "EQUIVALENT"}
                or (match_type == "EXACT" and _skill_key(evidence["name"]) != required_key)
                or (match_type == "EQUIVALENT" and _skill_key(evidence["name"]) == required_key)
            ):
                raise HTTPException(
                    status_code=502,
                    detail={"code": "AI_OWNER_SKILL_MATCH_EVIDENCE_INVALID"},
                )
            matched_keys.add(required_key)
            evidence_keys.add(evidence_id)
            validated_skill_matches.append({
                "required_skill": exact_required_by_key[required_key],
                "confirmed_skill": evidence["name"],
                "evidence_fact_id": evidence_id,
                "match_type": match_type,
                "rationale": match.get("rationale", ""),
            })
        unmatched = [
            exact_required_by_key[key]
            for key in exact_required_by_key
            if key not in matched_keys
        ]
        model_unmatched = recommendation.get("unmatched_required_skills") or []
        if (
            len({_skill_key(value) for value in model_unmatched}) != len(model_unmatched)
            or {_skill_key(value) for value in model_unmatched}
            != {_skill_key(value) for value in unmatched}
        ):
            raise HTTPException(
                status_code=502,
                detail={"code": "AI_OWNER_SKILL_GAP_ANALYSIS_INVALID"},
            )
        candidate["exact_skill_matches"] = candidate["matched_skill_evidence"]
        candidate["semantic_skill_matches"] = [
            item for item in validated_skill_matches if item["match_type"] == "EQUIVALENT"
        ]
        candidate["matched_skill_evidence"] = [
            {
                **skill_evidence_by_user[member_id][item["evidence_fact_id"]],
                "required_skill": item["required_skill"],
                "match_type": item["match_type"],
            }
            for item in validated_skill_matches
        ]
        candidate["matched_skills"] = list(dict.fromkeys(
            item["confirmed_skill"] for item in validated_skill_matches
        ))
        candidate["matched_required_skills"] = [item["required_skill"] for item in validated_skill_matches]
        candidate["unmatched_skills"] = unmatched
        candidate["unmatched_required_skills"] = unmatched
        candidate["ai_rank"] = ai_rank_by_user[member_id]
        candidate["ai_reason"] = recommendation["reason"]
        candidate["ai_supporting_facts"] = [
            next(fact["description"] for fact in facts_by_user[member_id] if fact["fact_id"] == fact_id)
            for fact_id in recommendation["supporting_facts"]
        ]
    decision_context = _owner_decision_context(candidates_by_user, profiles_by_user, project_workload)
    for member_id, candidate in candidates_by_user.items():
        candidate["decision_context"] = decision_context[member_id]["context"]
        candidate["decision_context_status"] = decision_context[member_id]["context_status"]
    candidates = sorted(
        (item for item in candidates_by_user.values() if not item["unmatched_skills"]),
        key=lambda item: (item["ai_rank"], item["user_id"]),
    )
    near_matches = sorted(
        (item for item in candidates_by_user.values() if item["unmatched_skills"]),
        key=lambda item: (
            len(item["unmatched_skills"]),
            item["ai_rank"],
            item["user_id"],
        ),
    )
    for rank, candidate in enumerate(candidates, start=1):
        candidate["recommendation_rank"] = rank
    for candidate in [*candidates, *near_matches]:
        candidate["matched_skill_count"] = len(candidate["matched_required_skills"])
        candidate["required_skill_count"] = len(required)
        candidate["skill_coverage"] = (
            len(candidate["matched_required_skills"]) / len(required)
            if required else 1.0
        )

    status = (
        "CANDIDATES_FOUND"
        if candidates
        else "NO_ELIGIBLE_TESTER"
        if not eligible
        else "PROJECT_LIMIT_REACHED"
        if excluded_by_project_limit and not candidates
        else "NEAR_MATCHES_FOUND"
        if near_matches and not candidates
        else "NO_CONFIRMED_SKILL_MATCH"
    )
    return {
        "project_id": project_id,
        "draft_id": payload.draft_id,
        "required_skills": required,
        "candidates": candidates,
        "near_matches": near_matches,
        "recommended_user_id": candidates[0]["user_id"] if candidates else None,
        "recommended_user_label": candidates[0]["user_label"] if candidates else None,
        "status": status,
        "method": "AI_RANKED_ELIGIBLE_CANDIDATES_WITH_SKILL_GAP_ANALYSIS",
        "active_project_count_basis": "OPEN_TEST_RUNS_OR_OVERLAPPING_REVIEWED_TEST_PLANS",
        "project_capacity_status": project_capacity_status,
        "excluded_by_project_limit_count": excluded_by_project_limit,
        "recommendation_engine": "AI",
        "recommendation_warnings": ai_result.get("warnings") or [],
        "applies_automatically": False,
    }
