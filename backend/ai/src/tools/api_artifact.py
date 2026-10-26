import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.tools.automation_publication import (
    publish_grounded_test_case,
    verified_test_case_publication_readback,
)
from src.tools.registry import with_tool_access
from src.tools.testing_api import AutomationOperationError, require_operation


@with_tool_access(
    ("test_design",),
    "MUTATE",
    "ai.generate_api_testcase",
)
async def process_confirmed_api_operation(
    operation_id: Annotated[
        str, Field(description="Confirmed API operation identifier")
    ],
    expected_revision: Annotated[int, Field(ge=1)],
    config: RunnableConfig = None,
) -> str:
    """Generate and publish evidence-grounded Test Cases for a confirmed API operation."""
    configurable = (config or {}).get("configurable", {})
    project_id = str(configurable.get("project_id") or "")
    permissions = set(configurable.get("permissions") or [])
    required_permissions = {
        "ai.generate_api_testcase",
        "testcase.import",
        "testcase.create",
        "testcase.read",
        "testcase.lint",
        "testcase.submit_review",
        "testcase.review",
        "testcase.version.read",
    }
    missing_permissions = sorted(required_permissions - permissions)
    if not project_id or missing_permissions:
        return json.dumps(
            {
                "status": "automation_blocked",
                "reason_code": "REQUIRED_PERMISSION_MISSING",
                "missing_permissions": missing_permissions,
            },
            ensure_ascii=False,
        )

    async def current_operation():
        operation = await require_operation(
            "GET",
            f"/dac-ta-giao-dien/thao-tac/{operation_id}",
            config,
        )
        if (
            operation.get("_id") != operation_id
            or operation.get("project_id") != project_id
            or operation.get("revision") != expected_revision
        ):
            raise AutomationOperationError("API_OPERATION_REVISION_STALE")
        return operation

    operation = await current_operation()
    job = await require_operation(
        "POST",
        f"/dac-ta-giao-dien/thao-tac/{operation_id}/sinh-ca-kiem-thu",
        config,
        {},
    )
    if (
        not job.get("_id")
        or job.get("project_id") != project_id
        or job.get("source_api_operation_id") != operation_id
    ):
        raise RuntimeError("API_TEST_IMPORT_PREVIEW_SCOPE_INVALID")

    if job.get("status") != "CONFIRMED":
        if job.get("status") != "PREVIEW_READY":
            raise AutomationOperationError("API_TEST_IMPORT_PREVIEW_STATE_INVALID")
        preview = job.get("preview") or []
        selected_indexes = [
            index
            for index, item in enumerate(preview)
            if not item.get("incomplete")
            and isinstance(item.get("draft"), dict)
            and not item.get("similar_cases")
        ]
        await current_operation()
        await require_operation(
            "POST",
            f"/nhap-ca-kiem-thu/{job['_id']}/xac-nhan",
            config,
            {"selected_indexes": selected_indexes},
        )

    stored_job = await require_operation(
        "GET", f"/nhap-ca-kiem-thu/{job['_id']}", config
    )
    if (
        stored_job.get("_id") != job.get("_id")
        or stored_job.get("project_id") != project_id
        or stored_job.get("source_api_operation_id") != operation_id
        or stored_job.get("status") != "CONFIRMED"
    ):
        raise RuntimeError("API_TEST_IMPORT_CONFIRMATION_READBACK_INVALID")

    published = []
    unresolved = []
    draft_ids = list(stored_job.get("created_draft_ids") or [])
    for draft_id in draft_ids:
        await current_operation()
        draft = await require_operation(
            "GET", f"/ban-nhap-ca-kiem-thu/{draft_id}", config
        )
        source_links = [
            item
            for item in draft.get("source_evidence", [])
            if item.get("artifact_type") == "api_operation"
            and item.get("artifact_version_id") == operation_id
        ]
        if (
            draft.get("_id") != draft_id
            or draft.get("project_id") != project_id
            or draft.get("origin") != "ai_generated"
            or not source_links
        ):
            raise RuntimeError("API_GENERATED_TEST_CASE_SOURCE_LINK_INVALID")

        if draft.get("status") == "APPROVED":
            frozen_version_id = draft.get("frozen_version_id")
            if not frozen_version_id:
                raise RuntimeError("API_GENERATED_TEST_CASE_FROZEN_VERSION_MISSING")
            frozen_version = await require_operation(
                "GET", f"/phien-ban-ca-kiem-thu/{frozen_version_id}", config
            )
            case_id = frozen_version.get("test_case_id")
            if (
                frozen_version.get("_id") != frozen_version_id
                or frozen_version.get("project_id") != project_id
                or frozen_version.get("status") != "ACTIVE"
                or not case_id
                or not _version_preserves_api_source(draft, frozen_version, operation_id)
            ):
                raise RuntimeError("API_GENERATED_TEST_CASE_FROZEN_VERSION_INVALID")
            case_readback = await require_operation(
                "GET", f"/ca-kiem-thu/{case_id}", config
            )
            version_readback = await require_operation(
                "GET", f"/phien-ban-ca-kiem-thu/{frozen_version_id}", config
            )
            if (
                not verified_test_case_publication_readback(
                    project_id,
                    case_readback,
                    frozen_version,
                    case_readback,
                    version_readback,
                )
                or not _version_preserves_api_source(
                    draft, version_readback, operation_id
                )
            ):
                raise RuntimeError("API_GENERATED_TEST_CASE_RETRY_READBACK_INVALID")
            published.append(
                {
                    "test_case_id": case_id,
                    "test_case_version_id": frozen_version_id,
                    "publication_status": "ALREADY_PUBLISHED",
                }
            )
            continue

        lint = await require_operation(
            "POST", f"/ban-nhap-ca-kiem-thu/{draft_id}/kiem-tra", config
        )
        if lint.get("valid") is not True:
            unresolved.append(
                {"test_case_draft_id": draft_id, "reason": "TEST_CASE_QUALITY_FAILED"}
            )
            continue
        await current_operation()
        try:
            case, version, publication_status = await publish_grounded_test_case(
                project_id,
                draft,
                config,
                before_write=current_operation,
            )
        except AutomationOperationError as error:
            unresolved.append(
                {"test_case_draft_id": draft_id, "reason": error.reason_code}
            )
            continue
        case_readback = await require_operation(
            "GET", f"/ca-kiem-thu/{case['_id']}", config
        )
        version_readback = await require_operation(
            "GET", f"/phien-ban-ca-kiem-thu/{version['_id']}", config
        )
        if not verified_test_case_publication_readback(
            project_id, case, version, case_readback, version_readback
        ) or not _version_preserves_api_source(draft, version_readback, operation_id):
            raise RuntimeError("API_GENERATED_TEST_CASE_READBACK_INVALID")
        published.append(
            {
                "test_case_id": case["_id"],
                "test_case_version_id": version["_id"],
                "publication_status": publication_status,
            }
        )

    if unresolved:
        status = "automation_partial_failure"
    else:
        status = "COMPLETED"
    return json.dumps(
        {
            "status": status,
            "reason_code": "API_OPERATION_TEST_DESIGN_COMPLETED" if not unresolved else "API_OPERATION_TEST_DESIGN_INCOMPLETE",
            "project_id": project_id,
            "api_operation_id": operation_id,
            "test_import_id": stored_job["_id"],
            "published_test_cases": published,
            "skipped_duplicate_indexes": stored_job.get("automatic_skipped_duplicate_indexes", []),
            "skipped_incomplete_indexes": stored_job.get("automatic_skipped_incomplete_indexes", []),
            "unresolved": unresolved,
            "verification": {
                "status": "COMPLETED" if not unresolved else "INCOMPLETE",
                "project_id": project_id,
                "artifact_ids": [
                    stored_job["_id"],
                    *[item["test_case_id"] for item in published],
                    *[item["test_case_version_id"] for item in published],
                ],
                "checks": [
                    "api_operation_revision_rechecked",
                    "duplicate_and_incomplete_candidates_not_published",
                    "frozen_test_case_versions_read_back",
                ],
            },
        },
        ensure_ascii=False,
    )


def _version_preserves_api_source(draft, version, operation_id):
    source_links = [
        item
        for item in version.get("source_evidence", [])
        if item.get("artifact_type") == "api_operation"
        and item.get("artifact_version_id") == operation_id
    ]
    return bool(source_links) and (
        version.get("source_evidence") == draft.get("source_evidence")
        and version.get("evidence_refs") == draft.get("evidence_refs")
        and version.get("evidence_quotes") == draft.get("evidence_quotes")
        and version.get("requirement_version_ids")
        == draft.get("requirement_version_ids")
    )
