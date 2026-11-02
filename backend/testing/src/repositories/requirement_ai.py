from pymongo import ReturnDocument

from src.core.database import database


class RequirementAiRepository:
    async def find_finding(self, query, session=None):
        return await database.value.ai_findings.find_one(
            query, **({"session": session} if session is not None else {})
        )

    async def find_quality_analysis_request(self, query):
        return await database.value.ai_findings.find_one(query)

    async def insert_quality_analysis_claim(self, value):
        await database.value.ai_findings.insert_one(value)
        return value

    async def reclaim_quality_analysis_claim(self, claim_id, fingerprint, timestamp, token, lease_expires_at):
        return await database.value.ai_findings.find_one_and_update(
            {
                "_id": claim_id,
                "result_type": "REQUIREMENT_QUALITY_ANALYSIS_PENDING",
                "request_fingerprint": fingerprint,
                "lease_expires_at": {"$lte": timestamp},
            },
            {
                "$set": {
                    "claim_token": token,
                    "lease_expires_at": lease_expires_at,
                    "claimed_at": timestamp,
                },
                "$inc": {"attempt": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def replace_quality_analysis_claim(self, claim_id, token, result, session=None):
        response = await database.value.ai_findings.replace_one(
            {
                "_id": claim_id,
                "result_type": "REQUIREMENT_QUALITY_ANALYSIS_PENDING",
                "claim_token": token,
            },
            result,
            **({"session": session} if session is not None else {}),
        )
        return response.modified_count == 1

    async def release_quality_analysis_claim(self, claim_id, token):
        await database.value.ai_findings.delete_one(
            {
                "_id": claim_id,
                "result_type": "REQUIREMENT_QUALITY_ANALYSIS_PENDING",
                "claim_token": token,
            }
        )

    async def find_latest_quality_analysis(self, project_id, version_id):
        values = await (
            database.value.ai_findings.find(
                {
                    "project_id": project_id,
                    "artifact_id": version_id,
                    "artifact_type": "requirement_version",
                    "result_type": "REQUIREMENT_QUALITY_ANALYSIS",
                }
            )
            .sort([("created_at", -1), ("_id", -1)])
            .limit(1)
            .to_list(1)
        )
        return values[0] if values else None

    async def list_acceptance_criteria(self, version_id, limit, session=None):
        return await database.value.acceptance_criteria.find(
            {"requirement_version_id": version_id},
            **({"session": session} if session is not None else {}),
        ).to_list(limit)

    async def insert_finding(self, value, session=None):
        await database.value.ai_findings.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def update_requirement(self, query, changes, session=None):
        return await database.value.requirement_versions.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def delete_acceptance_criteria(self, version_id, session=None):
        await database.value.acceptance_criteria.delete_many(
            {"requirement_version_id": version_id},
            **({"session": session} if session is not None else {}),
        )

    async def find_requirement_version(self, version_id, session=None):
        return await database.value.requirement_versions.find_one(
            {"_id": version_id}, **({"session": session} if session is not None else {})
        )

    async def mark_suggestion_applied(
        self, finding_id, project_id, suggestion_id, updated_at, session=None
    ):
        result = await database.value.ai_findings.update_one(
            {"_id": finding_id, "project_id": project_id},
            {
                "$addToSet": {"applied_suggestion_ids": suggestion_id},
                "$set": {"updated_at": updated_at},
            },
            **({"session": session} if session is not None else {}),
        )
        return result.matched_count == 1


requirement_ai_repository = RequirementAiRepository()
