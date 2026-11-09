from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.authentication import load_accounts
from src.core.auth import CurrentUser, get_current_user
from src.core.common import audit, envelope, new_id, now
from src.core.database import database
from src.schemas.contracts.resource_capacity import CapacityUpdate

router = APIRouter(prefix="/kiem-thu/quan-tri", tags=["Quản trị công suất"])


def _require_admin(user):
    if not user.is_system_admin:
        raise HTTPException(status_code=403, detail={"code": "SYSTEM_ADMIN_REQUIRED"})


@router.get("/cong-suat")
async def list_capacity_periods(user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    periods = (
        await database.value.resource_capacity_periods.find({})
        .sort([("period_start", -1), ("period_end", -1)])
        .to_list(500)
    )
    user_ids = list(
        dict.fromkeys(
            entry.get("user_id")
            for period in periods
            for entry in period.get("entries") or []
            if entry.get("user_id")
        )
    )
    identities = await load_accounts(user_ids)
    for period in periods:
        period.pop("assignment_fence_revision", None)
        period["entries"] = [
            {**entry, "employee": identities.get(entry.get("user_id"))}
            for entry in period.get("entries") or []
        ]
    return envelope(periods)


@router.put("/cong-suat")
async def update_capacity(payload: CapacityUpdate, user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    identities = await load_accounts([entry.user_id for entry in payload.entries])
    unknown = sorted({entry.user_id for entry in payload.entries} - set(identities))
    if unknown:
        raise HTTPException(
            status_code=422, detail={"code": "CAPACITY_USER_NOT_FOUND", "user_ids": unknown}
        )
    collection = database.value.resource_capacity_periods
    existing = await collection.find_one(
        {
            "period_start": payload.period_start.isoformat(),
            "period_end": payload.period_end.isoformat(),
        }
    )
    overlapping_period = await collection.find_one(
        {
            "_id": {"$ne": existing["_id"] if existing else None},
            "period_start": {"$lte": payload.period_end.isoformat()},
            "period_end": {"$gte": payload.period_start.isoformat()},
        }
    )
    if overlapping_period:
        raise HTTPException(status_code=409, detail={"code": "CAPACITY_PERIOD_OVERLAP"})
    current_revision = existing.get("revision", 0) if existing else 0
    fence_revision = existing.get("assignment_fence_revision", 0) if existing else 0
    if current_revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": "CAPACITY_REVISION_CONFLICT", "current_revision": current_revision},
        )
    document = {
        "_id": existing["_id"] if existing else new_id("CAP"),
        "period_start": payload.period_start.isoformat(),
        "period_end": payload.period_end.isoformat(),
        "entries": [item.model_dump(mode="json") for item in payload.entries],
        "revision": current_revision + 1,
        "assignment_fence_revision": fence_revision,
        "updated_by": user.id,
        "updated_at": now(),
    }
    if existing:
        result = await collection.replace_one(
            {
                "_id": existing["_id"],
                "revision": current_revision,
                "$or": [
                    {"assignment_fence_revision": fence_revision},
                    {"assignment_fence_revision": {"$exists": False}},
                ],
            },
            document,
        )
        if result.modified_count != 1:
            raise HTTPException(status_code=409, detail={"code": "CAPACITY_REVISION_CONFLICT"})
    else:
        try:
            await collection.insert_one(document)
        except DuplicateKeyError as error:
            raise HTTPException(
                status_code=409, detail={"code": "CAPACITY_REVISION_CONFLICT"}
            ) from error
    await audit(
        user.id,
        "resource_capacity_updated",
        "ResourceCapacity",
        document["_id"],
        None,
        {"revision": document["revision"], "member_count": len(document["entries"])},
    )
    return envelope(
        {key: value for key, value in document.items() if key != "assignment_fence_revision"},
        revision=document["revision"],
    )
