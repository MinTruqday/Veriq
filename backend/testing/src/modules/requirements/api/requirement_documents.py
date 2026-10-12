import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from src.core.auth import CurrentUser, get_current_user
from src.core.configuration import settings
from src.core.common import envelope, get_project_entity
from src.schemas.contracts.project import ProjectArchiveInput
from src.schemas.contracts.requirements import (
    ImportCreate,
    KnowledgeSourceCreate,
    RequirementDocumentPatch,
    RequirementDocumentAccessPatch,
    RequirementDocumentAIReadPatch,
    RequirementExtractionInput,
    RequirementParseRetry,
)
from src.schemas.contracts.common import KnowledgeSourceType
from src.modules.requirements.services.requirement_documents import (
    archive_requirement_document_record,
    create_requirement_document_record,
    get_requirement_document_record,
    list_requirement_document_records,
    read_raw_requirement_source,
    require_document_access,
    reindex_requirement_document_record,
    restore_requirement_document_record,
    retry_requirement_document_parse_record,
    update_requirement_document_record,
    update_requirement_document_access,
    update_requirement_document_ai_read,
    upload_requirement_document_record,
)
from src.modules.requirements.services.requirement_import_workflow import extract_requirement_candidates
from src.modules.requirements.services.requirement_import import (
    safe_requirement_filename,
    supported_requirement_formats,
)
from src.modules.requirements.services.requirement_sources import (
    archive_requirement_source,
    create_requirement_source,
    list_requirement_sources,
    reindex_requirement_source,
)

router = APIRouter(prefix="/kiem-thu", tags=["Yêu cầu kiểm thử"])

@router.post("/du-an/{project_id}/tai-lieu-yeu-cau", status_code=201)
async def create_requirement_document(
    project_id: str, payload: ImportCreate, user: CurrentUser = Depends(get_current_user)
):
    document = await create_requirement_document_record(project_id, payload, user)
    return envelope(document, revision=document["revision"])


@router.post("/du-an/{project_id}/tai-lieu-yeu-cau/tai-len", status_code=201)
async def upload_requirement_document(
    project_id: str,
    format: str = Form(),
    visibility: str = Form(default="private"),
    shared_with: str = Form(default="[]"),
    ai_enabled: bool = Form(default=False),
    source_type: KnowledgeSourceType = Form(default="REFERENCE"),
    file: UploadFile = File(),
    user: CurrentUser = Depends(get_current_user),
):
    if format not in supported_requirement_formats():
        raise HTTPException(status_code=422, detail={"code": "UNSUPPORTED_IMPORT_FORMAT"})
    data = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    try:
        recipients = json.loads(shared_with)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_RECIPIENTS_INVALID"}) from error
    if visibility not in {"private", "project", "shared"} or not isinstance(recipients, list):
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_ACCESS_INVALID"})
    if visibility == "shared" and not recipients:
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_RECIPIENTS_REQUIRED"})
    if visibility != "shared" and recipients:
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_RECIPIENTS_UNEXPECTED"})
    result = await upload_requirement_document_record(
        project_id,
        format,
        file.filename,
        file.content_type,
        data,
        user,
        visibility,
        recipients,
        ai_enabled,
        source_type,
    )
    return envelope(
        result.data,
        revision=result.data["revision"],
        status=result.status,
        degraded_mode=result.degraded_mode,
    )


@router.get("/du-an/{project_id}/tai-lieu-yeu-cau")
async def list_requirement_documents(
    project_id: str,
    status: str = Query(default="", max_length=30),
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=200, ge=1, le=1000),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_requirement_document_records(project_id, status, q, limit, user)
    )


@router.post("/du-an/{project_id}/nguon-tri-thuc", status_code=201)
async def create_knowledge_source(
    project_id: str, payload: KnowledgeSourceCreate, user: CurrentUser = Depends(get_current_user)
):
    result = await create_requirement_source(project_id, payload, user)
    return envelope(
        result.data,
        revision=result.data.get("revision", 1),
        status=result.status,
        degraded_mode=result.degraded_mode,
    )


@router.get("/du-an/{project_id}/nguon-tri-thuc")
async def list_knowledge_sources(
    project_id: str,
    include_archived: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_requirement_sources(project_id, include_archived, user)
    )


@router.post("/nguon-tri-thuc/{document_id}/luu-tru")
async def archive_knowledge_source(
    document_id: str, payload: ProjectArchiveInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await archive_requirement_source(document_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/nguon-tri-thuc/{document_id}/lap-chi-muc-lai", status_code=202)
async def reindex_knowledge_source(
    document_id: str, user: CurrentUser = Depends(get_current_user)
):
    result = await reindex_requirement_source(document_id, user)
    return envelope(
        result.data,
        revision=result.data["revision"],
        status=result.status,
        degraded_mode=result.degraded_mode,
    )


@router.get("/tai-lieu-yeu-cau/{document_id}")
async def get_requirement_document(document_id: str, user: CurrentUser = Depends(get_current_user)):
    document = await get_requirement_document_record(document_id, user)
    return envelope(document, revision=document["revision"])


@router.patch("/tai-lieu-yeu-cau/{document_id}")
async def update_requirement_document_metadata(
    document_id: str,
    payload: RequirementDocumentPatch,
    user: CurrentUser = Depends(get_current_user),
):
    result = await update_requirement_document_record(document_id, payload, user)
    return envelope(
        result.data,
        revision=result.data["revision"],
        status=result.status,
        degraded_mode=result.degraded_mode,
    )


@router.patch("/tai-lieu-yeu-cau/{document_id}/quyen-truy-cap")
async def update_requirement_document_access_control(
    document_id: str,
    payload: RequirementDocumentAccessPatch,
    user: CurrentUser = Depends(get_current_user),
):
    result = await update_requirement_document_access(document_id, payload, user)
    return envelope(result.data, revision=result.data["revision"])


@router.patch("/tai-lieu-yeu-cau/{document_id}/ai-doc")
async def update_requirement_document_ai_read_access(
    document_id: str,
    payload: RequirementDocumentAIReadPatch,
    user: CurrentUser = Depends(get_current_user),
):
    result = await update_requirement_document_ai_read(document_id, payload, user)
    return envelope(result.data, revision=result.data["revision"])


@router.post("/tai-lieu-yeu-cau/{document_id}/lap-chi-muc-lai", status_code=202)
async def reindex_requirement_document(
    document_id: str, user: CurrentUser = Depends(get_current_user)
):
    result = await reindex_requirement_document_record(document_id, user)
    return envelope(
        result.data,
        revision=result.data["revision"],
        status=result.status,
        degraded_mode=result.degraded_mode,
    )


@router.get("/tai-lieu-yeu-cau/{document_id}/tai-xuong")
async def download_requirement_document(
    document_id: str, user: CurrentUser = Depends(get_current_user)
):
    document = await get_project_entity(
        "requirement_documents", document_id, user, "requirement_document.download"
    )
    await require_document_access(document, user, "requirement_document.download")
    data = await read_raw_requirement_source(document)
    filename = safe_requirement_filename(document.get("filename") or "source.bin")
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/tai-lieu-yeu-cau/{document_id}/luu-tru")
async def archive_requirement_document(
    document_id: str, payload: ProjectArchiveInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await archive_requirement_document_record(document_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/tai-lieu-yeu-cau/{document_id}/khoi-phuc")
async def restore_requirement_document(
    document_id: str, payload: ProjectArchiveInput, user: CurrentUser = Depends(get_current_user)
):
    updated = await restore_requirement_document_record(document_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post("/tai-lieu-yeu-cau/{document_id}/thu-lai-phan-tich")
async def retry_requirement_document_parse(
    document_id: str, payload: RequirementParseRetry, user: CurrentUser = Depends(get_current_user)
):
    result = await retry_requirement_document_parse_record(document_id, payload, user)
    return envelope(
        result.data,
        revision=result.data["revision"],
        status=result.status,
        degraded_mode=result.degraded_mode,
    )


@router.post("/tai-lieu-yeu-cau/{document_id}/trich-xuat", status_code=201)
async def extract_requirement_document(
    document_id: str,
    payload: RequirementExtractionInput,
    user: CurrentUser = Depends(get_current_user),
):
    job = await extract_requirement_candidates(document_id, payload, user)
    return envelope(job, revision=job.get("revision", 1))
