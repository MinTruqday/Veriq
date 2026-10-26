import hashlib
import re
import unicodedata
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

    warnings = list(extracted.get("warnings") or [])
    if conversion.unprocessed_blocks:
        warnings.append("CV_HAS_UNPROCESSED_SOURCE_BLOCKS")
    if source_truncated:
        warnings.append("CV_EXTRACTION_INPUT_LIMIT_REACHED")
    return {
        "project_id": project_id,
        "skills": extracted.get("skills") or [],
        "experiences": extracted.get("experiences") or [],
        "warnings": list(dict.fromkeys(warnings)),
        "parser": conversion.parser,
        "parser_version": conversion.parser_version,
        "page_count": conversion.page_count,
        "source_block_count": len(source_blocks),
        "extracted_characters": extracted_characters,
        "source_sha256": source_sha256,
        "cv_persisted": False,
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
        confirmed = {
            _normalized(skill.get("name")): skill
            for skill in profile.get("skills", [])
            if skill.get("confirmed") is True
        }
        matched = [skill for skill in required if skill in confirmed]
        if required and not matched:
            continue
        candidates.append(
            {
                "user_id": member_id,
                "matched_skills": [confirmed[key].get("name") for key in matched],
                "matched_skill_evidence": [
                    {
                        "name": confirmed[key].get("name"),
                        "level": confirmed[key].get("level", "NOT_ASSESSED"),
                        "evidence": confirmed[key].get("evidence", ""),
                        "source_block_id": confirmed[key].get("source_block_id"),
                        "source_page_no": confirmed[key].get("source_page_no"),
                        "source_sha256": confirmed[key].get("source_sha256"),
                    }
                    for key in matched
                ],
                "unmatched_skills": [item for item in required if item not in confirmed],
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


async def automatically_assign_test_cases(project_id, versions, session=None):
    """Assign a new run's cases only when active Testers confirm every required skill."""
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
    async for active_run in skill_profile_repository.iter_active_runs(
        project_id, eligible_ids, session=session
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

    candidate_map = {}
    candidate_reason_by_version = {}
    for version in versions:
        required = {
            _normalized(skill)
            for skill in version.get("required_skills", [])
            if _normalized(skill)
        }
        candidates = []
        has_confirmed_profile = False
        has_available_profile = False
        for member_id in eligible_ids:
            profile = profiles_by_user.get(member_id)
            if not profile:
                continue
            has_confirmed_profile = True
            availability = profile.get("availability")
            if availability == "UNAVAILABLE":
                continue
            if availability not in {"AVAILABLE", "LIMITED"}:
                continue
            has_available_profile = True
            confirmed = {
                _normalized(skill.get("name"))
                for skill in profile.get("skills", [])
                if skill.get("confirmed") is True
            }
            if required and not required.issubset(confirmed):
                continue
            candidates.append(member_id)
        candidate_map[version["_id"]] = candidates
        candidate_reason_by_version[version["_id"]] = (
            "NO_ELIGIBLE_TESTER"
            if not eligible_ids
            else "PROFILE_NOT_CONFIRMED"
            if not has_confirmed_profile
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
    assigned_run_members = set()
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
        confirmed = {
            _normalized(skill.get("name")): skill
            for skill in profile.get("skills", [])
            if skill.get("confirmed") is True
        }
        required_names = [
            str(skill).strip()
            for skill in (version.get("required_skills") or [])
            if _normalized(skill)
        ]
        decisions[version["_id"]] = {
            "assignee_id": assignee,
            "required_skills": required_names,
            "matched_skills": [
                confirmed[name].get("name")
                for name in dict.fromkeys(_normalized(skill) for skill in required_names)
                if name in confirmed
            ],
            "matched_skill_evidence": [
                {
                    "name": confirmed[name].get("name"),
                    "level": confirmed[name].get("level", "NOT_ASSESSED"),
                    "evidence": confirmed[name].get("evidence", ""),
                    "source_block_id": confirmed[name].get("source_block_id"),
                    "source_page_no": confirmed[name].get("source_page_no"),
                    "source_sha256": confirmed[name].get("source_sha256"),
                }
                for name in dict.fromkeys(_normalized(skill) for skill in required_names)
                if name in confirmed
            ],
            "skill_profile_revision": profile.get("revision", 0),
            "availability_at_assignment": profile.get("availability", "PROFILE_NOT_SET"),
            "active_case_count_before_assignment": case_load[assignee],
            "active_run_count_before_assignment": run_load[assignee],
            "reason": (
                "CONFIRMED_SKILLS_THEN_AVAILABILITY_AND_LOWEST_ACTIVE_CASE_AND_RUN_LOAD"
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
    memberships = await project_repository.list_members(project_id)
    eligible = [
        item for item in memberships
        if item.get("status") == "ACTIVE" and "TESTER" in roles_for_membership(item)
    ]
    eligible_ids = [item["user_id"] for item in eligible]
    profiles = await skill_profile_repository.list_for_members(project_id, eligible_ids)
    by_user = {item["user_id"]: item for item in profiles}
    workload = {member_id: 0 for member_id in eligible_ids}
    case_workload = {member_id: 0 for member_id in eligible_ids}
    async for active_run in skill_profile_repository.iter_active_runs(
        project_id, eligible_ids
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
        "status": "CANDIDATES_FOUND" if candidates else "NO_MATCHING_CONFIRMED_SKILLS",
        "method": "CONFIRMED_SKILLS_AND_ACTIVE_CASE_AND_RUN_LOAD",
        "applies_automatically": False,
        "case_recommendations": case_recommendations,
        "unresolved_cases": unresolved_cases,
        "assignment_plan_status": (
            "READY" if not unresolved_cases and all(item["status"] != "NO_FULL_SKILL_MATCH" and item["status"] != "NO_ELIGIBLE_TESTER" for item in case_recommendations)
            else "PARTIAL"
        ),
    }
