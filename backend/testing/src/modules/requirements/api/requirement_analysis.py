from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, get_project, get_project_entity
from src.core.internal import require_internal_token
from src.schemas.contracts.requirements import (
    RequirementAIAnalysisInput,
    RequirementCompareInput,
    RequirementDuplicateCheckInput,
    RequirementMergeInput,
    RequirementSplitInput,
)
from src.modules.requirements.services.requirement_ai import (
    analyze_requirement_quality,
    get_latest_requirement_quality_analysis,
)
from src.modules.requirements.services.requirement_analysis import (
    compare_requirement_versions,
    find_requirement_duplicates,
)
from src.modules.requirements.services.requirement_transformations import (
    claim_requirement_transformation,
    execute_requirement_transformation,
    find_requirement_transformation,
    hydrate_requirement_transformation,
    load_requirement_baselines,
)

router = APIRouter(prefix="/kiem-thu", tags=["Yêu cầu kiểm thử"])

@router.get("/phien-ban-yeu-cau/{version_id}/ai/ket-qua-moi-nhat")
async def latest_requirement_quality_analysis(
    version_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await get_latest_requirement_quality_analysis(version_id, user))


@router.post("/phien-ban-yeu-cau/{version_id}/ai/kiem-tra")
async def analyze_requirement_quality_for_automation(
    version_id: str,
    payload: RequirementAIAnalysisInput,
    _: None = Depends(require_internal_token),
    user: CurrentUser = Depends(get_current_user),
):
    if not payload.idempotency_key.startswith("requirement-quality-event:"):
        raise HTTPException(status_code=404, detail={"code": "AUTOMATIC_ANALYSIS_ONLY"})
    return envelope(await analyze_requirement_quality(version_id, payload, user))


@router.post("/yeu-cau/{requirement_id}/so-sanh")
async def compare_requirement(
    requirement_id: str,
    payload: RequirementCompareInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await compare_requirement_versions(
            requirement_id,
            payload.from_version_id,
            payload.to_version_id,
            user,
        )
    )


@router.get("/yeu-cau/{requirement_id}/khac-biet")
async def diff_requirement(
    requirement_id: str,
    from_version: str = Query(alias="from", min_length=1, max_length=200),
    to_version: str = Query(alias="to", min_length=1, max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return await compare_requirement(
        requirement_id,
        RequirementCompareInput(from_version_id=from_version, to_version_id=to_version),
        user,
    )


@router.post("/du-an/{project_id}/yeu-cau/{requirement_id}/tach", status_code=201)
async def split_requirement(
    project_id: str,
    requirement_id: str,
    payload: RequirementSplitInput,
    user: CurrentUser = Depends(get_current_user),
):
    expected_versions = {requirement_id: payload.expected_source_version_id}
    await get_project(project_id, user, "requirement.split")
    existing = await find_requirement_transformation(project_id, payload.idempotency_key)
    sources = None
    if not existing:
        sources = await load_requirement_baselines(
            project_id, [requirement_id], expected_versions, user, "requirement.split"
        )
    transformation, execute = await claim_requirement_transformation(
        project_id, "SPLIT", payload, [requirement_id], [payload.expected_source_version_id], user
    )
    if not execute:
        return envelope(await hydrate_requirement_transformation(transformation))
    if sources is None:
        sources = await load_requirement_baselines(
            project_id, [requirement_id], expected_versions, user, "requirement.split"
        )
    return await execute_requirement_transformation(
        project_id, transformation, sources, payload.drafts, user, "split"
    )


@router.post("/du-an/{project_id}/yeu-cau/gop", status_code=201)
async def merge_requirements(
    project_id: str, payload: RequirementMergeInput, user: CurrentUser = Depends(get_current_user)
):
    await get_project(project_id, user, "requirement.merge")
    existing = await find_requirement_transformation(project_id, payload.idempotency_key)
    sources = None
    if not existing:
        sources = await load_requirement_baselines(
            project_id,
            payload.source_requirement_ids,
            payload.expected_source_version_ids,
            user,
            "requirement.merge",
        )
    transformation, execute = await claim_requirement_transformation(
        project_id,
        "MERGE",
        payload,
        payload.source_requirement_ids,
        [payload.expected_source_version_ids[item] for item in payload.source_requirement_ids],
        user,
    )
    if not execute:
        return envelope(await hydrate_requirement_transformation(transformation))
    if sources is None:
        sources = await load_requirement_baselines(
            project_id,
            payload.source_requirement_ids,
            payload.expected_source_version_ids,
            user,
            "requirement.merge",
        )
    return await execute_requirement_transformation(
        project_id, transformation, sources, [payload.draft], user, "merge"
    )


@router.post("/du-an/{project_id}/yeu-cau/kiem-tra-trung-lap", status_code=201)
async def find_duplicate_requirements(
    project_id: str,
    payload: RequirementDuplicateCheckInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await find_requirement_duplicates(project_id, payload, user))

