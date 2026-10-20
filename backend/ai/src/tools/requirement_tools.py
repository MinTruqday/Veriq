import json
from typing import Annotated
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.prompts.requirement_analysis import requirement_quality_analysis_instruction
from src.tools.registry import with_tool_access
from src.tools.testing_api import call, parse


@with_tool_access(("requirement", "analysis"), "READ", "requirement.version.read")
async def get_requirement_version(
    requirement_version_id: Annotated[str, Field(description="Requirement version identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read one immutable requirement version and its evidence"""
    return await call("GET", f"/phien-ban-yeu-cau/{requirement_version_id}", config)

@with_tool_access(("requirement", "analysis"), "READ", "requirement.diff.read")
async def compare_requirement_versions(
    requirement_id: Annotated[str, Field(description="Requirement identifier")],
    from_version_id: Annotated[str, Field(description="Source version identifier")],
    to_version_id: Annotated[str, Field(description="Target version identifier")],
    config: RunnableConfig = None,
) -> str:
    """Compare two versions of the same requirement semantically"""
    return await call(
        "POST",
        f"/yeu-cau/{requirement_id}/so-sanh",
        config,
        {"from_version_id": from_version_id, "to_version_id": to_version_id},
    )

@with_tool_access(("requirement", "test_design"), "READ", "requirement.read")
async def get_acceptance_criteria(
    requirement_id: Annotated[str, Field(description="Requirement identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read versioned acceptance criteria with authority metadata"""
    return await call("GET", f"/yeu-cau/{requirement_id}", config)

@with_tool_access(("analysis", "reporting"), "READ", "trace.read")
async def get_trace_links(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read the trace link matrix including confirmation status"""
    return await call("GET", f"/du-an/{project_id}/truy-vet", config)

@with_tool_access(
    ("requirement",),
    "MUTATE",
    "requirement.create",
    {
        "path": "/du-an/{project_id}/mau-yeu-cau/{identifier}",
        "identifier": "$result._id",
        "expected": {"_id": "$result._id", "project_id": "$project.id", "status": "DRAFT", "revision": "$result.revision"},
    },
)
async def synthesize_requirement_template(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    name: Annotated[str, Field(min_length=2, max_length=200, description="Template title supported by the project evidence")],
    product_types: Annotated[list[str], Field(min_length=1, max_length=6, description="Supported product types evidenced by the project source")],
    source_document_ids: Annotated[list[str], Field(description="Permitted source document identifiers")],
    source_template_ids: Annotated[list[str], Field(description="Existing template identifiers used as evidence")] = Field(default_factory=list),
    instruction: Annotated[str, Field(description="Evidence grounded synthesis objective")] = "",
    config: RunnableConfig = None,
) -> str:
    """Create a requirement-template draft from permitted source documents without waiting for a separate AI confirmation"""
    payload = {
        "name": name,
        "product_types": product_types,
        "source_document_ids": source_document_ids,
        "source_template_ids": source_template_ids,
        "instruction": instruction,
    }
    return await call("POST", f"/du-an/{project_id}/mau-yeu-cau/tong-hop", config, payload)


@with_tool_access(
    ("requirement",),
    "MUTATE",
    "requirement.create",
    {
        "path": "/yeu-cau/{identifier}",
        "identifier": "$result._id",
        "expected": {
            "_id": "$result._id",
            "project_id": "$project.id",
            "current_version.status": "DRAFT",
            "current_version.revision": 1,
        },
    },
)

async def create_requirement_draft(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    requirement_json: Annotated[
        str,
        Field(description="A single Requirement draft supported by supplied source evidence"),
    ],
    config: RunnableConfig = None,
) -> str:
    """Create a source-grounded Requirement draft in the current project"""
    payload = parse(requirement_json)
    if not payload:
        return json.dumps({"status": "invalid_payload"})
    payload["source_refs"] = [
        reference
        for reference in payload.get("source_refs", [])
        if isinstance(reference, dict)
    ]
    return await call("POST", f"/du-an/{project_id}/yeu-cau", config, payload)

@with_tool_access(("analysis", "test_design"), "PROPOSE", "trace.create")
async def create_trace_link_suggestion(
    trace_json: Annotated[
        str, Field(description="Trace link JSON with evidence confidence and project identifier")
    ],
    config: RunnableConfig = None,
) -> str:
    """Create an unconfirmed trace link suggestion"""
    payload = parse(trace_json)
    if payload:
        payload["origin"] = "ai_suggested"
    return (
        await call("POST", "/lien-ket-truy-vet", config, payload)
        if payload
        else json.dumps({"status": "invalid_payload"})
    )

@with_tool_access(
    ("analysis",),
    "MUTATE",
    "trace.confirm",
    {
        "path": "/lien-ket-truy-vet/{identifier}",
        "identifier": "$arguments.trace_link_id",
        "expected": {"_id": "$arguments.trace_link_id", "project_id": "$project.id", "status": "CONFIRMED", "revision": "$result.revision"},
    },
)
async def confirm_trace_link(
    trace_link_id: Annotated[str, Field(description="Trace link identifier")], config: RunnableConfig = None
) -> str:
    """Confirm a trace link when the invoking actor has confirmation permission"""
    return await call("POST", f"/lien-ket-truy-vet/{trace_link_id}/xac-nhan", config)


@with_tool_access(
    ("requirement",),
    "MUTATE",
    "requirement.approve",
    {
        "path": "/phien-ban-yeu-cau/{identifier}",
        "identifier": "$arguments.requirement_version_id",
        "expected": {"_id": "$arguments.requirement_version_id", "project_id": "$project.id", "status": "BASELINED", "revision": "$result.revision"},
    },
)

async def baseline_requirement_version(
    requirement_version_id: Annotated[str, Field(description="Requirement version identifier")],
    expected_revision: Annotated[int, Field(ge=1, description="Current revision")],
    config: RunnableConfig = None,
) -> str:
    """Baseline a requirement version when the invoking actor has baseline permission"""
    return await call(
        "POST",
        f"/phien-ban-yeu-cau/{requirement_version_id}/chot-chuan",
        config,
        {"expected_revision": expected_revision},
    )


@with_tool_access(("requirement", "analysis"), "READ", "requirement.read")
async def get_requirement(
    requirement_id: Annotated[str, Field(description="Requirement identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read a requirement with its current version"""
    return await call("GET", f"/yeu-cau/{requirement_id}", config)

@with_tool_access(("analysis",), "READ", "changeset.read")
async def get_change_facts(
    change_set_id: Annotated[str, Field(description="Change set identifier")], config: RunnableConfig = None
) -> str:
    """Read a stored change set and its change facts"""
    return await call("GET", f"/bo-thay-doi/{change_set_id}", config)

@with_tool_access(("requirement",), "PROPOSE", "ai.run_lint")
async def lint_requirement(
    requirement_version_id: Annotated[str, Field(description="Requirement version identifier")],
    config: RunnableConfig = None,
) -> str:
    """Evaluate requirement version quality"""
    return await call(
        "POST",
        f"/phien-ban-yeu-cau/{requirement_version_id}/ai/kiem-tra",
        config,
        {
            "idempotency_key": f"agent-requirement-analysis-{uuid4().hex}",
        "instruction": requirement_quality_analysis_instruction(),
        },
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )

@with_tool_access(("analysis", "reporting"), "READ", "trace.read")
async def get_traceability_links(
    project_id: Annotated[str, Field(description="Project identifier")], config: RunnableConfig = None
) -> str:
    """Read traceability links within a project"""
    return await call("GET", f"/du-an/{project_id}/truy-vet", config)

