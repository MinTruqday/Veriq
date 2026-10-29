import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from itertools import chain

from fastapi import HTTPException, UploadFile
from pymongo.errors import DuplicateKeyError

from src.core.auth import roles_for_membership
from src.core.common import audit, get_project, get_project_entity, load_user_identities, now
from src.core.database import database
from src.repositories.project import project_repository
from src.repositories.skill_profile import skill_profile_repository
from src.repositories.test_run import test_run_repository
from src.clients.ai_automation import ai_automation_client
from src.clients.document_conversion import convert_requirement_source
from src.core.configuration import settings


CV_SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".txt"})
CV_MAX_EXTRACTED_CHARACTERS = 100_000
CV_MAX_SOURCE_BLOCKS = 500
CV_SOURCE_BLOCK_CHARACTERS = 3_000


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
            "level": "NOT_ASSESSED",
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
        extracted = await ai_automation_client.extract_skill_profile(project_id, source_blocks)
    except Exception as error:
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


def _availability_rank(value):
    return {"AVAILABLE": 0, "LIMITED": 1}.get(value, 2)


def _owner_score_factors(candidates, profiles, payroll_costs, currency):
    member_ids = list(candidates)
    max_workload = max(
        (candidates[member_id]["active_case_count"] + candidates[member_id]["active_run_count"] for member_id in member_ids),
        default=0,
    )
    has_experience_data = all(
        any(item.get("confirmed") is True for item in (profiles.get(member_id) or {}).get("experiences", []))
        for member_id in member_ids
    )
    has_comparable_payroll = bool(currency) and all(member_id in payroll_costs for member_id in member_ids)
    payroll_values = [payroll_costs[member_id] for member_id in member_ids] if has_comparable_payroll else []
    lowest_rate = min(payroll_values) if payroll_values else None
    highest_rate = max(payroll_values) if payroll_values else None
    results = {}
    for member_id in member_ids:
        candidate = candidates[member_id]
        profile = profiles.get(member_id) or {}
        levels = {
            "BEGINNER": 1 / 3,
            "INTERMEDIATE": 2 / 3,
            "ADVANCED": 1.0,
        }
        skill_values = [
            levels[skill["level"]]
            for skill in candidate["matched_skill_evidence"]
            if skill.get("level") in levels
        ]
        factors = {
            "skill_level": round(sum(skill_values) / len(skill_values), 3) if skill_values else 0.5,
            "availability": 1.0 if candidate["availability"] == "AVAILABLE" else 0.5,
            "workload": (
                round(1 - (candidate["active_case_count"] + candidate["active_run_count"]) / max_workload, 3)
                if max_workload else 1.0
            ),
        }
        if has_experience_data:
            experiences = [
                item for item in profile.get("experiences", [])
                if item.get("confirmed") is True
            ]
            experience_text = " ".join(
                str(value or "")
                for item in experiences
                for value in (
                    item.get("title"), item.get("domain"), item.get("responsibilities"),
                    *(item.get("technologies") or []),
                )
            )
            factors["experience_relevance"] = round(
                sum(1 for skill in candidate["matched_skills"] if _normalized(skill) in _normalized(experience_text))
                / max(len(candidate["matched_skills"]), 1),
                3,
            )
        if has_comparable_payroll:
            spread = highest_rate - lowest_rate
            factors["payroll_cost"] = (
                round(float((highest_rate - payroll_costs[member_id]) / spread), 3)
                if spread else 1.0
            )
        results[member_id] = {
            "factors": factors,
            "factor_status": {
                "skill_level": "ASSESSED" if skill_values else "NOT_ASSESSED_NEUTRAL",
                "experience_relevance": "ASSESSED" if has_experience_data else "MISSING_FOR_COMPARISON",
                "payroll_cost": "ASSESSED" if has_comparable_payroll else "MISSING_OR_INCOMPARABLE",
            },
            "score": round(sum(factors.values()) / len(factors), 3),
        }
    return results


def _confirmed_skills(profile):
    confirmed = {}
    for skill in profile.get("skills", []):
        if skill.get("confirmed") is not True:
            continue
        key = _normalized(skill.get("name"))
        if key:
            confirmed.setdefault(key, skill)
    return confirmed


def _assignment_skills(profile):
    return _confirmed_skills(profile)


def rank_skill_candidates(
    memberships, profiles, workloads, required_skills, *, case_workloads=None
):
    required = list(
        dict.fromkeys(_normalized(value) for value in required_skills if _normalized(value))
    )
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
        matched = [skill for skill in required if skill in usable]
        if required and not matched:
            continue
        candidates.append(
            {
                "user_id": member_id,
                "matched_skills": [usable[key].get("name") for key in matched],
                "matched_skill_evidence": [
                    {
                        "name": usable[key].get("name"),
                        "level": usable[key].get("level", "NOT_ASSESSED"),
                        "source_kind": usable[key].get("source_kind", "MEMBER_DECLARED"),
                        "confirmed": usable[key].get("confirmed") is True,
                    }
                    for key in matched
                ],
                "unmatched_skills": [item for item in required if item not in usable],
                "availability": profile.get("availability", "PROFILE_NOT_SET"),
                "active_run_count": workloads.get(member_id, 0),
                "active_case_count": case_workloads.get(member_id, 0),
                "profile_exists": bool(profile),
                "score": len(matched),
            }
        )
    candidates.sort(
        key=lambda item: (
            -item["score"],
            _availability_rank(item["availability"]),
            item["active_case_count"],
            item["active_run_count"],
            item["user_id"],
        )
    )
    return required, candidates


async def automatically_assign_test_cases(
    project_id,
    versions,
    session=None,
    existing_case_assignments=None,
    existing_assignee_id=None,
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
    async for active_run in skill_profile_repository.iter_active_runs_for_members(
        eligible_ids, session=session
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
            if required and not candidates
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
                    "level": usable_skills[name].get("level", "NOT_ASSESSED"),
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
    if run.get("test_plan_id"):
        plan = await database.value.test_plans.find_one(
            {"_id": run["test_plan_id"], "project_id": project_id}
        )
        if plan:
            plan_source = (plan.get("approved_snapshot") or plan) if plan.get("status") == "APPROVED" else plan
            plan_staffing = (plan_source.get("estimation") or {}).get("effort_allocations") or []
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
    async for active_run in skill_profile_repository.iter_active_runs_for_members(
        eligible_ids
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

    versions = await test_run_repository.list_versions(
        list(dict.fromkeys(run.get("test_case_version_ids", []))),
        len(run.get("test_case_version_ids", [])),
    )
    versions_by_id = {item["_id"]: item for item in versions}
    proposed_workload = dict(case_workload)
    existing_assignments = run.get("test_case_assignments") or {}
    case_recommendations = []
    unresolved_cases = []
    for version_id in run.get("test_case_version_ids", []):
        version = versions_by_id.get(version_id)
        if not version or version.get("project_id") != project_id:
            unresolved_cases.append({"test_case_version_id": version_id, "reason": "VERSION_UNAVAILABLE"})
            continue
        if existing_assignments.get(version_id):
            case_recommendations.append({
                "test_case_version_id": version_id,
                "required_skills": version.get("required_skills", []),
                "assignee_id": existing_assignments[version_id],
                "status": "EXISTING_ASSIGNMENT_PRESERVED",
                "candidates": [],
            })
            continue
        case_required = list(dict.fromkeys(
            _normalized(value)
            for value in (version.get("required_skills") or payload.required_skills)
            if _normalized(value)
        ))
        _, ranked = rank_skill_candidates(
            eligible,
            profiles,
            workload,
            case_required,
            case_workloads=proposed_workload,
        )
        suitable = [
            candidate
            for candidate in ranked
            if candidate["profile_exists"]
            and candidate["availability"] in {"AVAILABLE", "LIMITED"}
            and not candidate["unmatched_skills"]
        ]
        for candidate in suitable:
            member_id = candidate["user_id"]
            candidate["user_label"] = (identities.get(member_id) or {}).get("label") or member_id
        if suitable:
            chosen = suitable[0]
            proposed_workload[chosen["user_id"]] = proposed_workload.get(chosen["user_id"], 0) + 1
            case_recommendations.append({
                "test_case_version_id": version_id,
                "required_skills": case_required,
                "assignee_id": chosen["user_id"],
                "assignee_label": chosen["user_label"],
                "matched_skill_evidence": chosen["matched_skill_evidence"],
                "status": "PROPOSED",
                "candidates": suitable,
            })
        else:
            case_recommendations.append({
                "test_case_version_id": version_id,
                "required_skills": case_required,
                "assignee_id": None,
                "status": "NO_FULL_SKILL_MATCH" if case_required else "NO_ELIGIBLE_TESTER",
                "candidates": ranked,
            })
    return {
        "test_run_id": run_id,
        "run_revision": run.get("revision", 1),
        "skill_profile_revisions": {
            member_id: by_user.get(member_id, {}).get("revision", 0)
            for member_id in eligible_ids
        },
        "required_skills": required,
        "recommendations": candidates,
        "status": "CANDIDATES_FOUND" if candidates else "NO_MATCHING_SKILL_EVIDENCE",
        "method": "SOURCE_EVIDENCE_AVAILABILITY_AND_ACTIVE_CASE_AND_RUN_LOAD",
        "staffing_source": "TEST_PLAN_EFFORT_ALLOCATION" if plan_staffing else "ACTIVE_PROJECT_TESTERS",
        "test_plan_staffing": plan_staffing,
        "applies_automatically": False,
        "case_recommendations": case_recommendations,
        "unresolved_cases": unresolved_cases,
        "assignment_plan_status": (
            "READY" if not unresolved_cases and all(item["status"] != "NO_FULL_SKILL_MATCH" and item["status"] != "NO_ELIGIBLE_TESTER" for item in case_recommendations)
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
        {"_id": project_id}, {"commercial_terms": 1, "locale": 1}
    )
    commercial_terms = (project or {}).get("commercial_terms") or {}
    output_language = output_language or (project or {}).get("locale")
    if not output_language:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_OUTPUT_LOCALE_REQUIRED"})
    currency = commercial_terms.get("currency")
    effective_date = datetime.now(timezone.utc).date().isoformat() if currency else None

    memberships = await project_repository.list_members(project_id)
    eligible = [
        item
        for item in memberships
        if item.get("status") == "ACTIVE" and "TESTER" in roles_for_membership(item)
    ]
    eligible_ids = [item["user_id"] for item in eligible]
    profiles = await skill_profile_repository.list_for_members(project_id, eligible_ids)
    profiles_by_user = {item["user_id"]: item for item in profiles}
    case_workload = {member_id: 0 for member_id in eligible_ids}
    run_workload = {member_id: 0 for member_id in eligible_ids}
    project_workload = {member_id: set() for member_id in eligible_ids}
    if eligible_ids:
        async for active_run in skill_profile_repository.iter_active_runs_for_members(eligible_ids):
            assigned_cases = list((active_run.get("test_case_assignments") or {}).values())
            assigned_members = set(assigned_cases)
            if active_run.get("assignee_id"):
                assigned_members.add(active_run["assignee_id"])
            for member_id in assigned_members:
                if member_id in run_workload:
                    run_workload[member_id] += 1
                    if active_run.get("project_id"):
                        project_workload[member_id].add(active_run["project_id"])
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
    payroll_costs = {}
    if eligible_ids and currency and effective_date:
        active_rates = await database.value.payroll_rates.find(
            {
                "user_id": {"$in": eligible_ids},
                "currency": currency,
                "valid_from": {"$lte": effective_date},
                "$or": [
                    {"valid_until": None},
                    {"valid_until": {"$gte": effective_date}},
                ],
            },
            {"user_id": 1, "hourly_cost": 1, "valid_from": 1},
        ).sort([("user_id", 1), ("valid_from", -1)]).to_list(10000)
        for rate in active_rates:
            payroll_costs.setdefault(
                rate["user_id"], Decimal(str(rate["hourly_cost"]))
            )

    qualified_candidates = []
    for candidate in ranked:
        member_id = candidate["user_id"]
        profile = profiles_by_user.get(member_id)
        if not profile or profile.get("availability") not in {"AVAILABLE", "LIMITED"}:
            continue
        if candidate["unmatched_skills"]:
            continue
        qualified_candidates.append(
            {
                **candidate,
                "user_label": (identities.get(member_id) or {}).get("label") or member_id,
                "skill_profile_revision": profile.get("revision", 0),
                "active_project_count": len(project_workload[member_id]),
            }
        )
    candidates = [
        {
            **candidate,
            "payroll_rate_available": candidate["user_id"] in payroll_costs,
        }
        for candidate in qualified_candidates
    ]
    candidates.sort(
        key=lambda item: (
            -item["score"],
            _availability_rank(item["availability"]),
            item["active_project_count"],
            item["active_case_count"],
            payroll_costs.get(item["user_id"], Decimal("Infinity")),
            item["active_run_count"],
            item["user_id"],
        )
    )

    candidates_by_user = {item["user_id"]: item for item in candidates}
    score_factors = _owner_score_factors(candidates_by_user, profiles_by_user, payroll_costs, currency)
    ai_candidate_inputs = []
    facts_by_user = {}
    for candidate in candidates:
        member_id = candidate["user_id"]
        profile = profiles_by_user.get(member_id) or {}
        facts = []
        for index, skill in enumerate(candidate["matched_skill_evidence"]):
            facts.append({
                "fact_id": f"skill-{index + 1}",
                "description": f"Kỹ năng đã xác nhận: {skill['name']} ({skill.get('level', 'NOT_ASSESSED')})",
            })
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
            ("active-projects", f"Số dự án đang tham gia: {len(project_workload[member_id])}"),
            ("active-cases", f"Số ca đang được giao: {candidate['active_case_count']}"),
            ("active-runs", f"Số đợt chạy đang tham gia: {candidate['active_run_count']}"),
        ):
            facts.append({"fact_id": fact_id, "description": description})
        payroll_factor = score_factors[member_id]["factors"].get("payroll_cost")
        if payroll_factor is not None:
            facts.append({
                "fact_id": "payroll-comparison",
                "description": f"Hệ số chi phí tương đối đã chuẩn hóa: {payroll_factor}",
            })
        facts_by_user[member_id] = facts
        ai_candidate_inputs.append({
            "candidate_id": member_id,
            "confirmed_skills": candidate["matched_skills"],
            "relevant_experience": [
                fact["description"] for fact in facts if fact["fact_id"].startswith("experience-")
            ],
            "evidence_facts": facts,
            "availability": candidate["availability"],
            "active_project_count": len(project_workload[member_id]),
            "active_case_count": candidate["active_case_count"],
            "active_run_count": candidate["active_run_count"],
            "payroll_cost_factor": (
                score_factors[member_id]["factors"].get("payroll_cost")
            ),
        })
    ai_result = await ai_automation_client.recommend_test_case_owners(
        project_id, output_language, required, ai_candidate_inputs
    ) if ai_candidate_inputs else {"recommendations": [], "warnings": []}
    recommendation_by_user = {
        item["candidate_id"]: item for item in ai_result.get("recommendations") or []
    }
    if set(recommendation_by_user) != set(candidates_by_user):
        raise HTTPException(status_code=502, detail={"code": "AI_OWNER_RECOMMENDATION_CANDIDATES_INVALID"})

    ai_rank_by_user = {
        item["candidate_id"]: rank
        for rank, item in enumerate(ai_result.get("recommendations") or [], start=1)
    }
    for member_id, candidate in candidates_by_user.items():
        recommendation = recommendation_by_user[member_id]
        candidate["ai_rank"] = ai_rank_by_user[member_id]
        candidate["ai_reason"] = recommendation["reason"]
        candidate["ai_supporting_facts"] = [
            next(fact["description"] for fact in facts_by_user[member_id] if fact["fact_id"] == fact_id)
            for fact_id in recommendation["supporting_facts"]
        ]
        candidate["score_0_to_1"] = score_factors[member_id]["score"]
        candidate["score_factors"] = score_factors[member_id]["factors"]
        candidate["score_factor_status"] = score_factors[member_id]["factor_status"]
    candidates = sorted(
        candidates_by_user.values(),
        key=lambda item: (-item["score_0_to_1"], item["ai_rank"], item["user_id"]),
    )

    status = (
        "CANDIDATES_FOUND"
        if candidates
        else "NO_ELIGIBLE_TESTER"
        if not eligible
        else "NO_CONFIRMED_SKILL_MATCH"
    )
    payroll_data_status = (
        "MISSING_PROJECT_CURRENCY"
        if not currency
        else "COMPLETE"
        if all(item["user_id"] in payroll_costs for item in qualified_candidates)
        else "PARTIAL"
        if payroll_costs
        else "MISSING_RATES"
    )
    return {
        "project_id": project_id,
        "draft_id": payload.draft_id,
        "required_skills": required,
        "candidates": candidates,
        "recommended_user_id": candidates[0]["user_id"] if candidates else None,
        "recommended_user_label": candidates[0]["user_label"] if candidates else None,
        "status": status,
        "payroll_data_status": payroll_data_status,
        "currency": currency,
        "payroll_effective_date": effective_date,
        "method": "AI_RANKED_CONFIRMED_SKILLS_EXPERIENCE_AVAILABILITY_WORKLOAD_AND_PAYROLL",
        "recommendation_engine": "AI",
        "score_method": "EQUAL_WEIGHT_MEAN_OF_AVAILABLE_NORMALIZED_FACTORS",
        "score_note": "Điểm 0–1 là mức phù hợp tương đối trong nhóm ứng viên đủ điều kiện, không phải xác suất thành công.",
        "score_factors_considered": list(score_factors[candidates[0]["user_id"]]["factors"]) if candidates else [],
        "score_factors_excluded": [
            key for key in ("experience_relevance", "payroll_cost")
            if candidates and score_factors[candidates[0]["user_id"]]["factor_status"][key] in {
                "MISSING_FOR_COMPARISON", "MISSING_OR_INCOMPARABLE"
            }
        ],
        "recommendation_warnings": ai_result.get("warnings") or [],
        "applies_automatically": False,
    }
