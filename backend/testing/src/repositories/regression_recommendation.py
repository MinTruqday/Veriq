from pymongo import ReturnDocument

from src.core.database import database


class RegressionRecommendationRepository:
    async def list_recent_runs(self, project_id, limit):
        return await database.value.test_runs.find(
            {"project_id": project_id}
        ).sort("created_at", -1).to_list(limit)

    async def list_results_by_status(self, run_ids, status, limit):
        return await database.value.test_results.find(
            {"test_run_id": {"$in": run_ids}, "status": status}
        ).to_list(limit)

    async def find_by_change_set(self, change_set_id, project_id=None):
        query = {"change_set_id": change_set_id}
        if project_id is not None:
            query["project_id"] = project_id
        return await database.value.regression_recommendations.find_one(
            query, sort=[("created_at", -1)]
        )

    async def find_latest_impact_analysis(self, change_set_id):
        return await database.value.impact_analyses.find_one(
            {"change_set_id": change_set_id}, sort=[("created_at", -1)]
        )

    async def find_test_case(self, test_case_id, project_id):
        return await database.value.test_cases.find_one(
            {"_id": test_case_id, "project_id": project_id}
        )

    async def insert_recommendation(self, value):
        await database.value.regression_recommendations.insert_one(value)
        return value

    async def update_recommendation(self, query, changes):
        return await database.value.regression_recommendations.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def find_suite(self, suite_id, project_id):
        return await database.value.test_suites.find_one(
            {"_id": suite_id, "project_id": project_id}
        )

    async def list_active_test_cases(self, project_id, version_ids, status, limit):
        return await database.value.test_cases.find(
            {
                "project_id": project_id,
                "current_version_id": {"$in": version_ids},
                "status": status,
            }
        ).to_list(limit)

    async def insert_suite(self, value):
        await database.value.test_suites.insert_one(value)
        return value

    async def delete_suite(self, suite_id, project_id):
        await database.value.test_suites.delete_one(
            {"_id": suite_id, "project_id": project_id}
        )

regression_recommendation_repository = RegressionRecommendationRepository()
