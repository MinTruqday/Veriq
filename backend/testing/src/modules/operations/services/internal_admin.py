import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException

from src.repositories.internal_admin import internal_admin_repository




def attachment_size(value):
    if isinstance(value, dict):
        return sum(
            int(item)
            if key in set(['size', 'size_bytes', 'bytes', 'byte_size'])
            and isinstance(item, (int, float))
            else attachment_size(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return sum(attachment_size(item) for item in value)
    return 0


class InternalAdminService:
    @staticmethod
    async def user_memberships(user_id):
        return await internal_admin_repository.list_memberships(
            {"user_id": user_id},
            {"project_id": 1, "project_role": 1, "status": 1, "membership_revision": 1},
            5000,
        )

    @staticmethod
    async def projects(search, status, limit):
        query = {}
        if status:
            query["status"] = status
        if search:
            pattern = re.escape(search.strip())
            query["$or"] = [
                {"key": {"$regex": pattern, "$options": "i"}},
                {"name": {"$regex": pattern, "$options": "i"}},
            ]
        values = await internal_admin_repository.list_projects(
            query,
            {
                "key": 1,
                "name": 1,
                "status": 1,
                "administrative_status": 1,
                "project_type": 1,
                "quota": 1,
                "created_by": 1,
                "created_at": 1,
                "updated_at": 1,
            },
            limit,
            ("updated_at", -1),
        )
        project_ids = [project["_id"] for project in values]
        counts = await internal_admin_repository.member_counts(project_ids, limit)
        by_project = {item["_id"]: item["count"] for item in counts}
        return [{**project, "member_count": by_project.get(project["_id"], 0)} for project in values]

    @staticmethod
    async def project(project_id):
        value = await internal_admin_repository.find_project(
            project_id,
            {
                "key": 1,
                "name": 1,
                "status": 1,
                "project_type": 1,
                "created_by": 1,
                "created_at": 1,
                "updated_at": 1,
                "revision": 1,
                "quota": 1,
            },
        )
        if not value:
            raise HTTPException(status_code=404, detail={"code": 'PROJECT_NOT_FOUND'})
        value["member_count"] = await internal_admin_repository.count_members(project_id)
        value["active_member_count"] = await internal_admin_repository.count_members(
            project_id, 'ACTIVE'
        )
        return value

    @staticmethod
    async def change_status(project_id, payload):
        timestamp = datetime.now(timezone.utc)
        value = await internal_admin_repository.update_project(
            project_id,
            {
                "administrative_status": payload.status,
                "administrative_reason": payload.reason,
                "administrative_updated_by": payload.actor_id,
                "administrative_updated_at": timestamp,
                "updated_at": timestamp,
            },
        )
        if not value:
            raise HTTPException(status_code=404, detail={"code": 'PROJECT_NOT_FOUND'})
        return value

    @staticmethod
    async def change_quota(project_id, payload):
        value = await internal_admin_repository.update_project(
            project_id,
            {
                "quota": payload.quota,
                "quota_updated_by": payload.actor_id,
                "quota_updated_at": datetime.now(timezone.utc),
            },
        )
        if not value:
            raise HTTPException(status_code=404, detail={"code": 'PROJECT_NOT_FOUND'})
        return {"project_id": project_id, "quota": payload.quota}

    @staticmethod
    async def project_memberships(project_id):
        if not await internal_admin_repository.find_project(project_id, {"_id": 1}):
            raise HTTPException(status_code=404, detail={"code": 'PROJECT_NOT_FOUND'})
        return await internal_admin_repository.list_memberships(
            {"project_id": project_id},
            {
                "user_id": 1,
                "project_role": 1,
                "project_roles": 1,
                "status": 1,
                "membership_revision": 1,
                "created_at": 1,
                "updated_at": 1,
            },
            10000,
            ("updated_at", -1),
        )

    @staticmethod
    async def delete_project(project_id, payload):
        value = await internal_admin_repository.find_project(project_id, {"key": 1})
        if not value:
            raise HTTPException(status_code=404, detail={"code": 'PROJECT_NOT_FOUND'})
        if payload.confirmation != value.get("key"):
            raise HTTPException(
                status_code=422,
                detail={"code": 'PROJECT_CONFIRMATION_MISMATCH'},
            )
        deleted = await internal_admin_repository.purge_project(
            project_id,
            set(['audit_events', 'counters', 'projects']),
            f"^{re.escape(project_id)}:",
        )
        return {"project_id": project_id, "project_key": value.get("key"), "deleted": deleted}

    @staticmethod
    async def break_glass_grants(active_only):
        query = (
            {
                "status": 'ACTIVE',
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            }
            if active_only
            else {}
        )
        return await internal_admin_repository.list_break_glass_grants(
            query, 1000
        )

    @staticmethod
    async def create_break_glass_grant(payload):
        if not await internal_admin_repository.find_project(payload.project_id, {"_id": 1}):
            raise HTTPException(status_code=404, detail={"code": 'PROJECT_NOT_FOUND'})
        timestamp = datetime.now(timezone.utc)
        value = {
            "_id": f"{'break-glass'}-{uuid4().hex}",
            "project_id": payload.project_id,
            "user_id": payload.user_id,
            "permissions": sorted(set(payload.permissions)),
            "status": 'ACTIVE',
            "reason": payload.reason,
            "created_by": payload.actor_id,
            "created_at": timestamp,
            "expires_at": timestamp + timedelta(minutes=payload.ttl_minutes),
        }
        await internal_admin_repository.insert_break_glass_grant(value)
        return value

    @staticmethod
    async def revoke_break_glass_grant(grant_id, payload):
        value = await internal_admin_repository.revoke_break_glass_grant(
            grant_id,
            'ACTIVE',
            'REVOKED',
            {
                "revoked_by": payload.actor_id,
                "revoked_at": datetime.now(timezone.utc),
                "revoke_reason": payload.reason,
            },
        )
        if not value:
            raise HTTPException(
                status_code=409, detail={"code": 'BREAK_GLASS_NOT_ACTIVE'}
            )
        return value

    @staticmethod
    async def operations_metrics():
        return {
            "impact_analyses": await internal_admin_repository.count_records(
                "impact_analyses", {}
            ),
            "degraded_impact_analyses": await internal_admin_repository.count_records(
                "impact_analyses", {"mode": 'DEGRADED_AI'}
            ),
            "pending_proposals": await internal_admin_repository.count_records(
                "maintenance_proposals", {"status": 'PENDING'}
            ),
        }

    @staticmethod
    async def rag_status():
        values = {}
        for collection_name in ['requirement_documents', 'requirement_versions', 'test_case_versions']:
            values[collection_name] = await internal_admin_repository.index_status_counts(
                collection_name,
                'UNKNOWN',
                100,
            )
        return values

    @staticmethod
    async def reindex_candidates(payload):
        if not await internal_admin_repository.find_project(payload.project_id, {"_id": 1}):
            raise HTTPException(status_code=404, detail={"code": 'PROJECT_NOT_FOUND'})
        artifact_ids = list(dict.fromkeys(payload.artifact_version_ids))
        if not artifact_ids:
            requirement_ids = await internal_admin_repository.distinct_ids(
                "requirement_versions",
                payload.project_id,
                'BASELINED',
            )
            test_case_ids = await internal_admin_repository.distinct_ids(
                "test_case_versions",
                payload.project_id,
                'APPROVED',
            )
            artifact_ids = requirement_ids + test_case_ids
        return {"artifact_version_ids": artifact_ids}

    @staticmethod
    async def storage_usage():
        projects = await internal_admin_repository.list_projects(
            {}, {"key": 1, "name": 1}, 10000
        )
        
        values = []
        for project in projects:
            total = 0
            files = 0
            for collection_name, field in [['requirement_documents', 'raw_source'],
 ['test_case_drafts', 'attachments'],
 ['test_case_versions', 'attachments'],
 ['test_results', 'attachments'],
 ['defects', 'attachments']]:
                documents = await internal_admin_repository.list_project_documents(
                    collection_name,
                    project["_id"],
                    field,
                    100000,
                )
                for document in documents:
                    value = document.get(field)
                    total += attachment_size(value)
                    files += len(value) if isinstance(value, list) else int(bool(value))
            values.append(
                {
                    "project_id": project["_id"],
                    "project_key": project.get("key"),
                    "project_name": project.get("name"),
                    "bytes": total,
                    "files": files,
                }
            )
        values.sort(key=lambda item: item["bytes"], reverse=True)
        return {
            "projects": values,
            "total_bytes": sum(item["bytes"] for item in values),
            "total_files": sum(item["files"] for item in values),
        }
