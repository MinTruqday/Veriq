from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.core.auth import CurrentUser, get_current_user
from src.core.configuration import settings
from src.core.common import envelope, get_project_entity
from src.schemas.contracts.requirements import (
    ImportConfirm,
    ImportCreate,
    RequirementCandidateMergeInput,
    RequirementCandidateRejectInput,
    RequirementCandidateSplitInput,
    RequirementImportReview,
    RequirementImportResolution,
)
from src.modules.requirements.services.requirement_import import (
    extract_file_content,
    supported_requirement_formats,
)
from src.modules.requirements.services.requirement_import_workflow import (
    authorize_requirement_import_job,
    apply_requirement_import_job,
    compare_requirement_import_job,
    confirm_requirement_import_job,
    create_requirement_import_job,
    merge_requirement_import_candidates,
    reject_requirement_import_candidate,
    review_requirement_import_job,
    resolve_requirement_import_candidate,
    split_requirement_import_candidate,
)

router = APIRouter(prefix="/kiem-thu", tags=["Yêu cầu kiểm thử"])

@router.post("/du-an/{project_id}/nhap-yeu-cau", status_code=201)
async def create_requirement_import(
    project_id: str, payload: ImportCreate, user: CurrentUser = Depends(get_current_user)
):
    job = await create_requirement_import_job(project_id, payload, user)
    return envelope(job, revision=1)


@router.post("/du-an/{project_id}/nhap-yeu-cau/tai-len", status_code=201)
async def upload_requirement_import(
    project_id: str,
    format: str = Form(),
    file: UploadFile = File(),
    user: CurrentUser = Depends(get_current_user),
):
    if format not in supported_requirement_formats():
        raise HTTPException(status_code=422, detail={"code": "UNSUPPORTED_IMPORT_FORMAT"})
    data = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail={"code": "EMPTY_IMPORT"})
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail={"code": "IMPORT_TOO_LARGE"})
    content = extract_file_content(data, format)
    return await create_requirement_import(
        project_id,
        ImportCreate(
            filename=file.filename or f"requirements.{format}", format=format, content=content
        ),
        user,
    )


@router.get("/nhap-yeu-cau/{job_id}")
async def get_requirement_import(job_id: str, user: CurrentUser = Depends(get_current_user)):
    job = await get_project_entity(
        "import_jobs", job_id, user, "requirement_document.review_extraction"
    )
    await authorize_requirement_import_job(job, user)
    return envelope(job, revision=job.get("revision", 1))


@router.get("/nhap-yeu-cau/{job_id}/doi-chieu")
async def compare_requirement_import(job_id: str, user: CurrentUser = Depends(get_current_user)):
    job = await get_project_entity(
        "import_jobs", job_id, user, "requirement_document.review_extraction"
    )
    return envelope(await compare_requirement_import_job(job, user), revision=job["revision"])


@router.patch("/nhap-yeu-cau/{job_id}")
async def review_requirement_import(
    job_id: str, payload: RequirementImportReview, user: CurrentUser = Depends(get_current_user)
):
    updated = await review_requirement_import_job(job_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/nhap-yeu-cau/{job_id}/ung-vien/gop")
async def merge_requirement_candidates(
    job_id: str,
    payload: RequirementCandidateMergeInput,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await merge_requirement_import_candidates(job_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/nhap-yeu-cau/{job_id}/ung-vien/{candidate_id}/tach")
async def split_requirement_candidate(
    job_id: str,
    candidate_id: str,
    payload: RequirementCandidateSplitInput,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await split_requirement_import_candidate(job_id, candidate_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/nhap-yeu-cau/{job_id}/ung-vien/{candidate_id}/tu-choi")
async def reject_requirement_candidate(
    job_id: str,
    candidate_id: str,
    payload: RequirementCandidateRejectInput,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await reject_requirement_import_candidate(job_id, candidate_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/nhap-yeu-cau/{job_id}/ung-vien/{candidate_id}/doi-chieu")
async def resolve_requirement_candidate(
    job_id: str,
    candidate_id: str,
    payload: RequirementImportResolution,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await resolve_requirement_import_candidate(job_id, candidate_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/nhap-yeu-cau/{job_id}/xac-nhan")
async def confirm_requirement_import(
    job_id: str, payload: ImportConfirm, user: CurrentUser = Depends(get_current_user)
):
    result = await confirm_requirement_import_job(job_id, payload, user)
    if result["job"] is not None:
        return envelope(result["job"])
    return envelope({"job_id": job_id, "requirements": result["requirements"]})


@router.post("/nhap-yeu-cau/{job_id}/tu-dong-ap-dung")
async def apply_requirement_import(
    job_id: str, payload: ImportConfirm, user: CurrentUser = Depends(get_current_user)
):
    result = await apply_requirement_import_job(job_id, payload, user)
    if result["job"] is not None:
        return envelope(result["job"])
    return envelope({"job_id": job_id, "requirements": result["requirements"]})
