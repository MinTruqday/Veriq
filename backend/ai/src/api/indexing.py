from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from loguru import logger
from uuid6 import uuid7

from src.core.dependency import (
    CurrentUser,
    SystemRole,
    get_current_user,
    get_current_user_optional,
    verify_internal_token,
)
from src.schemas.inference_staffing import StaffingRecommendationRequest
from src.schemas.ingestion import (
    AttachmentConversionRequest,
    ConversionCheckpointCleanupRequest,
    IngestRequest,
)
from src.schemas.response import APIResponse
from src.services.ingestion import convert_attachment as convert_attachment_data
from src.services.ingestion import index_document as index_document_data
from src.services.ingestion import remove_document as remove_document_data
from src.services.conversion import document_parser
from src.services.staffing_recommendation import recommend_staffing
from src.core.infrastructure.mq import mq
from src.runtime.queue_names import DOCUMENT_INGESTION_QUEUE

router = APIRouter(prefix="/tiep-nap")
indexing_router = APIRouter(dependencies=[Depends(verify_internal_token)])


@indexing_router.post("/tiep-nap/tai-lieu-dang-tai")
async def queue_uploaded_document(
    document_id: str,
    user_id: str = "",
    superseded_document_id: str = "",
    event_id: str = "",
):
    document_id = document_id.strip()
    if not document_id:
        raise HTTPException(status_code=422, detail={"code": "DOCUMENT_ID_REQUIRED"})
    resolved_event_id = event_id.strip() or str(uuid7())
    published = await mq.publish(
        DOCUMENT_INGESTION_QUEUE,
        {
            "event_id": resolved_event_id,
            "document_id": document_id,
            "user_id": user_id,
            "superseded_document_id": superseded_document_id,
            "attempt": 0,
        },
    )
    if not published:
        raise HTTPException(
            status_code=503,
            detail={"code": "DOCUMENT_INGESTION_QUEUE_UNAVAILABLE"},
        )
    return {"status": "accepted", "event_id": resolved_event_id}


@router.post("")
async def ingest_endpoint(
    req: IngestRequest, current_user: CurrentUser = Depends(get_current_user)
):
    logger.info(f"Started document ingestion process document_id={req.document_id}")
    try:
        result = await index_document_data(
            req.document_id,
            str(current_user.id),
            current_user.system_role == SystemRole.ADMIN,
        )
        logger.info(f"Document ingestion completed document_id={req.document_id}")
        return result
    except Exception as error:
        if isinstance(error, (HTTPException, PermissionError, ValueError)):
            logger.warning("Document ingestion rejected error_type={}", type(error).__name__)
        else:
            logger.exception("Document ingestion pipeline error")
        raise document_error(error) from error


@router.delete("/tai-lieu/{document_id}")
async def delete_document_endpoint(
    document_id: str, current_user: CurrentUser = Depends(get_current_user)
):
    logger.info(f"Started document deletion from vector store document_id={document_id}")
    try:
        await remove_document_data(
            document_id,
            str(current_user.id),
            current_user.system_role == SystemRole.ADMIN,
        )
        logger.info(f"Document deletion completed document_id={document_id}")
        return {"status": "success", "message_code": "document_vectors_deleted"}
    except Exception as error:
        if isinstance(error, (HTTPException, PermissionError, ValueError)):
            logger.warning("Document deletion rejected error_type={}", type(error).__name__)
        else:
            logger.exception("Document deletion error")
        raise document_error(error) from error


def document_error(error: Exception):
    if isinstance(error, HTTPException):
        return error
    if isinstance(error, PermissionError):
        return HTTPException(status_code=403, detail="Document access denied")
    if isinstance(error, ValueError):
        return HTTPException(status_code=404, detail=str(error))
    return HTTPException(status_code=502, detail={"code": "knowledge_dependency_failed"})


@indexing_router.post(
    "/chuyen-doi",
    response_model=APIResponse[dict],
    description="Chuyển đổi attachment thành nội dung có cấu trúc",
)
async def convert_attachment(req: AttachmentConversionRequest):
    try:
        result = await convert_attachment_data(
            req.data,
            req.filename,
            req.page_range,
            req.document_id,
            req.project_id,
            req.owner_id,
            req.ocr_language,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return APIResponse(data=result, message="Chuyển đổi tài liệu thành công")


@indexing_router.delete(
    "/chuyen-doi/checkpoints",
    response_model=APIResponse[dict],
    description="Dọn checkpoint chuyển đổi sau khi dịch vụ nguồn đã lưu kết quả",
)
async def clear_conversion_checkpoints(req: ConversionCheckpointCleanupRequest):
    from src.repositories.document_ingestion_checkpoint import (
        document_ingestion_checkpoint_repository,
    )

    await document_ingestion_checkpoint_repository.delete_source_version(
        req.document_id, req.project_id, req.owner_id, req.source_hash
    )
    return APIResponse(data={"deleted": True}, message="Đã dọn checkpoint chuyển đổi")


@indexing_router.get(
    "/tai-lieu/{document_id}/anh-nguon",
    description="Đọc ảnh nguồn riêng tư sau khi dịch vụ Testing đã kiểm tra quyền tài liệu",
)
async def read_document_picture_asset(
    document_id: str,
    project_id: str = Query(min_length=1, max_length=200),
    asset_key: str = Query(min_length=1, max_length=1000),
):
    try:
        content, content_type = await document_parser.read_picture_asset(
            project_id,
            document_id,
            asset_key,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail="DOCUMENT_IMAGE_NOT_FOUND") from error
    except Exception as error:
        logger.exception("Source image read failed document_id={}", document_id)
        raise HTTPException(status_code=502, detail="DOCUMENT_IMAGE_UNAVAILABLE") from error
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@indexing_router.post(
    "/kiem-thu/goi-y-phan-cong",
    description="Xếp hạng người thực hiện từ dữ liệu năng lực, khả dụng và tải công việc",
)
async def staffing_recommendation(req: StaffingRecommendationRequest):
    result = await recommend_staffing(req)
    return APIResponse(data=result, message="Đã tạo đề xuất phân công có căn cứ")


@indexing_router.delete(
    "/tai-lieu/{document_id}",
    response_model=APIResponse[dict],
    description="Xóa chỉ mục knowledge của tài liệu",
)
async def delete_document(
    document_id: str,
    requester_id: str = "",
    is_admin: bool = False,
    user: CurrentUser = Depends(get_current_user_optional),
):
    resolved_id = str(user.id) if user else requester_id
    resolved_admin = user.is_admin() if user else is_admin
    if not resolved_id:
        raise HTTPException(status_code=403, detail="Missing document requester")
    try:
        result = await remove_document_data(document_id, resolved_id, resolved_admin)
    except Exception as error:
        raise document_error(error)
    return APIResponse(data=result, message="Xóa chỉ mục tài liệu thành công")
