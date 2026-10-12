import re

from fastapi import HTTPException

from src.clients.worker import WorkerClientError, worker_client
from src.core.auth import CurrentUser
from src.core.common import load_user_identities, now
from src.repositories.operations import operations_repository


class OperationsService:
    @staticmethod
    async def overview(limit, audit_q, audit_event, audit_project_id, user: CurrentUser):
        
        OperationsService._require_system_admin(user)
        failed_ingestion = await operations_repository.list_records(
            "import_jobs",
            {"status": {"$in": ['FAILED', 'PARSE_FAILED']}},
            "created_at",
            limit,
        )
        failed_impact = await operations_repository.list_records(
            "impact_analyses",
            {"status": {"$in": ['FAILED', 'DEGRADED']}},
            "updated_at",
            limit,
        )
        worker_failures = await operations_repository.list_records(
            "worker_events",
            {"status": 'FAILED'},
            "completed_at",
            limit,
        )
        indexing_backlog = await operations_repository.count_records(
            "requirement_versions",
            {"index_status": {"$in": ['PENDING', 'FAILED']}},
        ) + await operations_repository.count_records(
            "test_case_versions",
            {"$or": [
                {"index_status": {"$in": ['PENDING', 'FAILED']}},
                {"index_status": {"$exists": False}},
            ]},
        )
        test_case_approval_backlog = await operations_repository.count_records(
            "test_case_versions",
            {"$or": [
                {"trace_status": {"$in": ['PENDING', 'FAILED']}},
                {"approval_audit_status": {"$in": ['PENDING', 'FAILED']}},
            ]},
        )
        audit_events = await OperationsService._audit_events(
            limit, audit_q, audit_event, audit_project_id
        )
        return {
            "generated_at": now(),
            "failed_ingestion_jobs": failed_ingestion,
            "failed_impact_jobs": failed_impact,
            "worker_failures": worker_failures,
            "storage_usage": await OperationsService._storage_usage(),
            "audit_events": audit_events,
            "knowledge_indexing_backlog": indexing_backlog,
            "test_case_approval_derived_backlog": test_case_approval_backlog,
            "ai_models": {'impact_analysis': 'evidence_impact_analysis',
 'maintenance_proposal': 'maintenance_analysis',
 'regression': 'risk_scoring'},
            "ai_request_metrics": await OperationsService._ai_request_metrics(),
        }

    @staticmethod
    async def retry_failed_job(job_id: str, user: CurrentUser):
        
        OperationsService._require_system_admin(user)
        try:
            return await worker_client.retry(job_id)
        except WorkerClientError as error:
            if error.status_code is None:
                raise HTTPException(
                    status_code=503, detail={"code": 'WORKER_UNAVAILABLE'}
                ) from error
            codes = {
                404: 'JOB_NOT_FOUND',
                409: 'JOB_RETRY_NOT_ALLOWED',
            }
            raise HTTPException(
                status_code=error.status_code,
                detail={"code": codes.get(error.status_code, 'WORKER_RETRY_FAILED')},
            ) from error

    @staticmethod
    def _require_system_admin(user: CurrentUser):
        
        if not user.is_system_admin:
            raise HTTPException(status_code=403, detail={"code": 'PLATFORM_ADMIN_REQUIRED'})

    @staticmethod
    def _attachment_size(value):
        size_keys = set(['size', 'size_bytes', 'bytes', 'byte_size'])
        if isinstance(value, dict):
            total = 0
            for key, item in value.items():
                if key in size_keys and isinstance(
                    item, (int, float)
                ):
                    total += int(item)
                elif isinstance(item, (dict, list)):
                    total += OperationsService._attachment_size(item)
            return total
        if isinstance(value, list):
            return sum(OperationsService._attachment_size(item) for item in value)
        return 0

    @staticmethod
    async def _storage_usage():
        
        projects = await operations_repository.list_records(
            "projects",
            {},
            "updated_at",
            10000,
            {"_id": 1, "key": 1, "name": 1},
        )
        usage = []
        for project in projects:
            total = 0
            file_count = 0
            for collection_name, field in [['requirement_documents', 'raw_source'],
 ['test_case_drafts', 'attachments'],
 ['test_case_versions', 'attachments'],
 ['test_results', 'attachments'],
 ['defects', 'attachments']]:
                rows = await operations_repository.list_project_storage_values(
                    collection_name,
                    project["_id"],
                    field,
                    10000,
                )
                for row in rows:
                    value = row.get(field)
                    total += OperationsService._attachment_size(value)
                    if isinstance(value, list):
                        file_count += len(value)
                    elif isinstance(value, dict) and value:
                        file_count += 1
            usage.append(
                {
                    "project_id": project["_id"],
                    "project_key": project.get("key"),
                    "project_name": project.get("name"),
                    "bytes": total,
                    "files": file_count,
                }
            )
        usage.sort(key=lambda item: item["bytes"], reverse=True)
        return usage

    @staticmethod
    async def _ai_request_metrics():
        
        impact_total = await operations_repository.count_records("impact_analyses", {})
        impact_success = await operations_repository.count_records(
            "impact_analyses", {"ai_result.status": 'SUCCESS'}
        )
        impact_degraded = await operations_repository.count_records(
            "impact_analyses", {"ai_result.status": 'DEGRADED'}
        )
        latency_rows = await operations_repository.average_impact_latency()
        measured = impact_success + impact_degraded
        return {
            "impact_classification": {
                "total": impact_total,
                "success": impact_success,
                "degraded": impact_degraded,
                "success_rate": round(impact_success / measured, 4) if measured else 0,
                "error_rate": round(impact_degraded / measured, 4) if measured else 0,
                "average_latency_ms": round(latency_rows[0]["average_ms"], 3)
                if latency_rows
                else 0,
            },
            "proposals": await operations_repository.count_records(
                "maintenance_proposals", {}
            ),
        }

    @staticmethod
    async def _audit_events(limit, audit_q, audit_event, audit_project_id):
        audit_filter = {}
        if audit_event:
            audit_filter["action"] = audit_event
        if audit_project_id:
            audit_filter["project_id"] = audit_project_id
        if audit_q:
            pattern = re.escape(audit_q)
            audit_filter["$or"] = [
                {"action": {"$regex": pattern, "$options": "i"}},
                {"entity_type": {"$regex": pattern, "$options": "i"}},
                {"entity_id": {"$regex": pattern, "$options": "i"}},
                {"actor_id": {"$regex": pattern, "$options": "i"}},
            ]
        events = await operations_repository.list_records(
            "audit_events", audit_filter, "created_at", limit
        )
        identities = await load_user_identities(event.get("actor_id") for event in events)
        for event in events:
            identity = identities.get(str(event.get("actor_id")))
            event["actor_label"] = identity.get("label") if identity else event.get("actor_id")
            if hasattr(event.get("created_at"), "isoformat"):
                event["created_at"] = event["created_at"].isoformat()
        return events
