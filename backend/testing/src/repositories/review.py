from datetime import datetime, timezone

from pymongo import ReturnDocument

from src.core.database import database


class ReviewRepository:
    async def migrate_legacy_finding_blocking(self):
        timestamp = datetime.now(timezone.utc)
        result = await database.value.review_findings.update_many(
            {"blocks_acceptance": {"$exists": False}},
            [{"$set": {"blocks_acceptance": {"$eq": ["$severity", "MAJOR"]}}}],
        )
        if result.modified_count:
            await database.value.audit_events.update_one(
                {"_id": "MIG-review-finding-blocking-v1"},
                {"$setOnInsert": {
                    "actor_id": "SYSTEM_MIGRATION",
                    "action": "review_finding_blocking_policy_migrated",
                    "entity_type": "ReviewFinding",
                    "entity_id": "*",
                    "project_id": None,
                    "created_at": timestamp,
                    "details": {"migrated_count": result.modified_count},
                }},
                upsert=True,
            )
        return result.modified_count

    @property
    def comments(self):
        return database.value.review_comments

    async def find_comment(self, comment_id, project_id):
        return await self.comments.find_one(
            {"_id": comment_id, "project_id": project_id}
        )

    async def insert_comment(self, value):
        await self.comments.insert_one(value)
        return value

    async def list_comments(self, query, limit=5000):
        return await self.comments.find(query).sort("created_at", 1).to_list(limit)

    async def update_comment(self, comment_id, project_id, changes):
        return await self.comments.find_one_and_update(
            {"_id": comment_id, "project_id": project_id},
            {"$set": changes},
            return_document=ReturnDocument.AFTER,
        )

    async def mark_comment_deleted(self, comment_id, project_id, changes):
        return await self.comments.update_one(
            {"_id": comment_id, "project_id": project_id},
            {"$set": changes},
        )

    async def transition_comment(
        self,
        comment_id,
        project_id,
        source_status,
        changes,
    ):
        return await self.comments.find_one_and_update(
            {
                "_id": comment_id,
                "project_id": project_id,
                "status": source_status,
            },
            {"$set": changes},
            return_document=ReturnDocument.AFTER,
        )

    async def count_active_members(self, project_id, user_ids, status):
        return await database.value.project_members.count_documents(
            {"project_id": project_id, "user_id": {"$in": user_ids}, "status": status}
        )

    async def find_review(self, review_id):
        return await database.value.review_sessions.find_one({"_id": review_id})

    async def list_reviews(self, query, limit):
        return await database.value.review_sessions.find(query).sort(
            "updated_at", -1
        ).to_list(limit)

    async def find_artifact(self, collection_name, artifact_id, project_id, extra=None):
        query = {"_id": artifact_id, "project_id": project_id}
        query.update(extra or {})
        return await database.value[collection_name].find_one(query)

    async def find_review_by_idempotency(self, project_id, idempotency_key):
        return await database.value.review_sessions.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def next_sequence(self, counter_id):
        return await database.value.counters.find_one_and_update(
            {"_id": counter_id},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def insert_review(self, value, session=None):
        await database.value.review_sessions.insert_one(value, session=session)
        return value

    async def update_review(self, query, changes):
        return await database.value.review_sessions.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def set_review_fields(self, review_id, changes):
        return await database.value.review_sessions.find_one_and_update(
            {"_id": review_id},
            {"$set": changes},
            return_document=ReturnDocument.AFTER,
        )

    async def find_finding(self, finding_id):
        return await database.value.review_findings.find_one({"_id": finding_id})

    async def list_findings(self, review_id, limit):
        return await database.value.review_findings.find(
            {"review_session_id": review_id}
        ).sort("created_at", 1).to_list(limit)

    async def count_findings(self, query):
        return await database.value.review_findings.count_documents(query)

    async def insert_finding(self, value):
        await database.value.review_findings.insert_one(value)
        return value

    async def update_finding(self, query, changes):
        return await database.value.review_findings.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )


review_repository = ReviewRepository()
