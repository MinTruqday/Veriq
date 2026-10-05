from pymongo import ReturnDocument

from src.core.database import database


class RequirementDocumentRepository:
    @property
    def documents(self):
        return database.value.requirement_documents

    async def find_by_hash(self, project_id, content_hash, created_by):
        return await self.documents.find_one(
            {"project_id": project_id, "content_hash": content_hash, "created_by": created_by}
        )

    async def find(self, document_id, project_id):
        return await self.documents.find_one(
            {"_id": document_id, "project_id": project_id}
        )

    async def list_by_ids(self, project_id, identifiers):
        return await self.documents.find(
            {"project_id": project_id, "_id": {"$in": identifiers}}
        ).to_list(len(identifiers))

    async def insert(self, value):
        await self.documents.insert_one(value)
        return value

    async def list(self, query, limit):
        return await self.documents.find(query).sort("updated_at", -1).limit(limit).to_list(limit)

    async def set_index_result(self, document_id, project_id, index_status, indexed_at):
        return await self.documents.update_one(
            {"_id": document_id, "project_id": project_id},
            {
                "$set": {
                    "index_status": index_status,
                    "indexed_at": indexed_at,
                }
            },
        )

    async def update(self, document_id, project_id, changes, increment_revision=False):
        update = {"$set": changes}
        if increment_revision:
            update["$inc"] = {"revision": 1}
        return await self.documents.update_one(
            {"_id": document_id, "project_id": project_id}, update
        )

    async def update_with_revision(
        self,
        document_id,
        project_id,
        revision,
        changes,
        status=None,
    ):
        query = {
            "_id": document_id,
            "project_id": project_id,
            "revision": revision,
        }
        if status:
            query["status"] = status
        return await self.documents.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def transition_status(
        self,
        document_id,
        project_id,
        source_status,
        changes,
    ):
        return await self.documents.find_one_and_update(
            {
                "_id": document_id,
                "project_id": project_id,
                "status": source_status,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def claim_status(self, document_id, project_id, source_status, revision, target_status, updated_at):
        return await self.documents.update_one(
            {
                "_id": document_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            {
                "$set": {"status": target_status, "updated_at": updated_at},
                "$inc": {"revision": 1},
            },
        )

    async def list_acceptance_criterion_ids(self, project_id, requirement_version_id, limit=1000):
        return await database.value.acceptance_criteria.find(
            {
                "project_id": project_id,
                "requirement_version_id": requirement_version_id,
            },
            {"_id": 1},
        ).to_list(limit)

    async def set_requirement_version_index_result(
        self, version_id, index_status, error_code, updated_at
    ):
        return await database.value.requirement_versions.update_one(
            {"_id": version_id},
            {
                "$set": {
                    "index_status": index_status,
                    "index_error_code": error_code,
                    "updated_at": updated_at,
                }
            },
        )

    async def project_authority_order(self, project_id):
        return await database.value.projects.find_one(
            {"_id": project_id}, {"settings.knowledge_authority_order": 1}
        )

    async def release_exists(self, project_id, release_id):
        return bool(
            await database.value.releases.find_one(
                {"_id": release_id, "project_id": project_id}, {"_id": 1}
            )
        )


requirement_document_repository = RequirementDocumentRepository()
