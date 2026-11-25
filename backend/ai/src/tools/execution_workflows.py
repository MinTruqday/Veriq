import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.tools.registry import with_tool_access
from src.tools.testing_api import call, parse


@with_tool_access(("execution",), "MUTATE", "testrun.create", owner_domain="execution")
async def process_approved_test_plan(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    test_plan_id: Annotated[str, Field(min_length=1, description="Approved Test Plan identifier")],
    expected_revision: Annotated[int, Field(ge=1, description="Revision captured by the approval event")],
    source_event_id: Annotated[str, Field(min_length=1, max_length=240)],
    config: RunnableConfig = None,
) -> str:
    """Create an idempotent Test Run from an approved immutable Test Plan and verify the run"""
    configurable = (config or {}).get("configurable", {})
    ai_run_id = configurable.get("ai_run_id")
    permissions = set(configurable.get("permissions", []))
    expected_event_id = f"test-plan:{test_plan_id}:{expected_revision}:TEST_PLAN_APPROVED"
    if not ai_run_id:
        return json.dumps(
            {"status": "blocked", "reason_code": "AI_RUN_REQUIRED"}
        )
    plan_source = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_plan"
            and str(item.get("artifact_id") or "") == test_plan_id
            and item.get("artifact_revision") == expected_revision
        ),
        None,
    )
    if not plan_source or source_event_id != expected_event_id:
        return json.dumps(
            {"status": "blocked", "reason_code": "TEST_PLAN_EVENT_EVIDENCE_REQUIRED"}
        )
    plan = parse(await call("GET", f"/ke-hoach-kiem-thu/{test_plan_id}", config))
    if not plan or plan.get("project_id") != project_id:
        return json.dumps(
            {"status": "blocked", "reason_code": "TEST_PLAN_PROJECT_SCOPE_INVALID"}
        )
    if plan.get("revision") != expected_revision:
        return json.dumps(
            {
                "status": "completed",
                "test_plan_id": test_plan_id,
                "action": "SKIPPED",
                "reason_code": "TEST_PLAN_APPROVAL_EVENT_SUPERSEDED",
                "event_revision": expected_revision,
                "observed_revision": plan.get("revision"),
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [test_plan_id],
                    "checks": ["project_scope", "approval_event_revision", "superseded_event_noop"],
                },
            },
            ensure_ascii=False,
        )
    if plan.get("status") != "APPROVED":
        return json.dumps(
            {"status": "blocked", "reason_code": "APPROVED_TEST_PLAN_REQUIRED"}
        )
    expected_snapshot_hash = str(plan.get("approved_snapshot_hash") or "")
    if not expected_snapshot_hash:
        return json.dumps(
            {"status": "blocked", "reason_code": "APPROVED_TEST_PLAN_SNAPSHOT_HASH_REQUIRED"}
        )
    snapshot = plan.get("approved_snapshot") or plan
    version_ids = list(dict.fromkeys(snapshot.get("test_case_version_ids") or []))
    if not version_ids:
        return json.dumps(
            {"status": "blocked", "reason_code": "APPROVED_TEST_PLAN_SCOPE_EMPTY"}
        )
    if "testrun.execute" not in permissions:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "TEST_RUN_EXECUTION_PERMISSION_REQUIRED",
            }
        )
    return await _create_test_run_draft_from_approved_plan(
        project_id,
        test_plan_id,
        plan,
        snapshot,
        ai_run_id,
        expected_snapshot_hash,
        config,
    )


async def _create_test_run_draft_from_approved_plan(
    project_id: str,
    test_plan_id: str,
    plan: dict,
    snapshot: dict,
    ai_run_id: str,
    expected_snapshot_hash: str,
    config: RunnableConfig,
) -> str:
    configurable = (config or {}).get("configurable", {})
    output_language = configurable.get("output_language")
    permissions = set(configurable.get("permissions", []))
    if "testrun.create" not in permissions or "testrun.execute" not in permissions:
        return json.dumps(
            {"status": "blocked", "reason_code": "TEST_RUN_PERMISSION_REQUIRED"}
        )
    version_ids = list(dict.fromkeys(snapshot.get("test_case_version_ids") or []))
    if not version_ids:
        return json.dumps(
            {"status": "blocked", "reason_code": "APPROVED_TEST_PLAN_SCOPE_EMPTY"}
        )
    payload = {
        "project_id": project_id,
        "name": (
            f"{plan.get('name') or test_plan_id} - "
            "bản nháp lần chạy"
        ),
        "test_plan_id": test_plan_id,
        "test_case_version_ids": version_ids,
        "environment": snapshot.get("environment") or "",
        "environment_id": snapshot.get("environment_id"),
        "release": snapshot.get("release") or "",
        "release_id": snapshot.get("release_id"),
        "build": snapshot.get("build") or "",
        "build_id": snapshot.get("build_id"),
        "idempotency_key": f"ai-automation-{ai_run_id}",
        "expected_test_plan_snapshot_hash": expected_snapshot_hash,
    }
    run = parse(await call("POST", f"/du-an/{project_id}/lan-chay-kiem-thu", config, payload))
    if not run or not run.get("_id"):
        return json.dumps(
            {"status": "partial_failure", "reason_code": "TEST_RUN_CREATE_FAILED"}
        )
    run_id = str(run["_id"])
    readback = parse(await call("GET", f"/lan-chay-kiem-thu/{run_id}", config))
    if (
        not readback
        or readback.get("_id") != run_id
        or readback.get("project_id") != project_id
        or readback.get("test_plan_id") != test_plan_id
        or readback.get("test_plan_snapshot_hash") != expected_snapshot_hash
        or readback.get("status") != "DRAFT"
        or set(readback.get("test_case_version_ids", [])) != set(version_ids)
    ):
        return json.dumps(
            {
                "status": "partial_failure",
                "test_run_id": run_id,
                "reason_code": "TEST_RUN_READBACK_MISMATCH",
            }
        )
    return json.dumps(
        {
            "status": "completed",
            "test_run_id": run_id,
            "test_plan_id": test_plan_id,
            "run_status": readback.get("status"),
            "test_case_version_ids": readback.get("test_case_version_ids", []),
            "verification": {
                "status": "COMPLETED",
                "project_id": project_id,
                "artifact_ids": [test_plan_id, run_id],
                "checks": [
                    "approved_plan",
                    "approved_scope",
                    "run_draft_created",
                    "run_readback",
                ],
                "warnings": ["TEST_RUN_REQUIRES_MANUAL_ASSIGNMENT"],
            },
        },
        ensure_ascii=False,
        default=str,
    )


@with_tool_access(("execution",), "MUTATE", "testrun.create", owner_domain="execution")
async def process_changed_test_plan(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    test_plan_id: Annotated[
        str, Field(min_length=1, description="Test Plan identifier from the verified project event")
    ],
    expected_revision: Annotated[
        int, Field(ge=1, description="Revision captured by the source event")
    ],
    config: RunnableConfig = None,
) -> str:
    """Validate and lock a changed plan under the authorized AI run, then start execution."""
    configurable = (config or {}).get("configurable", {})
    ai_run_id = configurable.get("ai_run_id")
    permissions = set(configurable.get("permissions", []))
    event_evidence = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_plan"
            and str(item.get("artifact_id") or "") == test_plan_id
        ),
        None,
    )
    if not ai_run_id or not event_evidence:
        return json.dumps(
            {"status": "blocked", "reason_code": "VERIFIED_TEST_PLAN_EVENT_REQUIRED"}
        )
    if event_evidence.get("artifact_revision") != expected_revision:
        return json.dumps(
            {"status": "blocked", "reason_code": "TEST_PLAN_EVENT_REVISION_MISMATCH"}
        )
    if "testplan.approve" not in permissions:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "TEST_PLAN_APPROVAL_PERMISSION_REQUIRED",
            }
        )
    plan = parse(await call("GET", f"/ke-hoach-kiem-thu/{test_plan_id}", config))
    if not plan or plan.get("project_id") != project_id:
        return json.dumps(
            {"status": "blocked", "reason_code": "TEST_PLAN_PROJECT_SCOPE_INVALID"}
        )
    if plan.get("revision") != expected_revision:
        return json.dumps(
            {
                "status": "completed",
                "test_plan_id": test_plan_id,
                "action": "SKIPPED",
                "reason_code": "TEST_PLAN_EVENT_SUPERSEDED",
                "observed_revision": plan.get("revision"),
                "event_revision": expected_revision,
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [test_plan_id],
                    "checks": ["project_scope", "source_event_revision", "superseded_event_noop"],
                },
            },
            ensure_ascii=False,
        )
    status = plan.get("status")
    if status != "APPROVED":
        if status not in {"DRAFT", "IN_REVIEW"}:
            return json.dumps(
                {"status": "blocked", "reason_code": "TEST_PLAN_NOT_APPROVABLE"}
            )
        if not plan.get("test_case_version_ids"):
            return json.dumps(
                {"status": "blocked", "reason_code": "TEST_PLAN_TEST_CASE_SCOPE_EMPTY"}
            )
        validation = parse(
            await call("POST", f"/ke-hoach-kiem-thu/{test_plan_id}/kiem-tra", config)
        )
        if not validation or validation.get("ready_for_approval") is not True:
            return json.dumps(
                {
                    "status": "blocked",
                    "reason_code": "TEST_PLAN_INCOMPLETE",
                    "findings": (validation or {}).get("findings", []),
                },
                ensure_ascii=False,
            )
        plan = parse(
            await call(
                "POST",
                f"/ke-hoach-kiem-thu/{test_plan_id}/phe-duyet",
                config,
                {
                    "expected_revision": plan.get("revision"),
                    "review_note": 'Phạm vi và quyền của sự kiện đã vượt qua các kiểm tra bắt buộc.',
                },
            )
        )
        if not plan or plan.get("status") != "APPROVED":
            return json.dumps(
                {
                    "status": "partial_failure",
                    "reason_code": "TEST_PLAN_APPROVAL_READBACK_MISMATCH",
                }
            )

    readback = parse(await call("GET", f"/ke-hoach-kiem-thu/{test_plan_id}", config))
    if (
        not readback
        or readback.get("project_id") != project_id
        or readback.get("status") != "APPROVED"
        or not readback.get("approved_snapshot")
        or readback.get("approved_snapshot_hash") != readback.get("baseline_hash")
    ):
        return json.dumps(
            {
                "status": "partial_failure",
                "reason_code": "TEST_PLAN_APPROVAL_READBACK_MISMATCH",
            }
        )
    snapshot = readback["approved_snapshot"]
    result = parse(
        await _create_test_run_draft_from_approved_plan(
            project_id,
            test_plan_id,
            readback,
            snapshot,
            ai_run_id,
            str(readback["approved_snapshot_hash"]),
            config,
        )
    )
    if not result or result.get("status") != "completed":
        return json.dumps(
            result
            or {"status": "partial_failure", "reason_code": "TEST_RUN_RESULT_INVALID"},
            ensure_ascii=False,
            default=str,
        )
    result["verification"]["checks"].insert(0, "test_plan_approval_readback")
    return json.dumps(result, ensure_ascii=False, default=str)
