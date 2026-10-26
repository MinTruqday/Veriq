from pymongo import ReturnDocument

from src.core.database import database


class RequirementImportRepository:
    async def find_source_document(self, document_id, project_id):
        return await database.value.requirement_documents.find_one(
            {"_id": document_id, "project_id": project_id}
        )
    async def find_by_template_version(self, project_id, template_id, version, public_view=False):
        return await database.value.import_jobs.find_one(
            {"project_id": project_id, "template_id": template_id, "template_version": version, "template_public_view": public_view}
        )
    async def find_by_source_document(self, document_id):
        return await database.value.import_jobs.find_one(
            {"source_document_id": document_id}
        )

    async def find(self, job_id, project_id):
        return await database.value.import_jobs.find_one(
            {"_id": job_id, "project_id": project_id}
        )

    async def list_current_requirements(self, project_id):
        requirements = await database.value.requirements.find(
            {"project_id": project_id},
            {"_id": 1, "requirement_key": 1, "current_version_id": 1, "status": 1},
        ).to_list(20001)
        if len(requirements) > 20000:
            return requirements, {}
        versions = await database.value.requirement_versions.find(
            {"project_id": project_id, "_id": {"$in": [item["current_version_id"] for item in requirements]}}
        ).to_list(len(requirements))
        return requirements, {item["_id"]: item for item in versions}

    async def find_current_version(self, project_id, version_id):
        return await database.value.requirement_versions.find_one(
            {"project_id": project_id, "_id": version_id}
        )

    async def list_linked_test_cases(self, project_id, version_ids):
        versions = await database.value.test_case_versions.find(
            {"project_id": project_id, "requirement_version_ids": {"$in": version_ids}},
            {"_id": 1, "test_case_id": 1, "requirement_version_ids": 1},
        ).to_list(20001)
        if len(versions) > 20000:
            return [], versions
        cases = await database.value.test_cases.find(
            {
                "project_id": project_id,
                "_id": {"$in": list({item["test_case_id"] for item in versions})},
                "status": {"$ne": "OBSOLETE"},
            },
            {"_id": 1, "test_case_key": 1, "current_version_id": 1},
        ).to_list(len(versions))
        return cases, versions

    async def insert(self, job):
        await database.value.import_jobs.insert_one(job)

    async def mark_document_extracted(
        self, document_id, project_id, status, job_id, updated_at
    ):
        await database.value.requirement_documents.update_one(
            {"_id": document_id, "project_id": project_id},
            {
                "$set": {
                    "status": status,
                    "last_import_job_id": job_id,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
        )

    async def update_preview(
        self,
        job_id,
        project_id,
        status,
        revision,
        preview,
        user_id,
        updated_at,
        review_note=None,
        push_field=None,
        push_value=None,
    ):
        changes = {
            "preview": preview,
            "candidate_count": len(preview),
            "reviewed_by": user_id,
            "reviewed_at": updated_at,
            "updated_at": updated_at,
        }
        if review_note is not None:
            changes["review_note"] = review_note
        update = {"$set": changes, "$inc": {"revision": 1}}
        if push_field:
            update["$push"] = {push_field: push_value}
        return await database.value.import_jobs.find_one_and_update(
            {
                "_id": job_id,
                "project_id": project_id,
                "status": status,
                "revision": revision,
            },
            update,
            return_document=ReturnDocument.AFTER,
        )

    async def finish_resolution(self, job_id, project_id, revision, preview, resolution, updated_at):
        return await database.value.import_jobs.find_one_and_update(
            {
                "_id": job_id,
                "project_id": project_id,
                "status": "RESOLVING",
                "revision": revision,
            },
            {
                "$set": {
                    "status": "PREVIEW_READY" if preview else "CONFIRMED",
                    "preview": preview,
                    "candidate_count": len(preview),
                    "updated_at": updated_at,
                },
                "$push": {"resolutions": resolution},
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def claim_confirmation(
        self,
        job_id,
        project_id,
        source_status,
        target_status,
        user_id,
        updated_at,
        revision=None,
    ):
        query = {"_id": job_id, "project_id": project_id, "status": source_status}
        if revision is not None:
            query["revision"] = revision
        result = await database.value.import_jobs.update_one(
            query,
            {
                "$set": {
                    "status": target_status,
                    "confirming_by": user_id,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
        )
        return result.matched_count == 1

    async def delete_created_requirements(self, requirement_ids, version_ids):
        if not requirement_ids:
            return
        await database.value.acceptance_criteria.delete_many(
            {"requirement_version_id": {"$in": version_ids}}
        )
        await database.value.requirement_versions.delete_many(
            {"_id": {"$in": version_ids}}
        )
        await database.value.requirements.delete_many(
            {"_id": {"$in": requirement_ids}}
        )

    async def reset_confirmation(
        self, job_id, project_id, source_status, target_status, updated_at
    ):
        await database.value.import_jobs.update_one(
            {"_id": job_id, "project_id": project_id, "status": source_status},
            {
                "$set": {"status": target_status, "updated_at": updated_at},
                "$inc": {"revision": 1},
            },
        )

    async def confirm(
        self,
        job_id,
        project_id,
        source_status,
        target_status,
        requirement_ids,
        selected_indexes,
        rejected_indexes,
        requirement_version_ids,
        user_id,
        updated_at,
        session=None,
    ):
        result = await database.value.import_jobs.update_one(
            {"_id": job_id, "project_id": project_id, "status": source_status},
            {
                "$set": {
                    "status": target_status,
                    "created_requirement_ids": requirement_ids,
                    "created_requirement_version_ids": requirement_version_ids,
                    "selected_indexes": selected_indexes,
                    "rejected_indexes": rejected_indexes,
                    "confirmed_at": updated_at,
                    "confirmed_by": user_id,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
            **({"session": session} if session is not None else {}),
        )
        return result.matched_count == 1

    async def confirm_document(self, document_id, project_id, status, updated_at, session=None):
        await database.value.requirement_documents.update_one(
            {"_id": document_id, "project_id": project_id},
            {
                "$set": {"status": status, "updated_at": updated_at},
                "$inc": {"revision": 1},
            },
            **({"session": session} if session is not None else {}),
        )


requirement_import_repository = RequirementImportRepository()
