"""Require signed, project-scoped publication authority for delegated AI runs."""

from fastapi import HTTPException


def require_automation_publication_authority(user, permission=None):
    if getattr(user, "_ai_automation_run_id", None):
        if permission and permission in set(
            getattr(user, "_ai_automation_publication_permissions", [])
        ):
            return
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AUTOMATION_PUBLICATION_NOT_AUTHORIZED",
                "message": "Lượt AI không được cấp quyền tự động công bố quyết định này.",
                "permission": permission,
            },
        )
