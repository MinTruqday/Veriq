from pymongo import ReturnDocument

from src.core.database import database
from src.repositories.common import common_repository


class RequirementClarificationRepository:
    @property
    def collection(self):
        return database.value.requirement_clarifications

    async def insert(self, value, session=None):
        await self.collection.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def list_for_version(self, project_id, requirement_version_id):
        items = await common_repository.list_all_by_id(
            "requirement_clarifications",
            {"project_id": project_id, "requirement_version_id": requirement_version_id},
        )
        return sorted(
            items,
            key=lambda item: (
                str(item.get("created_at") or ""),
                str(item.get("_id") or ""),
            ),
            reverse=True,
        )

    async def list_open_for_version(self, project_id, requirement_version_id, session=None):
        return await common_repository.list_all_by_id(
            "requirement_clarifications",
            {
                "project_id": project_id,
                "requirement_version_id": requirement_version_id,
                "status": {"$in": ["OPEN", "ANSWERED"]},
            },
            session,
        )

    async def list_open_for_versions(self, project_id, requirement_version_ids):
        if not requirement_version_ids:
            return []
        return await common_repository.list_all_by_id(
            "requirement_clarifications",
            {
                "project_id": project_id,
                "requirement_version_id": {"$in": list(requirement_version_ids)},
                "status": {"$in": ["OPEN", "ANSWERED"]},
            },
        )

    async def find(self, clarification_id, project_id=None):
        query = {"_id": clarification_id}
        if project_id:
            query["project_id"] = project_id
        return await self.collection.find_one(query)

    async def find_finding(
        self, project_id, requirement_version_id, finding_key, session=None
    ):
        return await self.collection.find_one(
            {
                "project_id": project_id,
                "requirement_version_id": requirement_version_id,
                "finding_key": finding_key,
            },
            **({"session": session} if session is not None else {}),
        )

    async def replace(self, clarification_id, project_id, revision, changes, session=None):
        return await self.collection.find_one_and_update(
            {"_id": clarification_id, "project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def supersede_for_requirement(
        self, project_id, requirement_id, keep_version_id, timestamp, session=None
    ):
        await self.collection.update_many(
            {
                "project_id": project_id,
                "requirement_id": requirement_id,
                "requirement_version_id": {"$ne": keep_version_id},
                "status": "OPEN",
            },
            {"$set": {"status": "SUPERSEDED", "superseded_at": timestamp, "updated_at": timestamp}, "$inc": {"revision": 1}},
            **({"session": session} if session is not None else {}),
        )


requirement_clarification_repository = RequirementClarificationRepository()
