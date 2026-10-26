from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, get_project_entity
from src.schemas.contracts.requirements import (
    RequirementBaselineInput,
    RequirementCreate,
    RequirementDependencyInput,
    RequirementDraftPatch,
    RequirementObsoleteInput,
    RequirementRestoreInput,
    RequirementVersionCreate,
    ReviewTransitionInput,
)
from src.schemas.contracts.requirement_clarification import (
    RequirementClarificationAnswer,
    RequirementClarificationCreate,
    RequirementClarificationDecision,
    RequirementClarificationResolution,
)
from src.modules.requirements.services.requirement_clarifications import (
    answer_clarification,
    create_clarification,
    decide_clarification,
    generate_clarifications,
    list_clarifications,
    resolve_clarification,
)
from src.modules.requirements.services.requirement_dependencies import add_dependency, remove_dependency
from src.modules.requirements.services.requirement_lifecycle import (
    baseline_requirement,
    make_requirement_obsolete,
    restore_obsolete_requirement,
    return_requirement_for_changes,
    submit_requirement_for_review,
)
from src.modules.requirements.services.requirement_records import (
    create_requirement_record,
    create_requirement_version_record,
    get_requirement_version_record,
    get_requirement_record,
    list_requirement_records,
    list_requirement_version_records,
    update_requirement_draft_record,
)

router = APIRouter(prefix="/kiem-thu", tags=["Yêu cầu kiểm thử"])


@router.get("/phien-ban-yeu-cau/{requirement_version_id}/phieu-lam-ro")
async def requirement_clarification_list(
    requirement_version_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await list_clarifications(requirement_version_id, user))


@router.post("/phien-ban-yeu-cau/{requirement_version_id}/phieu-lam-ro/tao-tu-ra-soat", status_code=201)
async def create_clarifications_from_review(
    requirement_version_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await generate_clarifications(requirement_version_id, user))


@router.post("/phien-ban-yeu-cau/{requirement_version_id}/phieu-lam-ro", status_code=201)
async def create_requirement_clarification(
    requirement_version_id: str,
    payload: RequirementClarificationCreate,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await create_clarification(requirement_version_id, payload, user), revision=1)


@router.patch("/phieu-lam-ro/{clarification_id}/tra-loi")
async def answer_requirement_clarification(
    clarification_id: str,
    payload: RequirementClarificationAnswer,
    user: CurrentUser = Depends(get_current_user),
):
    value = await answer_clarification(clarification_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phieu-lam-ro/{clarification_id}/xac-nhan-giai-quyet")
async def resolve_requirement_clarification(
    clarification_id: str,
    payload: RequirementClarificationResolution,
    user: CurrentUser = Depends(get_current_user),
):
    value = await resolve_clarification(clarification_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/phieu-lam-ro/{clarification_id}/quyet-dinh")
async def decide_requirement_clarification(
    clarification_id: str,
    payload: RequirementClarificationDecision,
    user: CurrentUser = Depends(get_current_user),
):
    value = await decide_clarification(clarification_id, payload, user)
    return envelope(value, revision=value["revision"])

@router.post("/du-an/{project_id}/yeu-cau", status_code=201)
async def create_requirement(
    project_id: str, payload: RequirementCreate, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await create_requirement_record(project_id, payload, user))


@router.get("/du-an/{project_id}/yeu-cau")
async def list_requirements(
    project_id: str,
    q: str = Query(default="", max_length=300),
    key: str = Query(default="", max_length=80),
    title: str = Query(default="", max_length=300),
    status: str = Query(default="", max_length=30),
    owner: str = Query(default="", max_length=200),
    tag: str = Query(default="", max_length=100),
    coverage: str = Query(default="", max_length=20),
    source_type: str = Query(default="", max_length=80),
    has_pending_impact: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort: str = Query(default="-updated_at", max_length=80),
    include_acceptance_criteria: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_requirement_records(
            project_id,
            user,
            q=q,
            key=key,
            title=title,
            status=status,
            owner=owner,
            tag=tag,
            coverage=coverage,
            source_type=source_type,
            has_pending_impact=has_pending_impact,
            page=page,
            page_size=page_size,
            sort=sort,
            include_acceptance_criteria=include_acceptance_criteria,
        )
    )


@router.get("/yeu-cau/{requirement_id}")
async def requirement_detail(requirement_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_requirement_record(requirement_id, user))


@router.patch("/du-an/{project_id}/yeu-cau/{requirement_id}")
async def update_requirement_draft(
    project_id: str,
    requirement_id: str,
    payload: RequirementDraftPatch,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await update_requirement_draft_record(project_id, requirement_id, payload, user)
    return envelope(
        updated,
        revision=updated["current_version"]["revision"],
    )


@router.post("/yeu-cau/{requirement_id}/phu-thuoc")
async def add_requirement_dependency(
    requirement_id: str,
    payload: RequirementDependencyInput,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await add_dependency(
        requirement_id,
        payload.dependency_requirement_id,
        payload.expected_revision,
        user,
    )
    return envelope(updated, revision=updated["revision"])


@router.delete("/yeu-cau/{requirement_id}/phu-thuoc/{dependency_requirement_id}")
async def remove_requirement_dependency(
    requirement_id: str,
    dependency_requirement_id: str,
    expected_revision: int = Query(ge=1),
    user: CurrentUser = Depends(get_current_user),
):
    updated = await remove_dependency(
        requirement_id, dependency_requirement_id, expected_revision, user
    )
    return envelope(updated, revision=updated["revision"])


@router.post("/yeu-cau/{requirement_id}/phien-ban", status_code=201)
async def create_requirement_version(
    requirement_id: str,
    payload: RequirementVersionCreate,
    user: CurrentUser = Depends(get_current_user),
):
    version = await create_requirement_version_record(requirement_id, payload, user)
    return envelope(version, revision=1)


@router.get("/yeu-cau/{requirement_id}/phien-ban")
async def list_requirement_versions(
    requirement_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await list_requirement_version_records(requirement_id, user))


@router.post("/du-an/{project_id}/yeu-cau/{requirement_id}/gui-ra-soat")
async def submit_requirement_review(
    project_id: str,
    requirement_id: str,
    payload: ReviewTransitionInput,
    user: CurrentUser = Depends(get_current_user),
):
    version = await submit_requirement_for_review(
        project_id,
        requirement_id,
        payload.expected_revision,
        payload.review_note,
        user,
    )
    return envelope(version, revision=version["revision"])


@router.post("/yeu-cau/{requirement_id}/ra-soat")
async def submit_requirement_review_alias(
    requirement_id: str,
    payload: ReviewTransitionInput,
    user: CurrentUser = Depends(get_current_user),
):
    requirement = await get_project_entity(
        "requirements", requirement_id, user, "requirement.submit_review"
    )
    return await submit_requirement_review(requirement["project_id"], requirement_id, payload, user)


@router.post("/du-an/{project_id}/yeu-cau/{requirement_id}/yeu-cau-chinh-sua")
async def request_requirement_changes(
    project_id: str,
    requirement_id: str,
    payload: ReviewTransitionInput,
    user: CurrentUser = Depends(get_current_user),
):
    version = await return_requirement_for_changes(
        project_id,
        requirement_id,
        payload.expected_revision,
        payload.review_note,
        user,
    )
    return envelope(version, revision=version["revision"])


@router.post("/phien-ban-yeu-cau/{version_id}/chot-chuan")
async def baseline_requirement_version(
    version_id: str,
    payload: RequirementBaselineInput,
    user: CurrentUser = Depends(get_current_user),
):
    result = await baseline_requirement(
        version_id,
        payload.expected_revision,
        payload.review_note,
        user,
    )
    return envelope(
        result.version,
        revision=result.version["revision"],
        status=result.status,
        degraded_mode=result.degraded_mode,
    )


@router.get("/phien-ban-yeu-cau/{version_id}")
async def get_requirement_version(version_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_requirement_version_record(version_id, user))


@router.post("/du-an/{project_id}/yeu-cau/{requirement_id}/phe-duyet")
async def approve_requirement(
    project_id: str,
    requirement_id: str,
    payload: RequirementBaselineInput,
    user: CurrentUser = Depends(get_current_user),
):
    requirement = await get_project_entity(
        "requirements", requirement_id, user, "requirement.approve"
    )
    if requirement["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    return await baseline_requirement_version(requirement["current_version_id"], payload, user)


@router.post("/yeu-cau/{requirement_id}/phe-duyet")
async def approve_requirement_alias(
    requirement_id: str,
    payload: RequirementBaselineInput,
    user: CurrentUser = Depends(get_current_user),
):
    requirement = await get_project_entity(
        "requirements", requirement_id, user, "requirement.approve"
    )
    return await baseline_requirement_version(requirement["current_version_id"], payload, user)


@router.post("/yeu-cau/{requirement_id}/ngung-hieu-luc")
async def mark_requirement_obsolete(
    requirement_id: str,
    payload: RequirementObsoleteInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await make_requirement_obsolete(
            requirement_id,
            payload.expected_current_version_id,
            payload.reason,
            user,
        )
    )


@router.post("/yeu-cau/{requirement_id}/khoi-phuc")
async def restore_requirement(
    requirement_id: str,
    payload: RequirementRestoreInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await restore_obsolete_requirement(
            requirement_id,
            payload.expected_current_version_id,
            payload.reason,
            user,
        )
    )
