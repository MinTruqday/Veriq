from fastapi import HTTPException

from src.core.auth import CurrentUser
from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.repositories.review import review_repository
from src.schemas.contracts.requirements import (
    ReviewCommentAction,
    ReviewCommentCreate,
    ReviewCommentPatch,
)


class ReviewCommentService:
    ARTIFACT_ACCESS = {
        "requirement_version": ("requirement_versions", "requirement.read"),
        "test_case_draft": ("test_case_drafts", "testcase.read"),
    }

    @staticmethod
    async def _require_artifact_read(project_id, artifact_type, artifact_id, user):
        access = ReviewCommentService.ARTIFACT_ACCESS.get(artifact_type)
        if not access:
            raise HTTPException(status_code=422, detail={"code": "COMMENT_ARTIFACT_TYPE_INVALID"})
        collection, permission = access
        artifact = await get_project_entity(collection, artifact_id, user, permission)
        if artifact.get("project_id") != project_id:
            raise HTTPException(status_code=404, detail={"code": "COMMENT_ARTIFACT_NOT_FOUND"})

    @staticmethod
    async def create(project_id: str, payload: ReviewCommentCreate, user: CurrentUser):
        await get_project(project_id, user, 'comment.create')
        await ReviewCommentService._require_artifact_read(
            project_id, payload.artifact_type, payload.artifact_id, user
        )
        if payload.parent_comment_id:
            parent = await review_repository.find_comment(
                payload.parent_comment_id, project_id
            )
            if not parent:
                raise HTTPException(
                    status_code=422,
                    detail={"code": 'PARENT_COMMENT_NOT_FOUND'},
                )
        comment = {
            "_id": new_id('RC'),
            "project_id": project_id,
            **payload.model_dump(),
            "author_id": user.id,
            "status": 'OPEN',
            "created_at": now(),
            "updated_at": now(),
        }
        await review_repository.insert_comment(comment)
        await audit(
            user.id,
            'review_comment_created',
            'ReviewComment',
            comment["_id"],
            project_id,
            {"artifact_type": payload.artifact_type, "artifact_id": payload.artifact_id},
        )
        return comment

    @staticmethod
    async def list(
        project_id: str,
        artifact_type: str | None,
        artifact_id: str | None,
        status: str | None,
        user: CurrentUser,
    ):
        await get_project(project_id, user, 'comment.read')
        if artifact_type or artifact_id:
            if not artifact_type or not artifact_id:
                raise HTTPException(status_code=422, detail={"code": "COMMENT_ARTIFACT_SCOPE_REQUIRED"})
            await ReviewCommentService._require_artifact_read(
                project_id, artifact_type, artifact_id, user
            )
        else:
            await get_project(project_id, user, "comment.moderate")
        query = {"project_id": project_id}
        if artifact_type:
            query["artifact_type"] = artifact_type
        if artifact_id:
            query["artifact_id"] = artifact_id
        query["status"] = status or 'OPEN'
        return await review_repository.list_comments(query)

    @staticmethod
    async def update(comment_id: str, payload: ReviewCommentPatch, user: CurrentUser):
        comment = await ReviewCommentService._get_for_change(comment_id, user)
        if comment.get("deleted_at"):
            raise HTTPException(
                status_code=409, detail={"code": 'COMMENT_DELETED'}
            )
        timestamp = now()
        updated = await review_repository.update_comment(
            comment_id,
            comment["project_id"],
            {"body_doc": payload.body_doc, "edited_at": timestamp, "updated_at": timestamp},
        )
        await audit(
            user.id,
            'review_comment_updated',
            'ReviewComment',
            comment_id,
            comment["project_id"],
        )
        return updated

    @staticmethod
    async def delete(comment_id: str, user: CurrentUser):
        comment = await get_project_entity(
            'review_comments',
            comment_id,
            user,
            'comment.read',
        )
        permission = (
            'comment.delete_own'
            if comment.get("author_id") == user.id
            else 'comment.moderate'
        )
        await get_project(comment["project_id"], user, permission)
        timestamp = now()
        await review_repository.mark_comment_deleted(
            comment_id,
            comment["project_id"],
            {
                "body_doc": {"type": "doc", "content": []},
                "status": 'DELETED',
                "deleted_by": user.id,
                "deleted_at": timestamp,
                "updated_at": timestamp,
            },
        )
        await audit(
            user.id,
            'review_comment_deleted',
            'ReviewComment',
            comment_id,
            comment["project_id"],
        )
        return {"deleted": True, "comment_id": comment_id}

    @staticmethod
    async def resolve(comment_id: str, payload: ReviewCommentAction, user: CurrentUser):
        return await ReviewCommentService._transition(
            comment_id,
            payload,
            user,
            'OPEN',
            'RESOLVED',
            "resolved",
            'review_comment_resolved',
        )

    @staticmethod
    async def reopen(comment_id: str, payload: ReviewCommentAction, user: CurrentUser):
        return await ReviewCommentService._transition(
            comment_id,
            payload,
            user,
            'RESOLVED',
            'OPEN',
            "reopened",
            'review_comment_reopened',
        )

    @staticmethod
    async def _get_for_change(comment_id: str, user: CurrentUser):
        comment = await get_project_entity(
            'review_comments',
            comment_id,
            user,
            'comment.read',
        )
        permission = (
            'comment.update_own'
            if comment.get("author_id") == user.id
            else 'comment.moderate'
        )
        await get_project(comment["project_id"], user, permission)
        return comment

    @staticmethod
    async def _transition(
        comment_id: str,
        payload: ReviewCommentAction,
        user: CurrentUser,
        source: str,
        target: str,
        action: str,
        audit_action: str,
    ):
        comment = await ReviewCommentService._get_for_change(comment_id, user)
        if comment["status"] == target:
            return comment
        timestamp = now()
        updated = await review_repository.transition_comment(
            comment_id,
            comment["project_id"],
            source,
            {
                "status": target,
                f"{action}_by": user.id,
                f"{action}_at": timestamp,
                "resolution_reason"
                if target == 'RESOLVED'
                else "reopen_reason": payload.reason,
                "updated_at": timestamp,
            },
        )
        if not updated:
            raise HTTPException(
                status_code=409, detail={"code": 'COMMENT_STATE_CONFLICT'}
            )
        await audit(
            user.id,
            audit_action,
            'ReviewComment',
            comment_id,
            comment["project_id"],
            {"reason": payload.reason},
        )
        return updated
