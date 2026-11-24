from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.test_analysis import (
    AnalysisFindingAssignment,
    AnalysisFindingCreate,
    AnalysisFindingTransition,
    FindingResolutionInput,
    TestAnalysisAIInput,
    TestAnalysisInput,
    TestConditionBulkPriorityInput,
    TestConditionCreate,
    TestConditionPatch,
    TestConditionTransition,
)
from src.modules.design.services.test_analysis import (
    assign_analysis_finding,
    bulk_prioritize_conditions,
    condition_coverage,
    create_analysis_finding,
    create_condition,
    get_condition_for_user,
    list_analysis_findings,
    list_ai_analysis_results,
    list_conditions,
    list_test_basis,
    resolve_finding,
    review_condition,
    run_ai_analysis,
    run_deterministic_analysis,
    transition_analysis_finding,
    transition_condition,
    update_condition,
)

router = APIRouter(prefix="/kiem-thu", tags=["Phân tích kiểm thử"])


@router.get("/du-an/{project_id}/dieu-kien-kiem-thu")
async def list_test_conditions(
    project_id: str,
    q: str = Query(default="", max_length=300),
    status: str = Query(default="", max_length=30),
    risk: str = Query(default="", max_length=30),
    testability_status: str = Query(default="", max_length=40),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_conditions(
            project_id, user, q, status, risk, testability_status, page, page_size
        )
    )


@router.post("/du-an/{project_id}/dieu-kien-kiem-thu", status_code=201)
async def create_test_condition(
    project_id: str, payload: TestConditionCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await create_condition(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/dieu-kien-kiem-thu/{condition_id}")
async def get_test_condition(condition_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await get_condition_for_user(condition_id, user)
    return envelope(value, revision=value["revision"])


@router.patch("/dieu-kien-kiem-thu/{condition_id}")
async def patch_test_condition(
    condition_id: str, payload: TestConditionPatch, user: CurrentUser = Depends(get_current_user)
):
    value = await update_condition(condition_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/dieu-kien-kiem-thu/{condition_id}/gui-ra-soat")
async def submit_test_condition_review(
    condition_id: str,
    payload: TestConditionTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_condition(condition_id, payload, user, "submit")
    return envelope(value, revision=value["revision"])


@router.post("/dieu-kien-kiem-thu/{condition_id}/phe-duyet")
async def approve_test_condition(
    condition_id: str,
    payload: TestConditionTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_condition(condition_id, payload, user, "approve")
    return envelope(value, revision=value["revision"])


@router.post("/dieu-kien-kiem-thu/{condition_id}/ra-soat")
async def review_test_condition(
    condition_id: str,
    payload: TestConditionTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await review_condition(condition_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/dieu-kien-kiem-thu/{condition_id}/luu-tru")
async def archive_test_condition(
    condition_id: str,
    payload: TestConditionTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_condition(condition_id, payload, user, "archive")
    return envelope(value, revision=value["revision"])


@router.post("/dieu-kien-kiem-thu/{condition_id}/ket-qua/{finding_id}/giai-quyet")
async def resolve_test_analysis_finding(
    condition_id: str,
    finding_id: str,
    payload: FindingResolutionInput,
    user: CurrentUser = Depends(get_current_user),
):
    value = await resolve_finding(condition_id, finding_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/phan-tich-kiem-thu/ai")
async def list_test_analysis_ai_results(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    idempotency_key: str | None = Query(default=None, min_length=8, max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_ai_analysis_results(project_id, user, limit, idempotency_key)
    )


@router.post("/du-an/{project_id}/phan-tich-kiem-thu/ai", status_code=201)
async def run_test_analysis_ai(
    project_id: str, payload: TestAnalysisAIInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await run_ai_analysis(project_id, payload, user))


@router.get("/du-an/{project_id}/phan-tich-kiem-thu/truy-vet")
async def get_test_condition_coverage(
    project_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await condition_coverage(project_id, user))


@router.get("/du-an/{project_id}/phan-tich-kiem-thu/co-so")
async def list_test_analysis_basis(
    project_id: str,
    artifact_type: str = Query(default="", max_length=100),
    q: str = Query(default="", max_length=300),
    limit: int = Query(default=200, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await list_test_basis(project_id, user, artifact_type, q, limit))


@router.post("/du-an/{project_id}/phan-tich-kiem-thu/kiem-tra")
async def run_deterministic_test_analysis(
    project_id: str, payload: TestAnalysisInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await run_deterministic_analysis(project_id, payload, user))


@router.get("/du-an/{project_id}/ket-qua-phan-tich")
async def list_test_analysis_findings(
    project_id: str,
    status: str = Query(
        default="", pattern="^(OPEN|IN_PROGRESS|RESOLVED|VERIFIED|ACCEPTED_RISK)?$"
    ),
    limit: int = Query(default=500, ge=1, le=1000),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await list_analysis_findings(project_id, user, status, limit))


@router.post("/du-an/{project_id}/ket-qua-phan-tich", status_code=201)
async def create_test_analysis_finding(
    project_id: str, payload: AnalysisFindingCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await create_analysis_finding(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/ket-qua-phan-tich/{finding_id}/phan-cong")
async def assign_test_analysis_finding(
    finding_id: str,
    payload: AnalysisFindingAssignment,
    user: CurrentUser = Depends(get_current_user),
):
    value = await assign_analysis_finding(finding_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/ket-qua-phan-tich/{finding_id}/giai-quyet")
async def resolve_standalone_test_analysis_finding(
    finding_id: str,
    payload: AnalysisFindingTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_analysis_finding(finding_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/ket-qua-phan-tich/{finding_id}/xac-minh")
async def verify_test_analysis_finding(
    finding_id: str,
    payload: AnalysisFindingTransition,
    user: CurrentUser = Depends(get_current_user),
):
    value = await transition_analysis_finding(finding_id, payload, user, verify=True)
    return envelope(value, revision=value["revision"])


@router.patch("/du-an/{project_id}/dieu-kien-kiem-thu/uu-tien")
async def bulk_prioritize_test_conditions(
    project_id: str,
    payload: TestConditionBulkPriorityInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await bulk_prioritize_conditions(project_id, payload, user))
