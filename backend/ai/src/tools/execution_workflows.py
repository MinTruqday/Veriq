import hashlib
import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.tools.registry import with_tool_access
from src.tools.testing_api import call, parse


@with_tool_access(("reporting",), "MUTATE", "teststatusreport.update", owner_domain="reporting")
async def process_created_status_report(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    report_id: Annotated[str, Field(min_length=1, description="Created status report identifier")],
    source_event_id: Annotated[str, Field(min_length=1, max_length=200)],
    source_event_revision: Annotated[int, Field(ge=1)],
    config: RunnableConfig = None,
) -> str:
    """Create a traceable narrative candidate for a newly created status report."""
    configurable = (config or {}).get("configurable", {})
    ai_run_id = configurable.get("ai_run_id")
    permissions = set(configurable.get("permissions", []))
    event_trigger = configurable.get("event_trigger") or configurable.get("trigger")
    if not ai_run_id or "teststatusreport.update" not in permissions:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "STATUS_REPORT_AI_RUN_PERMISSION_REQUIRED",
            }
        )
    if event_trigger != "STATUS_REPORT_CREATED":
        return json.dumps(
            {"status": "blocked", "reason_code": "VERIFIED_STATUS_REPORT_EVENT_REQUIRED"}
        )
    source = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_status_report"
            and str(item.get("artifact_id") or "") == report_id
            and item.get("artifact_revision") == source_event_revision
        ),
        None,
    )
    expected_event_id = f"status-report:{report_id}:{source_event_revision}:STATUS_REPORT_CREATED"
    if not source or source_event_id != expected_event_id:
        return json.dumps(
            {"status": "blocked", "reason_code": "STATUS_REPORT_EVENT_SOURCE_INVALID"}
        )
    report = parse(await call("GET", f"/bao-cao-trang-thai/{report_id}", config))
    if not report or report.get("project_id") != project_id:
        return json.dumps(
            {"status": "blocked", "reason_code": "STATUS_REPORT_PROJECT_SCOPE_INVALID"}
        )
    if report.get("revision") != source_event_revision:
        return json.dumps(
            {
                "status": "completed",
                "action": "SKIPPED",
                "reason_code": "STATUS_REPORT_EVENT_SUPERSEDED",
                "report_id": report_id,
                "event_revision": source_event_revision,
                "current_revision": report.get("revision"),
            },
            ensure_ascii=False,
        )
    if report.get("status") != "DRAFT":
        return json.dumps(
            {"status": "blocked", "reason_code": "STATUS_REPORT_NOT_DRAFT"}
        )
    suffix = hashlib.sha256(source_event_id.encode("utf-8")).hexdigest()
    idempotency_key = f"ai-status-report-{suffix}"
    await call(
        "POST",
        f"/bao-cao-trang-thai/{report_id}/ai/ban-nhap",
        config,
        {
            "idempotency_key": idempotency_key,
            "instruction": "",
            "source_event_id": source_event_id,
            "source_event_revision": source_event_revision,
            "source_event_trigger": event_trigger,
        },
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )
    result = parse(await call("GET", f"/bao-cao-trang-thai/{report_id}/ai/ban-nhap", config))
    if (
        not result
        or result.get("project_id") != project_id
        or result.get("subject_id") != report_id
        or result.get("result_type") != "STATUS_REPORT_NARRATIVE"
        or result.get("source_event_id") != source_event_id
        or result.get("source_event_revision") != source_event_revision
        or result.get("source_event_trigger") != event_trigger
        or result.get("source_ai_run_id") != ai_run_id
        or result.get("idempotency_key") != idempotency_key
    ):
        return json.dumps(
            {
                "status": "partial_failure",
                "reason_code": "STATUS_REPORT_NARRATIVE_READBACK_INVALID",
            }
        )
    return json.dumps(
        {
            "status": "completed",
            "report_id": report_id,
            "narrative_result_id": result.get("_id"),
            "narrative_status": result.get("status"),
            "candidate_only": result.get("candidate_only") is True,
            "verification": {
                "status": "COMPLETED",
                "project_id": project_id,
                "artifact_ids": [report_id, str(result.get("_id") or "")],
                "checks": [
                    "report_scope",
                    "source_event_revision",
                    "narrative_readback",
                    "candidate_only",
                ],
            },
        },
        ensure_ascii=False,
    )


@with_tool_access(("reporting",), "MUTATE", "testcompletion.update", owner_domain="reporting")
async def process_created_test_completion_report(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    report_id: Annotated[
        str, Field(min_length=1, description="Created completion report identifier")
    ],
    source_event_id: Annotated[str, Field(min_length=1, max_length=200)],
    source_event_revision: Annotated[int, Field(ge=1)],
    config: RunnableConfig = None,
) -> str:
    """Create traceable narrative and lessons candidates for a completion report."""
    configurable = (config or {}).get("configurable", {})
    ai_run_id = configurable.get("ai_run_id")
    permissions = set(configurable.get("permissions", []))
    event_trigger = configurable.get("event_trigger") or configurable.get("trigger")
    if not ai_run_id or "testcompletion.update" not in permissions:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "COMPLETION_AI_RUN_PERMISSION_REQUIRED",
            }
        )
    if event_trigger != "TEST_COMPLETION_REPORT_CREATED":
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "VERIFIED_COMPLETION_REPORT_EVENT_REQUIRED",
            }
        )
    expected_event_id = (
        f"completion-report:{report_id}:{source_event_revision}:TEST_COMPLETION_REPORT_CREATED"
    )
    source = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_completion_report"
            and str(item.get("artifact_id") or "") == report_id
            and item.get("artifact_revision") == source_event_revision
        ),
        None,
    )
    if not source or source_event_id != expected_event_id:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "COMPLETION_REPORT_EVENT_SOURCE_INVALID",
            }
        )
    report = parse(await call("GET", f"/hoan-tat-kiem-thu/{report_id}", config))
    if not report or report.get("project_id") != project_id:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "COMPLETION_REPORT_PROJECT_SCOPE_INVALID",
            }
        )
    if report.get("revision") != source_event_revision:
        return json.dumps(
            {
                "status": "completed",
                "action": "SKIPPED",
                "reason_code": "COMPLETION_REPORT_EVENT_SUPERSEDED",
                "report_id": report_id,
                "event_revision": source_event_revision,
                "current_revision": report.get("revision"),
            },
            ensure_ascii=False,
        )
    if report.get("status") != "DRAFT":
        return json.dumps(
            {"status": "blocked", "reason_code": "COMPLETION_REPORT_NOT_DRAFT"}
        )
    suffix = hashlib.sha256(source_event_id.encode("utf-8")).hexdigest()
    outputs = [
        (
            "COMPLETION_REPORT_NARRATIVE",
            "/ai/ban-nhap",
            "completion-report-narrative",
            "Draft a report narrative from the supplied metrics and source evidence.",
        )
    ]
    if report.get("lessons_learned"):
        outputs.append(
            (
                "LESSONS_LEARNED_CLUSTERING",
                "/ai/gom-bai-hoc",
                "completion-lessons",
                "Cluster lessons learned while preserving their source identifiers.",
            )
        )
    readbacks = []
    for result_type, route, key_name, instruction in outputs:
        idempotency_key = f"ai-{key_name}-{suffix}"
        await call(
            "POST",
            f"/hoan-tat-kiem-thu/{report_id}{route}",
            config,
            {
                "idempotency_key": idempotency_key,
                "instruction": instruction,
                "source_event_id": source_event_id,
                "source_event_revision": source_event_revision,
                "source_event_trigger": event_trigger,
            },
            timeout=settings.MODEL_TIMEOUT_SECONDS,
        )
        result = parse(await call("GET", f"/hoan-tat-kiem-thu/{report_id}{route}", config))
        if (
            not result
            or result.get("project_id") != project_id
            or result.get("subject_id") != report_id
            or result.get("result_type") != result_type
            or result.get("source_event_id") != source_event_id
            or result.get("source_event_revision") != source_event_revision
            or result.get("source_event_trigger") != event_trigger
            or result.get("source_ai_run_id") != ai_run_id
            or result.get("idempotency_key") != idempotency_key
        ):
            return json.dumps(
                {
                    "status": "partial_failure",
                    "reason_code": "COMPLETION_AI_READBACK_INVALID",
                }
            )
        readbacks.append(result)
    return json.dumps(
        {
            "status": "completed",
            "report_id": report_id,
            "results": [
                {"result_type": item.get("result_type"), "result_id": item.get("_id")}
                for item in readbacks
            ],
            "verification": {
                "status": "COMPLETED",
                "project_id": project_id,
                "artifact_ids": [report_id, *[str(item.get("_id")) for item in readbacks]],
                "checks": [
                    "project_scope",
                    "source_revision",
                    "event_provenance",
                    "idempotent_readback",
                ],
            },
        },
        ensure_ascii=False,
    )


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


@with_tool_access(("execution",), "MUTATE", "release.close", owner_domain="execution")
async def process_changed_release(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    release_id: Annotated[
        str, Field(min_length=1, description="Release identifier from the verified project event")
    ],
    expected_revision: Annotated[
        int, Field(ge=1, description="Revision captured by the source event")
    ],
    config: RunnableConfig = None,
) -> str:
    """Close an active Release after its test completion reports are verified."""
    configurable = (config or {}).get("configurable", {})
    ai_run_id = configurable.get("ai_run_id")
    permissions = set(configurable.get("permissions", []))
    source = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "release"
            and item.get("authority") == "release_gate"
            and str(item.get("artifact_id") or "") == release_id
        ),
        None,
    )
    if not ai_run_id or not source:
        return json.dumps(
            {"status": "blocked", "reason_code": "VERIFIED_RELEASE_GATE_RECHECK_EVENT_REQUIRED"}
        )
    if not str(configurable.get("source_event_id") or "").startswith(
        f"release-gate:{release_id}:"
    ):
        return json.dumps(
            {"status": "blocked", "reason_code": "RELEASE_GATE_EVENT_ID_INVALID"}
        )
    if source.get("artifact_revision") != expected_revision:
        return json.dumps(
            {"status": "blocked", "reason_code": "RELEASE_EVENT_REVISION_MISMATCH"}
        )
    if "release.close" not in permissions:
        return json.dumps(
            {"status": "blocked", "reason_code": "RELEASE_CLOSE_PERMISSION_REQUIRED"}
        )

    release = parse(await call("GET", f"/ban-phat-hanh/{release_id}", config))
    if not release or release.get("_id") != release_id or release.get("project_id") != project_id:
        return json.dumps(
            {"status": "blocked", "reason_code": "RELEASE_PROJECT_SCOPE_INVALID"}
        )
    if release.get("revision") != expected_revision:
        return json.dumps(
            {
                "status": "completed",
                "release_id": release_id,
                "release_status": release.get("status"),
                "action": "SKIPPED",
                "reason_code": "RELEASE_EVENT_SUPERSEDED",
                "observed_revision": release.get("revision"),
                "event_revision": expected_revision,
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [release_id],
                    "checks": ["project_scope", "source_event_revision", "superseded_event_noop"],
                },
            },
            ensure_ascii=False,
        )
    if release.get("status") == "CLOSED":
        return json.dumps(
            {
                "status": "completed",
                "release_id": release_id,
                "release_status": "CLOSED",
                "already_closed": True,
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [release_id],
                },
            },
            ensure_ascii=False,
        )
    if release.get("status") != "ACTIVE":
        return json.dumps(
            {
                "status": "completed",
                "release_id": release_id,
                "release_status": release.get("status"),
                "close_attempted": False,
                "reason_code": "RELEASE_NOT_ACTIVE",
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [release_id],
                },
            },
            ensure_ascii=False,
        )
    if not isinstance(release.get("revision"), int) or release["revision"] < 1:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "RELEASE_REVISION_REQUIRED",
                "release_id": release_id,
                "verification": {
                    "status": "BLOCKED",
                    "project_id": project_id,
                    "artifact_ids": [release_id],
                },
            },
            ensure_ascii=False,
        )

    plans_response = await call(
        "GET",
        f"/du-an/{project_id}/ke-hoach-kiem-thu?release_id={release_id}&status=APPROVED",
        config,
    )
    try:
        plans = json.loads(plans_response)
    except (TypeError, json.JSONDecodeError):
        plans = None
    if isinstance(plans, dict):
        plans = plans.get("data")
    if not isinstance(plans, list) or not plans:
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": "APPROVED_RELEASE_TEST_PLAN_REQUIRED",
                "release_id": release_id,
            },
            ensure_ascii=False,
        )

    completion_reports = []
    for plan in plans:
        plan_id = str(plan.get("_id") or "") if isinstance(plan, dict) else ""
        approved_snapshot = plan.get("approved_snapshot") if isinstance(plan, dict) else None
        if (
            not plan_id
            or plan.get("project_id") != project_id
            or plan.get("status") != "APPROVED"
            or not isinstance(approved_snapshot, dict)
            or approved_snapshot.get("release_id") != release_id
            or plan.get("approved_snapshot_hash") != plan.get("baseline_hash")
        ):
            return json.dumps(
                {
                    "status": "blocked",
                    "reason_code": "APPROVED_RELEASE_TEST_PLAN_SNAPSHOT_INVALID",
                    "test_plan_id": plan_id or None,
                },
                ensure_ascii=False,
            )
        build_id = str(approved_snapshot.get("build_id") or plan.get("build_id") or "")
        if not build_id:
            return json.dumps(
                {
                    "status": "blocked",
                    "reason_code": "RELEASE_COMPLETION_BUILD_REQUIRED",
                    "test_plan_id": plan_id,
                },
                ensure_ascii=False,
            )
        suffix = hashlib.sha256(f"{ai_run_id}:{plan_id}".encode("utf-8")).hexdigest()
        monitoring = parse(
            await call(
                "POST",
                f"/du-an/{project_id}/giam-sat-kiem-thu/anh-chup",
                config,
                {
                    "idempotency_key": f"release-gate-{suffix}-monitoring",
                    "test_plan_id": plan_id,
                    "release_id": release_id,
                },
            )
        )
        if (
            not monitoring
            or not monitoring.get("_id")
            or monitoring.get("project_id") != project_id
        ):
            error = monitoring.get("error") if isinstance(monitoring, dict) else None
            return json.dumps(
                {
                    "status": "blocked",
                    "reason_code": str(
                        (error or {}).get("code")
                        or (monitoring or {}).get("status")
                        or "RELEASE_MONITORING_SNAPSHOT_FAILED"
                    ),
                    "test_plan_id": plan_id,
                },
                ensure_ascii=False,
            )
        report = parse(
            await call(
                "POST",
                f"/du-an/{project_id}/hoan-tat-kiem-thu",
                config,
                {
                    "idempotency_key": f"release-gate-{suffix}-completion",
                    "snapshot_id": monitoring["_id"],
                    "build_id": build_id,
                },
            )
        )
        if (
            not report
            or not report.get("_id")
            or report.get("project_id") != project_id
            or report.get("release_id") != release_id
            or report.get("test_plan_id") != plan_id
            or report.get("monitoring_snapshot_id") != monitoring["_id"]
            or report.get("status") != "DRAFT"
            or report.get("ai_run_id") != ai_run_id
        ):
            error = report.get("error") if isinstance(report, dict) else None
            return json.dumps(
                {
                    "status": "blocked",
                    "reason_code": str(
                        (error or {}).get("code")
                        or (report or {}).get("status")
                        or "RELEASE_COMPLETION_REPORT_INVALID"
                    ),
                    "test_plan_id": plan_id,
                },
                ensure_ascii=False,
            )
        completion_reports.append(report)

    close_response = parse(
        await call(
            "POST",
            f"/ban-phat-hanh/{release_id}/dong",
            config,
            {
                "expected_revision": release["revision"],
                "reason": 'Các báo cáo hoàn tất kiểm thử đã được xác minh.',
            },
        )
    )
    if close_response and close_response.get("status") == "qa_operation_failed":
        error = close_response.get("error") or {}
        return json.dumps(
            {
                "status": "blocked",
                "reason_code": str(error.get("code") or "RELEASE_CLOSE_GATE_FAILED"),
                "release_id": release_id,
                "release_status": release.get("status"),
                "upstream_status": close_response.get("upstream_status"),
                "verification": {
                    "status": "BLOCKED",
                    "project_id": project_id,
                    "artifact_ids": [release_id],
                },
            },
            ensure_ascii=False,
        )
    closed = close_response
    if not closed or closed.get("status") != "CLOSED" or closed.get("project_id") != project_id:
        return json.dumps(
            {
                "status": "partial_failure",
                "reason_code": "RELEASE_CLOSE_READBACK_INVALID",
                "release_id": release_id,
            }
        )

    readback = parse(await call("GET", f"/ban-phat-hanh/{release_id}", config))
    if (
        not readback
        or readback.get("_id") != release_id
        or readback.get("project_id") != project_id
        or readback.get("status") != "CLOSED"
        or readback.get("revision", 0) <= release.get("revision", 0)
    ):
        return json.dumps(
            {
                "status": "partial_failure",
                "reason_code": "RELEASE_CLOSE_READBACK_INVALID",
                "release_id": release_id,
            }
        )
    return json.dumps(
        {
            "status": "completed",
            "release_id": release_id,
            "release_status": "CLOSED",
            "verification": {
                "status": "COMPLETED",
                "project_id": project_id,
                "artifact_ids": [release_id],
                "checks": [
                    "release_project_scope",
                    "deterministic_plan_scope_evaluation",
                    "immutable_automation_completion_snapshots",
                    "release_completion_gate",
                    "closed_release_readback",
                ],
            },
            "completion_report_ids": [item["_id"] for item in completion_reports],
        },
        ensure_ascii=False,
    )
