from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.causal_analysis import (
    CausalAiRequest,
    CausalAnalysisCreate,
    CausalAnalysisPatch,
    CausalApproval,
    CausalDefectLink,
    CausalEffectivenessInput,
    CausalFiveWhyInput,
    CausalReviewInput,
    CausalRootCauseInput,
    PreventionActionAssign,
    PreventionActionCreate,
    PreventionActionPatch,
)
from src.modules.quality.services.causal_analysis import CausalAnalysisService

router = APIRouter(prefix="/kiem-thu", tags=["Phòng ngừa lỗi"])


@router.get("/du-an/{project_id}/phan-tich-nguyen-nhan")
async def list_causal_analyses(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await CausalAnalysisService.list(project_id, user))


@router.get("/du-an/{project_id}/phan-tich-nguyen-nhan/ung-vien")
async def suggest_causal_analysis_candidates(
    project_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await CausalAnalysisService.candidates(project_id, user))


@router.post("/du-an/{project_id}/phan-tich-nguyen-nhan", status_code=201)
async def create_causal_analysis(
    project_id: str, payload: CausalAnalysisCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.create(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/phan-tich-nguyen-nhan/{analysis_id}")
async def get_causal_analysis(analysis_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await CausalAnalysisService.get(analysis_id, user)
    return envelope(value, revision=value["revision"])


@router.patch("/phan-tich-nguyen-nhan/{analysis_id}")
async def patch_causal_analysis(
    analysis_id: str, payload: CausalAnalysisPatch, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.update(analysis_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/lien-ket-loi")
async def link_causal_analysis_defects(
    analysis_id: str, payload: CausalDefectLink, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.link_defects(analysis_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/nam-tai-sao")
async def add_causal_analysis_five_why(
    analysis_id: str, payload: CausalFiveWhyInput, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.add_five_why(analysis_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/nguyen-nhan-goc")
async def record_causal_analysis_root_cause(
    analysis_id: str, payload: CausalRootCauseInput, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.record_root_cause(analysis_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/hanh-dong-khac-phuc", status_code=201)
async def create_corrective_action(
    analysis_id: str, payload: PreventionActionCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.create_action(
        analysis_id, payload, user, "CORRECTIVE"
    )
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/hanh-dong-phong-ngua", status_code=201)
async def create_preventive_action(
    analysis_id: str, payload: PreventionActionCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.create_action(
        analysis_id, payload, user, "PREVENTIVE"
    )
    return envelope(value, revision=value["revision"])


@router.post("/hanh-dong-phong-ngua/{action_id}/phan-cong")
async def assign_prevention_action(
    action_id: str, payload: PreventionActionAssign, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.assign_action(action_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/hanh-dong-phong-ngua/{action_id}")
async def patch_prevention_action(
    action_id: str, payload: PreventionActionPatch, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.update_action(action_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/gui-ra-soat")
async def submit_causal_analysis_review(
    analysis_id: str, payload: CausalReviewInput, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.submit_review(analysis_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/phe-duyet")
async def approve_causal_analysis(
    analysis_id: str, payload: CausalApproval, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.approve(analysis_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/danh-gia-hieu-luc")
async def review_causal_analysis_effectiveness(
    analysis_id: str,
    payload: CausalEffectivenessInput,
    user: CurrentUser = Depends(get_current_user),
):
    value = await CausalAnalysisService.review_effectiveness(
        analysis_id, payload, user
    )
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/dong")
async def close_causal_analysis(
    analysis_id: str, payload: CausalReviewInput, user: CurrentUser = Depends(get_current_user)
):
    value = await CausalAnalysisService.close(analysis_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/phan-tich-nguyen-nhan/{analysis_id}/ai/goi-y")
async def generate_causal_analysis_hypotheses(
    analysis_id: str, payload: CausalAiRequest, user: CurrentUser = Depends(get_current_user)
):
    return envelope(
        await CausalAnalysisService.generate_hypotheses(analysis_id, payload, user)
    )


@router.get("/phan-tich-nguyen-nhan/{analysis_id}/goi-y-tu-dong")
async def get_latest_causal_analysis_hypotheses(
    analysis_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await CausalAnalysisService.latest_hypothesis_result(analysis_id, user))
