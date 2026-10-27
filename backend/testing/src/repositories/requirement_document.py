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

    async def find_by_deduplication_key(self, project_id, deduplication_key):
        return await self.documents.find_one(
            {
                "project_id": project_id,
                "deduplication_key": deduplication_key,
            }
        )

    async def find_reusable_duplicate(
        self,
        project_id,
        content_hash,
        format,
        visibility,
        shared_with,
        ai_enabled,
        source_type,
        user_id,
        ocr_language=None,
    ):
        if visibility not in {"project", "shared"}:
            return None
        if visibility == "shared" and user_id not in shared_with:
            return None
        query = {
            "project_id": project_id,
            "content_hash": content_hash,
            "format": format,
            "visibility": visibility,
            "ai_enabled": ai_enabled,
            "source_type": source_type,
            "ocr_language": ocr_language,
            "status": {"$nin": ["ARCHIVED", "PARSE_FAILED"]},
        }
        if visibility == "shared":
            query["shared_with"] = shared_with
        return await self.documents.find_one(query)

    async def latest_in_source_series(self, project_id, source_series_id):
        return await self.documents.find_one(
            {"project_id": project_id, "source_series_id": source_series_id},
            sort=[("source_version_sequence", -1)],
        )

    async def list_source_series(self, project_id, source_series_id):
        return await self.documents.find(
            {"project_id": project_id, "source_series_id": source_series_id}
        ).sort([("source_version_sequence", 1), ("_id", 1)]).to_list(None)

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

    async def next_parse_candidate(self, stale_before, available_at):
        return await self.documents.find_one(
            {
                "$or": [
                    {
                        "status": "UPLOADED",
                        "$or": [
                            {"parse_next_attempt_at": {"$exists": False}},
                            {"parse_next_attempt_at": {"$lte": available_at}},
                        ],
                    },
                    {
                        "status": "PARSING",
                        "updated_at": {"$lte": stale_before},
                        "$or": [
                            {"parse_next_attempt_at": {"$exists": False}},
                            {"parse_next_attempt_at": {"$lte": available_at}},
                        ],
                    },
                ]
            },
            sort=[("updated_at", 1), ("_id", 1)],
        )

    async def defer_parse_attempt(self, document, retry_at, stale_before):
        query = {
            "_id": document["_id"],
            "project_id": document["project_id"],
            "status": document.get("status"),
            "revision": document.get("revision"),
        }
        if document.get("status") == "PARSING":
            query["updated_at"] = {"$lte": stale_before}
            query["parse_attempt_id"] = document.get("parse_attempt_id")
        result = await self.documents.update_one(
            query,
            {"$set": {"parse_next_attempt_at": retry_at}},
        )
        return result.matched_count == 1

    async def fail_unavailable_owner_parse(
        self, document, error_code, updated_at, stale_before
    ):
        status = document.get("status")
        if status not in {"UPLOADED", "PARSING"}:
            return None
        query = {
            "_id": document["_id"],
            "project_id": document["project_id"],
            "status": status,
            "revision": document.get("revision"),
        }
        if status == "PARSING":
            query["updated_at"] = {"$lte": stale_before}
            query["parse_attempt_id"] = document.get("parse_attempt_id")
        update = {
            "$set": {
                "status": "PARSE_FAILED",
                "parse_error_type": error_code,
                "updated_at": updated_at,
            },
            "$inc": {"revision": 1},
            "$unset": {"parse_next_attempt_at": ""},
        }
        if status == "PARSING":
            update["$unset"]["parse_attempt_id"] = ""
        return await self.documents.find_one_and_update(
            query,
            update,
            return_document=ReturnDocument.AFTER,
        )

    async def list_ai_scope_page(self, project_id, after_id, limit):
        query = {
            "project_id": project_id,
            "status": "READY",
            "ai_enabled": True,
        }
        if after_id:
            query["_id"] = {"$gt": after_id}
        return await self.documents.find(query).sort("_id", 1).limit(limit).to_list(limit)

    async def set_index_result(
        self,
        document_id,
        project_id,
        index_status,
        indexed_at,
        expected_revision=None,
        index_contract_version=None,
    ):
        query = {"_id": document_id, "project_id": project_id}
        if expected_revision is not None:
            query["revision"] = expected_revision
        changes = {
            "index_status": index_status,
            "indexed_at": indexed_at,
        }
        if index_contract_version is not None:
            changes["index_contract_version"] = index_contract_version
        return await self.documents.update_one(
            query,
            {"$set": changes},
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
        unset_fields=None,
    ):
        query = {
            "_id": document_id,
            "project_id": project_id,
            "revision": revision,
        }
        if status:
            query["status"] = status
        update = {"$set": changes, "$inc": {"revision": 1}}
        if unset_fields:
            update["$unset"] = {str(field): "" for field in unset_fields}
        return await self.documents.find_one_and_update(
            query,
            update,
            return_document=ReturnDocument.AFTER,
        )

    async def transition_status(
        self,
        document_id,
        project_id,
        source_status,
        changes,
        attempt_id=None,
        unset_fields=None,
    ):
        query = {
            "_id": document_id,
            "project_id": project_id,
            "status": source_status,
        }
        update = {"$set": changes, "$inc": {"revision": 1}}
        if attempt_id:
            query["parse_attempt_id"] = attempt_id
            update["$unset"] = {"parse_attempt_id": ""}
        if unset_fields:
            update.setdefault("$unset", {}).update(
                {str(field): "" for field in unset_fields}
            )
        return await self.documents.find_one_and_update(
            query,
            update,
            return_document=ReturnDocument.AFTER,
        )

    async def claim_status(
        self,
        document_id,
        project_id,
        source_status,
        revision,
        target_status,
        updated_at,
        attempt_id=None,
    ):
        changes = {"status": target_status, "updated_at": updated_at}
        if attempt_id:
            changes["parse_attempt_id"] = attempt_id
        update = {
            "$set": changes,
            "$inc": {"revision": 1},
            "$unset": {"parse_next_attempt_at": ""},
        }
        return await self.documents.update_one(
            {
                "_id": document_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            update,
        )

    async def claim_stale_parse(
        self, document_id, project_id, revision, stale_before, updated_at, attempt_id
    ):
        return await self.documents.update_one(
            {
                "_id": document_id,
                "project_id": project_id,
                "status": "PARSING",
                "revision": revision,
                "updated_at": {"$lte": stale_before},
            },
            {
                "$set": {
                    "status": "PARSING",
                    "updated_at": updated_at,
                    "parse_attempt_id": attempt_id,
                },
                "$inc": {"revision": 1},
                "$unset": {"parse_next_attempt_at": ""},
            },
        )

    async def heartbeat_parse_attempt(self, document_id, project_id, attempt_id, updated_at):
        return await self.documents.update_one(
            {
                "_id": document_id,
                "project_id": project_id,
                "status": "PARSING",
                "parse_attempt_id": attempt_id,
            },
            {"$set": {"updated_at": updated_at}},
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
