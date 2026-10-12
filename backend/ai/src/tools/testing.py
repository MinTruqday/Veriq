import json
from typing import Annotated
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import Field

from src.core.infrastructure.configuration import settings
from src.tools.registry import with_tool_access
from src.tools.http_client import INTERNAL_API_URL, make_api_request


def headers(config):
    token = (config or {}).get("configurable", {}).get("token")
    return {"Authorization": token, "X-Internal-Token": settings.SECRET_KEY} if token else None


async def call(method, path, config, payload=None):
    request_headers = headers(config)
    if not request_headers:
        return json.dumps({"status": "authentication_required"})
    response = await make_api_request(
        method,
        f"{INTERNAL_API_URL}/kiem-thu{path}",
        headers=request_headers,
        json=payload,
        timeout=60,
    )
    try:
        body = response.json()
    except ValueError:
        body = {"error": {"code": "UPSTREAM_RESPONSE_INVALID"}}
    if response.status_code >= 400:
        return json.dumps(
            {
                "status": "qa_operation_failed",
                "upstream_status": response.status_code,
                "error": body.get("error"),
            },
            ensure_ascii=False,
        )
    return json.dumps(body.get("data", body), ensure_ascii=False, default=str)


def parse(value):
    try:
        result = json.loads(value)
        return result if isinstance(result, dict) else None
    except (TypeError, json.JSONDecodeError):
        return None


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


@with_tool_access(("requirement", "analysis"), "READ", "requirement.version.read")
async def get_requirement_version(
    requirement_id: Annotated[str, Field(description="Requirement identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read a requirement with its current version and acceptance criteria"""
    return await call("GET", f"/yeu-cau/{requirement_id}", config)


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


@with_tool_access(("execution", "analysis", "reporting"), "READ", "testrun.read")
async def get_test_results(
    test_run_id: Annotated[str, Field(description="Test run identifier")], config: RunnableConfig = None
) -> str:
    """Read a test run snapshot with results and related defects"""
    return await call("GET", f"/lan-chay-kiem-thu/{test_run_id}", config)


@with_tool_access(("analysis", "execution", "reporting"), "READ", "defect.read")
async def get_historical_defects(
    project_id: Annotated[str, Field(description="Testing project identifier")],
    config: RunnableConfig = None,
) -> str:
    """Read defect history as evidence for testing proposals"""
    return await call("GET", f"/du-an/{project_id}/loi", config)


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
    True,
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
    """Create a test case draft for human review"""
    payload = parse(draft_json)
    return (
        await call("POST", f"/du-an/{project_id}/ban-nhap-ca-kiem-thu", config, payload)
        if payload
        else json.dumps({"status": "invalid_payload"})
    )


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
    """Create a maintenance proposal pending human review"""
    return await call("POST", f"/phan-tich-anh-huong/{impact_analysis_id}/de-xuat-bao-tri", config)


@with_tool_access(("analysis",), "PROPOSE", "ai.generate_regression")
async def create_regression_recommendation(
    change_set_id: Annotated[str, Field(description="Change set identifier")], config: RunnableConfig = None
) -> str:
    """Create a regression recommendation from risk traceability and defect history"""
    return await call("POST", f"/bo-thay-doi/{change_set_id}/de-xuat-hoi-quy", config)


@with_tool_access(
    ("analysis",),
    "MUTATE",
    "trace.confirm",
    True,
    {
        "path": "/lien-ket-truy-vet/{identifier}",
        "identifier": "$arguments.trace_link_id",
        "expected": {"_id": "$arguments.trace_link_id", "project_id": "$project.id", "status": "CONFIRMED", "revision": "$result.revision"},
    },
)
async def confirm_trace_link(
    trace_link_id: Annotated[str, Field(description="Trace link identifier")], config: RunnableConfig = None
) -> str:
    """Confirm a trace link after an explicit human decision"""
    return await call("POST", f"/lien-ket-truy-vet/{trace_link_id}/xac-nhan", config)


@with_tool_access(
    ("requirement",),
    "MUTATE",
    "requirement.approve",
    True,
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
    """Baseline a requirement version after explicit human approval"""
    return await call(
        "POST",
        f"/phien-ban-yeu-cau/{requirement_version_id}/chot-chuan",
        config,
        {"expected_revision": expected_revision},
    )


@with_tool_access(
    ("test_design",),
    "MUTATE",
    "testcase.approve",
    True,
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
    """Freeze a test case draft into a version after human approval"""
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
    True,
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
        str, Field(min_length=2, description="User confirmed obsolescence reason")
    ],
    config: RunnableConfig = None,
) -> str:
    """Mark a test case obsolete after an explicit human decision"""
    return await call(
        "POST",
        f"/ca-kiem-thu/{test_case_id}/ngung-hieu-luc",
        config,
        {"expected_current_version_id": expected_current_version_id, "reason": reason},
    )


@with_tool_access(
    ("test_design",),
    "MUTATE",
    "testcase.update",
    True,
    {
        "path": "/de-xuat-bao-tri/{identifier}",
        "identifier": "$arguments.proposal_id",
        "expected": {"_id": "$arguments.proposal_id", "project_id": "$project.id", "status": "$result.proposal.status", "applied_artifact_id": "$result.result._id", "revision": "$result.proposal.revision"},
    },
)
async def apply_test_case_revision(
    proposal_id: Annotated[str, Field(description="Maintenance proposal identifier")],
    expected_revision: Annotated[int, Field(ge=1, description="Proposal revision")],
    patch_json: Annotated[str, Field(description="User approved patch JSON")] = "{}",
    config: RunnableConfig = None,
) -> str:
    """Apply a test case revision through a human accepted proposal"""
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
            "instruction": "Analyze requirement quality and propose evidence grounded revisions",
        },
    )


@with_tool_access(("analysis", "reporting"), "READ", "trace.read")
async def get_traceability_links(
    project_id: Annotated[str, Field(description="Project identifier")], config: RunnableConfig = None
) -> str:
    """Read traceability links within a project"""
    return await call("GET", f"/du-an/{project_id}/truy-vet", config)


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
    )


@with_tool_access(("test_design",), "PROPOSE", "ai.generate_testcase")
async def generate_testcases(
    requirement_version_id: Annotated[str, Field(description="Requirement version identifier")],
    instruction: Annotated[str, Field(description="Test case generation instruction")] = "",
    config: RunnableConfig = None,
) -> str:
    """Generate a structured test case draft from a requirement version"""
    return await call(
        "POST",
        f"/phien-ban-yeu-cau/{requirement_version_id}/ai/sinh-ca-kiem-thu",
        config,
        {"instruction": instruction},
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


@with_tool_access(("analysis",), "PROPOSE", "impact.execute")
async def analyze_change_impact(
    change_set_id: Annotated[str, Field(description="Change set identifier")], config: RunnableConfig = None
) -> str:
    """Analyze the impact of a change set"""
    return await call("POST", f"/bo-thay-doi/{change_set_id}/phan-tich-anh-huong", config)


@with_tool_access(("analysis", "test_design"), "PROPOSE", "ai.create_proposal")
async def propose_testcase_revision(
    impact_analysis_id: Annotated[str, Field(description="Impact analysis identifier")],
    config: RunnableConfig = None,
) -> str:
    """Generate a test case update proposal pending review"""
    return await call("POST", f"/phan-tich-anh-huong/{impact_analysis_id}/de-xuat-bao-tri", config)


@with_tool_access(("analysis", "test_design"), "PROPOSE", "ai.create_proposal")
async def propose_new_testcase(
    impact_analysis_id: Annotated[str, Field(description="Impact analysis identifier")],
    config: RunnableConfig = None,
) -> str:
    """Generate a new test case proposal pending review"""
    return await call("POST", f"/phan-tich-anh-huong/{impact_analysis_id}/de-xuat-bao-tri", config)


@with_tool_access(("analysis", "test_design"), "PROPOSE", "ai.create_proposal")
async def propose_obsolete_testcase(
    impact_analysis_id: Annotated[str, Field(description="Impact analysis identifier")],
    config: RunnableConfig = None,
) -> str:
    """Generate a test case obsolescence proposal pending review"""
    return await call("POST", f"/phan-tich-anh-huong/{impact_analysis_id}/de-xuat-bao-tri", config)


@with_tool_access(("analysis",), "PROPOSE", "ai.generate_regression")
async def suggest_regression_scope(
    change_set_id: Annotated[str, Field(description="Change set identifier")], config: RunnableConfig = None
) -> str:
    """Recommend regression scope from a change set"""
    return await call("POST", f"/bo-thay-doi/{change_set_id}/de-xuat-hoi-quy", config)


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
