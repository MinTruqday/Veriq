from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.core.database import database


class SkillProfileRepository:
    @property
    def profiles(self):
        return database.value.member_skill_profiles

    async def find(self, project_id, user_id):
        return await self.profiles.find_one({"project_id": project_id, "user_id": user_id})

    async def upsert(
        self, project_id, user_id, expected_revision, changes, timestamp, *, session=None
    ):
        session_options = {"session": session} if session is not None else {}
        if expected_revision == 0:
            existing = await self.profiles.find_one_and_update(
                {
                    "project_id": project_id,
                    "user_id": user_id,
                    "revision": 0,
                },
                {
                    "$set": {**changes, "updated_at": timestamp},
                    "$inc": {"revision": 1},
                },
                return_document=ReturnDocument.AFTER,
                **session_options,
            )
            if existing:
                return existing
            document = {
                "project_id": project_id,
                "user_id": user_id,
                **changes,
                "revision": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            try:
                await self.profiles.insert_one(document, **session_options)
                return document
            except DuplicateKeyError:
                return await self.profiles.find_one_and_update(
                    {
                        "project_id": project_id,
                        "user_id": user_id,
                        "revision": 0,
                    },
                    {
                        "$set": {**changes, "updated_at": timestamp},
                        "$inc": {"revision": 1},
                    },
                    return_document=ReturnDocument.AFTER,
                    **session_options,
                )
        return await self.profiles.find_one_and_update(
            {
                "project_id": project_id,
                "user_id": user_id,
                "revision": expected_revision,
            },
            {"$set": {**changes, "updated_at": timestamp}, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            **session_options,
        )

    async def fence_assignment_revisions(
        self, project_id, expected_revisions, timestamp, *, session
    ):
        """Serialize assignment against concurrent edits to the same skill profiles."""
        for user_id, expected_revision in expected_revisions.items():
            selector = {
                "project_id": project_id,
                "user_id": user_id,
                "revision": expected_revision,
            }
            update = {
                "$inc": {"assignment_fence_revision": 1},
                "$set": {"assignment_fence_updated_at": timestamp},
            }
            if expected_revision == 0:
                update["$setOnInsert"] = {
                    "skills": [],
                    "experiences": [],
                    "availability": "AVAILABLE",
                    "created_at": timestamp,
                }
            result = await self.profiles.update_one(
                selector,
                update,
                upsert=expected_revision == 0,
                session=session,
            )
            if expected_revision != 0 and result.matched_count != 1:
                return [user_id]
        return []

    async def list_for_members(self, project_id, user_ids, session=None):
        if not user_ids:
            return []
        return await self.profiles.find(
            {"project_id": project_id, "user_id": {"$in": user_ids}},
            session=session,
        ).to_list(len(user_ids))

    async def iter_active_runs(self, project_id, user_ids, session=None):
        if not user_ids:
            return
        cursor = database.value.test_runs.find(
            {
                "project_id": project_id,
                "status": {"$in": ["READY", "IN_PROGRESS"]},
            },
            {"assignee_id": 1, "test_case_assignments": 1},
            session=session,
        )
        async for run in cursor:
            yield run

    async def iter_active_runs_for_members(self, user_ids, session=None):
        if not user_ids:
            return
        cursor = database.value.test_runs.find(
            {
                "status": {"$in": ["READY", "IN_PROGRESS"]},
                "$or": [
                    {"assignee_id": {"$in": user_ids}},
                    {
                        "$expr": {
                            "$gt": [
                                {
                                    "$size": {
                                        "$filter": {
                                            "input": {
                                                "$objectToArray": {
                                                    "$ifNull": ["$test_case_assignments", {}]
                                                }
                                            },
                                            "as": "assignment",
                                            "cond": {"$in": ["$$assignment.v", user_ids]},
                                        }
                                    }
                                },
                                0,
                            ]
                        }
                    },
                ],
            },
            {"project_id": 1, "assignee_id": 1, "test_case_assignments": 1},
            session=session,
        )
        async for run in cursor:
            yield run


skill_profile_repository = SkillProfileRepository()
