import json
import math
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.tools.registry import with_tool_access
from src.tools.testing_api import AutomationOperationError, call, require_operation


@with_tool_access(("execution", "analysis", "reporting"), "READ", "testrun.read")
async def get_test_results(
    test_run_id: Annotated[str, Field(description="Test run identifier")], config: RunnableConfig = None
) -> str:
    """Read a test run snapshot with results and related defects"""
    return await call("GET", f"/lan-chay-kiem-thu/{test_run_id}", config)

@with_tool_access(("execution", "analysis"), "READ", "testrun.read")
async def get_test_result(
    result_id: Annotated[str, Field(description="Test result identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read a result with its Test Run, Test Case version, and linked defects"""
    return await call("GET", f"/ket-qua-kiem-thu/{result_id}", config)

@with_tool_access(("execution", "analysis"), "READ", "testplan.read")
async def get_test_plan(
    test_plan_id: Annotated[str, Field(description="Test Plan identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read the current Test Plan and its approved scope snapshot"""
    return await call("GET", f"/ke-hoach-kiem-thu/{test_plan_id}", config)

@with_tool_access(("execution", "analysis"), "READ", "release.read")
async def get_release(
    release_id: Annotated[str, Field(description="Release identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read a Release and its current lifecycle state"""
    return await call("GET", f"/ban-phat-hanh/{release_id}", config)

@with_tool_access(("analysis", "reporting"), "READ", "project.read")
async def get_work_item(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    work_item_id: Annotated[str, Field(description="Work Item identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read a project Work Item and its current planning state"""
    return await call("GET", f"/du-an/{project_id}/cong-viec/{work_item_id}", config)


@with_tool_access(("analysis",), "READ", "project.read")
async def get_work_item_impact_context(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    work_item_id: Annotated[str, Field(description="Project Work Item identifier")],
    expected_revision: Annotated[int, Field(ge=1, description="Revision recorded by the verified Work Item event")],
    config: RunnableConfig = None,
) -> str:
    """Read a Work Item and the project-scoped Requirement versions and Test Cases explicitly linked to it"""
    configurable = (config or {}).get("configurable", {})
    permissions = set(configurable.get("permissions", []))
    required_permissions = {"project.read", "requirement.read", "requirement.version.read", "testcase.read"}
    if not required_permissions.issubset(permissions):
        return json.dumps(
            {"status": "denied", "reason_code": "LINKED_IMPACT_CONTEXT_PERMISSION_MISSING"},
            ensure_ascii=False,
        )
    work_item = await require_operation(
        "GET", f"/du-an/{project_id}/cong-viec/{work_item_id}", config
    )
    if work_item.get("_id") != work_item_id or work_item.get("project_id") != project_id:
        return json.dumps(
            {"status": "denied", "reason_code": "WORK_ITEM_SCOPE_MISMATCH"},
            ensure_ascii=False,
        )
    if type(work_item.get("revision")) is not int or work_item["revision"] != expected_revision:
        return json.dumps(
            {
                "status": "superseded",
                "reason_code": "WORK_ITEM_EVENT_REVISION_SUPERSEDED",
                "project_id": project_id,
                "work_item_id": work_item_id,
                "expected_revision": expected_revision,
                "current_revision": work_item.get("revision"),
            },
            ensure_ascii=False,
        )

    requirements = []
    test_cases = []
    for requirement_id in dict.fromkeys(str(value) for value in work_item.get("requirement_ids", []) if value):
        requirement = await require_operation("GET", f"/yeu-cau/{requirement_id}", config)
        if requirement.get("_id") != requirement_id or requirement.get("project_id") != project_id:
            return json.dumps(
                {
                    "status": "incomplete",
                    "reason_code": "WORK_ITEM_REQUIREMENT_SCOPE_MISMATCH",
                    "work_item_id": work_item_id,
                    "requirement_id": requirement_id,
                },
                ensure_ascii=False,
            )
        version = requirement.get("current_version")
        version_id = requirement.get("current_version_id") or (
            version.get("_id") if isinstance(version, dict) else None
        )
        if version_id and (
            not isinstance(version, dict) or version.get("_id") != version_id
        ):
            version = await require_operation("GET", f"/phien-ban-yeu-cau/{version_id}", config)
        if version and (
            version.get("_id") != version_id
            or version.get("project_id") != project_id
            or version.get("requirement_id") != requirement_id
        ):
            return json.dumps(
                {
                    "status": "incomplete",
                    "reason_code": "WORK_ITEM_REQUIREMENT_VERSION_SCOPE_MISMATCH",
                    "work_item_id": work_item_id,
                    "requirement_id": requirement_id,
                    "requirement_version_id": version_id,
                },
                ensure_ascii=False,
            )
        if not version_id or not version:
            return json.dumps(
                {
                    "status": "incomplete",
                    "reason_code": "WORK_ITEM_REQUIREMENT_VERSION_UNAVAILABLE",
                    "work_item_id": work_item_id,
                    "requirement_id": requirement_id,
                },
                ensure_ascii=False,
            )
        requirements.append(
            {"requirement": requirement, "current_version": version}
        )
        cases = await list_all_requirement_test_cases(
            project_id, requirement_id, config
        )
        for case in cases:
            current = case.get("current_version") or {}
            linked_versions = set(current.get("requirement_version_ids") or [])
            if (
                case.get("project_id") == project_id
                and version_id in linked_versions
            ):
                test_cases.append(case)

    test_cases = list({str(item["_id"]): item for item in test_cases}.values())

    return json.dumps(
        {
            "status": "completed",
            "project_id": project_id,
            "work_item": work_item,
            "linked_requirements": requirements,
            "linked_test_cases": test_cases,
        },
        ensure_ascii=False,
        default=str,
    )


async def list_all_requirement_test_cases(project_id, requirement_id, config):
    page_size = 500
    max_items = 20000
    first = await require_operation(
        "GET",
        f"/du-an/{project_id}/ca-kiem-thu?requirement_id={requirement_id}&page=1&page_size={page_size}",
        config,
    )
    if not isinstance(first, dict):
        raise AutomationOperationError("WORK_ITEM_IMPACT_PAGINATION_INVALID")

    total = first.get("total")
    total_pages = first.get("total_pages")
    if isinstance(total, int) and not isinstance(total, bool) and total >= max_items:
        raise AutomationOperationError("WORK_ITEM_IMPACT_RESULT_LIMIT_REACHED")
    if (
        not isinstance(total, int)
        or isinstance(total, bool)
        or total < 0
        or total > max_items
        or not isinstance(total_pages, int)
        or isinstance(total_pages, bool)
        or total_pages < 0
        or total_pages != math.ceil(total / page_size)
        or first.get("page") != 1
        or first.get("page_size") != page_size
        or not isinstance(first.get("items"), list)
    ):
        raise AutomationOperationError("WORK_ITEM_IMPACT_PAGINATION_INVALID")

    items = list(first["items"])
    for page in range(2, total_pages + 1):
        result = await require_operation(
            "GET",
            f"/du-an/{project_id}/ca-kiem-thu?requirement_id={requirement_id}&page={page}&page_size={page_size}",
            config,
        )
        if (
            not isinstance(result, dict)
            or result.get("page") != page
            or result.get("page_size") != page_size
            or result.get("total") != total
            or result.get("total_pages") != total_pages
            or not isinstance(result.get("items"), list)
        ):
            raise AutomationOperationError("WORK_ITEM_IMPACT_PAGINATION_CHANGED")
        items.extend(result["items"])

    identifiers = [str(item.get("_id") or "") for item in items if isinstance(item, dict)]
    if (
        len(items) != total
        or len(identifiers) != len(items)
        or any(not identifier for identifier in identifiers)
        or len(set(identifiers)) != len(identifiers)
        or any(item.get("project_id") != project_id for item in items)
    ):
        raise AutomationOperationError("WORK_ITEM_IMPACT_PAGINATION_INCOMPLETE")
    return items

@with_tool_access(("analysis", "execution", "reporting"), "READ", "defect.read")
async def get_historical_defects(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read defect history as evidence for testing proposals"""
    return await call("GET", f"/du-an/{project_id}/loi", config)

@with_tool_access(("analysis",), "PROPOSE", "impact.execute")
async def create_impact_analysis(
    change_set_id: Annotated[str, Field(description="Change set identifier")], config: RunnableConfig = None
) -> str:
    """Run evidence grounded impact analysis for a change set"""
    return await call("POST", f"/bo-thay-doi/{change_set_id}/phan-tich-anh-huong", config)

@with_tool_access(("analysis",), "PROPOSE", "ai.create_proposal")
async def create_maintenance_proposal(
    impact_analysis_id: Annotated[str, Field(description="Impact analysis identifier")],
    config: RunnableConfig = None,
) -> str:
    """Create a maintenance proposal from verified impact evidence"""
    return await call("POST", f"/phan-tich-anh-huong/{impact_analysis_id}/de-xuat-bao-tri", config)

@with_tool_access(("analysis",), "PROPOSE", "ai.generate_regression")
async def create_regression_recommendation(
    change_set_id: Annotated[str, Field(description="Change set identifier")], config: RunnableConfig = None
) -> str:
    """Create a regression recommendation from risk traceability and defect history"""
    return await call("POST", f"/bo-thay-doi/{change_set_id}/de-xuat-hoi-quy", config)


@with_tool_access(("analysis",), "PROPOSE", "impact.execute")
async def analyze_change_impact(
    change_set_id: Annotated[str, Field(description="Change set identifier")], config: RunnableConfig = None
) -> str:
    """Analyze the impact of a change set"""
    return await call(
        "POST", f"/bo-thay-doi/{change_set_id}/phan-tich-anh-huong", config,
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )

@with_tool_access(("analysis",), "PROPOSE", "ai.generate_regression")
async def suggest_regression_scope(
    change_set_id: Annotated[str, Field(description="Change set identifier")], config: RunnableConfig = None
) -> str:
    """Recommend regression scope from a change set"""
    return await call(
        "POST", f"/bo-thay-doi/{change_set_id}/de-xuat-hoi-quy", config,
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )


@with_tool_access(
    ("execution", "analysis", "reporting"),
    "READ",
    "testrun.read",
    owner_domain="execution",
    label="Lịch sử thực thi",
    user_selectable=True,
)

async def get_execution_history(
    project_id: Annotated[str, Field(description="Project identifier")], config: RunnableConfig = None
) -> str:
    """Read project test run and execution history"""
    return await call("GET", f"/du-an/{project_id}/lan-chay-kiem-thu", config)

@with_tool_access(("analysis", "execution", "reporting"), "READ", "defect.read")
async def get_bug_history(
    project_id: Annotated[str, Field(description="Project identifier")], config: RunnableConfig = None
) -> str:
    """Read project defect history"""
    return await call("GET", f"/du-an/{project_id}/loi", config)

@with_tool_access(("execution", "analysis"), "PROPOSE", "ai.suggest_bug_trace")
async def link_bug_candidates(
    defect_id: Annotated[str, Field(description="Defect identifier")], config: RunnableConfig = None
) -> str:
    """Find trace candidates for a defect"""
    return await call("GET", f"/loi/{defect_id}/ung-vien-truy-vet", config)

