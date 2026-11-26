from pymongo import ReturnDocument

from src.core.database import database


class ExecutionAssetRepository:
    async def list_script_drafts(self, project_id, limit=500):
        return await database.value.automation_script_drafts.find(
            {"project_id": project_id}
        ).sort("updated_at", -1).to_list(limit)

    async def find_script_by_idempotency_key(self, project_id, idempotency_key):
        return await database.value.automation_script_drafts.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_test_case_version(self, project_id, version_id):
        return await database.value.test_case_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def insert_script_draft(self, value, session=None):
        await database.value.automation_script_drafts.insert_one(value, session=session)
        return value

    async def list_executions(self, project_id, limit=1000):
        return await database.value.automation_executions.find(
            {"project_id": project_id}
        ).sort("created_at", -1).to_list(limit)

    async def find_execution_by_idempotency_key(self, project_id, idempotency_key):
        return await database.value.automation_executions.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_confirmed_postman_import(self, project_id, artifact_id, artifact_format, status):
        return await database.value.api_imports.find_one(
            {
                "_id": artifact_id,
                "project_id": project_id,
                "format": artifact_format,
                "status": status,
            }
        )

    async def find_approved_playwright_script(self, project_id, script_id, framework, status):
        return await database.value.automation_script_drafts.find_one(
            {
                "_id": script_id,
                "project_id": project_id,
                "framework": framework,
                "status": status,
            }
        )

    async def find_active_environment(self, project_id, environment_id, archived_status):
        return await database.value.test_environments.find_one(
            {
                "_id": environment_id,
                "project_id": project_id,
                "status": {"$ne": archived_status},
            }
        )

    async def insert_execution(self, value, session=None):
        await database.value.automation_executions.insert_one(value, session=session)
        return value

    async def transition_execution(self, execution_id, revision, source_status, changes):
        return await database.value.automation_executions.find_one_and_update(
            {"_id": execution_id, "revision": revision, "status": source_status},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def rollback_queued_execution(
        self,
        execution_id,
        revision,
        operation_id,
        queued_status,
        created_status,
        updated_at,
    ):
        return await database.value.automation_executions.update_one(
            {
                "_id": execution_id,
                "revision": revision + 1,
                "status": queued_status,
                "operation_id": operation_id,
            },
            {
                "$set": {"status": created_status, "revision": revision, "updated_at": updated_at},
                "$unset": {"operation_id": "", "start_idempotency_key": "", "queued_at": ""},
            },
        )

    async def find_execution_operation(self, execution_id, operation_id):
        return await database.value.automation_executions.find_one(
            {"_id": execution_id, "operation_id": operation_id}
        )

    async def ingest_execution_result(
        self,
        execution_id,
        operation_id,
        source_statuses,
        changes,
    ):
        return await database.value.automation_executions.find_one_and_update(
            {
                "_id": execution_id,
                "operation_id": operation_id,
                "status": {"$in": list(source_statuses)},
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

execution_asset_repository = ExecutionAssetRepository()
