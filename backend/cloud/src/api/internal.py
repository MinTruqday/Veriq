import hashlib
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from src.core.dependency import verify_internal_token
from src.core.storage import delete_file, download_file, upload_file
from src.services.internal_storage import InternalStorageService

router = APIRouter(prefix="/noi-bo")


@router.post(
    "/kiem-thu/nguon-yeu-cau",
    dependencies=[Depends(verify_internal_token)],
    include_in_schema=False,
)
async def store_qa_requirement_source(
    project_id: str = Form(), document_id: str = Form(), file: UploadFile = File()
):
    data = await file.read(25 * 1024 * 1024 + 1)
    if not data:
        raise HTTPException(status_code=422, detail={"code": "EMPTY_SOURCE_FILE"})
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": "SOURCE_FILE_TOO_LARGE"})
    safe_name = (
        re.sub(r"[^A-Za-z0-9._-]+", "-", file.filename or "requirements.bin").strip("-")
        or "requirements.bin"
    )
    object_key = f"system/qa/{project_id}/yeu-cau/{document_id}/{safe_name}"
    await upload_file(data, object_key, file.content_type or "application/octet-stream")
    return {
        "data": {
            "object_key": object_key,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "content_type": file.content_type or "application/octet-stream",
        }
    }


@router.get(
    "/kiem-thu/nguon-yeu-cau",
    dependencies=[Depends(verify_internal_token)],
    include_in_schema=False,
)
async def read_qa_requirement_source(project_id: str, document_id: str, object_key: str):
    prefixes = (
        f"system/qa/{project_id}/yeu-cau/{document_id}/",
        f"system/qa/{project_id}/requirements/{document_id}/",
    )
    if not object_key.startswith(prefixes):
        raise HTTPException(status_code=403, detail={"code": "SOURCE_PATH_FORBIDDEN"})
    data, content_type = await download_file(object_key)
    return Response(content=data, media_type=content_type or "application/octet-stream")


@router.delete(
    "/kiem-thu/nguon-yeu-cau",
    dependencies=[Depends(verify_internal_token)],
    include_in_schema=False,
)
async def delete_qa_requirement_source(project_id: str, document_id: str, object_key: str):
    prefix = f"system/qa/{project_id}/yeu-cau/{document_id}/"
    if not object_key.startswith(prefix):
        raise HTTPException(status_code=403, detail={"code": "SOURCE_PATH_FORBIDDEN"})
    await delete_file(object_key)
    return {"data": {"deleted": True}}


@router.post("/luu-tru", dependencies=[Depends(verify_internal_token)], include_in_schema=False)
async def internal_storage_data(req: dict):
    return {"data": await InternalStorageService.execute(req)}
