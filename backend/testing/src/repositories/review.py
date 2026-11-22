from pymongo import ReturnDocument

from src.core.database import database


class ReviewRepository:
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

    async def find_artifact(self, collection_name, artifact_id, project_id, extra=None):
        query = {"_id": artifact_id, "project_id": project_id}
        query.update(extra or {})
        return await database.value[collection_name].find_one(query)

    async def next_sequence(self, counter_id):
        return await database.value.counters.find_one_and_update(
            {"_id": counter_id},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )


review_repository = ReviewRepository()
