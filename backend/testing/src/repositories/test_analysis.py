from pymongo import ReturnDocument

from src.core.database import database


class TestAnalysisRepository:
    async def find_ai_result(self, project_id, idempotency_key):
        return await database.value.ai_results.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def list_ai_results(self, project_id, limit):
        return await database.value.ai_results.find(
            {
                "project_id": project_id,
                "result_type": {"$in": ["TEST_CONDITION_CANDIDATES", "TESTABILITY_BLUEPRINT"]},
            },
            {"basis_snapshots": 0, "created_by": 0},
        ).sort("created_at", -1).limit(limit).to_list(limit)

    async def find_latest_blueprint(
        self, project_id, requirement_version_id, source_hash=None
    ):
        query = {
                "project_id": project_id,
                "result_type": {"$in": ["TEST_CONDITION_CANDIDATES", "TESTABILITY_BLUEPRINT"]},
                "testability_blueprint": {"$ne": None},
                "basis_snapshots.resolved_id": requirement_version_id,
            }
        if source_hash:
            query["basis_snapshots.source_hash"] = source_hash
        results = await database.value.ai_results.find(
            query,
            {
                "testability_blueprint": 1,
                "testability_blueprint_before_review": 1,
                "blueprint_self_review": 1,
                "blueprint_ai_metadata": 1,
                "basis_snapshots": 1,
                "created_at": 1,
            },
        ).sort("created_at", -1).limit(20).to_list(20)
        for result in results:
            snapshot = next(
                (
                    item
                    for item in result.get("basis_snapshots", [])
                    if item.get("resolved_id") == requirement_version_id
                ),
                None,
            )
            if (
                snapshot
                and source_hash
                and snapshot.get("source_hash") == source_hash
            ) or (snapshot and source_hash is None):
                return result
        return None

    async def find_blueprint_for_sources(self, project_id, basis_snapshots):
        def signature(items):
            return sorted(
                (
                    str(item.get("resolved_id") or item.get("artifact_version_id") or item.get("artifact_id") or ""),
                    str(item.get("source_hash") or ""),
                    str(item.get("text") or ""),
                )
                for item in items
            )

        expected = signature(basis_snapshots)
        if not expected:
            return None
        results = await database.value.ai_results.find(
            {
                "project_id": project_id,
                "result_type": {"$in": ["TEST_CONDITION_CANDIDATES", "TESTABILITY_BLUEPRINT"]},
                "testability_blueprint": {"$ne": None},
            },
            {
                "testability_blueprint": 1,
                "testability_blueprint_before_review": 1,
                "blueprint_self_review": 1,
                "blueprint_ai_metadata": 1,
                "basis_snapshots": 1,
                "created_at": 1,
            },
        ).sort("created_at", -1).limit(100).to_list(100)
        return next(
            (
                result
                for result in results
                if signature(result.get("basis_snapshots", [])) == expected
            ),
            None,
        )

    async def insert_ai_result(self, value, session=None):
        await database.value.ai_results.insert_one(value, session=session)
        return value

    async def list_conditions(self, project_id, archived_status, limit):
        return await database.value.test_conditions.find(
            {"project_id": project_id, "status": {"$ne": archived_status}}
        ).sort([("_id", 1)]).limit(limit + 1).to_list(limit + 1)

    async def list_scenarios(self, project_id, condition_ids, limit):
        return await database.value.test_scenarios.find(
            {"project_id": project_id, "test_condition_ids": {"$in": condition_ids}}
        ).sort([("_id", 1)]).limit(limit + 1).to_list(limit + 1)

    async def list_case_versions(self, project_id, condition_ids, scenario_ids, limit):
        return await database.value.test_cases.aggregate([
            {"$match": {"project_id": project_id, "status": "ACTIVE", "current_version_id": {"$ne": None}}},
            {"$lookup": {"from": "test_case_versions", "localField": "current_version_id", "foreignField": "_id", "as": "version"}},
            {"$unwind": "$version"},
            {"$replaceRoot": {"newRoot": "$version"}},
            {"$match": {
                "project_id": project_id,
                "$or": [
                    {"test_condition_ids": {"$in": condition_ids}},
                    {"scenario_id": {"$in": scenario_ids}},
                ],
            }},
            {"$sort": {"_id": 1}},
            {"$limit": limit + 1},
        ]).to_list(limit + 1)

    async def list_findings(self, query, limit):
        return await database.value.test_analysis_findings.find(query).sort(
            "updated_at", -1
        ).limit(limit).to_list(limit)

    async def find_basis(self, collection_name, identifier, project_id):
        return await database.value[collection_name].find_one(
            {"_id": identifier, "project_id": project_id}, {"_id": 1}
        )

    async def insert_finding(self, value):
        await database.value.test_analysis_findings.insert_one(value)
        return value

    async def find_finding(self, finding_id):
        return await database.value.test_analysis_findings.find_one({"_id": finding_id})

    async def find_active_member(self, project_id, user_id, status):
        return await database.value.project_members.find_one(
            {"project_id": project_id, "user_id": user_id, "status": status}
        )

    async def update_finding(self, query, changes):
        return await database.value.test_analysis_findings.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )


test_analysis_repository = TestAnalysisRepository()
