import json
from typing import Annotated
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.tools.registry import with_tool_access
from src.tools.testing_api import call, parse


@with_tool_access(("test_design", "analysis"), "READ", "testcase.read")
async def search_test_cases(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    query: Annotated[str, Field(description="Test case search query")] = "",
    config: RunnableConfig = None,
) -> str:
    """Search for test cases within the project boundary"""
    return await call("GET", f"/du-an/{project_id}/ca-kiem-thu?q={query}", config)

@with_tool_access(("test_design", "execution", "analysis"), "READ", "testcase.version.read")
async def get_test_case_version(
    test_case_id: Annotated[str, Field(description="Test case identifier")], config: RunnableConfig = None
) -> str:
    """Read the immutable test case version history"""
    return await call("GET", f"/ca-kiem-thu/{test_case_id}/phien-ban", config)

@with_tool_access(("test_design", "analysis"), "READ", "testcase.read")
async def get_test_case_draft(
    draft_id: Annotated[str, Field(description="Test Case draft identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read the current editable Test Case draft"""
    return await call("GET", f"/ban-nhap-ca-kiem-thu/{draft_id}", config)

@with_tool_access(("test_design", "analysis"), "READ", "testcase.version.read")
async def get_test_case_version_by_id(
    version_id: Annotated[str, Field(description="Immutable Test Case version identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read one immutable Test Case version by its identifier"""
    return await call("GET", f"/phien-ban-ca-kiem-thu/{version_id}", config)

@with_tool_access(("test_design",), "READ", "testcase.duplicate_check")
async def find_near_duplicates(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    config: RunnableConfig = None,
) -> str:
    """Find near duplicate test cases and return structured evidence"""
    return await call("GET", f"/du-an/{project_id}/ca-kiem-thu/trung-lap", config)


@with_tool_access(
    ("test_design",),
    "MUTATE",
    "testcase.create",
    {
        "path": "/ban-nhap-ca-kiem-thu/{identifier}",
        "identifier": "$result._id",
        "expected": {"_id": "$result._id", "project_id": "$project.id", "status": "DRAFT", "revision": "$result.revision"},
    },
)

async def create_test_case_draft(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    draft_json: Annotated[
        str, Field(description="Test case draft JSON containing Tiptap documents")
    ],
    config: RunnableConfig = None,
) -> str:
    """Create an evidence-grounded test case draft for continued processing by the authorized workflow"""
    payload = parse(draft_json)
    return (
        await call("POST", f"/du-an/{project_id}/ban-nhap-ca-kiem-thu", config, payload)
        if payload
        else json.dumps({"status": "invalid_payload"})
    )

@with_tool_access(
    ("test_design",),
    "MUTATE",
    "testcase.approve",
    {
        "path": "/ca-kiem-thu/{identifier}",
        "identifier": "$result.test_case._id",
        "expected": {"_id": "$result.test_case._id", "project_id": "$project.id", "status": "$result.test_case.status", "current_version_id": "$result.version._id"},
    },
)
async def approve_test_case_version(
    test_case_draft_id: Annotated[str, Field(description="Test case draft identifier")],
    expected_revision: Annotated[int, Field(ge=1, description="Current revision")],
    change_reason: Annotated[str, Field(description="Approval reason")],
    config: RunnableConfig = None,
) -> str:
    """Freeze a test case draft into a version when project permissions allow version freezing"""
    return await call(
        "POST",
        f"/ban-nhap-ca-kiem-thu/{test_case_draft_id}/dong-bang",
        config,
        {"expected_revision": expected_revision, "change_reason": change_reason},
    )


@with_tool_access(
    ("test_design",),
    "MUTATE",
    "testcase.archive",
    {
        "path": "/ca-kiem-thu/{identifier}",
        "identifier": "$arguments.test_case_id",
        "expected": {"_id": "$arguments.test_case_id", "project_id": "$project.id", "status": "OBSOLETE", "current_version_id": "$arguments.expected_current_version_id"},
    },
)

async def mark_test_case_obsolete(
    test_case_id: Annotated[str, Field(description="Test case identifier")],
    expected_current_version_id: Annotated[str, Field(description="Current version identifier")],
    reason: Annotated[
        str, Field(min_length=2, description="Evidence-grounded obsolescence reason")
    ],
    config: RunnableConfig = None,
) -> str:
    """Mark a test case obsolete when the invoking actor has archive permission"""
    return await call(
        "POST",
        f"/ca-kiem-thu/{test_case_id}/ngung-hieu-luc",
        config,
        {"expected_current_version_id": expected_current_version_id, "reason": reason},
    )


@with_tool_access(
    ("test_design",),
    "MUTATE",
    "proposal.approve",
    {
        "path": "/de-xuat-bao-tri/{identifier}",
        "identifier": "$arguments.proposal_id",
        "expected": {"_id": "$arguments.proposal_id", "project_id": "$project.id", "status": "$result.proposal.status", "applied_artifact_id": "$result.result._id", "revision": "$result.proposal.revision"},
    },
)

async def apply_test_case_revision(
    proposal_id: Annotated[str, Field(description="Maintenance proposal identifier")],
    expected_revision: Annotated[int, Field(ge=1, description="Proposal revision")],
    patch_json: Annotated[str, Field(description="Evidence-grounded revision patch JSON")] = "{}",
    config: RunnableConfig = None,
) -> str:
    """Apply an evidence-grounded test case revision when the invoking actor has proposal approval permission"""
    patch = parse(patch_json)
    return await call(
        "POST",
        f"/de-xuat-bao-tri/{proposal_id}/chap-nhan-co-chinh-sua",
        config,
        {
            "expected_revision": expected_revision,
            "patch": patch or {},
            "review_note": "Approved through the testing agent tool",
        },
    )


@with_tool_access(
    ("analysis", "test_design"),
    "MUTATE",
    "proposal.approve",
    {
        "path": "/de-xuat-bao-tri/{identifier}",
        "identifier": "$arguments.proposal_id",
        "expected": {
            "_id": "$arguments.proposal_id",
            "project_id": "$project.id",
            "status": "$result.proposal.status",
            "applied_artifact_id": "$result.result._id",
            "revision": "$result.proposal.revision",
        },
    },
)

async def apply_maintenance_proposal(
    project_id: Annotated[str, Field(description="Project identifier")],
    proposal_id: Annotated[str, Field(description="Evidence-grounded maintenance proposal identifier")],
    expected_revision: Annotated[int, Field(ge=1, description="Current proposal revision")],
    review_note: Annotated[str, Field(min_length=2, description="Reason the verified proposal is applied")],
    config: RunnableConfig = None,
) -> str:
    """Apply a validated maintenance proposal when the automation principal has proposal approval permission"""
    return await call(
        "POST",
        f"/du-an/{project_id}/de-xuat-ai/{proposal_id}/phe-duyet",
        config,
        {"expected_revision": expected_revision, "review_note": review_note},
    )


@with_tool_access(("test_design", "analysis"), "READ", "testcase.read")
async def search_related_testcases(
    project_id: Annotated[str, Field(description="Project identifier")],
    query: Annotated[str, Field(description="Relevant content query")],
    config: RunnableConfig = None,
) -> str:
    """Find related test cases within a project"""
    return await call("GET", f"/du-an/{project_id}/ca-kiem-thu?q={query}", config)

@with_tool_access(("test_design",), "PROPOSE", "ai.generate_scenario")
async def generate_test_scenarios(
    requirement_version_id: Annotated[str, Field(description="Requirement version identifier")],
    instruction: Annotated[str, Field(description="Scenario generation instruction")] = "",
    config: RunnableConfig = None,
) -> str:
    """Generate a test scenario draft from a requirement version"""
    return await call(
        "POST",
        f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-kich-ban",
        config,
        {"instruction": instruction},
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )

@with_tool_access(("test_design",), "PROPOSE", "ai.generate_testcase")
async def generate_testcases(
    requirement_version_id: Annotated[str, Field(description="Requirement version identifier")],
    instruction: Annotated[str, Field(description="Test case generation instruction")] = "",
    config: RunnableConfig = None,
) -> str:
    """Generate evidence-grounded test cases for the automation run to save after duplicate checks"""
    return await call(
        "POST",
        f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu",
        config,
        {"instruction": instruction, "preview_only": True},
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )

@with_tool_access(("test_design",), "READ", "testcase.lint")
async def lint_testcase(
    test_case_draft_id: Annotated[str, Field(description="Test case draft identifier")],
    config: RunnableConfig = None,
) -> str:
    """Evaluate test case draft quality"""
    return await call("POST", f"/ban-nhap-ca-kiem-thu/{test_case_draft_id}/kiem-tra", config)

@with_tool_access(("test_design",), "READ", "testcase.duplicate_check")
async def find_duplicate_testcases(
    project_id: Annotated[str, Field(description="Project identifier")], config: RunnableConfig = None
) -> str:
    """Find duplicate or near duplicate test cases"""
    return await call("GET", f"/du-an/{project_id}/ca-kiem-thu/trung-lap", config)

@with_tool_access(("test_design", "analysis", "reporting"), "READ", "coverage.read")
async def calculate_coverage(
    project_id: Annotated[str, Field(description="Project identifier")], config: RunnableConfig = None
) -> str:
    """Compute deterministic project coverage"""
    return await call("GET", f"/du-an/{project_id}/do-phu", config)

@with_tool_access(("analysis", "test_design"), "PROPOSE", "ai.create_proposal")
async def propose_testcase_revision(
    impact_analysis_id: Annotated[str, Field(description="Impact analysis identifier")],
    config: RunnableConfig = None,
) -> str:
    """Generate a test case update proposal pending review"""
    return await call(
        "POST", f"/phan-tich-anh-huong/{impact_analysis_id}/de-xuat-bao-tri", config,
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )

@with_tool_access(("analysis", "test_design"), "PROPOSE", "ai.create_proposal")
async def propose_new_testcase(
    impact_analysis_id: Annotated[str, Field(description="Impact analysis identifier")],
    config: RunnableConfig = None,
) -> str:
    """Generate a new test case proposal pending review"""
    return await call(
        "POST", f"/phan-tich-anh-huong/{impact_analysis_id}/de-xuat-bao-tri", config,
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )

@with_tool_access(("analysis", "test_design"), "PROPOSE", "ai.create_proposal")
async def propose_obsolete_testcase(
    impact_analysis_id: Annotated[str, Field(description="Impact analysis identifier")],
    config: RunnableConfig = None,
) -> str:
    """Generate a test case obsolescence proposal pending review"""
    return await call(
        "POST", f"/phan-tich-anh-huong/{impact_analysis_id}/de-xuat-bao-tri", config,
        timeout=settings.MODEL_TIMEOUT_SECONDS,
    )

