"""Automatic execution-feedback workflow owned by the execution domain."""

import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.tools.registry import with_tool_access
from src.tools.testing_api import AutomationOperationError, require_operation


@with_tool_access(("execution",), "MUTATE", "testcase.read", owner_domain="execution")
async def process_recorded_test_execution(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    result_id: Annotated[str, Field(min_length=1, description="Recorded Test Result identifier")],
    expected_revision: Annotated[int, Field(ge=1, description="Revision captured by the verified result event")],
    config: RunnableConfig = None,
) -> str:
    """Record a verified failed execution against mapped assurance obligations."""
    configurable = (config or {}).get("configurable", {})
    if not configurable.get("automation_run_id"):
        return json.dumps({"status": "automation_blocked", "reason_code": "AUTOMATION_RUN_REQUIRED"})
    source_event = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_result"
            and str(item.get("artifact_id") or "") == result_id
            and item.get("artifact_revision") == expected_revision
        ),
        None,
    )
    if not source_event:
        return json.dumps({"status": "automation_blocked", "reason_code": "VERIFIED_TEST_RESULT_EVENT_REQUIRED"})

    result = await require_operation("GET", f"/ket-qua-kiem-thu/{result_id}", config)
    if result.get("project_id") != project_id or result.get("_id") != result_id:
        return json.dumps({"status": "automation_blocked", "reason_code": "TEST_RESULT_PROJECT_SCOPE_INVALID"})
    if result.get("revision") != expected_revision:
        return json.dumps(
            {
                "status": "completed",
                "result_id": result_id,
                "action": "SKIPPED",
                "reason_code": "TEST_RESULT_EVENT_SUPERSEDED",
                "event_revision": expected_revision,
                "observed_revision": result.get("revision"),
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [result_id],
                    "checks": ["project_scope", "result_revision", "superseded_event_noop"],
                },
            },
            ensure_ascii=False,
        )

    case = result.get("test_case_version") or {}
    case_version_id = str(result.get("test_case_version_id") or case.get("_id") or "")
    linked_defects = [
        str(item.get("_id") or item.get("defect_id") or "")
        for item in result.get("defects", [])
        if isinstance(item, dict) and (item.get("_id") or item.get("defect_id"))
    ]
    linked_defects = list(dict.fromkeys(linked_defects))
    if len(linked_defects) > 1:
        return json.dumps(
            {
                "status": "needs_review",
                "result_id": result_id,
                "feedback_recorded": 0,
                "reason_code": "MULTIPLE_LINKED_DEFECTS_REQUIRE_REVIEW",
                "linked_defect_ids": linked_defects,
                "verification": {
                    "status": "NEEDS_REVIEW",
                    "project_id": project_id,
                    "artifact_ids": [result_id, *linked_defects],
                    "checks": [
                        "result_readback",
                        "project_scope",
                        "ambiguous_defect_mapping_not_applied",
                    ],
                },
            },
            ensure_ascii=False,
        )
    if result.get("status") != "FAIL" or not case_version_id or not linked_defects:
        return json.dumps(
            {
                "status": "completed",
                "result_id": result_id,
                "feedback_recorded": 0,
                "reason_code": "NO_LINKED_FAILURE_EVIDENCE",
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [result_id],
                    "checks": ["result_readback", "project_scope", "no_unlinked_failure_claim"],
                },
            },
            ensure_ascii=False,
        )

    matched_coverage_item_ids = []
    feedback_recorded = []
    already_recorded = []
    for requirement_version_id in dict.fromkeys(
        str(value) for value in case.get("requirement_version_ids", []) if value
    ):
        assessment = await require_operation(
            "GET", f"/phien-ban-yeu-cau/{requirement_version_id}/do-day-du-kiem-thu", config
        )
        if assessment.get("project_id") != project_id:
            raise AutomationOperationError("ASSURANCE_PROJECT_SCOPE_INVALID")
        for item in assessment.get("coverage_items", []):
            mapped_versions = {
                str(value.get("id"))
                for value in item.get("test_case_versions", [])
                if isinstance(value, dict) and value.get("id")
            }
            if case_version_id not in mapped_versions:
                continue
            coverage_item_id = str(item.get("coverage_item_id") or "")
            if not coverage_item_id:
                raise AutomationOperationError("COVERAGE_ITEM_IDENTIFIER_MISSING")
            matched_coverage_item_ids.append(coverage_item_id)
            if any(
                str(feedback.get("test_result_id") or "") == result_id
                and feedback.get("test_result_revision") == expected_revision
                for feedback in item.get("execution_feedback", [])
            ):
                already_recorded.append(coverage_item_id)
                continue
            updated = await require_operation(
                "POST",
                f"/do-day-du-kiem-thu/{assessment['_id']}/hang-muc/{coverage_item_id}/phan-hoi-thuc-thi",
                config,
                {
                    "expected_revision": assessment["revision"],
                    "test_case_version_id": case_version_id,
                    "test_result_revision": expected_revision,
                    "outcome": "CAUGHT_DEFECT",
                    "test_result_id": result_id,
                    "defect_id": linked_defects[0],
                    "note": "Đối chiếu từ kết quả FAIL đã lưu và defect được liên kết trong cùng dự án",
                },
            )
            readback = await require_operation(
                "GET", f"/phien-ban-yeu-cau/{requirement_version_id}/do-day-du-kiem-thu", config
            )
            verified_item = next(
                (value for value in readback.get("coverage_items", []) if value.get("coverage_item_id") == coverage_item_id),
                None,
            )
            if (
                not updated
                or not verified_item
                or not any(
                    str(feedback.get("test_result_id") or "") == result_id
                    and feedback.get("test_result_revision") == expected_revision
                    and feedback.get("outcome") == "CAUGHT_DEFECT"
                    for feedback in verified_item.get("execution_feedback", [])
                )
            ):
                raise AutomationOperationError("EXECUTION_FEEDBACK_READBACK_FAILED")
            feedback_recorded.append(coverage_item_id)

    return json.dumps(
        {
            "status": "completed",
            "result_id": result_id,
            "feedback_recorded": len(feedback_recorded),
            "coverage_item_ids": list(dict.fromkeys(matched_coverage_item_ids)),
            "already_recorded": list(dict.fromkeys(already_recorded)),
            "verification": {
                "status": "COMPLETED",
                "project_id": project_id,
                "artifact_ids": [result_id, *linked_defects, *list(dict.fromkeys(matched_coverage_item_ids))],
                "checks": [
                    "failed_result_readback",
                    "linked_defect",
                    "mapped_test_case_version",
                    "assurance_feedback_readback",
                ],
            },
        },
        ensure_ascii=False,
        default=str,
    )
