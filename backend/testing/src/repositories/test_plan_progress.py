from src.core.database import database


class TestPlanProgressRepository:
    async def find_plan(self, project_id, plan_id):
        return await database.value.test_plans.find_one(
            {"_id": plan_id, "project_id": project_id}
        )

    async def list_runs(self, project_id, plan_id, limit):
        return await database.value.test_runs.find(
            {"project_id": project_id, "test_plan_id": plan_id}
        ).to_list(limit)

    async def list_results(self, project_id, run_ids, limit):
        if not run_ids:
            return []
        return await database.value.test_results.find(
            {"project_id": project_id, "test_run_id": {"$in": run_ids}}
        ).to_list(limit)

    async def list_defects(self, project_id, result_ids, defect_ids, limit):
        links = []
        if result_ids:
            links.append({"linked_test_result_id": {"$in": list(result_ids)}})
        if defect_ids:
            links.append({"_id": {"$in": list(defect_ids)}})
        if not links:
            return []
        return await database.value.defects.find(
            {"project_id": project_id, "$or": links}
        ).to_list(limit)


test_plan_progress_repository = TestPlanProgressRepository()
