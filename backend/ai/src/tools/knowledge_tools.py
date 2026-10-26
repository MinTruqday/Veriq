import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.tools.registry import with_tool_access
from src.tools.testing_api import call


@with_tool_access(("reporting",), "READ", "project.read")
async def get_project_context(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read a project and dashboard within the current tenant"""
    project = await call("GET", f"/du-an/{project_id}", config)
    dashboard = await call("GET", f"/du-an/{project_id}/tong-quan", config)
    return json.dumps(
        {"project": json.loads(project), "dashboard": json.loads(dashboard)}, ensure_ascii=False
    )

@with_tool_access(("requirement", "reporting"), "READ", "knowledge.read")
async def search_project_knowledge(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    query: Annotated[str, Field(min_length=1, description="Artifact search query")],
    config: RunnableConfig = None,
) -> str:
    """Search for evidence within one testing project"""
    return await call(
        "POST",
        f"/du-an/{project_id}/tri-thuc/tim-kiem",
        config,
        {"query": query, "artifact_types": [], "limit": 20},
    )

@with_tool_access(
    ("requirement", "test_design", "analysis", "execution", "reporting"),
    "READ",
    "knowledge.read",
    owner_domain="analysis",
    label="Tìm bằng chứng dự án",
    user_selectable=True,
)
async def retrieve_project_evidence(
    project_id: Annotated[str, Field(description="Project identifier")],
    instruction: Annotated[str, Field(min_length=1, description="Evidence retrieval objective")],
    artifact_types: Annotated[
        str, Field(description="Comma separated artifact type list")
    ] = "",
    config: RunnableConfig = None,
) -> str:
    """Retrieve knowledge evidence within the project boundary"""
    types = [value.strip() for value in artifact_types.split(",") if value.strip()]
    return await call(
        "POST",
        f"/du-an/{project_id}/tri-thuc/tim-kiem",
        config,
        {"query": instruction, "artifact_types": types, "limit": 20},
    )

