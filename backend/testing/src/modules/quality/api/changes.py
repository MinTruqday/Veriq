from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, get_project_entity
from src.schemas.contracts.design import (
    ChangeSetReviewInput,
    ImpactRerunInput,
    ImpactReviewInput,
    ProposalAction,
    ProposalRegenerateInput,
    RegressionApprovalInput,
)
from src.schemas.contracts.requirements import RequirementCompareInput
from src.modules.quality.services.change_set import (
    create_change_set_record,
    get_change_set_record,
    list_change_set_records,
    review_change_set_record,
)
from src.modules.quality.services.impact_analysis import (
    add_impact_review_perspective_record,
    create_impact_analysis_record,
    get_change_set_impact_record,
    get_impact_analysis_record,
    rerun_impact_analysis_record,
    review_impact_analysis_record,
)
from src.modules.quality.services.maintenance_proposal import (
    create_maintenance_proposal_records,
    get_maintenance_proposal_record,
    list_maintenance_proposal_records,
    regenerate_maintenance_proposal_record,
    reject_maintenance_proposal_record,
    review_maintenance_proposal_record,
)
from src.modules.quality.services.proposal_application import approve_maintenance_proposal
from src.modules.quality.services.regression_recommendation import (
    approve_regression_recommendation_record,
    create_regression_recommendation_record,
    edit_regression_recommendation_record,
    get_change_set_regression_record,
    get_regression_recommendation_record,
)

router = APIRouter(prefix="/kiem-thu", tags=["Bảo trì thay đổi kiểm thử"])


@router.post("/yeu-cau/{requirement_id}/bo-thay-doi", status_code=201)
async def create_change_set(
    requirement_id: str,
    payload: RequirementCompareInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await create_change_set_record(requirement_id, payload, user))


@router.get("/du-an/{project_id}/bo-thay-doi")
async def list_change_sets(
    project_id: str,
    requirement_id: str = Query(default="", max_length=200),
    status: str = Query(default="", max_length=30),
    sort: str = Query(default="-created_at", max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_change_set_records(
            project_id,
            user,
            requirement_id=requirement_id,
            status=status,
            sort=sort,
            limit=limit,
        )
    )


@router.get("/bo-thay-doi/{change_set_id}")
async def get_change_set(change_set_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_change_set_record(change_set_id, user))


@router.post("/bo-thay-doi/{change_set_id}/ra-soat")
async def review_change_set(
    change_set_id: str, payload: ChangeSetReviewInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await review_change_set_record(change_set_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/bo-thay-doi/{change_set_id}/phan-tich-anh-huong", status_code=201)
@router.post("/du-an/{project_id}/bo-thay-doi/{change_set_id}/phan-tich-anh-huong", status_code=201)
async def analyze_impact(
    change_set_id: str, project_id: str | None = None, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await create_impact_analysis_record(change_set_id, project_id, user))


@router.get("/bo-thay-doi/{change_set_id}/phan-tich-anh-huong")
async def get_change_set_impact_analysis(
    change_set_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await get_change_set_impact_record(change_set_id, user))


@router.get("/phan-tich-anh-huong/{analysis_id}")
async def get_impact_analysis(analysis_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_impact_analysis_record(analysis_id, user))


@router.post("/phan-tich-anh-huong/{analysis_id}/chay-lai", status_code=201)
async def rerun_impact_analysis(
    analysis_id: str, payload: ImpactRerunInput, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await rerun_impact_analysis_record(analysis_id, payload, user))


@router.post("/phan-tich-anh-huong/{analysis_id}/ra-soat")
async def review_impact_analysis(
    analysis_id: str, payload: ImpactReviewInput, user: CurrentUser = Depends(get_current_user)
):
    analysis = await review_impact_analysis_record(analysis_id, payload, user)
    return envelope(analysis, revision=analysis["revision"])


@router.post("/phan-tich-anh-huong/{analysis_id}/goc-nhin", status_code=201)
async def add_impact_review_perspective(
    analysis_id: str, payload: dict, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await add_impact_review_perspective_record(analysis_id, payload, user))


@router.post("/phan-tich-anh-huong/{analysis_id}/de-xuat-bao-tri", status_code=201)
async def create_maintenance_proposals(
    analysis_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await create_maintenance_proposal_records(analysis_id, user))


@router.get("/du-an/{project_id}/de-xuat-bao-tri")
async def list_proposals(
    project_id: str,
    status: str = Query(default="", max_length=30),
    proposal_type: str = Query(default="", max_length=50),
    target_artifact_id: str = Query(default="", max_length=200),
    impact_analysis_id: str = Query(default="", max_length=200),
    sort: str = Query(default="-created_at", max_length=80),
    limit: int = Query(default=100, ge=1, le=10000),
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=500, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    if page and not impact_analysis_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "PAGINATION_REQUIRES_IMPACT_ANALYSIS_SCOPE"},
        )
    return envelope(
        await list_maintenance_proposal_records(
            project_id,
            user,
            status=status,
            proposal_type=proposal_type,
            target_artifact_id=target_artifact_id,
            impact_analysis_id=impact_analysis_id,
            sort=sort,
            limit=limit,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/de-xuat-bao-tri/{proposal_id}")
async def get_maintenance_proposal(proposal_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_maintenance_proposal_record(proposal_id, user))


@router.post("/du-an/{project_id}/de-xuat-ai/{proposal_id}/ra-soat")
async def review_project_proposal(
    project_id: str,
    proposal_id: str,
    payload: ProposalAction,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await review_maintenance_proposal_record(project_id, proposal_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/de-xuat-bao-tri/{proposal_id}/chap-nhan", status_code=201)
async def accept_proposal(
    proposal_id: str, payload: ProposalAction, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await approve_maintenance_proposal(proposal_id, payload, user))


@router.post("/du-an/{project_id}/de-xuat-ai/{proposal_id}/phe-duyet", status_code=201)
async def approve_project_proposal(
    project_id: str,
    proposal_id: str,
    payload: ProposalAction,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await approve_maintenance_proposal(
            proposal_id,
            payload,
            user,
            edited=payload.patch is not None,
            expected_project_id=project_id,
        )
    )


@router.post("/de-xuat-bao-tri/{proposal_id}/chap-nhan-co-chinh-sua", status_code=201)
async def accept_proposal_with_edit(
    proposal_id: str, payload: ProposalAction, user: CurrentUser = Depends(get_current_user)
):
    return envelope(
        await approve_maintenance_proposal(proposal_id, payload, user, edited=True)
    )


@router.post("/de-xuat-bao-tri/{proposal_id}/tu-choi")
async def reject_proposal(
    proposal_id: str, payload: ProposalAction, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await reject_maintenance_proposal_record(proposal_id, payload, user))


@router.post("/du-an/{project_id}/de-xuat-ai/{proposal_id}/tu-choi")
async def reject_project_proposal(
    project_id: str,
    proposal_id: str,
    payload: ProposalAction,
    user: CurrentUser = Depends(get_current_user),
):
    proposal = await get_maintenance_proposal_record(proposal_id, user, "proposal.reject")
    if proposal["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    return await reject_proposal(proposal_id, payload, user)


@router.post("/de-xuat-bao-tri/{proposal_id}/sinh-lai", status_code=201)
async def regenerate_proposal(
    proposal_id: str,
    payload: ProposalRegenerateInput,
    user: CurrentUser = Depends(get_current_user),
):
    replacement = await regenerate_maintenance_proposal_record(proposal_id, payload, user)
    return envelope(replacement, revision=1)


@router.post("/bo-thay-doi/{change_set_id}/de-xuat-hoi-quy", status_code=201)
async def regression_recommendation(
    change_set_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await create_regression_recommendation_record(change_set_id, user))


@router.get("/bo-thay-doi/{change_set_id}/de-xuat-hoi-quy")
async def get_change_set_regression_recommendation(
    change_set_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await get_change_set_regression_record(change_set_id, user))


@router.post("/du-an/{project_id}/hoi-quy/sinh", status_code=201)
async def generate_project_regression(
    project_id: str, payload: dict, user: CurrentUser = Depends(get_current_user)
):
    change_set_id = str(payload.get("change_set_id") or "")
    change_set = await get_project_entity(
        "requirement_change_sets", change_set_id, user, "regression.generate"
    )
    if change_set["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    return envelope(await create_regression_recommendation_record(change_set_id, user))


@router.get("/de-xuat-hoi-quy/{recommendation_id}")
async def get_regression_recommendation(
    recommendation_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await get_regression_recommendation_record(recommendation_id, user))


@router.patch("/de-xuat-hoi-quy/{recommendation_id}")
async def edit_regression_recommendation(
    recommendation_id: str,
    payload: RegressionApprovalInput,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await edit_regression_recommendation_record(recommendation_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/de-xuat-hoi-quy/{recommendation_id}/phe-duyet", status_code=201)
async def approve_regression_recommendation(
    recommendation_id: str,
    payload: RegressionApprovalInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await approve_regression_recommendation_record(recommendation_id, payload, user)
    )


@router.post("/du-an/{project_id}/hoi-quy/{recommendation_id}/phe-duyet", status_code=201)
async def approve_project_regression(
    project_id: str,
    recommendation_id: str,
    payload: RegressionApprovalInput,
    user: CurrentUser = Depends(get_current_user),
):
    recommendation = await get_project_entity(
        "regression_recommendations", recommendation_id, user, "regression.approve"
    )
    if recommendation["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": "PROJECT_MISMATCH"})
    return envelope(
        await approve_regression_recommendation_record(recommendation_id, payload, user)
    )
