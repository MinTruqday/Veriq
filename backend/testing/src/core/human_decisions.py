from fastapi import HTTPException


def require_automation_publication_authority(user, permission=None):
    if getattr(user, "_ai_automation_run_id", None):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AUTOMATION_PUBLICATION_NOT_AUTHORIZED",
                "message": "Quyết định phê duyệt phải được người có quyền thực hiện trực tiếp.",
                "permission": permission,
            },
        )
