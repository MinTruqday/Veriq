from pymongo import ReturnDocument

from src.core.database import database


class RequirementRepository:
    async def find_transformation(self, project_id, idempotency_key):
        return await database.value.requirement_transformations.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def claim_failed_transformation(
        self, transformation_id, project_id, failed_status, active_status, updated_at
    ):
        return await database.value.requirement_transformations.find_one_and_update(
            {
                "_id": transformation_id,
                "project_id": project_id,
                "status": failed_status,
            },
            {
                "$set": {"status": active_status, "updated_at": updated_at},
                "$unset": {"error_code": ""},
                "$inc": {"attempt": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def insert_transformation(self, transformation):
        await database.value.requirement_transformations.insert_one(transformation)

    async def list_requirements_by_ids(self, project_id, requirement_ids, limit):
        return await database.value.requirements.find(
            {"_id": {"$in": requirement_ids}, "project_id": project_id}
        ).to_list(limit)

    async def insert_outputs(self, requirements, versions, criteria):
        await database.value.requirements.insert_many(requirements)
        await database.value.requirement_versions.insert_many(versions)
        if criteria:
            await database.value.acceptance_criteria.insert_many(criteria)

    async def supersede_version(
        self,
        version_id,
        project_id,
        source_status,
        target_status,
        result_ids,
        transformation_id,
        user_id,
        timestamp,
    ):
        result = await database.value.requirement_versions.update_one(
            {
                "_id": version_id,
                "project_id": project_id,
                "status": source_status,
                "superseded_by_transformation_id": {"$exists": False},
            },
            {
                "$set": {
                    "status": target_status,
                    "superseded_by_requirement_ids": result_ids,
                    "superseded_by_transformation_id": transformation_id,
                    "superseded_at": timestamp,
                    "superseded_by": user_id,
                    "updated_at": timestamp,
                },
                "$inc": {"revision": 1},
            },
        )
        return result.matched_count == 1

    async def supersede_requirement(
        self,
        requirement_id,
        version_id,
        project_id,
        source_status,
        target_status,
        result_ids,
        transformation_id,
        user_id,
        timestamp,
    ):
        result = await database.value.requirements.update_one(
            {
                "_id": requirement_id,
                "project_id": project_id,
                "current_version_id": version_id,
                "status": source_status,
                "superseded_by_transformation_id": {"$exists": False},
            },
            {
                "$set": {
                    "status": target_status,
                    "superseded_by_requirement_ids": result_ids,
                    "superseded_by_transformation_id": transformation_id,
                    "superseded_at": timestamp,
                    "superseded_by": user_id,
                    "updated_at": timestamp,
                }
            },
        )
        return result.matched_count == 1

    async def confirm_transformation(
        self,
        transformation_id,
        project_id,
        source_status,
        target_status,
        requirement_ids,
        version_ids,
        timestamp,
    ):
        return await database.value.requirement_transformations.find_one_and_update(
            {
                "_id": transformation_id,
                "project_id": project_id,
                "status": source_status,
            },
            {
                "$set": {
                    "status": target_status,
                    "result_requirement_ids": requirement_ids,
                    "result_version_ids": version_ids,
                    "confirmed_at": timestamp,
                    "updated_at": timestamp,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def rollback_superseded_source(
        self, requirement_id, version_id, project_id, transformation_id, status, updated_at
    ):
        cleanup = {
            "superseded_by_requirement_ids": "",
            "superseded_by_transformation_id": "",
            "superseded_at": "",
            "superseded_by": "",
        }
        await database.value.requirements.update_one(
            {
                "_id": requirement_id,
                "project_id": project_id,
                "superseded_by_transformation_id": transformation_id,
            },
            {"$set": {"status": status, "updated_at": updated_at}, "$unset": cleanup},
        )
        await database.value.requirement_versions.update_one(
            {
                "_id": version_id,
                "project_id": project_id,
                "superseded_by_transformation_id": transformation_id,
            },
            {
                "$set": {"status": status, "updated_at": updated_at},
                "$unset": cleanup,
                "$inc": {"revision": 1},
            },
        )

    async def discard_transformation_outputs(self, project_id, transformation_id, criterion_ids):
        await database.value.acceptance_criteria.delete_many(
            {"project_id": project_id, "_id": {"$in": criterion_ids}}
        )
        await database.value.requirement_versions.delete_many(
            {"project_id": project_id, "transformation_id": transformation_id}
        )
        await database.value.requirements.delete_many(
            {"project_id": project_id, "transformation_id": transformation_id}
        )

    async def fail_transformation(
        self, transformation_id, project_id, status, error_code, updated_at
    ):
        await database.value.requirement_transformations.update_one(
            {"_id": transformation_id, "project_id": project_id},
            {
                "$set": {
                    "status": status,
                    "error_code": error_code,
                    "updated_at": updated_at,
                }
            },
        )

    async def insert_acceptance_criteria(self, criteria):
        if criteria:
            await database.value.acceptance_criteria.insert_many(criteria)

    async def set_acceptance_criterion_ids(self, version_id, criterion_ids):
        await database.value.requirement_versions.update_one(
            {"_id": version_id},
            {"$set": {"acceptance_criterion_ids": criterion_ids}},
        )

    async def insert_requirement(self, requirement):
        await database.value.requirements.insert_one(requirement)

    async def insert_version(self, version):
        await database.value.requirement_versions.insert_one(version)

    async def delete_requirement(self, requirement_id, project_id=None):
        query = {"_id": requirement_id}
        if project_id:
            query["project_id"] = project_id
        await database.value.requirements.delete_one(query)

    async def delete_version(self, version_id, project_id=None):
        query = {"_id": version_id}
        if project_id:
            query["project_id"] = project_id
        await database.value.requirement_versions.delete_one(query)

    async def delete_acceptance_criteria(self, version_id):
        await database.value.acceptance_criteria.delete_many(
            {"requirement_version_id": version_id}
        )

    async def list_requirements(self, project_id, status=None, limit=20000):
        query = {"project_id": project_id}
        if status:
            query["status"] = status
        return await database.value.requirements.find(query).to_list(limit)

    async def list_versions_by_ids(self, project_id, version_ids, limit=20000):
        return await database.value.requirement_versions.find(
            {"project_id": project_id, "_id": {"$in": version_ids}}
        ).to_list(limit)

    async def list_confirmed_trace_sources(
        self, project_id, version_ids, status, source_type, limit=50000
    ):
        return await database.value.trace_links.find(
            {
                "project_id": project_id,
                "status": status,
                "source_type": source_type,
                "source_id": {"$in": version_ids},
            },
            {"source_id": 1},
        ).to_list(limit)

    async def list_pending_change_targets(
        self, project_id, version_ids, completed_statuses, limit=20000
    ):
        return await database.value.requirement_change_sets.find(
            {
                "project_id": project_id,
                "to_version_id": {"$in": version_ids},
                "status": {"$nin": completed_statuses},
            },
            {"to_version_id": 1},
        ).to_list(limit)

    async def find_duplicate_key(self, project_id, requirement_id, requirement_key):
        return await database.value.requirements.find_one(
            {
                "project_id": project_id,
                "requirement_key": requirement_key,
                "_id": {"$ne": requirement_id},
            }
        )

    async def update_draft(self, version_id, project_id, revision, draft_status, changes):
        return await database.value.requirement_versions.find_one_and_update(
            {
                "_id": version_id,
                "project_id": project_id,
                "status": draft_status,
                "revision": revision,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def update_requirement_identity(
        self, requirement_id, project_id, changes, version_id=None
    ):
        query = {"_id": requirement_id, "project_id": project_id}
        if version_id:
            query["current_version_id"] = version_id
        await database.value.requirements.update_one(query, {"$set": changes})

    async def replace_acceptance_criteria(self, version_id, criteria, criterion_ids):
        await self.delete_acceptance_criteria(version_id)
        await self.insert_acceptance_criteria(criteria)
        await self.set_acceptance_criterion_ids(version_id, criterion_ids)

    async def find_latest_version(self, requirement_id):
        return await database.value.requirement_versions.find_one(
            {"requirement_id": requirement_id}, sort=[("version", -1)]
        )

    async def activate_version(
        self, requirement_id, version_id, status, tags, owner_id, updated_at, expected_current_version_id
    ):
        result = await database.value.requirements.update_one(
            {"_id": requirement_id, "current_version_id": expected_current_version_id},
            {
                "$set": {
                    "current_version_id": version_id,
                    "status": status,
                    "tags": tags,
                    "owner_id": owner_id,
                    "updated_at": updated_at,
                }
            },
        )
        return result.modified_count == 1

    async def list_versions(self, requirement_id, limit=500):
        return (
            await database.value.requirement_versions.find(
                {"requirement_id": requirement_id}
            )
            .sort("version", -1)
            .to_list(limit)
        )

    async def find_version(self, version_id, project_id=None, requirement_id=None, status=None):
        query = {"_id": version_id}
        if project_id:
            query["project_id"] = project_id
        if requirement_id:
            query["requirement_id"] = requirement_id
        if status:
            query["status"] = status
        return await database.value.requirement_versions.find_one(query)

    async def list_acceptance_criteria(self, version_id, limit):
        return await database.value.acceptance_criteria.find(
            {"requirement_version_id": version_id}
        ).to_list(limit)

    async def find_project_settings(self, project_id):
        return await database.value.projects.find_one({"_id": project_id}, {"settings": 1})

    async def transition_version(
        self, version_id, project_id, revision, source_status, target_status, changes
    ):
        result = await database.value.requirement_versions.update_one(
            {
                "_id": version_id,
                "project_id": project_id,
                "revision": revision,
                "status": source_status,
            },
            {"$set": {**changes, "status": target_status}, "$inc": {"revision": 1}},
        )
        return result.matched_count == 1

    async def set_requirement_status(self, requirement_id, project_id, status, updated_at):
        await database.value.requirements.update_one(
            {"_id": requirement_id, "project_id": project_id},
            {"$set": {"status": status, "updated_at": updated_at}},
        )

    async def baseline_version(self, version_id, project_id, revision, source_status, changes):
        return await database.value.requirement_versions.find_one_and_update(
            {
                "_id": version_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def set_current_baseline(
        self, requirement_id, version_id, status, updated_at
    ):
        await database.value.requirements.update_one(
            {"_id": requirement_id},
            {
                "$set": {
                    "current_version_id": version_id,
                    "status": status,
                    "updated_at": updated_at,
                }
            },
        )

    async def approve_acceptance_criteria(
        self, version_id, source_status, target_status, approved_at, approved_by
    ):
        await database.value.acceptance_criteria.update_many(
            {"requirement_version_id": version_id, "status": source_status},
            {
                "$set": {
                    "status": target_status,
                    "approved_at": approved_at,
                    "approved_by": approved_by,
                }
            },
        )

    async def mark_requirement_obsolete(
        self,
        requirement_id,
        project_id,
        version_id,
        source_status,
        obsolete_status,
        reason,
        user_id,
        timestamp,
    ):
        return await database.value.requirements.find_one_and_update(
            {
                "_id": requirement_id,
                "project_id": project_id,
                "current_version_id": version_id,
                "status": source_status,
            },
            {
                "$set": {
                    "status": obsolete_status,
                    "status_before_obsolete": source_status,
                    "obsolete_reason": reason,
                    "obsolete_by": user_id,
                    "obsolete_at": timestamp,
                    "updated_at": timestamp,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def mark_version_obsolete(
        self,
        version_id,
        project_id,
        requirement_id,
        source_statuses,
        obsolete_status,
        previous_status,
        reason,
        user_id,
        timestamp,
    ):
        result = await database.value.requirement_versions.update_one(
            {
                "_id": version_id,
                "project_id": project_id,
                "requirement_id": requirement_id,
                "status": {"$in": source_statuses},
            },
            {
                "$set": {
                    "status": obsolete_status,
                    "status_before_obsolete": previous_status,
                    "obsolete_reason": reason,
                    "obsolete_by": user_id,
                    "obsolete_at": timestamp,
                    "updated_at": timestamp,
                },
                "$inc": {"revision": 1},
            },
        )
        return result.matched_count == 1

    async def rollback_requirement_obsolete(
        self, requirement_id, project_id, obsolete_status, obsolete_at, restored_status, updated_at
    ):
        await database.value.requirements.update_one(
            {
                "_id": requirement_id,
                "project_id": project_id,
                "status": obsolete_status,
                "obsolete_at": obsolete_at,
            },
            {
                "$set": {"status": restored_status, "updated_at": updated_at},
                "$unset": {
                    "obsolete_reason": "",
                    "obsolete_by": "",
                    "obsolete_at": "",
                    "status_before_obsolete": "",
                },
            },
        )

    async def restore_version(
        self,
        version_id,
        project_id,
        requirement_id,
        obsolete_status,
        restored_status,
        reason,
        user_id,
        timestamp,
    ):
        result = await database.value.requirement_versions.update_one(
            {
                "_id": version_id,
                "project_id": project_id,
                "requirement_id": requirement_id,
                "status": obsolete_status,
            },
            {
                "$set": {
                    "status": restored_status,
                    "restore_reason": reason,
                    "restored_by": user_id,
                    "restored_at": timestamp,
                    "updated_at": timestamp,
                },
                "$unset": {
                    "status_before_obsolete": "",
                    "obsolete_reason": "",
                    "obsolete_by": "",
                    "obsolete_at": "",
                },
                "$inc": {"revision": 1},
            },
        )
        return result.matched_count == 1

    async def restore_requirement(
        self,
        requirement_id,
        project_id,
        version_id,
        obsolete_status,
        restored_status,
        reason,
        user_id,
        timestamp,
    ):
        return await database.value.requirements.find_one_and_update(
            {
                "_id": requirement_id,
                "project_id": project_id,
                "current_version_id": version_id,
                "status": obsolete_status,
            },
            {
                "$set": {
                    "status": restored_status,
                    "restore_reason": reason,
                    "restored_by": user_id,
                    "restored_at": timestamp,
                    "updated_at": timestamp,
                },
                "$unset": {
                    "status_before_obsolete": "",
                    "obsolete_reason": "",
                    "obsolete_by": "",
                    "obsolete_at": "",
                },
            },
            return_document=ReturnDocument.AFTER,
        )

    async def rollback_version_restore(
        self, version_id, project_id, obsolete_status, restored_status, updated_at
    ):
        await database.value.requirement_versions.update_one(
            {"_id": version_id, "project_id": project_id},
            {
                "$set": {
                    "status": obsolete_status,
                    "status_before_obsolete": restored_status,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
        )


requirement_repository = RequirementRepository()
