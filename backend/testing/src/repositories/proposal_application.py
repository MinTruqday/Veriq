from pymongo import ReturnDocument

from src.core.database import database


class ProposalApplicationRepository:
    async def find_applied_artifact(self, artifact_id, project_id):
        value = await database.value.test_case_versions.find_one(
            {"_id": artifact_id, "project_id": project_id}
        )
        if value:
            return value
        value = await database.value.test_case_drafts.find_one(
            {"_id": artifact_id, "project_id": project_id}
        )
        if value:
            return value
        return await database.value.test_cases.find_one(
            {"_id": artifact_id, "project_id": project_id}
        )

    async def find_proposal(self, proposal_id):
        return await database.value.maintenance_proposals.find_one(
            {"_id": proposal_id}
        )

    async def transition_proposal(
        self, proposal_id, project_id, revision, source_status, changes
    ):
        return await database.value.maintenance_proposals.find_one_and_update(
            {
                "_id": proposal_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def update_proposal(self, query, changes):
        return await database.value.maintenance_proposals.update_one(
            query, {"$set": changes, "$inc": {"revision": 1}}
        )

    async def find_test_case(self, test_case_id, project_id):
        return await database.value.test_cases.find_one(
            {"_id": test_case_id, "project_id": project_id}
        )

    async def find_test_version(self, version_id, project_id=None):
        query = {"_id": version_id}
        if project_id:
            query["project_id"] = project_id
        return await database.value.test_case_versions.find_one(query)

    async def find_test_draft(self, draft_id, project_id):
        return await database.value.test_case_drafts.find_one(
            {"_id": draft_id, "project_id": project_id}
        )

    async def insert_test_version(self, value):
        await database.value.test_case_versions.insert_one(value)

    async def activate_test_version(
        self,
        test_case_id,
        project_id,
        current_version_id,
        version_id,
        status,
        updated_at,
    ):
        result = await database.value.test_cases.update_one(
            {
                "_id": test_case_id,
                "project_id": project_id,
                "current_version_id": current_version_id,
            },
            {
                "$set": {
                    "current_version_id": version_id,
                    "status": status,
                    "updated_at": updated_at,
                }
            },
        )
        return result.matched_count == 1

    async def set_test_case_status(self, test_case_id, project_id, status, updated_at):
        result = await database.value.test_cases.update_one(
            {"_id": test_case_id, "project_id": project_id},
            {"$set": {"status": status, "updated_at": updated_at}},
        )
        return result.matched_count == 1

    async def mark_previous_traces(self, project_id, target_id, statuses, status, updated_at):
        await database.value.trace_links.update_many(
            {
                "project_id": project_id,
                "target_id": target_id,
                "status": {"$in": statuses},
            },
            {"$set": {"status": status, "updated_at": updated_at}},
        )

    async def find_impact_analysis(self, analysis_id):
        return await database.value.impact_analyses.find_one({"_id": analysis_id})

    async def find_change_set(self, change_set_id):
        return await database.value.requirement_change_sets.find_one(
            {"_id": change_set_id}
        )

    async def list_acceptance_criteria_for_version(self, version_id, project_id):
        return await database.value.acceptance_criteria.find(
            {"requirement_version_id": version_id, "project_id": project_id}
        ).to_list(10000)

    async def list_acceptance_criteria_by_ids(self, criterion_ids, project_id):
        if not criterion_ids:
            return []
        return await database.value.acceptance_criteria.find(
            {"_id": {"$in": criterion_ids}, "project_id": project_id}
        ).to_list(10000)

    async def find_requirement_version(self, version_id, project_id):
        return await database.value.requirement_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def find_trace(self, query):
        return await database.value.trace_links.find_one(query)

    async def insert_trace(self, value):
        await database.value.trace_links.insert_one(value)

    async def mark_test_obsolete(
        self, test_case_id, project_id, current_version_id, status, updated_at
    ):
        result = await database.value.test_cases.update_one(
            {
                "_id": test_case_id,
                "project_id": project_id,
                "current_version_id": current_version_id,
            },
            {"$set": {"status": status, "updated_at": updated_at}},
        )
        return result.matched_count == 1


proposal_application_repository = ProposalApplicationRepository()
