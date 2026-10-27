import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.project import (
    ProjectArchiveInput,
    ProjectCapabilities,
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberPatch,
    ProjectPatch,
    ProjectProgressPatch,
    ProjectTaskCreate,
    ProjectTaskDelete,
    ProjectTaskPatch,
)
from src.schemas.contracts.skill_profile import (
    AssignmentRecommendationInput,
    SkillProfilePatch,
    TestCaseOwnerRecommendationInput,
)
from src.modules.projects.services.project import ProjectService
from src.modules.projects.services.project_progress import ProjectProgressService
from src.modules.projects.services.skill_profiles import (
    extract_own_skill_profile_from_cv,
    get_own_skill_profile,
    recommend_test_case_owner,
    recommend_test_run_assignments,
    update_own_skill_profile,
)

router = APIRouter(prefix="/kiem-thu", tags=["Dự án kiểm thử"])


def _accept_language(request):
    for item in request.headers.get("accept-language", "").split(","):
        locale = item.split(";", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", locale):
            return locale
    return None


@router.get("/du-an/{project_id}/ho-so-nang-luc/cua-toi")
async def read_own_skill_profile(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_own_skill_profile(project_id, user))


@router.put("/du-an/{project_id}/ho-so-nang-luc/cua-toi")
async def save_own_skill_profile(
    project_id: str,
    payload: SkillProfilePatch,
    user: CurrentUser = Depends(get_current_user),
):
    value = await update_own_skill_profile(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/ho-so-nang-luc/cua-toi/trich-xuat-cv")
async def extract_own_skill_profile_cv(
    project_id: str,
    file: UploadFile = File(),
    user: CurrentUser = Depends(get_current_user),
):
    result = await extract_own_skill_profile_from_cv(project_id, file, user)
    return envelope(result)


@router.post("/du-an/{project_id}/lan-chay-kiem-thu/{run_id}/goi-y-phan-cong")
async def suggest_test_run_assignments(
    project_id: str,
    run_id: str,
    payload: AssignmentRecommendationInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await recommend_test_run_assignments(project_id, run_id, payload, user))


@router.post("/du-an/{project_id}/ca-kiem-thu/goi-y-nguoi-phu-trach")
async def suggest_test_case_owner(
    project_id: str,
    payload: TestCaseOwnerRecommendationInput,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await recommend_test_case_owner(
            project_id, payload, user, output_language=_accept_language(request)
        )
    )


@router.get("/du-an/kha-nang", response_model=dict)
async def project_capabilities(user: CurrentUser = Depends(get_current_user)):
    value = ProjectCapabilities(
        can_create_project=await ProjectService.can_create_project(user)
    )
    return envelope(value.model_dump())


@router.post("/du-an", status_code=201)
async def create_project(
    payload: ProjectCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    if payload.locale is None:
        payload = payload.model_copy(update={"locale": _accept_language(request)})
    value = await ProjectService.create(payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an")
async def list_projects(
    q: str = Query(default="", max_length=200),
    status: str = Query(default="active", max_length=30),
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await ProjectService.list(q, status, limit, user))


@router.get("/loi-moi-du-an", openapi_extra={"x-function-ids": ["MEM-01"]})
async def list_project_invitations(user: CurrentUser = Depends(get_current_user)):
    return envelope(await ProjectService.list_invitations(user))


@router.get("/du-an/{project_id}")
async def project_detail(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await ProjectService.get(project_id, user))


@router.patch("/du-an/{project_id}")
async def update_project(
    project_id: str, payload: ProjectPatch, user: CurrentUser = Depends(get_current_user)
):
    value = await ProjectService.update(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/du-an/{project_id}/tien-do")
async def update_project_progress(
    project_id: str,
    payload: ProjectProgressPatch,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectProgressService.update_project_progress(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/cong-viec-cu", include_in_schema=False)
async def list_project_tasks(
    project_id: str,
    status: str | None = Query(default=None, max_length=30),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await ProjectProgressService.list_tasks(project_id, user, status=status))


@router.post("/du-an/{project_id}/cong-viec-cu", status_code=201, include_in_schema=False)
async def create_project_task(
    project_id: str,
    payload: ProjectTaskCreate,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectProgressService.create_task(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/du-an/{project_id}/cong-viec-cu/{task_id}", include_in_schema=False)
async def update_project_task(
    project_id: str,
    task_id: str,
    payload: ProjectTaskPatch,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectProgressService.update_task(project_id, task_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.delete("/du-an/{project_id}/cong-viec-cu/{task_id}", include_in_schema=False)
async def delete_project_task(
    project_id: str,
    task_id: str,
    payload: ProjectTaskDelete,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await ProjectProgressService.delete_task(project_id, task_id, payload, user))


@router.get(
    "/du-an/{project_id}/cai-dat",
    openapi_extra={"x-function-ids": [f"PSET-{index:02d}" for index in range(1, 13)]},
)
async def read_project_settings(project_id: str, user: CurrentUser = Depends(get_current_user)):
    value, revision = await ProjectService.get_settings(project_id, user)
    return envelope(value, revision=revision)


@router.patch(
    "/du-an/{project_id}/cai-dat",
    openapi_extra={"x-function-ids": [f"PSET-{index:02d}" for index in range(1, 13)]},
)
async def update_project_settings(
    project_id: str, payload: ProjectPatch, user: CurrentUser = Depends(get_current_user)
):
    value, revision = await ProjectService.update_settings(project_id, payload, user)
    return envelope(value, revision=revision)


@router.post("/du-an/{project_id}/luu-tru")
async def archive_project(
    project_id: str,
    payload: ProjectArchiveInput,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectService.archive(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/khoi-phuc")
async def restore_project(
    project_id: str,
    payload: ProjectArchiveInput,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectService.restore(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/thanh-vien")
async def list_project_members(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await ProjectService.list_members(project_id, user))


@router.post("/du-an/{project_id}/thanh-vien", status_code=201)
async def add_project_member(
    project_id: str,
    payload: ProjectMemberCreate,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectService.add_member(project_id, payload, user)
    return envelope(value, revision=value["membership_revision"])


@router.post("/du-an/{project_id}/loi-moi", status_code=201)
async def invite_project_member(
    project_id: str,
    payload: ProjectMemberCreate,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectService.add_member(project_id, payload, user, invited=True)
    return envelope(value, revision=value["membership_revision"])


@router.post(
    "/loi-moi-du-an/{invitation_id}/chap-nhan",
    openapi_extra={"x-function-ids": ["MEM-SELF-01"]},
)
async def accept_project_invitation_by_id(
    invitation_id: str, user: CurrentUser = Depends(get_current_user)
):
    value = await ProjectService.accept_invitation(invitation_id, user)
    return envelope(value, revision=value["membership_revision"])


@router.post("/du-an/{project_id}/thanh-vien/{member_user_id}/chap-nhan")
async def accept_project_invitation(
    project_id: str,
    member_user_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectService.accept_project_invitation(project_id, member_user_id, user)
    return envelope(value, revision=value["membership_revision"])


@router.post(
    "/loi-moi-du-an/{invitation_id}/tu-choi",
    openapi_extra={"x-function-ids": ["MEM-SELF-02"]},
)
async def decline_project_invitation(
    invitation_id: str, user: CurrentUser = Depends(get_current_user)
):
    value = await ProjectService.decline_invitation(invitation_id, user)
    return envelope(value, revision=value["membership_revision"])


@router.post("/du-an/{project_id}/roi-du-an", openapi_extra={"x-function-ids": ["MEM-SELF-03"]})
async def leave_project(project_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await ProjectService.leave(project_id, user)
    return envelope(value, revision=value["membership_revision"])


@router.post("/du-an/{project_id}/thanh-vien/{member_user_id}/gui-lai-loi-moi")
async def resend_project_invitation(
    project_id: str,
    member_user_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectService.resend_invitation(project_id, member_user_id, user)
    return envelope(value, revision=value["membership_revision"])


@router.post("/du-an/{project_id}/thanh-vien/{member_user_id}/huy-loi-moi")
async def cancel_project_invitation(
    project_id: str,
    member_user_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectService.cancel_invitation(project_id, member_user_id, user)
    return envelope(value, revision=value["membership_revision"])


@router.patch("/du-an/{project_id}/thanh-vien/{member_user_id}")
async def update_project_member(
    project_id: str,
    member_user_id: str,
    payload: ProjectMemberPatch,
    user: CurrentUser = Depends(get_current_user),
):
    value = await ProjectService.update_member(project_id, member_user_id, payload, user)
    return envelope(value, revision=value["membership_revision"])


@router.delete("/du-an/{project_id}/thanh-vien/{member_user_id}")
async def remove_project_member(
    project_id: str,
    member_user_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await ProjectService.remove_member(project_id, member_user_id, user))
