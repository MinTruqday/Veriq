import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.core.common import audit, get_project, new_id, now, plain_text
from src.core.database import database
from src.modules.requirements.services.document_reader import _document_text
from src.modules.requirements.services.requirement_documents import can_read_requirement_document
from src.core.source_evidence import split_source_evidence
from src.modules.projects.services.project_complexity_config import (
    resolve_project_complexity_dimensions,
)


def _fingerprint(manifest):
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def _commercial_feasibility(project_id, user):
    if not user.is_system_admin:
        return None
    project = await database.value.projects.find_one(
        {"_id": project_id}, {"commercial_terms": 1}
    )
    terms = (project or {}).get("commercial_terms") or {}
    if not terms.get("contract_price"):
        return {"status": "MISSING_CUSTOMER_PRICE"}
    plan = await database.value.test_plans.find_one(
        {"project_id": project_id, "status": "APPROVED"},
        sort=[("updated_at", -1)],
    )
    if not plan:
        return {"status": "MISSING_APPROVED_TEST_PLAN"}
    plan_source = plan.get("approved_snapshot") or plan
    estimation = plan_source.get("estimation") or {}
    allocations = estimation.get("effort_allocations") or []
    try:
        planned_hours = Decimal(str(estimation.get("planned_effort_hours") or 0))
        allocated_hours = sum(
            (Decimal(str(item.get("planned_hours") or 0)) for item in allocations),
            Decimal(0),
        )
    except (InvalidOperation, TypeError, ValueError):
        return {"status": "FINANCIAL_DATA_INVALID", "currency": terms.get("currency")}
    if planned_hours <= 0 or allocated_hours != planned_hours or not allocations:
        return {"status": "APPROVED_PLAN_EFFORT_INCOMPLETE", "currency": terms.get("currency")}
    try:
        effective_date = date.fromisoformat(str((plan_source.get("schedule") or {}).get("planned_start_at"))[:10])
    except ValueError:
        return {"status": "APPROVED_PLAN_START_DATE_MISSING", "currency": terms.get("currency")}
    labor_cost = Decimal(0)
    missing_rates = 0
    for allocation in allocations:
        rate = await database.value.payroll_rates.find_one(
            {
                "user_id": allocation.get("user_id"),
                "currency": terms.get("currency"),
                "valid_from": {"$lte": effective_date.isoformat()},
                "$or": [{"valid_until": None}, {"valid_until": {"$gte": effective_date.isoformat()}}],
            },
            sort=[("valid_from", -1)],
            projection={"hourly_cost": 1},
        )
        if not rate:
            missing_rates += 1
            continue
        try:
            labor_cost += Decimal(str(rate["hourly_cost"])) * Decimal(str(allocation["planned_hours"]))
        except (InvalidOperation, KeyError, ValueError):
            missing_rates += 1
    if missing_rates:
        return {
            "status": "MISSING_LABOR_RATES",
            "currency": terms.get("currency"),
            "planned_hours": str(planned_hours),
            "missing_rate_count": missing_rates,
        }
    try:
        customer_price = Decimal(str(terms["contract_price"]))
    except (InvalidOperation, KeyError, ValueError):
        return {"status": "FINANCIAL_DATA_INVALID", "currency": terms.get("currency")}
    variance = customer_price - labor_cost
    return {
        "status": "FORECAST_ONLY",
        "customer_price": str(customer_price),
        "estimated_labor_cost": str(labor_cost),
        "variance_before_other_costs": str(variance),
        "currency": terms.get("currency"),
        "planned_hours": str(planned_hours),
        "comparison": "BELOW_LABOR_COST" if variance < 0 else "COVERS_LABOR_COST",
        "actual_cost_available": False,
        "scope_note": terms.get("scope_note") or "",
    }


async def _source_scope(
    project_id,
    user,
    *,
    include_text=False,
    document_ids=None,
    requirement_version_ids=None,
    include_documents=True,
):
    await get_project(project_id, user, "ai.ask_project")
    await get_project(project_id, user, "requirement.read")
    if include_documents and (document_ids is None or document_ids):
        await get_project(project_id, user, "requirement_document.read")
    scoped = document_ids is not None or requirement_version_ids is not None
    selected_document_ids = set(document_ids or []) if scoped else None
    selected_requirement_version_ids = set(requirement_version_ids or []) if scoped else None
    documents = await database.value.requirement_documents.find(
        {"project_id": project_id}
    ).sort([("source_series_id", 1), ("source_version_sequence", -1), ("_id", -1)]).to_list(None)
    latest_by_series = {}
    standalone = []
    for document in documents:
        series_id = document.get("source_series_id")
        if not series_id:
            standalone.append(document)
            continue
        key = str(series_id)
        current = latest_by_series.get(key)
        if current is None or int(document.get("source_version_sequence") or 0) > int(
            current.get("source_version_sequence") or 0
        ):
            latest_by_series[key] = document
    current_documents = [*standalone, *latest_by_series.values()]
    manifest = []
    evidence = []
    source_options = {"documents": [], "requirements": []}
    excluded = {"not_readable": 0, "ai_not_allowed": 0, "not_ready": 0, "empty": 0}
    extraction_gaps = []
    for document in current_documents if include_documents else []:
        document_id = str(document["_id"])
        if selected_document_ids is not None and document_id not in selected_document_ids:
            continue
        if not can_read_requirement_document(document, user):
            excluded["not_readable"] += 1
            if not scoped:
                manifest.append({"id": document_id, "access": "unavailable"})
            continue
        if document.get("status") == "ARCHIVED":
            continue
        entry = {
            "id": document_id,
            "revision": document.get("revision"),
            "content_hash": document.get("content_hash"),
            "source_version": document.get("source_version"),
            "status": document.get("status"),
            "ai_enabled": document.get("ai_enabled") is True,
            "unprocessed_block_count": len((document.get("parse_report") or {}).get("unprocessed_blocks") or []),
            "extraction_warning_count": len((document.get("parse_report") or {}).get("extraction_warnings") or []),
        }
        if document.get("ai_enabled") is not True:
            excluded["ai_not_allowed"] += 1
            if not scoped:
                manifest.append(entry)
            continue
        if document.get("status") != "READY":
            excluded["not_ready"] += 1
            if not scoped:
                manifest.append(entry)
            continue
        source_options["documents"].append(
            {
                "id": document_id,
                "filename": document.get("filename") or document.get("title") or document_id,
                "source_version": str(
                    document.get("source_version")
                    or document.get("source_version_sequence")
                    or "1"
                ),
                "revision": document.get("revision"),
            }
        )
        manifest.append(entry)
        report = document.get("parse_report") or {}
        if report.get("unprocessed_blocks") or report.get("extraction_warnings"):
            extraction_gaps.append(
                {
                    "source_id": document_id,
                    "unprocessed_block_count": len(report.get("unprocessed_blocks") or []),
                    "warning_count": len(report.get("extraction_warnings") or []),
                }
            )
        if include_text:
            text = (await _document_text(document)).strip()
            chunks = split_source_evidence("requirement_document", document_id, text)
            for chunk in chunks:
                chunk_ref = f"{document_id}:v{document.get('source_version_sequence') or 1}:c{chunk['chunk_index']}"
                evidence.append(
                    {
                        "artifact_type": "requirement_document",
                        "artifact_id": document_id,
                        "artifact_version_id": chunk_ref,
                        "source_version": str(document.get("source_version") or document.get("source_version_sequence") or "1"),
                        "text": chunk["text"],
                    }
                )
            if not chunks:
                excluded["empty"] += 1

    requirements = await database.value.requirements.find(
        {"project_id": project_id, "status": {"$ne": "ARCHIVED"}},
        {"_id": 1, "current_version_id": 1, "requirement_key": 1},
    ).to_list(None)
    requirements_by_version = {
        str(item["current_version_id"]): item
        for item in requirements
        if item.get("current_version_id")
    }
    current_version_ids = [
        item["current_version_id"] for item in requirements if item.get("current_version_id")
    ]
    versions = await database.value.requirement_versions.find(
        {"project_id": project_id, "_id": {"$in": current_version_ids}, "status": "BASELINED"}
    ).to_list(None) if current_version_ids else []
    version_ids = [item["_id"] for item in versions]
    criteria = await database.value.acceptance_criteria.find(
        {"project_id": project_id, "requirement_version_id": {"$in": version_ids}}
    ).to_list(None) if version_ids else []
    criteria_by_version = {}
    for criterion in criteria:
        criteria_by_version.setdefault(criterion["requirement_version_id"], []).append(criterion)
    for version in versions:
        version_id = str(version["_id"])
        requirement = requirements_by_version.get(version_id, {})
        source_options["requirements"].append(
            {
                "version_id": version_id,
                "requirement_id": str(version.get("requirement_id") or requirement.get("_id") or ""),
                "requirement_key": requirement.get("requirement_key") or "",
                "title": version.get("title") or "",
                "revision": version.get("revision"),
            }
        )
    available_document_ids = {item["id"] for item in source_options["documents"]}
    available_requirement_version_ids = {
        item["version_id"] for item in source_options["requirements"]
    }
    if scoped and (
        not selected_document_ids.issubset(available_document_ids)
        or not selected_requirement_version_ids.issubset(available_requirement_version_ids)
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "PROJECT_COMPLEXITY_SOURCE_SCOPE_UNAVAILABLE", "retryable": True},
        )
    selected_versions = [
        version
        for version in versions
        if selected_requirement_version_ids is None
        or str(version["_id"]) in selected_requirement_version_ids
    ]
    for version in selected_versions:
        version_id = str(version["_id"])
        manifest.append(
            {
                "id": version_id,
                "requirement_id": str(version.get("requirement_id") or ""),
                "revision": version.get("revision"),
                "status": version.get("status"),
            }
        )
        if include_text:
            content_parts = [
                str(version.get("title") or "").strip(),
                str(version.get("plain_text_projection") or plain_text(version.get("content_doc", {}))).strip(),
                *[str(item).strip() for item in version.get("business_rules") or []],
                *[str(item).strip() for item in version.get("actors") or []],
                *[str(item).strip() for item in version.get("dependencies") or []],
                *[
                    str(item.get("plain_text") or plain_text(item.get("content_doc", {}))).strip()
                    for item in criteria_by_version.get(version["_id"], [])
                ],
            ]
            text = "\n".join(part for part in content_parts if part)
            for chunk in split_source_evidence("requirement_version", version_id, text):
                chunk_ref = f"{version_id}:c{chunk['chunk_index']}"
                evidence.append(
                    {
                        "artifact_type": "requirement_version",
                        "artifact_id": str(version.get("requirement_id") or version_id),
                        "artifact_version_id": chunk_ref,
                        "authority": "PROJECT_BASELINE",
                        "text": chunk["text"],
                    }
                )
    selected_version_ids = {str(item["_id"]) for item in selected_versions}
    for criterion in criteria:
        if str(criterion.get("requirement_version_id") or "") not in selected_version_ids:
            continue
        criterion_text = str(
            criterion.get("plain_text") or plain_text(criterion.get("content_doc", {}))
        ).strip()
        manifest.append(
            {
                "id": str(criterion["_id"]),
                "requirement_version_id": str(criterion.get("requirement_version_id") or ""),
                "revision": criterion.get("revision"),
                "content_hash": hashlib.sha256(criterion_text.encode("utf-8")).hexdigest(),
            }
        )
    manifest.sort(key=lambda item: (item.get("id", ""), item.get("status", "")))
    return {
        "manifest": manifest,
        "fingerprint": _fingerprint(manifest),
        "evidence": evidence,
        "excluded": excluded,
        "extraction_gaps": extraction_gaps,
        "requirement_count": len(selected_versions),
        "document_count": sum(
            1
            for item in manifest
            if item.get("ai_enabled") and item.get("status") == "READY"
        ),
        "source_options": source_options,
    }


async def get_project_complexity_scope(project_id, user):
    include_documents = True
    try:
        await get_project(project_id, user, "requirement_document.read")
    except HTTPException as error:
        if error.status_code != 403:
            raise
        include_documents = False
    scope = await _source_scope(
        project_id,
        user,
        include_documents=include_documents,
    )
    return {
        **scope["source_options"],
        "excluded": scope["excluded"],
        "document_count": scope["document_count"],
        "requirement_count": scope["requirement_count"],
    }


async def _claim_project_complexity_request(
    project_id, user, payload, fingerprint, output_language,
    *, result_type="PROJECT_COMPLEXITY_ASSESSMENT", request_context=None,
):
    request_values = {
            "actor_id": user.id,
            "source_fingerprint": fingerprint,
            "instruction": payload.instruction.strip(),
            "output_language": output_language,
        }
    if request_context is not None:
        request_values["context"] = request_context
    request_fingerprint = _fingerprint(request_values)
    claim_token = new_id("AIC")
    timestamp = now()
    reservation = {
        "_id": new_id("AIR"),
        "project_id": project_id,
        "result_type": f"{result_type}_PENDING",
        "idempotency_key": payload.idempotency_key,
        "request_fingerprint": request_fingerprint,
        "source_fingerprint": fingerprint,
        "output_language": output_language,
        "claim_token": claim_token,
        "lease_expires_at": timestamp + timedelta(minutes=35),
        "created_by": user.id,
        "created_at": timestamp,
    }
    try:
        await database.value.ai_results.insert_one(reservation)
        return reservation, None
    except DuplicateKeyError:
        existing = await database.value.ai_results.find_one(
            {"project_id": project_id, "idempotency_key": payload.idempotency_key}
        )
        if not existing or existing.get("request_fingerprint") != request_fingerprint:
            raise HTTPException(status_code=409, detail={"code": "PROJECT_COMPLEXITY_IDEMPOTENCY_KEY_REUSED"})
        if existing.get("result_type") == result_type:
            return None, existing
        if existing.get("result_type") != f"{result_type}_PENDING":
            raise HTTPException(status_code=409, detail={"code": "PROJECT_COMPLEXITY_RESERVATION_INVALID"})
        reclaimed = await database.value.ai_results.find_one_and_update(
            {
                "_id": existing["_id"],
                "result_type": f"{result_type}_PENDING",
                "lease_expires_at": {"$lte": timestamp},
            },
            {
                "$set": {
                    "claim_token": claim_token,
                    "lease_expires_at": timestamp + timedelta(minutes=35),
                    "updated_at": timestamp,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not reclaimed:
            raise HTTPException(
                status_code=409,
                detail={"code": "PROJECT_COMPLEXITY_ASSESSMENT_IN_PROGRESS", "retryable": True},
            )
        return reclaimed, None


async def assess_project_complexity(project_id, user, payload, *, output_language=None):
    scope = await _source_scope(
        project_id,
        user,
        include_text=True,
        document_ids=payload.document_ids,
        requirement_version_ids=payload.requirement_version_ids,
        include_documents=bool(payload.document_ids),
    )
    evidence = scope["evidence"]
    if not evidence:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_COMPLEXITY_EVIDENCE_REQUIRED", "excluded": scope["excluded"]})
    if len(evidence) > 100:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_COMPLEXITY_SOURCE_SCOPE_TOO_LARGE", "evidence_chunks": len(evidence), "maximum": 100},
        )
    project = await database.value.projects.find_one(
        {"_id": project_id}, {"locale": 1, "settings": 1}
    )
    locale = str(output_language or (project or {}).get("locale") or "").strip()
    if not locale:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_OUTPUT_LANGUAGE_REQUIRED"},
        )
    dimensions_config = resolve_project_complexity_dimensions(
        (project or {}).get("settings")
    )
    dimension_ids = {item["id"] for item in dimensions_config}
    rubric_fingerprint = _fingerprint(dimensions_config)
    request_fingerprint = _fingerprint(
        {"source_fingerprint": scope["fingerprint"], "rubric_fingerprint": rubric_fingerprint}
    )
    context = {
        "assessment_dimensions": dimensions_config,
        "source_coverage": {
            "current_ai_readable_documents": scope["document_count"],
            "baselined_requirements": scope["requirement_count"],
            "excluded_sources": scope["excluded"],
            "extraction_gaps": scope["extraction_gaps"],
            "historical_projects": "NOT_USED_NO_VALIDATED_ORG_POLICY",
        },
        "user_instruction": payload.instruction.strip(),
    }
    reservation, replay = await _claim_project_complexity_request(
        project_id, user, payload, request_fingerprint, locale
    )
    if replay:
        latest_scope = await _source_scope(
            project_id,
            user,
            document_ids=payload.document_ids,
            requirement_version_ids=payload.requirement_version_ids,
            include_documents=bool(payload.document_ids),
        )
        replay_dimensions = replay.get("complexity_dimensions") or resolve_project_complexity_dimensions({})
        if (
            latest_scope["fingerprint"] != scope["fingerprint"]
            or replay_dimensions != dimensions_config
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "PROJECT_COMPLEXITY_SOURCES_CHANGED", "retryable": True},
            )
        response = {**replay, "stale": False, "saved": True, "approved": False}
        response.pop("source_manifest", None)
        response.pop("claim_token", None)
        response.pop("lease_expires_at", None)
        labels = {item["id"]: item["label"] for item in dimensions_config}
        for item in (response.get("suggestions") or [{}])[0].get("dimensions") or []:
            item.setdefault("label", labels.get(item.get("dimension_id"), item.get("dimension_id")))
        response["commercial_feasibility"] = await _commercial_feasibility(project_id, user)
        return response
    try:
        result = await request_ai_automation(
            "project_complexity_assessment",
            project_id,
            json.dumps(context, ensure_ascii=False),
            evidence,
            output_language=locale,
        )
        if result.get("status") != "SUCCESS" or result.get("degraded_mode"):
            raise HTTPException(status_code=503, detail={"code": "AI_PROVIDER_UNAVAILABLE", "retryable": True})
        suggestions = result.get("suggestions") or []
        if len(suggestions) != 1:
            raise HTTPException(status_code=502, detail={"code": "PROJECT_COMPLEXITY_RESPONSE_INVALID"})
        suggestion = suggestions[0]
        dimensions = suggestion.get("dimensions") or []
        returned_dimension_ids = [item.get("dimension_id") for item in dimensions]
        if len(returned_dimension_ids) != len(dimension_ids) or set(returned_dimension_ids) != dimension_ids:
            raise HTTPException(status_code=502, detail={"code": "PROJECT_COMPLEXITY_DIMENSIONS_INVALID"})
        dimension_by_id = {item["id"]: item for item in dimensions_config}
        for dimension in dimensions:
            dimension["label"] = dimension_by_id[dimension["dimension_id"]]["label"]
            dimension["description"] = dimension_by_id[dimension["dimension_id"]]["description"]
        sources = {item["artifact_version_id"]: item for item in evidence}
        locale = locale.lower()
        insufficient_explanation = (
            "Không đủ dẫn chứng đã xác minh để đánh giá chiều này."
            if locale.startswith("vi")
            else "There is not enough verified source evidence to assess this dimension."
        )
        citations = []
        grounded_dimension_count = 0
        for dimension in dimensions:
            valid_quotes = []
            for quote in dimension.get("evidence_quotes") or []:
                source = sources.get(quote.get("evidence_ref"))
                text = str(quote.get("quote") or "").strip()
                if source and text and text in source["text"]:
                    valid_quotes.append({"evidence_ref": quote["evidence_ref"], "quote": text})
            dimension["evidence_quotes"] = valid_quotes
            if dimension.get("level") != "INSUFFICIENT_EVIDENCE" and valid_quotes:
                grounded_dimension_count += 1
            elif dimension.get("level") != "INSUFFICIENT_EVIDENCE":
                dimension["level"] = "INSUFFICIENT_EVIDENCE"
                dimension["explanation"] = insufficient_explanation
                dimension["confidence"] = 0
                dimension["uncertainty"] = list(dict.fromkeys([*(dimension.get("uncertainty") or []), "EVIDENCE_NOT_GROUNDED"]))
                dimension["testing_impacts"] = []
            for quote in valid_quotes:
                source = sources.get(quote["evidence_ref"])
                citations.append(
                    {
                        "evidence_ref": quote["evidence_ref"],
                        "artifact_type": source["artifact_type"],
                        "artifact_id": source["artifact_id"],
                        "source_version": source.get("source_version"),
                        "quote": quote["quote"],
                    }
                )
        if grounded_dimension_count < len(dimensions):
            if locale.startswith("vi"):
                suggestion["readiness_summary"] = (
                    f"Có đủ dẫn chứng đã xác minh cho {grounded_dimension_count} trên {len(dimensions)} chiều đánh giá; "
                    f"{len(dimensions) - grounded_dimension_count} chiều chưa đủ căn cứ."
                )
            else:
                suggestion["readiness_summary"] = (
                    f"Verified evidence supports {grounded_dimension_count} of {len(dimensions)} assessment dimensions; "
                    f"{len(dimensions) - grounded_dimension_count} dimensions lack sufficient evidence."
                )
        result["evidence_refs"] = list(
            dict.fromkeys(
                quote["evidence_ref"]
                for dimension in dimensions
                for quote in dimension.get("evidence_quotes") or []
            )
        )
        latest_scope = await _source_scope(
            project_id,
            user,
            document_ids=payload.document_ids,
            requirement_version_ids=payload.requirement_version_ids,
            include_documents=bool(payload.document_ids),
        )
        if latest_scope["fingerprint"] != scope["fingerprint"]:
            raise HTTPException(status_code=409, detail={"code": "PROJECT_COMPLEXITY_SOURCES_CHANGED", "retryable": True})
        latest_project = await database.value.projects.find_one(
            {"_id": project_id}, {"settings": 1}
        )
        latest_dimensions = resolve_project_complexity_dimensions(
            (latest_project or {}).get("settings")
        )
        if latest_dimensions != dimensions_config:
            raise HTTPException(
                status_code=409,
                detail={"code": "PROJECT_COMPLEXITY_RUBRIC_CHANGED", "retryable": True},
            )
        record = {
            **reservation,
            "result_type": "PROJECT_COMPLEXITY_ASSESSMENT",
            "candidate_only": True,
            "human_confirmation_required": True,
            "suggestions": suggestions,
            "citations": citations,
            "source_manifest": scope["manifest"],
            "source_selection": {
                "document_ids": payload.document_ids,
                "requirement_version_ids": payload.requirement_version_ids,
            },
            "source_fingerprint": scope["fingerprint"],
            "rubric_fingerprint": rubric_fingerprint,
            "complexity_dimensions": dimensions_config,
            "scope_summary": {
                "current_ai_readable_documents": scope["document_count"],
                "baselined_requirements": scope["requirement_count"],
                "excluded_sources": scope["excluded"],
                "extraction_gaps": scope["extraction_gaps"],
                "historical_projects": "NOT_USED_NO_VALIDATED_ORG_POLICY",
            },
            "created_at": now(),
            **ai_contract_metadata(result),
        }
        record.pop("lease_expires_at", None)
        persisted = await database.value.ai_results.replace_one(
            {"_id": reservation["_id"], "claim_token": reservation["claim_token"]},
            record,
        )
        if persisted.matched_count != 1:
            raise HTTPException(status_code=409, detail={"code": "PROJECT_COMPLEXITY_RESERVATION_EXPIRED", "retryable": True})
    except Exception:
        await database.value.ai_results.delete_one(
            {"_id": reservation["_id"], "claim_token": reservation["claim_token"]}
        )
        raise
    await audit(user.id, "project_complexity_assessed", "Project", project_id, project_id, {"result_id": record["_id"], "source_count": len(evidence)})
    response = {**record, "stale": False, "saved": True, "approved": False}
    response.pop("source_manifest", None)
    response.pop("claim_token", None)
    response.pop("lease_expires_at", None)
    response["commercial_feasibility"] = await _commercial_feasibility(project_id, user)
    return response


async def get_latest_project_complexity(project_id, user):
    project = await get_project(project_id, user, "ai.ask_project")
    record = await database.value.ai_results.find_one(
        {"project_id": project_id, "result_type": "PROJECT_COMPLEXITY_ASSESSMENT"},
        sort=[("created_at", -1)],
    )
    if not record:
        return None
    selection = record.get("source_selection") or {}
    try:
        scope = await _source_scope(
            project_id,
            user,
            document_ids=selection.get("document_ids"),
            requirement_version_ids=selection.get("requirement_version_ids"),
        include_documents=(
            selection.get("document_ids") is None or bool(selection.get("document_ids"))
        ),
        )
        current_dimensions = resolve_project_complexity_dimensions(
            project.get("settings")
        )
        stored_dimensions = record.get("complexity_dimensions") or resolve_project_complexity_dimensions({})
        stale = (
            scope["fingerprint"] != record.get("source_fingerprint")
            or current_dimensions != stored_dimensions
        )
    except HTTPException as error:
        error_detail = error.detail if isinstance(error.detail, dict) else {}
        inaccessible_selected_documents = (
            error_detail.get("code") == "PROJECT_PERMISSION_DENIED"
            and error_detail.get("permission") == "requirement_document.read"
        )
        if not inaccessible_selected_documents and error_detail.get("code") not in {
            "PROJECT_COMPLEXITY_SOURCE_SCOPE_UNAVAILABLE",
            "PROJECT_COMPLEXITY_SOURCE_SCOPE_CHANGED",
        }:
            raise
        stale = True
    if stale:
        record["citations"] = []
        record["suggestions"] = []
    else:
        labels = {
            item["id"]: item["label"]
            for item in resolve_project_complexity_dimensions(project.get("settings"))
        }
        for item in (record.get("suggestions") or [{}])[0].get("dimensions") or []:
            item.setdefault("label", labels.get(item.get("dimension_id"), item.get("dimension_id")))
    record.pop("source_manifest", None)
    record.pop("evidence_refs", None)
    record["stale"] = stale
    record["commercial_feasibility"] = await _commercial_feasibility(project_id, user)
    return record
