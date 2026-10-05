from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import (
    envelope,
    get_project_entity,
)
from src.schemas.contracts.design import (
    ScenarioCreate,
    ScenarioPatch,
    TestCaseCloneInput,
)
from src.schemas.contracts.project import ProjectArchiveInput
from src.schemas.contracts.requirements import ReviewTransitionInput
from src.schemas.contracts.utility import (
    GenerateInput,
    TestCaseGenerateInput,
    TechniqueRecommendationInput,
)
from src.schemas.contracts.design import TestCaseDraftCreate as CaseDraftCreate
from src.schemas.contracts.design import TestCaseDraftPatch as CaseDraftPatch
from src.schemas.contracts.design import TestCaseFreezeInput as CaseFreezeInput
from src.modules.design.services.test_case_records import (
    create_test_case_draft_record,
    update_test_case_draft_record,
)
from src.modules.design.services.test_case_query import (
    clone_test_case_record,
    create_test_case_version_draft_record,
    diff_test_case_version_records,
    get_test_case_record,
    list_test_case_drafts as list_test_case_draft_records,
    list_test_case_records,
    list_test_case_versions as list_test_case_version_records,
    restore_test_case_record,
    set_test_case_obsolete,
)
from src.modules.design.services.test_case_lifecycle import (
    approve_test_case_draft_record,
    lint_test_case_draft_record,
    request_test_case_changes_record,
    submit_test_case_review_record,
)
from src.modules.design.services.test_case_assistance import (
    find_duplicate_test_case_records,
    generate_test_case_draft_records,
    recommend_test_design_techniques,
)
from src.modules.design.services.test_scenario import (
    archive_test_scenario_record,
    clone_test_scenario_record,
    create_test_scenario_record,
    generate_test_scenario_records,
    get_test_scenario_record,
    list_test_scenario_records,
    update_test_scenario_record,
)

router = APIRouter(prefix="/kiem-thu", tags=["Thiết kế kiểm thử"])


@router.post("/du-an/{project_id}/kich-ban-kiem-thu", status_code=201)
async def create_scenario(
    project_id: str, payload: ScenarioCreate, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await create_test_scenario_record(project_id, payload, user), revision=1)


@router.get("/du-an/{project_id}/kich-ban-kiem-thu")
async def list_scenarios(
    project_id: str,
    q: str = Query(default="", max_length=300),
    status: str = Query(default="", max_length=30),
    category: str = Query(default="", max_length=50),
    risk: str = Query(default="", max_length=30),
    sort: str = Query(default="-updated_at", max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_test_scenario_records(
            project_id,
            user,
            q=q,
            status=status,
            category=category,
            risk=risk,
            sort=sort,
            limit=limit,
        )
    )


@router.get("/kich-ban-kiem-thu/{scenario_id}")
async def get_test_scenario(scenario_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_test_scenario_record(scenario_id, user))


@router.patch("/kich-ban-kiem-thu/{scenario_id}")
async def update_scenario(
    scenario_id: str, payload: ScenarioPatch, user: CurrentUser = Depends(get_current_user)
):
    updated = await update_test_scenario_record(scenario_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/kich-ban-kiem-thu/{scenario_id}/nhan-ban", status_code=201)
async def clone_scenario(scenario_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await clone_test_scenario_record(scenario_id, user), revision=1)


@router.post("/kich-ban-kiem-thu/{scenario_id}/luu-tru")
async def archive_scenario(
    scenario_id: str, payload: ProjectArchiveInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await archive_test_scenario_record(scenario_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/phien-ban-yeu-cau/{version_id}/ai/sinh-kich-ban", status_code=201)
async def generate_scenarios(
    version_id: str, payload: GenerateInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await generate_test_scenario_records(version_id, payload, user))


@router.post("/du-an/{project_id}/ca-kiem-thu", status_code=201)
@router.post("/du-an/{project_id}/ban-nhap-ca-kiem-thu", status_code=201)
async def create_test_case_draft(
    project_id: str, payload: CaseDraftCreate, user: CurrentUser = Depends(get_current_user)
):
    draft = await create_test_case_draft_record(project_id, payload, user)
    return envelope(draft, revision=1)


@router.get("/du-an/{project_id}/ban-nhap-ca-kiem-thu")
async def list_test_case_drafts(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await list_test_case_draft_records(project_id, limit, user))


@router.get("/ban-nhap-ca-kiem-thu/{draft_id}")
async def get_test_case_draft(draft_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_project_entity("test_case_drafts", draft_id, user, "testcase.read"))


@router.get("/ca-kiem-thu/{test_case_id}")
async def get_test_case(test_case_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_test_case_record(test_case_id, user))


@router.patch("/du-an/{project_id}/ca-kiem-thu/{draft_id}")
@router.patch("/ca-kiem-thu/{draft_id}/ban-nhap")
@router.patch("/ban-nhap-ca-kiem-thu/{draft_id}")
async def update_test_case_draft(
    draft_id: str,
    payload: CaseDraftPatch,
    project_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await update_test_case_draft_record(draft_id, payload, user, project_id)
    return envelope(updated, revision=updated["revision"])


@router.post("/du-an/{project_id}/ca-kiem-thu/{draft_id}/kiem-tra")
@router.post("/ca-kiem-thu/{draft_id}/kiem-tra")
@router.post("/ban-nhap-ca-kiem-thu/{draft_id}/kiem-tra")
async def lint_test_case_draft(
    draft_id: str, project_id: str | None = None, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await lint_test_case_draft_record(draft_id, user, project_id))


@router.post("/du-an/{project_id}/ca-kiem-thu/{draft_id}/gui-ra-soat")
async def submit_test_case_review(
    project_id: str,
    draft_id: str,
    payload: ReviewTransitionInput,
    user: CurrentUser = Depends(get_current_user),
):
    draft = await submit_test_case_review_record(project_id, draft_id, payload, user)
    return envelope(draft, revision=draft["revision"])


@router.post("/ca-kiem-thu/{draft_id}/ra-soat")
async def submit_test_case_review_alias(
    draft_id: str, payload: ReviewTransitionInput, user: CurrentUser = Depends(get_current_user)
):
    draft = await get_project_entity("test_case_drafts", draft_id, user, "testcase.submit_review")
    return await submit_test_case_review(draft["project_id"], draft_id, payload, user)


@router.post("/du-an/{project_id}/ca-kiem-thu/{draft_id}/yeu-cau-chinh-sua")
async def request_test_case_changes(
    project_id: str,
    draft_id: str,
    payload: ReviewTransitionInput,
    user: CurrentUser = Depends(get_current_user),
):
    draft = await request_test_case_changes_record(project_id, draft_id, payload, user)
    return envelope(draft, revision=draft["revision"])


@router.post("/ban-nhap-ca-kiem-thu/{draft_id}/dong-bang", status_code=201)
async def freeze_test_case_draft(
    draft_id: str, payload: CaseFreezeInput, user: CurrentUser = Depends(get_current_user)
):
    result = await approve_test_case_draft_record(draft_id, payload, user)
    return envelope(
        result["data"],
        status=result["status"],
        degraded_mode=result["degraded_mode"],
    )


@router.post("/du-an/{project_id}/ca-kiem-thu/{draft_id}/phe-duyet", status_code=201)
async def approve_test_case(
    project_id: str,
    draft_id: str,
    payload: CaseFreezeInput,
    user: CurrentUser = Depends(get_current_user),
):
    draft = await get_project_entity("test_case_drafts", draft_id, user, "testcase.approve")
    if draft["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    return await freeze_test_case_draft(draft_id, payload, user)


@router.post("/ca-kiem-thu/{draft_id}/phe-duyet", status_code=201)
async def approve_test_case_alias(
    draft_id: str, payload: CaseFreezeInput, user: CurrentUser = Depends(get_current_user)
):
    await get_project_entity("test_case_drafts", draft_id, user, "testcase.approve")
    return await freeze_test_case_draft(draft_id, payload, user)


@router.get("/du-an/{project_id}/ca-kiem-thu")
async def list_test_cases(
    project_id: str,
    q: str = Query(default="", max_length=300),
    key: str = Query(default="", max_length=80),
    title: str = Query(default="", max_length=300),
    status: str = Query(default="", max_length=30),
    priority: str = Query(default="", max_length=30),
    test_type: str = Query(default="", max_length=40),
    technique: str = Query(default="", max_length=80),
    stale_status: str = Query(default="", max_length=30),
    automation_status: str = Query(default="", max_length=30),
    requirement_id: str = Query(default="", max_length=200),
    suite_id: str = Query(default="", max_length=200),
    latest_result: str = Query(default="", max_length=30),
    tag: str = Query(default="", max_length=100),
    owner: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort: str = Query(default="-updated_at", max_length=80),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_test_case_records(
            project_id,
            user,
            q=q,
            key=key,
            title=title,
            status=status,
            priority=priority,
            test_type=test_type,
            technique=technique,
            stale_status=stale_status,
            automation_status=automation_status,
            requirement_id=requirement_id,
            suite_id=suite_id,
            latest_result=latest_result,
            tag=tag,
            owner=owner,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    )
@router.post("/ca-kiem-thu/{test_case_id}/nhan-ban", status_code=201)
async def clone_test_case(
    test_case_id: str, payload: TestCaseCloneInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await clone_test_case_record(test_case_id, payload, user), revision=1)


@router.get("/ca-kiem-thu/{test_case_id}/phien-ban")
async def list_test_case_versions(test_case_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await list_test_case_version_records(test_case_id, user))


@router.post("/ca-kiem-thu/{test_case_id}/phien-ban/ban-nhap", status_code=201)
async def create_test_case_version_draft(
    test_case_id: str, payload: dict = Body(), user: CurrentUser = Depends(get_current_user)
):
    value = await create_test_case_version_draft_record(test_case_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/ca-kiem-thu/{test_case_id}/khac-biet")
async def diff_test_case_versions(
    test_case_id: str,
    from_version: str = Query(alias="from", min_length=1, max_length=200),
    to_version: str = Query(alias="to", min_length=1, max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await diff_test_case_version_records(
            test_case_id, from_version, to_version, user
        )
    )


@router.post("/ca-kiem-thu/{test_case_id}/ngung-hieu-luc")
async def mark_test_case_obsolete(
    test_case_id: str, payload: dict = Body(), user: CurrentUser = Depends(get_current_user)
):
    return envelope(await set_test_case_obsolete(test_case_id, payload, user))


@router.post("/ca-kiem-thu/{test_case_id}/khoi-phuc")
async def restore_test_case(
    test_case_id: str, payload: dict = Body(), user: CurrentUser = Depends(get_current_user)
):
    return envelope(await restore_test_case_record(test_case_id, payload, user))


@router.post("/phien-ban-yeu-cau/{version_id}/ai/sinh-ca-kiem-thu", status_code=201)
async def generate_test_cases(
    version_id: str, payload: GenerateInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await generate_test_case_draft_records(version_id, payload, user))


@router.post("/phien-ban-yeu-cau/{version_id}/ai/de-xuat-ky-thuat")
async def recommend_techniques(
    version_id: str,
    payload: TechniqueRecommendationInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await recommend_test_design_techniques(version_id, payload, user))


@router.post("/du-an/{project_id}/ca-kiem-thu/sinh", status_code=201)
async def generate_project_test_cases(
    project_id: str, payload: TestCaseGenerateInput, user: CurrentUser = Depends(get_current_user)
):
    version = await get_project_entity(
        "requirement_versions", payload.requirement_version_id, user, "ai.generate_testcase"
    )
    if version["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    return await generate_test_cases(
        payload.requirement_version_id,
        GenerateInput(
            categories=payload.categories,
            techniques=payload.techniques,
            count_per_category=payload.count_per_category,
            max_cases=payload.max_cases,
            instruction=payload.instruction,
            preview_only=payload.preview_only,
        ),
        user,
    )


@router.get("/du-an/{project_id}/ca-kiem-thu/trung-lap")
async def find_duplicates(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await find_duplicate_test_case_records(project_id, user))
