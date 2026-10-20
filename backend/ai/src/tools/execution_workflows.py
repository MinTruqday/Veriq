import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.prompts.defect_analysis import causal_hypothesis_instruction
from src.tools.registry import with_tool_access
from src.tools.testing import AutomationOperationError, call, parse, require_operation

@with_tool_access(("analysis",), "MUTATE", "causalanalysis.create", owner_domain="analysis")
async def process_recorded_defect(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    defect_id: Annotated[str, Field(min_length=1, description="Verified defect identifier")],
    config: RunnableConfig = None,
) -> str:
    """Create an idempotent defect-analysis record, generate hypotheses, and verify the saved record"""
    configurable = (config or {}).get("configurable", {})
    execution_user_id = configurable.get("user_id")
    automation_run_id = configurable.get("automation_run_id")
    permissions = set(configurable.get("permissions", []))
    if not execution_user_id or not automation_run_id:
        return json.dumps({"status": "automation_blocked", "reason_code": "AUTOMATION_IDENTITY_REQUIRED"})
    if "causalanalysis.update" not in permissions:
        return json.dumps({"status": "automation_blocked", "reason_code": "CAUSAL_ANALYSIS_UPDATE_PERMISSION_REQUIRED"})
    source = next(
        (
            item for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and str(item.get("artifact_type", "")).casefold() == "defect"
            and defect_id in {
                str(item.get("artifact_id") or ""),
                str(item.get("artifact_version_id") or ""),
            }
        ),
        None,
    )
    if not source or not str(source.get("text") or "").strip():
        return json.dumps({"status": "automation_blocked", "reason_code": "DEFECT_SOURCE_EVIDENCE_REQUIRED"})
    evidence_ref = str(source.get("artifact_version_id") or source.get("artifact_id"))
    idempotency_key = f"ai-automation-{automation_run_id}"
    analysis = parse(await call(
        "POST",
        f"/du-an/{project_id}/phan-tich-nguyen-nhan",
        config,
        {
            "idempotency_key": idempotency_key,
            "defect_ids": [defect_id],
            "problem_statement": str(source["text"]).strip(),
            "evidence_refs": [evidence_ref],
            "owner_id": execution_user_id,
        },
    ))
    if not analysis or not analysis.get("_id"):
        return json.dumps({"status": "automation_partial_failure", "reason_code": "CAUSAL_ANALYSIS_CREATE_FAILED"})
    analysis_id = str(analysis["_id"])
    hypotheses = parse(await call(
        "POST",
        f"/phan-tich-nguyen-nhan/{analysis_id}/ai/goi-y",
        config,
        {
            "idempotency_key": idempotency_key,
            "instruction": causal_hypothesis_instruction(),
        },
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    ))
    if not hypotheses or hypotheses.get("status") == "qa_operation_failed":
        return json.dumps({"status": "automation_partial_failure", "analysis_id": analysis_id, "reason_code": "CAUSAL_HYPOTHESES_FAILED"})
    readback = parse(await call("GET", f"/phan-tich-nguyen-nhan/{analysis_id}", config))
    if not readback or readback.get("_id") != analysis_id or readback.get("project_id") != project_id:
        return json.dumps({"status": "automation_partial_failure", "analysis_id": analysis_id, "reason_code": "CAUSAL_ANALYSIS_READBACK_FAILED"})
    return json.dumps({
        "status": "completed",
        "analysis_id": analysis_id,
        "analysis_status": readback.get("status"),
        "hypothesis_result_id": hypotheses.get("_id"),
        "candidate_only": hypotheses.get("candidate_only", True),
        "verification": {
            "status": "COMPLETED",
            "project_id": project_id,
            "artifact_ids": [analysis_id, *([str(hypotheses["_id"])] if hypotheses.get("_id") else [])],
            "checks": ["causal_analysis_readback", "project_scope", "source_evidence"],
        },
    }, ensure_ascii=False, default=str)


@with_tool_access(("execution",), "MUTATE", "testrun.create", owner_domain="execution")
async def process_approved_test_plan(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    test_plan_id: Annotated[str, Field(min_length=1, description="Approved Test Plan identifier")],
    config: RunnableConfig = None,
) -> str:
    """Create an idempotent Test Run from an approved immutable Test Plan and verify the run"""
    configurable = (config or {}).get("configurable", {})
    automation_run_id = configurable.get("automation_run_id")
    permissions = set(configurable.get("permissions", []))
    if not automation_run_id:
        return json.dumps({"status": "automation_blocked", "reason_code": "AUTOMATION_RUN_REQUIRED"})
    plan_source = next(
        (
            item for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_plan"
            and str(item.get("artifact_id") or "") == test_plan_id
        ),
        None,
    )
    if not plan_source:
        return json.dumps({"status": "automation_blocked", "reason_code": "TEST_PLAN_EVENT_EVIDENCE_REQUIRED"})
    plan = parse(await call("GET", f"/ke-hoach-kiem-thu/{test_plan_id}", config))
    if not plan or plan.get("project_id") != project_id or plan.get("status") != "APPROVED":
        return json.dumps({"status": "automation_blocked", "reason_code": "APPROVED_TEST_PLAN_REQUIRED"})
    snapshot = plan.get("approved_snapshot") or plan
    version_ids = list(dict.fromkeys(snapshot.get("test_case_version_ids") or []))
    if not version_ids:
        return json.dumps({"status": "automation_blocked", "reason_code": "APPROVED_TEST_PLAN_SCOPE_EMPTY"})
    if "testrun.execute" not in permissions:
        return json.dumps({"status": "automation_blocked", "reason_code": "TEST_RUN_EXECUTION_PERMISSION_REQUIRED"})
    return await _start_test_run_from_approved_plan(
        project_id, test_plan_id, plan, snapshot, automation_run_id, config
    )


async def _start_test_run_from_approved_plan(
    project_id: str,
    test_plan_id: str,
    plan: dict,
    snapshot: dict,
    automation_run_id: str,
    config: RunnableConfig,
) -> str:
    configurable = (config or {}).get("configurable", {})
    permissions = set(configurable.get("permissions", []))
    if "testrun.create" not in permissions or "testrun.execute" not in permissions:
        return json.dumps({"status": "automation_blocked", "reason_code": "TEST_RUN_PERMISSION_REQUIRED"})
    version_ids = list(dict.fromkeys(snapshot.get("test_case_version_ids") or []))
    if not version_ids:
        return json.dumps({"status": "automation_blocked", "reason_code": "APPROVED_TEST_PLAN_SCOPE_EMPTY"})
    payload = {
        "project_id": project_id,
        "name": f"{plan.get('name') or test_plan_id} - lần chạy tự động",
        "test_plan_id": test_plan_id,
        "test_case_version_ids": version_ids,
        "environment": snapshot.get("environment") or "",
        "environment_id": snapshot.get("environment_id"),
        "release": snapshot.get("release") or "",
        "release_id": snapshot.get("release_id"),
        "build": snapshot.get("build") or "",
        "build_id": snapshot.get("build_id"),
        "idempotency_key": f"ai-automation-{automation_run_id}",
    }
    run = parse(await call("POST", f"/du-an/{project_id}/lan-chay-kiem-thu", config, payload))
    if not run or not run.get("_id"):
        return json.dumps({"status": "automation_partial_failure", "reason_code": "TEST_RUN_CREATE_FAILED"})
    run_id = str(run["_id"])
    if run.get("status") in {"DRAFT", "READY"}:
        started = parse(await call("POST", f"/lan-chay-kiem-thu/{run_id}/bat-dau", config))
        if not started or started.get("status") != "IN_PROGRESS":
            return json.dumps({"status": "automation_partial_failure", "test_run_id": run_id, "reason_code": "TEST_RUN_START_FAILED"})
    readback = parse(await call("GET", f"/lan-chay-kiem-thu/{run_id}", config))
    if (
        not readback
        or readback.get("_id") != run_id
        or readback.get("project_id") != project_id
        or readback.get("test_plan_id") != test_plan_id
        or readback.get("status") not in {"IN_PROGRESS", "COMPLETED"}
        or set(readback.get("test_case_version_ids", [])) != set(version_ids)
    ):
        return json.dumps({"status": "automation_partial_failure", "test_run_id": run_id, "reason_code": "TEST_RUN_READBACK_MISMATCH"})
    return json.dumps({
        "status": "completed",
        "test_run_id": run_id,
        "test_plan_id": test_plan_id,
        "status_after_start": readback.get("status"),
        "test_case_version_ids": readback.get("test_case_version_ids", []),
        "verification": {
            "status": "COMPLETED",
            "project_id": project_id,
            "artifact_ids": [test_plan_id, run_id],
            "checks": ["approved_plan", "approved_scope", "run_started", "run_readback"],
        },
    }, ensure_ascii=False, default=str)


@with_tool_access(("execution",), "MUTATE", "testplan.approve", owner_domain="execution")
async def process_changed_test_plan(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    test_plan_id: Annotated[str, Field(min_length=1, description="Test Plan identifier from the verified project event")],
    config: RunnableConfig = None,
) -> str:
    """Validate a changed Test Plan, approve it as the project's QA principal when complete, then create, start, and verify its Test Run"""
    configurable = (config or {}).get("configurable", {})
    automation_run_id = configurable.get("automation_run_id")
    permissions = set(configurable.get("permissions", []))
    event_evidence = next(
        (
            item for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_plan"
            and str(item.get("artifact_id") or "") == test_plan_id
        ),
        None,
    )
    if not automation_run_id or not event_evidence:
        return json.dumps({"status": "automation_blocked", "reason_code": "VERIFIED_TEST_PLAN_EVENT_REQUIRED"})
    if "testplan.approve" not in permissions:
        return json.dumps({"status": "automation_blocked", "reason_code": "TEST_PLAN_APPROVAL_PERMISSION_REQUIRED"})

    plan = parse(await call("GET", f"/ke-hoach-kiem-thu/{test_plan_id}", config))
    if not plan or plan.get("project_id") != project_id:
        return json.dumps({"status": "automation_blocked", "reason_code": "TEST_PLAN_PROJECT_SCOPE_INVALID"})
    status = plan.get("status")
    if status != "APPROVED":
        if status not in {"DRAFT", "IN_REVIEW"}:
            return json.dumps({"status": "automation_blocked", "reason_code": "TEST_PLAN_NOT_APPROVABLE"})
        if not plan.get("test_case_version_ids"):
            return json.dumps({"status": "automation_blocked", "reason_code": "TEST_PLAN_TEST_CASE_SCOPE_EMPTY"})
        validation = parse(
            await call("POST", f"/ke-hoach-kiem-thu/{test_plan_id}/kiem-tra", config)
        )
        if not validation or validation.get("ready_for_approval") is not True:
            return json.dumps({
                "status": "automation_blocked",
                "reason_code": "TEST_PLAN_INCOMPLETE",
                "findings": (validation or {}).get("findings", []),
            }, ensure_ascii=False)
        approved = parse(
            await call(
                "POST",
                f"/ke-hoach-kiem-thu/{test_plan_id}/phe-duyet",
                config,
                {
                    "expected_revision": plan.get("revision"),
                    "review_note": "Tự động duyệt sau khi kiểm tra đủ điều kiện",
                },
            )
        )
        if not approved or approved.get("status") != "APPROVED":
            return json.dumps({"status": "automation_partial_failure", "reason_code": "TEST_PLAN_APPROVAL_FAILED"})
        plan = approved

    readback = parse(await call("GET", f"/ke-hoach-kiem-thu/{test_plan_id}", config))
    if (
        not readback
        or readback.get("project_id") != project_id
        or readback.get("status") != "APPROVED"
        or not readback.get("approved_snapshot")
        or readback.get("approved_snapshot_hash") != readback.get("baseline_hash")
    ):
        return json.dumps({"status": "automation_partial_failure", "reason_code": "TEST_PLAN_APPROVAL_READBACK_MISMATCH"})
    snapshot = readback["approved_snapshot"]
    result = parse(
        await _start_test_run_from_approved_plan(
            project_id, test_plan_id, readback, snapshot, automation_run_id, config
        )
    )
    if not result or result.get("status") != "completed":
        return json.dumps(result or {"status": "automation_partial_failure", "reason_code": "TEST_RUN_RESULT_INVALID"}, ensure_ascii=False, default=str)
    result["verification"]["checks"].insert(0, "test_plan_validated_and_approved")
    return json.dumps(result, ensure_ascii=False, default=str)
