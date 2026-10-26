from pymongo import ReturnDocument

from src.core.database import database
from src.repositories.common import common_repository
from src.schemas.contracts.common import FAILED_OUTCOME


class ActiveTestCaseVersionIntegrityError(Exception):
    """A current Test Case points at a missing or mismatched version record."""


class AnalysisRepository:
    async def list_requirements_by_ids(self, project_id, requirement_ids, limit):
        return await database.value.requirements.find(
            {"project_id": project_id, "_id": {"$in": requirement_ids}},
            {"_id": 1, "requirement_key": 1, "title": 1},
        ).to_list(limit)

    async def list_requirement_version_labels(self, project_id, version_ids, limit):
        return await database.value.requirement_versions.find(
            {"project_id": project_id, "_id": {"$in": version_ids}},
            {"_id": 1, "version": 1},
        ).to_list(limit)

    async def list_change_pair_versions(self, requirement_id, version_ids):
        return await database.value.requirement_versions.find(
            {"requirement_id": requirement_id, "_id": {"$in": version_ids}}
        ).to_list(len(version_ids))

    async def find_change_set_for_target(self, requirement_id, target_version_id):
        return await database.value.requirement_change_sets.find_one(
            {"requirement_id": requirement_id, "to_version_id": target_version_id}
        )

    async def insert_change_set(self, value):
        await database.value.requirement_change_sets.insert_one(value)
        return value

    async def refresh_empty_change_set(
        self, change_set_id, project_id, revision, changes
    ):
        return await database.value.requirement_change_sets.find_one_and_update(
            {
                "_id": change_set_id,
                "project_id": project_id,
                "revision": revision,
                "changes": [],
                "status": "READY",
            },
            {
                "$set": {"changes": changes, "model_version": "semantic_diff"},
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def mark_traces_stale(self, project_id, source_ids, confirmed_status, stale_status, updated_at):
        await database.value.trace_links.update_many(
            {
                "project_id": project_id,
                "source_id": {"$in": source_ids},
                "status": confirmed_status,
            },
            {"$set": {"status": stale_status, "updated_at": updated_at}},
        )

    async def list_change_sets(self, query, sort_field, direction, limit):
        return await database.value.requirement_change_sets.find(query).sort(
            sort_field, direction
        ).to_list(limit)

    async def review_change_set(self, change_set_id, project_id, revision, source_status, changes):
        return await database.value.requirement_change_sets.find_one_and_update(
            {
                "_id": change_set_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def list_acceptance_criteria(self, requirement_version_id, limit=None):
        query = {"requirement_version_id": requirement_version_id}
        if limit is not None:
            return await database.value.acceptance_criteria.find(query).to_list(limit)
        return await common_repository.list_all_acceptance_criteria(requirement_version_id)

    async def list_active_test_case_versions(self, project_id, active_status, limit=2000):
        return await database.value.test_cases.aggregate([
            {"$match": {"project_id": project_id, "status": active_status, "current_version_id": {"$ne": None}}},
            {"$lookup": {"from": "test_case_versions", "localField": "current_version_id", "foreignField": "_id", "as": "version"}},
            {"$unwind": "$version"},
            {"$replaceRoot": {"newRoot": "$version"}},
            {"$limit": limit},
        ]).to_list(limit)

    async def iter_active_test_case_version_pages(self, project_id, active_status, page_size=500):
        """Yield every current active Test Case version in stable bounded pages."""
        last_case_id = None
        while True:
            query = {
                "project_id": project_id,
                "status": active_status,
                "current_version_id": {"$ne": None},
            }
            if last_case_id is not None:
                query["_id"] = {"$gt": last_case_id}
            cases = await database.value.test_cases.find(
                query,
                {"_id": 1, "current_version_id": 1},
            ).sort("_id", 1).to_list(page_size)
            if not cases:
                return
            version_ids = [case["current_version_id"] for case in cases]
            versions = await database.value.test_case_versions.find(
                {"_id": {"$in": version_ids}, "project_id": project_id}
            ).to_list(len(version_ids))
            by_id = {version["_id"]: version for version in versions}
            if len(by_id) != len(cases) or any(
                by_id.get(case["current_version_id"], {}).get("test_case_id") != case["_id"]
                for case in cases
            ):
                raise ActiveTestCaseVersionIntegrityError
            yield [by_id[case["current_version_id"]] for case in cases]
            last_case_id = cases[-1]["_id"]
            if len(cases) < page_size:
                return

    async def list_related_active_test_case_versions(self, project_id, version_id, limit):
        return await database.value.test_cases.aggregate([
            {"$match": {"project_id": project_id, "status": "ACTIVE", "current_version_id": {"$ne": None}}},
            {"$lookup": {"from": "test_case_versions", "localField": "current_version_id", "foreignField": "_id", "as": "version"}},
            {"$unwind": "$version"},
            {"$replaceRoot": {"newRoot": "$version"}},
            {"$match": {"project_id": project_id, "requirement_version_ids": version_id}},
            {"$limit": limit},
        ]).to_list(limit)

    async def list_active_defects(self, project_id, excluded_statuses, limit=2000):
        return await database.value.defects.find(
            {"project_id": project_id, "status": {"$nin": list(excluded_statuses)}}
        ).sort("updated_at", -1).to_list(limit)

    async def list_current_requirements(self, project_id, excluded_status, limit=2000):
        return await database.value.requirements.find(
            {"project_id": project_id, "status": {"$ne": excluded_status}}
        ).to_list(limit)

    async def list_requirement_versions(self, project_id, identifiers, limit=2000):
        return await database.value.requirement_versions.find(
            {"project_id": project_id, "_id": {"$in": identifiers}}
        ).to_list(limit)

    async def list_current_test_cases(
        self, project_id, excluded_status, projection=None, limit=5000
    ):
        return await database.value.test_cases.find(
            {"project_id": project_id, "status": {"$ne": excluded_status}},
            projection,
        ).to_list(limit)

    async def list_test_case_versions(self, project_id, identifiers, projection=None, limit=5000):
        return await database.value.test_case_versions.find(
            {"project_id": project_id, "_id": {"$in": identifiers}},
            projection,
        ).to_list(limit)

    async def find_latest_risk_ranking(self, project_id):
        return await database.value.risk_rankings.find_one(
            {"project_id": project_id},
            sort=[("created_at", -1)],
        )

    async def insert_risk_ranking(self, value):
        await database.value.risk_rankings.insert_one(value)
        return value

    async def failure_counts(self, project_id, limit=5000):
        return await database.value.test_results.aggregate(
            [
                {"$match": {"project_id": project_id, "status": FAILED_OUTCOME}},
                {"$group": {"_id": "$test_case_version_id", "count": {"$sum": 1}}},
            ]
        ).to_list(limit)

    async def upsert_worker_event(self, event_id, value):
        return await database.value.worker_events.update_one(
            {"_id": event_id}, {"$set": value}, upsert=True
        )

    async def find_requirement_version(self, project_id, version_id):
        return await database.value.requirement_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def find_test_case_version(self, project_id, version_id):
        return await database.value.test_case_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def set_artifact_index_result(
        self, collection, project_id, version_id, index_status, error_code, indexed_at
    ):
        return await database.value[collection].update_one(
            {"_id": version_id, "project_id": project_id},
            {
                "$set": {
                    "index_status": index_status,
                    "index_error_code": error_code,
                    "indexed_at": indexed_at,
                }
            },
        )


analysis_repository = AnalysisRepository()
