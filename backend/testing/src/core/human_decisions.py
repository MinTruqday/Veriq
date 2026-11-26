from fastapi import HTTPException
from src.core.database import database


async def can_auto_approve_project_content(project_id, user):
    if getattr(user, "is_system_admin", False):
        return True
    if not project_id:
        return False
    project = await database.value.projects.find_one(
        {"_id": project_id}, {"project_lead_user_id": 1}
    )
    return bool(project and project.get("project_lead_user_id") == user.id)

def require_ai_publication_authority(user, permission=None):
    if getattr(user, "_ai_capability_run_id", None):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AI_RUN_PUBLICATION_NOT_AUTHORIZED",
                "message": "Quyết định phê duyệt phải được người có quyền thực hiện trực tiếp.",
                "permission": permission,
            },
        )


def content_authorship_changes(record, user, changes):
    content_changes = {
        key: value
        for key, value in changes.items()
        if key not in {
            "expected_revision", "updated_at", "content_author_ids", "content_authorship_status",
            "owner_id", "assignee_id", "reviewer_id", "editor_ids", "recipients",
        }
    }
    if not any(record.get(key) != value for key, value in content_changes.items()):
        return changes
    authors = set(record.get("content_author_ids") or [])
    if record.get("created_by"):
        authors.add(record["created_by"])
    authors.add(user.id)
    verified = bool(record.get("created_by")) and (
        record.get("revision") == 1 or record.get("content_authorship_status") == "VERIFIED"
    )
    return {
        **changes,
        "content_author_ids": sorted(authors),
        "content_authorship_status": "VERIFIED" if verified else record.get("content_authorship_status", "UNVERIFIED"),
    }


async def require_independent_review(record, user, code="SELF_REVIEW_FORBIDDEN"):
    if await can_auto_approve_project_content(record.get("project_id"), user):
        return
    reject_self_approval(record, user, code)


def reject_self_approval(record, user, code="SELF_REVIEW_FORBIDDEN"):
    if record.get("content_authorship_status") == "INCOMPLETE":
        raise HTTPException(409, detail={"code": "REVIEW_AUTHORSHIP_UNVERIFIED", "message": "Lịch sử người sửa bản cũ chưa đủ để xác minh duyệt độc lập. Cần tạo bản nháp mới trước khi duyệt."})
    authors = set(record.get("content_author_ids") or [])
    if record.get("created_by"):
        authors.add(record["created_by"])
    if user.id in authors:
        raise HTTPException(
            status_code=403,
            detail={"code": code, "message": "Người tạo hoặc sửa nội dung không thể tự duyệt bản này."},
        )
