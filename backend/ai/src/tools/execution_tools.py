import json
from typing import Annotated
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.tools.registry import with_tool_access
from src.tools.testing_api import call, parse


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

from src.tools.requirement_workflows import (
    process_changed_requirement_version,
    process_ingested_requirement_document,
)
from src.tools.execution_workflows import (
    process_approved_test_plan,
    process_changed_test_plan,
    process_recorded_defect,
)

