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

    async def find_data_set_version(self, project_id, data_set_id, version_id):
        return await database.value.data_set_versions.find_one(
            {
                "_id": version_id,
                "project_id": project_id,
                "data_set_id": data_set_id,
            }
        )

    async def create_data_set(self, data_set, version):
        await database.value.data_set_versions.insert_one(version)
        try:
            await database.value.data_sets.insert_one(data_set)
        except Exception:
            await database.value.data_set_versions.delete_one(
                {"_id": version["_id"], "project_id": data_set["project_id"]}
            )
            raise

    async def list_data_sets(self, query, limit):
        return await database.value.data_sets.find(query).sort(
            "updated_at", -1
        ).to_list(limit)

    async def list_data_set_versions(self, query, limit, newest_first=False):
        cursor = database.value.data_set_versions.find(query)
        if newest_first:
            cursor = cursor.sort("version", -1)
        return await cursor.to_list(limit)

    async def create_data_set_version(self, data_set, version, name, updated_at):
        await database.value.data_set_versions.insert_one(version)
        try:
            result = await database.value.data_sets.update_one(
                {
                    "_id": data_set["_id"],
                    "project_id": data_set["project_id"],
                    "current_version_id": data_set["current_version_id"],
                    "revision": data_set["revision"],
                },
                {
                    "$set": {
                        "name": name,
                        "current_version_id": version["_id"],
                        "updated_at": updated_at,
                    },
                    "$inc": {"revision": 1},
                },
            )
        except Exception:
            await database.value.data_set_versions.delete_one(
                {"_id": version["_id"], "project_id": data_set["project_id"]}
            )
            raise
        if result.matched_count == 1:
            return True
        await database.value.data_set_versions.delete_one(
            {"_id": version["_id"], "project_id": data_set["project_id"]}
        )
        return False

    async def bind_data_set_version(
        self, draft_id, project_id, revision, version_id, draft_status, updated_at
    ):
        return await database.value.test_case_drafts.find_one_and_update(
            {
                "_id": draft_id,
                "project_id": project_id,
                "status": draft_status,
                "revision": revision,
            },
            {
                "$addToSet": {"data_set_version_ids": version_id},
                "$inc": {"revision": 1},
                "$set": {"updated_at": updated_at},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def archive_data_set(
        self,
        data_set_id,
        project_id,
        revision,
        reason,
        active_status,
        archived_status,
        updated_at,
    ):
        return await database.value.data_sets.find_one_and_update(
            {
                "_id": data_set_id,
                "project_id": project_id,
                "status": active_status,
                "revision": revision,
            },
            {
                "$set": {
                    "status": archived_status,
                    "archive_reason": reason,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
        )


execution_asset_repository = ExecutionAssetRepository()
