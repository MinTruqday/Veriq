import json
import hashlib

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.repositories.test_design import test_design_repository
from src.core.ai_automation import (
    ai_contract_metadata,
    request_ai_automation,
    require_ai_automation_event,
)
from src.modules.quality.services.non_functional_test import get_plan as get_non_functional_plan
from src.modules.design.services.generation import validated_suggestions
from src.schemas.contracts.environment import PerformancePlanDraftInput
from src.schemas.test_analysis import PerformanceScenario, SecurityCandidate


async def requirement_evidence(project_id, requirement_version_ids):
    
    query = {"project_id": project_id}
    if requirement_version_ids:
        query["_id"] = {"$in": list(dict.fromkeys(requirement_version_ids))}
    versions = await test_design_repository.list_requirement_evidence(
        query, 500
    )
    if requirement_version_ids and len(versions) != len(set(requirement_version_ids)):
        raise HTTPException(status_code=422, detail={"code": "INVALID_REQUIREMENT_VERSION"})
    return versions, [
        {
            "artifact_type": "requirement_version",
            "artifact_id": item.get("requirement_id"),
            "artifact_version_id": item["_id"],
            "authority": item.get("status") or "PROJECT_REQUIREMENT_VERSION",
            "text": " ".join(
                filter(
                    None,
                    [str(item.get("title") or ""), str(item.get("plain_text_projection") or "")],
                )
            )[: 4000],
        }
        for item in versions
    ]


def performance_targets_match(scenarios, payload):
    return all(
        item["virtual_users"] == payload.target_virtual_users
        and item["duration_minutes"] == payload.duration_minutes
        and item["requests_per_second"] == payload.target_requests_per_second
        for item in scenarios
    )


def approved_performance_configuration_inputs(plan):
    workload_sections = ("baseline", "load", "stress", "spike", "soak")
    workload_types = [
        field
        for field in workload_sections
        if isinstance(plan.get(field), dict) and bool(plan[field])
    ]
    concurrency = plan.get("concurrency")
    target_virtual_users = (
        concurrency if type(concurrency) is int and concurrency > 0 else None
    )
    duration_minutes = plan.get("duration_minutes")
    if type(duration_minutes) is not int or duration_minutes < 1:
        duration_minutes = None
    requirement_refs = list(dict.fromkeys(plan.get("requirement_refs") or []))
    missing = []
    if not workload_types:
        missing.append("phần tải được cấu hình (baseline, load, stress, spike hoặc soak)")
    if target_virtual_users is None:
        missing.append("concurrency dạng số nguyên dương")
    if duration_minutes is None:
        missing.append("duration_minutes")
    if not requirement_refs:
        missing.append("Requirement version liên kết làm căn cứ")
    throughput_target = plan.get("throughput_target")
    if (
        not isinstance(throughput_target, (int, float))
        or isinstance(throughput_target, bool)
        or throughput_target <= 0
    ):
        throughput_target = None
    return {
        "workload_types": workload_types,
        "target_virtual_users": target_virtual_users,
        "duration_minutes": duration_minutes,
        "requirement_version_ids": requirement_refs,
        "target_requests_per_second": throughput_target,
        "workload_configuration": {
            field: plan[field] for field in workload_types
        },
    }, missing


class DesignSuggestionService:
    @staticmethod
    async def list_security(project_id, user):
        await get_project(project_id, user, "ai.generate_security_tests")
        return await test_design_repository.list_security_suggestions(
            project_id, 200
        )

    @staticmethod
    async def generate_security(project_id, payload, user):
        automation = require_ai_automation_event(user, {"REQUIREMENT_CHANGED"})
        await get_project(project_id, user, "ai.generate_security_tests")
        versions, evidence = await requirement_evidence(project_id, payload.requirement_version_ids)
        if (
            not payload.source_event_id
            or payload.source_event_revision is None
            or payload.source_event_id != automation["source_event_id"]
            or len(versions) != 1
        ):
            raise HTTPException(403, detail={"code": "VERIFIED_REQUIREMENT_EVENT_REQUIRED"})
        version = versions[0]
        requirement = await test_design_repository.find_current_requirement(
            project_id, version.get("requirement_id")
        )
        expected_event_id = (
            f"requirement-version:{version['_id']}:{payload.source_event_revision}:BASELINED"
        )
        if (
            version.get("status") != "BASELINED"
            or requirement is None
            or requirement.get("current_version_id") != version["_id"]
            or int(version.get("revision") or 0) != payload.source_event_revision
            or payload.source_event_id != expected_event_id
        ):
            raise HTTPException(409, detail={"code": "REQUIREMENT_EVENT_SOURCE_CHANGED"})
        expected_key = "security-requirement:" + hashlib.sha256(
            f"{payload.source_event_id}:{version['_id']}".encode("utf-8")
        ).hexdigest()
        if payload.idempotency_key != expected_key:
            raise HTTPException(422, detail={"code": "SECURITY_SUGGESTION_EVENT_KEY_INVALID"})
        existing = await test_design_repository.find_security_suggestion(
            project_id, payload.idempotency_key
        )
        if existing:
            if (
                existing.get("source_event_id") != payload.source_event_id
                or existing.get("source_event_revision") != payload.source_event_revision
                or existing.get("requirement_version_ids") != [versions[0]["_id"]]
            ):
                raise HTTPException(409, detail={"code": "SECURITY_SUGGESTION_EVENT_KEY_CONFLICT"})
            return existing, {}
        ai_result = await request_ai_automation(
            "security_test_generation",
            project_id,
            json.dumps({"categories": payload.categories}, ensure_ascii=False),
            evidence
            + [
                {
                    "artifact_type": "design_request",
                    "artifact_id": payload.idempotency_key,
                    "authority": "USER_REQUEST",
                    "text": json.dumps(
                        {"categories": payload.categories, "context": payload.context},
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        candidates = validated_suggestions(
            ai_result,
            SecurityCandidate,
            allow_empty=not payload.categories,
        )
        version_ids = {item["_id"] for item in versions}
        source_text_by_version = {
            item["_id"]: " ".join(
                filter(
                    None,
                    [str(item.get("title") or ""), str(item.get("plain_text_projection") or "")],
                )
            )
            for item in versions
        }
        requested_categories_match = (
            {item["category"] for item in candidates} == set(payload.categories)
            if payload.categories
            else all(item["category"] in {
                "authorization", "authentication", "input_validation", "session", "data_protection"
            } for item in candidates)
        )
        if not requested_categories_match or any(
            not item["requirement_version_ids"]
            or not set(item["requirement_version_ids"]) <= version_ids
            or not item["evidence_quotes"]
            or any(
                quote["evidence_ref"] not in item["requirement_version_ids"]
                or quote["evidence_ref"] not in source_text_by_version
                or quote["quote"].strip() not in source_text_by_version[quote["evidence_ref"]]
                for quote in item["evidence_quotes"]
            )
            for item in candidates
        ):
            raise HTTPException(502, detail={"code": "AI_GENERATION_INVALID"})
        candidates = [
            {
                **item,
                "candidate_id": f"{'SEC-'}{index}",
                "status": 'SUGGESTED',
                "origin": 'ai_generated',
            }
            for index, item in enumerate(candidates, 1)
        ]
        timestamp = now()
        ai_contract = ai_contract_metadata(ai_result)
        result = {
            "_id": new_id('SECSUG'),
            "project_id": project_id,
            "result_type": 'SECURITY_TEST_SUGGESTION',
            "categories": payload.categories,
            "requirement_version_ids": [item["_id"] for item in versions],
            "source_event_id": payload.source_event_id,
            "source_event_revision": payload.source_event_revision,
            "candidates": candidates,
            "model_suggestions": ai_result.get("suggestions", []),
            **ai_contract,
            "ai_contract": ai_contract,
            "ai_status": ai_contract["status"],
            "latency_ms": ai_result.get("latency_ms"),
            "status": 'PENDING_REVIEW',
            "generation_status": ai_result.get("status", 'SUCCESS'),
            "candidate_only": True,
            "vulnerability_scan_performed": False,
            "human_confirmation_required": True,
            "idempotency_key": payload.idempotency_key,
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await test_design_repository.insert_security_suggestion(result)
        except DuplicateKeyError:
            existing = await test_design_repository.find_security_suggestion(
                project_id, payload.idempotency_key
            )
            if existing:
                return existing, {}
            raise
        await audit(
            user.id,
            "security_test_suggestions_generated",
            "SecurityTestSuggestion",
            result["_id"],
            project_id,
            {"candidate_count": len(result["candidates"])},
        )
        return result, {
            "status": ai_result.get("status", 'SUCCESS'),
            "degraded_mode": ai_result.get("degraded_mode"),
        }

    @staticmethod
    async def list_performance(project_id, user):
        await get_project(project_id, user, "ai.generate_performance_plan")
        return await test_design_repository.list_performance_drafts(
            project_id, 200
        )

    @staticmethod
    async def generate_performance(project_id, payload, user, source_configuration=None):
        automation = require_ai_automation_event(user, {"PERFORMANCE_CONFIGURATION_APPROVED"})
        if (
            not source_configuration
            or source_configuration.get("event_id") != automation["source_event_id"]
        ):
            raise HTTPException(status_code=403, detail={"code": "VERIFIED_PERFORMANCE_CONFIGURATION_EVENT_REQUIRED"})
        await get_project(project_id, user, "ai.generate_performance_plan")
        existing = await test_design_repository.find_performance_draft(
            project_id, payload.idempotency_key
        )
        if existing:
            if source_configuration and (
                existing.get("source_configuration_id") != source_configuration["plan_id"]
                or existing.get("source_event_id") != source_configuration["event_id"]
                or existing.get("source_event_revision") != source_configuration["revision"]
            ):
                raise HTTPException(409, detail={"code": "PERFORMANCE_EVENT_IDEMPOTENCY_CONFLICT"})
            return existing, {}
        versions, evidence = await requirement_evidence(project_id, payload.requirement_version_ids)
        ai_result = await request_ai_automation(
            "performance_plan_generation",
            project_id,
            json.dumps(
                {
                    "workload_types": payload.workload_types,
                    "target_virtual_users": payload.target_virtual_users,
                    "target_requests_per_second": payload.target_requests_per_second,
                    "duration_minutes": payload.duration_minutes,
                    "objective": payload.objective,
                },
                ensure_ascii=False,
            ),
            evidence
            + [
                {
                    "artifact_type": "design_request",
                    "artifact_id": payload.idempotency_key,
                    "authority": "USER_REQUEST",
                    "text": json.dumps(
                        {
                            "objective": payload.objective,
                            "workload_types": payload.workload_types,
                            "target_virtual_users": payload.target_virtual_users,
                            "target_requests_per_second": payload.target_requests_per_second,
                            "duration_minutes": payload.duration_minutes,
                            "context": payload.context,
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        generated_scenarios = ai_result.get("suggestions", [])
        if any(
            item.get("virtual_users") is None
            or item.get("duration_minutes") is None
            or (
                payload.target_requests_per_second is not None
                and item.get("requests_per_second") is None
            )
            for item in generated_scenarios
            if isinstance(item, dict)
        ):
            raise HTTPException(
                422,
                detail={
                    "code": "PERFORMANCE_TARGETS_MISSING",
                    "message": "Nguồn chưa cung cấp đủ thông số tải để tạo kế hoạch có căn cứ.",
                },
            )
        scenarios = validated_suggestions(ai_result, PerformanceScenario)
        if {item["workload_type"] for item in scenarios} != set(payload.workload_types):
            raise HTTPException(502, detail={"code": "AI_GENERATION_INVALID"})
        if not performance_targets_match(scenarios, payload):
            raise HTTPException(
                502,
                detail={
                    "code": "AI_PERFORMANCE_TARGET_MISMATCH",
                    "message": "AI đã đề xuất thông số tải khác với mục tiêu đã được cung cấp.",
                },
            )
        scenarios = [
            {**item, "scenario_id": f"{'PERF-'}{index}"}
            for index, item in enumerate(scenarios, 1)
        ]
        timestamp = now()
        ai_contract = ai_contract_metadata(ai_result)
        result = {
            "_id": new_id('PERFPLAN'),
            "project_id": project_id,
            "name": payload.name,
            "objective": payload.objective,
            "requirement_version_ids": [item["_id"] for item in versions],
            "workload": {
                "target_virtual_users": payload.target_virtual_users,
                "target_requests_per_second": payload.target_requests_per_second,
                "duration_minutes": payload.duration_minutes,
            },
            "scenarios": scenarios,
            "metrics": [
                {"key": 'response_time_p95_ms', "threshold": payload.response_time_p95_ms},
                {"key": 'error_rate', "threshold": payload.maximum_error_rate},
                {"key": 'throughput', "threshold": payload.target_requests_per_second},
            ],
            "model_suggestions": ai_result.get("suggestions", []),
            **ai_contract,
            "ai_contract": ai_contract,
            "ai_status": ai_contract["status"],
            "latency_ms": ai_result.get("latency_ms"),
            "status": 'DRAFT',
            "generation_status": ai_result.get("status", 'SUCCESS'),
            "load_execution_performed": False,
            "human_confirmation_required": True,
            **(
                {
                    "source_configuration_id": source_configuration["plan_id"],
                    "source_event_id": source_configuration["event_id"],
                    "source_event_revision": source_configuration["revision"],
                }
                if source_configuration
                else {}
            ),
            "idempotency_key": payload.idempotency_key,
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await test_design_repository.insert_performance_draft(result)
        except DuplicateKeyError:
            existing = await test_design_repository.find_performance_draft(
                project_id, payload.idempotency_key
            )
            if existing:
                return existing, {}
            raise
        await audit(
            user.id,
            "performance_plan_draft_generated",
            "PerformanceTestPlanDraft",
            result["_id"],
            project_id,
            {"scenario_count": len(result["scenarios"])},
        )
        return result, {
            "status": ai_result.get("status", 'SUCCESS'),
            "degraded_mode": ai_result.get("degraded_mode"),
        }

    @staticmethod
    async def generate_performance_from_approved_configuration(project_id, payload, user):
        if (
            not getattr(user, "_ai_automation_run_id", "")
            or getattr(user, "_ai_automation_trigger", "")
            != "PERFORMANCE_CONFIGURATION_APPROVED"
            or getattr(user, "_ai_automation_source_event_id", "")
            != payload.source_event_id
        ):
            raise HTTPException(
                status_code=403,
                detail={"code": "VERIFIED_PERFORMANCE_CONFIGURATION_EVENT_REQUIRED"},
            )
        await get_project(project_id, user, "ai.generate_performance_plan")
        plan = await get_non_functional_plan(payload.plan_id, user, "nfrtest.read")
        if (
            plan.get("project_id") != project_id
            or plan.get("plan_type") != "PERFORMANCE_TEST_PLAN"
            or plan.get("status") != "APPROVED"
            or plan.get("revision") != payload.source_event_revision
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "APPROVED_PERFORMANCE_CONFIGURATION_CHANGED"},
            )
        expected_event_id = (
            f"performance-configuration:{payload.plan_id}:{payload.source_event_revision}:"
            "PERFORMANCE_CONFIGURATION_APPROVED"
        )
        if payload.source_event_id != expected_event_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "PERFORMANCE_CONFIGURATION_EVENT_ID_MISMATCH"},
            )

        inputs, missing = approved_performance_configuration_inputs(plan)
        if missing:
            return {
                "status": "automation_waiting_for_input",
                "reason_code": "CLARIFICATION_REQUIRED",
                "source_configuration_id": payload.plan_id,
                "source_event_id": payload.source_event_id,
                "source_event_revision": payload.source_event_revision,
                "missing_inputs": missing,
                "question": (
                    "Tạo cấu hình hiệu năng mới, bổ sung các đầu vào còn thiếu rồi duyệt lại: "
                    + "; ".join(missing)
                    + "."
                ),
            }

        versions, _ = await requirement_evidence(
            project_id, inputs["requirement_version_ids"]
        )
        if not versions:
            return {
                "status": "automation_waiting_for_input",
                "reason_code": "CLARIFICATION_REQUIRED",
                "source_configuration_id": payload.plan_id,
                "source_event_id": payload.source_event_id,
                "source_event_revision": payload.source_event_revision,
                "missing_inputs": ["nội dung Requirement version có thể đọc được"],
                "question": "Liên kết Requirement version có tồn tại và được phép đọc không?",
            }

        idempotency_key = "performance-configuration:" + hashlib.sha256(
            f"{payload.source_event_id}:{payload.plan_id}".encode("utf-8")
        ).hexdigest()
        request = PerformancePlanDraftInput(
            name=plan["name"],
            objective=plan["objective"],
            requirement_version_ids=inputs["requirement_version_ids"],
            workload_types=inputs["workload_types"],
            target_virtual_users=inputs["target_virtual_users"],
            target_requests_per_second=inputs["target_requests_per_second"],
            duration_minutes=inputs["duration_minutes"],
            context=json.dumps(
                {
                    "approved_source_configuration_id": payload.plan_id,
                    "approved_workload_configuration": inputs["workload_configuration"],
                },
                ensure_ascii=False,
                default=str,
            ),
            idempotency_key=idempotency_key,
        )
        result, metadata = await DesignSuggestionService.generate_performance(
            project_id,
            request,
            user,
            source_configuration={
                "plan_id": payload.plan_id,
                "event_id": payload.source_event_id,
                "revision": payload.source_event_revision,
            },
        )
        return {"status": "completed", "draft": result, "metadata": metadata}
