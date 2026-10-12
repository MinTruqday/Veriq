from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import StreamingResponse

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, get_project
from src.schemas.contracts.defects import (
    BugTraceSuggestionInput,
    DefectCreate,
    DefectPatch,
    DefectRetestInput,
    DefectTraceUpdateInput,
    DefectTransition,
)
from src.schemas.contracts.execution import (
    TestExecutionPatch,
    TestPlanPatch,
    TestResultCorrectionInput,
    TestResultInput,
    TestRunAssignmentInput,
    TestRunCreate,
    TestRunPatch,
    TestRunResumeInput,
    TestSuiteCreate,
    TestSuitePatch,
)
from src.schemas.contracts.planning import TestPlanCreate
from src.schemas.contracts.project import ProjectArchiveInput
from src.schemas.contracts.requirements import ReviewTransitionInput
from src.modules.quality.services.defect_analysis import find_duplicate_defect_pairs
from src.modules.quality.services.defect_records import (
    build_defect_export,
    create_defect_record,
    get_defect_record,
    list_defect_records,
)
from src.modules.quality.services.defect_lifecycle import (
    retest_defect_record,
    transition_defect_record,
    update_defect_record,
)
from src.modules.quality.services.defect_trace import (
    list_defect_trace_candidates,
    suggest_defect_trace_record,
    update_defect_trace_record,
)
from src.modules.execution.services.test_plan import (
    approve_test_plan_record,
    archive_test_plan_record,
    clone_test_plan_record,
    create_test_plan_record,
    get_test_plan_record,
    list_test_plan_records,
    submit_test_plan_record,
    update_test_plan_record,
    validate_test_plan_record,
)
from src.modules.execution.services.test_suite import (
    archive_test_suite_record,
    clone_test_suite_record,
    create_test_suite_record,
    get_test_suite_record,
    list_test_suite_records,
    update_test_suite_record,
)
from src.modules.execution.services.test_run import (
    abort_test_run_record,
    assign_test_run_record,
    build_test_run_report,
    complete_test_run_record,
    correct_test_result_record,
    create_test_run_record,
    get_test_run_record,
    list_test_result_records,
    list_test_run_records,
    record_test_result_entry,
    resume_test_run_record,
    start_test_run_record,
    update_test_execution_record,
    update_test_run_record,
)

router = APIRouter(prefix="/kiem-thu", tags=["Thực thi kiểm thử"])


@router.post("/ke-hoach-kiem-thu", status_code=201)
@router.post("/du-an/{project_id}/ke-hoach-kiem-thu", status_code=201)
async def create_test_plan(
    payload: TestPlanCreate,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    plan = await create_test_plan_record(payload, project_id, user)
    return envelope(plan, revision=1)


@router.get("/du-an/{project_id}/ke-hoach-kiem-thu")
async def list_test_plans(
    project_id: str,
    q: str = Query(default="", max_length=300),
    release: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    build_id: str = Query(default="", max_length=200),
    environment_id: str = Query(default="", max_length=200),
    status: str = Query(default="", max_length=30),
    sort: str = Query(default="-updated_at", max_length=80),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_test_plan_records(
            project_id,
            user,
            q=q,
            release=release,
            release_id=release_id,
            build_id=build_id,
            environment_id=environment_id,
            status=status,
            sort=sort,
        )
    )


@router.get("/ke-hoach-kiem-thu/{plan_id}")
async def get_test_plan(plan_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_test_plan_record(plan_id, user))


@router.post("/ke-hoach-kiem-thu/{plan_id}/kiem-tra")
async def validate_test_plan(plan_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await validate_test_plan_record(plan_id, user))


@router.patch("/ke-hoach-kiem-thu/{plan_id}")
async def update_test_plan(
    plan_id: str, payload: TestPlanPatch, user: CurrentUser = Depends(get_current_user)
):
    updated = await update_test_plan_record(plan_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/ke-hoach-kiem-thu/{plan_id}/gui-ra-soat")
async def submit_test_plan(
    plan_id: str, payload: ReviewTransitionInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await submit_test_plan_record(plan_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/ke-hoach-kiem-thu/{plan_id}/phe-duyet")
async def approve_test_plan(
    plan_id: str, payload: ReviewTransitionInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await approve_test_plan_record(plan_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/ke-hoach-kiem-thu/{plan_id}/luu-tru")
async def archive_test_plan(
    plan_id: str, payload: ProjectArchiveInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await archive_test_plan_record(plan_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/ke-hoach-kiem-thu/{plan_id}/nhan-ban", status_code=201)
async def clone_test_plan(plan_id: str, user: CurrentUser = Depends(get_current_user)):
    cloned = await clone_test_plan_record(plan_id, user)
    return envelope(cloned, revision=1)


@router.post("/bo-kiem-thu", status_code=201)
@router.post("/du-an/{project_id}/bo-kiem-thu", status_code=201)
async def create_test_suite(
    payload: TestSuiteCreate,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    suite = await create_test_suite_record(payload, project_id, user)
    return envelope(suite, revision=1)


@router.get("/du-an/{project_id}/bo-kiem-thu")
async def list_test_suites(
    project_id: str,
    q: str = Query(default="", max_length=300),
    suite_type: str = Query(default="", max_length=40),
    status: str = Query(default="", max_length=30),
    sort: str = Query(default="-updated_at", max_length=80),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_test_suite_records(
            project_id,
            user,
            q=q,
            suite_type=suite_type,
            status=status,
            sort=sort,
        )
    )


@router.get("/bo-kiem-thu/{suite_id}")
async def get_test_suite(suite_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_test_suite_record(suite_id, user))


@router.patch("/bo-kiem-thu/{suite_id}")
async def update_test_suite(
    suite_id: str, payload: TestSuitePatch, user: CurrentUser = Depends(get_current_user)
):
    updated = await update_test_suite_record(suite_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/bo-kiem-thu/{suite_id}/nhan-ban", status_code=201)
async def clone_test_suite(suite_id: str, user: CurrentUser = Depends(get_current_user)):
    cloned = await clone_test_suite_record(suite_id, user)
    return envelope(cloned, revision=1)


@router.post("/bo-kiem-thu/{suite_id}/luu-tru")
async def archive_test_suite(
    suite_id: str, payload: ProjectArchiveInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await archive_test_suite_record(suite_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/lan-chay-kiem-thu", status_code=201)
@router.post("/du-an/{project_id}/lan-chay-kiem-thu", status_code=201)
async def create_test_run(
    payload: TestRunCreate,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    run = await create_test_run_record(payload, project_id, user)
    return envelope(run, revision=1)


@router.patch("/du-an/{project_id}/lan-chay-kiem-thu/{run_id}")
async def update_test_run(
    project_id: str,
    run_id: str,
    payload: TestRunPatch,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await update_test_run_record(project_id, run_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/du-an/{project_id}/lan-chay-kiem-thu/{run_id}/phan-cong")
async def assign_test_run(
    project_id: str,
    run_id: str,
    payload: TestRunAssignmentInput,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await assign_test_run_record(project_id, run_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.get("/du-an/{project_id}/lan-chay-kiem-thu")
async def list_test_runs(
    project_id: str,
    name: str = Query(default="", max_length=300),
    release: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    build: str = Query(default="", max_length=200),
    build_id: str = Query(default="", max_length=200),
    environment: str = Query(default="", max_length=200),
    environment_id: str = Query(default="", max_length=200),
    status: str = Query(default="", max_length=30),
    created_by: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort: str = Query(default="-updated_at", max_length=80),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_test_run_records(
            project_id,
            user,
            name=name,
            release=release,
            release_id=release_id,
            build=build,
            build_id=build_id,
            environment=environment,
            environment_id=environment_id,
            status=status,
            created_by=created_by,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    )


@router.get("/du-an/{project_id}/ket-qua-kiem-thu")
async def list_test_results(
    project_id: str,
    status: str = Query(default="", max_length=100),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await list_test_result_records(project_id, user, status=status))


@router.get("/lan-chay-kiem-thu/{run_id}")
async def get_test_run(run_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_test_run_record(run_id, user))


@router.get("/lan-chay-kiem-thu/{run_id}/bao-cao")
async def export_test_run_report(run_id: str, user: CurrentUser = Depends(get_current_user)):
    content = await build_test_run_report(run_id, user)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="test-run-{run_id}.csv"'},
    )


@router.post("/lan-chay-kiem-thu/{run_id}/bat-dau")
async def start_test_run(run_id: str, user: CurrentUser = Depends(get_current_user)):
    updated = await start_test_run_record(run_id, user)
    return envelope(updated, revision=updated["revision"])


@router.post(
    "/du-an/{project_id}/lan-chay-kiem-thu/{run_id}/tiep-tuc",
    openapi_extra={"x-function-ids": ["RUN-15"]},
)
async def resume_test_run(
    project_id: str,
    run_id: str,
    payload: TestRunResumeInput,
    user: CurrentUser = Depends(get_current_user),
):
    result, revision = await resume_test_run_record(project_id, run_id, payload, user)
    return envelope(result, revision=revision)


@router.post("/lan-chay-kiem-thu/{run_id}/ket-qua/{test_case_version_id}")
async def record_test_result(
    run_id: str,
    test_case_version_id: str,
    payload: TestResultInput,
    user: CurrentUser = Depends(get_current_user),
):
    result = await record_test_result_entry(run_id, test_case_version_id, payload, user)
    return envelope(result)


@router.patch("/du-an/{project_id}/thuc-thi-kiem-thu/{execution_id}")
async def patch_test_execution(
    project_id: str,
    execution_id: str,
    payload: TestExecutionPatch,
    user: CurrentUser = Depends(get_current_user),
):
    result = await update_test_execution_record(project_id, execution_id, payload, user)
    return envelope(result, revision=result["execution"]["revision"])


@router.post("/ket-qua-kiem-thu/{result_id}/hieu-chinh")
async def correct_test_result(
    result_id: str,
    payload: TestResultCorrectionInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await correct_test_result_record(result_id, payload, user))


@router.post("/lan-chay-kiem-thu/{run_id}/hoan-tat")
async def complete_test_run(run_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await complete_test_run_record(run_id, user))


@router.post("/lan-chay-kiem-thu/{run_id}/huy")
async def abort_test_run(
    run_id: str,
    reason: str = Body(embed=True, min_length=2, max_length=2000),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await abort_test_run_record(run_id, reason, user))


@router.post("/du-an/{project_id}/loi", status_code=201)
async def create_defect(
    project_id: str, payload: DefectCreate, user: CurrentUser = Depends(get_current_user)
):
    defect = await create_defect_record(project_id, payload, user)
    return envelope(defect, revision=1)


@router.get("/du-an/{project_id}/loi")
async def list_defects(
    project_id: str,
    q: str = Query(default="", max_length=300),
    key: str = Query(default="", max_length=80),
    title: str = Query(default="", max_length=300),
    status: str = Query(default="", max_length=40),
    severity: str = Query(default="", max_length=30),
    priority: str = Query(default="", max_length=30),
    assignee: str = Query(default="", max_length=200),
    release: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    environment: str = Query(default="", max_length=500),
    environment_id: str = Query(default="", max_length=200),
    build: str = Query(default="", max_length=200),
    build_id: str = Query(default="", max_length=200),
    requirement_id: str = Query(default="", max_length=200),
    test_case_id: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort: str = Query(default="-updated_at", max_length=80),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_defect_records(
            project_id,
            user,
            q=q,
            key=key,
            title=title,
            status=status,
            severity=severity,
            priority=priority,
            assignee=assignee,
            release=release,
            release_id=release_id,
            environment=environment,
            environment_id=environment_id,
            build=build,
            build_id=build_id,
            requirement_id=requirement_id,
            test_case_id=test_case_id,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    )


@router.get("/du-an/{project_id}/loi/trung-lap")
async def find_duplicate_defects(project_id: str, user: CurrentUser = Depends(get_current_user)):
    await get_project(project_id, user, "defect.duplicate_check")
    return envelope(await find_duplicate_defect_pairs(project_id))


@router.get("/du-an/{project_id}/loi/xuat")
async def export_defects(project_id: str, user: CurrentUser = Depends(get_current_user)):
    content = await build_defect_export(project_id, user)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="defects-{project_id}.csv"'},
    )


@router.get("/du-an/{project_id}/loi/{defect_id}", openapi_extra={"x-function-ids": ["DEF-02"]})
@router.get("/loi/{defect_id}", openapi_extra={"x-function-ids": ["DEF-02"]})
async def defect_detail(
    defect_id: str, project_id: str | None = None, user: CurrentUser = Depends(get_current_user)
):
    defect = await get_defect_record(defect_id, project_id, user)
    return envelope(defect, revision=defect.get("revision", 1))


@router.post("/du-an/{project_id}/ai/loi/{defect_id}/goi-y-truy-vet", status_code=201)
async def suggest_defect_trace(
    project_id: str,
    defect_id: str,
    payload: BugTraceSuggestionInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await suggest_defect_trace_record(project_id, defect_id, payload, user))


@router.get("/loi/{defect_id}/ung-vien-truy-vet", deprecated=True)
async def find_defect_trace_candidates(
    defect_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await list_defect_trace_candidates(defect_id, user))


@router.patch("/du-an/{project_id}/loi/{defect_id}/truy-vet")
async def update_defect_trace(
    project_id: str,
    defect_id: str,
    payload: DefectTraceUpdateInput,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await update_defect_trace_record(project_id, defect_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.patch("/loi/{defect_id}")
@router.patch("/du-an/{project_id}/loi/{defect_id}")
async def update_defect(
    defect_id: str,
    payload: DefectPatch,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await update_defect_record(defect_id, payload, project_id, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/loi/{defect_id}/chuyen-trang-thai")
async def transition_defect(
    defect_id: str, payload: DefectTransition, user: CurrentUser = Depends(get_current_user)
):
    updated = await transition_defect_record(defect_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/du-an/{project_id}/loi/{defect_id}/kiem-thu-lai")
async def retest_defect(
    project_id: str,
    defect_id: str,
    payload: DefectRetestInput,
    user: CurrentUser = Depends(get_current_user),
):
    result = await retest_defect_record(project_id, defect_id, payload, user)
    return envelope(result, revision=result["defect"]["revision"])
