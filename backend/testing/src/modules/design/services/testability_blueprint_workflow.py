import hashlib
import json

from fastapi import HTTPException

from src.clients.ai_automation import ai_automation_client
from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.core.common import new_id, now
from src.core.database import database
from src.repositories.test_analysis import test_analysis_repository
from src.modules.design.services.test_evidence import requirement_test_evidence_text


def _source_hash(value, text):
    return str(
        value.get("normalized_content_hash")
        or value.get("content_hash")
        or hashlib.sha256(text.encode("utf-8")).hexdigest()
    )


def _requirement_snapshot(version, criteria):
    text = requirement_test_evidence_text(version).strip()
    if not text:
        raise HTTPException(422, detail={"code": "TEST_PLAN_REQUIREMENT_CONTENT_EMPTY"})
    version_id = str(version["_id"])
    items = [
        {
            "artifact_type": "REQUIREMENT_VERSION",
            "artifact_id": version_id,
            "artifact_version_id": version_id,
            "resolved_id": version_id,
            "source_version": str(version.get("version") or version.get("revision") or ""),
            "source_hash": _source_hash(version, text),
            "text": text,
        }
    ]
    for criterion in criteria:
        criterion_text = str(criterion.get("plain_text") or "").strip()
        if not criterion_text:
            continue
        criterion_id = str(criterion["_id"])
        items.append(
            {
                "artifact_type": "ACCEPTANCE_CRITERION",
                "artifact_id": criterion_id,
                "artifact_version_id": criterion_id,
                "resolved_id": criterion_id,
                "source_version": str(criterion.get("revision") or ""),
                "source_hash": _source_hash(criterion, criterion_text),
                "text": criterion_text,
            }
        )
    return items


def _relevant_blueprint(blueprint, allowed_refs):
    return {
        **blueprint,
        "obligations": [
            item
            for item in blueprint.get("obligations", [])
            if str(item.get("source_ref") or "") in allowed_refs
        ],
        "clarifications": [
            item
            for item in blueprint.get("clarifications", [])
            if set(map(str, item.get("evidence_refs") or [])) & allowed_refs
        ],
        "evidence_refs": [
            str(item) for item in blueprint.get("evidence_refs", [])
            if str(item) in allowed_refs
        ],
    }


def _blueprint_hash(blueprint):
    value = json.dumps(blueprint, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _evaluate_blueprint_reference(project_id, requester_user_id, snapshots, blueprint):
    try:
        return await ai_automation_client.evaluate_blueprint_against_reference(
            project_id,
            str(requester_user_id),
            [
                {
                    "source_id": item["artifact_id"],
                    "artifact_type": item["artifact_type"].lower(),
                    "artifact_version_id": item["artifact_version_id"],
                    "authority": "APPROVED_SOURCE",
                    "text": item["text"],
                }
                for item in snapshots
            ],
            blueprint,
        )
    except Exception as error:
        return {
            "assessment_type": "NOT_AVAILABLE",
            "independently_validated": False,
            "reason": "Không thể hoàn tất truy vấn Benchmark; Blueprint vẫn được giữ để tiếp tục quy trình.",
            "reason_code": f"BENCHMARK_LOOKUP_{type(error).__name__.upper()}",
        }


async def blueprint_for_requirement(project_id, version, criteria, mode, user):
    """Return only a Blueprint bound to this exact Requirement version; OFF never reads it."""
    if mode == "OFF":
        return None
    if mode not in {"BLUEPRINT_ONLY", "BLUEPRINT_BENCHMARK"}:
        raise HTTPException(422, detail={"code": "TESTABILITY_MODE_INVALID"})

    from src.modules.design.services.test_analysis import (
        _automation_instruction,
        _blueprint_evidence,
        _bounded_blueprint_context,
        _compile_user_blueprint,
        _run_blueprint_review,
    )

    snapshots = _requirement_snapshot(version, criteria)
    version_id = str(version["_id"])
    saved = await test_analysis_repository.find_blueprint_for_sources(
        project_id, snapshots
    )
    blueprint = None
    review = None
    metadata = {}
    created = False
    metadata_changed = False
    result_id = None
    if saved:
        result_id = saved.get("_id")
        blueprint = _relevant_blueprint(
            saved.get("testability_blueprint") or {},
            {item["artifact_version_id"] for item in snapshots},
        )
        review = saved.get("blueprint_self_review")
        metadata = dict(saved.get("blueprint_ai_metadata") or {})
        if not blueprint.get("obligations") and not blueprint.get("clarifications"):
            blueprint = None

    if blueprint is None:
        evidence, source_text_by_ref = _blueprint_evidence(snapshots)
        blueprint, compilation = await _compile_user_blueprint(
            project_id, evidence, source_text_by_ref
        )
        metadata = {"compilation": ai_contract_metadata(compilation)}
        created = True
    else:
        evidence, source_text_by_ref = _blueprint_evidence(snapshots)

    before_review = None
    if mode == "BLUEPRINT_BENCHMARK" and not review:
        before_review = blueprint
        review, review_result = await _run_blueprint_review(
            project_id, blueprint, evidence, source_text_by_ref
        )
        metadata["self_review"] = ai_contract_metadata(review_result)
        metadata_changed = True
        suggestions = list(review.get("improvement_suggestions") or [])
        suggestions.extend(
            str(item.get("suggested_change") or "")
            for item in review.get("findings", [])
            if item.get("suggested_change")
        )
        suggestions = list(dict.fromkeys(item.strip() for item in suggestions if item.strip()))[:50]
        if suggestions:
            instruction = _automation_instruction(
                {
                    "task": "Refine this Blueprint once using only the cited findings and source evidence. Keep supported items, preserve exact citations, do not add unstated behavior, and do not resolve conflicts by choosing a source.",
                    "current_blueprint": _bounded_blueprint_context(blueprint),
                    "review_findings": review.get("findings", []),
                    "improvement_suggestions": suggestions,
                }
            )
            blueprint, refinement = await _compile_user_blueprint(
                project_id, evidence, source_text_by_ref, instruction
            )
            metadata["refinement"] = ai_contract_metadata(refinement)
            metadata_changed = True

    benchmark = None
    if mode == "BLUEPRINT_BENCHMARK":
        saved_metadata = (saved or {}).get("blueprint_ai_metadata", {})
        benchmark = saved_metadata.get("benchmark")
        if saved_metadata.get("benchmark_blueprint_hash") != _blueprint_hash(blueprint):
            benchmark = await _evaluate_blueprint_reference(
                project_id, user.id, snapshots, blueprint
            )
            metadata["benchmark"] = benchmark
            metadata["benchmark_blueprint_hash"] = _blueprint_hash(blueprint)
            metadata_changed = True

    if created or metadata_changed or not saved:
        result_id = new_id("AIR")
        stored = {
            "_id": result_id,
            "project_id": project_id,
            "result_type": "TESTABILITY_BLUEPRINT",
            "testability_mode": mode,
            "testability_blueprint": blueprint,
            "testability_blueprint_before_review": before_review,
            "blueprint_self_review": (
                {"assessment_type": "SELF_REVIEW", "independently_validated": False, **review}
                if review
                else None
            ),
            "blueprint_ai_metadata": metadata,
            "basis_snapshots": snapshots,
            "requirement_version_id": version_id,
            "candidate_only": True,
            "created_by": user.id,
            "created_at": now(),
        }
        await database.value.ai_results.insert_one(stored)

    return {
        "blueprint_result_id": result_id,
        "blueprint": blueprint,
        "blueprint_before_review": before_review or (saved or {}).get("testability_blueprint_before_review"),
        "self_review": review,
        "benchmark": benchmark,
        "metadata": metadata,
    }
