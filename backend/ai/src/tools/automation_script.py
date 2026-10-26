import hashlib
import json

from langchain_core.runnables import RunnableConfig
from pydantic import Field
from typing import Annotated

from src.tools.registry import with_tool_access
from src.tools.testing_api import AutomationOperationError, parse, require_operation


@with_tool_access(("execution", "analysis"), "MUTATE", "ai.generate_automation_script")
async def generate_automation_script_after_test_case_approval(
    project_id: Annotated[str, Field(min_length=1)],
    version_id: Annotated[str, Field(min_length=1)],
    event_key: Annotated[str, Field(min_length=1, max_length=200)],
    event_revision: Annotated[int, Field(ge=1)],
    config: RunnableConfig = None,
) -> str:
    """Generate an automation script proposal for an approved Test Case version."""
    configurable = (config or {}).get("configurable", {})
    if not configurable.get("automation_run_id"):
        return json.dumps(
            {"status": "automation_blocked", "reason_code": "AUTOMATION_RUN_REQUIRED"}
        )

    evidence = next(
        (
            item
            for item in configurable.get("evidence", [])
            if isinstance(item, dict)
            and item.get("project_id") == project_id
            and item.get("artifact_type") == "test_case_version"
            and str(item.get("artifact_id") or "") == version_id
            and item.get("artifact_revision") == event_revision
        ),
        None,
    )
    expected_event_key = (
        f"test-case-version:{version_id}:{event_revision}:TEST_CASE_APPROVED"
    )
    if not evidence or event_key != expected_event_key:
        return json.dumps(
            {
                "status": "automation_blocked",
                "reason_code": "VERIFIED_TEST_CASE_APPROVAL_EVENT_REQUIRED",
            }
        )

    version = await require_operation("GET", f"/phien-ban-ca-kiem-thu/{version_id}", config)
    if version.get("_id") != version_id or version.get("project_id") != project_id:
        raise AutomationOperationError("TEST_CASE_VERSION_PROJECT_SCOPE_INVALID")
    if version.get("status") != "ACTIVE":
        return json.dumps(
            {
                "status": "automation_blocked",
                "reason_code": "TEST_CASE_VERSION_NOT_ACTIVE",
                "version_id": version_id,
            }
        )
    if version.get("automation_status") != "automated":
        return json.dumps(
            {
                "status": "completed",
                "reason_code": "TEST_CASE_NOT_MARKED_FOR_AUTOMATION",
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [version_id],
                    "checks": ["approved_version_readback", "automation_scope"],
                },
            },
            ensure_ascii=False,
        )

    project = await require_operation("GET", f"/du-an/{project_id}", config)
    if project.get("_id") != project_id:
        raise AutomationOperationError("AUTOMATION_PROJECT_SCOPE_INVALID")
    framework = project.get("automation_framework")
    language = project.get("automation_language")
    compatible = {
        "playwright": {"typescript", "javascript"},
        "cypress": {"typescript", "javascript"},
        "selenium": {"python"},
    }
    if language not in compatible.get(framework, set()):
        return json.dumps(
            {
                "status": "completed",
                "reason_code": "PROJECT_AUTOMATION_RUNTIME_NOT_CONFIGURED",
                "verification": {
                    "status": "COMPLETED",
                    "project_id": project_id,
                    "artifact_ids": [version_id],
                    "checks": ["approved_version_readback", "no_implicit_runtime_selection"],
                },
            },
            ensure_ascii=False,
        )

    idempotency_key = "approved-test-case-script:" + hashlib.sha256(
        f"{event_key}:{version_id}:{framework}:{language}".encode("utf-8")
    ).hexdigest()
    generated = await require_operation(
        "POST",
        f"/du-an/{project_id}/ai/ban-nhap-kich-ban-tu-dong",
        config,
        {
            "framework": framework,
            "language": language,
            "test_case_version_id": version_id,
            "source_event_key": event_key,
            "source_event_revision": event_revision,
            "context": "",
            "idempotency_key": idempotency_key,
        },
    )
    draft_id = str(generated.get("_id") or "")
    if not draft_id:
        raise AutomationOperationError("AUTOMATION_SCRIPT_DRAFT_CREATE_FAILED")
    readback = await require_operation(
        "GET", f"/ban-nhap-kich-ban-tu-dong/{draft_id}", config
    )
    if (
        readback.get("_id") != draft_id
        or readback.get("project_id") != project_id
        or readback.get("test_case_version_id") != version_id
        or readback.get("framework") != framework
        or readback.get("language") != language
        or not str(readback.get("source") or "").strip()
        or readback.get("idempotency_key") != idempotency_key
    ):
        raise AutomationOperationError("AUTOMATION_SCRIPT_READBACK_INVALID")
    return json.dumps(
        {
            "status": "completed",
            "script_draft_id": draft_id,
            "test_case_version_id": version_id,
            "framework": framework,
            "language": language,
            "verification": {
                "status": "COMPLETED",
                "project_id": project_id,
                "artifact_ids": [draft_id],
                "checks": [
                    "approved_test_case_event",
                    "project_configuration",
                    "idempotent_generation",
                    "script_source_readback",
                ],
            },
        },
        ensure_ascii=False,
    )
