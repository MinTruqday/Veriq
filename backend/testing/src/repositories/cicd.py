from pymongo import ReturnDocument

from src.core.database import database


class CiCdRepository:
    async def list_bindings(self, project_id, limit):
        return (
            await database.value.cicd_bindings.find({"project_id": project_id})
            .sort("updated_at", -1)
            .to_list(limit)
        )

    async def list_runs(self, project_id, limit):
        return (
            await database.value.pipeline_runs.find({"project_id": project_id})
            .sort("created_at", -1)
            .to_list(limit)
        )

    async def list_reconciliations(self, project_id, limit):
        return (
            await database.value.cicd_reconciliation_jobs.find({"project_id": project_id})
            .sort("created_at", -1)
            .to_list(limit)
        )

    async def find_active_connector(self, connector_id, project_id, status):
        return await database.value.project_connectors.find_one(
            {
                "_id": connector_id,
                "project_id": project_id,
                "status": status,
                "enabled": True,
            }
        )

    async def find_api_artifact(self, artifact_id, project_id, format_name, status):
        return await database.value.api_imports.find_one(
            {
                "_id": artifact_id,
                "project_id": project_id,
                "format": format_name,
                "status": status,
            }
        )

    async def insert_binding(self, value):
        await database.value.cicd_bindings.insert_one(value)

    async def update_binding(self, binding_id, project_id, revision, changes):
        return await database.value.cicd_bindings.find_one_and_update(
            {"_id": binding_id, "project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def find_run_by_idempotency(self, project_id, idempotency_key):
        return await database.value.pipeline_runs.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_active_binding(self, binding_id, project_id):
        return await database.value.cicd_bindings.find_one(
            {"_id": binding_id, "project_id": project_id, "enabled": True}
        )

    async def insert_execution(self, value, session=None):
        await database.value.automation_executions.insert_one(value, session=session)

    async def insert_run(self, value, session=None):
        await database.value.pipeline_runs.insert_one(value, session=session)

    async def find_run(self, run_id, project_id):
        return await database.value.pipeline_runs.find_one(
            {"_id": run_id, "project_id": project_id}
        )

    async def complete_run(self, run_id, project_id, running_status, changes):
        return await database.value.pipeline_runs.find_one_and_update(
            {"_id": run_id, "project_id": project_id, "status": running_status},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def complete_execution(
        self, execution_id, project_id, running_status, changes
    ):
        return await database.value.automation_executions.update_one(
            {
                "_id": execution_id,
                "project_id": project_id,
                "status": running_status,
            },
            {"$set": changes, "$inc": {"revision": 1}},
        )

    async def find_reconciliation(self, project_id, idempotency_key):
        return await database.value.cicd_reconciliation_jobs.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_reconciliation(self, value, session=None):
        await database.value.cicd_reconciliation_jobs.insert_one(value, session=session)


cicd_repository = CiCdRepository()
