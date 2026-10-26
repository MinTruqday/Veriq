from pymongo import ReturnDocument

from src.core.database import database


class CommonRepository:
    async def list_all_by_id(self, collection_name, query, session=None):
        """Read a complete result set in stable keyset pages, optionally in a transaction."""
        records = []
        last_id = None
        while True:
            page_query = dict(query)
            if last_id is not None:
                id_after_cursor = {"_id": {"$gt": last_id}}
                if "_id" in page_query:
                    page_query = {"$and": [page_query, id_after_cursor]}
                else:
                    page_query.update(id_after_cursor)
            page = await database.value[collection_name].find(
                page_query, **({"session": session} if session is not None else {})
            ).sort("_id", 1).to_list(500)
            if not page:
                break
            records.extend(page)
            last_id = page[-1]["_id"]
            if len(page) < 500:
                break
        return records

    async def list_all_acceptance_criteria(self, requirement_version_id, session=None):
        """Read every criterion for one Requirement version without silent truncation."""
        return await self.list_all_by_id(
            "acceptance_criteria",
            {"requirement_version_id": requirement_version_id},
            session,
        )

    async def insert_audit_event(self, event, session=None):
        await database.value.audit_events.insert_one(
            event, **({"session": session} if session is not None else {})
        )
        return event

    async def find_project(self, project_id, projection=None):
        return await database.value.projects.find_one({"_id": project_id}, projection)

    async def find_membership(self, project_id, user_id, status=None, projection=None):
        query = {"project_id": project_id, "user_id": user_id}
        if status:
            query["status"] = status
        return await database.value.project_members.find_one(query, projection)

    async def find_active_grant(self, project_id, user_id, active_status, active_after):
        return await database.value.break_glass_grants.find_one(
            {
                "project_id": project_id,
                "user_id": user_id,
                "status": active_status,
                "expires_at": {"$gt": active_after},
            }
        )

    async def find_entity_identity(self, collection, entity_id, projection):
        return await database.value[collection].find_one({"_id": entity_id}, projection)

    async def find_project_entity(self, collection, entity_id, project_id):
        return await database.value[collection].find_one(
            {"_id": entity_id, "project_id": project_id}
        )

    async def optimistic_patch(
        self,
        collection,
        entity_id,
        project_id,
        expected_revision,
        changes,
        include_project_scope=True,
        session=None,
    ):
        scope = {"_id": entity_id, "revision": expected_revision}
        if include_project_scope:
            scope["project_id"] = project_id
        return await database.value[collection].find_one_and_update(
            scope,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def find_entity(self, collection, entity_id):
        return await database.value[collection].find_one({"_id": entity_id})

    async def next_counter(self, counter_id):
        return await database.value.counters.find_one_and_update(
            {"_id": counter_id},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )


common_repository = CommonRepository()
