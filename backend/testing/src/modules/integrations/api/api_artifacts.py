from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from src.core.auth import CurrentUser, get_current_user
from src.schemas.contracts.design import TestImportConfirm
from src.schemas.contracts.requirements import (
    APIArtifactArchive,
    APIArtifactConfirm,
    APIArtifactImpact,
    APIArtifactReview,
    ImportCreate,
)
from src.modules.integrations.services import api_artifact

router = APIRouter(prefix="/kiem-thu", tags=["Kiểm thử API và khôi phục"])


@router.get("/du-an/{project_id}/dac-ta-giao-dien", openapi_extra={"x-function-ids": ["API-01"]})
async def list_api_artifacts(
    project_id: str,
    status: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.list_api_artifacts(project_id, status, user)


@router.get("/dac-ta-giao-dien/{artifact_id}", openapi_extra={"x-function-ids": ["API-01"]})
async def get_api_artifact(
    artifact_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.get_api_artifact(artifact_id, user)


@router.post(
    "/du-an/{project_id}/dac-ta-giao-dien/nhap",
    status_code=201,
    openapi_extra={"x-function-ids": ["API-02", "API-03"]},
)
async def import_api_artifact(
    project_id: str,
    payload: ImportCreate,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.import_api_artifact(project_id, payload, user)


@router.patch(
    "/dac-ta-giao-dien/{artifact_id}/ra-soat",
    openapi_extra={"x-function-ids": ["API-04"]},
)
async def review_api_artifact(
    artifact_id: str,
    payload: APIArtifactReview,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.review_api_artifact(artifact_id, payload, user)


@router.post(
    "/dac-ta-giao-dien/{artifact_id}/xac-nhan",
    openapi_extra={"x-function-ids": ["API-05"]},
)
async def confirm_api_artifact(
    artifact_id: str,
    payload: APIArtifactConfirm,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.confirm_api_artifact(artifact_id, payload, user)


@router.get(
    "/du-an/{project_id}/dac-ta-giao-dien/thao-tac",
    openapi_extra={"x-function-ids": ["API-01"]},
)
async def list_api_operations(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.list_api_operations(project_id, user)


@router.get("/dac-ta-giao-dien/thao-tac/{operation_id}")
async def get_api_operation(
    operation_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.get_api_operation(operation_id, user)


@router.post(
    "/dac-ta-giao-dien/thao-tac/{operation_id}/sinh-ca-kiem-thu",
    status_code=201,
    openapi_extra={"x-function-ids": ["API-06"]},
)
async def generate_api_tests(
    operation_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.generate_api_tests(operation_id, user)


@router.get("/nhap-ca-kiem-thu/{job_id}")
async def get_test_import_preview(
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.get_test_import_preview(job_id, user)


@router.get(
    "/du-an/{project_id}/dac-ta-giao-dien/khac-biet",
    openapi_extra={"x-function-ids": ["API-07"]},
)
async def diff_api_artifacts(
    project_id: str,
    from_artifact_id: str = Query(),
    to_artifact_id: str = Query(),
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.diff_api_artifacts(
        project_id,
        from_artifact_id,
        to_artifact_id,
        user,
    )


@router.post(
    "/du-an/{project_id}/dac-ta-giao-dien/phan-tich-anh-huong",
    status_code=201,
    openapi_extra={"x-function-ids": ["API-08"]},
)
async def analyze_api_artifact_impact(
    project_id: str,
    payload: APIArtifactImpact,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.analyze_api_artifact_impact(project_id, payload, user)


@router.post(
    "/dac-ta-giao-dien/{artifact_id}/luu-tru",
    openapi_extra={"x-function-ids": ["API-09"]},
)
async def archive_api_artifact(
    artifact_id: str,
    payload: APIArtifactArchive,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.archive_api_artifact(artifact_id, payload, user)


@router.post("/du-an/{project_id}/khoi-phuc-truy-vet", status_code=201)
async def recover_trace_links(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.recover_trace_links(project_id, user)


@router.post("/du-an/{project_id}/nhap-ca-kiem-thu", status_code=201)
async def preview_test_import(
    project_id: str,
    payload: ImportCreate,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.preview_test_import(project_id, payload, user)


@router.post("/du-an/{project_id}/nhap-ca-kiem-thu/tai-len", status_code=201)
async def upload_test_import(
    project_id: str,
    format: str = Form(),
    file: UploadFile = File(),
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.upload_test_import(project_id, format, file, user)


@router.post("/nhap-ca-kiem-thu/{job_id}/xac-nhan")
async def confirm_test_import(
    job_id: str,
    payload: TestImportConfirm,
    user: CurrentUser = Depends(get_current_user),
):
    return await api_artifact.confirm_test_import(job_id, payload, user)


@router.get("/du-an/{project_id}/ca-kiem-thu/xuat")
async def export_test_cases(
    project_id: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    user: CurrentUser = Depends(get_current_user),
):
    exported = await api_artifact.export_test_cases(project_id, format, user)
    return StreamingResponse(
        iter([exported["content"]]),
        media_type=exported["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{exported["filename"]}"'},
    )
