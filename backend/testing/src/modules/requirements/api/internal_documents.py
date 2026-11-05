from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.core.common import envelope, get_project
from src.core.internal import require_internal_token
from src.modules.requirements.services.requirement_documents import (
    can_read_requirement_document,
)
from src.repositories.requirement_document import requirement_document_repository
from src.schemas.contracts.common import CurrentUser, SystemRole

router = APIRouter(
    prefix="/kiem-thu/noi-bo/tai-lieu-yeu-cau",
    tags=["Quyền tài liệu nội bộ"],
    dependencies=[Depends(require_internal_token)],
)


class RequirementSourceAccessCheck(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    document_ids: list[str] = Field(min_length=1, max_length=100)
    requester_id: str = Field(min_length=1, max_length=200)
    is_admin: bool = False


@router.post("/kiem-tra-quyen-ai")
async def check_requirement_source_ai_access(payload: RequirementSourceAccessCheck):
    requester = CurrentUser(
        _id=payload.requester_id,
        system_role=SystemRole.ADMIN if payload.is_admin else SystemRole.USER,
    )
    if not requester.is_system_admin:
        try:
            await get_project(payload.project_id, requester, "requirement_document.read")
        except HTTPException as error:
            if error.status_code in {403, 404, 423}:
                return envelope({"documents": []})
            raise
    documents = await requirement_document_repository.find_ai_search_sources(
        payload.project_id, payload.document_ids
    )
    accessible = [
        {
            "document_id": str(document["_id"]),
            "content_hash": str(document.get("content_hash") or ""),
        }
        for document in documents
        if document.get("ai_enabled") is True
        and document.get("status") == "READY"
        and document.get("index_status") in {"INDEXED", "DEGRADED"}
        and not document.get("access_update_pending")
        and can_read_requirement_document(document, requester)
    ]
    return envelope({"documents": accessible})
