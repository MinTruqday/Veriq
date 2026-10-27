from pymongo import ReturnDocument

from src.core.database import database


class DefectRepository:
    async def find_test_result(self, result_id, project_id, status=None, session=None):
        query = {"_id": result_id, "project_id": project_id}
        if status is not None:
            query["status"] = status
        return await database.value.test_results.find_one(
            query, **({"session": session} if session is not None else {})
        )

    async def find_test_run(self, run_id, project_id, session=None):
        return await database.value.test_runs.find_one(
            {"_id": run_id, "project_id": project_id},
            **({"session": session} if session is not None else {}),
        )

    async def link_failed_result_to_defect(
        self, result_id, project_id, expected_revision, test_run_id,
        test_case_version_id, defect_id, updated_at, session,
    ):
        query = {
            "_id": result_id,
            "project_id": project_id,
            "test_run_id": test_run_id,
            "test_case_version_id": test_case_version_id,
            "status": "FAIL",
            "revision": expected_revision,
        }
        return await database.value.test_results.find_one_and_update(
            query,
            {
                "$addToSet": {"linked_defect_ids": defect_id},
                "$set": {"updated_at": updated_at},
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )

    async def insert_defect(self, value, session=None):
        await database.value.defects.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def find_defect_by_idempotency(
        self, project_id, user_id, idempotency_key, session=None
    ):
        return await database.value.defects.find_one(
            {
                "project_id": project_id,
                "created_by": user_id,
                "idempotency_key": idempotency_key,
            },
            **({"session": session} if session is not None else {}),
        )

    async def list_requirement_version_ids(self, project_id, requirement_id, limit):
        values = await database.value.requirement_versions.find(
            {"project_id": project_id, "requirement_id": requirement_id}, {"_id": 1}
        ).to_list(limit)
        return [value["_id"] for value in values]

    async def list_test_case_version_ids(self, project_id, test_case_id, limit):
        values = await database.value.test_case_versions.find(
            {"project_id": project_id, "test_case_id": test_case_id}, {"_id": 1}
        ).to_list(limit)
        return [value["_id"] for value in values]

    async def count_defects(self, query):
        return await database.value.defects.count_documents(query)

    async def list_defects(self, query, sort_field, direction, skip, limit):
        return await database.value.defects.find(query).sort(
            sort_field, direction
        ).skip(skip).limit(limit).to_list(limit)

    async def list_project_defects(self, project_id, limit):
        return await database.value.defects.find({"project_id": project_id}).to_list(limit)

    async def list_trace_links(self, project_id, defect_id, artifact_type, limit):
        return await database.value.trace_links.find(
            {
                "project_id": project_id,
                "$or": [
                    {"source_type": artifact_type, "source_id": defect_id},
                    {"target_type": artifact_type, "target_id": defect_id},
                ],
            }
        ).sort("created_at", -1).to_list(limit)

    async def list_comments(self, project_id, defect_id, artifact_type, limit):
        return await database.value.review_comments.find(
            {
                "project_id": project_id,
                "artifact_type": artifact_type,
                "artifact_id": defect_id,
            }
        ).sort("created_at", 1).to_list(limit)

    async def list_attachments(
        self, project_id, defect_id, artifact_type, active_status, limit
    ):
        return await database.value.attachments.find(
            {
                "project_id": project_id,
                "artifact_type": artifact_type,
                "artifact_id": defect_id,
                "status": active_status,
            }
        ).sort("created_at", -1).to_list(limit)

    async def find_test_case_version(self, version_id, project_id, session=None):
        return await database.value.test_case_versions.find_one(
            {"_id": version_id, "project_id": project_id},
            **({"session": session} if session is not None else {}),
        )

    async def count_requirement_versions(self, project_id, version_ids, session=None):
        return await database.value.requirement_versions.count_documents(
            {"project_id": project_id, "_id": {"$in": version_ids}},
            **({"session": session} if session is not None else {}),
        )

    async def transition_defect(
        self, defect_id, project_id, current_status, revision, changes, session=None
    ):
        return await database.value.defects.find_one_and_update(
            {
                "_id": defect_id,
                "project_id": project_id,
                "status": current_status,
                "revision": revision,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def find_retest(self, defect_id, idempotency_key):
        return await database.value.defect_retests.find_one(
            {"defect_id": defect_id, "idempotency_key": idempotency_key}
        )

    async def find_defect(self, defect_id, project_id):
        return await database.value.defects.find_one(
            {"_id": defect_id, "project_id": project_id}
        )

    async def insert_retest(self, value, session=None):
        await database.value.defect_retests.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def apply_retest(
        self,
        defect_id,
        project_id,
        source_status,
        revision,
        target_status,
        event_id,
        result_id,
        updated_at,
        session=None,
    ):
        return await database.value.defects.find_one_and_update(
            {
                "_id": defect_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            {
                "$set": {
                    "status": target_status,
                    "last_retest_id": event_id,
                    "last_retest_result_id": result_id,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
                "$push": {"retest_event_ids": event_id},
            },
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def delete_retest(self, event_id, application_status):
        await database.value.defect_retests.delete_one(
            {"_id": event_id, "application_status": application_status}
        )

    async def mark_retest_applied(self, event_id, application_status, session=None):
        await database.value.defect_retests.update_one(
            {"_id": event_id},
            {"$set": {"application_status": application_status}},
            **({"session": session} if session is not None else {}),
        )

    async def find_ai_result_by_idempotency(self, project_id, idempotency_key):
        return await database.value.ai_results.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_ai_result(self, value):
        await database.value.ai_results.insert_one(value)
        return value

    async def find_ai_result(self, result_id, project_id, result_type, subject_id):
        return await database.value.ai_results.find_one(
            {
                "_id": result_id,
                "project_id": project_id,
                "result_type": result_type,
                "subject_id": subject_id,
            }
        )

    async def list_ai_results_for_defects(self, project_id, defect_ids):
        return await database.value.ai_results.aggregate(
            [
                {
                    "$match": {
                        "project_id": project_id,
                        "result_type": "BUG_TRACE_SUGGESTION",
                        "subject_id": {"$in": defect_ids},
                    }
                },
                {"$sort": {"created_at": -1, "_id": -1}},
                {"$group": {"_id": "$subject_id", "item": {"$first": "$$ROOT"}}},
                {"$replaceRoot": {"newRoot": "$item"}},
            ]
        ).to_list(len(defect_ids))

    async def review_ai_result(self, result_id, project_id, changes):
        await database.value.ai_results.update_one(
            {"_id": result_id, "project_id": project_id},
            {"$set": changes, "$inc": {"revision": 1}},
        )


defect_repository = DefectRepository()
