from pymongo import ReturnDocument

from src.core.database import database


class BulkOperationRepository:
    collections = {
        "requirement": "requirements",
        "test_case": "test_cases",
    }

    async def find_operation(self, project_id, idempotency_key):
        return await database.value.bulk_operations.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_operation(self, operation, session=None):
        await database.value.bulk_operations.insert_one(operation, session=session)

    async def find_artifact(self, artifact_type, artifact_id, project_id):
        return await database.value[self.collections[artifact_type]].find_one(
            {"_id": artifact_id, "project_id": project_id}
        )

    async def update_artifact_tags(
        self, artifact_type, artifact_id, project_id, tags, updated_at, session=None
    ):
        return await database.value[self.collections[artifact_type]].update_one(
            {"_id": artifact_id, "project_id": project_id},
            {"$set": {"tags": tags, "updated_at": updated_at}},
            session=session,
        )

    async def find_suite(self, suite_id, project_id):
        return await database.value.test_suites.find_one(
            {"_id": suite_id, "project_id": project_id}
        )

    async def find_current_case(self, test_case_id, project_id, excluded_status):
        return await database.value.test_cases.find_one(
            {
                "_id": test_case_id,
                "project_id": project_id,
                "status": {"$ne": excluded_status},
            }
        )

    async def update_suite_versions(
        self, suite_id, project_id, expected_revision, version_ids, updated_at, session=None
    ):
        return await database.value.test_suites.find_one_and_update(
            {
                "_id": suite_id,
                "project_id": project_id,
                "revision": expected_revision,
            },
            {
                "$set": {
                    "test_case_version_ids": version_ids,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )

    async def mark_case_review_required(
        self,
        test_case_id,
        project_id,
        excluded_status,
        target_status,
        reason,
        user_id,
        updated_at,
        session=None,
    ):
        return await database.value.test_cases.update_one(
            {
                "_id": test_case_id,
                "project_id": project_id,
                "status": {"$ne": excluded_status},
            },
            {
                "$set": {
                    "status": target_status,
                    "review_required_reason": reason,
                    "review_required_by": user_id,
                    "updated_at": updated_at,
                }
            },
            session=session,
        )

    async def find_active_run(self, project_id, statuses, test_case_version_id):
        return await database.value.test_runs.find_one(
            {
                "project_id": project_id,
                "status": {"$in": statuses},
                "test_case_version_ids": test_case_version_id,
            },
            {"_id": 1},
        )

    async def archive_artifact(
        self,
        artifact_type,
        artifact_id,
        project_id,
        current_version_id,
        status,
        reason,
        user_id,
        archived_at,
        session=None,
    ):
        return await database.value[self.collections[artifact_type]].update_one(
            {
                "_id": artifact_id,
                "project_id": project_id,
                "current_version_id": current_version_id,
            },
            {
                "$set": {
                    "status": status,
                    "obsolete_reason": reason,
                    "obsolete_by": user_id,
                    "obsolete_at": archived_at,
                    "updated_at": archived_at,
                }
            },
            session=session,
        )

    async def find_impact_analysis(self, analysis_id, project_id):
        return await database.value.impact_analyses.find_one(
            {"_id": analysis_id, "project_id": project_id}
        )

    async def count_proposals(self, analysis_id):
        return await database.value.maintenance_proposals.count_documents(
            {"impact_analysis_id": analysis_id}
        )

    async def find_proposal(self, proposal_id, project_id):
        return await database.value.maintenance_proposals.find_one(
            {"_id": proposal_id, "project_id": project_id}
        )

    async def find_case_version_identity(self, test_case_id, project_id):
        return await database.value.test_cases.find_one(
            {"_id": test_case_id, "project_id": project_id},
            {"current_version_id": 1},
        )


bulk_operation_repository = BulkOperationRepository()
