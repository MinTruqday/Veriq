import difflib
import hashlib
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from src.clients.document_conversion import read_requirement_source_image
from src.clients.project_knowledge import list_project_artifact_chunks
from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, get_project_entity
from src.core.configuration import settings
from src.modules.requirements.services.document_reader import (
    cancel_document_summary_job,
    get_document_summary_job,
    read_document_page,
    read_document_source_image,
    read_document_source_page,
    retry_document_summary_job,
    search_document,
    start_document_summary_job,
)
from src.modules.requirements.services.requirement_documents import (
    archive_requirement_document_record,
    create_requirement_document_record,
    find_matching_requirement_document_projects,
    find_requirement_document_duplicates,
    get_requirement_document_record,
    get_requirement_source_impact,
    list_ai_requirement_document_page,
    list_requirement_document_records,
    list_requirement_source_structure_page,
    normalized_document_duplicate_text,
    read_raw_requirement_source,
    reindex_requirement_document_record,
    require_document_access,
    restore_requirement_document_record,
    retry_requirement_document_parse_record,
    update_requirement_document_access,
    update_requirement_document_ai_read,
    update_requirement_document_record,
    upload_requirement_document_record,
)
from src.modules.requirements.services.requirement_import import (
    extract_file_content,
    safe_requirement_filename,
    source_document_text,
    supported_requirement_formats,
)
from src.modules.requirements.services.requirement_sources import (
    archive_requirement_source,
    create_requirement_source,
    list_requirement_sources,
    reindex_requirement_source,
)
from src.modules.requirements.services.requirement_workflow import serialized_content
from src.repositories.requirement_source_block import requirement_source_block_repository
from src.schemas.contracts.common import KnowledgeSourceType
from src.schemas.contracts.project import ProjectArchiveInput
from src.schemas.contracts.requirements import (
    ImportCreate,
    KnowledgeSourceCreate,
    RequirementDocumentAccessPatch,
    RequirementDocumentAIReadPatch,
    RequirementDocumentPatch,
    RequirementDocumentSummaryRequest,
    RequirementParseRetry,
)

router = APIRouter(prefix="/kiem-thu", tags=["Yêu cầu kiểm thử"])

@router.post("/du-an/{project_id}/tai-lieu-yeu-cau", status_code=201)
async def create_requirement_document(
    project_id: str, payload: ImportCreate, user: CurrentUser = Depends(get_current_user)
):
    document = await create_requirement_document_record(
        project_id, payload, user, require_duplicate_confirmation=True
    )
    return envelope(document, revision=document["revision"])


@router.post("/du-an/{project_id}/tai-lieu-yeu-cau/doi-chieu")
async def compare_requirement_document_content(
    project_id: str,
    payload: ImportCreate,
    user: CurrentUser = Depends(get_current_user),
):
    normalized_content = (
        payload.content
        if payload.format in {"openapi", "postman"}
        else source_document_text(payload.content)
    )
    content_hash = hashlib.sha256(
        serialized_content(payload.content).encode("utf-8")
    ).hexdigest()
    result = await find_requirement_document_duplicates(
        project_id,
        user,
        filename=payload.filename,
        content_hash=content_hash,
        normalized_content=normalized_content,
    )
    return envelope(result)


@router.post("/du-an/{project_id}/tai-lieu-yeu-cau/doi-chieu-tap")
async def compare_requirement_document_batch(
    project_id: str,
    files: list[UploadFile] = File(),
    formats: str = Form(),
    user: CurrentUser = Depends(get_current_user),
):
    if not files or len(files) > settings.DOCUMENT_DUPLICATE_BATCH_MAX_FILES:
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_BATCH_SIZE_INVALID"})
    try:
        requested_formats = json.loads(formats)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_FORMATS_INVALID"}) from error
    if not isinstance(requested_formats, list) or len(requested_formats) != len(files):
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_FORMATS_INVALID"})
    items = []
    file_results = []
    batch_candidates = []
    total_bytes = 0
    for uploaded, document_format in zip(files, requested_formats):
        if document_format not in supported_requirement_formats():
            raise HTTPException(status_code=422, detail={"code": "UNSUPPORTED_IMPORT_FORMAT"})
        data = await uploaded.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
        total_bytes += len(data)
        if not data or len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail={"code": "IMPORT_TOO_LARGE"})
        if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES * settings.DOCUMENT_DUPLICATE_BATCH_MAX_FILES:
            raise HTTPException(status_code=413, detail={"code": "DOCUMENT_BATCH_TOO_LARGE"})
        content = extract_file_content(data, document_format)
        raw_hash = hashlib.sha256(data).hexdigest()
        result = await find_requirement_document_duplicates(
            project_id,
            user,
            filename=uploaded.filename or "Tài liệu",
            content_hash=raw_hash,
            normalized_content=content,
        )
        normalized = normalized_document_duplicate_text(content)
        batch_matches = []
        for previous in batch_candidates:
            raw_exact = raw_hash == previous["content_hash"]
            normalized_exact = bool(normalized and normalized == previous["normalized_content"])
            if raw_exact or normalized_exact:
                similarity = 1.0
                match_type = "IN_IMPORT"
                difference_summary = "Tệp này khớp hoàn toàn với một tệp đứng trước trong lô."
            elif normalized and previous["normalized_content"]:
                similarity = difflib.SequenceMatcher(
                    None, normalized, previous["normalized_content"]
                ).ratio()
                if similarity < settings.DOCUMENT_DUPLICATE_SIMILARITY_THRESHOLD:
                    continue
                match_type = "SIMILAR_CONTENT_IN_IMPORT"
                difference_summary = "Tệp này có nội dung tương tự một tệp đứng trước trong lô."
            else:
                continue
            batch_matches.append(
                {
                    "candidate_index": previous["candidate_index"],
                    "project_id": project_id,
                    "project_name": "Lô đang import",
                    "filename": previous["filename"],
                    "status": "CHƯA LƯU",
                    "similarity_percent": round(similarity * 100, 2),
                    "match_type": match_type,
                    "difference_summary": difference_summary,
                    "same_project": False,
                    "reusable": False,
                }
            )
        result["matches"].extend(batch_matches)
        batch_candidates.append(
            {
                "candidate_index": len(file_results),
                "filename": uploaded.filename or "Tài liệu",
                "content_hash": raw_hash,
                "normalized_content": normalized,
            }
        )
        items.append(
            {
                "filename": uploaded.filename or "Tài liệu",
                "normalized_hash": hashlib.sha256(
                    normalized.encode("utf-8")
                ).hexdigest()
                if normalized
                else raw_hash,
            }
        )
        file_results.append({"filename": uploaded.filename or "Tài liệu", **result})
    project_matches = await find_matching_requirement_document_projects(project_id, user, items)
    return envelope({"files": file_results, "matching_projects": project_matches})


@router.post("/du-an/{project_id}/tai-lieu-yeu-cau/tai-len", status_code=201)
async def upload_requirement_document(
    project_id: str,
    format: str = Form(),
    visibility: str = Form(default="private"),
    shared_with: str = Form(default="[]"),
    ai_enabled: bool = Form(default=False),
    ocr_language: str | None = Form(default=None, min_length=2, max_length=32),
    source_type: KnowledgeSourceType = Form(default="REFERENCE"),
    supersedes_document_id: str | None = Form(default=None),
    duplicate_confirmed: bool = Form(default=False),
    duplicate_confirmed_document_ids: str = Form(default="[]"),
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
    try:
        confirmed_document_ids = json.loads(duplicate_confirmed_document_ids)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_DUPLICATE_CONFIRMATION_INVALID"}) from error
    if visibility not in {"private", "project", "shared"} or not isinstance(recipients, list):
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_ACCESS_INVALID"})
    if not isinstance(confirmed_document_ids, list) or len(
        confirmed_document_ids
    ) > (
        settings.DOCUMENT_DUPLICATE_MATCH_LIMIT
        + settings.DOCUMENT_DUPLICATE_BATCH_MAX_FILES
    ) or any(
        not isinstance(document_id, str) or not document_id for document_id in confirmed_document_ids
    ):
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_DUPLICATE_CONFIRMATION_INVALID"})
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
        ocr_language,
        supersedes_document_id,
        duplicate_confirmed,
        confirmed_document_ids,
        True,
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


@router.post("/du-an/{project_id}/tai-lieu-yeu-cau/tom-tat", status_code=202)
async def summarize_project_requirement_documents(
    project_id: str,
    payload: RequirementDocumentSummaryRequest,
    user: CurrentUser = Depends(get_current_user),
):
    result = await start_document_summary_job(project_id, payload, user)
    return envelope(result, status=result["status"])


@router.get("/du-an/{project_id}/tai-lieu-yeu-cau/tom-tat/{job_id}")
async def get_project_document_summary_job(
    project_id: str,
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await get_document_summary_job(project_id, job_id, user))


@router.post("/du-an/{project_id}/tai-lieu-yeu-cau/tom-tat/{job_id}/thu-lai", status_code=202)
async def retry_project_document_summary_job(
    project_id: str,
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await retry_document_summary_job(project_id, job_id, user), status="QUEUED")


@router.delete("/du-an/{project_id}/tai-lieu-yeu-cau/tom-tat/{job_id}")
async def cancel_project_document_summary_job(
    project_id: str,
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await cancel_document_summary_job(project_id, job_id, user))


@router.get("/du-an/{project_id}/tai-lieu-yeu-cau/nguon-ai")
async def list_ai_readable_requirement_documents(
    project_id: str,
    cursor: str = Query(default="", max_length=512),
    limit: int = Query(default=200, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await list_ai_requirement_document_page(project_id, cursor, limit, user))


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


@router.get("/du-an/{project_id}/nguon-tri-thuc/{document_id}/cac-doan")
async def list_knowledge_source_chunks(
    project_id: str,
    document_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    document = await get_project_entity(
        "requirement_documents", document_id, user, "knowledge.read"
    )
    if document.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_SOURCE_NOT_FOUND"})
    await require_document_access(document, user, "knowledge.read")
    result = await list_project_artifact_chunks(
        project_id, str(document.get("artifact_version_id") or document_id), limit, cursor
    )
    return envelope(result)


@router.get("/du-an/{project_id}/nguon-tri-thuc/{document_id}/cau-truc-nguon")
async def list_knowledge_source_structure(
    project_id: str,
    document_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=250),
    user: CurrentUser = Depends(get_current_user),
):
    document = await get_project_entity(
        "requirement_documents", document_id, user, "knowledge.read"
    )
    if document.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_SOURCE_NOT_FOUND"})
    await require_document_access(document, user, "knowledge.read")
    return envelope(
        await list_requirement_source_structure_page(
            document_id, offset, limit, user, permission="knowledge.read"
        )
    )


@router.get("/du-an/{project_id}/nguon-tri-thuc/{document_id}/anh/{block_index}")
async def read_knowledge_source_image(
    project_id: str,
    document_id: str,
    block_index: int,
    user: CurrentUser = Depends(get_current_user),
):
    document = await get_project_entity(
        "requirement_documents", document_id, user, "knowledge.read"
    )
    if document.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_SOURCE_NOT_FOUND"})
    await require_document_access(document, user, "knowledge.read")
    source_hash = str(
        document.get("source_structure_source_hash") or document.get("content_hash") or ""
    )
    if document.get("source_structure_store") == "blocks":
        rows = await requirement_source_block_repository.page_version(
            project_id,
            document_id,
            source_hash,
            block_index,
            1,
        )
        row = rows[0] if rows and rows[0].get("block_index") == block_index else None
        block = row.get("block", {}) if row else {}
    else:
        source_blocks = document.get("source_structure") or []
        block = (
            source_blocks[block_index]
            if 0 <= block_index < len(source_blocks)
            and isinstance(source_blocks[block_index], dict)
            else {}
        )
    image_metadata = block.get("image_metadata") or {}
    asset_key = str(image_metadata.get("asset_key") or "")
    if image_metadata.get("asset_status") != "STORED" or not asset_key:
        raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_SOURCE_IMAGE_NOT_FOUND"})
    try:
        content, content_type = await read_requirement_source_image(
            project_id,
            document_id,
            asset_key,
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "KNOWLEDGE_SOURCE_IMAGE_UNAVAILABLE"},
        ) from error
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
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


@router.get("/tai-lieu-yeu-cau/{document_id}/noi-dung")
async def read_requirement_document(
    document_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20000, ge=1000, le=40000),
    sheet: str | None = Query(default=None, max_length=200),
    row_limit: int = Query(default=100, ge=1, le=500),
    page_no: int | None = Query(default=None, ge=1),
    user: CurrentUser = Depends(get_current_user),
):
    if page_no is not None:
        return envelope(await read_document_source_page(document_id, page_no, user))
    return envelope(await read_document_page(document_id, offset, limit, user, sheet, row_limit))


@router.get("/tai-lieu-yeu-cau/{document_id}/anh-nguon/{block_index}")
async def read_requirement_document_image(
    document_id: str, block_index: int, user: CurrentUser = Depends(get_current_user)
):
    data, content_type = await read_document_source_image(document_id, block_index, user)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/tai-lieu-yeu-cau/{document_id}/tim-kiem")
async def search_requirement_document(
    document_id: str,
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await search_document(document_id, q, user, limit))


@router.get("/tai-lieu-yeu-cau/{document_id}/tac-dong")
async def get_requirement_document_impact(
    document_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await get_requirement_source_impact(document_id, user))


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


@router.get("/tai-lieu-yeu-cau/{document_id}/xem-ban-goc")
async def preview_requirement_document(
    document_id: str, user: CurrentUser = Depends(get_current_user)
):
    document = await get_requirement_document_record(document_id, user)
    if document.get("format") != "pdf":
        raise HTTPException(status_code=415, detail={"code": "INLINE_PREVIEW_UNAVAILABLE"})
    data = await read_raw_requirement_source(document)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="document.pdf"',
            "Cache-Control": "private, no-store",
        },
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
