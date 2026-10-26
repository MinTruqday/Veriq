from datetime import datetime, timezone

from passlib.context import CryptContext

from src.schemas.document import DocumentStatus

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def serialize_document(document):
    if not document:
        return None
    if "_id" in document:
        document["_id"] = str(document["_id"])
    if "created_at" not in document:
        document["created_at"] = datetime.now(timezone.utc)
    views = document.get("views", 0)
    document["view_count"] = views
    document["views_count"] = views
    document.pop("password", None)
    document.pop("access_password_hash", None)
    document.pop("indexing_attempt_id", None)
    document.pop("indexing_lease_token", None)
    document.pop("indexing_lease_until", None)
    return document


def is_admin(current_user) -> bool:
    from src.core.dependency import SystemRole

    return bool(current_user and current_user.system_role == SystemRole.ADMIN)


async def can_read_full(document: dict, current_user) -> bool:
    if not document:
        return False
    user_id = str(current_user.id) if current_user else None
    if user_id == document.get("creator_id") or is_admin(current_user):
        return True
    if document.get("status") != DocumentStatus.PUBLISHED or document.get("is_deleted") is True:
        return False
    if document.get("visibility", "public") != "public":
        return False
    return True
