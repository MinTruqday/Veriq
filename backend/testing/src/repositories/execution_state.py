from src.core.database import database


class ExecutionPolicyRepository:
    async def project_settings(self, project_id):
        return await database.value.projects.find_one({"_id": project_id}, {"settings": 1})

    async def active_membership_role(self, project_id, user_id, active_status):
        return await database.value.project_members.find_one(
            {"project_id": project_id, "user_id": user_id, "status": active_status},
            {"project_role": 1},
        )

    async def list_results(self, run_id, version_ids, limit=10000):
        return await database.value.test_results.find(
            {"test_run_id": run_id, "test_case_version_id": {"$in": version_ids}}
        ).to_list(limit)

    async def find_result(self, result_id):
        return await database.value.test_results.find_one({"_id": result_id})

    async def find_test_case_version(self, version_id, project_id):
        return await database.value.test_case_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def count_test_case_versions(self, project_id, version_ids):
        return await database.value.test_case_versions.count_documents(
            {"project_id": project_id, "_id": {"$in": version_ids}}
        )


execution_policy_repository = ExecutionPolicyRepository()
