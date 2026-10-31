from fastapi import HTTPException

from src.core.auth import CurrentUser
from src.core.common import audit, get_project, get_project_entity, get_project_role, new_id, now
from src.repositories.test_design import test_design_repository
from src.schemas.contracts.requirements import (
    AttachmentCreate,
    AttachmentModeration,
)


class AttachmentService:

    @staticmethod
    async def register(project_id: str, payload: AttachmentCreate, user: CurrentUser):
        await get_project(project_id, user, "attachment.upload")
        if (payload.artifact_type is None) != (payload.artifact_id is None):
            raise HTTPException(
                status_code=422,
                detail={"code": 'ATTACHMENT_REFERENCE_INCOMPLETE'},
            )
        if payload.artifact_type and payload.artifact_id:
            collection = {
                "requirement": "requirements",
                "requirement_document": "requirement_documents",
                "test_case_draft": "test_case_drafts",
                "test_case_version": "test_case_versions",
                "test_result": "test_results",
                "defect": "defects",
                "review_comment": "review_comments",
                "test_status_report": "test_status_reports",
                "test_completion_report": "test_completion_reports",
            }.get(payload.artifact_type)
            if not collection:
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'ATTACHMENT_ARTIFACT_TYPE_INVALID'},
                )
            if collection == "requirement_documents":
                from src.modules.requirements.services.requirement_documents import get_requirement_document_record

                await get_requirement_document_record(payload.artifact_id, user)
            elif not await test_design_repository.artifact_exists(
                collection, project_id, payload.artifact_id
            ):
                raise HTTPException(
                    status_code=404,
                    detail={"code": 'ATTACHMENT_ARTIFACT_NOT_FOUND'},
                )
        existing = await test_design_repository.find_active_attachment(
            project_id,
            user.id,
            payload.url,
            'ACTIVE',
            payload.artifact_type,
            payload.artifact_id,
        )
        if existing:
            return existing
        attachment = {
            "_id": new_id('ATT'),
            "project_id": project_id,
            "owner_id": user.id,
            **payload.model_dump(),
            "status": 'ACTIVE',
            "revision": 1,
            "created_at": now(),
            "updated_at": now(),
        }
        await test_design_repository.insert_attachment(attachment)
        await audit(
            user.id,
            "attachment_registered",
            "Attachment",
            attachment["_id"],
            project_id,
            {"artifact_type": payload.artifact_type, "artifact_id": payload.artifact_id},
        )
        return attachment

    @staticmethod
    async def list(
        project_id: str,
        artifact_type: str | None,
        artifact_id: str | None,
        user: CurrentUser,
    ):
        await get_project(project_id, user, "attachment.read")
        query = {"project_id": project_id, "status": 'ACTIVE'}
        role = await get_project_role(project_id, user.id)
        if role == 'VIEWER' and artifact_type == "defect":
            return []
        if role == 'VIEWER':
            query["artifact_type"] = {"$ne": "defect"}
        if artifact_type:
            query["artifact_type"] = artifact_type
        if artifact_id:
            query["artifact_id"] = artifact_id
        attachments = await test_design_repository.list_attachments(query)
        document_ids = {
            item.get("artifact_id")
            for item in attachments
            if item.get("artifact_type") == "requirement_document" and item.get("artifact_id")
        }
        if not document_ids:
            return attachments
        from src.modules.requirements.services.requirement_documents import require_document_access
        from src.repositories.requirement_document import requirement_document_repository

        documents = await requirement_document_repository.list_by_ids(project_id, list(document_ids))
        by_id = {item["_id"]: item for item in documents}
        visible = []
        for attachment in attachments:
            if attachment.get("artifact_type") != "requirement_document":
                visible.append(attachment)
                continue
            document = by_id.get(attachment.get("artifact_id"))
            if not document:
                continue
            try:
                await require_document_access(document, user, "requirement_document.read")
            except HTTPException as error:
                if error.status_code != 403:
                    raise
                continue
            visible.append(attachment)
        return visible

    @staticmethod
    async def delete(attachment_id: str, user: CurrentUser):
        attachment = await get_project_entity(
            'attachments', attachment_id, user, "attachment.read"
        )
        permission = (
            "attachment.delete_own_unreferenced"
            if attachment.get("owner_id") == user.id
            else "attachment.moderate"
        )
        await get_project(attachment["project_id"], user, permission)
        if attachment.get("artifact_id"):
            raise HTTPException(
                status_code=409,
                detail={"code": 'ATTACHMENT_REFERENCED_IMMUTABLE'},
            )
        updated = await AttachmentService._mark_deleted(attachment_id, attachment, user.id)
        await audit(
            user.id, "attachment_deleted", "Attachment", attachment_id, attachment["project_id"]
        )
        return {"deleted": True, "attachment_id": attachment_id}, updated["revision"]

    @staticmethod
    async def moderate(
        attachment_id: str,
        payload: AttachmentModeration,
        user: CurrentUser,
    ):
        attachment = await get_project_entity(
            'attachments', attachment_id, user, "attachment.moderate"
        )
        if attachment.get("status") == 'DELETED':
            return {
                "deleted": True,
                "attachment_id": attachment_id,
            }, attachment.get("revision", 1)
        updated = await AttachmentService._mark_deleted(
            attachment_id, attachment, user.id, payload.reason
        )
        await audit(
            user.id,
            "attachment_moderated",
            "Attachment",
            attachment_id,
            attachment["project_id"],
            {"reason": payload.reason},
        )
        return {"deleted": True, "attachment_id": attachment_id}, updated["revision"]

    @staticmethod
    async def _mark_deleted(
        attachment_id: str,
        attachment: dict,
        actor_id: str,
        reason: str | None = None,
    ):
        changes = {
            "status": 'DELETED',
            "deleted_by": actor_id,
            "deleted_at": now(),
            "updated_at": now(),
        }
        if reason is not None:
            changes["moderation_reason"] = reason
        updated = await test_design_repository.mark_attachment_deleted(
            attachment_id,
            attachment["project_id"],
            attachment.get("revision", 1),
            'ACTIVE',
            changes,
        )
        if not updated:
            raise HTTPException(
                status_code=409,
                detail={"code": 'ATTACHMENT_REVISION_CONFLICT'},
            )
        return updated
