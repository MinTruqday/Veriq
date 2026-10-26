"""Automatic synchronization of Requirement assurance snapshots."""

import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.tools.registry import with_tool_access
from src.tools.testing_api import AutomationOperationError, require_operation


def _test_case_version_ids(assessment):
    return {
        str(version.get("id"))
        for item in assessment.get("coverage_items", [])
        if isinstance(item, dict)
        for version in item.get("test_case_versions", [])
        if isinstance(version, dict) and version.get("id")
    }


@with_tool_access(("analysis", "test_design"), "MUTATE", "testcase.read")
async def refresh_assurance_after_test_case_approval(
    project_id: Annotated[str, Field(min_length=1, description="Dự án sở hữu Test Case")],
    version_id: Annotated[str, Field(min_length=1, description="Phiên bản Test Case đã đóng băng")],
    config: RunnableConfig = None,
) -> str:
    """Refresh only derived assurance snapshots linked to a verified approved Test Case."""
    configurable = (config or {}).get("configurable", {})
    if not configurable.get("automation_run_id"):
        return json.dumps({"status": "automation_blocked", "reason_code": "AUTOMATION_RUN_REQUIRED"})

    event = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_case_version"
            and str(item.get("artifact_id") or "") == version_id
        ),
        None,
    )
    if not event:
        return json.dumps(
            {"status": "automation_blocked", "reason_code": "VERIFIED_TEST_CASE_APPROVAL_EVENT_REQUIRED"}
        )

    case_version = await require_operation(
        "GET", f"/phien-ban-ca-kiem-thu/{version_id}", config
    )
    if case_version.get("_id") != version_id or case_version.get("project_id") != project_id:
        raise AutomationOperationError("TEST_CASE_VERSION_PROJECT_SCOPE_INVALID")
    if case_version.get("status") != "ACTIVE":
        return json.dumps(
            {
                "status": "automation_blocked",
                "reason_code": "TEST_CASE_VERSION_NOT_ACTIVE",
                "version_id": version_id,
            },
            ensure_ascii=False,
        )

    refreshed = []
    unmapped_requirement_versions = []
    for requirement_version_id in dict.fromkeys(
        str(value)
        for value in case_version.get("requirement_version_ids", [])
        if value
    ):
        assessment = await require_operation(
            "GET",
            f"/phien-ban-yeu-cau/{requirement_version_id}/do-day-du-kiem-thu",
            config,
        )
        if (
            assessment.get("project_id") != project_id
            or assessment.get("requirement_version_id") != requirement_version_id
        ):
            raise AutomationOperationError("ASSURANCE_REQUIREMENT_SCOPE_INVALID")

        try:
            updated = await require_operation(
                "POST",
                f"/phien-ban-yeu-cau/{requirement_version_id}/do-day-du-kiem-thu/lam-moi",
                config,
                {"expected_revision": assessment["revision"]},
            )
        except (AutomationOperationError, KeyError) as error:
            latest = await require_operation(
                "GET",
                f"/phien-ban-yeu-cau/{requirement_version_id}/do-day-du-kiem-thu",
                config,
            )
            if (
                latest.get("project_id") == project_id
                and latest.get("requirement_version_id") == requirement_version_id
                and version_id in _test_case_version_ids(latest)
            ):
                updated = latest
            else:
                raise AutomationOperationError("ASSURANCE_REFRESH_REVISION_CONFLICT") from error

        readback = await require_operation(
            "GET",
            f"/phien-ban-yeu-cau/{requirement_version_id}/do-day-du-kiem-thu",
            config,
        )
        if (
            not updated
            or readback.get("project_id") != project_id
            or readback.get("requirement_version_id") != requirement_version_id
            or int(readback.get("revision") or 0) < int(updated.get("revision") or 0)
        ):
            raise AutomationOperationError("ASSURANCE_REFRESH_READBACK_INVALID")
        mapped = version_id in _test_case_version_ids(readback)
        if not mapped:
            unmapped_requirement_versions.append(requirement_version_id)
        refreshed.append(
            {
                "requirement_version_id": requirement_version_id,
                "assessment_id": readback.get("_id"),
                "revision": readback.get("revision"),
                "mapped": mapped,
            }
        )

    return json.dumps(
        {
            "status": "completed",
            "version_id": version_id,
            "refreshed_assessments": refreshed,
            "unmapped_requirement_version_ids": unmapped_requirement_versions,
            "verification": {
                "status": "COMPLETED",
                "project_id": project_id,
                "artifact_ids": [
                    version_id,
                    *[item["assessment_id"] for item in refreshed if item.get("assessment_id")],
                ],
                "checks": [
                    "verified_approval_event",
                    "test_case_version_project_scope",
                    "revision_checked_assurance_refresh",
                    "assurance_snapshot_readback",
                ],
            },
        },
        ensure_ascii=False,
    )
