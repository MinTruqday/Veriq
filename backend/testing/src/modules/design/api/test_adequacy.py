from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.test_adequacy import AdequacyRevisionInput, CoverageDecisionInput, CoverageExecutionFeedbackInput
from src.modules.design.services.test_adequacy import (
    approve_adequacy_assessment,
    add_execution_feedback,
    adequacy_change_impact,
    decide_coverage_item,
    get_adequacy_assessment,
    refresh_adequacy_assessment,
    request_adequacy_changes,
    submit_adequacy_assessment,
)


router = APIRouter(prefix="/kiem-thu", tags=["Độ đầy đủ kiểm thử"])


@router.get("/phien-ban-yeu-cau/{requirement_version_id}/do-day-du-kiem-thu")
async def get_assessment(requirement_version_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_adequacy_assessment(requirement_version_id, user))


@router.get("/yeu-cau/{requirement_id}/do-day-du-kiem-thu/tac-dong")
async def get_change_impact(requirement_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await adequacy_change_impact(requirement_id, user))


@router.post("/phien-ban-yeu-cau/{requirement_version_id}/do-day-du-kiem-thu/lam-moi")
async def refresh_assessment(
    requirement_version_id: str,
    payload: AdequacyRevisionInput | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    result = await refresh_adequacy_assessment(
        requirement_version_id, user, payload.expected_revision if payload else None
    )
    return envelope(result, revision=result["revision"])


@router.post("/do-day-du-kiem-thu/{assessment_id}/gui-ra-soat")
async def submit_assessment(
    assessment_id: str, payload: AdequacyRevisionInput, user: CurrentUser = Depends(get_current_user)
):
    result = await submit_adequacy_assessment(assessment_id, payload, user)
    return envelope(result, revision=result["revision"])


@router.post("/do-day-du-kiem-thu/{assessment_id}/phe-duyet")
async def approve_assessment(
    assessment_id: str, payload: AdequacyRevisionInput, user: CurrentUser = Depends(get_current_user)
):
    result = await approve_adequacy_assessment(assessment_id, payload, user)
    return envelope(result, revision=result["revision"])


@router.post("/do-day-du-kiem-thu/{assessment_id}/yeu-cau-chinh-sua")
async def request_changes(
    assessment_id: str, payload: AdequacyRevisionInput, user: CurrentUser = Depends(get_current_user)
):
    result = await request_adequacy_changes(assessment_id, payload, user)
    return envelope(result, revision=result["revision"])


@router.patch("/do-day-du-kiem-thu/{assessment_id}/hang-muc/{coverage_item_id}")
async def decide_item(
    assessment_id: str,
    coverage_item_id: str,
    payload: CoverageDecisionInput,
    user: CurrentUser = Depends(get_current_user),
):
    result = await decide_coverage_item(assessment_id, coverage_item_id, payload, user)
    return envelope(result, revision=result["revision"])


@router.post("/do-day-du-kiem-thu/{assessment_id}/hang-muc/{coverage_item_id}/phan-hoi-thuc-thi")
async def execution_feedback(
    assessment_id: str,
    coverage_item_id: str,
    payload: CoverageExecutionFeedbackInput,
    user: CurrentUser = Depends(get_current_user),
):
    result = await add_execution_feedback(assessment_id, coverage_item_id, payload, user)
    return envelope(result, revision=result["revision"])
