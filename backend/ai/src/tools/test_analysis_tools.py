import hashlib
import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.tools.registry import with_tool_access
from src.tools.testing_api import call, parse


@with_tool_access(("requirement", "test_design"), "MUTATE", "testanalysis.run_ai")
async def generate_test_conditions_for_requirement_baseline(
    project_id: Annotated[str, Field(min_length=1)],
    requirement_version_id: Annotated[str, Field(min_length=1)],
    source_event_id: Annotated[str, Field(min_length=1, max_length=200)],
    source_event_revision: Annotated[int, Field(ge=1)],
    config: RunnableConfig = None,
) -> str:
    """Generate source-grounded test-condition candidates for a Requirement baseline."""
    configurable = (config or {}).get("configurable", {})
    automation_run_id = str(configurable.get("automation_run_id") or "")
    evidence = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "requirement_version"
            and str(item.get("artifact_version_id") or "") == requirement_version_id
            and item.get("artifact_revision") == source_event_revision
            and str(item.get("text") or "").strip()
        ),
        None,
    )
    expected_event_id = (
        f"requirement-version:{requirement_version_id}:"
        f"{source_event_revision}:BASELINED"
    )
    if not automation_run_id:
        return json.dumps(
            {"status": "automation_blocked", "reason_code": "VERIFIED_AUTOMATION_RUN_REQUIRED"}
        )
    if not evidence or source_event_id != expected_event_id:
        return json.dumps(
            {"status": "automation_blocked", "reason_code": "BASELINED_REQUIREMENT_EVENT_EVIDENCE_REQUIRED"}
        )
    idempotency_key = "test-condition-baseline:" + hashlib.sha256(
        f"{source_event_id}:{requirement_version_id}".encode("utf-8")
    ).hexdigest()
    basis_ref = {
        "artifact_type": "REQUIREMENT_VERSION",
        "artifact_id": str(evidence.get("artifact_id") or requirement_version_id),
        "artifact_version_id": requirement_version_id,
        "relationship": "DERIVED_FROM",
    }
    result = parse(
        await call(
            "POST",
            f"/du-an/{project_id}/phan-tich-kiem-thu/ai",
            config,
            {
                "basis_refs": [basis_ref],
                "instruction": "",
                "idempotency_key": idempotency_key,
                "source_event_id": source_event_id,
                "source_event_revision": source_event_revision,
            },
        )
    )
    if not isinstance(result, dict) or not result.get("_id"):
        return json.dumps(
            {"status": "automation_partial_failure", "reason_code": "TEST_CONDITION_RESULT_CREATE_FAILED"}
        )
    stored = parse(
        await call(
            "GET",
            f"/du-an/{project_id}/phan-tich-kiem-thu/ai?idempotency_key={idempotency_key}",
            config,
        )
    )
    if isinstance(stored, dict) and isinstance(stored.get("data"), dict):
        stored = stored["data"]
    readback = stored if isinstance(stored, dict) else None
    if (
        not readback
        or readback.get("project_id") != project_id
        or readback.get("requirement_version_id") != requirement_version_id
        or readback.get("source_event_id") != source_event_id
        or readback.get("source_event_revision") != source_event_revision
        or readback.get("candidate_only") is not True
        or readback.get("generation_status") != "SUCCESS"
        or readback.get("degraded_mode")
        or any(
            not item.get("evidence_quotes") or not item.get("basis_refs")
            for item in readback.get("candidates", [])
        )
    ):
        return json.dumps(
            {"status": "automation_partial_failure", "reason_code": "TEST_CONDITION_RESULT_READBACK_INVALID"}
        )
    return json.dumps(
        {
            "status": "completed",
            "analysis_result_id": result["_id"],
            "candidate_count": len(readback.get("candidates") or []),
            "source_event_id": source_event_id,
            "source_event_revision": source_event_revision,
            "verification": {
                "status": "COMPLETED",
                "project_id": project_id,
                "artifact_ids": [result["_id"]],
                "checks": [
                    "project_scope",
                    "source_event_revision",
                    "persisted_candidate_only",
                    "candidate_source_quotes",
                ],
            },
        },
        ensure_ascii=False,
    )
