import json

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.repositories.test_design import test_design_repository
from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.modules.design.services.generation import PerformanceScenario, SecurityCandidate, validated_suggestions


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


class DesignSuggestionService:
    @staticmethod
    async def list_security(project_id, user):
        await get_project(project_id, user, "ai.generate_security_tests")
        return await test_design_repository.list_security_suggestions(
            project_id, 200
        )

    @staticmethod
    async def generate_security(project_id, payload, user):
        
        await get_project(project_id, user, "ai.generate_security_tests")
        existing = await test_design_repository.find_security_suggestion(
            project_id, payload.idempotency_key
        )
        if existing:
            return existing, {}
        versions, evidence = await requirement_evidence(project_id, payload.requirement_version_ids)
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
        candidates = validated_suggestions(ai_result, SecurityCandidate)
        version_ids = {item["_id"] for item in versions}
        if {item["category"] for item in candidates} != set(payload.categories) or any(
            not set(item["requirement_version_ids"]) <= version_ids for item in candidates
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
    async def generate_performance(project_id, payload, user):
        
        await get_project(project_id, user, "ai.generate_performance_plan")
        existing = await test_design_repository.find_performance_draft(
            project_id, payload.idempotency_key
        )
        if existing:
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
        scenarios = validated_suggestions(ai_result, PerformanceScenario)
        if {item["workload_type"] for item in scenarios} != set(payload.workload_types):
            raise HTTPException(502, detail={"code": "AI_GENERATION_INVALID"})
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
