from pymongo import ReturnDocument

from src.core.database import database


class ImpactAnalysisRepository:
    async def find_by_change_and_model(self, change_set_id, model_version):
        return await database.value.impact_analyses.find_one(
            {"change_set_id": change_set_id, "model_version": model_version}
        )

    async def list_acceptance_criteria(self, version_ids, limit):
        return await database.value.acceptance_criteria.find(
            {"requirement_version_id": {"$in": version_ids}}
        ).to_list(limit)

    async def list_trace_links(self, project_id, source_ids, statuses, limit):
        return await database.value.trace_links.find(
            {
                "project_id": project_id,
                "source_id": {"$in": source_ids},
                "status": {"$in": statuses},
            }
        ).to_list(limit)

    async def list_current_tests(self, project_id, statuses, limit):
        return await database.value.test_cases.find(
            {"project_id": project_id, "status": {"$in": statuses}}
        ).to_list(limit)

    async def list_test_versions(self, project_id, version_ids, limit):
        return await database.value.test_case_versions.find(
            {"project_id": project_id, "_id": {"$in": version_ids}}
        ).to_list(limit)

    async def find_requirement_version(self, version_id, project_id):
        return await database.value.requirement_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def insert_analysis(self, value):
        await database.value.impact_analyses.insert_one(value)

    async def commit_analysis_for_change_set(
        self,
        analysis,
        change_set_id,
        project_id,
        expected_revision,
        expected_status,
        updated_at,
        session,
    ):
        changed = await database.value.requirement_change_sets.find_one_and_update(
            {
                "_id": change_set_id,
                "project_id": project_id,
                "revision": expected_revision,
                "status": expected_status,
            },
            {
                "$set": {"status": "ANALYZED", "updated_at": updated_at},
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        if changed is None:
            return False
        await database.value.impact_analyses.insert_one(analysis, session=session)
        return True

    async def set_change_status(self, change_set_id, project_id, status, updated_at):
        await database.value.requirement_change_sets.update_one(
            {"_id": change_set_id, "project_id": project_id},
            {"$set": {"status": status, "updated_at": updated_at}},
        )

    async def find_latest_for_change(self, change_set_id, project_id):
        return await database.value.impact_analyses.find_one(
            {"change_set_id": change_set_id, "project_id": project_id},
            sort=[("created_at", -1)],
        )

    async def transition_analysis(
        self,
        analysis_id,
        project_id,
        revision,
        source_status,
        changes,
        unset=None,
    ):
        update = {"$set": changes, "$inc": {"revision": 1}}
        if unset:
            update["$unset"] = unset
        return await database.value.impact_analyses.find_one_and_update(
            {
                "_id": analysis_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            update,
            return_document=ReturnDocument.AFTER,
        )

    async def delete_analysis(self, analysis_id, project_id):
        await database.value.impact_analyses.delete_one(
            {"_id": analysis_id, "project_id": project_id}
        )

    async def restore_analysis_status(
        self, analysis_id, project_id, source_status, target_status, updated_at
    ):
        await database.value.impact_analyses.update_one(
            {"_id": analysis_id, "project_id": project_id, "status": source_status},
            {
                "$set": {"status": target_status, "updated_at": updated_at},
                "$unset": {"rerun_requested_by": "", "rerun_requested_at": ""},
                "$inc": {"revision": 1},
            },
        )

    async def review_analysis(
        self, analysis_id, project_id, revision, source_status, changes
    ):
        result = await database.value.impact_analyses.update_one(
            {
                "_id": analysis_id,
                "project_id": project_id,
                "revision": revision,
                "status": source_status,
            },
            {"$set": changes, "$inc": {"revision": 1}},
        )
        return result.matched_count == 1

    async def find_analysis(self, analysis_id, project_id):
        return await database.value.impact_analyses.find_one(
            {"_id": analysis_id, "project_id": project_id}
        )

    async def insert_perspective(self, value):
        await database.value.impact_review_perspectives.insert_one(value)


impact_analysis_repository = ImpactAnalysisRepository()
