import hashlib

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.ai_automation import request_ai_automation
from src.core.common import audit, get_project, get_project_entity, new_id, now, plain_text, validate_doc
from src.core.database import database
from src.schemas.contracts.requirements import RequirementCreate, RequirementExtractionInput, RequirementVersionCreate
from src.repositories.requirement_import import requirement_import_repository
from src.repositories.requirement import requirement_repository
from src.modules.requirements.services.requirement_import import atomic_requirement_candidates, source_document_text
from src.modules.requirements.services.requirement_documents import create_requirement_document_record, require_document_access
from src.modules.requirements.services.requirement_indexing import (
    index_requirement_version,
    validate_requirement_sources,
)
from src.modules.requirements.services.requirement_records import create_requirement_record, create_requirement_version_record
from src.modules.requirements.services.requirement_transformations import unique_source_refs
from src.repositories.analysis import analysis_repository
from src.clients.project_knowledge import (
    compare_project_text_semantics,
    search_project_with_status,
)
from src.modules.requirements.services.requirement_workflow import (
    candidate_fingerprint,
    prepare_requirement_candidates,
    text_doc,
)
from src.modules.design.services.linters import requirement_duplicate_score
from src.schemas.contracts.requirements import RequirementDuplicateCheckInput


def grounded_requirement_candidates(document, result_batches):
    text = source_document_text(document["normalized_content"])
    evidence = []
    for start in range(0, len(text), 3500):
        reference = f"{document['_id']}:{start}"
        evidence.append({
            "artifact_type": f"requirement_document:{document.get('source_type', 'REFERENCE')}",
            "artifact_id": reference,
            "text": text[start : start + 3500],
        })
    evidence_by_ref = {item["artifact_id"]: item["text"] for item in evidence}
    candidates = []
    conflicts = []
    for result in result_batches:
        conflicts.extend(result.get("conflicts", []))
        for suggestion in result.get("suggestions", []):
            references = suggestion.get("evidence_refs", [])
            if not references or any(reference not in evidence_by_ref for reference in references):
                raise HTTPException(status_code=502, detail={"code": "REQUIREMENT_EVIDENCE_INVALID"})
            source_refs = []
            verified_quotes = []
            for reference in references:
                chunk = evidence_by_ref[reference]
                quote = str((suggestion.get("source_quotes") or {}).get(reference) or "").strip()
                if not quote or quote not in chunk:
                    raise HTTPException(status_code=502, detail={"code": "REQUIREMENT_SOURCE_QUOTE_INVALID"})
                source_start = int(reference.rsplit(":", 1)[1])
                quote_start = chunk.find(quote)
                source_refs.append({
                    "requirement_document_id": document["_id"],
                    "content_hash": document["content_hash"],
                    "source_version": document.get("source_version"),
                    "source_start": source_start + quote_start,
                    "source_end": source_start + quote_start + len(quote),
                    "source_text_hash": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                    "source_quote": quote,
                    "format": document["format"],
                })
                verified_quotes.append(quote)
            cited_text = "\n".join(verified_quotes)
            key = suggestion.get("requirement_key")
            if key and not any(key in quote for quote in verified_quotes):
                raise HTTPException(status_code=502, detail={"code": "REQUIREMENT_KEY_UNGROUNDED"})
            def contains(value):
                return bool(value) and str(value).casefold() in cited_text.casefold()

            acceptance_criteria = [
                value for value in suggestion.get("acceptance_criteria", []) if contains(value)
            ]
            actors = [value for value in suggestion.get("actors", []) if contains(value)]
            business_rules = [
                value for value in suggestion.get("business_rules", []) if contains(value)
            ]
            dependencies = [
                value for value in suggestion.get("dependencies", []) if contains(value)
            ]
            details = {}
            for field in ("main_flow", "exception_flow", "data_rules", "integration", "quality_measure"):
                value = suggestion.get(field)
                if contains(value):
                    details[field] = value
            story = {
                field: suggestion.get(f"user_story_{field}")
                for field in ("actor", "goal", "value")
                if contains(suggestion.get(f"user_story_{field}"))
            }
            if story and document.get("source_type") == "USER_STORY":
                details["user_story"] = story
            missing = set(suggestion.get("missing_sections", []))
            missing.update(
                field for field, values in (
                    ("acceptance_criteria", acceptance_criteria),
                    ("actors", actors),
                    ("business_rules", business_rules),
                    ("dependencies", dependencies),
                )
                if suggestion.get(field) and not values
            )
            section_states = {field: "missing" for field in missing}
            section_states.update(
                {
                    field: "not_applicable"
                    for field in suggestion.get("not_applicable_sections", [])
                }
            )
            section_states.update(
                {
                    field: "provided"
                    for field, values in (
                        ("acceptance_criteria", acceptance_criteria),
                        ("actors", actors),
                        ("business_rules", business_rules),
                        ("dependencies", dependencies),
                    )
                    if values
                }
            )
            section_states.update({field: "provided" for field in details})
            candidate = {
                "requirement_key": key,
                "title": suggestion["title"],
                "type": suggestion["type"],
                "content_doc": text_doc(suggestion["content"]),
                "acceptance_criteria": [
                    {"key": f"AC-{index + 1}", "content_doc": text_doc(value)}
                    for index, value in enumerate(acceptance_criteria)
                ],
                "actors": actors,
                "business_rules": business_rules,
                "dependencies": dependencies,
                "details": details,
                "section_states": section_states,
                "source_refs": source_refs,
            }
            candidates.append(candidate)
    return candidates, conflicts


async def extract_grounded_requirement_candidates(document, project_id):
    text = source_document_text(document["normalized_content"])
    evidence = [
        {
            "artifact_type": f"requirement_document:{document.get('source_type', 'REFERENCE')}",
            "artifact_id": f"{document['_id']}:{start}",
            "source_version": document.get("source_version"),
            "authority": document.get("authority"),
            "text": text[start : start + 3500],
        }
        for start in range(0, len(text), 3500)
    ]
    if not evidence:
        return [], []
    if len(evidence) > 100:
        raise HTTPException(status_code=413, detail={"code": "REQUIREMENT_SOURCE_TOO_LARGE"})
    results = []
    for start in range(0, len(evidence), 8):
        result = await request_ai_automation(
            "requirement_template_synthesis",
            project_id,
            "Extract complete source-grounded Requirement records. Preserve source identifiers exactly.",
            evidence[start : start + 8],
        )
        if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
            raise HTTPException(status_code=503, detail={"code": "REQUIREMENT_EXTRACTION_UNAVAILABLE", "warnings": result.get("warnings", [])})
        results.append(result)
    return grounded_requirement_candidates(document, results)


def requirement_import_match_score(lexical_score, semantic_score, threshold):
    lexical = max(0.0, float(lexical_score or 0.0))
    if semantic_score is None:
        return lexical
    semantic = max(0.0, float(semantic_score))
    combined = (lexical * semantic) ** 0.5
    if semantic >= threshold:
        return max(combined, semantic)
    return combined


async def authorize_requirement_import_job(job, user):
    if job.get("template_id"):
        from src.modules.requirements.services.requirement_templates import get_template_version
        from src.repositories.requirement_template import requirement_template_repository

        template = await get_template_version(
            job["project_id"], job["template_id"], job["template_version"], user
        )
        source = await requirement_template_repository.find(job["template_id"])
        if source and source.get("project_id") == job["project_id"] and template.get("project_id") != job["project_id"] and not (job.get("template_public_view") and source.get("status") == "PUBLISHED"):
            raise HTTPException(status_code=403, detail={"code": "TEMPLATE_SOURCE_ACCESS_DENIED"})
    document_ids = {
        reference["requirement_document_id"]
        for item in job.get("preview", [])
        for reference in item.get("source_refs", [])
        if reference.get("requirement_document_id")
    }
    if job.get("source_document_id"):
        document_ids.add(job["source_document_id"])
    for document_id in document_ids:
        document = await requirement_import_repository.find_source_document(document_id, job["project_id"])
        if not document:
            raise HTTPException(status_code=422, detail={"code": "IMPORT_SOURCE_MISSING"})
        await require_document_access(document, user, 'requirement_document.read')


async def compare_requirement_import_job(job, user):
    await authorize_requirement_import_job(job, user)
    await get_project(job["project_id"], user, "requirement.read")
    requirements, versions = await requirement_import_repository.list_current_requirements(job["project_id"])
    if len(requirements) > 20000:
        raise HTTPException(status_code=422, detail={"code": "IMPORT_REQUIREMENT_COMPARISON_LIMIT_EXCEEDED"})
    if len(versions) != len(requirements):
        raise HTTPException(status_code=409, detail={"code": "IMPORT_REQUIREMENT_VERSION_MISSING"})
    threshold = RequirementDuplicateCheckInput().threshold
    comparisons = []
    matched_version_ids = set()
    criteria_cache = {}
    for index, candidate in enumerate(job.get("preview", [])):
        matches = []
        for previous_index, previous in enumerate(job.get("preview", [])[:index]):
            score, reasons = requirement_duplicate_score(
                candidate,
                previous,
            )
            same_key = bool(
                candidate.get("requirement_key")
                and candidate["requirement_key"] == previous.get("requirement_key")
            )
            if score >= threshold or same_key:
                matches.append({
                    "candidate_index": previous_index,
                    "candidate_id": previous.get("candidate_id"),
                    "requirement_key": previous.get("requirement_key"),
                    "title": previous.get("title"),
                    "content": plain_text(previous.get("content_doc", {})),
                    "score": score,
                    "match_type": "SAME_KEY_IN_IMPORT" if same_key else "IN_IMPORT",
                    "reasons": reasons,
                    "affected_test_cases": [],
                })
        lexical_candidates = []
        for requirement in requirements:
            version = versions.get(requirement.get("current_version_id"))
            if not version:
                continue
            version_id = version["_id"]
            if version_id not in criteria_cache:
                criteria_cache[version_id] = await analysis_repository.list_acceptance_criteria(
                    version_id
                )
            score, reasons = requirement_duplicate_score(
                candidate,
                {**version, "acceptance_criteria": criteria_cache[version_id]},
            )
            if (
                candidate.get("type") == version.get("type")
                and candidate.get("acceptance_criteria")
                and criteria_cache[version_id]
            ):
                criterion_score, criterion_reasons = requirement_duplicate_score(
                    {
                        "type": candidate.get("type"),
                        "acceptance_criteria": candidate["acceptance_criteria"],
                    },
                    {
                        "type": version.get("type"),
                        "acceptance_criteria": criteria_cache[version_id],
                    },
                )
                if criterion_score > score:
                    score = criterion_score
                    reasons = [*reasons, *criterion_reasons]
            same_key = bool(
                candidate.get("requirement_key")
                and candidate["requirement_key"] == requirement.get("requirement_key")
            )
            lexical_candidates.append((requirement, version, score, reasons, same_key))

        semantic_scores = {}
        has_semantic_scope = any(
            requirement.get("status") not in {"OBSOLETE", "ARCHIVED"}
            for requirement, _, _, _, _ in lexical_candidates
        )
        if has_semantic_scope and not any(
            score >= threshold or same_key
            for _, _, score, _, same_key in lexical_candidates
        ):
            candidate_criteria = candidate.get("acceptance_criteria", [])
            candidate_text = " ".join(
                [
                    str(candidate.get("title") or ""),
                    plain_text(candidate.get("content_doc", {})),
                    *[str(item) for item in candidate.get("actors", [])],
                    *[str(item) for item in candidate.get("business_rules", [])],
                    *[
                        item.get("plain_text")
                        or plain_text(item.get("content_doc", {}))
                        for item in candidate_criteria
                    ],
                ]
            ).strip()
            semantic_search = await search_project_with_status(
                job["project_id"],
                candidate_text,
                ["requirement_version"],
                100,
                user,
            )
            if semantic_search.get("degraded_mode") != "NORMAL":
                raise HTTPException(
                    status_code=503,
                    detail={"code": "REQUIREMENT_SEMANTIC_MATCH_UNAVAILABLE"},
                )
            current_versions_by_id = {
                version["_id"]: (requirement, version)
                for requirement, version, _, _, _ in lexical_candidates
                if requirement.get("status") not in {"OBSOLETE", "ARCHIVED"}
            }
            semantic_hits = {}
            for item in semantic_search.get("items", []):
                version_id = item.get("artifact_version_id")
                if version_id in current_versions_by_id:
                    semantic_hits[version_id] = current_versions_by_id[version_id]
            if semantic_hits:
                passages = []
                semantic_version_ids = list(semantic_hits)
                for version_id in semantic_version_ids:
                    version = semantic_hits[version_id][1]
                    if version_id not in criteria_cache:
                        criteria_cache[version_id] = await analysis_repository.list_acceptance_criteria(
                            version_id
                        )
                    passages.append(
                        " ".join(
                            [
                                str(version.get("title") or ""),
                                version.get("plain_text_projection")
                                or plain_text(version.get("content_doc", {})),
                                *[str(value) for value in version.get("actors", [])],
                                *[str(value) for value in version.get("business_rules", [])],
                                *[
                                    criterion.get("plain_text")
                                    or plain_text(criterion.get("content_doc", {}))
                                    for criterion in criteria_cache[version_id]
                                ],
                            ]
                        ).strip()
                    )
                try:
                    semantic_values = await compare_project_text_semantics(
                        candidate_text, passages
                    )
                except Exception as error:
                    raise HTTPException(
                        status_code=503,
                        detail={"code": "REQUIREMENT_SEMANTIC_MATCH_UNAVAILABLE"},
                    ) from error
                semantic_scores = dict(zip(semantic_version_ids, semantic_values))

        for requirement, version, lexical_score, reasons, same_key in lexical_candidates:
            semantic_score = semantic_scores.get(version["_id"])
            score = requirement_import_match_score(
                lexical_score, semantic_score, threshold
            )
            if semantic_score is not None:
                if score >= threshold and "Ngữ nghĩa nội dung, quy tắc và tiêu chí gần giống" not in reasons:
                    reasons = [*reasons, "Ngữ nghĩa nội dung, quy tắc và tiêu chí gần giống"]
            if requirement.get("status") in {"OBSOLETE", "ARCHIVED"} and not same_key:
                continue
            if score < threshold and not same_key:
                continue
            exact_core = (
                lexical_score == 1
                and candidate.get("type") == version.get("type")
                and all(
                    not candidate.get(field) or candidate[field] == version.get(field, [])
                    for field in ("actors", "business_rules", "dependencies", "details", "section_states", "custom_values")
                )
            )
            if exact_core:
                existing_criteria = criteria_cache[version["_id"]]
                exact_core = len(existing_criteria) < 500 and [
                    plain_text(item.get("content_doc") or {}).strip()
                    for item in candidate.get("acceptance_criteria", [])
                ] == [
                    (item.get("plain_text") or plain_text(item.get("content_doc") or {})).strip()
                    for item in existing_criteria
                ]
            matches.append({
                "requirement_id": requirement["_id"],
                "requirement_key": requirement.get("requirement_key"),
                "requirement_status": requirement.get("status"),
                "version_id": version["_id"],
                "title": version.get("title"),
                "content": version.get("plain_text_projection") or plain_text(version.get("content_doc", {})),
                "score": score,
                "match_type": "EXACT" if exact_core else "SAME_KEY" if same_key else "POSSIBLE",
                "reasons": reasons,
            })
            matched_version_ids.add(version["_id"])
        matches.sort(key=lambda item: (-item["score"], str(item.get("requirement_id", item.get("candidate_index")))))
        comparisons.append({
            "candidate_index": index,
            "candidate_id": candidate.get("candidate_id"),
            "matches": matches,
        })
    if matched_version_ids:
        cases, case_versions = await requirement_import_repository.list_linked_test_cases(
            job["project_id"], list(matched_version_ids)
        )
        if len(case_versions) > 20000:
            raise HTTPException(status_code=422, detail={"code": "IMPORT_TEST_CASE_IMPACT_LIMIT_EXCEEDED"})
        case_by_id = {item["_id"]: item for item in cases}
        affected = {}
        for case_version in case_versions:
            case = case_by_id.get(case_version.get("test_case_id"))
            if not case or case.get("current_version_id") != case_version["_id"]:
                continue
            for version_id in case_version.get("requirement_version_ids", []):
                affected.setdefault(version_id, []).append({
                    "test_case_id": case["_id"],
                    "test_case_key": case.get("test_case_key"),
                })
        for comparison in comparisons:
            for match in comparison["matches"]:
                match["affected_test_cases"] = affected.get(match.get("version_id"), [])
    return {"job_id": job["_id"], "revision": job["revision"], "comparisons": comparisons}


async def resolve_requirement_import_candidate(job_id, candidate_id, payload, user):
    job = await get_project_entity(
        "import_jobs", job_id, user, "requirement_document.review_extraction"
    )
    if job.get("status") != "PREVIEW_READY" or job.get("revision") != payload.expected_revision:
        raise HTTPException(409, detail={"code": "IMPORT_REVISION_CONFLICT"})
    candidate = next(
        (item for item in job.get("preview", []) if item.get("candidate_id") == candidate_id), None
    )
    if not candidate:
        raise HTTPException(404, detail={"code": "IMPORT_CANDIDATE_NOT_FOUND"})
    comparison = await compare_requirement_import_job(job, user)
    candidate_comparison = next(
        (item for item in comparison["comparisons"] if item["candidate_id"] == candidate_id),
        None,
    )
    if not candidate_comparison:
        raise HTTPException(409, detail={"code": "IMPORT_MATCH_CHANGED"})
    if payload.action == "create_requirement":
        if candidate_comparison.get("matches"):
            raise HTTPException(
                409,
                detail={
                    "code": "IMPORT_MATCH_REVIEW_REQUIRED",
                    "candidate_indexes": [candidate_comparison["candidate_index"]],
                },
            )
        claimed = await requirement_import_repository.claim_confirmation(
            job_id,
            job["project_id"],
            "PREVIEW_READY",
            "RESOLVING",
            user.id,
            now(),
            payload.expected_revision,
        )
        if not claimed:
            raise HTTPException(409, detail={"code": "IMPORT_REVISION_CONFLICT"})
        remaining_preview = [
            item for item in job["preview"] if item.get("candidate_id") != candidate_id
        ]
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    created = await create_requirement_record(
                        job["project_id"],
                        RequirementCreate(**candidate),
                        user,
                        origin="import",
                        session=session,
                    )
                    resolution = {
                        "candidate_id": candidate_id,
                        "action": payload.action,
                        "requirement_id": created["_id"],
                        "to_version_id": created["current_version"]["_id"],
                        "reason": payload.reason,
                        "resolved_by": user.id,
                        "resolved_at": now(),
                    }
                    updated = await requirement_import_repository.finish_resolution(
                        job_id,
                        job["project_id"],
                        payload.expected_revision + 1,
                        remaining_preview,
                        resolution,
                        now(),
                        session=session,
                    )
                    if not updated:
                        raise HTTPException(
                            409, detail={"code": "IMPORT_RESOLUTION_INCOMPLETE"}
                        )
                    if updated["status"] == "CONFIRMED" and job.get("source_document_id"):
                        await requirement_import_repository.confirm_document(
                            job["source_document_id"],
                            job["project_id"],
                            "CONFIRMED",
                            now(),
                            session=session,
                        )
                    await audit(
                        user.id,
                        "requirement_import_candidate_resolved",
                        "RequirementImport",
                        job_id,
                        job["project_id"],
                        resolution,
                        session=session,
                    )
        except Exception:
            await requirement_import_repository.reset_confirmation(
                job_id, job["project_id"], "RESOLVING", "PREVIEW_READY", now()
            )
            raise
        await index_requirement_version(created["current_version"])
        return updated

    if not payload.target_requirement_id or not payload.expected_target_version_id:
        raise HTTPException(422, detail={"code": "IMPORT_RESOLUTION_TARGET_REQUIRED"})
    match = next(
        (
            item
            for entry in comparison["comparisons"]
            if entry["candidate_id"] == candidate_id
            for item in entry["matches"]
            if item.get("requirement_id") == payload.target_requirement_id
            and item.get("version_id") == payload.expected_target_version_id
        ),
        None,
    )
    if not match:
        raise HTTPException(409, detail={"code": "IMPORT_MATCH_CHANGED"})
    requirement = await get_project_entity(
        "requirements", payload.target_requirement_id, user, "requirement.version.create"
    )
    if requirement.get("current_version_id") != payload.expected_target_version_id:
        raise HTTPException(409, detail={"code": "REVISION_CONFLICT"})
    criteria = await analysis_repository.list_acceptance_criteria(
        payload.expected_target_version_id
    )
    old_criteria = [
        {
            "key": item["key"],
            "content_doc": item["content_doc"],
            "status": item.get("status", "draft"),
            "source_span": item.get("source_span"),
        }
        for item in criteria
    ]
    current = await requirement_import_repository.find_current_version(
        job["project_id"], payload.expected_target_version_id
    )
    if not current:
        raise HTTPException(409, detail={"code": "IMPORT_MATCH_CHANGED"})
    source_refs = unique_source_refs(
        current.get("source_refs", []) + candidate.get("source_refs", [])
    )
    if payload.action == "link_source" and match["match_type"] != "EXACT":
        raise HTTPException(422, detail={"code": "SOURCE_LINK_REQUIRES_EXACT_MATCH"})
    if payload.action == "link_source" and source_refs == current.get("source_refs", []):
        claimed = await requirement_import_repository.claim_confirmation(
            job_id,
            job["project_id"],
            "PREVIEW_READY",
            "RESOLVING",
            user.id,
            now(),
            payload.expected_revision,
        )
        if not claimed:
            raise HTTPException(409, detail={"code": "IMPORT_REVISION_CONFLICT"})
        remaining_preview = [
            item for item in job["preview"] if item.get("candidate_id") != candidate_id
        ]
        resolution = {
            "candidate_id": candidate_id,
            "action": "link_source_already_present",
            "requirement_id": requirement["_id"],
            "from_version_id": current["_id"],
            "to_version_id": current["_id"],
            "reason": payload.reason,
            "resolved_by": user.id,
            "resolved_at": now(),
        }
        try:
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    latest_requirement = await database.value.requirements.find_one(
                        {
                            "_id": requirement["_id"],
                            "project_id": job["project_id"],
                            "current_version_id": current["_id"],
                        },
                        session=session,
                    )
                    latest_version = await database.value.requirement_versions.find_one(
                        {
                            "_id": current["_id"],
                            "project_id": job["project_id"],
                            "requirement_id": requirement["_id"],
                        },
                        session=session,
                    )
                    if not latest_requirement or not latest_version:
                        raise HTTPException(
                            409, detail={"code": "REVISION_CONFLICT"}
                        )
                    latest_source_refs = unique_source_refs(
                        latest_version.get("source_refs", [])
                    )
                    if unique_source_refs(
                        latest_source_refs + candidate.get("source_refs", [])
                    ) != latest_source_refs:
                        raise HTTPException(
                            409, detail={"code": "SOURCE_LINK_STATE_CHANGED"}
                        )
                    updated = await requirement_import_repository.finish_resolution(
                        job_id,
                        job["project_id"],
                        payload.expected_revision + 1,
                        remaining_preview,
                        resolution,
                        now(),
                        session=session,
                    )
                    if not updated:
                        raise HTTPException(
                            409, detail={"code": "IMPORT_RESOLUTION_INCOMPLETE"}
                        )
                    if updated["status"] == "CONFIRMED" and job.get("source_document_id"):
                        await requirement_import_repository.confirm_document(
                            job["source_document_id"],
                            job["project_id"],
                            "CONFIRMED",
                            now(),
                            session=session,
                        )
                    await audit(
                        user.id,
                        "requirement_import_candidate_resolved",
                        "RequirementImport",
                        job_id,
                        job["project_id"],
                        resolution,
                        session=session,
                    )
        except Exception:
            await requirement_import_repository.reset_confirmation(
                job_id, job["project_id"], "RESOLVING", "PREVIEW_READY", now()
            )
            raise
        return updated
    values = {
        **current,
        "requirement_key": requirement.get("requirement_key"),
        "acceptance_criteria": old_criteria,
        "source_refs": source_refs,
        "change_reason": payload.reason,
        "expected_current_version_id": current["_id"],
    }
    if payload.action == "create_version":
        values["title"] = candidate.get("title") or current.get("title")
        values["type"] = candidate.get("type") or current.get("type")
        values["content_doc"] = candidate.get("content_doc") or current.get("content_doc")
        candidate_criteria = candidate.get("acceptance_criteria") or old_criteria
        values["acceptance_criteria"] = candidate_criteria
        for field in (
            "priority",
            "risk",
            "business_rules",
            "actors",
            "dependencies",
            "tags",
            "details",
            "section_states",
            "custom_values",
        ):
            candidate_value = candidate.get(field)
            current_value = current.get(field)
            values[field] = (
                candidate_value
                if candidate_value not in (None, "", [], {})
                else current_value
                if current_value is not None
                else RequirementCreate.model_fields[field].get_default(
                    call_default_factory=True
                )
            )
        section_states = dict(values.get("section_states") or {})
        for key, state in section_states.items():
            if key in RequirementCreate.model_fields and key not in {"details", "section_states"}:
                section_value = values.get(key)
            else:
                section_value = values.get("details")
                for part in key.split("."):
                    section_value = (
                        section_value.get(part)
                        if isinstance(section_value, dict)
                        else None
                    )
            has_content = (
                any(bool(item) for item in section_value.values())
                if isinstance(section_value, dict)
                else bool(section_value)
            )
            if has_content and state != "provided":
                section_states[key] = "provided"
            elif not has_content and state == "provided":
                section_states[key] = "missing"
        values["section_states"] = section_states
    claimed = await requirement_import_repository.claim_confirmation(
        job_id, job["project_id"], "PREVIEW_READY", "RESOLVING", user.id, now(),
        payload.expected_revision,
    )
    if not claimed:
        raise HTTPException(409, detail={"code": "IMPORT_REVISION_CONFLICT"})
    remaining_preview = [
        item for item in job["preview"] if item.get("candidate_id") != candidate_id
    ]
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                version = await create_requirement_version_record(
                    requirement["_id"],
                    RequirementVersionCreate(**values),
                    user,
                    session=session,
                )
                resolution = {
                    "candidate_id": candidate_id,
                    "action": payload.action,
                    "requirement_id": requirement["_id"],
                    "from_version_id": current["_id"],
                    "to_version_id": version["_id"],
                    "reason": payload.reason,
                    "resolved_by": user.id,
                    "resolved_at": now(),
                }
                updated = await requirement_import_repository.finish_resolution(
                    job_id,
                    job["project_id"],
                    payload.expected_revision + 1,
                    remaining_preview,
                    resolution,
                    now(),
                    session=session,
                )
                if not updated:
                    raise HTTPException(
                        409, detail={"code": "IMPORT_RESOLUTION_INCOMPLETE"}
                    )
                if updated["status"] == "CONFIRMED" and job.get("source_document_id"):
                    await requirement_import_repository.confirm_document(
                        job["source_document_id"],
                        job["project_id"],
                        "CONFIRMED",
                        now(),
                        session=session,
                    )
                await audit(
                    user.id,
                    "requirement_import_candidate_resolved",
                    "RequirementImport",
                    job_id,
                    job["project_id"],
                    resolution,
                    session=session,
                )
    except Exception:
        await requirement_import_repository.reset_confirmation(
            job_id, job["project_id"], "RESOLVING", "PREVIEW_READY", now()
        )
        raise
    await index_requirement_version(version)
    return updated




async def extract_requirement_candidates(document_id, payload, user):
    
    document = await get_project_entity(
        'requirement_documents',
        document_id,
        user,
        'requirement_document.extract',
    )
    await require_document_access(document, user, 'requirement_document.read')
    if document.get("status") == 'ARCHIVED':
        raise HTTPException(
            status_code=409, detail={"code": 'DOCUMENT_ARCHIVED'}
        )
    if document.get("normalized_content") is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'DOCUMENT_PARSE_REQUIRED',
                "status": document.get("status"),
            },
        )
    existing = await requirement_import_repository.find_by_source_document(document_id)
    if existing:
        return existing
    await audit(
        user.id,
        'requirement_extraction_requested',
        'RequirementDocument',
        document_id,
        document["project_id"],
    )
    job_id = new_id('RIMP')
    extraction_mode = "DETERMINISTIC"
    conflicts = []
    if document.get("ai_enabled") and document.get("format") not in {"openapi", "postman"}:
        extracted, conflicts = await extract_grounded_requirement_candidates(
            document, document["project_id"]
        )
        extraction_mode = "AI_GROUNDED"
    else:
        extracted = atomic_requirement_candidates(document)
    if len(extracted) > 500:
        raise HTTPException(status_code=413, detail={"code": "IMPORT_CANDIDATE_LIMIT_EXCEEDED"})
    candidates = prepare_requirement_candidates(job_id, extracted)
    job = {
        "_id": job_id,
        "project_id": document["project_id"],
        "source_document_id": document_id,
        "source_content_hash": document["content_hash"],
        "filename": document["filename"],
        "format": document["format"],
        "status": 'PREVIEW_READY',
        "preview": candidates,
        "candidate_count": len(candidates),
        "warnings": (["NO_DOCUMENTED_BEHAVIOR_TO_DRAFT"] if not candidates else [])
        + (["SOURCE_CONFLICTS_FOUND"] if conflicts else []),
        "source_conflicts": conflicts,
        "extraction_mode": extraction_mode,
        "idempotency_key": payload.idempotency_key,
        "revision": 1,
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        await requirement_import_repository.insert(job)
    except DuplicateKeyError:
        return await requirement_import_repository.find_by_source_document(document_id)
    await requirement_import_repository.mark_document_extracted(
        document_id,
        document["project_id"],
        'EXTRACTED',
        job["_id"],
        now(),
    )
    await audit(
        user.id,
        'requirement_extraction_completed',
        'RequirementDocument',
        document_id,
        document["project_id"],
        {"job_id": job["_id"], "candidate_count": len(candidates)},
    )
    return job


async def create_requirement_import_job(project_id, payload, user):
    document = await create_requirement_document_record(project_id, payload, user)
    return await extract_requirement_candidates(
        document["_id"],
        RequirementExtractionInput(idempotency_key=f"source-{document['content_hash']}"),
        user,
    )


async def create_requirement_preview_from_candidates(project_id, filename, candidates, user, template_id=None, template_version=None, template_public_view=False):
    await get_project(project_id, user, 'requirement.create')
    if not candidates or len(candidates) > 500:
        raise HTTPException(status_code=422, detail={"code": "IMPORT_CANDIDATE_COUNT_INVALID"})
    if template_id:
        existing = await requirement_import_repository.find_by_template_version(project_id, template_id, template_version, template_public_view)
        if existing:
            return existing
    job_id = new_id('RIMP')
    previews = prepare_requirement_candidates(job_id, candidates)
    job = {
        "_id": job_id,
        "project_id": project_id,
        "filename": filename,
        "format": "template",
        "template_id": template_id,
        "template_version": template_version,
        "template_public_view": template_public_view,
        "status": 'PREVIEW_READY',
        "preview": previews,
        "candidate_count": len(previews),
        "revision": 1,
        "created_by": user.id,
        "created_at": now(),
    }
    try:
        await requirement_import_repository.insert(job)
    except DuplicateKeyError:
        if template_id:
            return await requirement_import_repository.find_by_template_version(project_id, template_id, template_version, template_public_view)
        raise
    await audit(user.id, 'requirement_import_previewed', 'RequirementImport', job_id, project_id, {"count": len(previews), "template_id": template_id})
    return job


async def review_requirement_import_job(job_id, payload, user):
    
    job = await get_project_entity(
        'import_jobs', job_id, user, 'requirement_document.review_extraction'
    )
    await authorize_requirement_import_job(job, user)
    if job.get("status") != 'PREVIEW_READY':
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'IMPORT_PREVIEW_NOT_EDITABLE',
                "status": job.get("status"),
            },
        )
    current_preview = prepare_requirement_candidates(job_id, job.get("preview", []))
    submitted = [candidate.model_dump() for candidate in payload.preview]
    if len(submitted) == len(current_preview) and all(
        not item.get("candidate_id") for item in submitted
    ):
        for index, item in enumerate(submitted):
            item["candidate_id"] = current_preview[index]["candidate_id"]
    current_by_id = {item["candidate_id"]: item for item in current_preview}
    submitted_by_id = {item.get("candidate_id"): item for item in submitted}
    if None in submitted_by_id or set(submitted_by_id) != set(current_by_id):
        raise HTTPException(
            status_code=422, detail={"code": 'CANDIDATE_SET_CHANGED'}
        )
    preview = []
    for current in current_preview:
        candidate = submitted_by_id[current["candidate_id"]]
        candidate["source_refs"] = current.get("source_refs", [])
        candidate["candidate_status"] = 'ACTIVE'
        candidate["candidate_revision"] = int(current.get("candidate_revision", 1)) + 1
        candidate["candidate_relation"] = current.get("candidate_relation")
        candidate["parent_candidate_ids"] = current.get("parent_candidate_ids", [])
        preview.append(candidate)
        validate_doc(candidate["content_doc"])
        for criterion in candidate.get("acceptance_criteria", []):
            validate_doc(criterion["content_doc"])
    updated = await requirement_import_repository.update_preview(
        job_id,
        job["project_id"],
        'PREVIEW_READY',
        payload.expected_revision,
        prepare_requirement_candidates(job_id, preview),
        user.id,
        now(),
        review_note=payload.review_note,
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    await audit(
        user.id,
        'requirement_import_reviewed',
        'RequirementImport',
        job_id,
        job["project_id"],
        {"candidate_count": len(preview), "review_note": payload.review_note},
    )
    return updated


async def merge_requirement_import_candidates(job_id, payload, user):
    
    job = await get_project_entity(
        'import_jobs', job_id, user, 'requirement_document.review_extraction'
    )
    await authorize_requirement_import_job(job, user)
    if job.get("status") != 'PREVIEW_READY':
        raise HTTPException(
            status_code=409, detail={"code": 'IMPORT_PREVIEW_NOT_EDITABLE'}
        )
    candidate_ids = list(dict.fromkeys(payload.candidate_ids))
    if len(candidate_ids) != len(payload.candidate_ids):
        raise HTTPException(
            status_code=422, detail={"code": 'DUPLICATE_CANDIDATE_ID'}
        )
    preview = prepare_requirement_candidates(job_id, job.get("preview", []))
    by_id = {item["candidate_id"]: item for item in preview}
    if not set(candidate_ids) <= set(by_id):
        raise HTTPException(
            status_code=404, detail={"code": 'CANDIDATE_NOT_FOUND'}
        )
    parents = [by_id[item] for item in candidate_ids]
    merged = payload.merged.model_dump()
    validate_doc(merged["content_doc"])
    for criterion in merged.get("acceptance_criteria", []):
        validate_doc(criterion["content_doc"])
    merged["source_refs"] = unique_source_refs(
        [source for parent in parents for source in parent.get("source_refs", [])]
        + merged.get("source_refs", [])
    )
    await validate_requirement_sources(job["project_id"], merged["source_refs"], user)
    merged_id = new_id('RCAND')
    merged.update(
        {
            "candidate_id": merged_id,
            "candidate_status": 'ACTIVE',
            "candidate_revision": 1,
            "candidate_relation": 'merged',
            "parent_candidate_ids": candidate_ids,
        }
    )
    first_index = min(
        index for index, item in enumerate(preview) if item["candidate_id"] in candidate_ids
    )
    next_preview = [item for item in preview if item["candidate_id"] not in candidate_ids]
    next_preview.insert(first_index, merged)
    event = {
        "_id": new_id('RCOP'),
        "type": 'MERGE',
        "parent_candidate_ids": candidate_ids,
        "result_candidate_ids": [merged_id],
        "parent_fingerprints": [candidate_fingerprint(item) for item in parents],
        "source_refs": merged["source_refs"],
        "reason": payload.reason,
        "actor_id": user.id,
        "created_at": now(),
    }
    updated = await requirement_import_repository.update_preview(
        job_id,
        job["project_id"],
        'PREVIEW_READY',
        payload.expected_revision,
        prepare_requirement_candidates(job_id, next_preview),
        user.id,
        now(),
        push_field="candidate_lineage",
        push_value=event,
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    await audit(
        user.id,
        'requirement_candidates_merged',
        'RequirementImport',
        job_id,
        job["project_id"],
        {
            "parent_candidate_ids": candidate_ids,
            "result_candidate_id": merged_id,
            "reason": payload.reason,
        },
    )
    return updated


async def split_requirement_import_candidate(job_id, candidate_id, payload, user):
    
    job = await get_project_entity(
        'import_jobs', job_id, user, 'requirement_document.review_extraction'
    )
    await authorize_requirement_import_job(job, user)
    if job.get("status") != 'PREVIEW_READY':
        raise HTTPException(
            status_code=409, detail={"code": 'IMPORT_PREVIEW_NOT_EDITABLE'}
        )
    preview = prepare_requirement_candidates(job_id, job.get("preview", []))
    parent = next((item for item in preview if item["candidate_id"] == candidate_id), None)
    if not parent:
        raise HTTPException(
            status_code=404, detail={"code": 'CANDIDATE_NOT_FOUND'}
        )
    if len(preview) - 1 + len(payload.drafts) > 500:
        raise HTTPException(
            status_code=422, detail={"code": 'CANDIDATE_LIMIT_EXCEEDED'}
        )
    children = []
    for index, draft in enumerate(payload.drafts):
        child = draft.model_dump()
        validate_doc(child["content_doc"])
        for criterion in child.get("acceptance_criteria", []):
            validate_doc(criterion["content_doc"])
        child["source_refs"] = unique_source_refs(
            parent.get("source_refs", []) + child.get("source_refs", [])
        )
        await validate_requirement_sources(job["project_id"], child["source_refs"], user)
        child.update(
            {
                "candidate_id": new_id('RCAND'),
                "candidate_status": 'ACTIVE',
                "candidate_revision": 1,
                "candidate_relation": f"{'split'}-{index + 1}",
                "parent_candidate_ids": [candidate_id],
            }
        )
        children.append(child)
    parent_index = next(
        index for index, item in enumerate(preview) if item["candidate_id"] == candidate_id
    )
    next_preview = list(preview)
    next_preview[parent_index : parent_index + 1] = children
    event = {
        "_id": new_id('RCOP'),
        "type": 'SPLIT',
        "parent_candidate_ids": [candidate_id],
        "result_candidate_ids": [item["candidate_id"] for item in children],
        "parent_fingerprints": [candidate_fingerprint(parent)],
        "source_refs": parent.get("source_refs", []),
        "reason": payload.reason,
        "actor_id": user.id,
        "created_at": now(),
    }
    updated = await requirement_import_repository.update_preview(
        job_id,
        job["project_id"],
        'PREVIEW_READY',
        payload.expected_revision,
        prepare_requirement_candidates(job_id, next_preview),
        user.id,
        now(),
        push_field="candidate_lineage",
        push_value=event,
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    await audit(
        user.id,
        'requirement_candidate_split',
        'RequirementImport',
        job_id,
        job["project_id"],
        {
            "parent_candidate_id": candidate_id,
            "result_candidate_ids": [item["candidate_id"] for item in children],
            "reason": payload.reason,
        },
    )
    return updated


async def reject_requirement_import_candidate(job_id, candidate_id, payload, user):
    
    job = await get_project_entity(
        'import_jobs', job_id, user, 'requirement_document.review_extraction'
    )
    await authorize_requirement_import_job(job, user)
    if job.get("status") != 'PREVIEW_READY':
        raise HTTPException(
            status_code=409, detail={"code": 'IMPORT_PREVIEW_NOT_EDITABLE'}
        )
    preview = prepare_requirement_candidates(job_id, job.get("preview", []))
    candidate = next((item for item in preview if item["candidate_id"] == candidate_id), None)
    if not candidate:
        rejected = next(
            (
                item
                for item in job.get("rejected_candidates", [])
                if item.get("candidate_id") == candidate_id
            ),
            None,
        )
        if rejected:
            return job
        raise HTTPException(
            status_code=404, detail={"code": 'CANDIDATE_NOT_FOUND'}
        )
    rejected = {
        **candidate,
        "candidate_status": 'REJECTED',
        "candidate_revision": int(candidate.get("candidate_revision", 1)) + 1,
        "rejection_reason": payload.reason,
        "rejected_by": user.id,
        "rejected_at": now(),
    }
    next_preview = [item for item in preview if item["candidate_id"] != candidate_id]
    updated = await requirement_import_repository.update_preview(
        job_id,
        job["project_id"],
        'PREVIEW_READY',
        payload.expected_revision,
        prepare_requirement_candidates(job_id, next_preview),
        user.id,
        now(),
        push_field="rejected_candidates",
        push_value=rejected,
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'REVISION_CONFLICT'}
        )
    await audit(
        user.id,
        'requirement_candidate_rejected',
        'RequirementImport',
        job_id,
        job["project_id"],
        {"candidate_id": candidate_id, "reason": payload.reason},
    )
    return updated


async def apply_requirement_import_job(job_id, payload, user):
    
    job = await get_project_entity(
        'import_jobs', job_id, user, 'requirement.create'
    )
    await authorize_requirement_import_job(job, user)
    await get_project(job["project_id"], user, 'requirement.create')
    if job["status"] == 'CONFIRMED':
        await recover_confirmed_import_index(job)
        return {"job": job, "requirements": None}
    indexes = payload.selected_indexes
    if not indexes:
        raise HTTPException(status_code=422, detail={"code": "IMPORT_SELECTION_REQUIRED"})
    indexes = list(dict.fromkeys(indexes))
    for index in indexes:
        if index < 0 or index >= len(job["preview"]):
            raise HTTPException(
                status_code=422,
                detail={"code": 'INVALID_PREVIEW_INDEX'},
            )
        item = job["preview"][index]
        if not plain_text(item.get("content_doc") or {}).strip() or not item.get("source_refs"):
            raise HTTPException(status_code=422, detail={"code": "IMPORT_CANDIDATE_INCOMPLETE", "index": index})
    comparison = await compare_requirement_import_job(job, user)
    key_conflicts = sorted({
        item["candidate_index"]
        for item in comparison["comparisons"]
        if item["candidate_index"] in indexes
        and job["preview"][item["candidate_index"]].get("requirement_key")
        and any(
            match.get("requirement_key")
            == job["preview"][item["candidate_index"]].get("requirement_key")
            and (
                match["match_type"] != "SAME_KEY_IN_IMPORT"
                or match["candidate_index"] in indexes
            )
            for match in item["matches"]
        )
    })
    if key_conflicts:
        raise HTTPException(
            status_code=409,
            detail={"code": "IMPORT_REQUIREMENT_KEY_CONFLICT", "candidate_indexes": key_conflicts},
        )
    matched_indexes = {
        item["candidate_index"]
        for item in comparison["comparisons"]
        if any(
            match["match_type"] not in {"IN_IMPORT", "SAME_KEY_IN_IMPORT"} or match["candidate_index"] in indexes
            for match in item["matches"]
        )
    }
    unresolved = sorted((set(indexes) & matched_indexes) - set(payload.separate_indexes))
    if unresolved:
        raise HTTPException(
            status_code=409,
            detail={"code": "IMPORT_MATCH_REVIEW_REQUIRED", "candidate_indexes": unresolved},
        )
    if set(payload.separate_indexes) - (set(indexes) & matched_indexes):
        raise HTTPException(status_code=422, detail={"code": "INVALID_IMPORT_RESOLUTION"})
    if any(
        not payload.separate_reasons.get(index, "").strip()
        for index in payload.separate_indexes
    ):
        raise HTTPException(status_code=422, detail={"code": "IMPORT_SEPARATE_REASON_REQUIRED"})
    claimed = await requirement_import_repository.claim_confirmation(
        job_id,
        job["project_id"],
        'PREVIEW_READY',
        'CONFIRMING',
        user.id,
        now(),
        payload.expected_revision,
    )
    if not claimed:
        current = await requirement_import_repository.find(job_id, job["project_id"])
        if current and current.get("status") == 'CONFIRMED':
            await recover_confirmed_import_index(current)
            return {"job": current, "requirements": None}
        raise HTTPException(
            status_code=409,
            detail={"code": 'IMPORT_CONFIRM_IN_PROGRESS'},
        )
    created = []
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                for index in indexes:
                    item = job["preview"][index]
                    created.append(
                        await create_requirement_record(
                            job["project_id"],
                            RequirementCreate(**item),
                            user,
                            origin='import',
                            session=session,
                        )
                    )
                rejected_indexes = [
                    index for index in range(len(job["preview"])) if index not in indexes
                ]
                confirmed = await requirement_import_repository.confirm(
                    job_id,
                    job["project_id"],
                    'CONFIRMING',
                    'CONFIRMED',
                    [item["_id"] for item in created],
                    indexes,
                    rejected_indexes,
                    [item["current_version"]["_id"] for item in created],
                    user.id,
                    now(),
                    session=session,
                )
                if not confirmed:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "IMPORT_CONFIRMATION_CONFLICT"},
                    )
                if job.get("source_document_id"):
                    await requirement_import_repository.confirm_document(
                        job["source_document_id"],
                        job["project_id"],
                        'CONFIRMED',
                        now(),
                        session=session,
                    )
                await audit(
                    user.id,
                    'requirement_import_confirmed',
                    'RequirementImport',
                    job_id,
                    job["project_id"],
                    {
                        "created_requirement_ids": [item["_id"] for item in created],
                        "selected_indexes": indexes,
                        "separate_reasons": {
                            str(index): payload.separate_reasons[index].strip()
                            for index in payload.separate_indexes
                        },
                        "rejected_indexes": rejected_indexes,
                    },
                    session=session,
                )
    except Exception:
        await requirement_import_repository.reset_confirmation(
            job_id,
            job["project_id"],
            'CONFIRMING',
            'PREVIEW_READY',
            now(),
        )
        await audit(
            user.id,
            'requirement_import_confirmation_failed',
            'RequirementImport',
            job_id,
            job["project_id"],
        )
        raise
    confirmed_job = await requirement_import_repository.find(job_id, job["project_id"])
    await recover_confirmed_import_index(confirmed_job)
    return {"job": None, "requirements": created}


async def confirm_requirement_import_job(job_id, payload, user):
    return await apply_requirement_import_job(job_id, payload, user)


async def recover_confirmed_import_index(job):
    version_ids = list(job.get("created_requirement_version_ids") or [])
    if not version_ids:
        return
    versions = await requirement_repository.list_versions_by_ids(
        job["project_id"], version_ids, len(version_ids)
    )
    versions_by_id = {item["_id"]: item for item in versions}
    if set(versions_by_id) != set(version_ids):
        raise HTTPException(
            status_code=409,
            detail={"code": "IMPORT_CONFIRMED_VERSION_MISSING"},
        )
    for version_id in version_ids:
        version = versions_by_id[version_id]
        if version.get("index_status") != "READY":
            await index_requirement_version(version)
